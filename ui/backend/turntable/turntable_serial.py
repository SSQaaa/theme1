"""转盘串口通信模块
用于向 STM32C8T6 单片机发送转盘扇区控制命令
"""
import serial
import threading
import logging
from typing import Optional
import platform

# ==================== 串口配置（可修改） ====================
# 串口设备路径
SERIAL_PORT = "/dev/ttyS3"  # 香橙派常用串口，也可能是 /dev/ttyS1 或 /dev/ttyUSB0

# 串口参数
BAUD_RATE = 115200            # 波特率：9600, 115200 等
DATA_BITS = serial.EIGHTBITS  # 数据位：8位
STOP_BITS = serial.STOPBITS_ONE  # 停止位：1位
PARITY = serial.PARITY_NONE   # 校验位：无校验
TIMEOUT = 1.0                 # 超时时间（秒）

# 数据格式配置
DATA_FORMAT = "BINARY"         # 数据格式："ASCII" 或 "BINARY"
LINE_ENDING = "\r\n"          # ASCII模式的行结束符
# =============================================================

logger = logging.getLogger(__name__)


class TurntableSerial:
    """转盘串口通信类

    负责通过串口向 STM32 发送转盘扇区控制命令。
    支持 ASCII 和 BINARY 两种数据格式。
    """

    def __init__(self,
                 port: Optional[str] = None,
                 baudrate: int = BAUD_RATE,
                 timeout: float = TIMEOUT):
        """初始化串口连接

        Args:
            port: 串口设备路径，默认使用全局配置
            baudrate: 波特率，默认使用全局配置
            timeout: 超时时间（秒）

        Raises:
            serial.SerialException: 串口打开失败
        """
        self.port = port or SERIAL_PORT
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn: Optional[serial.Serial] = None
        self.lock = threading.Lock()  # 线程安全锁
        self.is_connected = False

        # 尝试打开串口
        self._connect()

    def _connect(self) -> None:
        """建立串口连接"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=DATA_BITS,
                stopbits=STOP_BITS,
                parity=PARITY,
                timeout=self.timeout
            )
            self.is_connected = True
            logger.info(f"转盘串口连接成功: {self.port} @ {self.baudrate}bps")
        except serial.SerialException as e:
            self.is_connected = False
            logger.error(f"转盘串口连接失败: {e}")
            raise

    def send_sector(self, sector: int) -> bool:
        """发送扇区编号到 STM32

        Args:
            sector: 扇区编号（1-6）

        Returns:
            bool: 发送成功返回 True，失败返回 False
        """
        if not self.is_connected or not self.serial_conn:
            logger.error("串口未连接，无法发送数据")
            return False

        if not (1 <= sector <= 6):
            logger.error(f"无效的扇区编号: {sector}，必须在 1-6 之间")
            return False

        try:
            with self.lock:  # 线程安全
                if DATA_FORMAT.upper() == "ASCII":
                    # ASCII 格式：发送纯数字字符 "<N>\r\n"
                    message = f"{sector}{LINE_ENDING}"
                    data = message.encode('utf-8')
                    logger.debug(f"发送 ASCII 数据: {repr(message)}")
                else:
                    # BINARY 格式：发送单字节
                    data = bytes([sector])
                    logger.debug(f"发送 BINARY 数据: {data.hex()}")

                self.serial_conn.write(data)
                self.serial_conn.flush()  # 确保数据立即发送

                logger.info(f"成功发送扇区 {sector} 到转盘")
                return True

        except serial.SerialException as e:
            logger.error(f"串口发送失败: {e}")
            return False
        except Exception as e:
            logger.error(f"发送数据时发生错误: {e}")
            return False

    def close(self) -> None:
        """关闭串口连接"""
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
                self.is_connected = False
                logger.info("转盘串口已关闭")
            except Exception as e:
                logger.error(f"关闭串口时发生错误: {e}")

    def __del__(self):
        """析构函数，确保串口被正确关闭"""
        self.close()

    def is_ready(self) -> bool:
        """检查串口是否就绪

        Returns:
            bool: 串口连接且可用返回 True
        """
        return self.is_connected and self.serial_conn is not None and self.serial_conn.is_open
