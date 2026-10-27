# HT-Mini-Pi-Plus-Robot

THU SIGS AIID × 高擎机电 方向二（强化学习运控与 Sim2Real，主）× 群核科技 方向二（空间数据与具身智能训练，辅）期末项目。

**当前阶段：W1 判定项已通过（2026-10-22）** —— 官方 Mini Pi+（20 自由度）策略在 MuJoCo 中稳定行走（0.51 m/s），可进入群核重建的**真实教室场景**；云端 Isaac Sim 4.5 + Isaac Lab 2.1 环境（RTX 4090）搭建完成并验证：**官方策略 Isaac 回放 365 秒连续行走、0 跌倒**（证据：`results/w1/`）。

## 快速开始

### 第 0 步：获取官方机器人资源（必须，约 33 MB）

`third_party/` 未纳入本仓库（体积 + 上游版权），首次使用需手动拉取：

```bash
git clone --depth 1 https://github.com/HighTorque-Robotics/Mini-Pi-Plus_AMP.git third_party/Mini-Pi-Plus_AMP
```

教室场景 `scenes/scene_classroom.xml` 里引用 `../third_party/.../meshes/*.STL`，
**跳过这步会报"找不到 mesh"**。若只想跑平地场景，仍需这些 STL。

> 群核原始点云（`classroom_raw.ply` 105 MB）同样不在仓库：场景 XML 已包含其全部
> 提取结果（房间尺寸、地面高度、地板色、家具包围盒），**跑场景不需要原始点云**。
> 需要重新生成场景时才要找原始 PLY（见下方第 5 步）。

```bash
# 依赖：Python 3.10+，已装 mujoco==3.3.2 / torch(CPU) / trimesh / fast-simplification / matplotlib / mujoco-python-viewer / pynput / pygame

# 1. 无头行走验证（定量指标）
python tools/mujoco_pi_plus_walk.py --duration 10
python tools/mujoco_pi_plus_walk.py --model scenes/scene_classroom.xml --duration 10   # 真实重建教室

# 2. 导出 TorchScript 策略（GUI 脚本必需，官方 checkpoint 缺 rsl_rl 依赖无法直接加载）
python tools/export_policy.py      # 输出 results/checkpoints/*_jit.pt

# 3. 官方 GUI 行走（现场 demo，小键盘 8/2/4/6/7/9 控速）
cd third_party/Mini-Pi-Plus_AMP
python legged_lab/scripts/sim2sim_pi_plus.py --duration 30 --policy ../../results/checkpoints/model_40000_jit.pt
python legged_lab/scripts/sim2sim_pi_plus.py --duration 30 --policy ../../results/checkpoints/model_40000_jit.pt --model ../../scenes/scene_classroom.xml

# 4. 合成教室（无需下载的保底场景）
python tools/scene_builder.py --synthetic

# 5. 换一个群核重建场景（studio.aholo3d.cn 登录后从项目接口取 plyPath，坐标为厘米时 --scale 0.01）
python tools/scene_builder.py --ply scenes/<新场景>.ply -o scenes/scene_new.xml --scale 0.01

# 6. 推力扰动鲁棒性评测（CSV + 曲线图 → results/）
python tools/disturbance_test.py
python tools/disturbance_test.py --friction 0.4
python tools/disturbance_test.py --scene scenes/scene_classroom.xml --pushes 0 80
```

## 目录结构

```
tools/
  mujoco_pi_plus_walk.py   # 无头 sim2sim 运行器（观测/PD 逻辑对齐官方脚本，支持推力扰动/摩擦覆盖/遥测）
  scene_builder.py         # Aholo PLY → MuJoCo 教室场景（家具聚类+AABB 合并+边界墙+演示相机）；--synthetic 合成教室
  ply_parser.py            # 3DGS/LiDAR PLY 解析（binary_little_endian，f_dc → 颜色）
  disturbance_test.py      # checkpoint × 推力 × 摩擦 消融，输出 CSV + 基座高度曲线
  export_policy.py         # 官方 checkpoint → TorchScript（GUI 脚本免 rsl_rl 依赖）
  render_scene.py          # 离屏多视角渲染检查场景
  record_demo.py           # 自动录屏：命名/跟拍机位 → MP4（25fps，results/videos/）
  sim2sim_interactive.py   # 交互仿真 GUI（键盘控速/多机位切换/实时节拍）
  play_log.py              # Isaac 回放（带仪表：仿真时长/跌倒重置计数/奖励，W1 判定取证用）
  install_isaac_recovery.sh # 云端 Isaac 环境一键复原（含 IsaacLab 源码安装与全部踩坑修法）
scenes/
  classroom_raw.ply        # 群核 Aholo 素材包：余姚第四中学空教室（禾赛激光雷达 3DGS 点云，197 万点，单位 cm）
  classroom.splat.spz      # 同素材的 3DGS 模型文件（NGSP v3 压缩格式，暂未破解，备用）
  scene_classroom.xml      # 生成的教室场景（真实地面高度/色 + 20 个真实课桌盒 + 边界墙 + 4 相机）
  scene_synthetic.xml      # 合成教室（无外部数据保底）
results/                   # 实验数据（CSV/plots/videos/checkpoints）
third_party/Mini-Pi-Plus_AMP  # 官方训练框架（BSD-3，含 3 个预训练 checkpoint）
DEMO_PLAN_KICKOFF.md       # 启动阶段 demo 方案（当前）
DEMO_PLAN_1DAY.md          # 真机部署冲刺方案（后续阶段）
DEMO_PLAN.md               # 两周完整计划（参考）
```

## 场景与数据文件清单

| 文件 | 入库 | 说明 |
|---|---|---|
| `scenes/scene_classroom.xml` | ✅ | MuJoCo 教室场景（40 KB）：房间 9.4×8.8 m、25 张课桌、讲台、黑板、边界墙、4 机位 |
| `scenes/scene_classroom.obj` | ✅ | 地板/墙面视觉网格（125 KB） |
| `scenes/scene_synthetic.xml` | ✅ | 合成教室保底场景，无外部依赖 |
| `tools/scene_builder.py` | ✅ | 点云 → 场景构建脚本 |
| `results/plots/scene_check_top.png` | ✅ | 场景俯视检查图 |
| `third_party/Mini-Pi-Plus_AMP/` | ❌ | 官方仓库（33 MB，含机器人 40 个 STL）—— 见第 0 步 |
| `scenes/classroom_raw.ply` | ❌ | 群核原始点云 105 MB（版权 + 体积）；场景 XML 已含提取结果，跑场景不需要它 |
| `scenes/classroom.splat.spz` | ❌ | 3DGS 模型文件 28.6 MB，同上 |

## 教室场景数据说明（重要，直接影响 PPT 怎么讲）

**这份点云不能直接提取桌椅**，实测三层证据：
1. 197 万点里 190 万（97%）挤在扫描者站立处 0.6m 半径内（手持激光雷达典型密度分布）
2. 桌面高度带（0.55–0.85m）俯视无课桌结构，只有一条斜向线状分布（线缆/横梁）
3. 桌腿层（0.05–0.35m）排除原点后仍是无结构连片杂点——3DGS 点云是体积散射

因此教室由"**真实数据 + 程序化布局**"组成：

| 部分 | 来源 |
|------|------|
| 房间尺寸 9.4×8.8m、地面高度 −1.4cm、地板颜色 | **真实点云**（家具点 xy 包络 / 2% 分位 / 地板层平均色） |
| 黑板 5×1.1m（底边离地 0.95m）、讲台 1.5×0.7×1.15m | 程序化，标准中学教室物理尺寸 |
| 25 张课桌 0.6×0.4m、桌面高 0.75m、座面 0.44m | 程序化，标准课桌物理尺寸，左右两列 + **中央 1.6m 宽过道** |
| 椅子 0.4×0.4m、座面 0.44m（颜色取真实家具点平均色） | 程序化 |

机器人从教室后部沿中央过道走向讲台，实测 **12s 前进 6.1m、0.51 m/s（与空地持平）**；
抗扰测试：0/40/80N 全部 100% 存活、120N 50% 存活。下一步接 SpatialLM 的结构化布局输出，
即可把"程序化布局"换成"数据驱动的真实布局"——这是当前的数据局限，也是课题下一步的明确方向。

> 注意：**不要并行运行两个 MuJoCo GUI 进程**（GLFW 窗口会创建失败）。现场演示只开一个 MuJoCo 窗口。

## 云端 Isaac 训练环境（W1 已打通）

- 平台：并行智算云 RTX 4090 ｜ Isaac Sim 4.5 + Isaac Lab 2.1（源码安装）+ torch 2.5.1
- 一键复原：`tools/install_isaac_recovery.sh`（Ubuntu 22.04，含 flatdict/setuptools、quat API 改名、COM 随机化垫片等全部修复）
- W1 判定证据：`results/w1/isaac_playback_300s_evidence.log`（365s / 0 跌倒 / 9 次重置均为回合自然到期）
- 注意：云服务器访问 GitHub 受限，代码同步走本地中转（scp）

## 说明

- 策略为官方 AMP 预训练模型（20 自由度：双腿各 6 + 双臂各 4），非自训练；自训练需 Isaac Lab（Linux+GPU），见 DEMO_PLAN.md Phase 3
- 群核教室 PLY 采集设备为禾赛激光雷达（点云），`scene_builder.py` 内置点云→高度场转换
- 上游代码遵循 BSD-3-Clause（RSL-RL / Isaac Lab / Legged Lab / TienKung-Lab），本项目工具脚本可开源发布（课题版权条款允许）
