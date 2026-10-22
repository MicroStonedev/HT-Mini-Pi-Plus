# -*- coding: utf-8 -*-
"""推力扰动鲁棒性测试：对行走中的 Mini Pi+ 周期性施加水平推力，统计存活率。

这正是高擎方向二"考察策略迁移稳定性 + 误差来源说明"的量化实验素材：
  - 多个官方 checkpoint × 多档推力 → 存活率 / 跌倒时间 / 恢复表现
  - 输出 CSV 表格 + 基座高度曲线图（results/ 下）

用法：
    python tools/disturbance_test.py                       # 默认：3 个官方 checkpoint × 4 档推力
    python tools/disturbance_test.py --pushes 40 80 120    # 自定义推力档位
    python tools/disturbance_test.py --friction 0.4        # 叠加低摩擦消融
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mujoco_pi_plus_walk import (AMP_ROOT, WalkParams, WalkRunner, load_policy,
                                 DEFAULT_MODEL)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
CHECKPOINTS = {
    "model_27000": os.path.join(AMP_ROOT, "Exported_policy", "model_27000.pt"),
    "model_30000_15": os.path.join(AMP_ROOT, "Exported_policy", "model_30000_15.pt"),
    "model_40000": os.path.join(AMP_ROOT, "Exported_policy", "model_40000.pt"),
}


def run_sweep(policy_paths: dict, pushes: list, duration: float, episodes: int,
              friction: float | None, scene: str | None) -> tuple:
    rows, curves = [], {}
    for ckpt_name, ckpt_path in policy_paths.items():
        for push in pushes:
            survives = []
            for ep in range(episodes):
                params = WalkParams(push_force=push, floor_friction=friction)
                runner = WalkRunner(ckpt_path, scene or DEFAULT_MODEL, params)
                r = runner.run(duration, cmd=(0.5, 0.0, 0.0), seed=ep, verbose=False)
                survives.append(r.survived)
                label = f"{ckpt_name} push={push:.0f}N ep{ep}"
                curves[label] = r.telemetry["z"]
                rows.append({
                    "checkpoint": ckpt_name, "push_N": push, "episode": ep,
                    "survived": int(r.survived), "fall_time_s": r.fall_time_s,
                    "base_height_mean_m": r.base_height_mean,
                    "mean_forward_vel_mps": r.mean_forward_vel,
                })
            rate = sum(survives) / len(survives)
            print(f"[sweep] {ckpt_name:16s} push={push:5.0f}N -> 存活率 {rate:.0%}")
    return rows, curves


def save_outputs(rows: list, curves: dict, tag: str) -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(os.path.join(RESULTS_DIR, "plots"), exist_ok=True)
    csv_path = os.path.join(RESULTS_DIR, f"disturbance_{tag}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"[out] CSV: {csv_path}")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    pick = [k for k in curves if "ep0" in k]
    ckpt_groups = {}
    for k in pick:
        name = k.rsplit(" ep0", 1)[0]
        ckpt_groups.setdefault(name.split(" push")[0], []).append(k)
    for ax, (ckpt, keys) in zip(axes, list(ckpt_groups.items())[:2]):
        for k in keys:
            ax.plot(curves[k], lw=0.8, label=k.split(" ep")[0])
        ax.axhline(0.22, color="r", ls="--", lw=1, label="跌倒阈值")
        ax.set_title(f"{ckpt} 基座高度（首个回合）")
        ax.set_xlabel("控制步 (50Hz)")
        ax.set_ylabel("基座高度 z (m)")
        ax.legend(fontsize=7)
    axes[0].set_ylabel("基座高度 z (m)")
    plot_path = os.path.join(RESULTS_DIR, "plots", f"disturbance_{tag}.png")
    fig.tight_layout()
    fig.savefig(plot_path, dpi=150)
    print(f"[out] 图: {plot_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="推力扰动鲁棒性测试")
    parser.add_argument("--pushes", type=float, nargs="+", default=[0, 40, 80, 120],
                        help="推力档位（牛顿），0 为无扰动基线")
    parser.add_argument("--duration", type=float, default=15.0, help="每回合时长(s)")
    parser.add_argument("--episodes", type=int, default=3, help="每档推力回合数（不同随机方向）")
    parser.add_argument("--friction", type=float, default=None, help="覆盖地面摩擦系数")
    parser.add_argument("--scene", default=None, help="自定义场景 XML（默认平地 pi_plus.xml）")
    parser.add_argument("--checkpoints", nargs="+", default=None,
                        help="只测指定 checkpoint（默认全部三个）")
    args = parser.parse_args()

    ckpts = CHECKPOINTS
    if args.checkpoints:
        ckpts = {k: v for k, v in CHECKPOINTS.items() if k in args.checkpoints}
    tag = "flat"
    if args.scene:
        tag = os.path.splitext(os.path.basename(args.scene))[0]
    if args.friction:
        tag += f"_mu{args.friction}"

    rows, curves = run_sweep(ckpts, args.pushes, args.duration, args.episodes,
                             args.friction, args.scene)
    save_outputs(rows, curves, tag)
