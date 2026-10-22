# Project Prototype/Demo 实施方案

> 期末展示：10 分钟 / 组，需要一个**能跑的 prototype**
> 主课题：高擎机电 方向二「强化学习运控与 Sim2Real」
> 辅课题：群核科技 方向二「空间数据与具身智能训练」
> 一句话故事：**把真实空间（群核重建）变成仿真训练场，让 Mini Pi+（高擎）在里面学会走路，并打通到真机的部署链路。**

---

## 0. Demo 总体设计（先想清楚要展示什么）

### 展示叙事链路

```
[真实空间]            [空间重建(群核)]        [仿真训练(高擎)]         [验证与部署]
 手机拍教室  ──▶  PLY/结构化场景(SpatialLM) ──▶  Isaac Lab RL 训练  ──▶  MuJoCo sim2sim ──▶ 真机视频
                        ▲                                              ▲
                 14个官方重建场景素材包                          官方预训练 checkpoint 保底
```

### 10 分钟展示脚本

| 时间 | 内容 | 形式 |
|------|------|------|
| 0:00–1:00 | 课题背景、为什么选方向二、系统架构图 | PPT 架构图 |
| 1:00–5:00 | **Live Demo**（核心，见下方三段） | 屏幕现场演示 |
| 5:00–7:00 | 真机部署视频（如真机未到：部署链路讲解 + 官方真机视频 + 我们的鲁棒性测试） | 视频 |
| 7:00–9:00 | 误差来源分析（PD 参数 / IMU 坐标 / 延迟 / 摩擦系数） | PPT + 数据表 |
| 9:00–10:00 | 结论、局限、下一步（连接两个课题的完整具身智能闭环） | PPT |

### Live Demo 三段（务必全部本地可跑、提前彩排）

1. **基线行走**：Mini Pi+ URDF + 官方预训练策略，在 MuJoCo 里平地行走 30 秒（对应"仿真训练成果"）
2. **真实场景行走（加分杀手锏）**：切换到群核重建的教室场景（PLY 转碰撞体），机器人在**真实重建的空间**里行走（对应群核方向二"从真实空间生成仿真场景"）
3. **鲁棒性测试**：运行中给机器人施加推力扰动 / 改摩擦系数，展示策略稳定性（对应高擎方向二考察重点"迁移稳定性 + 误差来源"）

---

## 1. 资源清单（全部已核实存在）

### 高擎（主线）

| 资源 | 地址 | 用途 |
|------|------|------|
| Mini-Pi-Plus_AMP | github.com/HighTorque-Robotics/Mini-Pi-Plus_AMP | RL 行走训练框架（Isaac Sim 4.5.0 + Isaac Lab 2.1.0），**自带 3 个预训练 checkpoint**，含 `sim2sim_pi_plus.py` |
| HT_Robot_URDF | github.com/HighTorque-Robotics/HT_Robot_URDF | Mini Pi 系列 URDF 模型 |
| sim2real-inference_code / _ros2 | 同组织 | 真机推理代码（C / ROS2 C++） |
| HT_Policy-Format-Convert | 同组织 | ONNX → RKNN / TensorRT 模型转换 |
| Mini_Pi_RL_Baseline | 同组织 | RL 基线（备用） |
| 从零搭建 Pi+ 教程 | hightorque.cn/pi-plus-from-scratch | 官方教程 |
| 二次开发文档 | hightorque.cn/docs | 文档中心 |

关键事实：AMP 仓库 `Exported_policy/` 里有 3 个示例 checkpoint；MuJoCo sim2sim 只需要 MuJoCo 3.3.2 + PyTorch，**Windows 可直接运行**，不需要 Isaac Lab。

### 群核（辅线）

| 资源 | 地址 | 用途 |
|------|------|------|
| SpatialLM | github.com/manycore-research/SpatialLM | 点云 → 结构化室内模型（NeurIPS 2025） |
| 14 个重建/生成场景（PLY+SPZ） | 文档内素材包表格 / studio.aholo3d.cn/library | 其中"余姚第四中学空教室""浙大小组研讨教室"适合做 demo 场景 |
| Aholo Reality | studio.aholo3d.cn/library | 实景采集 → 重建（可自己拍教室重建，效果更个人化） |
| SpatialVerse | coohomcloud.com | 空间智能平台（智能体训练演示参照） |
| InteriorGS 数据集 | github.com/manycore-research/InteriorGS | 带语义标注的室内场景（备用数据） |

### 环境

- **Windows 本机（你现在这台）**：跑 MuJoCo sim2sim、场景转换脚本、现场 Live Demo —— 全部够用
- **Linux + NVIDIA GPU（WSL2 / 实验室服务器 / 云 GPU）**：仅在要自己训练时需要（Isaac Lab 不支持 Windows 原生）；没有 GPU 也能完成 demo（用官方 checkpoint）

---

## 2. 两周执行计划（按天）

### Phase 1：打通保底 demo（Day 1–2）⚡ 最优先

目标：**48 小时内先有一个"会走的机器人"**，之后所有工作都是增量改进。

```bash
# 1. 克隆仓库
git clone https://github.com/HighTorque-Robotics/Mini-Pi-Plus_AMP.git
git clone https://github.com/HighTorque-Robotics/HT_Robot_URDF.git

# 2. Windows 上装最小依赖（不需要 Isaac Lab）
pip install mujoco==3.3.2 torch

# 3. 用官方预训练策略跑 sim2sim（保底 demo 立刻成立）
python legged_lab/scripts/sim2sim_pi_plus.py ^
  --policy=Exported_policy/model_40000.pt ^
  --model=legged_lab/assets/hightorque/pi_plus/pi_plus.xml ^
  --duration=30
```

验收标准：MuJoCo 窗口里 Mini Pi+ 稳定行走 ≥30 秒。若 3 个 checkpoint 效果不同，记录对比（这本身就是评测素材）。

### Phase 2：群核场景接入（Day 3–6）🌟 差异化亮点

目标：把群核重建的真实场景变成 MuJoCo 训练/演示场景。

**Step 2.1 获取场景（Day 3）**
- 从素材包下载"余姚第四中学空教室"（或自选）的 PLY
- 进阶选项：用手机拍自己的实验室/教室 → Aholo Reality 重建 → 导出 PLY（更有展示冲击力，"我们在自己上课的教室里训练机器人"）

**Step 2.2 PLY → MuJoCo 场景（Day 4–5）**

技术路线（写一个 `tools/scene_builder.py`）：
1. 用 `trimesh`/`open3d` 读取 PLY 网格
2. 网格简化（`simplify_quadric_decimation` 降到 ≤50k 面，MuJoCo 碰撞体要求）
3. 裁剪：只保留地面 + 1.5m 以下障碍（行人视角碰撞才有意义）
4. 导出 OBJ/STL，生成 MuJoCo XML 场景文件（引用 AMP 仓库的 pi_plus.xml，替换/追加地面与障碍 mesh）
5. 处理坐标对齐：重建坐标系 → 机器人初始位姿（z 高度、yaw 朝向）——**这一步的误差分析正好写进报告**

**Step 2.3（进阶，时间富余才做）SpatialLM 结构化输出**

用 SpatialLM 对点云输出结构化布局（墙/门/窗/家具的语义框），再由脚本把布局框**自动生成** MuJoCo 场景 XML——"语义理解 → 仿真场景"的全自动管线，比手工转 PLY 更贴合群核方向二。

**验收标准**：`sim2sim_pi_plus.py --model=scene_classroom.xml` 机器人在重建教室里行走。

### Phase 3：训练自己的策略 或 强化分析（Day 7–9）🔧 二选一

**路线 A（有 Linux + RTX GPU，推荐）**：真正训练
```bash
# Isaac Lab 环境内（WSL2/服务器），小显存可降 num_envs
python legged_lab/scripts/train.py --task=pi_plus_amp_sym_flat --headless \
  --logger=tensorboard --num_envs=1024
# 训练曲线截图进 PPT；导出 TorchScript 后重复 Phase 1 的 sim2sim
```
展示点：TensorBoard 曲线、奖励曲线、AMP 参考动作对比（`play_amp_animation.py`）。

**路线 B（无 GPU）**：不训练，做**系统性评测与消融**（同样有含金量，正好呼应课题"应用与评测"）：
- 3 个官方 checkpoint 在平地/教室场景/不同摩擦系数下的行走时长对比表
- 推力扰动测试（MuJoCo `xfrc_applied` 周期性推机器人，记录恢复率）
- 观测噪声注入（给 IMU 观测加噪声，量化性能退化）——这就是"误差来源分析"的实验证据

### Phase 4：真机链路（Day 10–11，视硬件到位情况）

真机到货：
1. `HT_Policy-Format-Convert`：policy.pt → ONNX → TensorRT/RKNN
2. `sim2real-inference_code_ros2` 跑通推理节点，连接 Mini Pi+
3. 全程录像（安全第一：先挂起测试，官方 README 也要求受控环境验证）

真机未到：录"部署链路走查"屏幕视频（模型转换 + 推理代码 + 数据流图），配合官方真机视频说明，明确说明硬件到位后 X 天内可完成部署。

### Phase 5：误差分析文档 + PPT + 彩排（Day 12–14）

误差来源清单（写入评测报告，直接对应高擎方向二交付物要求）：
- PD 增益：仿真值 vs 手册值的差异（可做参数扫描实验）
- IMU：坐标轴定义差异、零偏
- 执行器：延迟、摩擦、齿隙
- 场景：重建网格 vs 真实地面的摩擦/平整度差异（群核场景接入引入的新误差类别——两个课题的交叉点，务必写）

PPT 页数 ≤10 页，架构图 1 页、demo 流程图 1 页、实验数据 2 页、误差分析 1 页。

---

## 3. 代码仓库结构（交付物之一）

```
HT-Mini-Pi-Plus-Robot/
├── README.md                 # 选题方案 + 复现指南
├── DEMO_PLAN.md              # 本文档
├── third_party/
│   ├── Mini-Pi-Plus_AMP/     # 官方训练框架 (git clone)
│   └── HT_Robot_URDF/
├── tools/
│   ├── scene_builder.py      # PLY → MuJoCo 场景转换
│   ├── disturbance_test.py   # 推力扰动鲁棒性测试
│   └── eval_sweep.py         # 摩擦/噪声消融实验
├── scenes/
│   ├── classroom_raw.ply     # 群核重建原始数据
│   ├── classroom_decimated.obj
│   └── scene_classroom.xml   # 生成的 MuJoCo 场景
├── results/
│   ├── checkpoints/          # 我们训练/评测的策略
│   ├── videos/               # demo 录屏
│   └── plots/                # 曲线与对比表
└── docs/
    ├── 误差来源分析.md
    └── 评测报告.md
```

---

## 4. 风险与保底（每项都有 fallback）

| 风险 | 概率 | 保底方案 |
|------|------|----------|
| 无 GPU 训练不了 | 高 | 官方 checkpoint + 评测消融路线 B，demo 完全成立 |
| 群核平台权限/素材下载受阻 | 中 | 素材包是公开的；再不行用 SpatialLM + InteriorGS 公开数据集 |
| PLY 网格太大 MuJoCo 卡顿 | 中 | 简化到 ≤50k 面 + 只留低处碰撞体 |
| Windows 下 MuJoCo 渲染问题 | 低 | 换 EGL 离屏渲染录视频播放；或 WSL2 跑 |
| 真机未到 | 高 | sim2sim 扰动实验当主要证据 + 部署链路讲解（见 Phase 4） |
| 现场 demo 翻车 | 低 | 提前录完整备份视频，现场出问题直接切视频 |

## 5. 立即可做的三个行动（今天）

1. `git clone` 两个官方仓库，跑通 Phase 1 的官方 checkpoint sim2sim（半天内可见机器人行走）
2. 下载群核素材包里的教室场景 PLY
3. 报名 10 月群核空间智能 workshop/黑客松（拿教程与算力积分，展示时可提一句）

## 6. 与课题交付要求的对应关系

| 课程要求 | 本 demo 覆盖 |
|----------|--------------|
| 高擎方向二：训练—验证—部署记录 | 训练(Phase 3)/官方策略 + sim2sim(Phase 1) + 部署链路(Phase 4)，全程日志留存 |
| 高擎方向二：误差来源说明 | Phase 5 误差清单 + 路线 B 的量化实验 |
| 群核方向二：真实空间 → 仿真数据 | Phase 2 场景重建接入 + (进阶)SpatialLM 自动化管线 |
| 作品说明 + 可运行代码仓库 + 评测报告 | 第 3 节仓库结构 + results/ + docs/ |
