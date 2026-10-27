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
import ctypes
import faulthandler
import os
import sys
import threading
import time

import mujoco
import mujoco_viewer

# Windows 默认 sleep 精度只有 15.6ms：实时节拍每步只需睡 ~11ms，
# 不提升精度会让控制循环掉到 ~42Hz 且节奏呈锯齿（画面一顿一顿）。
if sys.platform == "win32":
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
    except Exception:
        pass

# native 段错误(窗口闪退)会写进 crash.log，便于事后定位
try:
    _CRASH_LOG = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "crash.log"), "w", buffering=1)
    faulthandler.enable(_CRASH_LOG)
except Exception:
    pass

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
        # 关闭左上/左下的信息叠加面板（FPS/时间/警告），避免遮挡机器人和课桌
        self.viewer._hide_menus = True
        # mujoco_viewer 自带一整套快捷键，会抢走 W/A/S/D/Q/E 之外的键：
        #   空格=暂停仿真(不是"站住")、S=仿真速度减半、D=切渲染、E=空分支吞键、
        #   Tab=它自己切相机、R=透明模式(物体只剩线框)。全部禁用，交给 pynput。
        try:
            import glfw
            glfw.set_key_callback(self.viewer.window, lambda *a, **k: None)
        except Exception:
            pass
        # 透明模式若被意外打开，画面会只剩骨架，这里强制关掉
        if getattr(self.viewer, "_transparent", False):
            self.viewer._transparent = False
        # 线框渲染标志强制关闭 + 打开阴影（否则场景看起来像只有框架）
        try:
            scn = self.viewer.scn
            scn.flags[mujoco.mjtRndFlag.mjRND_WIREFRAME] = 0
            scn.flags[mujoco.mjtRndFlag.mjRND_SHADOW] = 1
        except Exception:
            pass
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

        # 渲染在主线程做（GLFW 窗口消息泵必须在创建线程里，搬线程会"未响应"）。
        # 通过 render_every 降频来控制渲染开销：默认 2 = 25fps（够流畅，不卡控制循环）。
        self._step_idx = 0
        self._closed_by_user = False

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
            # 降频渲染：每 render_every 步渲染一次（默认 2 = 25fps）。
            # 50fps 渲染在 1050Ti 上偶发 30-60ms 尖刺（vsync），会把控制循环
            # 从 50Hz 拖到 30Hz 且按键延迟 → 渲染放主线程但降频。
            if self._step_idx % self.render_every == 0:
                try:
                    self.viewer.render()
                except Exception:
                    print("\n[viewer] 窗口已关闭，退出仿真", flush=True)
                    self._closed_by_user = True
                    break
            self._step_idx += 1
            if self.realtime:
                remain = self.dt - (time.time() - step_start)
                if remain > 0:
                    time.sleep(remain)
        if not getattr(self, "_closed_by_user", False) and not exit_flag:
            print(f"[done] 仿真时长 {duration:.0f}s 已跑完（正常结束，不是崩溃）", flush=True)
        print()
        if getattr(self, "listener", None) is not None:
            self.listener.stop()
        try:
            if not getattr(self, "_closed_by_user", False):
                self.viewer.close()
        except Exception:
            pass

    def start_keyboard_listener(self):
        """用 GLFW 原生键盘回调（与窗口焦点同步、不受中文输入法影响）。

        旧实现用 pynput 全局钩子，实测在中文输入法下会漏键：
        空格能收到、W 收不到。GLFW 回调直接来自窗口，是 MuJoCo 官方 demo 的做法。
        """
        global x_vel_cmd, y_vel_cmd, yaw_vel_cmd, exit_flag
        try:
            import glfw
        except Exception:
            print("[warn] glfw 不可用，键盘控制禁用", flush=True)
            self.listener = None
            return

        K = {
            "W": glfw.KEY_W, "S": glfw.KEY_S, "A": glfw.KEY_A, "D": glfw.KEY_D,
            "Q": glfw.KEY_Q, "E": glfw.KEY_E,
            "8": glfw.KEY_8, "2": glfw.KEY_2, "4": glfw.KEY_4,
            "6": glfw.KEY_6, "7": glfw.KEY_7, "9": glfw.KEY_9, "5": glfw.KEY_5,
            "SPACE": glfw.KEY_SPACE, "TAB": glfw.KEY_TAB, "ESC": glfw.KEY_ESCAPE,
            "H": glfw.KEY_H,
        }

        def on_key(window, key, scancode, action, mods):
            global x_vel_cmd, y_vel_cmd, yaw_vel_cmd, exit_flag
            if action not in (glfw.PRESS, glfw.REPEAT):
                return
            if key == K["ESC"]:
                exit_flag = True
                print("\n[cmd] 退出", flush=True)
                return
            if key == K["TAB"]:
                self.cycle_camera()
                return
            if key == K["H"]:
                self.viewer._hide_menus = not self.viewer._hide_menus
                state = "已隐藏" if self.viewer._hide_menus else "已显示"
                print(f"\n[ui] 信息面板{state}", flush=True)
                return
            if key in (K["SPACE"], K["5"]):
                x_vel_cmd = y_vel_cmd = yaw_vel_cmd = 0.0
                print("\n[cmd] 速度已清零", flush=True)
                return
            if key in (K["W"], K["8"]):
                x_vel_cmd = float(np.clip(x_vel_cmd + 0.2, -CMD_MAX[0], CMD_MAX[0]))
            elif key in (K["S"], K["2"]):
                x_vel_cmd = float(np.clip(x_vel_cmd - 0.2, -CMD_MAX[0], CMD_MAX[0]))
            elif key in (K["A"], K["4"]):
                y_vel_cmd = float(np.clip(y_vel_cmd - 0.2, -CMD_MAX[1], CMD_MAX[1]))
            elif key in (K["D"], K["6"]):
                y_vel_cmd = float(np.clip(y_vel_cmd + 0.2, -CMD_MAX[1], CMD_MAX[1]))
            elif key in (K["Q"], K["7"]):
                yaw_vel_cmd = float(np.clip(yaw_vel_cmd - 0.2, -CMD_MAX[2], CMD_MAX[2]))
            elif key in (K["E"], K["9"]):
                yaw_vel_cmd = float(np.clip(yaw_vel_cmd + 0.2, -CMD_MAX[2], CMD_MAX[2]))
            else:
                return
            print(f"\n[cmd] vx={x_vel_cmd:+.2f} vy={y_vel_cmd:+.2f} yaw={yaw_vel_cmd:+.2f}", flush=True)

        glfw.set_key_callback(self.viewer.window, on_key)
        # 打印实际渲染显卡：NVIDIA Optimus 笔记本默认会用 Intel 核显，
        # 核显渲染 MuJoCo 会卡到不可用（需在 Windows 图形设置里指定 python.exe 用高性能）。
        try:
            renderer = glfw.get_window_attrib
            import OpenGL.GL as _gl
            _name = _gl.glGetString(_gl.GL_RENDERER).decode(errors="ignore")
            if "Intel" in _name or "llvmpipe" in _name or "Microsoft Basic" in _name:
                print(f"[warn] 当前使用 {_name}（核显/软件渲染）——画面会卡、鼠标会迟钝。", flush=True)
                print("       修复：Windows 设置 → 系统 → 显示 → 图形设置 → 浏览到 python.exe → 选项 → 高性能",
                      flush=True)
            else:
                print(f"[gpu] 渲染显卡: {_name}", flush=True)
        except Exception:
            pass
        self.listener = None
        print("[key] GLFW 键盘已启用：W/S 前后 A/D 平移 Q/E 转向 空格停 Tab 切视角 Esc 退出",
              flush=True)

    def cycle_camera(self) -> None:
        """Tab 循环切机位（旧版 2/4 与速度键冲突，改用单键循环）。"""
        if not hasattr(self, "_cam_cycle"):
            self._cam_cycle = 0
        names = ["overview", "walker", "side", "top"]
        name = names[self._cam_cycle % len(names)]
        self._cam_cycle += 1
        cid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_CAMERA, name)
        if cid < 0:
            self.viewer.cam.type = CAM_FREE
            print(f"\n[cam] 场景无 {name}，切到自由视角（鼠标拖动）", flush=True)
        else:
            self.viewer.cam.type = CAM_FIXED
            self.viewer.cam.fixedcamid = cid
            print(f"\n[cam] 机位 → {name}", flush=True)

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
    parser.add_argument("--duration", type=float, default=3600.0,
                        help="仿真时长上限（秒），默认 1 小时；体验时不用管")
    parser.add_argument("--maxspeed", action="store_true",
                        help="关闭实时节拍，仿真全速运行（做基准测试用）")
    parser.add_argument("--render-size", type=int, default=640,
                        help="窗口渲染分辨率宽度（默认 640，独显下 50fps 可达 90%% 实时）")
    parser.add_argument("--render-every", type=int, default=1,
                        help="每 N 个控制步渲染一次（1=50fps 最流畅；卡顿时设 2）")
    args = parser.parse_args()
    if not os.path.isfile(args.policy):
        sys.exit(f"[ERROR] 策略不存在: {args.policy}（先跑 python tools/export_policy.py）")
    if not os.path.isfile(args.model):
        sys.exit(f"[ERROR] 模型不存在: {args.model}")
    cfg = SimToSimCfg()
    cfg.sim.sim_duration = args.duration
    # 顶层兜底：任何未捕获异常都写 run_error.log 并暂停，避免窗口一闪而过看不到原因
    try:
        InteractiveRunner(cfg, args.policy, args.model,
                          realtime=not args.maxspeed,
                          render_size=args.render_size,
                          render_every=args.render_every).run(args.duration)
    except Exception:
        import traceback
        err_path = os.path.join(ROOT_DIR, "run_error.log")
        with open(err_path, "w", encoding="utf-8") as f:
            f.write("参数: " + " ".join(sys.argv[1:]) + "\n\n")
            traceback.print_exc(file=f)
        print("\n[ERROR] 程序异常，详情已写入:", err_path, flush=True)
        traceback.print_exc()
    finally:
        # 双击 bat 时防止窗口立刻关闭，留时间看报错
        try:
            input("\n按回车键退出...")
        except Exception:
            pass
