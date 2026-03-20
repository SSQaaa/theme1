import requests
import time
import asyncio
import os
import edge_tts
import subprocess
from WakeEngine import WakeEngine
from myrecorder import Recorder
import threading
from Sherpa_onnx_stt import SpeechToText

# INITIALIZE
FS = 16000
ARECORD_DEVICE = "plughw:rockchipes8388,0"   # 我的录音卡
MP3_PATH = "output.mp3"
WAV_PATH = "output.wav"
RKLLM_URL = "http://127.0.0.1:8080/rkllm_chat"
ASSISTANT_EVENT_URL = os.getenv("ASSISTANT_EVENT_URL", "http://127.0.0.1:8000/api/assistant/event")
DB_THRESHOLD = -30   # 分贝阈值，float32 范围 [-1,1]
FRAME_DURATION = 0.5  # 每帧 0.5 秒



# ============================
# 0. 监听唤醒 + 分贝监听
# ============================
 
wake_engine = WakeEngine()

def send_assistant_event(event_type, text=None):
    if not ASSISTANT_EVENT_URL:
        return
    payload = {"type": event_type}
    if text is not None:
        payload["text"] = text
    try:
        requests.post(ASSISTANT_EVENT_URL, json=payload, timeout=0.5)
    except Exception:
        pass

def wake_listen_loop():
    global wake_state

    while True:
        keywords = wake_engine.detect_keywords()  # 阻塞也没关系，线程单独跑
        print("keywords detected:", keywords, flush=True)
        if keywords == "wake" and not wake_state:
            wake_cmd = ["aplay", "-D", "plughw:rockchipes8388,0", "wake.wav"]
            # print("KUNKUN WOKE UP!", flush=True)
            wake_state = True
            send_assistant_event("wake")
            time.sleep(0.5) 
            subprocess.run(wake_cmd)
        elif keywords == "exit" and wake_state:
            exit_cmd = ["aplay", "-D", "plughw:rockchipes8388,0", "exit.wav"]
            # print("KUNKUN EXITED!", flush=True)
            wake_state = False
            recorder.stop()
            send_assistant_event("close")
            time.sleep(0.5) 
            subprocess.run(exit_cmd)
        

        time.sleep(0.02)
      
# ============================
# 1. 录音 → 保存 WAV
# ============================

recorder = Recorder(
    samplerate=FS,
    threshold_db=DB_THRESHOLD,
    silence_timeout=1.2,
    min_record_time=1.0
)

# ============================
# 2. Whisper → 文字
# ============================

stt = SpeechToText()

# ============================
# 3. 调用 RKLLM Server
# ============================

def ask_llm(user_text):
    payload = {
        "model": "qwen",     
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
# # ============================
# # 6. 播放 指令WAV
# def play_target_audio(wav_path):
#     cmd = ["aplay", "-D", "plughw:rockchipes8388,0", wav_path]
#     print("播放音频...")
#     subprocess.run(cmd)
# ============================
# ============================
# MAIN
# ============================
if __name__ == "__main__":
    # 开机欢迎
    cmd = ["aplay", "-D", "plughw:rockchipes8388,0", "welcome.wav"]
    print("说“你好，困困”来唤醒我吧！")
    subprocess.run(cmd)
    # wake_engine.start()

    wake_state = False
    record_duration = 0

    threading.Thread(target=wake_listen_loop, daemon=True).start()

    try:
        while True:
            # print("Wake State:", wake_state, flush=True)
            if wake_state == True:
                recorder.reset()
                # print("被唤醒了！准备录音...")
                time.sleep(3)  # 等待2秒，避免录到刚唤醒时的声音

                
                audio_path = recorder.listen_and_record()

                if audio_path is None:
                    continue
                
                recorder.stop()

                if wake_state == False:
                    continue

                text = stt.transcribe_file(audio_path)
                # 如果检测为空则跳回主循环继续等待下一次录音。这避免将空输入送入 LLM 或播放空白 TTS。
                if text.strip() == "":
                    print("NO INPUT DETECTED, SKIPPING...")
                    continue

                if "质量好差" in text:
                    llm_reply = "好的，已帮您开启空气净化器"
                    print("KunKun says:", "好的，已帮您开启空气净化器")

                else:
                    send_assistant_event("thinking")
                    llm_reply = ask_llm(text)
                    print("KunKun says:", llm_reply)

                send_assistant_event("reply", text=llm_reply)
                Kun_reply = tts_edge(llm_reply)
                play_audio(Kun_reply)
                send_assistant_event("reply_done")

                time.sleep(0.02)

    except KeyboardInterrupt:
        pass
    finally:
        print("退出程序。") 
