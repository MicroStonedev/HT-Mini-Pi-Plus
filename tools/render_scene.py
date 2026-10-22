# -*- coding: utf-8 -*-
"""离屏渲染场景检查：从多个视角渲染 XML，输出 PNG 供人工检查。

用法：
  python tools/render_scene.py scenes/scene_classroom.xml            # 放入机器人并先跑 10s 进入步态
  python tools/render_scene.py scenes/scene_classroom.xml --no-policy --cameras overview walker
"""
from __future__ import annotations

import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mujoco

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mujoco_pi_plus_walk import DEFAULT_MODEL, DEFAULT_POLICY, WalkParams, WalkRunner


def render_model(model_path: str, out_prefix: str, cameras: list | None,
                 warmup_s: float, policy_path: str | None) -> list[str]:
    model = mujoco.MjModel.from_xml_path(model_path)
    data = mujoco.MjData(model)
    if policy_path:
        params = WalkParams()
        runner = WalkRunner(policy_path, model_path, params)
        runner.override_model(model, data)  # 用同一套扮演推进步态
        runner.run(warmup_s, cmd=(0.5, 0.0, 0.0), verbose=False)
    else:
        data.qpos[7:] = default_pose()
        mujoco.mj_forward(model, data)

    available = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_CAMERA, i)
                 for i in range(model.ncam)]
    print(f"[render] 模型相机: {available}")
    cams = cameras or [c for c in available if c] or ["free"]

    renderer = mujoco.Renderer(model, width=640, height=480)
    paths = []
    for cam in cams:
        try:
            if cam in available:
                renderer.update_scene(data, camera=cam)
            else:
                renderer.update_scene(data, camera=-1)
            img = renderer.render()
        except Exception as e:
            print(f"[render] 相机 {cam} 失败: {e}")
            continue
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.imshow(img)
        ax.set_title(f"{os.path.basename(model_path)} — {cam}")
        ax.axis("off")
        path = f"{out_prefix}_{cam}.png"
        fig.tight_layout()
        fig.savefig(path, dpi=110, bbox_inches="tight")
        plt.close(fig)
        paths.append(path)
        print(f"[render] 已保存 {path}")
    return paths


def default_pose():
    import numpy as np
    return np.array(
        [-0.25, 0, 0, 0.65, -0.4, 0, 0, 0.2, 0, -1.2,
         -0.25, 0, 0, 0.65, -0.4, 0, 0, -0.2, 0, -1.2])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("model")
    parser.add_argument("-o", "--out", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "results", "plots", "scene_check"))
    parser.add_argument("--policy", default=DEFAULT_POLICY)
    parser.add_argument("--cameras", nargs="*", default=None)
    parser.add_argument("--warmup", type=float, default=8.0,
                        help="先用策略跑多少秒再渲染（让机器人进入行走步态）")
    parser.add_argument("--no-policy", action="store_true", help="只渲染空场景")
    args = parser.parse_args()
    render_model(args.model, args.out, args.cameras, args.warmup,
                 None if args.no_policy else args.policy)
