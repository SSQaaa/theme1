import serial
from WakeEngine import WakeEngine
import time
import subprocess
from umbrella import umbrella_control


ser_zhuan = serial.Serial(
    port="/dev/ttyS6",      # 转盘
    baudrate=115200,
    timeout=0.1,
    write_timeout=1,
)
ser_mu = serial.Serial(
    port="/dev/ttyS7",      # 木板
    baudrate=115200,
    timeout=0.1,
    write_timeout=1,
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
    # elif "加湿器" in text:
    #     return "jiashiqi"
    elif "有点干" in text:
        return "youdiangan"
    elif "开灯" in text or "打开灯" in text:
        return "light_on"
    elif "关灯" in text or "关闭灯" in text:
        return "light_off"
    elif "调高亮度" in text or "亮一点" in text:
        return "light_up"
    elif "调低亮度" in text or "暗一点" in text:
        return "light_down"
    elif "你回去吧" in text:
        return "muban_off"
    elif "我要睡觉了" in text:
        return "sleep"

    return None

def control(keywords, brightness, safe_play_wav):
    if keywords == "sleep":  # 我要睡觉了，雨伞转过来
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        umbrella_control("open")  # 打开伞
        time.sleep(3)
        ser_mu.write(b'\x03')  # 顺时针转动120度
        ser_mu.flush()
        safe_play_wav("WAV/muban.wav")
        return True
    
    elif keywords == "xianshiping":  # 显示屏
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        ser_mu.write(b'\x03')  # 顺时针转动120度
        ser_mu.flush()
        return True
    
    elif keywords == "yssd":   # 雨伞上电
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        ser_mu.write(b'\x07')  # 定义当前为绝对零度
        ser_mu.flush()
        time.sleep(0.5)
        ser_mu.write(b'\x60')  # 使能
        ser_mu.flush()
        safe_play_wav("WAV/welcome_VITS.wav")
        return True
    
    elif keywords == "ysxd":   # 雨伞下电
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        ser_mu.write(b'\x61')  # 失能
        ser_mu.flush()
        safe_play_wav("WAV/welcome_VITS.wav")
        return True

    elif keywords == "zpsd":   # 转盘上电
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        ser_zhuan.write(b'\x07')  # 定义当前为绝对零度
        ser_zhuan.flush()
        time.sleep(0.5)
        ser_zhuan.write(b'\x60')  # 使能
        ser_zhuan.flush()
        safe_play_wav("WAV/welcome_VITS.wav")
        return True
    
    elif keywords == "zpxd":   # 转盘下电
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        ser_zhuan.write(b'\x61')  # 失能
        ser_zhuan.flush()
        safe_play_wav("WAV/welcome_VITS.wav")
        return True
        
    elif keywords == "peoplewake":  # 收雨伞
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5)
        umbrella_control("close")  # 关闭伞
        time.sleep(2)
        safe_play_wav("WAV/welcome_VITS.wav")
        return True

    elif keywords == "ssz":   # 顺时针
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        ser_zhuan.write(b'\x03')  
        ser_zhuan.flush()
        safe_play_wav("WAV/welcome_VITS.wav")
        return True
    
    elif keywords == "nsz":   # 逆时针
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        ser_zhuan.write(b'\x02')  
        ser_zhuan.flush()
        safe_play_wav("WAV/welcome_VITS.wav")
        return True  

    elif keywords == "light_up":   # 灯亮度+++++
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        from HA import set_brightness
        brightness = min(100, brightness + 10)
        set_brightness(brightness)
        safe_play_wav("WAV/light_up.wav")
        return True

    elif keywords == "light_down":  # 亮度------
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        from HA import set_brightness
        brightness = max(0, brightness - 10)
        set_brightness(brightness)
        safe_play_wav("WAV/light_down.wav")
        return True

    elif keywords == "light_on":   # 开灯
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        from HA import turn_on
        turn_on()
        safe_play_wav("WAV/light_on.wav")
        return True

    elif keywords == "light_off":    # 关灯
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        from HA import turn_off
        turn_off()
        safe_play_wav("WAV/light_off.wav")
        return True

    elif keywords == "ersai":
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        ser_zhuan.write(b'\x02')  # 转盘转到耳塞
        ser_zhuan.flush()
        safe_play_wav("WAV/ersai.wav")
        return True

    elif keywords == "yanzhao":
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        ser_zhuan.write(b'\x03')  # 转盘转到眼罩
        ser_zhuan.flush()
        safe_play_wav("WAV/yanzhao.wav")
        return True

    elif keywords == "youdiangan":
        # print("KUNKUN WOKE UP!", flush=True)
        time.sleep(0.5) 
        ser_zhuan.write(b'\x04')  # 转盘转到加湿器
        ser_zhuan.flush()
        safe_play_wav("WAV/jiashiqi.wav")
        return True
    
    return False
