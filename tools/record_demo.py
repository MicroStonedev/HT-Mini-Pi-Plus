# -*- coding: utf-8 -*-
"""自动化录屏：把 Mini Pi+ 行走演示直接渲染成 MP4（不依赖录屏软件，机位精确可复现）。

用法：
  python tools/record_demo.py --model scenes/scene_classroom.xml --camera walker --duration 15
  python tools/record_demo.py --camera overview --duration 20            # 平地场景 + 俯视
  python tools/record_demo.py --scene scene_synthetic --camera side      # 合成教室

输出：results/videos/demo_<场景名>_<机位>_<时长>s.mp4
帧率 25fps（控制环 50Hz 隔帧采样），分辨率 960x720。
"""
from __future__ import annotations

import argparse
import os
import sys

import imageio.v2 as imageio
import numpy as np
import mujoco

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mujoco_pi_plus_walk import (DEFAULT_MODEL, DEFAULT_POLICY, KDS, KPS,
                                 ISAAC_TO_MUJOCO_IDX, MUJOCO_TO_ISAAC_IDX,
                                 DEFAULT_DOF_POS, WalkParams, load_policy,
                                 quat_apply_inverse)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENES = {
    "classroom": os.path.join(ROOT_DIR, "scenes", "scene_classroom.xml"),
    "synthetic": os.path.join(ROOT_DIR, "scenes", "scene_synthetic.xml"),
    "flat": DEFAULT_MODEL,
}
OUT_DIR = os.path.join(ROOT_DIR, "results", "videos")
FPS = 25
CAM_NAMES = {"overview", "walker", "side", "top"}


def record(model_path: str, camera: str, duration: float, out_path: str,
           cmd=(0.5, 0.0, 0.0), push: float = 0.0, width: int = 960,
           height: int = 720) -> str:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    model = mujoco.MjModel.from_xml_path(model_path)
    model.opt.timestep = 0.002
    # 离屏渲染缓冲上限由 XML 的 <visual><global offwidth/offheight> 决定；
    # 官方 pi_plus.xml 未设置（默认 640），超了会直接报错，这里自动降级
    off_w = int(model.vis.global_.offwidth) or 640
    if width > off_w:
        height = int(height * off_w / width)
        print(f"[record] 离屏缓冲上限 {off_w}px，分辨率降为 {off_w}x{height}")
        width = off_w
    data = mujoco.MjData(model)
    sign = 1 if mujoco.__version__ >= "3" else 1
    data.qpos[7:] = DEFAULT_DOF_POS.copy()
    mujoco.mj_forward(model, data)
    policy = load_policy(args.policy)

    cam_id = None
    if camera in CAM_NAMES:
        cam_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, camera)
        if cam_id < 0:
            print(f"[record] 该场景无 {camera} 相机，改用自由视角")
            camera = "free"
    print(f"[record] 场景 {os.path.basename(model_path)} | 机位 {camera} | {duration}s @ {FPS}fps")

    renderer = mujoco.Renderer(model, width=width, height=height)
    # 自由机位（场景无命名相机时）：跟拍机器人，距离 3.5m、方位 135°、俯角 20°
    free_cam = None
    if camera == "free":
        free_cam = mujoco.MjvCamera()
        free_cam.type, free_cam.distance = 0, 3.5
        free_cam.azimuth, free_cam.elevation = 135.0, -20.0
        free_cam.lookat[:] = [0, 0, 0.5]
    p = WalkParams(push_force=push)
    action = np.zeros(p.num_action)
    obs_hist = np.zeros(p.num_obs_per_step * p.actor_obs_history_length, dtype=np.float32)
    cmd_arr = np.asarray(cmd, dtype=np.float32)
    base_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "base_link")

    writer = imageio.get_writer(out_path, fps=FPS, codec="libx264", quality=7,
                                ffmpeg_params=["-pix_fmt", "yuv420p"])
    frames, frame_every = 0, 2          # 50Hz 控制 → 25fps
    step = 0
    self_x, self_y = 0.0, 0.0
    while data.time < duration:
        self_x, self_y = float(data.qpos[0]), float(data.qpos[1])
        dof_pos, dof_vel = data.qpos[7:], data.qvel[6:]
        obs = np.zeros(p.num_obs_per_step, dtype=np.float32)
        obs[0:3] = data.sensor("angular-velocity").data
        obs[3:6] = quat_apply_inverse(
            data.sensor("orientation").data[[1, 2, 3, 0]], np.array([0, 0, -1]))
        obs[6:9] = cmd_arr
        obs[9:29] = (dof_pos - DEFAULT_DOF_POS)[MUJOCO_TO_ISAAC_IDX]
        obs[29:49] = dof_vel[MUJOCO_TO_ISAAC_IDX]
        obs[49:69] = np.clip(action, -p.clip_actions, p.clip_actions)
        obs_hist = np.roll(obs_hist, -p.num_obs_per_step)
        obs_hist[-p.num_obs_per_step:] = obs
        with torch.no_grad():
            act = policy(torch.tensor(obs_hist, dtype=torch.float32).unsqueeze(0))
        action = np.clip(act.numpy()[0, :p.num_action], -p.clip_actions, p.clip_actions)
        target = (action * p.action_scale)[ISAAC_TO_MUJOCO_IDX] + DEFAULT_DOF_POS

        if p.push_force > 0 and (data.time % 3.0) < 0.15:
            data.xfrc_applied[base_id, [0, 1]] = [p.push_force * 0.7, p.push_force * 0.7]
        for _ in range(p.decimation):
            data.ctrl = (target - data.qpos[7:]) * KPS - data.qvel[6:] * KDS
            mujoco.mj_step(model, data)
        if step % frame_every == 0:
            if cam_id is not None:
                renderer.update_scene(data, camera=cam_id)
            elif free_cam is not None:
                free_cam.lookat[:] = self_x, self_y, 0.5     # 跟拍机器人
                renderer.update_scene(data, camera=free_cam)
            else:
                renderer.update_scene(data, camera=-1)
            writer.append_data(renderer.render())
            frames += 1
        step += 1

    writer.close()
    size_mb = os.path.getsize(out_path) / 1e6
    print(f"[record] 完成：{out_path}（{frames} 帧，{size_mb:.1f} MB）")
    return out_path


if __name__ == "__main__":
    import torch
    parser = argparse.ArgumentParser(description="Mini Pi+ 行走演示自动录屏")
    parser.add_argument("--model", default=None, help="场景 XML（优先于 --scene）")
    parser.add_argument("--scene", default="classroom", choices=list(SCENES))
    parser.add_argument("--camera", default="walker",
                        choices=["overview", "walker", "side", "top", "free"])
    parser.add_argument("--duration", type=float, default=15.0)
    parser.add_argument("--cmd", type=float, nargs=3, default=[0.5, 0.0, 0.0])
    parser.add_argument("--push", type=float, default=0.0, help="推力扰动(N)")
    parser.add_argument("--policy", default=DEFAULT_POLICY, help="策略jit文件(默认官方model_40000)")
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args()
    model = args.model or SCENES[args.scene]
    if not os.path.isfile(model):
        sys.exit(f"[ERROR] 场景不存在: {model}")
    name = os.path.splitext(os.path.basename(model))[0].replace("scene_", "")
    out = os.path.join(OUT_DIR, f"demo_{name}_{args.camera}_{int(args.duration)}s.mp4")
    record(model, args.camera, args.duration, out, tuple(args.cmd), args.push,
           args.width, args.height)
