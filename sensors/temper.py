import subprocess
import re

proc = subprocess.Popen(
    ["./temper"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,   # 行缓冲
    universal_newlines=True
)

try:
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.strip()
        match = re.search(r'温度: (\d+)°C, 湿度: (\d+)%', line)
        if match:
            temp = int(match.group(1))
            hum = int(match.group(2))
            print(f"温度={temp}°C  湿度={hum}%")
except KeyboardInterrupt:
    proc.terminate()
