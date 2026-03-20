#!/usr/bin/env python3
"""Inspect Emotiv dataset .mat and scales.xls structure."""

import os
import sys


def inspect_mat(mat_path: str) -> None:
    print("MAT:", mat_path)
    try:
        import scipy.io as sio  # type: ignore
    except Exception as exc:
        print("scipy is required to read .mat files.")
        print(str(exc))
        return
    try:
        mat = sio.loadmat(mat_path)
    except NotImplementedError:
        try:
            import h5py  # type: ignore
        except Exception as exc:
            print("MAT seems v7.3; install h5py to read it.")
            print(str(exc))
            return
        with h5py.File(mat_path, "r") as f:
            keys = list(f.keys())
            print("keys:", keys)
            for k in keys:
                obj = f[k]
                try:
                    print(k, obj.shape, obj.dtype)
                except Exception:
                    print(k, obj)
        return

    keys = [k for k in mat.keys() if not k.startswith("__")]
    print("keys:", keys)
    for k in keys:
        v = mat[k]
        shape = getattr(v, "shape", None)
        dtype = getattr(v, "dtype", None)
        print(k, shape, dtype)


def inspect_scales(xls_path: str) -> None:
    print("XLS:", xls_path)
    try:
        import pandas as pd  # type: ignore
    except Exception as exc:
        print("pandas is required to read scales.xls")
        print(str(exc))
        return
    try:
        df = pd.read_excel(xls_path)
    except Exception as exc:
        print("Failed to read scales.xls (need xlrd for .xls).")
        print(str(exc))
        return
    print("columns:", list(df.columns))
    print(df.head())


def main() -> None:
    base = r"D:\A_theme_one\EEG\dataset\Data"
    mat_path = os.path.join(base, "raw_data", "Arithmetic_sub_10_trial1.mat")
    xls_path = os.path.join(base, "scales.xls")
    inspect_mat(mat_path)
    print("")
    inspect_scales(xls_path)


if __name__ == "__main__":
    main()
