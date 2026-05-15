import requests
import time
import asyncio
import os
import subprocess
from WakeEngine import WakeEngine
from myrecorder import Recorder
import threading
from Sherpa_onnx_stt import SpeechToText
import re
from streaming_tts import StreamingEdgeTTS

# INITIALIZE
FS = 16000
MP3_PATH = "output.mp3"
WAV_PATH = "output.wav"
RKLLM_URL = "http://127.0.0.1:8080/rkllm_chat"
ASSISTANT_EVENT_URL = os.getenv("ASSISTANT_EVENT_URL", "http://127.0.0.1:8000/api/assistant/event")
DB_THRESHOLD = -30   # 分贝阈值，float32 范围 [-1,1]
FRAME_DURATION = 0.5  # 每帧 0.5 秒

# detect ALSA devices (input/output) at runtime instead of hardcoding
def find_alsa_device(kind: str, prefer: tuple[str, ...] = ()): 
    """Find an ALSA card/device from `arecord -l` (input) or `aplay -l` (output).

    If `prefer` keywords are provided, it will try to match those keywords (case-insensitive)
    in each device block first; otherwise it falls back to the first device.

    Returns string like 'plughw:2,0' or None if not found.
    """
    cmd = ["arecord", "-l"] if kind == "input" else ["aplay", "-l"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        out = proc.stdout

        # Split output into device blocks beginning with "card X:"
        blocks = re.split(r"(?=^card\s+\d+:)", out, flags=re.MULTILINE)

        def pick_from_blocks(block_list):
            for b in block_list:
                m = re.search(r"^card\s+(\d+):.*?device\s+(\d+):", b, flags=re.MULTILINE)
                if m:
                    return f"plughw:{m.group(1)},{m.group(2)}"
            return None

        # 1) preferred match (try keywords in order, first match wins)
        if prefer:
            for kw in prefer:
                kw_low = kw.lower()
                matched_blocks = [b for b in blocks if kw_low in b.lower()]
                dev = pick_from_blocks(matched_blocks)
                if dev:
                    return dev

        # 2) fallback: first device
        return pick_from_blocks(blocks)

    except Exception:
        return None

# discover devices on each run (sensible defaults)
# Allow forcing devices via environment variables.
# Examples:
#   ARECORD_DEVICE=plughw:3,0 APLAY_DEVICE=plughw:3,0 python main.py
#   PREFER_ARECORD_CARD=3 python main.py
ARECORD_DEVICE = os.getenv("ARECORD_DEVICE") or None
APLAY_DEVICE = os.getenv("APLAY_DEVICE") or None

# Optional: force by card number (uses the first device index found for that card)
PREFER_ARECORD_CARD = os.getenv("PREFER_ARECORD_CARD")
PREFER_APLAY_CARD = os.getenv("PREFER_APLAY_CARD")

# try to detect input/output devices; fall back gracefully
if not ARECORD_DEVICE:
    if PREFER_ARECORD_CARD:
        m = re.search(rf"^card\s+({re.escape(PREFER_ARECORD_CARD)}):.*?device\s+(\d+):", subprocess.run(["arecord", "-l"], capture_output=True, text=True).stdout, flags=re.MULTILINE)
        if m:
            ARECORD_DEVICE = f"plughw:{m.group(1)},{m.group(2)}"

if not APLAY_DEVICE:
    if PREFER_APLAY_CARD:
        m = re.search(rf"^card\s+({re.escape(PREFER_APLAY_CARD)}):.*?device\s+(\d+):", subprocess.run(["aplay", "-l"], capture_output=True, text=True).stdout, flags=re.MULTILINE)
        if m:
            APLAY_DEVICE = f"plughw:{m.group(1)},{m.group(2)}"

if not ARECORD_DEVICE:
    _detect_in = find_alsa_device('input', prefer=(
        # Prefer external USB microphones first
        'uacdemov10', 'uacdemo', 'usb audio',
        # Then fall back to onboard codecs
        'es8323', 'es8388', 'dailink-multicodecs', 'rockchipes8388'
    ))
    ARECORD_DEVICE = _detect_in

if not APLAY_DEVICE:
    _detect_out = find_alsa_device('output', prefer=(
        # Prefer external USB audio first
        'uacdemov10', 'uacdemo', 'usb audio',
        # Then fall back to onboard codecs
        'es8323', 'es8388', 'dailink-multicodecs', 'rockchipes8388'
    ))
    APLAY_DEVICE = _detect_out or ARECORD_DEVICE

print(f"Detected input device: {ARECORD_DEVICE}")
print(f"Detected output device: {APLAY_DEVICE}")

# helper to build aplay command with optional device
def aplay_cmd_for(wav_path: str):
    cmd = ["aplay"]
    if APLAY_DEVICE:
        cmd += ["-D", APLAY_DEVICE]
    cmd.append(wav_path)
    return cmd

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
            wake_cmd = aplay_cmd_for("wake.wav")
            # print("KUNKUN WOKE UP!", flush=True)
            wake_state = True
            send_assistant_event("wake")
            time.sleep(0.5) 
            subprocess.run(wake_cmd)
        elif keywords == "exit" and wake_state:
            exit_cmd = aplay_cmd_for("exit.wav")
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
    min_record_time=1.0,
    device=ARECORD_DEVICE
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

# init streaming TTS (overlap generation & playback)
stream_tts = StreamingEdgeTTS(aplay_device=APLAY_DEVICE)

# ============================
# 5. 播放 WAV
# ============================
def play_audio(wav_path):
    cmd = aplay_cmd_for(wav_path)
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
    cmd = aplay_cmd_for("welcome.wav")
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
                stream_tts.speak(llm_reply)
                send_assistant_event("reply_done")

                time.sleep(0.02)

    except KeyboardInterrupt:
        pass
    finally:
        print("退出程序。")
