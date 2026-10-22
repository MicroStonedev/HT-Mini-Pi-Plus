# -*- coding: utf-8 -*-
"""Mini Pi+ 无头 sim2sim 运行器（headless）。

复刻官方 third_party/Mini-Pi-Plus_AMP/legged_lab/scripts/sim2sim_pi_plus.py 的
观测构建 / PD 控制 / 动作映射逻辑，去掉 viewer/手柄/键盘依赖，增加：
  - 推力扰动注入（xfrc_applied，作用于 base）
  - 遥测记录（基座高度 / 姿态 / 位移 / 动作）
  - 定量指标：存活时间、平均基高、前向速度、跌倒检测

用法（作为库）：
    from mujoco_pi_plus_walk import WalkRunner, WalkParams
    runner = WalkRunner(policy_path, model_path)
    result = runner.run(duration_s=10.0, cmd=(0.5, 0, 0))
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import mujoco
import numpy as np
import torch
import torch.nn as nn


@dataclass
class WalkParams:
    """与官方 SimToSimCfg 保持一致的参数。"""
    num_action: int = 20
    num_obs_per_step: int = 69
    actor_obs_history_length: int = 5
    dt: float = 0.002
    decimation: int = 10
    clip_observations: float = 100.0
    clip_actions: float = 100.0
    action_scale: float = 0.25
    spawn_height: float = 0.39
    # 扰动：每 push_interval_s 施加 push_duration_s 的水平力（牛顿）
    push_force: float = 0.0
    push_interval_s: float = 3.0
    push_duration_s: float = 0.15
    # 跌倒判定：基座高度低于该值认为摔倒
    fall_height: float = 0.22
    # 地面摩擦（覆盖模型默认值，用于消融实验；None 表示不改）
    floor_friction: float | None = None


DEFAULT_DOF_POS = np.array([
    -0.25, 0.0, 0.0, 0.65, -0.4, 0.0, 0.0, 0.2, 0.0, -1.2,
    -0.25, 0.0, 0.0, 0.65, -0.4, 0.0, 0.0, -0.2, 0.0, -1.2,
])
KPS = [80, 80, 80, 80, 60, 60, 30, 30, 30, 30] * 2
KDS = [1.1, 1.1, 1.1, 1.1, 1.2, 1.2, 0.6, 0.6, 0.6, 0.6] * 2
ISAAC_TO_MUJOCO_IDX = [0, 4, 8, 12, 16, 18, 1, 5, 9, 13, 2, 6, 10, 14, 17, 19, 3, 7, 11, 15]
MUJOCO_TO_ISAAC_IDX = [0, 6, 10, 16, 1, 7, 11, 17, 2, 8, 12, 18, 3, 9, 13, 19, 4, 14, 5, 15]


def load_policy(path: str) -> torch.nn.Module:
    """加载 TorchScript 策略；失败则从训练 checkpoint 重建 actor（与官方脚本一致）。"""
    try:
        policy = torch.jit.load(path, map_location="cpu")
        policy.eval()
        return policy
    except RuntimeError:
        pass
    # 训练 checkpoint 反序列化需要仓库内的 rsl_rl / legged_lab 模块
    import sys
    _repo_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "third_party", "Mini-Pi-Plus_AMP")
    for _sub in (_repo_root, os.path.join(_repo_root, "rsl_rl")):
        if os.path.isdir(_sub) and _sub not in sys.path:
            sys.path.insert(0, _sub)

    class _Any:
        """pickle 中自定义类的替身：只保证能反序列化，不参与计算。"""
        def __init__(self, *a, **k): pass
        def __setstate__(self, state): pass
        def __reduce__(self): return (_Any, ())

    def _stub_module(name: str):
        import types
        mod = types.ModuleType(name)
        mod.__getattr__ = lambda attr: _Any  # PEP 562
        sys.modules[name] = mod
        return mod

    for _name in ("rsl_rl", "rsl_rl.utils", "rsl_rl.utils.utils", "legged_lab"):
        if _name not in sys.modules:
            _stub_module(_name)
    try:
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        checkpoint = torch.load(path, map_location="cpu")
    state_dict = checkpoint["model_state_dict"]
    actor_keys = [k for k in state_dict if k.startswith("actor.")]
    weight_keys = [k for k in actor_keys if k.endswith(".weight")]
    input_dim = state_dict[weight_keys[0]].shape[1]
    hidden_dims = [state_dict[k].shape[0] for k in weight_keys[:-1]]
    output_dim = state_dict[weight_keys[-1]].shape[0]
    layers, in_dim = [], input_dim
    for h in hidden_dims:
        layers += [nn.Linear(in_dim, h), nn.ELU()]
        in_dim = h
    layers.append(nn.Linear(in_dim, output_dim))
    actor = nn.Sequential(*layers)
    actor_state = {k[len("actor."):]: v for k, v in state_dict.items() if k.startswith("actor.")}
    actor.load_state_dict(actor_state)
    actor.eval()
    print(f"[policy] checkpoint iter={checkpoint.get('iter', '?')} "
          f"actor {input_dim}->{hidden_dims}->{output_dim}")
    return actor


def quat_apply_inverse(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    q_w, q_vec = q[-1], q[:3]
    a = v * (2.0 * q_w**2 - 1.0)
    b = np.cross(q_vec, v) * q_w * 2.0
    c = q_vec * np.dot(q_vec, v) * 2.0
    return a - b + c


@dataclass
class WalkResult:
    survived: bool
    fall_time_s: float          # 未跌倒时 = duration
    duration_s: float
    base_height_mean: float
    base_height_min: float
    forward_displacement: float  # x 方向位移
    mean_forward_vel: float
    world_xy: tuple = (0.0, 0.0)           # 世界系 xy 位移（旋转出生时用于核对）
    telemetry: dict = field(default_factory=dict)  # time/z/roll_pitch/xy/fwd 数组


class WalkRunner:
    def __init__(self, policy_path: str, model_path: str, params: WalkParams | None = None):
        self.p = params or WalkParams()
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.model.opt.timestep = self.p.dt
        if self.p.floor_friction is not None:
            self._set_floor_friction(self.p.floor_friction)
        self.data = mujoco.MjData(self.model)
        self.policy = load_policy(policy_path)
        self.base_body_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "base_link")
        # 出生高度取模型里 base_link 的初始 z（场景可能带地面偏移）
        self.spawn_z = float(self.model.body_pos[self.base_body_id][2])

    def override_model(self, model, data) -> None:
        """用外部已构造的 model/data 替换内部实例（渲染脚本复用推进逻辑时用）。"""
        self.model, self.data = model, data

    def _set_floor_friction(self, friction: float) -> None:
        """把所有 'floor' 类命名的 geom 摩擦改为给定值，并同步两足默认摩擦。"""
        for i in range(self.model.ngeom):
            name = mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_GEOM, i) or ""
            if "floor" in name.lower() or self.model.geom_type[i] == mujoco.mjtGeom.mjGEOM_PLANE:
                self.model.geom_friction[i] = [friction, 0.005, 0.0001]

    def _reset(self) -> None:
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[7:] = DEFAULT_DOF_POS.copy()
        self.data.qpos[2] = self.spawn_z
        mujoco.mj_forward(self.model, self.data)
        self.action = np.zeros(self.p.num_action)
        self.obs_history = np.zeros(
            self.p.num_obs_per_step * self.p.actor_obs_history_length, dtype=np.float32)

    def _get_obs(self, cmd: np.ndarray) -> np.ndarray:
        dof_pos, dof_vel = self.data.qpos[7:], self.data.qvel[6:]
        obs = np.zeros(self.p.num_obs_per_step, dtype=np.float32)
        obs[0:3] = self.data.sensor("angular-velocity").data
        obs[3:6] = quat_apply_inverse(
            self.data.sensor("orientation").data[[1, 2, 3, 0]], np.array([0, 0, -1]))
        obs[6:9] = cmd
        obs[9:29] = (dof_pos - DEFAULT_DOF_POS)[MUJOCO_TO_ISAAC_IDX]
        obs[29:49] = dof_vel[MUJOCO_TO_ISAAC_IDX]
        obs[49:69] = np.clip(self.action, -self.p.clip_actions, self.p.clip_actions)
        self.obs_history = np.roll(self.obs_history, -self.p.num_obs_per_step)
        self.obs_history[-self.p.num_obs_per_step:] = obs
        return np.clip(self.obs_history, -self.p.clip_observations, self.p.clip_observations)

    def run(self, duration_s: float = 10.0, cmd: tuple = (0.5, 0.0, 0.0),
            seed: int = 0, verbose: bool = True) -> WalkResult:
        rng = np.random.default_rng(seed)
        self._reset()
        # 初始朝向（世界系）：由 base 四元数推得，用于统计"前进"位移
        self.start_xy = self.data.qpos[:2].copy()
        q = self.data.qpos[3:7]
        # 四元数 (w,x,y,z) 的旋转矩阵第 0 列 = 机体 +x 轴在世界系的方向
        self.fwd_dir = np.array([1 - 2 * (q[2] ** 2 + q[3] ** 2),
                                 2 * (q[0] * q[3] + q[1] * q[2])])
        cmd_arr = np.asarray(cmd, dtype=np.float32)
        push_dir = rng.uniform(0, 2 * np.pi)  # 本回合扰动方向固定
        tele = {"t": [], "z": [], "roll_pitch": [], "x": [], "y": [], "fwd": []}
        fall_time = duration_s
        control_dt = self.p.decimation * self.p.dt

        while self.data.time < duration_s:
            obs = self._get_obs(cmd_arr)
            with torch.no_grad():
                action = self.policy(torch.tensor(obs, dtype=torch.float32).unsqueeze(0))
            self.action[:] = action.numpy()[0, :self.p.num_action]
            self.action = np.clip(self.action, -self.p.clip_actions, self.p.clip_actions)
            target = self.action * self.p.action_scale
            target_dof_pos = target[ISAAC_TO_MUJOCO_IDX] + DEFAULT_DOF_POS

            # 推力扰动：周期性水平推基座
            phase = self.data.time % self.p.push_interval_s
            if self.p.push_force > 0 and phase < self.p.push_duration_s:
                fx = self.p.push_force * np.cos(push_dir)
                fy = self.p.push_force * np.sin(push_dir)
            else:
                fx = fy = 0.0
            self.data.xfrc_applied[self.base_body_id, [0, 1]] = [fx, fy]

            for _ in range(self.p.decimation):
                tau = (target_dof_pos - self.data.qpos[7:]) * KPS \
                    - self.data.qvel[6:] * KDS
                self.data.ctrl = tau
                mujoco.mj_step(self.model, self.data)

            z = float(self.data.qpos[2])
            tele["t"].append(self.data.time)
            tele["z"].append(z)
            quat = self.data.sensor("orientation").data[[1, 2, 3, 0]]
            roll = np.degrees(np.arctan2(2 * (quat[3] * quat[0] + quat[1] * quat[2]),
                                         1 - 2 * (quat[0] ** 2 + quat[1] ** 2)))
            pitch = np.degrees(np.arcsin(np.clip(2 * (quat[3] * quat[1] - quat[2] * quat[0]), -1, 1)))
            tele["roll_pitch"].append((roll, pitch))
            tele["x"].append(float(self.data.qpos[0]))
            tele["y"].append(float(self.data.qpos[1]))
            tele["fwd"].append(float(np.dot(
                self.data.qpos[:2] - self.start_xy, self.fwd_dir)))
            if z < self.p.fall_height:
                fall_time = self.data.time
                break

        z_arr = np.array(tele["z"])
        result = WalkResult(
            survived=fall_time >= duration_s,
            fall_time_s=round(fall_time, 2),
            duration_s=duration_s,
            base_height_mean=round(float(z_arr.mean()), 3),
            base_height_min=round(float(z_arr.min()), 3),
            forward_displacement=round(tele["fwd"][-1], 3),
            mean_forward_vel=round(tele["fwd"][-1] / max(tele["t"][-1], 1e-6), 3),
            world_xy=(round(tele["x"][-1] - tele["x"][0], 3),
                      round(tele["y"][-1] - tele["y"][0], 3)),
            telemetry=tele,
        )
        if verbose:
            status = "存活" if result.survived else f"于 {result.fall_time_s}s 跌倒"
            print(f"[run] {status} | 平均基高 {result.base_height_mean} m | "
                  f"沿朝向前进 {result.forward_displacement} m | "
                  f"平均速度 {result.mean_forward_vel} m/s | 世界位移 {result.world_xy}")
        return result


AMP_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "third_party", "Mini-Pi-Plus_AMP")
DEFAULT_MODEL = os.path.join(AMP_ROOT, "legged_lab", "assets", "hightorque", "pi_plus", "pi_plus.xml")
DEFAULT_POLICY = os.path.join(AMP_ROOT, "Exported_policy", "model_40000.pt")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Headless sim2sim 行走验证")
    parser.add_argument("--policy", default=DEFAULT_POLICY)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--cmd", type=float, nargs=3, default=[0.5, 0.0, 0.0],
                        help="x/y/yaw 速度指令")
    parser.add_argument("--push", type=float, default=0.0, help="推力扰动大小(N)，0=关闭")
    parser.add_argument("--friction", type=float, default=None, help="覆盖地面摩擦系数")
    args = parser.parse_args()
    params = WalkParams(push_force=args.push, floor_friction=args.friction)
    runner = WalkRunner(args.policy, args.model, params)
    runner.run(args.duration, tuple(args.cmd))
