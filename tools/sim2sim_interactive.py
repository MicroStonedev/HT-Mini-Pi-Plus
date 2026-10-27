# -*- coding: utf-8 -*-
"""交互版 sim2sim：修好官方脚本的键盘控制（官方版键盘事件会被全局速度覆盖，
仅游戏手柄生效），并实时显示当前速度指令。

基于 third_party/Mini-Pi-Plus_AMP 的 sim2sim_pi_plus.py（BSD-3）修改：
  1. 键盘按键直接修改全局速度指令（官方逻辑的修正）
  2. 每次按键后打印当前指令；每 2 秒在终端回显一次
  3. 默认模型/策略指向本项目的场景与 jit 策略

控制键（主键盘数字排或小键盘均可）：
  8 / 2 : 前进速度 +0.2 / -0.2 m/s（范围 ±1.0）
  4 / 6 : 侧移指令 -0.2 / +0.2 m/s
  7 / 9 : 原地转向 -0.2 / +0.2 rad/s
  5     : 全部清零（站住）
  0     : 自由视角（鼠标拖动/滚轮）
  1-4   : overview / walker / side / top 机位（录屏推荐用 2 跟拍）
  Esc   : 结束
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import time

import mujoco
import mujoco_viewer

# MuJoCo MjvCamera.type 的取值（C 宏，Python 未导出）
CAM_FREE, CAM_TRACKING, CAM_FIXED = 0, 1, 2
import numpy as np
import torch
from pynput import keyboard

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AMP_ROOT = os.path.join(ROOT_DIR, "third_party", "Mini-Pi-Plus_AMP")
DEFAULT_MODEL = os.path.join(AMP_ROOT, "legged_lab", "assets", "hightorque", "pi_plus", "pi_plus.xml")
DEFAULT_POLICY = os.path.join(ROOT_DIR, "results", "checkpoints", "model_40000_jit.pt")

# 全局速度指令（观测每步读取这三个值）
x_vel_cmd, y_vel_cmd, yaw_vel_cmd = 0.5, 0.0, 0.0
CMD_MAX = (1.0, 0.6, 2.0)
exit_flag = False


def pd_control(target_q, q, kp, target_dq, dq, kd):
    return (target_q - q) * kp + (target_dq - dq) * kd


class SimToSimCfg:
    class sim:
        sim_duration = 60.0
        num_action = 20
        num_obs_per_step = 69
        actor_obs_history_length = 5
        dt = 0.002
        decimation = 10
        clip_observations = 100.0
        clip_actions = 100.0
        action_scale = 0.25


def load_policy(path: str):
    try:
        policy = torch.jit.load(path, map_location="cpu")
        policy.eval()
        return policy
    except RuntimeError:
        pass
    sys.path.insert(0, os.path.join(ROOT_DIR, "tools"))
    from mujoco_pi_plus_walk import load_policy as _load
    return _load(path)


def quat_apply_inverse(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    q_w, q_vec = q[-1], q[:3]
    a = v * (2.0 * q_w**2 - 1.0)
    b = np.cross(q_vec, v) * q_w * 2.0
    c = q_vec * np.dot(q_vec, v) * 2.0
    return a - b + c


class InteractiveRunner:
    def __init__(self, cfg, policy_path, model_path, realtime=True, render_size=640,
                 render_every=1):
        self.cfg = cfg
        self.realtime = realtime
        self.render_every = max(1, int(render_every))
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.model.opt.timestep = self.cfg.sim.dt
        # 窗口渲染分辨率：场景 XML 里的 offwidth（录屏用的高清缓冲）对交互是负担，
        # mujoco_viewer 每帧要把整个缓冲从 GPU 拷回 CPU，1280x960 会明显掉帧。
        self.model.vis.global_.offwidth = int(render_size)
        self.model.vis.global_.offheight = int(render_size * 3 // 4)
        self.policy = load_policy(policy_path)
        self.data = mujoco.MjData(self.model)
        self.viewer = mujoco_viewer.MujocoViewer(self.model, self.data)
        self.viewer._render_every_frame = False
        self.init_variables()
        self.data.qpos[7:] = self.default_dof_pos.copy()
        self.data.qvel[6:] = np.zeros_like(self.data.qvel[6:])
        mujoco.mj_forward(self.model, self.data)

    def init_variables(self):
        self.dt = self.cfg.sim.decimation * self.cfg.sim.dt
        self.action = np.zeros(self.cfg.sim.num_action)
        self.default_dof_pos = np.array(
            [-0.25, 0, 0, 0.65, -0.4, 0, 0, 0.2, 0, -1.2,
             -0.25, 0, 0, 0.65, -0.4, 0, 0, -0.2, 0, -1.2])
        self.kps = [80, 80, 80, 80, 60, 60, 30, 30, 30, 30] * 2
        self.kds = [1.1, 1.1, 1.1, 1.1, 1.2, 1.2, 0.6, 0.6, 0.6, 0.6] * 2
        self.isaac_to_mujoco_idx = [0, 4, 8, 12, 16, 18, 1, 5, 9, 13, 2, 6, 10, 14, 17, 19, 3, 7, 11, 15]
        self.mujoco_to_isaac_idx = [0, 6, 10, 16, 1, 7, 11, 17, 2, 8, 12, 18, 3, 9, 13, 19, 4, 14, 5, 15]
        self.obs_history = np.zeros(
            self.cfg.sim.num_obs_per_step * self.cfg.sim.actor_obs_history_length,
            dtype=np.float32)

    def get_obs(self):
        global x_vel_cmd, y_vel_cmd, yaw_vel_cmd
        dof_pos, dof_vel = self.data.qpos[7:], self.data.qvel[6:]
        obs = np.zeros(self.cfg.sim.num_obs_per_step, dtype=np.float32)
        obs[0:3] = self.data.sensor("angular-velocity").data
        obs[3:6] = quat_apply_inverse(
            self.data.sensor("orientation").data[[1, 2, 3, 0]], np.array([0, 0, -1]))
        obs[6:9] = (x_vel_cmd, y_vel_cmd, yaw_vel_cmd)
        obs[9:29] = (dof_pos - self.default_dof_pos)[self.mujoco_to_isaac_idx]
        obs[29:49] = dof_vel[self.mujoco_to_isaac_idx]
        obs[49:69] = np.clip(self.action, -self.cfg.sim.clip_actions, self.cfg.sim.clip_actions)
        self.obs_history = np.roll(self.obs_history, -self.cfg.sim.num_obs_per_step)
        self.obs_history[-self.cfg.sim.num_obs_per_step:] = obs
        return np.clip(self.obs_history, -self.cfg.sim.clip_observations, self.cfg.sim.clip_observations)

    def run(self, duration):
        global exit_flag
        self._step_idx = 0
        self.start_keyboard_listener()

        def heartbeat():
            while not exit_flag:
                print(f"\r[cmd] vx={x_vel_cmd:+.2f} vy={y_vel_cmd:+.2f} "
                      f"yaw={yaw_vel_cmd:+.2f} | t={self.data.time:5.1f}s ", end="", flush=True)
                time.sleep(2.0)
        hb = threading.Thread(target=heartbeat, daemon=True)
        hb.start()

        # 初始取景：对准机器人，距离 4.5m、方位 135°、俯角 25°
        if self.viewer.cam.type == CAM_FREE:
            bid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "base_link")
            if bid >= 0:
                self.viewer.cam.lookat[:] = self.model.body_pos[bid]
                self.viewer.cam.distance = 4.5
                self.viewer.cam.azimuth = 135.0
                self.viewer.cam.elevation = -25.0

        while self.data.time < duration and not exit_flag:
            step_start = time.time()
            obs = self.get_obs()
            with torch.no_grad():
                action = self.policy(torch.tensor(obs, dtype=torch.float32).unsqueeze(0))
            self.action[:] = action.numpy()[0, :self.cfg.sim.num_action]
            self.action = np.clip(self.action, -self.cfg.sim.clip_actions, self.cfg.sim.clip_actions)
            target_dof_pos = (self.action * self.cfg.sim.action_scale)[self.isaac_to_mujoco_idx] + self.default_dof_pos
            for _ in range(self.cfg.sim.decimation):
                tau = pd_control(target_dof_pos, self.data.qpos[7:], self.kps,
                                 np.zeros_like(self.kds), self.data.qvel[6:], self.kds)
                self.data.ctrl = tau
                mujoco.mj_step(self.model, self.data)
            # 每个控制步渲染一次（50Hz）。旧版在 decimation 内渲染 = 500 次/秒，
            # 被 vsync 阻塞后仿真掉到 1/8 实时速度且周期性卡顿——这是卡停主因
            if self._step_idx % self.render_every == 0:
                self.viewer.render()
            self._step_idx += 1
            if self.realtime:
                remain = self.dt - (time.time() - step_start)
                if remain > 0:
                    time.sleep(remain)
        print()
        self.listener.stop()
        self.viewer.close()

    def start_keyboard_listener(self):
        def on_press(key):
            global x_vel_cmd, y_vel_cmd, yaw_vel_cmd, exit_flag
            char = getattr(key, "char", None)
            if char in ("8", "2"):
                x_vel_cmd = float(np.clip(x_vel_cmd + 0.2 * (1 if char == "8" else -1), -CMD_MAX[0], CMD_MAX[0]))
            elif char in ("4", "6"):
                y_vel_cmd = float(np.clip(y_vel_cmd + 0.2 * (-1 if char == "4" else 1), -CMD_MAX[1], CMD_MAX[1]))
            elif char in ("7", "9"):
                yaw_vel_cmd = float(np.clip(yaw_vel_cmd + 0.2 * (-1 if char == "7" else 1), -CMD_MAX[2], CMD_MAX[2]))
            elif char == "5":
                x_vel_cmd = y_vel_cmd = yaw_vel_cmd = 0.0
                print("\n[cmd] 速度已清零")
            elif key == keyboard.Key.esc:
                exit_flag = True
                print("\n[cmd] 退出")
            elif char in ("0", "1", "2", "3", "4"):
                self.switch_camera(char)
                return
            else:
                return
            print(f"\n[cmd] vx={x_vel_cmd:+.2f} vy={y_vel_cmd:+.2f} yaw={yaw_vel_cmd:+.2f}")
        self.listener = keyboard.Listener(on_press=on_press)
        self.listener.start()

    def switch_camera(self, key: str) -> None:
        """切换视角：0 自由视角（鼠标拖动）/ 1-4 场景 XML 内置相机。"""
        if key == "0":
            self.viewer.cam.type = CAM_FREE
            print("\n[cam] 自由视角（鼠标拖动旋转、滚轮缩放）")
            return
        names = {"1": "overview", "2": "walker", "3": "side", "4": "top"}
        name = names[key]
        cid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_CAMERA, name)
        if cid < 0:
            print(f"\n[cam] 当前场景没有 {name} 相机（平地场景只有 0/1）")
            return
        self.viewer.cam.type = CAM_FIXED
        self.viewer.cam.fixedcamid = cid
        print(f"\n[cam] 已切换到 {name} 机位")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="交互版 sim2sim（键盘可控）")
    parser.add_argument("--policy", default=DEFAULT_POLICY)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--maxspeed", action="store_true",
                        help="关闭实时节拍，仿真全速运行（做基准测试用）")
    parser.add_argument("--render-size", type=int, default=640,
                        help="窗口渲染分辨率宽度（默认 640，卡顿时降到 480）")
    parser.add_argument("--render-every", type=int, default=1,
                        help="每 N 个控制步渲染一次（默认 1=50fps，卡顿时设 2=25fps）")
    args = parser.parse_args()
    if not os.path.isfile(args.policy):
        sys.exit(f"[ERROR] 策略不存在: {args.policy}（先跑 python tools/export_policy.py）")
    if not os.path.isfile(args.model):
        sys.exit(f"[ERROR] 模型不存在: {args.model}")
    cfg = SimToSimCfg()
    cfg.sim.sim_duration = args.duration
    InteractiveRunner(cfg, args.policy, args.model,
                      realtime=not args.maxspeed,
                      render_size=args.render_size,
                      render_every=args.render_every).run(args.duration)
