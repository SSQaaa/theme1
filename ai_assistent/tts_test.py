import asyncio
import edge_tts
import subprocess
import os

MP3_PATH = "muban_off.mp3"
WAV_PATH = "muban_off.wav"

async def tts(text):

    communicate = edge_tts.Communicate(
        text=text,
        voice="zh-CN-XiaoxiaoNeural",
    )

    await communicate.save(MP3_PATH)


    # MP3 -> WAV（强制成声卡友好格式）
    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", MP3_PATH,
        "-ar", "16000",        # 16kHz
        "-ac", "1",            # mono
        "-sample_fmt", "s16",  # 16bit
        WAV_PATH
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    asyncio.run(tts("我已做好陪伴您入睡的准备了，祝您做个好梦！"))
