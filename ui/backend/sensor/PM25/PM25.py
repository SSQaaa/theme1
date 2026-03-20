import serial
import time
import re

ser = serial.Serial(
    port='/dev/ttyS0',   # 你实际的串口
    baudrate=9600,
    timeout=1
)

while True:
    Data_raw = ser.read_all()
    pm25 = 0

    if Data_raw and Data_raw[0] == 0xa5:
        datah = Data_raw[1] # 数据的高七位
        datal = Data_raw[2] # 数据的低七位
        pm25 = datah * 128 + datal
        print("PM2.5浓度为: {} μg/m³".format(pm25))

    time.sleep(1)
