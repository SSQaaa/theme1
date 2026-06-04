import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import sherpa_onnx
import soundfile as sf


def split_sentences(text: str) -> List[str]:
    """Split Chinese/English text into short chunks for faster first playback."""
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return []

    parts = [
        part.strip()
        for part in re.split(r"(?<=[。！？!?；;])\s*", text)
        if part.strip()
    ]
    if len(parts) <= 1 and len(text) > 80:
        parts = [text[i : i + 60].strip() for i in range(0, len(text), 60)]
    return parts


@dataclass
class LocalVitsTTSConfig:
    model_dir: str = os.getenv(
        "SHERPA_TTS_MODEL_DIR",
        str(Path(__file__).resolve().parent / "vits-melo-tts-zh_en"),
    )
    num_threads: int = int(os.getenv("SHERPA_TTS_NUM_THREADS", "2"))
    provider: str = os.getenv("SHERPA_TTS_PROVIDER", "cpu")
    speaker_id: int = int(os.getenv("SHERPA_TTS_SID", "0"))
    speed: float = float(os.getenv("SHERPA_TTS_SPEED", "1.0"))
    silence_scale: float = float(os.getenv("SHERPA_TTS_SILENCE_SCALE", "0.2"))
    debug: bool = os.getenv("SHERPA_TTS_DEBUG", "0") == "1"


class LocalVitsTTS:
    """Local sherpa-onnx VITS synthesis with sentence-by-sentence playback."""

    def __init__(
        self,
        aplay_device: Optional[str] = None,
        config: Optional[LocalVitsTTSConfig] = None,
    ):
        self.aplay_device = aplay_device
        self.config = config or LocalVitsTTSConfig()
        self.model_dir = Path(self.config.model_dir).expanduser().resolve()
        self.tts = self._create_tts()

    def _required_path(self, filename: str) -> str:
        path = self.model_dir / filename
        if not path.is_file():
            raise FileNotFoundError(
                f"Missing sherpa-onnx VITS file: {path}\n"
                "Download the model first or set SHERPA_TTS_MODEL_DIR."
            )
        return str(path)

    def _create_tts(self) -> sherpa_onnx.OfflineTts:
        rule_fsts = [
            str(path)
            for path in (
                self.model_dir / "phone.fst",
                self.model_dir / "date.fst",
                self.model_dir / "number.fst",
            )
            if path.is_file()
        ]
        config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model=self._required_path("model.onnx"),
                    lexicon=self._required_path("lexicon.txt"),
                    tokens=self._required_path("tokens.txt"),
                ),
                provider=self.config.provider,
                debug=self.config.debug,
                num_threads=self.config.num_threads,
            ),
            rule_fsts=",".join(rule_fsts),
        )
        if not config.validate():
            raise ValueError(f"Invalid sherpa-onnx VITS config: {self.model_dir}")
        return sherpa_onnx.OfflineTts(config)

    def _aplay_cmd(self, wav_path: str) -> List[str]:
        cmd = ["aplay"]
        if self.aplay_device:
            cmd += ["-D", self.aplay_device]
        return [*cmd, wav_path]

    def synthesize(self, text: str, wav_path: str) -> str:
        generation_config = sherpa_onnx.GenerationConfig()
        generation_config.sid = self.config.speaker_id
        generation_config.speed = self.config.speed
        generation_config.silence_scale = self.config.silence_scale

        audio = self.tts.generate(text, generation_config)
        if len(audio.samples) == 0:
            raise RuntimeError("sherpa-onnx generated empty audio")
        sf.write(wav_path, audio.samples, audio.sample_rate, subtype="PCM_16")
        return wav_path

    def speak(self, text: str) -> None:
        for sentence in split_sentences(text):
            wav_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
            try:
                self.synthesize(sentence, wav_path)
                subprocess.run(self._aplay_cmd(wav_path), check=True)
            finally:
                try:
                    os.unlink(wav_path)
                except OSError:
                    pass


__all__ = ["LocalVitsTTS", "LocalVitsTTSConfig", "split_sentences"]
