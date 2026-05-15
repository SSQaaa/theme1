import serial
import time



ser_32_0 = serial.Serial('/dev/ttyS6', 115200, timeout=0.1) 

def send_32_0(data_byte):
    packet_0 = bytes([data_byte])
    ser_32_0.write(packet_0)
    print(f"[S0] Sent: {packet_0.hex()}")



if __name__ == '__main__':

    ser_32_0.write(bytes([0x01]))


    time.sleep(0.1) 

# import serial, time

# ser = serial.Serial(
#     "/dev/ttyS3",
#     baudrate=115200,
#     bytesize=serial.EIGHTBITS,
#     parity=serial.PARITY_NONE,
#     stopbits=serial.STOPBITS_ONE,
#     timeout=0.5,
#     xonxoff=False,
#     rtscts=False,
#     dsrdtr=False,
# )

# ser.reset_input_buffer()
# ser.reset_output_buffer()

# ser.write(b"\x01")
# ser.flush()

# time.sleep(0.2)
# print("sent 01")