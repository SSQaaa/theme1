#!/usr/bin/env python3
"""Lightweight EEG 3-class training script (LOSO, 30s evaluation)."""

import argparse
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple, Union

import numpy as np
from scipy.signal import butter, filtfilt, iirnotch, welch
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, recall_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

try:
    from joblib import dump as joblib_dump
except Exception:
    joblib_dump = None


FS = 250
EMOTIV_FS = 128
INNER_SEC_DEFAULT = 4.0
OUTER_SEC_DEFAULT = 30.0
OVERLAP_DEFAULT = 0.5
THRESHOLD_DEFAULT = 0.6
TRIM_FRAC_DEFAULT = 0.1

LEVEL_TO_CLASS = {
    "natural": "LOW",
    "lowlevel": "MID",
    "midlevel": "MID",
    "highlevel": "HIGH",
}
CLASS_TO_ID = {"LOW": 0, "MID": 1, "HIGH": 2}
ID_TO_CLASS = {0: "LOW", 1: "MID", 2: "HIGH"}

EMOTIV_TASK_MAP = {
    "arithmetic": "Maths",
    "maths": "Maths",
    "mirror_image": "Symmetry",
    "symmetry": "Symmetry",
    "stroop": "Stroop",
    "relax": "Relax",
    "relaxation": "Relax",
}

# Order matches user electrode order: O1, O2, FP1, FP2, C3, C4, P7, P8
EMOTIV_CHANNEL_IDX = [15, 18, 2, 31, 6, 27, 13, 20]  # 0-based indices


@dataclass
class Segment:
    subject_id: int
    label_id: int
    level: str
    task_type: str
    features: np.ndarray  # shape [n_windows, n_features]
    good_mask: np.ndarray  # shape [n_windows], True means good quality
    agg_features_base: np.ndarray  # shape [n_features_base]
    agg_features_ext: np.ndarray  # shape [n_features_ext]


@dataclass
class ModelBundle:
    kind: str  # "flat" or "hier"
    model: Optional[CalibratedClassifierCV] = None
    model_high: Optional[CalibratedClassifierCV] = None
    model_lowmid: Optional[CalibratedClassifierCV] = None
    feature_variant: str = "ext"


# ------------------------- Data Loading -------------------------

def _split_line(line: str, delim: str) -> List[str]:
    line = line.strip()
    if not line:
        return []
    if delim == " ":
        parts = re.split(r"\s+", line)
    else:
        parts = [p.strip() for p in line.split(delim)]
    return [p for p in parts if p != ""]


def _try_float(token: str) -> Optional[float]:
    try:
        return float(token)
    except Exception:
        return None


def _count_numeric(tokens: List[str]) -> int:
    return sum(1 for t in tokens if _try_float(t) is not None)


def _detect_delimiter(lines: List[str]) -> str:
    candidates = [",", ";", "\t", " "]
    best = None
    best_score = (-1, -1)  # (valid_lines, median_cols)
    for delim in candidates:
        lengths = []
        for line in lines:
            tokens = _split_line(line, delim)
            numeric_count = _count_numeric(tokens)
            if numeric_count >= 8:
                lengths.append(len(tokens))
        if not lengths:
            continue
        median_cols = int(np.median(lengths))
        score = (len(lengths), median_cols)
        if score > best_score:
            best_score = score
            best = delim
    return best if best is not None else " "


def _parse_level_and_subject(filename: str) -> Tuple[Optional[str], Optional[int]]:
    name = filename.lower()
    m = re.search(r"(natural|lowlevel|midlevel|highlevel)[-_]?(\d+)", name)
    if m:
        return m.group(1), int(m.group(2))
    # fallback: try to get digits only
    digits = re.findall(r"\d+", name)
    subject_id = int(digits[0]) if digits else None
    return None, subject_id


def _parse_task_type(path: str) -> str:
    p = path.lower()
    if "arithmetic_data" in p:
        return "Arithmetic"
    if "stroop_data" in p:
        return "Stroop"
    return "Unknown"


def _is_time_like_column(col: np.ndarray) -> bool:
    if col.size < 3:
        return False
    if not np.isfinite(col).all():
        return False
    diffs = np.diff(col)
    if not (np.all(diffs >= 0) or np.all(diffs <= 0)):
        return False
    col_centered = col - float(np.mean(col))
    idx = np.arange(col.size, dtype=np.float32)
    idx_centered = idx - float(np.mean(idx))
    denom = float(np.linalg.norm(col_centered) * np.linalg.norm(idx_centered))
    if denom < 1e-12:
        return False
    corr = float(np.dot(col_centered, idx_centered) / denom)
    return bool(np.isfinite(corr) and abs(corr) > 0.98)


def load_eeg_file(
    filepath: str, fs: int = FS
) -> Tuple[Optional[int], Optional[str], str, np.ndarray, float]:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.read().splitlines()

    sample_lines = [ln for ln in lines if ln.strip()][:50]
    delim = _detect_delimiter(sample_lines)

    rows: List[List[float]] = []
    max_len = 0
    for line in lines:
        if not line.strip():
            continue
        tokens = _split_line(line, delim)
        if not tokens:
            continue
        row: List[float] = []
        numeric_count = 0
        for tok in tokens:
            val = _try_float(tok)
            if val is None:
                row.append(np.nan)
            else:
                row.append(float(val))
                numeric_count += 1
        if numeric_count < 8:
            # likely header/metadata line
            continue
        max_len = max(max_len, len(row))
        rows.append(row)

    if not rows:
        raise ValueError("no numeric data rows found")

    data = np.full((len(rows), max_len), np.nan, dtype=np.float32)
    for i, row in enumerate(rows):
        data[i, : len(row)] = np.asarray(row, dtype=np.float32)

    if data.ndim != 2:
        raise ValueError("data is not 2D")

    # Drop columns with too many non-finite values (e.g., timestamps)
    finite_ratio = np.mean(np.isfinite(data), axis=0)
    keep_cols = finite_ratio >= 0.8
    data = data[:, keep_cols]

    # Clean NaN/Inf rows after column filtering
    mask = np.isfinite(data).all(axis=1)
    data = data[mask]
    if data.size == 0:
        raise ValueError("data contains no finite rows")

    ncols = data.shape[1]
    if ncols == 8:
        eeg = data
    elif ncols == 9:
        # Drop the most likely time/sample index column
        first_time = _is_time_like_column(data[:, 0])
        last_time = _is_time_like_column(data[:, -1])
        if first_time and not last_time:
            eeg = data[:, 1:]
        elif last_time and not first_time:
            eeg = data[:, :-1]
        else:
            eeg = data[:, 1:]
    elif ncols > 9:
        variances = np.var(data, axis=0)
        for i in range(ncols):
            col = data[:, i]
            if _is_time_like_column(col):
                variances[i] = 0.0
                continue
            if float(np.std(col)) < 1e-6:
                variances[i] = 0.0
        best_i = 0
        best_score = -1.0
        for i in range(0, ncols - 7):
            score = float(np.sum(variances[i : i + 8]))
            if score > best_score:
                best_score = score
                best_i = i
        eeg = data[:, best_i : best_i + 8]
    else:
        raise ValueError(f"unexpected column count: {ncols}")

    level, subject_id = _parse_level_and_subject(os.path.basename(filepath))
    task_type = _parse_task_type(filepath)
    duration_sec = float(eeg.shape[0]) / float(fs)
    return subject_id, level, task_type, eeg, duration_sec


def _parse_emotiv_filename(filename: str) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    name = filename.lower()
    m = re.search(r"([a-z_]+)_sub_(\d+)_trial(\d+)", name)
    if not m:
        return None, None, None
    task = m.group(1)
    subject_id = int(m.group(2))
    trial_id = int(m.group(3))
    return task, subject_id, trial_id


def load_emotiv_mat(filepath: str, channel_idx: List[int]) -> np.ndarray:
    try:
        import scipy.io as sio  # type: ignore
    except Exception as exc:
        raise RuntimeError("scipy is required to read .mat files") from exc

    mat = sio.loadmat(filepath)
    if "Data" in mat:
        data = mat["Data"]
    elif "Clean_data" in mat:
        data = mat["Clean_data"]
    else:
        raise ValueError("missing Data/Clean_data field in .mat")
    if data.ndim != 2:
        raise ValueError("Data is not 2D")
    if data.shape[0] == 32:
        eeg = data[channel_idx, :]
    elif data.shape[1] == 32:
        eeg = data[:, channel_idx].T
    else:
        raise ValueError("unexpected Data shape")
    return eeg.T.astype(np.float32)


def load_emotiv_scales(scales_path: str) -> Dict[Tuple[int, int, str], int]:
    try:
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("pandas is required to read scales.xls") from exc

    df = pd.read_excel(scales_path)
    cols = list(df.columns)
    if len(cols) < 4:
        raise ValueError("unexpected scales.xls format")

    # Identify header row where Subject No. is NaN
    header_row = df[df[cols[0]].isna()]
    task_labels = None
    if not header_row.empty:
        header_values = header_row.iloc[0].tolist()
        task_labels = header_values[1:]

    # Chunk columns after subject into trials of 3 tasks
    task_map = {}
    task_cols = cols[1:]
    if task_labels is None:
        task_labels = ["Maths", "Symmetry", "Stroop"] * 3

    for row_idx, row in df.iterrows():
        subject_val = row[cols[0]]
        if subject_val != subject_val:
            continue
        try:
            subject_id = int(subject_val)
        except Exception:
            continue
        for i in range(0, len(task_cols), 3):
            trial_id = i // 3 + 1
            for j in range(3):
                col = task_cols[i + j]
                task = str(task_labels[i + j]).strip()
                try:
                    rating = int(row[col])
                except Exception:
                    continue
                task_map[(subject_id, trial_id, task)] = rating

    return task_map


def rating_to_label(rating: int) -> str:
    if rating <= 3:
        return "LOW"
    if rating <= 7:
        return "MID"
    return "HIGH"


def iter_eeg_files(data_root: str) -> Iterable[str]:
    for root, _, files in os.walk(data_root):
        for name in files:
            if name.lower().endswith(".txt"):
                yield os.path.join(root, name)


def iter_emotiv_files(data_root: str) -> Iterable[str]:
    for root, _, files in os.walk(data_root):
        for name in files:
            if name.lower().endswith(".mat"):
                yield os.path.join(root, name)


def summarize_dataset(data_root: str, fs: int = FS) -> None:
    class_counts = defaultdict(int)
    subject_counts = defaultdict(int)
    class_durations = defaultdict(list)
    anomalies = []

    for path in iter_eeg_files(data_root):
        try:
            subject_id, level, task_type, eeg, duration = load_eeg_file(path, fs=fs)
        except Exception as exc:
            anomalies.append((path, str(exc)))
            continue

        if level is None or level not in LEVEL_TO_CLASS:
            anomalies.append((path, "cannot parse level"))
            continue
        if subject_id is None:
            anomalies.append((path, "cannot parse subject_id"))
            continue

        class_name = LEVEL_TO_CLASS[level]
        class_counts[class_name] += 1
        subject_counts[subject_id] += 1
        class_durations[class_name].append(duration)

    print("Dataset summary")
    print("- samples per class:")
    for k in ["LOW", "MID", "HIGH"]:
        print(f"  {k}: {class_counts.get(k, 0)}")
    print("- samples per subject:")
    for sid in sorted(subject_counts.keys()):
        print(f"  subject {sid}: {subject_counts[sid]}")
    print("- avg duration per class (sec):")
    for k in ["LOW", "MID", "HIGH"]:
        vals = class_durations.get(k, [])
        avg = float(np.mean(vals)) if vals else 0.0
        print(f"  {k}: {avg:.2f}")

    if anomalies:
        print("- anomalous files:")
        for path, reason in anomalies:
            print(f"  {path} -> {reason}")


def summarize_dataset_emotiv(
    data_root: str,
    scales_path: str,
    fs: int,
    include_relax: bool,
) -> None:
    class_counts = defaultdict(int)
    subject_counts = defaultdict(int)
    class_durations = defaultdict(list)
    anomalies = []

    scale_map = load_emotiv_scales(scales_path)

    for path in iter_emotiv_files(data_root):
        try:
            task, subject_id, trial_id = _parse_emotiv_filename(os.path.basename(path))
            if task is None or subject_id is None or trial_id is None:
                anomalies.append((path, "cannot parse filename"))
                continue
            task_key = EMOTIV_TASK_MAP.get(task, None)
            if task_key is None:
                anomalies.append((path, "unknown task"))
                continue
            if task_key == "Relax" and not include_relax:
                continue
            if task_key == "Relax":
                class_name = "LOW"
            else:
                rating = scale_map.get((subject_id, trial_id, task_key))
                if rating is None:
                    anomalies.append((path, "missing rating"))
                    continue
                class_name = rating_to_label(int(rating))

            eeg = load_emotiv_mat(path, EMOTIV_CHANNEL_IDX)
            duration = float(eeg.shape[0]) / float(fs)
        except Exception as exc:
            anomalies.append((path, str(exc)))
            continue

        class_counts[class_name] += 1
        subject_counts[subject_id] += 1
        class_durations[class_name].append(duration)

    print("Dataset summary")
    print("- samples per class:")
    for k in ["LOW", "MID", "HIGH"]:
        print(f"  {k}: {class_counts.get(k, 0)}")
    print("- samples per subject:")
    for sid in sorted(subject_counts.keys()):
        print(f"  subject {sid}: {subject_counts[sid]}")
    print("- avg duration per class (sec):")
    for k in ["LOW", "MID", "HIGH"]:
        vals = class_durations.get(k, [])
        avg = float(np.mean(vals)) if vals else 0.0
        print(f"  {k}: {avg:.2f}")

    if anomalies:
        print("- anomalous files:")
        for path, reason in anomalies:
            print(f"  {path} -> {reason}")


# ------------------------- Preprocessing -------------------------

def apply_filters(eeg: np.ndarray, fs: int = FS) -> np.ndarray:
    nyq = 0.5 * fs
    b_notch, a_notch = iirnotch(50.0 / nyq, Q=30.0)
    b_band, a_band = butter(4, [1.0 / nyq, 40.0 / nyq], btype="band")
    # Zero-phase filtering per channel
    filtered = filtfilt(b_notch, a_notch, eeg, axis=0)
    filtered = filtfilt(b_band, a_band, filtered, axis=0)
    return filtered


def _bandpower_from_psd(f: np.ndarray, pxx: np.ndarray, band: Tuple[float, float]) -> float:
    idx = (f >= band[0]) & (f < band[1])
    if not np.any(idx):
        return 0.0
    # numpy >=2.0 may not expose trapz; use trapezoid
    return float(np.trapz(pxx[idx], f[idx]))


def extract_features(window: np.ndarray, fs: int = FS) -> np.ndarray:
    # Features per channel: theta/alpha/beta abs+rel + alpha/beta + theta/beta
    eps = 1e-12
    feats: List[float] = []
    nperseg = min(512, window.shape[0])
    for ch in range(window.shape[1]):
        x = window[:, ch]
        f, pxx = welch(x, fs=fs, nperseg=nperseg)
        total = _bandpower_from_psd(f, pxx, (1.0, 40.0)) + eps
        theta = _bandpower_from_psd(f, pxx, (4.0, 8.0))
        alpha = _bandpower_from_psd(f, pxx, (8.0, 13.0))
        beta = _bandpower_from_psd(f, pxx, (13.0, 30.0))
        theta_rel = theta / total
        alpha_rel = alpha / total
        beta_rel = beta / total
        log_theta = np.log10(theta + eps)
        log_alpha = np.log10(alpha + eps)
        log_beta = np.log10(beta + eps)
        log_alpha_beta = log_alpha - log_beta
        log_theta_beta = log_theta - log_beta
        feats.extend(
            [
                log_theta,
                log_alpha,
                log_beta,
                theta_rel,
                alpha_rel,
                beta_rel,
                log_alpha_beta,
                log_theta_beta,
            ]
        )
    return np.asarray(feats, dtype=np.float32)


def segment_to_features(
    segment: np.ndarray, fs: int, inner_sec: float, overlap: float
) -> Tuple[np.ndarray, np.ndarray]:
    win = int(round(inner_sec * fs))
    step = int(round(win * (1.0 - overlap)))
    if step <= 0:
        raise ValueError("overlap too high; step <= 0")
    feats = []
    median_stds: List[float] = []
    median_ptps: List[float] = []
    flat_flags: List[bool] = []
    for start in range(0, segment.shape[0] - win + 1, step):
        window = segment[start : start + win]
        feats.append(extract_features(window, fs=fs))
        stds = np.std(window, axis=0)
        ptp = np.ptp(window, axis=0)
        median_stds.append(float(np.median(stds)))
        median_ptps.append(float(np.median(ptp)))
        flat_flags.append(bool(np.any(stds < 1e-6)))
    if not feats:
        return np.empty((0, 0), dtype=np.float32), np.empty((0,), dtype=bool)
    features = np.vstack(feats)

    n_windows = features.shape[0]
    good_mask = np.ones(n_windows, dtype=bool)
    if n_windows >= 3:
        eps = 1e-12
        std_arr = np.asarray(median_stds, dtype=np.float32)
        ptp_arr = np.asarray(median_ptps, dtype=np.float32)
        med_std = float(np.median(std_arr))
        med_ptp = float(np.median(ptp_arr))
        mad_std = float(np.median(np.abs(std_arr - med_std))) + eps
        mad_ptp = float(np.median(np.abs(ptp_arr - med_ptp))) + eps
        z_std = np.abs((std_arr - med_std) / (1.4826 * mad_std))
        z_ptp = np.abs((ptp_arr - med_ptp) / (1.4826 * mad_ptp))
        flat_arr = np.asarray(flat_flags, dtype=bool)
        good_mask = (z_std <= 6.0) & (z_ptp <= 6.0) & (~flat_arr)

    return features, good_mask


def aggregate_segment_features(
    window_features: np.ndarray,
    good_mask: np.ndarray,
    task_type: str,
    trim_frac: float = TRIM_FRAC_DEFAULT,
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    if window_features.size == 0:
        return None, None
    if good_mask.size > 0 and np.any(good_mask):
        feats = window_features[good_mask]
    else:
        feats = window_features
    if feats.size == 0:
        return None, None
    mean = np.mean(feats, axis=0)
    std = np.std(feats, axis=0)
    median = np.median(feats, axis=0)
    base = np.concatenate([mean, std, median]).astype(np.float32)
    q1 = np.percentile(feats, 25, axis=0)
    q3 = np.percentile(feats, 75, axis=0)
    iqr = q3 - q1
    trim_frac = float(np.clip(trim_frac, 0.0, 0.4))
    if feats.shape[0] >= 5 and trim_frac > 0.0:
        k = int(np.floor(feats.shape[0] * trim_frac))
        if k > 0 and feats.shape[0] - 2 * k >= 1:
            sorted_feats = np.sort(feats, axis=0)
            trimmed = sorted_feats[k : feats.shape[0] - k]
            tmean = np.mean(trimmed, axis=0)
        else:
            tmean = mean
    else:
        tmean = mean

    task_lower = task_type.lower()
    task_onehot = None
    if task_lower in ["maths", "symmetry", "stroop", "relax"]:
        task_onehot = np.zeros(4, dtype=np.float32)
        if task_lower == "maths":
            task_onehot[0] = 1.0
        elif task_lower == "symmetry":
            task_onehot[1] = 1.0
        elif task_lower == "stroop":
            task_onehot[2] = 1.0
        elif task_lower == "relax":
            task_onehot[3] = 1.0
    else:
        task_onehot = np.zeros(2, dtype=np.float32)
        if task_lower == "arithmetic":
            task_onehot[0] = 1.0
        elif task_lower == "stroop":
            task_onehot[1] = 1.0

    ext = np.concatenate([mean, std, median, iqr, tmean, task_onehot]).astype(
        np.float32
    )
    return base, ext


def _split_outer_segments(eeg: np.ndarray, outer_sec: float, fs: int) -> Iterable[np.ndarray]:
    outer_len = int(round(outer_sec * fs))
    n_seg = eeg.shape[0] // outer_len
    for i in range(n_seg):
        yield eeg[i * outer_len : (i + 1) * outer_len]


# ------------------------- Modeling -------------------------

def train_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    model_type: str = "svm",
    svm_params: Optional[Dict[str, float]] = None,
    random_state: int = 42,
) -> CalibratedClassifierCV:
    if model_type == "svm":
        params = svm_params or {"C": 1.0, "gamma": "scale"}
        base = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "svm",
                    SVC(
                        kernel="rbf",
                        C=float(params.get("C", 1.0)),
                        gamma=params.get("gamma", "scale"),
                        class_weight="balanced",
                    ),
                ),
            ]
        )
    elif model_type == "rf":
        base = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "rf",
                    RandomForestClassifier(
                        n_estimators=300,
                        max_depth=None,
                        random_state=random_state,
                        class_weight="balanced",
                        n_jobs=-1,
                    ),
                ),
            ]
        )
    else:
        raise ValueError("model_type must be 'svm' or 'rf'")

    try:
        clf = CalibratedClassifierCV(estimator=base, method="sigmoid", cv=3)
    except TypeError:
        clf = CalibratedClassifierCV(base_estimator=base, method="sigmoid", cv=3)
    clf.fit(X_train, y_train)
    return clf


def build_segment_dataset(
    segments: List[Segment],
    feature_variant: str,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    X_list = []
    y_list = []
    g_list = []
    for seg in segments:
        if feature_variant == "base":
            feats = seg.agg_features_base
        else:
            feats = seg.agg_features_ext
        if feats.size == 0:
            continue
        X_list.append(feats)
        y_list.append(seg.label_id)
        g_list.append(seg.subject_id)
    if not X_list:
        return (
            np.empty((0, 0), dtype=np.float32),
            np.empty((0,), dtype=np.int64),
            np.empty((0,), dtype=np.int64),
        )
    X = np.vstack(X_list)
    y = np.asarray(y_list, dtype=np.int64)
    groups = np.asarray(g_list, dtype=np.int64)
    return X, y, groups


def tune_svm_params_segment(
    X: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    inner_splits: int = 3,
    labels: Optional[List[int]] = None,
) -> Dict[str, float]:
    if X.size == 0:
        return {"C": 1.0, "gamma": "scale"}
    unique_groups = np.unique(groups)
    if unique_groups.size < 2:
        return {"C": 1.0, "gamma": "scale"}

    c_grid = [0.05, 0.1, 1.0, 10.0, 100.0]
    gamma_grid = ["scale", 0.1, 0.01, 0.001]
    best_score = -1.0
    best_params = {"C": 1.0, "gamma": "scale"}

    n_splits = min(inner_splits, unique_groups.size)
    splitter = GroupKFold(n_splits=n_splits)

    label_list = labels or sorted(list(set(y.tolist())))

    for c_val in c_grid:
        for g_val in gamma_grid:
            scores = []
            for train_idx, val_idx in splitter.split(X, y, groups):
                base = Pipeline(
                    [
                        ("scaler", StandardScaler()),
                        (
                            "svm",
                            SVC(
                                kernel="rbf",
                                C=float(c_val),
                                gamma=g_val,
                                class_weight="balanced",
                            ),
                        ),
                    ]
                )
                base.fit(X[train_idx], y[train_idx])
                y_pred = base.predict(X[val_idx])
                scores.append(
                    f1_score(y[val_idx], y_pred, average="macro", labels=label_list)
                )
            if scores:
                score = float(np.mean(scores))
                if score > best_score:
                    best_score = score
                    best_params = {"C": float(c_val), "gamma": g_val}

    return best_params


def select_best_config(
    train_segments: List[Segment],
    model_type: str,
    candidates: List[Tuple[str, str]],
) -> Tuple[str, str]:
    groups = np.asarray([s.subject_id for s in train_segments], dtype=np.int64)
    unique_groups = np.unique(groups)
    if unique_groups.size < 2:
        return candidates[0]

    splitter = GroupKFold(n_splits=min(3, unique_groups.size))
    best_score = -1.0
    best_cfg = candidates[0]

    for mode, variant in candidates:
        scores = []
        for train_idx, val_idx in splitter.split(train_segments, groups=groups):
            train_fold = [train_segments[i] for i in train_idx]
            val_fold = [train_segments[i] for i in val_idx]
            try:
                if mode == "flat":
                    model_bundle = train_flat_model(
                        train_fold, model_type=model_type, tune=False, feature_variant=variant
                    )
                else:
                    model_bundle = train_hierarchical_model(
                        train_fold, model_type=model_type, tune=False, feature_variant=variant
                    )
            except ValueError:
                continue
            metrics = evaluate_segments(model_bundle, val_fold, threshold=0.0)
            scores.append(metrics["acc"])
        if scores:
            score = float(np.mean(scores))
            if score > best_score:
                best_score = score
                best_cfg = (mode, variant)

    return best_cfg


def train_flat_model(
    train_segments: List[Segment],
    model_type: str,
    tune: bool,
    feature_variant: str,
) -> ModelBundle:
    X, y, groups = build_segment_dataset(train_segments, feature_variant)
    if X.size == 0:
        raise ValueError("no training segments available")
    svm_params = None
    if model_type == "svm" and tune:
        svm_params = tune_svm_params_segment(X, y, groups, inner_splits=3)
    model = train_model(X, y, model_type=model_type, svm_params=svm_params)
    return ModelBundle(kind="flat", model=model, feature_variant=feature_variant)


def train_hierarchical_model(
    train_segments: List[Segment],
    model_type: str,
    tune: bool,
    feature_variant: str,
) -> ModelBundle:
    X, y, groups = build_segment_dataset(train_segments, feature_variant)
    if X.size == 0:
        raise ValueError("no training segments available")

    high_id = CLASS_TO_ID["HIGH"]
    y_high = (y == high_id).astype(np.int64)
    if np.unique(y_high).size < 2:
        return train_flat_model(
            train_segments, model_type=model_type, tune=tune, feature_variant=feature_variant
        )

    svm_params_high = None
    if model_type == "svm" and tune:
        svm_params_high = tune_svm_params_segment(
            X, y_high, groups, inner_splits=3, labels=[0, 1]
        )
    model_high = train_model(X, y_high, model_type=model_type, svm_params=svm_params_high)

    mask_lm = y != high_id
    X_lm = X[mask_lm]
    y_lm = y[mask_lm]
    groups_lm = groups[mask_lm]
    if X_lm.size == 0 or np.unique(y_lm).size < 2:
        return train_flat_model(
            train_segments, model_type=model_type, tune=tune, feature_variant=feature_variant
        )

    y_lm_bin = (y_lm == CLASS_TO_ID["MID"]).astype(np.int64)
    svm_params_lm = None
    if model_type == "svm" and tune:
        svm_params_lm = tune_svm_params_segment(
            X_lm, y_lm_bin, groups_lm, inner_splits=3, labels=[0, 1]
        )
    model_lowmid = train_model(X_lm, y_lm_bin, model_type=model_type, svm_params=svm_params_lm)

    return ModelBundle(
        kind="hier",
        model_high=model_high,
        model_lowmid=model_lowmid,
        feature_variant=feature_variant,
    )


def _expand_probs(probs: np.ndarray, classes: np.ndarray) -> np.ndarray:
    out = np.zeros(3, dtype=np.float32)
    for i, cls in enumerate(classes):
        out[int(cls)] = float(probs[i])
    return out


def _get_segment_features(segment: Segment, feature_variant: str) -> np.ndarray:
    if feature_variant == "base":
        return segment.agg_features_base
    return segment.agg_features_ext


def predict_segment_proba(model_bundle: ModelBundle, features: np.ndarray) -> np.ndarray:
    if model_bundle.kind == "flat":
        model = model_bundle.model
        probs = model.predict_proba(features.reshape(1, -1))[0]
        return _expand_probs(probs, model.classes_)

    model_high = model_bundle.model_high
    model_lowmid = model_bundle.model_lowmid
    probs_high = model_high.predict_proba(features.reshape(1, -1))[0]
    classes_high = model_high.classes_
    idx_high = int(np.where(classes_high == 1)[0][0])
    p_high = float(probs_high[idx_high])

    probs_lm = model_lowmid.predict_proba(features.reshape(1, -1))[0]
    classes_lm = model_lowmid.classes_
    idx_mid = int(np.where(classes_lm == 1)[0][0])
    idx_low = int(np.where(classes_lm == 0)[0][0])
    p_low = float(probs_lm[idx_low]) * (1.0 - p_high)
    p_mid = float(probs_lm[idx_mid]) * (1.0 - p_high)
    return np.asarray([p_low, p_mid, p_high], dtype=np.float32)


def _get_model_feature_dim(model_bundle: ModelBundle) -> Optional[int]:
    model = model_bundle.model if model_bundle.kind == "flat" else model_bundle.model_high
    if model is None:
        return None
    if hasattr(model, "calibrated_classifiers_") and model.calibrated_classifiers_:
        est = model.calibrated_classifiers_[0].estimator
        if hasattr(est, "n_features_in_"):
            return int(est.n_features_in_)
        if hasattr(est, "named_steps"):
            scaler = est.named_steps.get("scaler")
            if scaler is not None and hasattr(scaler, "n_features_in_"):
                return int(scaler.n_features_in_)
    if hasattr(model, "n_features_in_"):
        return int(model.n_features_in_)
    return None


def evaluate_segments(
    model_bundle: ModelBundle,
    segments: List[Segment],
    threshold: float,
) -> Dict[str, Union[float, np.ndarray]]:
    y_true: List[int] = []
    y_pred: List[int] = []
    y_pred_rej: List[int] = []

    for seg in segments:
        feats = _get_segment_features(seg, model_bundle.feature_variant)
        if feats.size == 0:
            continue
        mean_prob = predict_segment_proba(model_bundle, feats)
        pred = int(np.argmax(mean_prob))
        y_true.append(seg.label_id)
        y_pred.append(pred)
        if float(np.max(mean_prob)) < threshold:
            y_pred_rej.append(-1)
        else:
            y_pred_rej.append(pred)

    if not y_true:
        return {
            "acc": 0.0,
            "macro_f1": 0.0,
            "recall": np.zeros(3, dtype=np.float32),
            "coverage": 0.0,
            "acc_covered": 0.0,
        }

    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", labels=[0, 1, 2]))
    recall = recall_score(y_true, y_pred, average=None, labels=[0, 1, 2])

    covered_idx = [i for i, p in enumerate(y_pred_rej) if p != -1]
    coverage = float(len(covered_idx)) / float(len(y_true))
    if covered_idx:
        y_true_cov = [y_true[i] for i in covered_idx]
        y_pred_cov = [y_pred_rej[i] for i in covered_idx]
        acc_covered = float(accuracy_score(y_true_cov, y_pred_cov))
    else:
        acc_covered = 0.0

    return {
        "acc": acc,
        "macro_f1": macro_f1,
        "recall": recall,
        "coverage": coverage,
        "acc_covered": acc_covered,
    }


# ------------------------- Build Dataset -------------------------

def resolve_data_root(path: str) -> str:
    if os.path.isdir(os.path.join(path, "Arithmetic_Data")):
        return path
    if os.path.isdir(os.path.join(path, "raw_data", "Arithmetic_Data")):
        return os.path.join(path, "raw_data")
    return path


def resolve_emotiv_root(base: str, source: str) -> str:
    if os.path.isdir(os.path.join(base, source)):
        return os.path.join(base, source)
    return base


def build_segments(
    data_root: str,
    fs: int,
    inner_sec: float,
    outer_sec: float,
    overlap: float,
) -> Tuple[List[Segment], List[Tuple[str, str]]]:
    segments: List[Segment] = []
    anomalies: List[Tuple[str, str]] = []

    for path in iter_eeg_files(data_root):
        try:
            subject_id, level, task_type, eeg, duration = load_eeg_file(path, fs=fs)
        except Exception as exc:
            anomalies.append((path, str(exc)))
            continue

        if subject_id is None or level is None:
            anomalies.append((path, "missing subject_id or level"))
            continue
        if level not in LEVEL_TO_CLASS:
            anomalies.append((path, "unknown level"))
            continue

        class_name = LEVEL_TO_CLASS[level]
        label_id = CLASS_TO_ID[class_name]

        if eeg.shape[0] < int(round(outer_sec * fs)):
            anomalies.append((path, "shorter than outer window"))
            continue

        try:
            eeg = apply_filters(eeg, fs=fs)
        except Exception as exc:
            anomalies.append((path, f"filter failed: {exc}"))
            continue

        for seg in _split_outer_segments(eeg, outer_sec, fs):
            feats, good_mask = segment_to_features(
                seg, fs=fs, inner_sec=inner_sec, overlap=overlap
            )
            if feats.size == 0:
                continue
            agg_base, agg_ext = aggregate_segment_features(feats, good_mask, task_type)
            if agg_base is None or agg_ext is None:
                continue
            segments.append(
                Segment(
                    subject_id=subject_id,
                    label_id=label_id,
                    level=level,
                    task_type=task_type,
                    features=feats,
                    good_mask=good_mask,
                    agg_features_base=agg_base,
                    agg_features_ext=agg_ext,
                )
            )

    return segments, anomalies


def build_segments_emotiv(
    data_root: str,
    scales_path: str,
    fs: int,
    inner_sec: float,
    outer_sec: float,
    overlap: float,
    include_relax: bool,
    apply_filter: bool,
) -> Tuple[List[Segment], List[Tuple[str, str]]]:
    segments: List[Segment] = []
    anomalies: List[Tuple[str, str]] = []

    scale_map = load_emotiv_scales(scales_path)

    for path in iter_emotiv_files(data_root):
        try:
            task, subject_id, trial_id = _parse_emotiv_filename(os.path.basename(path))
            if task is None or subject_id is None or trial_id is None:
                anomalies.append((path, "cannot parse filename"))
                continue
            task_key = EMOTIV_TASK_MAP.get(task, None)
            if task_key is None:
                anomalies.append((path, "unknown task"))
                continue
            if task_key == "Relax" and not include_relax:
                continue
            if task_key == "Relax":
                class_name = "LOW"
            else:
                rating = scale_map.get((subject_id, trial_id, task_key))
                if rating is None:
                    anomalies.append((path, "missing rating"))
                    continue
                class_name = rating_to_label(int(rating))

            label_id = CLASS_TO_ID[class_name]
            eeg = load_emotiv_mat(path, EMOTIV_CHANNEL_IDX)
            if eeg.shape[0] < int(round(outer_sec * fs)):
                anomalies.append((path, "shorter than outer window"))
                continue
            if apply_filter:
                eeg = apply_filters(eeg, fs=fs)
        except Exception as exc:
            anomalies.append((path, str(exc)))
            continue

        for seg in _split_outer_segments(eeg, outer_sec, fs):
            feats, good_mask = segment_to_features(
                seg, fs=fs, inner_sec=inner_sec, overlap=overlap
            )
            if feats.size == 0:
                continue
            agg_base, agg_ext = aggregate_segment_features(
                feats, good_mask, task_key
            )
            if agg_base is None or agg_ext is None:
                continue
            segments.append(
                Segment(
                    subject_id=subject_id,
                    label_id=label_id,
                    level=class_name.lower(),
                    task_type=task_key,
                    features=feats,
                    good_mask=good_mask,
                    agg_features_base=agg_base,
                    agg_features_ext=agg_ext,
                )
            )

    return segments, anomalies


# ------------------------- Inference -------------------------

def predict_30s(
    eeg_array: np.ndarray,
    model: Union[ModelBundle, CalibratedClassifierCV],
    fs: int = FS,
    inner_sec: float = INNER_SEC_DEFAULT,
    overlap: float = OVERLAP_DEFAULT,
    threshold: float = THRESHOLD_DEFAULT,
    task_type: str = "Unknown",
    feature_variant: str = "ext",
    force_label: bool = True,
) -> Dict[str, Union[float, str]]:
    expected_len = int(round(30.0 * fs))
    if eeg_array.shape != (expected_len, 8):
        raise ValueError("eeg_array must have shape [7500, 8]")

    eeg_filt = apply_filters(eeg_array, fs=fs)
    feats, good_mask = segment_to_features(
        eeg_filt, fs=fs, inner_sec=inner_sec, overlap=overlap
    )
    if feats.size == 0:
        raise ValueError("no valid windows for prediction")
    agg_base, agg_ext = aggregate_segment_features(feats, good_mask, task_type)
    if agg_base is None or agg_ext is None:
        raise ValueError("no valid windows for prediction")
    model_bundle = model if isinstance(model, ModelBundle) else ModelBundle(
        kind="flat", model=model, feature_variant=feature_variant
    )
    feats_seg = agg_base if model_bundle.feature_variant == "base" else agg_ext
    expected_dim = _get_model_feature_dim(model_bundle)
    if expected_dim is not None and feats_seg.size != expected_dim:
        if feats_seg.size < expected_dim:
            pad = np.zeros(expected_dim - feats_seg.size, dtype=feats_seg.dtype)
            feats_seg = np.concatenate([feats_seg, pad])
        else:
            feats_seg = feats_seg[:expected_dim]
    mean_prob = predict_segment_proba(model_bundle, feats_seg)
    pred_id = int(np.argmax(mean_prob))
    max_prob = float(np.max(mean_prob))

    label = ID_TO_CLASS[pred_id]
    if not force_label and max_prob < threshold:
        label = "UNCERTAIN"

    return {
        "label": label,
        "prob_low": float(mean_prob[0]),
        "prob_mid": float(mean_prob[1]),
        "prob_high": float(mean_prob[2]),
        "confidence": max_prob,
    }


# ------------------------- Main -------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="EEG 3-class LOSO training script")
    parser.add_argument(
        "--data_dir",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "dataset", "raw_data"),
        help="Path to dataset root (contains Arithmetic_Data/Stroop_Data)",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="auto",
        choices=["auto", "openbci", "emotiv"],
        help="Dataset type: auto/openbci/emotiv",
    )
    parser.add_argument(
        "--emotiv_source",
        type=str,
        default="filtered_data",
        choices=["raw_data", "filtered_data"],
        help="Emotiv data source folder",
    )
    parser.add_argument(
        "--no_relax",
        action="store_true",
        help="Exclude Relax trials (Emotiv only)",
    )
    parser.add_argument("--model", type=str, default="svm", choices=["svm", "rf"])
    parser.add_argument(
        "--no_tune",
        action="store_true",
        help="Disable SVM hyperparameter tuning (default: tuned)",
    )
    parser.add_argument(
        "--flat",
        action="store_true",
        help="Use a single flat 3-class model (default: hierarchical)",
    )
    parser.add_argument(
        "--feature_variant",
        type=str,
        default="auto",
        choices=["auto", "base", "ext"],
        help="Segment feature set: auto/base/ext (default: auto)",
    )
    parser.add_argument(
        "--save_model",
        action="store_true",
        help="Save final model trained on all data",
    )
    parser.add_argument(
        "--model_out_dir",
        type=str,
        default=os.path.dirname(__file__),
        help="Output directory for saved model",
    )
    parser.add_argument(
        "--model_out_prefix",
        type=str,
        default="model_bundle_acc",
        help="Prefix for saved model filename",
    )
    parser.add_argument("--inner_window", type=float, default=INNER_SEC_DEFAULT)
    parser.add_argument("--outer_window", type=float, default=None)
    parser.add_argument("--overlap", type=float, default=OVERLAP_DEFAULT)
    parser.add_argument("--threshold", type=float, default=THRESHOLD_DEFAULT)
    args = parser.parse_args()

    dataset = args.dataset
    if dataset == "auto":
        if os.path.isfile(os.path.join(args.data_dir, "scales.xls")):
            dataset = "emotiv"
        else:
            dataset = "openbci"

    if dataset == "emotiv":
        fs = EMOTIV_FS
        outer_window = args.outer_window if args.outer_window is not None else 25.0
        data_root = resolve_emotiv_root(args.data_dir, args.emotiv_source)
        scales_path = os.path.join(os.path.dirname(data_root), "scales.xls")
        print(f"Using data root: {data_root}")
        include_relax = not args.no_relax
        summarize_dataset_emotiv(
            data_root=data_root,
            scales_path=scales_path,
            fs=fs,
            include_relax=include_relax,
        )
        print("Building segments...")
        segments, anomalies = build_segments_emotiv(
            data_root=data_root,
            scales_path=scales_path,
            fs=fs,
            inner_sec=args.inner_window,
            outer_sec=outer_window,
            overlap=args.overlap,
            include_relax=include_relax,
            apply_filter=(args.emotiv_source == "raw_data"),
        )
    else:
        fs = FS
        outer_window = args.outer_window if args.outer_window is not None else OUTER_SEC_DEFAULT
        data_root = resolve_data_root(args.data_dir)
        print(f"Using data root: {data_root}")
        summarize_dataset(data_root, fs=fs)
        print("Building segments...")
        segments, anomalies = build_segments(
            data_root=data_root,
            fs=fs,
            inner_sec=args.inner_window,
            outer_sec=outer_window,
            overlap=args.overlap,
        )
    if anomalies:
        print("Anomalies during segment build:")
        for path, reason in anomalies:
            print(f"  {path} -> {reason}")

    if not segments:
        print("No segments available for training.")
        return

    subject_ids = sorted({s.subject_id for s in segments})
    print(f"Subjects found: {subject_ids}")

    fold_metrics = []
    for sid in subject_ids:
        train_segments = [s for s in segments if s.subject_id != sid]
        test_segments = [s for s in segments if s.subject_id == sid]
        if not test_segments:
            continue

        if args.feature_variant == "auto":
            candidates = []
            if args.flat:
                candidates.extend([("flat", "base"), ("flat", "ext")])
            else:
                candidates.extend(
                    [("hier", "base"), ("hier", "ext"), ("flat", "base"), ("flat", "ext")]
                )
            mode, variant = select_best_config(
                train_segments, model_type=args.model, candidates=candidates
            )
        else:
            variant = args.feature_variant
            mode = "flat" if args.flat else "hier"

        try:
            if mode == "flat":
                model_bundle = train_flat_model(
                    train_segments,
                    model_type=args.model,
                    tune=not args.no_tune,
                    feature_variant=variant,
                )
            else:
                model_bundle = train_hierarchical_model(
                    train_segments,
                    model_type=args.model,
                    tune=not args.no_tune,
                    feature_variant=variant,
                )
        except ValueError:
            continue

        metrics = evaluate_segments(model_bundle, test_segments, threshold=args.threshold)
        fold_metrics.append(metrics)

        recall = metrics["recall"]
        print(
            "Fold subject {} | Acc {:.4f} | MacroF1 {:.4f} | Recall [L {:.3f} M {:.3f} H {:.3f}] | "
            "Coverage {:.3f} | Acc@Coverage {:.3f}".format(
                sid,
                metrics["acc"],
                metrics["macro_f1"],
                recall[0],
                recall[1],
                recall[2],
                metrics["coverage"],
                metrics["acc_covered"],
            )
        )

    if not fold_metrics:
        print("No folds were evaluated.")
        return

    mean_acc = float(np.mean([m["acc"] for m in fold_metrics]))
    mean_f1 = float(np.mean([m["macro_f1"] for m in fold_metrics]))
    mean_recall = np.mean([m["recall"] for m in fold_metrics], axis=0)
    mean_cov = float(np.mean([m["coverage"] for m in fold_metrics]))
    mean_acc_cov = float(np.mean([m["acc_covered"] for m in fold_metrics]))

    print("\nAverage over folds")
    print(
        "Acc {:.4f} | MacroF1 {:.4f} | Recall [L {:.3f} M {:.3f} H {:.3f}] | Coverage {:.3f} | Acc@Coverage {:.3f}".format(
            mean_acc,
            mean_f1,
            mean_recall[0],
            mean_recall[1],
            mean_recall[2],
            mean_cov,
            mean_acc_cov,
        )
    )

    if args.save_model:
        if joblib_dump is None:
            print("joblib is required to save the model.")
            return
        if args.feature_variant == "auto":
            candidates = []
            if args.flat:
                candidates.extend([("flat", "base"), ("flat", "ext")])
            else:
                candidates.extend(
                    [("hier", "base"), ("hier", "ext"), ("flat", "base"), ("flat", "ext")]
                )
            mode, variant = select_best_config(
                segments, model_type=args.model, candidates=candidates
            )
        else:
            variant = args.feature_variant
            mode = "flat" if args.flat else "hier"

        if mode == "flat":
            model_bundle = train_flat_model(
                segments,
                model_type=args.model,
                tune=not args.no_tune,
                feature_variant=variant,
            )
        else:
            model_bundle = train_hierarchical_model(
                segments,
                model_type=args.model,
                tune=not args.no_tune,
                feature_variant=variant,
            )

        acc_str = "na"
        if mean_acc == mean_acc:
            acc_str = f"{mean_acc:.4f}"
        filename = f"{args.model_out_prefix}_{acc_str}.joblib"
        out_path = os.path.join(args.model_out_dir, filename)
        joblib_dump({"model_bundle": model_bundle}, out_path)
        print(f"Saved model to {out_path}")


if __name__ == "__main__":
    main()
