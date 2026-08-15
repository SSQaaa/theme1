from periphery import GPIO
import time

def umbrella_control(state):
    if state == "open":
        gpio_open = GPIO("/dev/gpiochip1", 8, "out")
        try:
            gpio_open.write(True)   # 输出高电平，触发开伞
            time.sleep(1)
            gpio_open.write(False)  # 拉低
        finally:
            gpio_open.close()  # 无论是否报错，释放

    elif state == "close":
        gpio_close = GPIO("/dev/gpiochip1", 9, "out")
        try:
            gpio_close.write(True)  # 输出高电平，触发关伞才吃饭成
            time.sleep(1)
            gpio_close.write(False) # 拉低
        finally:
            gpio_close.close()
    else:
        raise ValueError("Invalid state. Use 'open' or 'close'.")
umbrella_control("open")  # 调用函数打开伞