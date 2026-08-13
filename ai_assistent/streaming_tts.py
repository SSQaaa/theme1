import os
import asyncio
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import numpy as np
import sherpa_onnx
import soundfile as sf


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
    volume_gain: float = float(os.getenv("SHERPA_TTS_VOLUME_GAIN", "2.0"))
    target_peak: float = float(os.getenv("SHERPA_TTS_TARGET_PEAK", "0.92"))
    debug: bool = os.getenv("SHERPA_TTS_DEBUG", "0") == "1"


@dataclass
class OnlineEdgeTTSConfig:
    voice: str = os.getenv("EDGE_TTS_VOICE", "zh-CN-XiaoxiaoNeural")
    ffmpeg_bin: str = os.getenv("FFMPEG_BIN", "ffmpeg")
    sample_rate: int = int(os.getenv("EDGE_TTS_SAMPLE_RATE", "16000"))
    channels: int = 1
    sample_fmt: str = "s16"


class LocalVitsTTS:
    """Local sherpa-onnx VITS synthesis and playback."""

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
        # sherpa-onnx 1.12.28 exposes GenerationConfig, but its VITS backend
        # does not implement that overload. The legacy keyword API works for
        # VITS and remains compatible with newer sherpa-onnx releases.
        audio = self.tts.generate(
            text,
            sid=self.config.speaker_id,
            speed=self.config.speed,
        )
        if len(audio.samples) == 0:
            raise RuntimeError(
                "sherpa-onnx VITS generated empty audio. Check that the model "
                "matches the installed sherpa-onnx version."
            )
        samples = self._postprocess_samples(audio.samples)
        sf.write(wav_path, samples, audio.sample_rate, subtype="PCM_16")
        return wav_path

    def _postprocess_samples(self, samples) -> np.ndarray:
        samples_np = np.asarray(samples, dtype=np.float32)
        if samples_np.size == 0:
            return samples_np

        peak = float(np.max(np.abs(samples_np)))
        if peak > 1e-6:
            # First lift quiet VITS output by a configurable gain, then cap the
            # peak so the PCM_16 WAV stays loud without clipping.
            samples_np = samples_np * self.config.volume_gain
            peak = float(np.max(np.abs(samples_np)))
            if peak > self.config.target_peak:
                samples_np = samples_np * (self.config.target_peak / peak)

        return np.clip(samples_np, -1.0, 1.0)

    def play(self, wav_path: str) -> None:
        subprocess.run(self._aplay_cmd(wav_path), check=True)

    def speak(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return

        wav_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        try:
            self.synthesize(text, wav_path)
            self.play(wav_path)
        finally:
            try:
                os.unlink(wav_path)
            except OSError:
                pass


class OnlineEdgeTTS:
    """Online Edge TTS synthesis and playback."""

    def __init__(
        self,
        aplay_device: Optional[str] = None,
        config: Optional[OnlineEdgeTTSConfig] = None,
    ):
        self.aplay_device = aplay_device
        self.config = config or OnlineEdgeTTSConfig()

    def _aplay_cmd(self, wav_path: str) -> List[str]:
        cmd = ["aplay"]
        if self.aplay_device:
            cmd += ["-D", self.aplay_device]
        return [*cmd, wav_path]

    async def _synthesize_async(self, text: str, wav_path: str) -> str:
        import edge_tts

        mp3_path = f"{wav_path}.mp3"
        communicate = edge_tts.Communicate(text=text, voice=self.config.voice)
        await communicate.save(mp3_path)

        subprocess.run(
            [
                self.config.ffmpeg_bin,
                "-y",
                "-i",
                mp3_path,
                "-ar",
                str(self.config.sample_rate),
                "-ac",
                str(self.config.channels),
                "-sample_fmt",
                self.config.sample_fmt,
                wav_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

        try:
            os.unlink(mp3_path)
        except OSError:
            pass

        return wav_path

    def synthesize(self, text: str, wav_path: str) -> str:
        return asyncio.run(self._synthesize_async(text, wav_path))

    def play(self, wav_path: str) -> None:
        subprocess.run(self._aplay_cmd(wav_path), check=True)

    def speak(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return

        wav_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        try:
            self.synthesize(text, wav_path)
            self.play(wav_path)
        finally:
            try:
                os.unlink(wav_path)
            except OSError:
                pass


__all__ = ["LocalVitsTTS", "LocalVitsTTSConfig", "OnlineEdgeTTS", "OnlineEdgeTTSConfig"]
