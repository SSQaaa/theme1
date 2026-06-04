import serial
from WakeEngine import WakeEngine
import time
import subprocess


ser_zhuan = serial.Serial(
    port="/dev/ttyS6",      # 转盘
    baudrate=115200,
    timeout=0.1
)
ser_mu = serial.Serial(
    port="/dev/ttyS7",      # 木板
    baudrate=9600,
    timeout=0.1
)

def control_int():
    # 木板
    ser_mu.write(b'\x61')  # 失能
    ser_mu.flush()
    time.sleep(0.5)
    ser_mu.write(b'\x07')  # 定义为0度
    ser_mu.flush()
    time.sleep(0.5)
    ser_mu.write(b'\x60')  # 使能
    ser_mu.flush()
    time.sleep(0.5)

    # 转盘
    ser_zhuan.write(b'\x61')  # 失能
    ser_zhuan.flush()
    time.sleep(0.5)
    ser_zhuan.write(b'\x07')  # 定义为0度
    ser_zhuan.flush()
    time.sleep(0.5)
    ser_zhuan.write(b'\x60')  # 使能
    ser_zhuan.flush()
    time.sleep(0.5)

def text_to_keyword(text):
    if "耳塞" in text:
        return "ersai"
    elif "眼罩" in text:
        return "yanzhao"
    elif "加湿器" in text:
        return "jiashiqi"
    elif "开灯" in text or "打开灯" in text:
        return "light_on"
    elif "关灯" in text or "关闭灯" in text:
        return "light_off"
    elif "调高亮度" in text or "亮一点" in text:
        return "light_up"
    elif "调低亮度" in text or "暗一点" in text:
        return "light_down"
    # elif "你回去吧" in text:
    #     return "muban_off"

    return None

def control(keywords, brightness, safe_play_wav):
    if keywords == "muban":
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        ser_mu.write(b'\x03')  # 木板转动90度
        ser_mu.flush()
        safe_play_wav("muban.wav")
        return True
    
    # if keywords == "muban_off":
    #     # print("KUNKUN WOKE UP!", flush=True)
    #     time.sleep(0.5) 
    #     ser_mu.write(b'\x01')  # 木板转动90度
    #     ser_mu.flush()
    #     safe_play_wav("muban_off.wav")
    #     return True

    elif keywords == "light_up":
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        from HA import set_brightness
        brightness = min(100, brightness + 10)
        set_brightness(brightness)
        safe_play_wav("light_up.wav")
        return True

    elif keywords == "light_down":
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        from HA import set_brightness
        brightness = max(0, brightness - 10)
        set_brightness(brightness)
        safe_play_wav("light_down.wav")
        return True

    elif keywords == "light_on":
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        from HA import turn_on
        turn_on()
        safe_play_wav("light_on.wav")
        return True

    elif keywords == "light_off":
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        from HA import turn_off
        turn_off()
        safe_play_wav("light_off.wav")
        return True

    elif keywords == "ersai":
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        ser_zhuan.write(b'\x02')  # 转盘转到耳塞
        ser_zhuan.flush()
        safe_play_wav("ersai.wav")
        return True

    elif keywords == "yanzhao":
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        ser_zhuan.write(b'\x03')  # 转盘转到眼罩
        ser_zhuan.flush()
        safe_play_wav("yanzhao.wav")
        return True

    elif keywords == "jiashiqi":
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        ser_zhuan.write(b'\x04')  # 转盘转到加湿器
        ser_zhuan.flush()
        safe_play_wav("jiashiqi.wav")
        return True
    return False