import time
import serial
import threading
from typing import Optional, Dict, Any
from dataclasses import dataclass
import platform

@dataclass
class SensorData:
    co2: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    timestamp: float = 0.0
    connected: bool = False
    error_message: str = ""

class CO2SensorReader:
    """Thread-safe CO2 sensor reader for serial communication."""

    def __init__(self, port: Optional[str] = None, baudrate: int = 9600):
        # Auto-detect serial port based on platform
        if port is None:
            port = self._get_default_port()

        self.port = port
        self.baudrate = baudrate
        self.timeout = 1
        self.ser: Optional[serial.Serial] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        self.data = SensorData()

    @staticmethod
    def _get_default_port() -> str:
        """Auto-detect serial port based on platform."""
        if platform.system() == "Linux":
            return "/dev/ttyS4"
        else:
            # Windows fallback (for testing)
            return "COM3"

    def _send_command(self, cmd: str) -> Optional[float]:
        """Send AT command and parse response."""
        try:
            # 清空接收缓冲区，避免读取到之前命令的残留数据
            self.ser.reset_input_buffer()

            # 发送命令
            self.ser.write((cmd + "\r\n").encode())
            time.sleep(0.2)
            data = self.ser.read_all()

            if not data:
                return None

            text = data.decode(errors='ignore')
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("+") and "=" in line:
                    value = line.split("=")[1]
                    try:
                        return float(value)
                    except ValueError:
                        return None
            return None
        except Exception as e:
            print(f"[SENSOR] Command {cmd} failed: {e}")
            return None

    def _read_loop(self):
        """Background thread that continuously reads sensor data."""
        while self.running:
            try:
                # Try to open serial port if not connected
                if self.ser is None or not self.ser.is_open:
                    self.ser = serial.Serial(
                        port=self.port,
                        baudrate=self.baudrate,
                        timeout=self.timeout
                    )
                    print(f"[SENSOR] Connected to {self.port}")

                # Read sensor values
                co2 = self._send_command("AT+CO2")
                temp = self._send_command("AT+T")
                hum = self._send_command("AT+H")

                # Update shared data with lock
                with self.lock:
                    self.data.co2 = co2
                    self.data.temperature = temp
                    self.data.humidity = hum
                    self.data.timestamp = time.time()
                    self.data.connected = True
                    self.data.error_message = ""

                time.sleep(1)  # Read every 1 second

            except serial.SerialException as e:
                # Handle serial port errors (permissions, disconnection)
                with self.lock:
                    self.data.connected = False
                    if "Permission denied" in str(e):
                        self.data.error_message = "传感器权限错误"
                    else:
                        self.data.error_message = "传感器断开"
                print(f"[SENSOR] Serial error: {e}")
                time.sleep(5)  # Wait before retry

            except Exception as e:
                with self.lock:
                    self.data.connected = False
                    self.data.error_message = "传感器读取失败"
                print(f"[SENSOR] Unexpected error: {e}")
                time.sleep(5)

    def start(self):
        """Start background reading thread."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        print(f"[SENSOR] Started reader on {self.port}")

    def stop(self):
        """Stop background reading thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.ser:
            self.ser.close()
        print("[SENSOR] Stopped reader")

    def get_data(self) -> Dict[str, Any]:
        """Get latest sensor data (thread-safe)."""
        with self.lock:
            return {
                "co2": self.data.co2,
                "temperature": self.data.temperature,
                "humidity": self.data.humidity,
                "timestamp": self.data.timestamp,
                "connected": self.data.connected,
                "error_message": self.data.error_message
            }
