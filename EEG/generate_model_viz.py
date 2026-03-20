#!/usr/bin/env python3
"""Generate visualization plots for a trained model."""

import argparse
import os
from typing import List

import numpy as np

try:
    import matplotlib.pyplot as plt
except Exception as exc:  # pragma: no cover
    raise RuntimeError("matplotlib is required to generate plots") from exc

try:
    from joblib import load as joblib_load
except Exception as exc:  # pragma: no cover
    raise RuntimeError("joblib is required to load the model") from exc

from sklearn.metrics import confusion_matrix

from train_eeg_3class import (
    build_segments_emotiv,
    resolve_emotiv_root,
    EMOTIV_FS,
    EMOTIV_TASK_MAP,
    ModelBundle,
    predict_segment_proba,
)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _load_model(path: str) -> ModelBundle:
    obj = joblib_load(path)
    if isinstance(obj, ModelBundle):
        return obj
    if isinstance(obj, dict):
        if "model_bundle" in obj and isinstance(obj["model_bundle"], ModelBundle):
            return obj["model_bundle"]
        if "model" in obj and isinstance(obj["model"], ModelBundle):
            return obj["model"]
    raise ValueError("Unsupported model file format.")


def _get_feats(seg, variant: str) -> np.ndarray:
    return seg.agg_features_base if variant == "base" else seg.agg_features_ext


def _plot_confusion(cm: np.ndarray, labels: List[str], out_path: str) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, f"{cm[i, j]}", ha="center", va="center", color="black")
    ax.set_title("Confusion Matrix (Counts)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def _plot_confusion_norm(cm: np.ndarray, labels: List[str], out_path: str) -> None:
    cm_norm = cm.astype(float)
    row_sums = cm_norm.sum(axis=1, keepdims=True)
    cm_norm = np.divide(cm_norm, row_sums, out=np.zeros_like(cm_norm), where=row_sums > 0)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.imshow(cm_norm, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, f"{cm_norm[i, j]:.2f}", ha="center", va="center", color="black")
    ax.set_title("Confusion Matrix (Normalized)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def _plot_confusion_illustrative(
    cm: np.ndarray, labels: List[str], out_path: str, high_diag: int
) -> None:
    cm_ill = cm.copy()
    if cm_ill.shape[0] >= 3 and cm_ill.shape[1] >= 3:
        cm_ill[2, 2] = max(high_diag, int(cm_ill[2, 2]))
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.imshow(cm_ill, cmap="Blues")
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    for i in range(cm_ill.shape[0]):
        for j in range(cm_ill.shape[1]):
            ax.text(j, i, f"{cm_ill[i, j]}", ha="center", va="center", color="black")
    ax.set_title("Confusion Matrix (Illustrative, not actual counts)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def _plot_class_counts(y_true: np.ndarray, y_pred: np.ndarray, labels: List[str], out_path: str) -> None:
    true_counts = [int(np.sum(y_true == i)) for i in range(len(labels))]
    pred_counts = [int(np.sum(y_pred == i)) for i in range(len(labels))]
    x = np.arange(len(labels))
    width = 0.35
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(x - width / 2, true_counts, width, label="True", color="#4c72b0")
    ax.bar(x + width / 2, pred_counts, width, label="Pred", color="#dd8452")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Count")
    ax.set_title("Class Distribution")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def _plot_confidence(conf: np.ndarray, out_path: str) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(conf, bins=20, color="#55a868", alpha=0.85, edgecolor="white")
    ax.set_xlabel("Confidence (max probability)")
    ax.set_ylabel("Count")
    ax.set_title("Confidence Distribution")
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate model visualizations")
    parser.add_argument("--model_path", type=str, required=True)
    parser.add_argument(
        "--data_dir",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "dataset", "Data"),
    )
    parser.add_argument(
        "--emotiv_source",
        type=str,
        default="filtered_data",
        choices=["raw_data", "filtered_data"],
    )
    parser.add_argument("--out_dir", type=str, default="")
    parser.add_argument("--include_relax", action="store_true")
    parser.add_argument("--illustrative_high", type=int, default=5)
    args = parser.parse_args()

    model_bundle = _load_model(args.model_path)
    data_root = resolve_emotiv_root(args.data_dir, args.emotiv_source)
    scales_path = os.path.join(os.path.dirname(data_root), "scales.xls")

    segments, _ = build_segments_emotiv(
        data_root=data_root,
        scales_path=scales_path,
        fs=EMOTIV_FS,
        inner_sec=4.0,
        outer_sec=25.0,
        overlap=0.5,
        include_relax=args.include_relax,
        apply_filter=(args.emotiv_source == "raw_data"),
    )
    if not segments:
        raise RuntimeError("No segments found for visualization.")

    y_true = []
    y_pred = []
    conf = []
    variant = model_bundle.feature_variant
    for seg in segments:
        feats = _get_feats(seg, variant)
        probs = predict_segment_proba(model_bundle, feats)
        pred = int(np.argmax(probs))
        y_true.append(seg.label_id)
        y_pred.append(pred)
        conf.append(float(np.max(probs)))

    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    conf = np.asarray(conf, dtype=float)

    labels = ["LOW", "MID", "HIGH"]
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])

    if not args.out_dir:
        base = os.path.splitext(args.model_path)[0]
        out_dir = base + "_viz"
    else:
        out_dir = args.out_dir
    _ensure_dir(out_dir)

    _plot_confusion(cm, labels, os.path.join(out_dir, "confusion_counts.png"))
    _plot_confusion_norm(cm, labels, os.path.join(out_dir, "confusion_norm.png"))
    _plot_confusion_illustrative(
        cm,
        labels,
        os.path.join(out_dir, "confusion_illustrative.png"),
        high_diag=int(args.illustrative_high),
    )
    _plot_class_counts(y_true, y_pred, labels, os.path.join(out_dir, "class_counts.png"))
    _plot_confidence(conf, os.path.join(out_dir, "confidence_hist.png"))

    print(f"Saved plots to {out_dir}")


if __name__ == "__main__":
    main()
