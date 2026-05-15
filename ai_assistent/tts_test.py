import asyncio
import edge_tts
import subprocess
import os

MP3_PATH = "jiashiqi.mp3"
WAV_PATH = "jiashiqi.wav"

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
    asyncio.run(tts("好的，已为您开启加湿器，希望干燥的环境能快点变得舒适！"))
