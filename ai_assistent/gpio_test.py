# 在运行程序前要先拉高 sudo gpio -g mode 38 up
from periphery import GPIO
import time

# 根据具体板卡的LED灯和按键连接修改使用的Chip和Line
# 这里以LubanCat 2为例，使用GPIO0_B0接LED，GPIO0_C2接按键
# LED_CHIP = "/dev/gpiochip0"
# LED_LINE_OFFSET = 8

BUTTON_CHIP = "/dev/gpiochip1"
BUTTON_LINE_OFFSET = 6

PULL_UP_HIGH = 1
PULL_UP_LOW = 0

# led = GPIO(LED_CHIP, LED_LINE_OFFSET, "out")
button = GPIO(BUTTON_CHIP, BUTTON_LINE_OFFSET, "in")
last_state = PULL_UP_HIGH

try:
    while True:
        current_state = button.read()
        time.sleep(0.02) # 消抖
        current_state = button.read()
        if current_state != last_state:
            if current_state == PULL_UP_LOW:
                print(1)  # 按下按键
            else:
                print(0)  # 松开按键
            last_state = current_state

    # 一直按下的时候打印的,sleep0.05s
        if current_state == PULL_UP_LOW:
            print(1)
            time.sleep(0.05)
finally:
    button.close()  # 释放GPIO资源
