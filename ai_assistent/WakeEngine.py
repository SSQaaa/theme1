import numpy as np
import pyaudio
import sherpa_onnx

decoder = "./sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/decoder-epoch-12-avg-2-chunk-16-left-64.onnx"
encoder = "./sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/encoder-epoch-12-avg-2-chunk-16-left-64.onnx"
joiner  = "./sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/joiner-epoch-12-avg-2-chunk-16-left-64.onnx"
tokens  = "./sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/tokens.txt"
keywords_file = "./sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/test_wavs/test_keywords.txt"
wake_keywors = ["你好困困"]
exit_keywords = ["再见困困", "困困拜拜"]

class WakeEngine:
    def __init__(self):
        # 创建关键词检测器
        self.kws = sherpa_onnx.KeywordSpotter(
            tokens=tokens,
            encoder=encoder,
            decoder=decoder,
            joiner=joiner,
            num_threads=2,
            max_active_paths=4,
            keywords_file=keywords_file,
            keywords_score=1.5,        # 越大越容易触发
            keywords_threshold=0.25,   # 越小越容易触发
            num_trailing_blanks=1,
            provider="cpu"
        )

        self.stream = self.kws.create_stream()
        self.p = pyaudio.PyAudio()

        self.audio_stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1600,  # 更低延迟
        )

        print("self.kws engine inited.")

    def detect_keywords(self):
        try:
            while True:
                # 从麦克风读取音频数据
                audio_data = self.audio_stream.read(1600, exception_on_overflow=False)

                # 将 bytes 转换为 numpy array
                samples_int16 = np.frombuffer(audio_data, dtype=np.int16)
                samples_float32 = samples_int16.astype(np.float32) / 32768.0

                # 将音频数据传递给关键词检测器
                self.stream.accept_waveform(16000, samples_float32)

                # 执行检测
                while self.kws.is_ready(self.stream):
                    self.kws.decode_stream(self.stream)
                    result = self.kws.get_result(self.stream)
                    
                    if result in wake_keywors:
                        print(f"KUNKUN WOKE UP!: {result}")
                        # 重要：检测到关键词后必须重置 self.stream
                        self.kws.reset_stream(self.stream)
                        return "wake"
                    elif result in exit_keywords:
                        print(f"KUNKUN EXITED!: {result}")
                        self.kws.reset_stream(self.stream)
                        return "exit"

        except KeyboardInterrupt:
            print("\n程序已停止（用户中断）")
            return False


    def close(self):
        self.audio_stream.stop_stream()
        self.audio_stream.close()
        self.p.terminate()




# ############################ sounddevice版本 ##################################

# # WakeEngine_sd.py
# import numpy as np
# import sounddevice as sd
# import sherpa_onnx
# import scipy.signal

# decoder = "/home/orangepi/Desktop/theme1/ai_assistent/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/decoder-epoch-12-avg-2-chunk-16-left-64.onnx"
# encoder = "/home/orangepi/Desktop/theme1/ai_assistent/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/encoder-epoch-12-avg-2-chunk-16-left-64.onnx"
# joiner  = "/home/orangepi/Desktop/theme1/ai_assistent/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/joiner-epoch-12-avg-2-chunk-16-left-64.onnx"
# tokens  = "/home/orangepi/Desktop/theme1/ai_assistent/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/tokens.txt"
# keywords_file = "/home/orangepi/Desktop/theme1/ai_assistent/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/test_wavs/test_keywords.txt"

# wake_keywords = ["你好困困"]
# exit_keywords = ["再见困困", "困困拜拜"]

# class WakeEngine:
#     def __init__(self, device=None):
#         self.device = device if device is not None else self.find_input_device()
#         print("Using audio device:", self.device)

#         self.kws = sherpa_onnx.KeywordSpotter(
#             tokens=tokens,
#             encoder=encoder,
#             decoder=decoder,
#             joiner=joiner,
#             num_threads=2,
#             max_active_paths=4,
#             keywords_file=keywords_file,
#             keywords_score=1.5,
#             keywords_threshold=0.25,
#             num_trailing_blanks=1,
#             provider="cpu"
#         )

#         self.stream = self.kws.create_stream()
#         print("Wake engine initialized.")

#     def find_input_device(self):
#         devices = sd.query_devices()
#         for i, dev in enumerate(devices):
#             if dev['max_input_channels'] > 0:
#                 name = dev['name'].lower()
#                 if "usb" in name or "mic" in name or "uac" in name:
#                     return i
#         # 如果没找到，返回默认输入
#         return sd.default.device[0]


#     def detect_keywords(self):
#         hw_samplerate = 48000  # 实际硬件采样率
#         target_samplerate = 16000  # KWS 模型需要
#         blocksize = 4800  # 0.1秒块：48000*0.1

#         with sd.InputStream(
#             samplerate=hw_samplerate,
#             channels=1,
#             dtype='int16',
#             blocksize=blocksize,
#             device=self.device
#         ) as audio_stream:

#             print("Listening for wake word...")
#             try:
#                 while True:
#                     audio_data, _ = audio_stream.read(blocksize)
#                     audio_float = audio_data.flatten().astype(np.float32) / 32768.0

#                     # 🔹 重新采样到 16kHz
#                     resampled = scipy.signal.resample_poly(audio_float, target_samplerate, hw_samplerate)

#                     self.stream.accept_waveform(target_samplerate, resampled)

#                     while self.kws.is_ready(self.stream):
#                         self.kws.decode_stream(self.stream)
#                         result = self.kws.get_result(self.stream)
#                         if result.strip():
#                             print("now:", result)

#                         if result in wake_keywords:
#                             print("KUNKUN WOKE UP!")
#                             self.kws.reset_stream(self.stream)
#                             return "wake"
#                         elif result in exit_keywords:
#                             print("KUNKUN EXITED!")
#                             self.kws.reset_stream(self.stream)
#                             return "exit"

#             except KeyboardInterrupt:
#                 print("\nStopped by user")
#                 return False





# from faster_whisper import WhisperModel
# from faster_whisper.vad import VadOptions, get_speech_timestamps
# import numpy as np
# import sounddevice as sd


# class WakeEngine:
#     def __init__(
#         self,
#         model_name="base",
#         device="cpu",
#         compute_type="int8",
#         samplerate=16000,
#         blocksize=16000,
#         channels=1,
#         wake_words=None,
#         hotwords=None
#     ):
#         self.samplerate = samplerate
#         self.blocksize = blocksize
#         self.channels = channels

#         # 唤醒词、热词配置
#         self.wake_words = wake_words or ["你好", "hello 困困", "hi 困困"]
#         self.hotwords = hotwords or ["你好困困", "Hello 困困", "hi 困困", "困困", "你好"]

#         # 模型加载
#         self.model = WhisperModel(model_name, device=device, compute_type=compute_type)

#         # VAD配置
#         self.vad_options = VadOptions(
#             threshold=0.6,
#             min_speech_duration_ms=300,
#             min_silence_duration_ms=100
#         )

#     def _process_audio_chunk(self, audio_chunk: bytes):
#         """VAD处理，返回语音片段"""
#         audio = np.frombuffer(audio_chunk, dtype=np.float32)
#         speech_chunks = get_speech_timestamps(audio, self.vad_options)

#         segments = []
#         for chunk in speech_chunks:
#             speech_segment = audio[chunk["start"]:chunk["end"]]
#             segments.append(speech_segment)

#         return segments

#     def detect_wake_word(self, speech_segment: np.ndarray):
#         """识别 + 唤醒检测"""
#         segments, _ = self.model.transcribe(
#             speech_segment,
#             language="zh",
#             beam_size=1,
#             vad_filter=False,
#             initial_prompt=self.hotwords
#         )

#         transcription = " ".join([s.text.strip().lower() for s in segments])

#         # 检查是否包含任何唤醒词
#         for word in self.wake_words:
#             if word in transcription:
#                 return True, transcription

#         return False, transcription

#     def start(self):

#         print("唤醒监听启动中...")

#         with sd.Inputself.stream(
#             samplerate=self.samplerate,
#             channels=self.channels,
#             blocksize=self.blocksize,
#             dtype="float32"
#         ) as self.stream:

#             while True:
#                 audio_chunk, _ = self.stream.read(self.blocksize)
#                 audio_chunk = audio_chunk.flatten().tobytes()

#                 speech_segments = self._process_audio_chunk(audio_chunk)

#                 for seg in speech_segments:
#                     detected, text = self.detect_wake_word(seg)

#                     if detected:
#                         print(f"唤醒成功: {text}")
#                         return True

# # from faster_whisper import WhisperModel
# # from faster_whisper.vad import VadOptions, get_speech_timestamps
# # import numpy as np
# # import sounddevice as sd
 
# # # 加载模型（使用INT8量化节省内存）
# # model = WhisperModel("base", device="cpu", compute_type="int8")
 
# # # 配置VAD参数
# # vad_options = VadOptions(
# #     threshold=0.6,
# #     min_speech_duration_ms=300,
# #     min_silence_duration_ms=100
# # )
 
# # def process_self.audio_self.stream(self.audio_self.stream):
# #     """处理实时音频流，返回语音片段"""
# #     for audio_chunk in self.audio_self.stream:
# #         # 将音频转换为numpy数组（16kHz单声道）
# #         audio = np.frombuffer(audio_chunk, dtype=np.float32)
        
# #         # 使用VAD检测语音片段
# #         speech_chunks = get_speech_timestamps(audio, vad_options)
        
# #         for chunk in speech_chunks:
# #             # 提取语音片段
# #             speech_segment = audio[chunk["start"]:chunk["end"]]
# #             yield speech_segment


# # def detect_wake_word(speech_segment, model, wake_words=["你好"]):
# #     """检测语音片段中是否包含唤醒词"""
# #     segments, _ = model.transcribe(
# #         speech_segment,
# #         language="zh",
# #         beam_size=1,  # 快速模式，牺牲少量准确率换取速度
# #         vad_filter=False,  # 已提前通过VAD处理
# #         initial_prompt="你好困困，Hello 困困，hi 困困，困困"
# #     )
    
# #     transcription = " ".join([s.text.strip().lower() for s in segments])
    
# #     # 检查是否包含任何唤醒词
# #     for word in wake_words:
# #         if word in transcription:
# #             return True, transcription
# #     return False, transcription

# # def main():
# #     samplerate = 16000  # Whisper推荐16kHz
# #     blocksize = 16000    # 每次读取1秒音频
# #     channels = 1         # 单声道
# #     wake_words=["你好困困","Hello 困困","hi 困困"]

# #     print("开始监听唤醒词...")

# #     # 使用sounddevice实时读取麦克风
# #     with sd.Inputself.stream(samplerate=samplerate, channels=channels, blocksize=blocksize, dtype='float32') as self.stream:
# #         while True:
# #             audio_chunk, _ = self.stream.read(blocksize)
# #             audio_chunk = audio_chunk.flatten().tobytes()  # 转为bytes
# #             for speech_segment in process_self.audio_self.stream([audio_chunk]):
# #                 detected, text = detect_wake_word(speech_segment, model, wake_words)
# #                 if detected:
# #                     print(f"检测到唤醒词！内容: {text}")

# # if __name__ == "__main__":
# #     main()
