# 启动阶段 Demo 方案（纯仿真，10 分钟展示）

> 场景：项目开始阶段的 prototype 展示，**无需真机**。
> 主课题：高擎方向二（RL 运控 + Sim2Real）｜辅课题：群核方向二（真实空间 → 仿真训练场）
> 展示叙事：**"训练—验证—部署"链路的仿真部分已全部打通：官方 Mini Pi+ 策略在 MuJoCo 中稳定行走，并能走进群核重建的真实教室场景。"**

---

## 0. 已完成并验证的部分（本机 Windows，全部实测通过）

| 项目 | 状态 | 证据 |
|------|------|------|
| 官方 Mini-Pi-Plus_AMP 仓库（20 自由度策略 + 3 个 checkpoint） | ✅ 已克隆 | `third_party/Mini-Pi-Plus_AMP` |
| MuJoCo 3.3.2 + CPU torch 环境 | ✅ 已安装 | `python -c "import mujoco, torch"` |
| 官方 checkpoint 平地行走（无头验证） | ✅ 10s 存活，0.486 m/s | `python tools/mujoco_pi_plus_walk.py` |
| **群核真实教室 PLY 下载**（余姚四中，197 万点激光雷达点云） | ✅ 106MB 已下载 | `scenes/classroom_raw.ply` |
| **真实教室场景 + 行走验证** | ✅ 沿过道 12s 前进 6.1m，0.51 m/s；抗扰 0/40/80N 100%、120N 50% | `scenes/scene_classroom.xml`（真实房间尺寸 + 标准课桌椅布局） |
| 官方 GUI sim2sim（教室场景 + jit 策略） | ✅ exit 0 完整运行（须单独运行，勿并行两个 GUI） | 需 `results/checkpoints/*_jit.pt` |
| 合成教室场景（保底） | ✅ 8s 存活，0.507 m/s | `scenes/scene_synthetic.xml` |
| 推力扰动评测：平地 3 checkpoint × 0/40/80/120N | ✅ ≤80N 全部 100% 存活，120N 跌倒 | `results/disturbance_flat.csv` |
| 推力扰动评测：真实教室场景 0/40/80/120N | ✅ ≤80N 100%、120N 50% | `results/disturbance_scene_classroom.csv` |
| TorchScript 策略导出（GUI 免 rsl_rl 依赖） | ✅ 3 个 | `results/checkpoints/` |
| 场景多视角离屏渲染检查 | ✅ 4 相机 | `results/plots/scene_check_*.png` |

## 1. Demo 日剩余工作（约半天）

### 1.1 已不需要下载 —— 真实教室场景已就绪

`scenes/scene_classroom.xml` 由群核"余姚第四中学空教室"点云（197 万点，禾赛激光雷达）自动生成，行走已验证。如需换场景（如浙大研讨教室），方法：在 studio.aholo3d.cn 登录状态下打开模型页，浏览器地址栏 projectId 替换后调用
`https://studio.aholo3d.cn/aholo/api/project/info?projectId=<ID>` 取返回 JSON 中 `task.result.plyPath` 下载，再跑
`python tools/scene_builder.py --ply <文件> -o scenes/scene_new.xml --scale 0.01`。

### 1.2 录制演示视频（1 小时）

GUI 脚本必须用导出的 jit 策略（官方 checkpoint 缺 rsl_rl 依赖加载不了）。小键盘 8/2/4/6/7/9 控速度方向，默认前进 0.5 m/s：
```bash
cd third_party/Mini-Pi-Plus_AMP
# 平地行走
python legged_lab/scripts/sim2sim_pi_plus.py --duration 30 --policy ../../results/checkpoints/model_40000_jit.pt
# 真实重建教室行走（群核点云场景）
python legged_lab/scripts/sim2sim_pi_plus.py --duration 30 --policy ../../results/checkpoints/model_40000_jit.pt --model ../../scenes/scene_classroom.xml
```
Win+G（Xbox Game Bar）或 OBS 录屏，存 `results/videos/`。每段 ≥30s，多录几条备剪。

### 1.3 跑完整评测出数据（30 分钟，挂后台即可）

```bash
python tools/disturbance_test.py                    # 3 checkpoint × 4 档推力 × 3 回合
python tools/disturbance_test.py --friction 0.4     # 低摩擦消融
```
产出 `results/disturbance_*.csv` + `results/plots/*.png`（基座高度曲线、存活率表）——这就是 PPT 的实验数据页。

### 1.4 PPT + 彩排（2 小时）

## 2. 10 分钟展示脚本

| 时间 | 内容 | 素材 |
|------|------|------|
| 0:00–1:30 | 课题与架构：四段式管线图（真实空间 → 空间重建 → RL 仿真训练 → sim2sim 验证 → [真机]） | PPT 架构图 |
| 1:30–4:30 | **Live demo**：①平地行走（键盘控速）②切到教室场景行走 ③讲一句"场景来自群核重建的余姚四中教室，点云转高度场接入" | GUI 脚本现场跑 |
| 4:30–6:00 | 鲁棒性：推力扰动曲线图 + 存活率表（"80N 推力 100% 存活；低摩擦下降到 x%"） | results/plots |
| 6:00–8:00 | 误差来源分析框架：PD 增益表 / IMU 坐标 / 关节映射 / 仿真-真机频率对齐（对应高擎方向二交付物要求） | PPT |
| 8:00–10:00 | 项目路线图：自训练策略（Isaac Lab，需 GPU）→ 真机部署（RKNN 链路已调研）→ SpatialLM 自动场景生成 | PPT + 备份视频 |

## 3. 现场防翻车

- Live demo 前关掉占 CPU 的程序；GUI 脚本实测可跑，但**必须提前在演示用电脑上完整跑一遍**
- 每段演示都有备份视频；断电/卡死直接切视频
- 讲稿词准备好"如果现场只放视频"的 10 分钟版本

## 4. 演示后进入正式开发（给老师看的路线图）

1. **训练自己的策略**：Linux + RTX GPU（实验室/云），`train.py --num_envs=1024`，产出自己的 checkpoint 替换官方模型 → 走同一套 sim2sim/场景验证
2. **真机部署**：`HT_Policy-Format-Convert`（pt→onnx→rknn）+ `sim2real-inference_code_ros2`（12 维腿部策略、STANDBY 0.05 缩放安全模式，详见 DEMO_PLAN_1DAY.md）
3. **群核深化**：SpatialLM 对教室点云输出结构化布局 → 自动生成仿真场景脚本（替代手工 PLY 转换）
4. **评测报告**：checkpoint × 场景 × 扰动 × 摩擦的系统消融，形成"训练—验证—部署"完整记录
