import time
import serial

ser = serial.Serial( port='/dev/ttyS4', baudrate=9600, timeout=1 )

def send(cmd):
    ser.write((cmd + "\r\n").encode())
    time.sleep(0.2)
    data = ser.read_all()

    if not data:
        return None

    # 1. bytes → str
    text = data.decode(errors='ignore')

    # 2. 按行拆
    for line in text.splitlines():
        line = line.strip()
        # 3. 找 "+XXX=值"
        if line.startswith("+") and "=" in line:
            value = line.split("=")[1]
            try:
                return float(value)
            except ValueError:
                return value

    return None


while True:
    co2 = send("AT+CO2")
    temp = send("AT+T")
    hum = send("AT+H")

    print(f"CO2: {co2} ppm")
    print(f"温度: {temp} °C")
    print(f"湿度: {hum} %")

    time.sleep(1)
