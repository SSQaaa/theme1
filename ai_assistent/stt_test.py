import sounddevice as sd
import numpy as np
import wave
from faster_whisper import WhisperModel

FS = 16000       # 采样率
DURATION = 5     # 秒
WAV_PATH = "temp.wav"

# =========================
# 1. 录音 5 秒
# =========================
print("开始录音 5 秒...")
audio = sd.rec(int(DURATION * FS), samplerate=FS, channels=1, dtype='float32')
sd.wait()  # 等待录音完成
print("录音完成")

# 保存为 wav
audio_int16 = (audio * 32767).astype(np.int16)  # 转成 int16
with wave.open(WAV_PATH, 'w') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)  # int16 = 2 bytes
    wf.setframerate(FS)
    wf.writeframes(audio_int16.tobytes())

# =========================
# 2. Faster Whisper 转录
# =========================
model_size = "base"
model = WhisperModel(
    model_size,
    device="cpu",
    compute_type="int8"  # INT8 加速
)

segments, info = model.transcribe(WAV_PATH, language="zh")
print("检测语言:", info.language)

print("识别结果：")
for segment in segments:
    print(segment.text)
