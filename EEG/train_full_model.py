#!/usr/bin/env python3
"""Train a final model on all subjects and save it for realtime inference."""

import argparse
import os
import sys

from joblib import dump as joblib_dump

from train_eeg_3class import (
    build_segments,
    build_segments_emotiv,
    resolve_data_root,
    resolve_emotiv_root,
    select_best_config,
    train_flat_model,
    train_hierarchical_model,
    EMOTIV_FS,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train full dataset model")
    parser.add_argument(
        "--data_dir",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "dataset", "raw_data"),
        help="Path to dataset root (contains Arithmetic_Data/Stroop_Data)",
    )
    parser.add_argument("--model", type=str, default="svm", choices=["svm", "rf"])
    parser.add_argument("--no_tune", action="store_true")
    parser.add_argument("--flat", action="store_true")
    parser.add_argument(
        "--dataset",
        type=str,
        default="auto",
        choices=["auto", "openbci", "emotiv"],
    )
    parser.add_argument(
        "--emotiv_source",
        type=str,
        default="filtered_data",
        choices=["raw_data", "filtered_data"],
    )
    parser.add_argument(
        "--no_relax",
        action="store_true",
    )
    parser.add_argument(
        "--feature_variant",
        type=str,
        default="auto",
        choices=["auto", "base", "ext"],
    )
    parser.add_argument(
        "--out_model",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "model_bundle.joblib"),
    )
    args = parser.parse_args()

    dataset = args.dataset
    if dataset == "auto":
        if os.path.isfile(os.path.join(args.data_dir, "scales.xls")):
            dataset = "emotiv"
        else:
            dataset = "openbci"

    if dataset == "emotiv":
        data_root = resolve_emotiv_root(args.data_dir, args.emotiv_source)
        scales_path = os.path.join(os.path.dirname(data_root), "scales.xls")
        segments, anomalies = build_segments_emotiv(
            data_root=data_root,
            scales_path=scales_path,
            fs=EMOTIV_FS,
            inner_sec=4.0,
            outer_sec=25.0,
            overlap=0.5,
            include_relax=not args.no_relax,
            apply_filter=(args.emotiv_source == "raw_data"),
        )
    else:
        data_root = resolve_data_root(args.data_dir)
        segments, anomalies = build_segments(
            data_root=data_root, fs=250, inner_sec=4.0, outer_sec=30.0, overlap=0.5
        )
    if anomalies:
        print("Anomalies during segment build:")
        for path, reason in anomalies:
            print(f"  {path} -> {reason}")
    if not segments:
        print("No segments available for training.", file=sys.stderr)
        sys.exit(1)

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
            segments, model_type=args.model, tune=not args.no_tune, feature_variant=variant
        )
    else:
        model_bundle = train_hierarchical_model(
            segments, model_type=args.model, tune=not args.no_tune, feature_variant=variant
        )

    joblib_dump({"model_bundle": model_bundle}, args.out_model)
    print(f"Saved model to {args.out_model}")


if __name__ == "__main__":
    main()
