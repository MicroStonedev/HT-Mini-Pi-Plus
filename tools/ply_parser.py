# -*- coding: utf-8 -*-
"""解析 3DGS / LiDAR 点云 PLY（binary_little_endian，float32 属性）。

3DGS 的 f_dc_0..2 是球谐 DC 项：color = clip(0.5 + 0.2820948 * f_dc)。
返回 (xyz: Nx3 float, rgb: Nx3 float in [0,1])。
"""
import struct

import numpy as np

SHDC = 0.28209479177387814


def parse_ply_binary(path: str):
    with open(path, "rb") as f:
        header = {}
        while True:
            line = f.readline().decode("ascii", "replace").strip()
            if line == "end_header":
                break
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "element":
                header[parts[1]] = int(parts[2])
            elif parts[0] == "property":
                header.setdefault("_props", []).append(parts[1:])
        dtype_list = []
        names = []
        for prop in header["_props"]:
            names.append(prop[1])
            dtype_list.append("<f4")
        dtype = np.dtype([(n, t) for n, t in zip(names, dtype_list)])
        raw = np.fromfile(f, dtype=dtype, count=header.get("vertex", 0))
    if raw.size == 0:
        raise ValueError(f"PLY 中没有 vertex 元素: {path}")
    xyz = np.stack([raw["x"], raw["y"], raw["z"]], axis=1).astype(np.float64)
    if all(k in raw.dtype.names for k in ("f_dc_0", "f_dc_1", "f_dc_2")):
        rgb = np.clip(
            np.stack([raw["f_dc_0"], raw["f_dc_1"], raw["f_dc_2"]], axis=1) * SHDC + 0.5,
            0.0, 1.0)
    else:
        rgb = np.full((len(raw), 3), 0.6)
    return xyz, rgb


if __name__ == "__main__":
    import sys
    p = sys.argv[1]
    xyz, rgb = parse_ply_binary(p)
    z = xyz[:, 2]
    print(f"点数: {len(z)}")
    print(f"极值 z: [{z.min():.2f}, {z.max():.2f}]")
    # 高度直方图（按 0.1 单位打印占比，观察地面/桌面/天花板分层）
    lo, hi = np.percentile(z, 0.5), np.percentile(z, 99.5)
    bins = np.linspace(lo, hi, 41)
    hist, edges = np.histogram(z, bins=bins)
    for h, e in zip(hist, edges):
        bar = "#" * int(45 * h / max(hist))
        pct = 100 * h / len(z)
        print(f"{e:8.1f} | {pct:5.2f}% {bar}")
