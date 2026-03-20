from DB_Monitor import AudioDBMonitor
import time

dbm = AudioDBMonitor()

while True:
    db = dbm.get_db_level()
    print(f"当前环境分贝: {db:.2f} dBFS")
    time.sleep(0.5)
