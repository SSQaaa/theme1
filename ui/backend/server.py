from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import time
import random
import os
import sys
import platform
import shutil
import asyncio
import json
import re
import urllib.error
import urllib.request
import threading
from typing import Any, Callable, Dict, Tuple, Optional, List, Literal

# Import sensor reader
try:
    from sensor.co2.sensor_reader import CO2SensorReader
except ImportError as e:
    print(f"[SENSOR] Failed to import sensor_reader: {e}")
    CO2SensorReader = None

# Import PM2.5 reader
try:
    from sensor.PM25.pm25_reader import PM25SensorReader
except ImportError as e:
    print(f"[PM25] Failed to import pm25_reader: {e}")
    PM25SensorReader = None

# Import turntable serial
try:
    from turntable.turntable_serial import TurntableSerial
except ImportError as e:
    print(f"[TURNTABLE] Failed to import turntable_serial: {e}")
    TurntableSerial = None

# EEG / BrainFlow (optional)
try:
    import numpy as np
except Exception as e:
    print(f"[EEG] Failed to import numpy: {e}")
    np = None

try:
    from brainflow.board_shim import BoardIds, BoardShim, BrainFlowInputParams
except Exception as e:
    print(f"[EEG] Failed to import BrainFlow: {e}")
    BoardIds = None
    BoardShim = None
    BrainFlowInputParams = None

try:
    from joblib import load as joblib_load
except Exception as e:
    print(f"[EEG] Failed to import joblib: {e}")
    joblib_load = None

# ============================================================
# 0) 环境自动检测和配置（自动适配 Windows/Linux）
# ============================================================

# 系统检测
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

# 获取项目基础目录（自动适配）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# Home Assistant light strip integration
# ============================================================

def _parse_py_constant(text: str, name: str) -> Optional[str]:
    pattern = rf"^{name}\s*=\s*['\"](.+?)['\"]"
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1) if match else None

def _resolve_ha_config() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    url = os.getenv("HA_URL")
    token = os.getenv("HA_TOKEN")
    entity_id = os.getenv("HA_ENTITY_ID")

    if url and token and entity_id:
        return url, token, entity_id

    candidate_paths = []
    env_path = os.getenv("HA_CONFIG_PATH")
    if env_path:
        candidate_paths.append(env_path)

    project_root = os.path.dirname(os.path.dirname(BASE_DIR))
    candidate_paths.append(os.path.join(project_root, "ai_assistent", "HA.py"))

    for path in candidate_paths:
        if not path or not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            url = url or _parse_py_constant(text, "HA_URL")
            token = token or _parse_py_constant(text, "TOKEN")
            entity_id = entity_id or _parse_py_constant(text, "ENTITY_ID")
        except Exception as e:
            print(f"[HA] Failed to read config from {path}: {e}")

    return url, token, entity_id

HA_URL, HA_TOKEN, HA_ENTITY_ID = _resolve_ha_config()

def _ha_ready() -> bool:
    return bool(HA_URL and HA_TOKEN and HA_ENTITY_ID)

def _ha_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

def _ha_request(method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    if not _ha_ready():
        return False, None, "HA config missing (HA_URL/HA_TOKEN/HA_ENTITY_ID)"

    url = f"{HA_URL}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in _ha_headers().items():
        req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            return True, json.loads(body) if body else None, ""
    except urllib.error.HTTPError as e:
        return False, None, f"HA HTTP {e.code}"
    except Exception as e:
        return False, None, f"HA request error: {e}"

def _ha_service(service: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
    ok, _, err = _ha_request("POST", f"/api/services/light/{service}", payload)
    return ok, err

def _fetch_light_state() -> Tuple[Optional[Dict[str, Any]], str]:
    ok, data, err = _ha_request("GET", f"/api/states/{HA_ENTITY_ID}")
    if not ok or not isinstance(data, dict):
        return None, err or "Failed to fetch HA state"
    return data, ""

def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))

def _normalize_brightness(brightness: Optional[float]) -> int:
    if brightness is None:
        return 0
    return int(round(_clamp(brightness, 0, 255) / 255 * 100))

def _get_color_temp_range(attrs: Dict[str, Any]) -> Tuple[str, int, int]:
    min_mireds = attrs.get("min_mireds")
    max_mireds = attrs.get("max_mireds")
    if isinstance(min_mireds, (int, float)) and isinstance(max_mireds, (int, float)):
        return "mireds", int(min_mireds), int(max_mireds)

    min_k = attrs.get("min_color_temp_kelvin")
    max_k = attrs.get("max_color_temp_kelvin")
    if isinstance(min_k, (int, float)) and isinstance(max_k, (int, float)):
        return "kelvin", int(min_k), int(max_k)

    return "kelvin", 2700, 6500

def _current_color_temp(attrs: Dict[str, Any], mode: str) -> Optional[int]:
    if mode == "mireds":
        ct = attrs.get("color_temp")
        if ct is None and attrs.get("color_temp_kelvin"):
            return int(round(1_000_000 / attrs["color_temp_kelvin"]))
        return int(ct) if isinstance(ct, (int, float)) else None

    if attrs.get("color_temp_kelvin"):
        return int(attrs["color_temp_kelvin"])
    if attrs.get("color_temp"):
        return int(round(1_000_000 / attrs["color_temp"]))
    return None

def _color_temp_percent(attrs: Dict[str, Any]) -> int:
    mode, min_v, max_v = _get_color_temp_range(attrs)
    current = _current_color_temp(attrs, mode)
    if current is None:
        return 50

    if max_v == min_v:
        return 50

    if mode == "mireds":
        pct = (current - min_v) / (max_v - min_v) * 100
    else:
        pct = (max_v - current) / (max_v - min_v) * 100

    return int(round(_clamp(pct, 0, 100)))

def _color_temp_value_from_percent(attrs: Dict[str, Any], percent: float) -> int:
    mode, min_v, max_v = _get_color_temp_range(attrs)
    percent = _clamp(percent, 0, 100)

    if mode == "mireds":
        ct = min_v + (percent / 100) * (max_v - min_v)
        return int(round(ct))

    kelvin = max_v - (percent / 100) * (max_v - min_v)
    return int(round(1_000_000 / kelvin))

# ============================================================
# EEG / BrainFlow integration
# ============================================================

PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
EEG_DIR = os.getenv("EEG_DIR") or os.path.join(PROJECT_ROOT, "EEG")
if EEG_DIR and EEG_DIR not in sys.path:
    sys.path.append(EEG_DIR)

EEG_MODEL_PATH = os.getenv("EEG_MODEL_PATH") or os.path.join(EEG_DIR, "model_bundle_acc_0.6312.joblib")
EEG_WIFI = str(os.getenv("EEG_WIFI", "true")).lower() in ("1", "true", "yes", "y")
EEG_IP_ADDRESS = os.getenv("EEG_IP_ADDRESS", "192.168.4.1")
EEG_IP_PORT = int(os.getenv("EEG_IP_PORT", "6677"))
EEG_SERIAL_PORT = os.getenv("EEG_SERIAL_PORT", "")
EEG_SAMPLE_RATE = int(os.getenv("EEG_SAMPLE_RATE", "250"))
EEG_DURATION = float(os.getenv("EEG_DURATION", "30"))
EEG_WARMUP = float(os.getenv("EEG_WARMUP", "2"))
EEG_CHANNEL_MAP = os.getenv("EEG_CHANNEL_MAP", "0,1,2,3,4,5,6,7")
EEG_TASK_TYPE = os.getenv("EEG_TASK_TYPE", "Unknown")
EEG_STREAM_INTERVAL = float(os.getenv("EEG_STREAM_INTERVAL", "0.1"))

try:
    from train_eeg_3class import ModelBundle, predict_30s
except Exception as e:
    print(f"[EEG] Failed to import train_eeg_3class: {e}")
    ModelBundle = None
    predict_30s = None

EEG_MODEL = None
EEG_MODEL_LOCK = threading.Lock()

def _parse_channel_map(text: str) -> Optional[List[int]]:
    if not text:
        return None
    parts = [p.strip() for p in text.split(",") if p.strip()]
    try:
        idx = [int(p) for p in parts]
    except Exception:
        return None
    return idx if len(idx) == 8 else None

def _get_eeg_model() -> Optional[Any]:
    global EEG_MODEL
    if EEG_MODEL is not None:
        return EEG_MODEL
    if joblib_load is None or ModelBundle is None:
        return None
    if not EEG_MODEL_PATH or not os.path.exists(EEG_MODEL_PATH):
        print(f"[EEG] Model path not found: {EEG_MODEL_PATH}")
        return None
    with EEG_MODEL_LOCK:
        if EEG_MODEL is not None:
            return EEG_MODEL
        try:
            # If the model was saved when ModelBundle lived in __main__,
            # ensure __main__.ModelBundle is available for unpickling.
            main_mod = sys.modules.get("__main__")
            if main_mod is not None and not hasattr(main_mod, "ModelBundle"):
                try:
                    setattr(main_mod, "ModelBundle", ModelBundle)
                except Exception:
                    pass
            obj = joblib_load(EEG_MODEL_PATH)
            if isinstance(obj, ModelBundle):
                EEG_MODEL = obj
            elif isinstance(obj, dict):
                if "model_bundle" in obj and isinstance(obj["model_bundle"], ModelBundle):
                    EEG_MODEL = obj["model_bundle"]
                elif "model" in obj and isinstance(obj["model"], ModelBundle):
                    EEG_MODEL = obj["model"]
            if EEG_MODEL is None:
                print("[EEG] Unsupported model file format.")
        except Exception as e:
            print(f"[EEG] Failed to load model: {e}")
    return EEG_MODEL

def _eeg_ready() -> bool:
    return (
        BoardShim is not None
        and BrainFlowInputParams is not None
        and np is not None
        and predict_30s is not None
        and _get_eeg_model() is not None
    )

def _build_eeg_board() -> Tuple[BoardShim, int]:
    params = BrainFlowInputParams()
    if EEG_WIFI:
        params.ip_address = EEG_IP_ADDRESS
        params.ip_port = EEG_IP_PORT
        if BoardIds is not None and hasattr(BoardIds, "CYTON_WIFI_BOARD"):
            board_id = BoardIds.CYTON_WIFI_BOARD.value
        else:
            board_id = 5
    else:
        if not EEG_SERIAL_PORT:
            raise RuntimeError("EEG_SERIAL_PORT is required when not using WiFi")
        params.serial_port = EEG_SERIAL_PORT
        board_id = BoardIds.CYTON_BOARD.value
    return BoardShim(board_id, params), board_id

class EEGSession:
    def __init__(self, websocket: WebSocket, loop: asyncio.AbstractEventLoop):
        self.websocket = websocket
        self.loop = loop
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=2)

    def _send(self, payload: Dict[str, Any]) -> None:
        try:
            msg = json.dumps(payload, ensure_ascii=False)
            asyncio.run_coroutine_threadsafe(self.websocket.send_text(msg), self.loop)
        except Exception as e:
            print(f"[EEG] Failed to send websocket message: {e}")

    def _run(self) -> None:
        if not _eeg_ready():
            self._send({"type": "error", "message": "EEG backend not ready"})
            return

        try:
            board, board_id = _build_eeg_board()
        except Exception as e:
            self._send({"type": "error", "message": f"EEG board init failed: {e}"})
            return

        channel_map = _parse_channel_map(EEG_CHANNEL_MAP)
        model = _get_eeg_model()
        collected: List[np.ndarray] = []
        buffered: List[np.ndarray] = []
        total = 0
        last_send = time.time()

        try:
            BoardShim.enable_dev_board_logger()
            board.prepare_session()
            board.start_stream()
            time.sleep(EEG_WARMUP)
            board.get_board_data()

            eeg_channels = BoardShim.get_eeg_channels(board_id)
            sampling_rate = BoardShim.get_sampling_rate(board_id)
            needed = int(round(EEG_DURATION * sampling_rate))
            self._send({"type": "meta", "sample_rate": sampling_rate})

            while not self.stop_event.is_set():
                data = board.get_board_data()
                if data.size > 0:
                    eeg = data[eeg_channels, :]
                    if channel_map is not None:
                        eeg = eeg[channel_map, :]
                    eeg = eeg.T.astype(np.float32)
                    if eeg.size:
                        buffered.append(eeg)
                        collected.append(eeg)
                        total += eeg.shape[0]

                now = time.time()
                if buffered and (now - last_send) >= EEG_STREAM_INTERVAL:
                    chunk = np.concatenate(buffered, axis=0)
                    buffered.clear()
                    self._send({"type": "samples", "samples": chunk.tolist()})
                    last_send = now

                if total >= needed:
                    eeg_all = np.concatenate(collected, axis=0)[:needed]
                    result = predict_30s(
                        eeg_all,
                        model,
                        fs=sampling_rate,
                        task_type=EEG_TASK_TYPE,
                        force_label=True,
                    )
                    self._send({"type": "result", **result})
                    break

                time.sleep(0.01)
        except Exception as e:
            self._send({"type": "error", "message": f"EEG streaming error: {e}"})
        finally:
            try:
                board.stop_stream()
                board.release_session()
            except Exception:
                pass


# ============================================================
# Face emotion integration (RKNN)
# ============================================================

FACE_DIR = os.getenv("FACE_DIR")
if not FACE_DIR:
    candidate1 = os.path.join(PROJECT_ROOT, "face")
    candidate2 = os.path.join(PROJECT_ROOT, "face", "face")
    if os.path.exists(os.path.join(candidate1, "emotion_detect.py")):
        FACE_DIR = candidate1
    elif os.path.exists(os.path.join(candidate2, "emotion_detect.py")):
        FACE_DIR = candidate2
    else:
        FACE_DIR = candidate1

if FACE_DIR and FACE_DIR not in sys.path:
    sys.path.append(FACE_DIR)

FACE_MODEL_PATH = os.getenv("FACE_MODEL_PATH") or os.path.join(FACE_DIR, "best_emotion_model.rknn")
FACE_CAMERA_INDEX = int(os.getenv("FACE_CAMERA_INDEX", "0"))
FACE_TARGET_FPS = float(os.getenv("FACE_TARGET_FPS", "10"))
FACE_MIN_CONF = float(os.getenv("FACE_MIN_CONF", "0.0"))

try:
    import cv2
except Exception as e:
    print(f"[FACE] Failed to import cv2: {e}")
    cv2 = None

try:
    import numpy as np
except Exception as e:
    print(f"[FACE] Failed to import numpy: {e}")
    np = None

try:
    import mediapipe as mp
except Exception as e:
    print(f"[FACE] Failed to import mediapipe: {e}")
    mp = None

try:
    from rknn_emotion import RKNNEmotionDetector
except Exception as e:
    print(f"[FACE] Failed to import rknn_emotion: {e}")
    RKNNEmotionDetector = None

EMOTION_LABELS = [
    "angry",
    "disgust",
    "fear",
    "happy",
    "neutral",
    "sad",
    "surprise",
]

EMOTION_LABELS_CN = {
    "angry": "愤怒",
    "disgust": "厭恶",
    "fear": "恐惧",
    "happy": "愉悦",
    "neutral": "平静",
    "sad": "悲伤",
    "surprise": "惊讶",
    "none": "未检测到",
}

class FaceEmotionService:
    def __init__(self):
        self.lock = threading.Lock()
        self.viewer_count = 0
        self.thread = None
        self.stop_event = threading.Event()
        self.running = False
        self.latest_frame = None
        self.latest_result = {
            "label": "none",
            "label_cn": EMOTION_LABELS_CN["none"],
            "confidence": 0.0,
            "probs": None,
        }
        self.last_probs = None
        self.alpha = 0.4

    def is_available(self) -> bool:
        return cv2 is not None and np is not None and mp is not None and RKNNEmotionDetector is not None

    def add_viewer(self) -> None:
        with self.lock:
            self.viewer_count += 1
            if not self.running:
                self._start()

    def remove_viewer(self) -> None:
        with self.lock:
            self.viewer_count = max(0, self.viewer_count - 1)
            if self.viewer_count == 0:
                self._stop()

    def get_frame(self):
        with self.lock:
            return self.latest_frame

    def get_result(self):
        with self.lock:
            return dict(self.latest_result)

    def _start(self):
        if self.running:
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.running = True
        self.thread.start()

    def _stop(self):
        if not self.running:
            return
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)
        self.running = False

    def _run(self):
        if not self.is_available():
            with self.lock:
                self.latest_result = {
                    "label": "none",
                    "label_cn": EMOTION_LABELS_CN["none"],
                    "confidence": 0.0,
                    "probs": None,
                    "error": "face backend not ready",
                }
            return

        detector = None
        face_detector = None
        cap = None

        try:
            detector = RKNNEmotionDetector(FACE_MODEL_PATH)
            face_detector = mp.solutions.face_detection.FaceDetection(
                model_selection=0, min_detection_confidence=0.5
            )
            cap = cv2.VideoCapture(FACE_CAMERA_INDEX)
            if not cap.isOpened():
                raise RuntimeError("cannot open camera")

            target_interval = 1.0 / max(1.0, FACE_TARGET_FPS)

            while not self.stop_event.is_set():
                start_t = time.time()
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.1)
                    continue

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                faces = face_detector.process(rgb)

                probs = None
                label = "none"
                conf = 0.0

                if faces and faces.detections:
                    h, w, _ = frame.shape
                    boxes = []
                    for det in faces.detections:
                        bbox = det.location_data.relative_bounding_box
                        x = int(bbox.xmin * w)
                        y = int(bbox.ymin * h)
                        ww = int(bbox.width * w)
                        hh = int(bbox.height * h)
                        boxes.append((x, y, ww, hh))

                    x, y, ww, hh = sorted(boxes, key=lambda b: b[2] * b[3], reverse=True)[0]
                    x = max(0, x)
                    y = max(0, y)
                    ww = min(ww, w - x)
                    hh = min(hh, h - y)
                    if ww > 0 and hh > 0:
                        face = frame[y:y + hh, x:x + ww]
                        probs, label, conf = detector.infer(face)
                        if self.last_probs is None:
                            self.last_probs = probs
                        else:
                            probs = self.alpha * probs + (1 - self.alpha) * self.last_probs
                            self.last_probs = probs
                        pred = int(np.argmax(probs))
                        label = EMOTION_LABELS[pred]
                        conf = float(probs[pred])

                label_cn = EMOTION_LABELS_CN.get(label, label)

                ok, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ok:
                    with self.lock:
                        self.latest_frame = jpeg.tobytes()
                        self.latest_result = {
                            "label": label,
                            "label_cn": label_cn,
                            "confidence": conf,
                            "probs": probs.tolist() if probs is not None else None,
                        }

                elapsed = time.time() - start_t
                if elapsed < target_interval:
                    time.sleep(target_interval - elapsed)

        except Exception as e:
            with self.lock:
                self.latest_result = {
                    "label": "none",
                    "label_cn": EMOTION_LABELS_CN["none"],
                    "confidence": 0.0,
                    "probs": None,
                    "error": f"{e}",
                }
        finally:
            try:
                if cap is not None:
                    cap.release()
            except Exception:
                pass
            try:
                if face_detector is not None:
                    face_detector.close()
            except Exception:
                pass
            try:
                if detector is not None:
                    detector.release()
            except Exception:
                pass

face_service = FaceEmotionService()


# MJPEG generator

def _face_mjpeg_generator():
    face_service.add_viewer()
    try:
        while True:
            frame = face_service.get_frame()
            if not frame:
                time.sleep(0.1)
                continue
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            time.sleep(max(0.02, 1.0 / max(1.0, FACE_TARGET_FPS)))
    finally:
        face_service.remove_viewer()
def find_audio_player() -> Tuple[Optional[str], Optional[str]]:
    """
    自动查找可用的音频播放器
    返回: (播放器路径, 播放器类型)
    优先级：
    - Windows: mpv.exe (本地开发) > startfile (备选)
    - Linux: mpv (香橙派) > mpg123 (树莓派老系统) > ffmpeg > None
    """
    # Windows 环境
    if IS_WINDOWS:
        # 1. 优先使用本地开发环境的mpv
        windows_mpv = r"D:\software\mpv\mpv.exe"
        if os.path.exists(windows_mpv):
            return windows_mpv, "mpv"
        # 2. 尝试系统PATH中的mpv
        mpv_path = shutil.which("mpv.exe")
        if mpv_path:
            return mpv_path, "mpv"
        # 3. Windows 备选：使用 os.startfile
        return None, "startfile"
    
    # Linux 环境（树莓派/香橙派）
    if IS_LINUX:
        # 1. 优先使用 mpv（香橙派推荐，未来使用）
        mpv_path = shutil.which("mpv")
        if mpv_path:
            return mpv_path, "mpv"
        # 尝试常见路径
        for path in ["/usr/bin/mpv", "/usr/local/bin/mpv"]:
            if os.path.exists(path):
                return path, "mpv"
        
        # 2. 使用 mpg123（树莓派老系统，可靠的选择）
        mpg123_path = shutil.which("mpg123")
        if mpg123_path:
            return mpg123_path, "mpg123"
        for path in ["/usr/bin/mpg123", "/usr/local/bin/mpg123"]:
            if os.path.exists(path):
                return path, "mpg123"
        
        # 3. 使用 ffmpeg（如果安装了）
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            return ffmpeg_path, "ffmpeg"
    
    return None, None

# 全局播放器配置
AUDIO_PLAYER, PLAYER_TYPE = find_audio_player()

def get_music_path(filename: str) -> str:
    """
    获取音乐文件路径（自动适配）
    优先级：Windows硬编码路径 > 相对路径（推荐）
    """
    # Windows 开发环境硬编码路径（如果存在）
    if IS_WINDOWS:
        win_path = rf"D:\A_theme_one\ui\backend\music\{filename}"
        if os.path.exists(win_path):
            return win_path
    
    # 默认相对路径（跨平台，推荐方式）
    default_path = os.path.join(BASE_DIR, "music", filename)
    return default_path

# 音乐文件路径（自动解析）
HARD_MUSIC_PATH = get_music_path("alarm.mp3")
HARD_MEDITATION_PATH = get_music_path("white.mp3")
FALLBACK_MUSIC_PATH = os.path.join(BASE_DIR, "music", "alarm.mp3")
FALLBACK_MEDITATION_PATH = os.path.join(BASE_DIR, "music", "white.mp3")

# 每个 cmd 对应一个 handler
HANDLERS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

def register_handlers() -> None:
    """把 cmd -> handler 的映射放在这里"""
    HANDLERS.update({
        "PLAY_MUSIC": handle_play_music,
        "PLAY_MEDITATION": handle_play_meditation,
        "SPIN_WHEEL": handle_spin_wheel,
        "STOP_MUSIC": handle_stop_music,
        "PING": handle_ping,
    })

# ============================================================
# 1) FastAPI 初始化
# ============================================================
app = FastAPI()

# 前端静态文件路径（如果存在 dist 文件夹，则提供前端服务）
FRONTEND_DIST = os.path.join(os.path.dirname(BASE_DIR), "dist")
if os.path.exists(FRONTEND_DIST):
    # 提供静态文件服务（Vite 构建的是 assets 文件夹）
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    print(f"[FRONTEND] 前端静态文件目录: {FRONTEND_DIST}")
else:
    print(f"[FRONTEND] 未找到前端构建文件，仅提供 API 服务")
    print(f"[FRONTEND] 提示: 运行 'npm run build' 后，dist 文件夹应位于: {os.path.dirname(BASE_DIR)}/dist")

# ============================================================
# 2) CORS：允许 Vite 开发端口访问
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # 开发阶段全放开
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 3) 音乐播放逻辑（统一接口，自动适配多种播放器）
# ============================================================
player_process = None
player_mode = None

# ============================================================
# Sensor reader instance
# ============================================================
sensor_reader: Optional[CO2SensorReader] = None

def init_sensor_reader():
    """Initialize sensor reader on startup."""
    global sensor_reader
    if CO2SensorReader is None:
        print("[SENSOR] CO2SensorReader not available (import failed)")
        return
    try:
        sensor_reader = CO2SensorReader()
        sensor_reader.start()
        print("[SENSOR] CO2 sensor reader started")
    except Exception as e:
        print(f"[SENSOR] Failed to start sensor reader: {e}")
        print("[SENSOR] Continuing without sensor support")

def init_pm25_reader():
    """Initialize PM2.5 reader on startup."""
    global pm25_reader
    if PM25SensorReader is None:
        print("[PM25] PM25SensorReader not available (import failed)")
        return
    try:
        pm25_reader = PM25SensorReader()
        pm25_reader.start()
        print("[PM25] PM2.5 reader started")
    except Exception as e:
        print(f"[PM25] Failed to start PM2.5 reader: {e}")


# ============================================================
# Turntable serial instance
# ============================================================
turntable_serial: Optional[TurntableSerial] = None

def init_turntable():
    """Initialize turntable serial on startup."""
    global turntable_serial
    if TurntableSerial is None:
        print("[TURNTABLE] TurntableSerial not available (import failed)")
        return
    try:
        turntable_serial = TurntableSerial()
        print("[TURNTABLE] 转盘串口初始化成功")
    except Exception as e:
        print(f"[TURNTABLE] 转盘串口初始化失败: {e}")
        print("[TURNTABLE] 继续运行（转盘功能不可用）")
        turntable_serial = None

def file_exists(path: str) -> bool:
    try:
        return os.path.exists(path)
    except Exception:
        return False

def resolve_music_path() -> str:
    """优先使用 HARD_MUSIC_PATH，如果不存在则使用 FALLBACK_MUSIC_PATH"""
    if file_exists(HARD_MUSIC_PATH):
        return HARD_MUSIC_PATH
    return FALLBACK_MUSIC_PATH

def resolve_meditation_path() -> str:
    """优先使用 HARD_MEDITATION_PATH，如果不存在则使用 FALLBACK_MEDITATION_PATH"""
    if file_exists(HARD_MEDITATION_PATH):
        return HARD_MEDITATION_PATH
    return FALLBACK_MEDITATION_PATH

def stop_music() -> Tuple[bool, str]:
    """
    停止音乐：支持所有播放器类型
    """
    global player_process, player_mode

    if player_mode in ["mpv", "mpg123", "ffmpeg"]:
        if player_process and player_process.poll() is None:
            print(f"[STOP] terminating {player_mode} process...")
            player_process.terminate()
            try:
                player_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                player_process.kill()
        player_process = None
        player_mode = None
        return True, f"stopped {player_mode}"

    if player_mode == "startfile":
        player_process = None
        player_mode = None
        return False, "startfile mode cannot force stop system player"

    return True, "no music playing"

def play_music(path: str, volume: int = 80, loop: bool = True) -> str:
    """
    播放音乐（自动适配 Windows/Linux，多种播放器）
    """
    global player_process, player_mode

    stop_music()

    print("[PLAY] requested path:", path)
    print("[PLAY] exists:", file_exists(path))
    print(f"[PLAY] player: {AUDIO_PLAYER} (type: {PLAYER_TYPE})")

    if not file_exists(path):
        raise FileNotFoundError(f"music file not found: {path}")

    if not AUDIO_PLAYER and PLAYER_TYPE != "startfile":
        raise RuntimeError(
            "No audio player found!\n"
            "For Raspberry Pi (old system): sudo apt install mpg123 -y\n"
            "For Orange Pi (future): sudo apt install mpv -y"
        )

    try:
        if PLAYER_TYPE == "mpv":
            # mpv 播放器（Windows 和 Linux 通用，香橙派推荐）
            player_mode = "mpv"
            args = [AUDIO_PLAYER, "--no-video", f"--volume={volume}"]

            # 让 mpv 自动选择音频设备（会自动处理 PulseAudio 和 ALSA）
            # 不指定 --audio-device，mpv 会尝试 PulseAudio，失败后自动回退到 ALSA

            if loop:
                args += ["--loop=inf"]
            args += [path]
            print("[PLAY] using mpv:", " ".join(args))
            player_process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # 等待一小段时间检查进程是否立即退出
            time.sleep(0.5)
            if player_process.poll() is not None:
                # 进程已退出，打印错误信息
                stdout, stderr = player_process.communicate()
                print("[PLAY ERROR] mpv exited immediately!")
                print("[PLAY ERROR] stdout:", stdout.decode(errors='ignore'))
                print("[PLAY ERROR] stderr:", stderr.decode(errors='ignore'))
            return "mpv"

        elif PLAYER_TYPE == "mpg123":
            # mpg123 播放器（树莓派老系统推荐）
            player_mode = "mpg123"
            # mpg123 音量范围 0-32768，volume 0-100 转换为 0-32768
            mpg123_volume = int(volume * 327.68)
            args = [AUDIO_PLAYER, "--gain", str(mpg123_volume), path]
            
            if loop:
                # mpg123 不支持内置循环，使用 shell 循环
                loop_script = f"while true; do {AUDIO_PLAYER} --gain {mpg123_volume} {path}; done"
                player_process = subprocess.Popen(
                    loop_script,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                player_process = subprocess.Popen(
                    args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            print("[PLAY] using mpg123:", " ".join(args) if not loop else loop_script)
            return "mpg123"

        elif PLAYER_TYPE == "ffmpeg":
            # ffmpeg 播放器（备选方案）
            player_mode = "ffmpeg"
            # ffmpeg 音量：-filter:a "volume=0.X" (0.0-1.0)
            volume_normalized = volume / 100.0
            args = [
                AUDIO_PLAYER,
                "-i", path,
                "-af", f"volume={volume_normalized}",
                "-f", "alsa",
                "default"
            ]
            
            if loop:
                # ffmpeg 循环需要脚本
                loop_script = f"while true; do {AUDIO_PLAYER} -i {path} -af volume={volume_normalized} -f alsa default; done"
                player_process = subprocess.Popen(
                    loop_script,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                player_process = subprocess.Popen(
                    args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            print("[PLAY] using ffmpeg:", " ".join(args) if not loop else loop_script)
            return "ffmpeg"

        elif PLAYER_TYPE == "startfile":
            # Windows 备选方案（如果没有 mpv）
            player_mode = "startfile"
            print("[PLAY] using os.startfile() on Windows")
            os.startfile(path)
            player_process = None
            return "startfile"

        else:
            raise RuntimeError(f"Unknown player type: {PLAYER_TYPE}")

    except Exception as e:
        raise RuntimeError(f"Failed to start player ({PLAYER_TYPE}): {e}")

# ============================================================
# 4) Handlers：每个命令一个函数
# ============================================================

def handle_play_music(data: Dict[str, Any]) -> Dict[str, Any]:
    path = resolve_music_path()
    volume = int(data.get("volume", 80))
    loop = bool(data.get("loop", True))

    print("[PLAY_MUSIC] resolved path:", path)
    mode = play_music(path, volume=volume, loop=loop)
    return {"ok": True, "msg": f"playing ({mode})", "path": path}

def handle_play_meditation(data: Dict[str, Any]) -> Dict[str, Any]:
    path = resolve_meditation_path()
    volume = int(data.get("volume", 80))
    loop = bool(data.get("loop", True))

    print("[PLAY_MEDITATION] resolved path:", path)
    mode = play_music(path, volume=volume, loop=loop)
    return {"ok": True, "msg": f"playing meditation ({mode})", "path": path}

def handle_spin_wheel(data: Dict[str, Any]) -> Dict[str, Any]:
    """处理转盘旋转指令"""
    sector = int(data.get("sector", 1))

    if sector < 1 or sector > 6:
        return {"ok": False, "msg": f"扇区编号必须在1-6之间，收到: {sector}"}

    # 发送串口命令到转盘
    if turntable_serial and turntable_serial.is_ready():
        success = turntable_serial.send_sector(sector)
        if success:
            print(f"[SPIN_WHEEL] 成功发送扇区 {sector} 到转盘")
            return {"ok": True, "msg": f"已发送扇区{sector}到转盘", "sector": sector}
        else:
            print(f"[SPIN_WHEEL] 串口发送失败")
            return {"ok": False, "msg": "串口发送失败", "sector": sector}
    else:
        print(f"[SPIN_WHEEL] 转盘串口未初始化，仅记录日志: 扇区 {sector}")
        return {"ok": False, "msg": "转盘串口未初始化", "sector": sector}

def handle_stop_music(data: Dict[str, Any]) -> Dict[str, Any]:
    ok, msg = stop_music()
    return {"ok": ok, "msg": msg}

def handle_ping(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"ok": True, "msg": "pong"}

# ============================================================
# 5) API：根路径和健康检查
# ============================================================

@app.get("/")
def root():
    """根路径，如果存在前端则返回前端页面，否则返回服务状态"""
    # 如果存在前端构建文件，返回前端页面
    if os.path.exists(FRONTEND_DIST):
        index_path = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)

    # 否则返回 API 状态信息
    return {
        "ok": True,
        "service": "Sleep Soothing System Backend",
        "version": "1.0.0",
        "endpoints": {
            "command": "/api/command (POST)",
            "sensors": "/api/sensors (GET)",
            "ws_sensors": "/ws/sensors (WebSocket)",
            "ws_eeg": "/ws/eeg (WebSocket)",
            "ping": "/api/command with cmd='PING'"
        },
        "player": {
            "type": PLAYER_TYPE or "NOT FOUND",
            "path": AUDIO_PLAYER or "NOT FOUND"
        }
    }

@app.get("/health")
def health():
    """健康检查接口"""
    return {"ok": True, "status": "healthy"}

# ============================================================
# 6) API：统一指令入口
# ============================================================

class LightPower(BaseModel):
    on: bool

class LightValue(BaseModel):
    value: float

@app.get("/api/light/state")
def light_state():
    state, err = _fetch_light_state()
    if state is None:
        return {"ok": False, "msg": err}

    attrs = state.get("attributes", {}) if isinstance(state, dict) else {}
    on = state.get("state") == "on"
    brightness = _normalize_brightness(attrs.get("brightness"))
    color_temp = _color_temp_percent(attrs)
    supported_modes = attrs.get("supported_color_modes") or []
    supports_color_temp = (
        "color_temp" in attrs
        or "color_temp_kelvin" in attrs
        or "color_temp" in supported_modes
    )

    return {
        "ok": True,
        "on": on,
        "brightness": brightness,
        "colorTemp": color_temp,
        "supportsColorTemp": supports_color_temp,
    }

@app.post("/api/light/power")
def light_power(payload: LightPower):
    if payload.on:
        ok, err = _ha_service("turn_on", {"entity_id": HA_ENTITY_ID})
    else:
        ok, err = _ha_service("turn_off", {"entity_id": HA_ENTITY_ID})
    if not ok:
        return {"ok": False, "msg": err}
    return {"ok": True, "on": payload.on}

@app.post("/api/light/brightness")
def light_brightness(payload: LightValue):
    value = float(payload.value)
    if value <= 0:
        ok, err = _ha_service("turn_off", {"entity_id": HA_ENTITY_ID})
        if not ok:
            return {"ok": False, "msg": err}
        return {"ok": True, "on": False, "brightness": 0}

    brightness = int(round(_clamp(value, 0, 100) / 100 * 255))
    if brightness < 1:
        brightness = 1
    ok, err = _ha_service("turn_on", {"entity_id": HA_ENTITY_ID, "brightness": brightness})
    if not ok:
        return {"ok": False, "msg": err}
    return {"ok": True, "on": True, "brightness": int(round(value))}

@app.post("/api/light/color_temp")
def light_color_temp(payload: LightValue):
    state, err = _fetch_light_state()
    if state is None:
        return {"ok": False, "msg": err}

    attrs = state.get("attributes", {}) if isinstance(state, dict) else {}
    ct_value = _color_temp_value_from_percent(attrs, payload.value)
    ok, err = _ha_service("turn_on", {"entity_id": HA_ENTITY_ID, "color_temp": ct_value})
    if not ok:
        return {"ok": False, "msg": err}
    return {"ok": True, "colorTemp": int(round(_clamp(payload.value, 0, 100)))}

class Command(BaseModel):
    cmd: str
    data: Optional[Dict[str, Any]] = None

class AssistantEvent(BaseModel):
    type: Literal["wake", "user_speaking", "thinking", "reply", "reply_done", "close"]
    text: Optional[str] = None

@app.post("/api/command")
def command(payload: Command):
    cmd = payload.cmd
    data: Dict[str, Any] = payload.data or {}

    print("\n========== COMMAND ==========")
    print("收到指令:", cmd, data)

    handler = HANDLERS.get(cmd)
    if handler is None:
        raise HTTPException(status_code=400, detail=f"Unknown cmd: {cmd}")

    try:
        return handler(data)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Handler error: {e}")

# ============================================================
# 6.1) API: AI Assistant 事件入口（供外部进程调用）
# ============================================================

@app.post("/api/assistant/event")
async def assistant_event(payload: AssistantEvent):
    await broadcast_assistant_event(payload.type, payload.text)
    return {"ok": True}

# ============================================================
# 7) API：传感器接口（先用模拟数据）
# ============================================================

@app.get("/api/sensors")
def sensors():
    """REST endpoint for sensor data (backward compatibility)."""
    data = None

    if sensor_reader:
        data = sensor_reader.get_data()
    else:
        temperature = round(20 + random.random() * 8, 2)
        humidity = round(40 + random.random() * 20, 2)
        co2 = round(400 + random.random() * 200, 1)
        data = {
            "temperature": temperature,
            "humidity": humidity,
            "co2": co2,
            "timestamp": int(time.time()),
            "connected": False,
            "error_message": "sensor not initialized",
        }

    if pm25_reader:
        pm = pm25_reader.get_data()
        data["pm25"] = pm.get("pm25")
        data["pm25_connected"] = pm.get("connected")
        data["pm25_error"] = pm.get("error_message")
    else:
        data["pm25"] = None
        data["pm25_connected"] = False
        data["pm25_error"] = ""

    return {"ok": True, "data": data}

# ============================================================
# 8) WebSocket: Real-time sensor data streaming
# ============================================================

# ============================================================
# AI Assistant WebSocket (供 main.py 调用)
# ============================================================
# 
# 使用方法 (在 ai_assistant/main.py 中):
# 
# from server import broadcast_assistant_event
# 
# # 检测到唤醒词 "困困" 时
# await broadcast_assistant_event("wake")
# 
# # 用户开始说话时
# await broadcast_assistant_event("user_speaking")
# 
# # LLM 开始思考时
# await broadcast_assistant_event("thinking")
# 
# # LLM 回复时（包含要显示的文字）
# await broadcast_assistant_event("reply", text="助手要说的内容")
# 
# # 语音播放完毕时
# await broadcast_assistant_event("reply_done")
# 
# # 检测到结束词 "困困再见" 时
# await broadcast_assistant_event("close")
# 
# ============================================================

# 存储所有连接的 AI 助手 WebSocket 客户端
assistant_clients: List[WebSocket] = []
ws_sensors_logged_connect = False
ws_sensors_logged_disconnect = False

async def broadcast_assistant_event(event_type: str, text: str = None):
    """
    向所有连接的前端客户端广播 AI 助手事件
    
    Args:
        event_type: 事件类型，可选值: "wake", "user_speaking", "thinking", "reply", "reply_done", "close"
        text: 当 event_type 为 "reply" 时，需要显示的文字内容
    """
    message = {"type": event_type}
    if text is not None:
        message["text"] = text
    
    message_json = json.dumps(message)
    
    # 复制列表以避免在迭代时修改
    clients_to_remove = []
    
    for client in assistant_clients:
        try:
            await client.send_text(message_json)
            print(f"[ASSISTANT WS] 广播事件: {event_type}" + (f", text: {text[:50]}..." if text and len(text) > 50 else (f", text: {text}" if text else "")))
        except Exception as e:
            print(f"[ASSISTANT WS] 发送失败，移除客户端: {e}")
            clients_to_remove.append(client)
    
    # 移除断开的客户端
    for client in clients_to_remove:
        if client in assistant_clients:
            assistant_clients.remove(client)

@app.websocket("/ws/assistant")
async def websocket_assistant(websocket: WebSocket):
    """
    AI 助手 WebSocket 端点
    前端连接此端点后，会收到来自 AI 助手的状态更新
    """
    await websocket.accept()
    assistant_clients.append(websocket)
    print(f"[ASSISTANT WS] 客户端已连接，当前连接数: {len(assistant_clients)}")
    
    try:
        # 保持连接，等待客户端断开
        while True:
            # 接收消息（主要用于保持连接和检测断开）
            try:
                data = await websocket.receive_text()
                # 可以在这里处理前端发来的消息（如果需要）
                print(f"[ASSISTANT WS] 收到前端消息: {data}")
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[ASSISTANT WS] 连接错误: {e}")
    finally:
        if websocket in assistant_clients:
            assistant_clients.remove(websocket)
        print(f"[ASSISTANT WS] 客户端断开，当前连接数: {len(assistant_clients)}")

# ============================================================
# EEG WebSocket: real-time EEG data + 30s inference
# ============================================================

EEG_SESSION_LOCK = threading.Lock()
EEG_SESSION_ACTIVE = False

@app.websocket("/ws/eeg")
async def websocket_eeg(websocket: WebSocket):
    await websocket.accept()
    global EEG_SESSION_ACTIVE

    with EEG_SESSION_LOCK:
        if EEG_SESSION_ACTIVE:
            await websocket.send_text(json.dumps({"type": "error", "message": "EEG session already active"}))
            await websocket.close()
            return
        EEG_SESSION_ACTIVE = True

    session = EEGSession(websocket, asyncio.get_event_loop())
    session.start()

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[EEG WS] Error: {e}")
    finally:
        session.stop()
        with EEG_SESSION_LOCK:
            EEG_SESSION_ACTIVE = False


@app.websocket("/ws/face")
async def websocket_face(websocket: WebSocket):
    await websocket.accept()

    if not face_service.is_available():
        await websocket.send_text(json.dumps({"type": "error", "message": "Face backend not ready"}, ensure_ascii=False))

    face_service.add_viewer()
    try:
        while True:
            await asyncio.sleep(1.0)
            result = face_service.get_result()
            await websocket.send_text(json.dumps({"type": "result", **result}, ensure_ascii=False))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[FACE WS] Error: {e}")
    finally:
        face_service.remove_viewer()


@app.get("/video/face")
def video_face():
    if not face_service.is_available():
        raise HTTPException(status_code=503, detail="Face backend not ready")
    return StreamingResponse(_face_mjpeg_generator(), media_type="multipart/x-mixed-replace; boundary=frame")
@app.websocket("/ws/sensors")
async def websocket_sensors(websocket: WebSocket):
    """
    WebSocket endpoint for real-time sensor data streaming.
    Sends sensor data every 2 seconds to match frontend update interval.
    """
    global ws_sensors_logged_connect, ws_sensors_logged_disconnect
    await websocket.accept()
    if not ws_sensors_logged_connect:
        print("[WS] Client connected to /ws/sensors")
        ws_sensors_logged_connect = True

    try:
        while True:
            # Get latest sensor data
            if sensor_reader:
                data = sensor_reader.get_data()
            else:
                # Fallback to mock data if sensor not available
                data = {
                    "co2": round(400 + random.random() * 200, 1),
                    "temperature": round(20 + random.random() * 8, 2),
                    "humidity": round(40 + random.random() * 20, 2),
                    "timestamp": time.time(),
                    "connected": False,
                    "error_message": "传感器未初始化"
                }

            # Send data to client
            if pm25_reader:
                pm = pm25_reader.get_data()
                data["pm25"] = pm.get("pm25")
                data["pm25_connected"] = pm.get("connected")
                data["pm25_error"] = pm.get("error_message")
            else:
                data["pm25"] = None
                data["pm25_connected"] = False
                data["pm25_error"] = ""

            await websocket.send_text(json.dumps({
                "ok": True,
                "data": data
            }))

            # Wait 2 seconds (match frontend update interval)
            await asyncio.sleep(2)

    except WebSocketDisconnect:
        if not ws_sensors_logged_disconnect:
            print("[WS] Client disconnected from /ws/sensors")
            ws_sensors_logged_disconnect = True
    except Exception as e:
        print(f"[WS] Error in websocket_sensors: {e}")
        try:
            await websocket.close()
        except:
            pass

# ============================================================
# 8) 启动时注册 handlers
# ============================================================

register_handlers()

# ============================================================
# 9) 启动时初始化传感器
# ============================================================

init_sensor_reader()

init_pm25_reader()

# ============================================================
# 10) 启动时初始化转盘串口
# ============================================================

init_turntable()

# ============================================================
# 9) 启动时打印环境信息（便于调试）
# ============================================================

print("\n" + "="*60)
print("SERVER START - Environment Detection")
print("="*60)
print(f"Platform: {platform.system()} {platform.release()}")
print(f"Python: {sys.version.split()[0]}")
print(f"BASE_DIR: {BASE_DIR}")
print(f"AUDIO_PLAYER: {AUDIO_PLAYER or 'NOT FOUND'}")
print(f"PLAYER_TYPE: {PLAYER_TYPE or 'NOT FOUND'}")
print(f"HARD_MUSIC_PATH: {HARD_MUSIC_PATH} (exists: {file_exists(HARD_MUSIC_PATH)})")
print(f"FALLBACK_MUSIC_PATH: {FALLBACK_MUSIC_PATH} (exists: {file_exists(FALLBACK_MUSIC_PATH)})")
print(f"HARD_MEDITATION_PATH: {HARD_MEDITATION_PATH} (exists: {file_exists(HARD_MEDITATION_PATH)})")
print(f"FALLBACK_MEDITATION_PATH: {FALLBACK_MEDITATION_PATH} (exists: {file_exists(FALLBACK_MEDITATION_PATH)})")
print(f"Registered handlers: {list(HANDLERS.keys())}")
print("="*60 + "\n")

# ============================================================
# 10) 前端静态文件服务（必须在所有 API 路由之后）
# ============================================================

# 如果存在前端构建文件，提供前端页面（SPA 路由支持）
if os.path.exists(FRONTEND_DIST):
    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        """
        提供前端页面（SPA 路由支持）
        注意：这个路由必须在所有 API 路由之后定义，否则会拦截 API 请求
        """
        # API 路径不处理（应该已经被上面的路由处理了）
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        
        # 静态资源文件（应该已经被 StaticFiles 处理了）
        if full_path.startswith("assets/"):
            raise HTTPException(status_code=404, detail="Static file not found")
        
        # 其他路径返回前端 index.html（支持 SPA 路由）
        index_path = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        else:
            raise HTTPException(status_code=404, detail="Frontend not found")
