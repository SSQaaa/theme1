import asyncio
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Iterable, List, Optional

import edge_tts


_SENT_SPLIT_RE = re.compile(r"(?<=[。！？!?；;])\s*|")


def split_sentences(text: str) -> List[str]:
    """Split Chinese/English text into speakable chunks.

    Keeps punctuation at the end of each sentence.
    """
    text = (text or "").strip()
    if not text:
        return []

    # Basic normalization: collapse whitespace
    text = re.sub(r"\s+", " ", text)

    # Prefer punctuation-based splitting
    parts = re.split(r"(?<=[。！？!?；;])\s*", text)
    parts = [p.strip() for p in parts if p and p.strip()]

    # Fallback: if no punctuation, chunk by length
    if len(parts) <= 1 and len(text) > 80:
        parts = [text[i : i + 60].strip() for i in range(0, len(text), 60)]

    return parts


@dataclass
class StreamingTTSConfig:
    voice: str = os.getenv("EDGE_TTS_VOICE", "zh-CN-XiaoxiaoNeural")
    sample_rate: int = 16000
    channels: int = 1
    sample_fmt: str = "s16"
    ffmpeg_bin: str = os.getenv("FFMPEG_BIN", "ffmpeg")


class StreamingEdgeTTS:
    """Stream-like TTS: synthesize sentence by sentence and play sequentially.

    This is not true audio streaming from edge-tts; instead it overlaps *generation* of
    the next sentence with *playback* of the current sentence.
    """

    def __init__(self, aplay_device: Optional[str] = None, config: Optional[StreamingTTSConfig] = None):
        self.aplay_device = aplay_device
        self.config = config or StreamingTTSConfig()

    def _aplay_cmd(self, wav_path: str) -> List[str]:
        cmd = ["aplay"]
        if self.aplay_device:
            cmd += ["-D", self.aplay_device]
        cmd.append(wav_path)
        return cmd

    async def _synth_to_wav_async(self, text: str, wav_path: str) -> str:
        # 1) edge-tts to temp mp3
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            mp3_path = f.name

        communicate = edge_tts.Communicate(text=text, voice=self.config.voice)
        await communicate.save(mp3_path)

        # 2) mp3 -> wav (16k mono s16)
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
        )

        try:
            os.unlink(mp3_path)
        except Exception:
            pass

        return wav_path

    def _synth_to_wav(self, text: str, wav_path: str) -> str:
        return asyncio.run(self._synth_to_wav_async(text, wav_path))

    def speak(self, text: str):
        """Speak text sentence-by-sentence, overlapping generation and playback."""
        sentences = split_sentences(text)
        if not sentences:
            return

        # Pre-generate first sentence (so we can start playing quickly)
        first = sentences[0]
        cur_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        self._synth_to_wav(first, cur_wav)

        for idx in range(len(sentences)):
            # Launch next sentence generation in background while playing current
            next_proc: Optional[subprocess.Popen] = None
            next_wav: Optional[str] = None

            if idx + 1 < len(sentences):
                next_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name

                py_code = """
import asyncio
import sys
import subprocess
import os
import edge_tts

async def main():
    text = sys.argv[1]
    voice = sys.argv[2]
    ffmpeg_bin = sys.argv[3]
    wav_path = sys.argv[4]

    # temp mp3
    mp3_path = wav_path + '.mp3'
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(mp3_path)

    subprocess.run([
        ffmpeg_bin, '-y', '-i', mp3_path,
        '-ar', '16000', '-ac', '1', '-sample_fmt', 's16', wav_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        os.unlink(mp3_path)
    except Exception:
        pass

asyncio.run(main())
"""
                next_proc = subprocess.Popen(
                    [
                        "python3",
                        "-c",
                        py_code,
                        sentences[idx + 1],
                        self.config.voice,
                        self.config.ffmpeg_bin,
                        next_wav,
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            # Play current
            subprocess.run(self._aplay_cmd(cur_wav))

            # Cleanup current
            try:
                os.unlink(cur_wav)
            except Exception:
                pass

            # Wait for next (if any) and roll forward
            if next_proc is not None and next_wav is not None:
                next_proc.wait()
                cur_wav = next_wav


__all__ = ["StreamingEdgeTTS", "StreamingTTSConfig", "split_sentences"]
