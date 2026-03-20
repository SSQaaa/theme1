
import time
import serial
import threading
from typing import Optional, Dict, Any
from dataclasses import dataclass
import platform

@dataclass
class PM25Data:
    pm25: Optional[float] = None
    timestamp: float = 0.0
    connected: bool = False
    error_message: str = ""

class PM25SensorReader:
    """Thread-safe PM2.5 sensor reader for serial communication."""

    def __init__(self, port: Optional[str] = None, baudrate: int = 9600):
        if port is None:
            port = self._get_default_port()

        self.port = port
        self.baudrate = baudrate
        self.timeout = 1
        self.ser: Optional[serial.Serial] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        self.data = PM25Data()

    @staticmethod
    def _get_default_port() -> str:
        if platform.system() == "Linux":
            return "/dev/ttyS0"
        return "COM4"

    def _parse_pm25(self, raw: bytes) -> Optional[float]:
        if not raw:
            return None
        idx = raw.find(b"\xA5")
        if idx < 0 or len(raw) < idx + 3:
            return None
        datah = raw[idx + 1]
        datal = raw[idx + 2]
        return float(datah * 128 + datal)

    def _read_loop(self):
        while self.running:
            try:
                if self.ser is None or not self.ser.is_open:
                    self.ser = serial.Serial(
                        port=self.port,
                        baudrate=self.baudrate,
                        timeout=self.timeout
                    )
                    print(f"[PM25] Connected to {self.port}")

                raw = self.ser.read_all()
                pm25 = self._parse_pm25(raw)

                with self.lock:
                    if pm25 is not None:
                        self.data.pm25 = pm25
                        self.data.timestamp = time.time()
                        self.data.connected = True
                        self.data.error_message = ""
                    else:
                        self.data.connected = True

                time.sleep(1)


            except serial.SerialException as e:
                with self.lock:
                    self.data.connected = False
                    if "Permission denied" in str(e):
                        self.data.error_message = "PM2.5 permission denied"
                    else:
                        self.data.error_message = "PM2.5 disconnected"
                print(f"[PM25] Serial error: {e}")
                time.sleep(5)
            except Exception as e:
                with self.lock:
                    self.data.connected = False
                    self.data.error_message = "PM2.5 read failed"
                print(f"[PM25] Unexpected error: {e}")
                time.sleep(5)

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        print(f"[PM25] Started reader on {self.port}")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.ser:
            self.ser.close()
        print("[PM25] Stopped reader")

    def get_data(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "pm25": self.data.pm25,
                "timestamp": self.data.timestamp,
                "connected": self.data.connected,
                "error_message": self.data.error_message,
            }
