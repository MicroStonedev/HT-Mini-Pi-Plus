# Copyright (c) 2021-2024, The RSL-RL Project Developers.
# All rights reserved.
# Original code is licensed under the BSD-3-Clause license.
#
# Copyright (c) 2022-2025, The Isaac Lab Project Developers.
# All rights reserved.
#
# Copyright (c) 2025-2026, The Legged Lab Project Developers.
# All rights reserved.
#
# Copyright (c) 2025-2026, The TienKung-Lab Project Developers.
# All rights reserved.
# Modifications are licensed under the BSD-3-Clause license.
#
# This file contains code derived from the RSL-RL, Isaac Lab, and Legged Lab Projects,
# with additional modifications by the TienKung-Lab Project,
# and is distributed under the BSD-3-Clause license.

import argparse
import os
import re
from typing import Optional

import torch
from isaaclab.app import AppLauncher

from legged_lab.utils import task_registry
from rsl_rl.runners import AmpOnPolicyRunner, OnPolicyRunner

# local imports
import legged_lab.utils.cli_args as cli_args  # isort: skip

# add argparse arguments
parser = argparse.ArgumentParser(description="Train an RL agent with RSL-RL.")
parser.add_argument("--task", type=str, default=None, help="Name of the task.")
parser.add_argument("--num_envs", type=int, default=None, help="Number of environments to simulate.")
parser.add_argument("--seed", type=int, default=None, help="Seed used for the environment")

# append RSL-RL cli arguments
cli_args.add_rsl_rl_args(parser)
# append AppLauncher cli args
AppLauncher.add_app_launcher_args(parser)
args_cli, hydra_args = parser.parse_known_args()
args_cli.enable_cameras = True  # camera_record: 强制相机渲染
# Start camera rendering
if "sensor" in args_cli.task:
    args_cli.enable_cameras = True

# launch omniverse app
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

from isaaclab_rl.rsl_rl import export_policy_as_jit, export_policy_as_onnx
from isaaclab_tasks.utils import get_checkpoint_path

from legged_lab.envs import *  # noqa:F401, F403
from legged_lab.utils.cli_args import update_rsl_rl_cfg

import pygame
from threading import Thread
import sys
import signal
import atexit
# 全局变量
x_vel_cmd, y_vel_cmd, yaw_vel_cmd = 0.0, 0.0, 0.0
x_vel_max, y_vel_max, yaw_vel_max = 1.2, 0.8, 1.57

joystick_use = True
joystick_opened = False
exit_flag = False
joystick_thread = None
joystick = None


def resolve_checkpoint_path(log_root_path: str, load_run: Optional[str], load_checkpoint: str) -> str:
    """Resolve a checkpoint from an explicit path or the standard log layout.

    IsaacLab's ``get_checkpoint_path`` treats ``load_run`` as a directory
    pattern. A user-facing play command is also commonly given a direct
    ``.pt`` path, so handle that form before delegating to IsaacLab.
    """

    candidates = []
    for value in (load_run, load_checkpoint):
        if not value:
            continue
        path = os.path.abspath(value)
        if os.path.isfile(path):
            return path
        candidates.append(path)

    # Support checkpoints placed directly in the experiment directory, as
    # well as the usual logs/<experiment>/<run>/model_*.pt layout.
    root_checkpoints = [
        os.path.join(log_root_path, name)
        for name in os.listdir(log_root_path)
        if os.path.isfile(os.path.join(log_root_path, name))
    ] if os.path.isdir(log_root_path) else []
    matching_root_checkpoints = [
        path for path in root_checkpoints if re.match(load_checkpoint, os.path.basename(path))
    ]
    if matching_root_checkpoints:
        matching_root_checkpoints.sort(key=lambda path: f"{os.path.basename(path):0>15}")
        return matching_root_checkpoints[-1]

    try:
        return get_checkpoint_path(log_root_path, load_run, load_checkpoint)
    except ValueError as exc:
        explicit = ", ".join(candidates) if candidates else "none"
        raise ValueError(
            f"Unable to find a checkpoint. Checked explicit paths: {explicit}; "
            f"run directories under '{log_root_path}' with checkpoint pattern '{load_checkpoint}'. "
            "Pass --load_run with a run directory or a .pt file path."
        ) from exc


def cleanup_resources():
    """清理资源的函数"""
    global exit_flag, joystick_thread, joystick
    
    print("正在清理手柄资源...")
    exit_flag = True
    
    # 等待手柄线程结束
    if joystick_thread and joystick_thread.is_alive():
        joystick_thread.join(timeout=2.0)  # 最多等待2秒
        if joystick_thread.is_alive():
            print("警告：手柄线程未能正常退出")
    
    # 清理pygame资源
    if joystick:
        try:
            joystick.quit()
        except:
            pass
    
    try:
        pygame.quit()
    except:
        pass
    
    print("手柄资源清理完成")

def signal_handler(signum, frame):
    """信号处理器，用于捕获Ctrl+C等信号"""
    print(f"\n接收到信号 {signum}，正在退出...")
    cleanup_resources()
    sys.exit(0)

if joystick_use:
    # 注册清理函数
    atexit.register(cleanup_resources)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    pygame.init()

    try:
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        joystick_opened = True
        print("手柄初始化成功")
    except Exception as e:
        print(f"无法打开手柄设备: {e}")
        joystick_use = False

    def handle_joystick_input():
        global exit_flag, x_vel_cmd, y_vel_cmd, yaw_vel_cmd
        
        print("手柄输入线程启动")
        while not exit_flag:
            try:
                pygame.event.get()
                
                if joystick and joystick.get_init():
                    x_vel_cmd = -joystick.get_axis(1) * x_vel_max
                    y_vel_cmd = -joystick.get_axis(0) * y_vel_max
                    yaw_vel_cmd = -joystick.get_axis(3) * yaw_vel_max
                
                pygame.time.delay(100)
            except Exception as e:
                print(f"手柄输入处理错误: {e}")
                break
        
        print("手柄输入线程退出")

    # 启动手柄线程
    if joystick_opened and joystick_use:
        joystick_thread = Thread(target=handle_joystick_input, daemon=True)
        joystick_thread.start()
        print("手柄线程已启动")


def play():
    runner: OnPolicyRunner
    env_cfg: BaseEnvCfg  # noqa:F405

    env_class_name = args_cli.task
    env_cfg, agent_cfg = task_registry.get_cfgs(env_class_name)

    env_cfg.noise.add_noise = False
    env_cfg.domain_rand.events.push_robot = None
    env_cfg.scene.max_episode_length_s = 40.0
    env_cfg.scene.num_envs = 50
    env_cfg.scene.env_spacing = 2.5
    env_cfg.commands.rel_standing_envs = 0.0
    env_cfg.commands.ranges.lin_vel_x = (1.0, 1.0)
    env_cfg.commands.ranges.lin_vel_y = (0.0, 0.0)
    env_cfg.scene.height_scanner.drift_range = (0.0, 0.0)

    env_cfg.scene.terrain_generator = None
    env_cfg.scene.terrain_type = "plane"

    if env_cfg.scene.terrain_generator is not None:
        env_cfg.scene.terrain_generator.num_rows = 5
        env_cfg.scene.terrain_generator.num_cols = 5
        env_cfg.scene.terrain_generator.curriculum = False
        env_cfg.scene.terrain_generator.difficulty_range = (0.4, 0.4)

    # --- camera_record: 挂第三人称 RGB 相机 ---
    from legged_lab.sensors.camera import CameraCfg
    from isaaclab.sim import PinholeCameraCfg
    _dc = env_cfg.scene.depth_camera
    _dc.enable_depth_camera = True
    _dc.prim_body_name = "base_link"
    _dc.data_types = ["rgb"]
    _dc.width = 640
    _dc.height = 480
    _dc.debug_vis = False
    _dc.offset = CameraCfg.OffsetCfg(pos=(-2.2, -1.2, 0.9), rot=(0.44, 0.0, 0.90, 0.0), convention="ros")
    _dc.spawn = PinholeCameraCfg(focal_length=1.24, horizontal_aperture=2.4, clipping_range=(0.2, 15.0))
    print("[CAM] third-person rgb camera injected", flush=True)

    if args_cli.num_envs is not None:
        env_cfg.scene.num_envs = args_cli.num_envs

    agent_cfg = update_rsl_rl_cfg(agent_cfg, args_cli)
    env_cfg.scene.seed = agent_cfg.seed

    env_class = task_registry.get_task_class(env_class_name)
    env = env_class(env_cfg, args_cli.headless)

    log_root_path = os.path.join("logs", agent_cfg.experiment_name)
    log_root_path = os.path.abspath(log_root_path)
    print(f"[INFO] Loading experiment from directory: {log_root_path}")
    resume_path = resolve_checkpoint_path(log_root_path, agent_cfg.load_run, agent_cfg.load_checkpoint)
    log_dir = os.path.dirname(resume_path)

    runner_class: OnPolicyRunner | AmpOnPolicyRunner = eval(agent_cfg.runner_class_name)
    runner = runner_class(env, agent_cfg.to_dict(), log_dir=log_dir, device=agent_cfg.device)
    if isinstance(runner, AmpOnPolicyRunner):
        # Playback only needs the actor. Older AMP checkpoints may have a
        # discriminator for a previous observation dimension (80 vs 104).
        runner.load(resume_path, load_optimizer=False, load_discriminator=False)
    else:
        runner.load(resume_path, load_optimizer=False)

    policy = runner.get_inference_policy(device=env.device)

    export_model_dir = os.path.join(os.path.dirname(resume_path), "exported")
    export_policy_as_jit(runner.alg.policy, runner.obs_normalizer, path=export_model_dir, filename="policy.pt")
    export_policy_as_onnx(
        runner.alg.policy, normalizer=runner.obs_normalizer, path=export_model_dir, filename="policy.onnx"
    )

    if not args_cli.headless:
        from legged_lab.utils.keyboard import Keyboard

        keyboard = Keyboard(env)  # noqa:F841

    obs, _ = env.get_observations()

    step_count, resets, prev_elb = 0, 0, 0
    _frames = []
    while simulation_app.is_running():

        with torch.inference_mode():
            if FIX_COMMAND:
                env.command_generator.command[:, 0] = 1.0
                env.command_generator.command[:, 1] = 0.
                env.command_generator.command[:, 2] = 0.0
            else:
                env.command_generator.command[:, 0] = x_vel_cmd
                env.command_generator.command[:, 1] = y_vel_cmd
                env.command_generator.command[:, 2] = yaw_vel_cmd
            actions = policy(obs)
            obs, rew, _, _ = env.step(actions)
            step_count += 1
            if hasattr(env, "depth_camera"):
                _rgb = env.depth_camera.data.output["rgb"]
                _frames.append(_rgb[0, :, :, :3].detach().cpu().numpy())
            if step_count * float(env.step_dt) >= getattr(args_cli, "video_sec", 60):
                import imageio.v2 as _iio
                _out = getattr(args_cli, "video_out", "/home/ubuntu/isaac_cam.mp4")
                _iio.mimwrite(_out, _frames[::2], fps=25, quality=8)
                _iio.imwrite(_out.replace(".mp4", "_first.png"), _frames[0])
                _iio.imwrite(_out.replace(".mp4", "_mid.png"), _frames[len(_frames)//2])
                print(f"[CAM-DONE] {len(_frames)}帧 -> {_out}", flush=True)
                break
            _elb = int(env.episode_length_buf[0].item())
            if _elb < prev_elb:
                resets += 1
                print(f"[RESET] sim_t={step_count*float(env.step_dt):.1f}s ep_len {prev_elb}->{_elb}", flush=True)
            prev_elb = _elb
            if step_count % 250 == 0:
                print(f"[RUN] sim_t={step_count*float(env.step_dt):.1f}s steps={step_count} resets={resets} reward={float(rew[0]):.3f}", flush=True)


if __name__ == "__main__":
    FIX_COMMAND = False
    play()
    simulation_app.close()
