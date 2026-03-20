import requests
import subprocess
import json
import sounddevice as sd
import numpy as np
import wave
from faster_whisper import WhisperModel
import tempfile
import os
import queue
from periphery import GPIO
import time
import asyncio
import edge_tts
import subprocess
import os


FS = 16000
ARECORD_DEVICE = "plughw:rockchipes8388,0"   # 我的录音卡
whisper_model_size = "base"  # 小模型足够
MP3_PATH = "output.mp3"
WAV_PATH = "output.wav"
RKLLM_URL = "http://127.0.0.1:8080/rkllm_chat"


# ============================
# 0. GPIO INIT
# ============================

LED_CHIP = "/dev/gpiochip1"
LED_LINE_OFFSET = 4

BUTTON_CHIP = "/dev/gpiochip1"
BUTTON_LINE_OFFSET = 6

PULL_UP_HIGH = 1
PULL_UP_LOW = 0

led = GPIO(LED_CHIP, LED_LINE_OFFSET, "out") # 初始化为输出模式
led.write(False)  # 初始低电平，LED灭
button = GPIO(BUTTON_CHIP, BUTTON_LINE_OFFSET, "in")
last_state = PULL_UP_HIGH

# ============================
# 1. 录音 → 保存 WAV
# ============================
def record_wav():
    tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    print("请按住按键开始录音...")

    # 等待按下按键
    while button.read() == PULL_UP_HIGH:
        time.sleep(0.01)

    print("录音开始...")
    led.write(True)

    audio_buffer = []

    def callback(indata, frames, time_info, status):
        audio_buffer.append(indata.copy())

    # 打开录音流
    with sd.InputStream(samplerate=FS, channels=1, dtype='float32', callback=callback):
        # 按住循环
        while button.read() == PULL_UP_LOW:
            time.sleep(0.01)  # CPU 不空转

    led.write(False)
    print("录音结束")

    # 合并缓冲区
    audio_np = np.concatenate(audio_buffer, axis=0)

    # 转 int16 保存 WAV
    audio_int16 = (audio_np * 32767).astype(np.int16)
    with wave.open(tmp_wav.name, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(FS)
        wf.writeframes(audio_int16.tobytes())

    print("保存 WAV 文件:", tmp_wav.name)
    return tmp_wav.name


# ============================
# 2. Whisper → 文字
# ============================

model = WhisperModel(
    whisper_model_size,
    device="cpu",
    compute_type="int8"  # INT8 加速
    )

def speech_to_text(wav_path):
    print("Whisper 正在识别...")

    segments, info = model.transcribe(wav_path, language="zh")

    text = "".join([segment.text for segment in segments])

    print("识别结果:", text)

    return text


# ============================
# 3. 调用 RKLLM Server
# ============================

def ask_llm(user_text):
    payload = {
        "model": "qwen",      # 你的 rkllmserver 里实际模型名字
        "messages": [
            {"role": "user", "content": user_text}
        ]
    }

    print("发送至 RKLLM Server ...")
    resp = requests.post(RKLLM_URL, json=payload)
    resp_json = resp.json()

    answer = resp_json["choices"][0]["message"]["content"]
    # print("LLM 回复:", answer)
    return answer


# ============================
# 4. Edge TTS 合成语音
# ============================

def tts_edge(text: str) -> str:
    async def _run():
        communicate = edge_tts.Communicate(
            text=text,
            voice="zh-CN-XiaoxiaoNeural"
        )
        await communicate.save(MP3_PATH)

    asyncio.run(_run())

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i", MP3_PATH,
            "-ar", "16000",
            "-ac", "1",
            "-sample_fmt", "s16",
            WAV_PATH
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    return WAV_PATH

# ============================
# 5. 播放 WAV
# ============================
def play_audio(wav_path):
    cmd = ["aplay", "-D", "plughw:rockchipes8388,0", wav_path]
    print("播放音频...")
    subprocess.run(cmd)

# ============================
# 综合流程
# ============================
if __name__ == "__main__":
    # 开机欢迎
    cmd = ["aplay", "-D", "plughw:rockchipes8388,0", "welcome.wav"]
    print("Press the bottom to talk with Senbeier")
    subprocess.run(cmd)
    
    try:
        last_state = PULL_UP_HIGH

        while True:
            state = button.read()

            if state == PULL_UP_LOW and last_state == PULL_UP_HIGH:
                print("start recording...")
                # 按下按键，从高电平到低电平
                audio_path = record_wav()
                text = speech_to_text(audio_path)

                # 如果检测为空则跳回主循环继续等待下一次按键。这避免将空输入送入 LLM 或播放空白 TTS。
                if text.strip() == "":
                    print("NO INPUT DETECTED, SKIPPING...")
                    continue

                llm_reply = ask_llm(text)
                print("KunKun says:", llm_reply)

                Kun_reply = tts_edge(llm_reply)
                play_audio(Kun_reply)

            last_state = state
            time.sleep(0.02)

    except KeyboardInterrupt:
        pass
    finally:
        button.close()
        print("退出程序。")
