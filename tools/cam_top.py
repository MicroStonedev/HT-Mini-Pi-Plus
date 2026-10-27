"""Minimal Isaac camera recording: top-down view + forced walking"""
import argparse, os
parser = argparse.ArgumentParser()
parser.add_argument("--task", default="pi_plus_amp_sym_flat")
parser.add_argument("--load_run", default=None)
parser.add_argument("--checkpoint", default=None)
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--headless", action="store_true")
parser.add_argument("--video_sec", type=float, default=20)
args, _ = parser.parse_known_args()
args.enable_cameras = True

from isaaclab.app import AppLauncher
app = AppLauncher(args).app

import torch
from legged_lab.envs import *
from legged_lab.utils import task_registry

# env config
env_cfg, agent_cfg = task_registry.get_cfgs(args.task)
env_cfg.scene.num_envs = 1
env_cfg.scene.seed = 42
env_cfg.commands.resampling_time_range = (9999.0, 9999.0)

# camera: top-down
from legged_lab.sensors.camera import CameraCfg
from isaaclab.sim import PinholeCameraCfg
_dc = env_cfg.scene.depth_camera
_dc.enable_depth_camera = True
_dc.prim_path = "/World/envs/env_0/Cam_top"
_dc.data_types = ["rgb", "distance_to_image_plane"]
_dc.width = 640; _dc.height = 480; _dc.debug_vis = False
_dc.offset = CameraCfg.OffsetCfg(pos=(0, 0, 1.0), rot=(0, 1, 0, 0), convention="ros")
_dc.spawn = PinholeCameraCfg(focal_length=1.24, horizontal_aperture=2.4, clipping_range=(0.2, 15))

agent_cfg.load_run = args.load_run or "2026-10-24_19-53-37"
agent_cfg.load_checkpoint = args.checkpoint or "model_14999.pt"

env_class = task_registry.get_task_class(args.task)
env = env_class(env_cfg, True)

# load policy
import legged_lab.utils.cli_args as cli_args
from rsl_rl.runners import OnPolicyRunner, AmpOnPolicyRunner
log_dir = os.path.join("logs", agent_cfg.experiment_name)
resume_path = os.path.join(log_dir, agent_cfg.load_run, agent_cfg.load_checkpoint)
runner = AmpOnPolicyRunner(env, agent_cfg.to_dict(), log_dir=log_dir, device=agent_cfg.device)
runner.load(resume_path)
policy = runner.get_inference_policy(device=env.device)
print("[READY] policy loaded, starting recording", flush=True)

# recording loop
import imageio.v2 as iio
frames = []
obs, _ = env.get_observations()
t = 0
while t < args.video_sec:
    # FORCE WALK FORWARD
    env.command_generator.command[:, 0] = 1.0
    env.command_generator.command[:, 1] = 0.0
    env.command_generator.command[:, 2] = 0.0

    with torch.inference_mode():
        actions = policy(obs)
    obs, _, _, _ = env.step(actions)
    t += float(env.step_dt)

    if hasattr(env, "depth_camera"):
        rgb = env.depth_camera.data.output["rgb"]
        frames.append(rgb[0, :, :, :3].detach().cpu().numpy())
        if len(frames) % 250 == 0:
            print(f"[REC] t={t:.1f}s frames={len(frames)}", flush=True)

iio.mimwrite("/home/ubuntu/isaac_top.mp4", frames[::2], fps=25, quality=8)
iio.imwrite("/home/ubuntu/isaac_top_first.png", frames[0])
print(f"[DONE] {len(frames)} frames -> isaac_top.mp4", flush=True)
env.close()
