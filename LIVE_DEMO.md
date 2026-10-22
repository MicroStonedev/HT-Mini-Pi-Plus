# 现场 Live Demo 操作手册

> 展示当天照此执行。两个双击脚本已备好：`demo_flat.bat`（平地）、`demo_classroom.bat`（教室场景）。

## 0. 录屏（提前把素材备好，别现场录）

### 方式 A：自动录屏脚本（推荐，机位精确、无需录屏软件）

**最省事：双击 bat**（和 demo 脚本一样，按任意键开始）
- `record_flat.bat` —— 平地行走 20 秒
- `record_classroom.bat` —— 教室过道跟拍 15 秒

**或命令行**（可选机位/时长/高清/扰动）：
```bash
# 三段标准素材
python tools/record_demo.py --scene flat --camera free --duration 20        # 平地行走（官方 XML 无命名相机，用跟拍自由机位）
python tools/record_demo.py --scene classroom --camera walker --duration 15  # 教室过道跟拍（最出效果）
python tools/record_demo.py --scene classroom --camera top --duration 12     # 俯视看课桌布局

# 其他机位 / 参数
python tools/record_demo.py --scene classroom --camera side --duration 12    # 从教室后方向前拍
python tools/record_demo.py --scene classroom --camera walker --duration 15 --push 80   # 带 80N 推力扰动
python tools/record_demo.py --scene classroom --camera walker --duration 15 --width 1920 --height 1440  # 高清
```

耗时约为视频时长的 2~4 倍，**等终端出现 `[record] 完成：...` 再关窗口**。
录完可抽帧检查：用 PotPlayer/Gaomon/系统"照片"应用都能直接播放 MP4；
命令行抽帧：`python -c "import imageio_ffmpeg,imageio;g=imageio_ffmpeg.read_frames('results/videos/xxx.mp4');next(g);f=next(g);imageio.imwrite('a.png',f)"`。

输出到 `results/videos/demo_<场景>_<机位>_<时长>s.mp4`（25fps，默认 960×720）。

**机位含义**：`overview` 俯视全屋、`walker` 跟在机器人身后拍过道（最能体现"在教室里走"）、
`top` 正俯视看课桌布局、`side` 从教室后方向前拍。

### 方式 B：Xbox Game Bar（零安装，录实时操作）

1. 按第 1 节做好准备，双击 `demo_flat.bat` 或 `demo_classroom.bat`
2. 等 MuJoCo 窗口出现后，**鼠标点一下窗口**（确保是当前活动窗口）
3. `Win + Alt + R` 开始录制（屏幕上方出现"录制中"小条）
4. 演示：先让它自己走 10 秒 → 按 `7/9` 展示转向 → 按 `2` 切跟拍机位
5. `Win + Alt + R` 停止
6. 文件在 `此电脑 → 视频 → 捕获`，拷到 `results/videos/` 重命名

注意：录制期间**不要切窗口**（Game Bar 只录当前应用窗口）。默认 30fps、最长 2 小时，
在 `Win+G → 设置 → 捕获` 里可改 60fps。备选：Windows 11"截图工具"→ 录像机图标 → 自选区域。

## 1. 上台前 10 分钟检查清单

- [ ] 笔记本接电源，电源模式调"最佳性能"
- [ ] 关掉微信/钉钉等通知（Windows 专注助手），关闭浏览器和其他占 CPU 程序
- [ ] 提前**完整跑一遍两个 bat**（教室场景首次加载要几秒，心里有数）
- [ ] 备份视频放桌面（`results/videos/`），出任何问题直接切视频
- [ ] 终端字体调大，音量静音（脚本无声音）

## 2. 现场调用（两步）

**Demo 1 平地行走**：双击 `demo_flat.bat` → 按任意键 → MuJoCo 窗口弹出，机器人以 0.5 m/s 前进
**Demo 2 教室场景**：双击 `demo_classroom.bat` → 按任意键 → 机器人从教室后部沿过道走向讲台

## 3. 窗口内控制（交互版 `tools/sim2sim_interactive.py`）

> 官方原版脚本键盘控制实际不生效（代码缺陷：键盘事件被覆盖，仅手柄可控），交互版已修复。
> 终端实时显示速度指令。

| 按键（主键盘数字排即可） | 作用 |
|------|------|
| `8` / `2` | 前进速度 +0.2 / −0.2 m/s（初始 0.5，范围 ±1.0） |
| `4` / `6` | 左 / 右侧移 |
| `7` / `9` | 原地左 / 右转向（演示"听指挥"的关键动作） |
| `5` | 速度清零，站住 |
| `0` | 自由视角（鼠标拖动旋转、滚轮缩放、右键平移） |
| `1` `2` `3` `4` | overview / walker / side / top 机位（**演示用 2 跟拍**） |
| `Esc` | 结束程序 |

每次按键终端打印最新指令（`[cmd] vx=+0.50 vy=+0.00 yaw=+0.00`），每 2 秒回显一次。

## 4. 手动命令版（bat 失效时用）

```bash
cd D:\zcodeproject\HT-Mini-Pi-Plus-Robot
python tools/sim2sim_interactive.py --duration 60                                      # 平地
python tools/sim2sim_interactive.py --duration 60 --model scenes/scene_classroom.xml   # 教室
```

## 5. 故障速查

| 现象 | 处理 |
|------|------|
| `No module named mujoco/torch` | 用错 Python；`where python` 确认是 D:\python3.12.10，或命令里写绝对路径 |
| 找不到 policy 文件 | 先跑 `python tools/export_policy.py` 生成 jit 策略 |
| 教室场景加载慢/卡 | 正常（首次编译大场景）；实在不行切 `demo_flat.bat` + 视频讲教室 |
| 机器人行为怪异 | 重启脚本；策略确定性，重跑结果一致 |
| GLFW "window does not exist" | **同时开了两个 MuJoCo 窗口**，关掉一个再跑 |
| 现场全挂 | 放备份视频，讲结果表（`results/*.csv` + `results/plots/*.png`） |

## 5.5 教室场景讲解口径（现场话术）

数据边界要主动讲清楚，否则容易被追问：

> "教室场景来自群核 Aholo 平台用禾赛激光雷达扫描的余姚四中教室。这份点云我们做了三轮量化分析：
> 197 万点里 190 万集中在扫描者站立的 0.6 米内；桌面高度带俯视没有课桌结构；桌腿层也
> 不成形——因为 3DGS 点云是体积散射，桌椅几何不在这份点云里。所以我们的做法是：房间
> 尺寸、地面高度、地板颜色全部用真实数据，桌椅按标准中学教室的物理尺寸程序化建模——
> 课桌桌面 0.75 米、讲台 1.15 米、左右两列加 1.6 米中央过道。机器人从教室后部沿过道
> 走向讲台，0.51 米每秒，和空地一样快，0 到 80 牛推力下全部扛住。下一步接 SpatialLM
> 的结构化布局输出，把布局换成数据驱动。"

要点：**不说"还原了教室"**（数据不支持，会被拆穿），说"真实房间 + 正确尺度的标准布局"，
并把数据局限主动讲成下一步工作——这正是课题要的"说清楚每一步误差来自哪里"。

## 6. 演示顺序建议（对应 10 分钟脚本）

1. 架构图讲完 → `demo_flat.bat`（30 秒，按 `7/9` 展示转向）
2. 切 `demo_classroom.bat`（60 秒，高潮：按 `2` 跟拍机位，沿中央过道走向讲台）
3. 关窗口 → 讲抗扰数据（`results/plots/disturbance_flat.png`：80N 存活、120N 跌倒 = 抗扰边界）
4. 误差分析 → 路线图收尾
