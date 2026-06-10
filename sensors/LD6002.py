import argparse
import glob
import math
import platform
import struct
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import serial


SOF_BYTE = 0x01
DEFAULT_BAUDRATE = 115200

TYPE_FIRMWARE_STATUS = 0xFFFF
TYPE_HUMAN_STATUS = 0x0F09
TYPE_HUMAN_POSITION = 0x0A04
TYPE_PHASE = 0x0A13
TYPE_BREATH_RATE = 0x0A14
TYPE_HEART_RATE = 0x0A15
TYPE_TARGET_RANGE = 0x0A16
TYPE_TRACKING_POSITION = 0x0A17


@dataclass
class TinyFrameMessage:
    frame_id: int
    data_type: int
    payload: bytes


@dataclass
class LD6002Data:
    is_human: Optional[bool] = None
    breath_rate: Optional[float] = None
    heart_rate: Optional[float] = None
    target_range_cm: Optional[float] = None
    range_valid: Optional[bool] = None
    phase: Dict[str, Optional[float]] = field(
        default_factory=lambda: {
            "total_phase": None,
            "breath_phase": None,
            "heart_phase": None,
        }
    )
    tracking_position: Dict[str, Optional[float]] = field(
        default_factory=lambda: {"x": None, "y": None, "z": None}
    )
    targets: List[Dict[str, Any]] = field(default_factory=list)
    firmware: Dict[str, Optional[int]] = field(
        default_factory=lambda: {
            "project": None,
            "major_version": None,
            "sub_version": None,
            "modified_version": None,
        }
    )
    last_type: Optional[int] = None
    last_raw: str = ""
    timestamp: float = 0.0
    connected: bool = False
    error_message: str = ""


class TinyFrameParser:
    """Parser for the LD6002 TinyFrame serial protocol."""

    def __init__(self, max_payload: int = 1024):
        self.max_payload = max_payload
        self._buffer = bytearray()

    @staticmethod
    def _checksum(data: bytes) -> int:
        value = 0
        for byte in data:
            value ^= byte
        return (~value) & 0xFF

    def feed(self, data: bytes) -> List[TinyFrameMessage]:
        messages: List[TinyFrameMessage] = []
        self._buffer.extend(data)

        while True:
            sof_index = self._buffer.find(bytes([SOF_BYTE]))
            if sof_index < 0:
                self._buffer.clear()
                break
            if sof_index > 0:
                del self._buffer[:sof_index]

            if len(self._buffer) < 8:
                break

            header_without_cksum = bytes(self._buffer[:7])
            header_cksum = self._buffer[7]
            if self._checksum(header_without_cksum) != header_cksum:
                del self._buffer[0]
                continue

            frame_id = int.from_bytes(self._buffer[1:3], byteorder="big")
            payload_len = int.from_bytes(self._buffer[3:5], byteorder="big")
            data_type = int.from_bytes(self._buffer[5:7], byteorder="big")

            if payload_len > self.max_payload:
                del self._buffer[0]
                continue

            frame_len = 8 + payload_len + (1 if payload_len > 0 else 0)
            if len(self._buffer) < frame_len:
                break

            payload = bytes(self._buffer[8 : 8 + payload_len])
            if payload_len > 0:
                data_cksum = self._buffer[8 + payload_len]
                if self._checksum(payload) != data_cksum:
                    del self._buffer[0]
                    continue

            messages.append(
                TinyFrameMessage(
                    frame_id=frame_id,
                    data_type=data_type,
                    payload=payload,
                )
            )
            del self._buffer[:frame_len]

        return messages


def _unpack_float(payload: bytes, offset: int = 0) -> Optional[float]:
    if len(payload) < offset + 4:
        return None
    return float(struct.unpack_from("<f", payload, offset)[0])


def _unpack_uint16(payload: bytes, offset: int = 0) -> Optional[int]:
    if len(payload) < offset + 2:
        return None
    return int.from_bytes(payload[offset : offset + 2], byteorder="little")


def _unpack_uint32(payload: bytes, offset: int = 0) -> Optional[int]:
    if len(payload) < offset + 4:
        return None
    return int.from_bytes(payload[offset : offset + 4], byteorder="little")


def _unpack_int32(payload: bytes, offset: int = 0) -> Optional[int]:
    if len(payload) < offset + 4:
        return None
    return int.from_bytes(payload[offset : offset + 4], byteorder="little", signed=True)


def parse_ld6002_message(message: TinyFrameMessage) -> Dict[str, Any]:
    payload = message.payload
    data_type = message.data_type
    result: Dict[str, Any] = {
        "frame_id": message.frame_id,
        "type": data_type,
        "type_hex": f"0x{data_type:04X}",
        "raw_payload": payload.hex(" "),
    }

    if data_type == TYPE_FIRMWARE_STATUS and len(payload) >= 4:
        result.update(
            {
                "name": "firmware_status",
                "project": payload[0],
                "major_version": payload[1],
                "sub_version": payload[2],
                "modified_version": payload[3],
            }
        )
    elif data_type == TYPE_HUMAN_STATUS:
        value = _unpack_uint16(payload)
        result.update(
            {
                "name": "human_status",
                "is_human": value == 1 if value is not None else None,
                "human_status_raw": value,
            }
        )
    elif data_type == TYPE_BREATH_RATE:
        result.update({"name": "breath_rate", "breath_rate": _unpack_float(payload)})
    elif data_type == TYPE_HEART_RATE:
        result.update({"name": "heart_rate", "heart_rate": _unpack_float(payload)})
    elif data_type == TYPE_PHASE:
        result.update(
            {
                "name": "phase",
                "total_phase": _unpack_float(payload, 0),
                "breath_phase": _unpack_float(payload, 4),
                "heart_phase": _unpack_float(payload, 8),
            }
        )
    elif data_type == TYPE_TARGET_RANGE:
        flag = _unpack_uint32(payload, 0)
        result.update(
            {
                "name": "target_range",
                "range_valid": flag == 1 if flag is not None else None,
                "target_range_cm": _unpack_float(payload, 4),
                "range_flag": flag,
            }
        )
    elif data_type == TYPE_TRACKING_POSITION:
        result.update(
            {
                "name": "tracking_position",
                "x": _unpack_float(payload, 0),
                "y": _unpack_float(payload, 4),
                "z": _unpack_float(payload, 8),
            }
        )
    elif data_type == TYPE_HUMAN_POSITION:
        target_num = _unpack_uint32(payload, 0) or 0
        targets = []
        offset = 4
        for _ in range(target_num):
            if len(payload) < offset + 20:
                break
            targets.append(
                {
                    "x": _unpack_float(payload, offset),
                    "y": _unpack_float(payload, offset + 4),
                    "z": _unpack_float(payload, offset + 8),
                    "dop_idx": _unpack_int32(payload, offset + 12),
                    "cluster_id": _unpack_int32(payload, offset + 16),
                }
            )
            offset += 20
        result.update({"name": "human_position", "target_num": target_num, "targets": targets})
    else:
        result.update({"name": "unknown"})

    return result


class LD6002SensorReader:
    """Thread-safe reader for the HLK-LD6002 breath and heart-rate radar."""

    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: int = DEFAULT_BAUDRATE,
        timeout: float = 0.2,
    ):
        self.port = port or self._get_default_port()
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser: Optional[serial.Serial] = None
        self.parser = TinyFrameParser()
        self.running = False
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        self.data = LD6002Data()

    @staticmethod
    def _get_default_port() -> str:
        if platform.system() == "Linux":
            ports = sorted(glob.glob("/dev/ttyUSB*"))
            return ports[0] if ports else "/dev/ttyUSB0"
        return "COM3"

    def _update_data(self, parsed: Dict[str, Any]) -> None:
        with self.lock:
            self.data.last_type = parsed["type"]
            self.data.last_raw = parsed["raw_payload"]
            self.data.timestamp = time.time()
            self.data.connected = True
            self.data.error_message = ""

            name = parsed.get("name")
            if name == "firmware_status":
                self.data.firmware.update(
                    {
                        "project": parsed.get("project"),
                        "major_version": parsed.get("major_version"),
                        "sub_version": parsed.get("sub_version"),
                        "modified_version": parsed.get("modified_version"),
                    }
                )
            elif name == "human_status":
                self.data.is_human = parsed.get("is_human")
            elif name == "breath_rate":
                self.data.breath_rate = parsed.get("breath_rate")
            elif name == "heart_rate":
                self.data.heart_rate = parsed.get("heart_rate")
            elif name == "phase":
                self.data.phase.update(
                    {
                        "total_phase": parsed.get("total_phase"),
                        "breath_phase": parsed.get("breath_phase"),
                        "heart_phase": parsed.get("heart_phase"),
                    }
                )
            elif name == "target_range":
                self.data.range_valid = parsed.get("range_valid")
                self.data.target_range_cm = parsed.get("target_range_cm")
            elif name == "tracking_position":
                self.data.tracking_position.update(
                    {
                        "x": parsed.get("x"),
                        "y": parsed.get("y"),
                        "z": parsed.get("z"),
                    }
                )
            elif name == "human_position":
                self.data.targets = parsed.get("targets", [])

    def read_available(self) -> List[Dict[str, Any]]:
        if self.ser is None or not self.ser.is_open:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
            )

        raw = self.ser.read_all()
        if not raw:
            raw = self.ser.read(1)

        parsed_messages = []
        for message in self.parser.feed(raw):
            parsed = parse_ld6002_message(message)
            self._update_data(parsed)
            parsed_messages.append(parsed)
        return parsed_messages

    def _close_serial(self) -> None:
        if self.ser is None:
            return
        try:
            self.ser.close()
        except serial.SerialException:
            pass
        finally:
            self.ser = None

    def _read_loop(self) -> None:
        while self.running and not self.stop_event.is_set():
            try:
                if self.ser is None or not self.ser.is_open:
                    self.ser = serial.Serial(
                        port=self.port,
                        baudrate=self.baudrate,
                        timeout=self.timeout,
                    )
                    print(f"[LD6002] Connected to {self.port}")

                messages = self.read_available()
                if not messages:
                    with self.lock:
                        self.data.connected = True
                self.stop_event.wait(0.02)

            except serial.SerialException as e:
                self._close_serial()
                with self.lock:
                    self.data.connected = False
                    if "Permission denied" in str(e):
                        self.data.error_message = "LD6002 permission denied"
                    else:
                        self.data.error_message = "LD6002 disconnected"
                print(f"[LD6002] Serial error: {e}")
                self.stop_event.wait(1)

            except Exception as e:
                self._close_serial()
                with self.lock:
                    self.data.connected = False
                    self.data.error_message = "LD6002 read failed"
                print(f"[LD6002] Unexpected error: {e}")
                self.stop_event.wait(1)

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        print(f"[LD6002] Started reader on {self.port}")

    def stop(self) -> None:
        self.running = False
        self.stop_event.set()
        self._close_serial()
        if self.thread:
            self.thread.join(timeout=2)
        print("[LD6002] Stopped reader")

    def get_data(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "is_human": self.data.is_human,
                "breath_rate": self.data.breath_rate,
                "heart_rate": self.data.heart_rate,
                "target_range_cm": self.data.target_range_cm,
                "range_valid": self.data.range_valid,
                "phase": dict(self.data.phase),
                "tracking_position": dict(self.data.tracking_position),
                "targets": list(self.data.targets),
                "firmware": dict(self.data.firmware),
                "last_type": self.data.last_type,
                "last_raw": self.data.last_raw,
                "timestamp": self.data.timestamp,
                "connected": self.data.connected,
                "error_message": self.data.error_message,
            }


def parse_bytes(data: bytes) -> List[Dict[str, Any]]:
    parser = TinyFrameParser()
    return [parse_ld6002_message(message) for message in parser.feed(data)]


def _format_message(parsed: Dict[str, Any]) -> str:
    name = parsed.get("name", "unknown")
    if name == "human_status":
        status = "human" if parsed.get("is_human") else "empty"
        return f"[LD6002] human_status={status}"
    if name == "breath_rate":
        value = parsed.get("breath_rate")
        return f"[LD6002] breath_rate={value:.2f} bpm" if value is not None else "[LD6002] breath_rate=None"
    if name == "heart_rate":
        value = parsed.get("heart_rate")
        return f"[LD6002] heart_rate={value:.2f} bpm" if value is not None else "[LD6002] heart_rate=None"
    if name == "target_range":
        return (
            f"[LD6002] range_valid={parsed.get('range_valid')} "
            f"target_range_cm={parsed.get('target_range_cm')}"
        )
    if name == "tracking_position":
        return (
            f"[LD6002] tracking_position="
            f"x={parsed.get('x')} y={parsed.get('y')} z={parsed.get('z')}"
        )
    if name == "human_position":
        return f"[LD6002] target_num={parsed.get('target_num')} targets={parsed.get('targets')}"
    if name == "phase":
        return (
            f"[LD6002] phase total={parsed.get('total_phase')} "
            f"breath={parsed.get('breath_phase')} heart={parsed.get('heart_phase')}"
        )
    return f"[LD6002] {parsed.get('type_hex')} payload={parsed.get('raw_payload')}"


def run_realtime_plot(
    reader: LD6002SensorReader,
    window_seconds: float = 120.0,
    refresh_interval: float = 0.2,
) -> None:
    import matplotlib.pyplot as plt

    reader.start()

    start_time = time.time()
    times = deque()
    breath_values = deque()
    heart_values = deque()

    plt.ion()
    fig, ax = plt.subplots(figsize=(10, 5))
    breath_line, = ax.plot([], [], label="Breath rate", color="#2E86AB", linewidth=2)
    heart_line, = ax.plot([], [], label="Heart rate", color="#D1495B", linewidth=2)
    status_text = ax.text(
        0.01,
        0.98,
        "",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=11,
        bbox={"facecolor": "white", "edgecolor": "#cccccc", "alpha": 0.9},
    )

    ax.set_title("HLK-LD6002 Breath and Heart Rate")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Rate (bpm)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")

    try:
        while plt.fignum_exists(fig.number) and not reader.stop_event.is_set():
            data = reader.get_data()
            now = time.time() - start_time
            times.append(now)
            breath_values.append(data["breath_rate"] if data["breath_rate"] is not None else math.nan)
            heart_values.append(data["heart_rate"] if data["heart_rate"] is not None else math.nan)

            while times and now - times[0] > window_seconds:
                times.popleft()
                breath_values.popleft()
                heart_values.popleft()

            x_values = list(times)
            breath_line.set_data(x_values, list(breath_values))
            heart_line.set_data(x_values, list(heart_values))

            left = max(0.0, now - window_seconds)
            right = max(window_seconds, now)
            ax.set_xlim(left, right)

            numeric_values = [
                value
                for value in list(breath_values) + list(heart_values)
                if value is not None and not math.isnan(value)
            ]
            if numeric_values:
                min_value = min(numeric_values)
                max_value = max(numeric_values)
                padding = max(5.0, (max_value - min_value) * 0.15)
                ax.set_ylim(max(0.0, min_value - padding), max_value + padding)
            else:
                ax.set_ylim(0, 120)

            if data["is_human"] is True:
                human_text = "Human: yes"
            elif data["is_human"] is False:
                human_text = "Human: no"
            else:
                human_text = "Human: unknown"

            range_value = data["target_range_cm"]
            if data["range_valid"] is False:
                range_text = "Range: invalid"
            elif range_value is None:
                range_text = "Range: unknown"
            else:
                range_text = f"Range: {range_value:.1f} cm"

            connection_text = "Connected" if data["connected"] else "Disconnected"
            status_text.set_text(f"{human_text}\n{range_text}\n{connection_text}")

            fig.canvas.draw_idle()
            plt.pause(refresh_interval)
    except KeyboardInterrupt:
        reader.stop_event.set()
        plt.close(fig)
    finally:
        reader.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Read and parse HLK-LD6002 serial data.")
    parser.add_argument("--port", default=None, help="Serial port, for example /dev/ttyUSB0")
    parser.add_argument("--baudrate", type=int, default=DEFAULT_BAUDRATE)
    parser.add_argument("--print-only", action="store_true", help="Print parsed messages instead of showing a plot")
    parser.add_argument("--window", type=float, default=120.0, help="Plot time window in seconds")
    parser.add_argument("--plot-interval", type=float, default=0.2, help="Plot refresh interval in seconds")
    args = parser.parse_args()

    reader = LD6002SensorReader(port=args.port, baudrate=args.baudrate)
    print(f"[LD6002] Reading from {reader.port} at {reader.baudrate} baud")

    if not args.print_only:
        run_realtime_plot(
            reader,
            window_seconds=args.window,
            refresh_interval=args.plot_interval,
        )
        return

    try:
        while True:
            for parsed in reader.read_available():
                print(_format_message(parsed))
            time.sleep(0.02)
    except KeyboardInterrupt:
        pass
    finally:
        reader.stop()


if __name__ == "__main__":
    main()
