#!/usr/bin/env python3
"""Capture 30s EEG from OpenBCI Cyton (BrainFlow) and run 3-class inference."""

import argparse
import os
import sys
import time
from datetime import datetime
from typing import Optional

import numpy as np

try:
    from brainflow.board_shim import BoardIds, BoardShim, BrainFlowInputParams
except Exception as exc:  # pragma: no cover
    print("BrainFlow is required. Install it in your environment.", file=sys.stderr)
    print(str(exc), file=sys.stderr)
    sys.exit(1)

try:
    from joblib import load as joblib_load
except Exception:  # pragma: no cover
    joblib_load = None

try:
    from serial.tools import list_ports
except Exception:
    list_ports = None

from train_eeg_3class import ModelBundle, predict_30s


def list_serial_ports() -> None:
    if list_ports is None:
        print("pyserial is not available to list ports.")
        return
    ports = list_ports.comports()
    if not ports:
        print("No serial ports found.")
        return
    for p in ports:
        print(f"{p.device} - {p.description}")


def load_model(model_path: str) -> ModelBundle:
    if joblib_load is None:
        raise RuntimeError("joblib is required to load the model.")
    obj = joblib_load(model_path)
    if isinstance(obj, ModelBundle):
        return obj
    if isinstance(obj, dict):
        if "model_bundle" in obj and isinstance(obj["model_bundle"], ModelBundle):
            return obj["model_bundle"]
        if "model" in obj and isinstance(obj["model"], ModelBundle):
            return obj["model"]
    raise ValueError("Unsupported model file format.")


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def save_capture(
    out_dir: str,
    eeg: np.ndarray,
    sample_rate: int,
    channel_map: str,
    task_type: str,
    save_csv: bool,
) -> str:
    ensure_dir(out_dir)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.join(out_dir, f"eeg_30s_{ts}")
    np.save(base + ".npy", eeg)
    if save_csv:
        np.savetxt(base + ".csv", eeg, delimiter=",")
    meta = {
        "sample_rate": sample_rate,
        "shape": list(eeg.shape),
        "channel_map": channel_map,
        "task_type": task_type,
    }
    with open(base + ".meta.txt", "w", encoding="utf-8") as f:
        for k, v in meta.items():
            f.write(f"{k}: {v}\n")
    return base


def parse_channel_map(text: str) -> np.ndarray:
    parts = [p.strip() for p in text.split(",") if p.strip()]
    idx = [int(p) for p in parts]
    if len(idx) != 8:
        raise ValueError("channel_map must contain 8 indices.")
    return np.asarray(idx, dtype=int)


def capture_30s(
    serial_port: str,
    duration: float,
    sample_rate: int,
    warmup: float,
    channel_map: Optional[np.ndarray],
    wifi: bool,
    ip_address: str,
    ip_port: int,
) -> np.ndarray:
    params = BrainFlowInputParams()
    if wifi:
        params.ip_address = ip_address
        params.ip_port = ip_port
        if hasattr(BoardIds, "CYTON_WIFI_BOARD"):
            board_id = BoardIds.CYTON_WIFI_BOARD.value
        else:
            board_id = 5
    else:
        params.serial_port = serial_port
        board_id = BoardIds.CYTON_BOARD.value
    board = BoardShim(board_id, params)

    BoardShim.enable_dev_board_logger()
    board.prepare_session()
    board.start_stream()
    time.sleep(warmup)
    board.get_board_data()  # flush warmup

    eeg_channels = BoardShim.get_eeg_channels(board_id)
    needed = int(round(duration * sample_rate))
    collected = []
    total = 0

    try:
        while total < needed:
            data = board.get_board_data()
            if data.size == 0:
                time.sleep(0.05)
                continue
            eeg = data[eeg_channels, :]
            if eeg.size == 0:
                continue
            collected.append(eeg)
            total += eeg.shape[1]
            time.sleep(0.01)
    finally:
        board.stop_stream()
        board.release_session()

    eeg_all = np.concatenate(collected, axis=1)
    eeg_all = eeg_all[:, :needed]
    if channel_map is not None:
        eeg_all = eeg_all[channel_map, :]
    return eeg_all.T.astype(np.float32)


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenBCI Cyton 30s capture + inference")
    parser.add_argument("--serial_port", type=str, default="", help="COM port, e.g., COM3")
    parser.add_argument("--list_ports", action="store_true", help="List available serial ports")
    parser.add_argument("--wifi", action="store_true", help="Use WiFi Shield mode")
    parser.add_argument("--ip_address", type=str, default="192.168.4.1")
    parser.add_argument("--ip_port", type=int, default=3)
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--sample_rate", type=int, default=250)
    parser.add_argument("--warmup", type=float, default=2.0)
    parser.add_argument("--model_path", type=str, default="")
    parser.add_argument("--task_type", type=str, default="Unknown")
    parser.add_argument("--channel_map", type=str, default="0,1,2,3,4,5,6,7")
    parser.add_argument("--out_dir", type=str, default=os.path.join(os.path.dirname(__file__), "captures"))
    parser.add_argument("--save_csv", action="store_true")
    args = parser.parse_args()

    if args.list_ports:
        list_serial_ports()
        return
    if not args.wifi and not args.serial_port:
        raise ValueError("serial_port is required (e.g., COM3)")
    if not args.model_path:
        raise ValueError("model_path is required for inference")

    channel_map = parse_channel_map(args.channel_map)
    model_bundle = load_model(args.model_path)

    eeg = capture_30s(
        serial_port=args.serial_port,
        duration=args.duration,
        sample_rate=args.sample_rate,
        warmup=args.warmup,
        channel_map=channel_map,
        wifi=args.wifi,
        ip_address=args.ip_address,
        ip_port=args.ip_port,
    )
    save_capture(
        out_dir=args.out_dir,
        eeg=eeg,
        sample_rate=args.sample_rate,
        channel_map=args.channel_map,
        task_type=args.task_type,
        save_csv=args.save_csv,
    )

    result = predict_30s(eeg, model_bundle, task_type=args.task_type, force_label=True)
    print("Prediction:", result)


if __name__ == "__main__":
    main()
