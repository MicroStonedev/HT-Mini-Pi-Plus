# 一天冲刺：Mini Pi+ 真机 Project Prototype/Demo 方案

> 条件：**真机 Mini Pi+ 到位 + 仅 1 天时间** + 10 分钟展示
> 主课题：高擎方向二（RL 运控 + Sim2Real）｜辅课题：群核方向二（真实空间 → 仿真场景）
> 核心原则：**真机走起来是主线，仿真与群核场景是保险和加分项。每个环节都有时间熔断线，卡住就切保底方案，绝不在一个坑里耗死。**

---

## 0. 一天开始前（前一晚必须完成）

下载与准备（现场网络不可靠，全部提前备好）：

```bash
# Windows 笔记本（仿真与展示机）
git clone https://github.com/HighTorque-Robotics/Mini-Pi-Plus_AMP.git
git clone https://github.com/HighTorque-Robotics/HT_Robot_URDF.git
pip install mujoco==3.3.2 torch
# 提前验证：官方 checkpoint 能在本机 MuJoCo 行走（这一步前一晚就要跑通！）
python legged_lab/scripts/sim2sim_pi_plus.py --policy=Exported_policy/model_40000.pt --model=legged_lab/assets/hightorque/pi_plus/pi_plus.xml --duration=30
```

- 下载群核素材包教室场景 PLY（studio.aholo3d.cn/library，「余姚第四中学空教室」）
- 克隆 `sim2real-inference_code_ros2` 和 `HT_Policy-Format-Convert` 到 U 盘/笔记本
- **硬件清单**：机器人电池充满 ×2、游戏手柄（装电池）、网线、吊装架或横杆+绑带（挂起测试用）、急停可用、开阔测试区（≥3m×3m）
- 人员分工：
  - **A（主操作手）**：真机部署，全程不换人
  - **B（仿真）**：MuJoCo + 群核场景 + 扰动测试
  - **C（记录）**：录像、日志截图、PPT

## 1. 已核实的官方部署链路（照做即可）

真机推理跑在**机器人自带 RK3588 控制器**上（Ubuntu 20.04 + ROS2 Foxy），流程：

1. 机器人上电 → 按官方教程 `First Run` / `Bringup` 章节（hightorque.cn/pi-plus-from-scratch/）连上机器人、配对手柄
2. 进入开发者模式，确认三个话题存在：`/sim2real_master_node/rbt_state`、`/sim2real_master_node/mtr_state`、`/yesense_imu/imu`
3. 在机器人上编译推理包：`colcon build --packages-select hightorque_rl_inference`
4. 策略模型为 **RKNN 格式**（`.rknn` 放入 `policy/`）——**仓库自带示例模型** `policy_0322_12dof_4000.rknn`，这是真机保底
5. 状态机切模：**STANDBY**（手柄 LT+RT+START，动作缩放 0.05 安全模式）→ 验证无误 → **RUNNING**（LT+RT+LB）
6. 速度指令限制：x ∈ [-0.55, 0.55]、y ∈ [-0.3, 0.3]、yaw ∈ [-2.0, 2.0]

**✅ 已核实的 Mini Pi+（22 自由度）部署形态**：官方两个推理仓库（ROS1/ROS2）均为 **12 维腿部策略**（双腿各 6 关节：髋 pitch/roll/yaw、膝、踝 pitch/roll）——这是 Mini Pi+ 官方行走的部署形态：**策略只控双腿 12 关节，手臂关节保持默认位姿**。当天第一小时仍需核实：开发者模式下查看关节话题，确认手臂 10 关节处于固定位/阻尼状态、不参与策略输出。配置层面逐字段核对：checkpoint 动作维度(12) ↔ `config_example.yaml` 的 `num_actions` ↔ `map_index`/`motor_direction` 映射。**`map_index` 配错是官方 README 点名的"机器人行为异常"头号原因。**

补充（官方教程 `Sim2Real Deployment` 章节的标准流程，供自研模型走标准链路时参照）：训练侧导出 `actor.onnx` + `metadata.json`（含观测顺序、动作缩放、默认关节位姿）→ 运行时 `obs → onnx → target_q = q_default + scale*action → PD 控力矩` → 安全层（关节限位/力矩裁剪/看门狗）→ **零动作验证（action=0 必须稳定无漂移）→ 渐进激活（零动作→小幅→单关节→完整策略）**。策略 50Hz / 控制器 500Hz 的频率对齐也在该章说明。

---

## 2. 逐小时作战表

### 9:00–11:00｜双线启动（互为保险）

**A 线（真机）**
- 开箱检查、电池装入、上电、按 `First Run` 连接（网络/SSH）、手柄配对
- 跑**官方预装/自带 rknn 示例模型**的行走 → ✅ 此时真机保底已成立（官方策略能走）
- 过一遍 `Safety & Teleoperation` 章节的急停操作，全场周知

**B 线（仿真）**
- 复跑前一晚已验证的官方 checkpoint sim2sim（确认环境没坏）
- 群核教室 PLY 简化（≤50k 面，只留地面+低处障碍）→ 生成 `scene_classroom.xml`
- 在重建教室场景里跑官方 checkpoint，录屏

**C 线**
- 全程录像开始；截取 B 线成果；起草架构图（真实空间 → 重建 → 仿真 → 真机 四段式）

### 11:00–12:00｜自研模型转换

- 用 `HT_Policy-Format-Convert`：AMP 仓库 `Exported_policy/policy.pt` → ONNX → RKNN
- 逐项核对 `config_example.yaml`：模型名、`num_actions`、`clip_actions(±18.0)`、`motor_direction`、`map_index`、`action_scale`
- **不急于上机**，先完成配置审查（对照官方示例模型的 config 逐字段比对）

### 12:00–13:00｜午休（A 线留一人给机器人充电、整理线缆）

### 13:00–15:00｜部署窗口（全天最长不确定段）

顺序严格从安全到放开：
1. **挂起测试**：吊装/绑横杆，加载我们的 rknn，进 **STANDBY**（0.05 缩放）看关节响应方向是否正确
2. 关节方向/幅度异常 → 立即回查 `map_index`、`motor_direction`（90% 是这里）
3. 挂起下切 **RUNNING**，小幅行走，看步态是否成形
4. 落地：双人左右保护，先原地踏步 → 前进 0.2 m/s 短距离 → 逐步放开到 0.5 m/s

**⏱ 熔断线：15:00**。自研模型若仍未稳定行走 → 永久切换到仓库自带示例 rknn 完成后续所有环节（演示链路完整：转换工具、部署流程、状态机都是我们做的，仅策略权重用官方——PPT 里诚实标注即可）。

### 15:00–17:00｜正式素材采集

- 真机多角度录像：起立→行走→转向→停止，多拍几条（含一两次失败-恢复片段，展示真实性）
- B 线完成扰动测试录屏：MuJoCo 里给行走中的机器人施加推力（`xfrc_applied`），展示策略抗扰恢复
- 群核场景 demo 录屏定稿：重建教室里行走 30 秒

### 17:00–19:00｜误差分析 + PPT

一天踩的坑就是最好的误差分析素材，逐条写成表：

| 误差来源 | 今天的表现 | 证据 |
|----------|-----------|------|
| 关节映射（map_index/motor_direction） | 挂起测试时方向错乱 | 录像+日志 |
| PD 增益差异 | STANDBY 阶段跟踪迟滞 | 对比官方 config |
| IMU 坐标/零偏 | 起立瞬间偏航 | 录像 |
| 执行器延迟 | sim 里稳定、真机前倾 | sim2sim vs 真机对比视频 |
| 重建场景 vs 真实地面 | 教室场景摩擦差异 | 两个 sim 场景对比 |

PPT ≤10 页：架构图 1、demo 流程 1、真机视频 2、群核场景 1、误差分析 1、结论 1。

### 19:00–20:00｜彩排 + 收尾

- 按脚本完整走一遍（含设备转场：笔记本→视频→真机）
- 机器人充电、急停复位、清点配件

---

## 3. 10 分钟展示脚本

| 时间 | 内容 | 形式 |
|------|------|------|
| 0:00–1:00 | 方向二定位 + 四段式架构图（群核重建→仿真→sim2sim→真机） | PPT |
| 1:00–5:00 | **真机现场 demo**：STANDBY→RUNNING 起立行走；空间不足则播放剪辑视频 | 现场/视频 |
| 5:00–7:00 | **群核环节**：MuJoCo live——官方 checkpoint 在重建教室场景行走 + 推力扰动 | 笔记本现场 |
| 7:00–9:00 | 误差来源分析（上表的现场版，附当日日志截图） | PPT |
| 9:00–10:00 | 结论：完整链路已通，后续接自训练策略 + SpatialLM 自动场景生成 | PPT |

现场翻车保险：真机环节备完整备份视频；笔记本 sim 提前跑通并录屏备份。

## 4. 风险熔断表（一天方案的生命线）

| 风险 | 熔断时限 | 保底动作 |
|------|----------|----------|
| 自研 rknn 上机后行为异常 | 15:00 | 切官方自带 rknn，PPT 诚实标注 |
| 模型转换工具链报错 | 12:00 | 直接用自带 rknn（跳过转换环节） |
| 机器人连接/开发者模式问题 | 11:00 | 官方 Troubleshooting 章节；仍不行→真机环节改为官方预装 demo + 部署链路讲解视频 |
| 群核 PLY 转换卡住 | 11:30 | 放弃本地场景，改为在线漫游展示重建场景 + 平地 sim |
| 场地太小真机不能走 | — | 提前确认教室/走廊；视频为主现场为辅 |

## 5. 当天交付物清单（对着打勾）

- [ ] 真机行走视频（自研模型 或 官方模型+我们的部署，二者至少其一）
- [ ] MuJoCo live demo 可现场运行（平地 + 重建教室两个场景）
- [ ] 10 分钟 PPT + 备份视频
- [ ] 误差分析表（附日志/录像证据）
- [ ] 代码/配置快照：config、转换脚本调用记录、sim2sim 命令（放进仓库即"可复现记录"的雏形）
