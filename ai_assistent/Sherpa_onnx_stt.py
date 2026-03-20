#!/usr/bin/env python3
from pathlib import Path
import sherpa_onnx
import soundfile as sf
from typing import Union
import numpy as np
import time

model_path = "/home/orangepi/Desktop/theme1/ai_assistent/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09/model.int8.onnx"
tokens_path = "/home/orangepi/Desktop/theme1/ai_assistent/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09/tokens.txt"
test_wav = "/home/orangepi/Desktop/theme1/ai_assistent/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09/test_wavs/zh.wav"

class SpeechToText:

    def __init__(self):

        self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=model_path,
            tokens=tokens_path,
            use_itn=True,
            debug=False,
        )

    def transcribe_file(self, wav_path: str) -> str:
        """识别 WAV 文件"""
        if not Path(wav_path).is_file():
            raise FileNotFoundError(f"WAV 文件不存在: {wav_path}")

        audio, sample_rate = sf.read(wav_path, dtype="float32", always_2d=True)
        audio = audio[:, 0]  # 取第一通道

        return self.transcribe_audio(audio, sample_rate)

    def transcribe_audio(self, audio: Union[np.ndarray, list], sample_rate: int) -> str:
        """识别音频数据"""
        audio_np = np.array(audio, dtype="float32")
        stream = self.recognizer.create_stream()
        stream.accept_waveform(sample_rate, audio_np)
        self.recognizer.decode_stream(stream)
        print("STT stream result:", stream.result)
        return stream.result.text if hasattr(stream.result, "text") else str(stream.result)
