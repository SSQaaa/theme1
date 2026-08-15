import numpy as np
import pyaudio
import sherpa_onnx

decoder = "./sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/decoder-epoch-12-avg-2-chunk-16-left-64.onnx"
encoder = "./sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/encoder-epoch-12-avg-2-chunk-16-left-64.onnx"
joiner  = "./sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/joiner-epoch-12-avg-2-chunk-16-left-64.onnx"
tokens  = "./sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/tokens.txt"
keywords_file = "./sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/test_wavs/test_keywords.txt"
KEYWORD_ACTIONS = {
    "你好困困": "wake",
    "再见困困": "exit",
    "困困拜拜": "exit",
    "帮我开灯": "light_on",
    "帮我关灯": "light_off",
    "我要睡觉了": "sleep",
    "耳塞": "ersai",
    "眼罩": "yanzhao",
    # "加湿器":"jiashiqi",
    "有点干":"youdiangan",
    "开灯": "light_on",
    "关灯": "light_off",
    "调高亮度": "light_up",
    "调低亮度": "light_down",
    "你回去吧": "muban_off",
    "显示屏" : "xianshiping",
    "雨伞上电" : "yssd",
    "雨伞下电" : "ysxd",
    "转盘上电" : "zpsd",
    "转盘下电" : "zpxd",
    "顺时针"  : "ssz",
    "逆时针" : "nsz",
    "我醒了"  : "peoplewake",
}
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
        self.p = None

        self.audio_stream = None

        print("self.kws engine inited.")

    def start(self):

        if self.audio_stream is not None:
            return

        self.p = pyaudio.PyAudio()

        self.audio_stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1600,
        )

        print("Microphone stream started.")

    def detect_keywords(self):
        try:
            if self.audio_stream is None:
                raise RuntimeError(
                    "WakeEngine.start() must be called first."
                )
            while True:
                audio_data = self.audio_stream.read(
                    1600,
                    exception_on_overflow=False
                )

                samples_int16 = np.frombuffer(
                    audio_data,
                    dtype=np.int16
                )

                samples_float32 = (
                    samples_int16.astype(np.float32) / 32768.0
                )

                self.stream.accept_waveform(
                    16000,
                    samples_float32
                )

                while self.kws.is_ready(self.stream):

                    self.kws.decode_stream(self.stream)

                    result = self.kws.get_result(self.stream)

                    action = KEYWORD_ACTIONS.get(result)

                    if action:
                        print(f"KWS DETECTED: {result} -> {action}")

                        self.kws.reset_stream(self.stream)

                        return action

        except KeyboardInterrupt:
            print("\n程序已停止（用户中断）")
            return False

    def close(self):

        if self.audio_stream is not None:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
            self.audio_stream = None

        if self.p is not None:
            self.p.terminate()
            self.p = None

        self.kws.reset_stream(self.stream)

