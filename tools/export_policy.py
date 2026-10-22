# -*- coding: utf-8 -*-
"""把官方训练 checkpoint 导出为 TorchScript 策略，供官方 GUI 脚本直接加载
（官方 sim2sim_pi_plus.py 的 jit.load 路径无需 rsl_rl 依赖）。

用法：python tools/export_policy.py
输出：results/checkpoints/<name>_jit.pt
"""
import os
import sys
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mujoco_pi_plus_walk import AMP_ROOT, load_policy

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "checkpoints")

if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    src_dir = os.path.join(AMP_ROOT, "Exported_policy")
    for fname in sorted(os.listdir(src_dir)):
        if not fname.endswith(".pt"):
            continue
        actor = load_policy(os.path.join(src_dir, fname))
        example = torch.zeros(1, 345)  # 69 obs × 5 历史
        scripted = torch.jit.script(actor)
        with torch.no_grad():
            out = scripted(example)
        dst = os.path.join(OUT_DIR, fname.replace(".pt", "_jit.pt"))
        scripted.save(dst)
        print(f"[export] {fname} -> {dst} (out shape {tuple(out.shape)})")
