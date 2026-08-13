from periphery import GPIO

gpio = GPIO("/dev/gpiochip1", 9, "out")

gpio.write(False) # 输出低电平
# gpio.write(True) #输出高电平

gpio.close()