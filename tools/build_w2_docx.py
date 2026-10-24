# -*- coding: utf-8 -*-
"""生成《W2 详细执行步骤》Word 文档"""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import copy

OUT = r"D:\zcodeproject\HT-Mini-Pi-Plus-Robot\docs\W2详细执行步骤.docx"
ACCENT = RGBColor(0x1F, 0x4E, 0x79)


def set_font(run, size=10.5, bold=False, color=None):
    run.font.name = "Calibri"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = color


def para(doc, text, size=10.5, bold=False, color=None, style=None):
    p = doc.add_paragraph(style=style)
    r = p.add_run(text)
    set_font(r, size, bold, color)
    return p


def code(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    r = p.add_run(text)
    r.font.name = "Consolas"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    r.font.size = Pt(9.5)
    r.font.color.rgb = RGBColor(0x8B, 0x2F, 0x2F)
    return p


def simple_table(doc, headers, rows, widths=None):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    for j, h in enumerate(headers):
        c = t.rows[0].cells[j]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        set_font(r, 10, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
        shd = c._tc.get_or_add_tcPr()
        el = shd.makeelement(qn("w:shd"), {qn("w:val"): "clear", qn("w:fill"): "1F4E79"})
        shd.append(el)
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            c = t.rows[i + 1].cells[j]
            c.text = ""
            r = c.paragraphs[0].add_run(str(v))
            set_font(r, 9.5)
    if widths:
        for j, w in enumerate(widths):
            for row in t.rows:
                row.cells[j].width = Cm(w)
    return t


doc = Document()
for s in doc.sections:
    s.top_margin, s.bottom_margin = Cm(2), Cm(2)
    s.left_margin, s.right_margin = Cm(2.2), Cm(2.2)

para(doc, "W2 详细执行步骤（10/25–10/29）：自主训练与消融实验", 16, True, ACCENT)
para(doc, "", 6)
para(doc, "阶段使命：把「官方策略能跑」升级为「自己训出的策略能走」——产出可写进简历的自训实测数字。")
para(doc, "起点资产：镜像 w1-d2-ready（5 分钟复活）｜复原脚本 v2｜GitHub 仓库｜W1 全部证据。")
para(doc, "机时预算：约 40–60 小时 ≈ 100–200 元（并行智算云 4090 约 4 元/h；AutoDL 约 2 元/h 可作比价备选）。")
para(doc, "关键认知：D3 实测 1024 环境仅用 4GB 显存 → 4090 上可开 4096 环境提速；完整训练 50000 iter 耗时 4–7 天不可行，"
          "W2 目标定为 15000–27000 iter（官方 model_27000 即为可用策略的实证），按里程碑分批训练、每批验证。", 10.5)

# ---------------- D5 ----------------
para(doc, "D5 · 10/25（主攻日，4–5h）：4090 上 4096 环境 + 第一个正式训练启动", 13, True, ACCENT)
para(doc, "步骤 1：用镜像开实例（10 分钟）", 11, True)
para(doc, "控制台 → 创建实例 → 镜像选自定义 w1-d2-ready → 机型 4090（无货则 3090×双机或降 2048 环境数）→ 系统盘 ≥150GB → 按流量带宽。开机后把公网 IP 发助手更新 SSH 配置。", 10.5)
para(doc, "步骤 2：环境快速验证（10 分钟）", 11, True)
code(doc, "ssh paratera  # 连通后：")
code(doc, "ls ~/RECOVERY_DONE && conda activate isaaclab  # 环境在位确认")
para(doc, "步骤 3：4096 环境压测（30 分钟）", 11, True)
para(doc, "先跑 200 iter 的 4096 环境短测，记录显存与速度，确认不爆显存：", 10.5)
code(doc, "tmux new -s train")
code(doc, "ACCEPT_EULA=Y python legged_lab/scripts/train.py --task=pi_plus_amp_sym_flat \\")
code(doc, "  --headless --logger=tensorboard --num_envs=4096 --max_iterations=200")
para(doc, "判定：nvidia-smi 显存 <20GB、速度 ≥6 iter/分钟 → 保持 4096；否则降 2048。记录数字进误差追踪表。", 10.5)
para(doc, "步骤 4：正式训练第一轮启动（目标 12000–15000 iter，约 24–36 小时连续）", 11, True)
code(doc, "tmux new -s run1")
code(doc, "ACCEPT_EULA=Y python legged_lab/scripts/train.py --task=pi_plus_amp_sym_flat \\")
code(doc, "  --headless --logger=tensorboard --num_envs=4096 --max_iterations=15000")
para(doc, "挂在 tmux 后设安全关机：训练结束自动关机（复用 D3 的看门狗模式，阈值改 15000）。当晚不用守，TensorBoard 随时看。", 10.5)
para(doc, "D5 完成 = 训练在跑 + 4096 显存数据入库 + 自动化保险挂好。", 10.5, True)

# ---------------- D6 ----------------
para(doc, "D6 · 10/26（监控日，2–3h）：中期检查与 checkpoint 管理", 13, True, ACCENT)
para(doc, "步骤 1：曲线健康判断（对照 D3 的经验）", 11, True)
code(doc, "# 本地隧道 + 浏览器 localhost:6006")
code(doc, "ssh -L 6006:localhost:6006 paratera")
para(doc, "健康标准：回合长度持续增长（对标 D3 的 17→528 形态，应达数千步）；奖励止跌回升；loss 平稳无爆炸。", 10.5)
para(doc, "步骤 2：中间 checkpoint 首验（关键环节，30 分钟）", 11, True)
para(doc, "训练到 5000–8000 iter 时，复制最新 checkpoint 做一次 Isaac 回放（不中断训练，另开 tmux）：", 10.5)
code(doc, "tmux new -s midcheck")
code(doc, "ACCEPT_EULA=Y python legged_lab/scripts/play_log.py --task=pi_plus_amp_sym_flat \\")
code(doc, "  --load_run=<最新run目录> --checkpoint=model_<最新>.pt --num_envs=1 --headless")
para(doc, "判定：回合长度 >1000 步（20 秒不摔）= 学习正常，继续训；秒摔 = 停训排查（reward 配置/学习率）。", 10.5)
para(doc, "步骤 3：证据例行归档", 11, True)
para(doc, "TensorBoard 截图 + 中间回放日志 scp 回本地 results/w2/。", 10.5)

# ---------------- D7 ----------------
para(doc, "D7 · 10/27（实验日，4–5h）：对照 run 与消融设计", 13, True, ACCENT)
para(doc, "步骤 1：第一个 run 收尾（若到 12000–15000 iter）", 11, True)
para(doc, "停训 → 用最优 checkpoint 做 300 秒回放判定（同 W1 判定流程）→ 归档。", 10.5)
para(doc, "步骤 2：消融实验矩阵确认（对照三周计划）", 11, True)
simple_table(doc, ["实验", "变量", "判定指标", "机时"], [
    ("A 基线", "默认配置完整训练", "回放 300s + 前进速度", "已完成(=run1)"),
    ("B 扰动", "回放时加推力 40/80/120N", "存活率（对标官方 80–120N 边界）", "~1h"),
    ("C 摩擦", "地面摩擦 0.4/0.8/1.2", "行走稳定性与速度", "~1h"),
    ("D DR 开关", "域随机化开/关各训短程 3000 iter", "泛化差距", "~6h"),
], [2.2, 5.2, 5.2, 2.6])
para(doc, "优先级：B、C 用 run1 的 checkpoint 直接做（便宜）；D 视进度取舍（时间紧则降为回放级对比）。", 10.5)
para(doc, "步骤 3：B/C 消融执行", 11, True)
para(doc, "复用 MuJoCo 侧 disturbance_test.py 的思路，在 Isaac 回放中注入扰动/改摩擦（改动 play_log.py 参数化注入即可，助手带做）。", 10.5)

# ---------------- D8 ----------------
para(doc, "D8 · 10/28（验证日，4–5h）：sim2sim 对照——自训策略回流本地", 13, True, ACCENT)
para(doc, "步骤 1：导出自训策略", 11, True)
code(doc, "# 云端：play_log.py 回放时会自动导出 policy.pt/jit 到 run 目录")
code(doc, "scp paratera:~/Mini-Pi-Plus_AMP/logs/pi_plus_amp_sym_flat/<run>/exported/*.pt results/checkpoints/")
para(doc, "步骤 2：本地 MuJoCo 验证（复用 W0 工具链）", 11, True)
code(doc, "python tools/mujoco_pi_plus_walk.py --policy results/checkpoints/policy.pt --duration 30")
code(doc, "python tools/mujoco_pi_plus_walk.py --model scenes/scene_classroom.xml --policy ... --duration 30")
para(doc, "步骤 3：产出核心数字（简历弹药）", 11, True)
para(doc, "自训策略：平地速度 ___ m/s（对标官方 0.51）｜教室场景通过性｜抗扰边界 ___ N（对标官方 80–120N）。"
          "诚实口径：与官方的差距及原因分析一段话（这就是面试最加分的部分）。", 10.5)

# ---------------- D9 ----------------
para(doc, "D9 · 10/29（固化日，3–4h）：Dockerfile v1 + 汇总 + 周报", 13, True, ACCENT)
para(doc, "步骤 1：Dockerfile v1（环境已定型，此刻做一次到位）", 11, True)
code(doc, "FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn8-runtime")
code(doc, "COPY install_isaac_recovery.sh /tmp/")
code(doc, "RUN bash /tmp/install_isaac_recovery.sh")
para(doc, "验收：docker build 成功 + 容器内跑通冒烟测试。", 10.5)
para(doc, "步骤 2：W2 数据汇总与周报（结构同 W1 周报）", 11, True)
para(doc, "步骤 3：简历更新", 11, True)
para(doc, "第一条 bullet 替换为自训实测数字（替换文本见 简历_三周完成版.md 预留段）。", 10.5)
para(doc, "步骤 4：打镜像 w2-trained-ready + 实例关机 + 全部产物推 GitHub。", 11, True)

# ---------------- 并行与速查 ----------------
para(doc, "与面试并行（每天 2–3h）", 13, True, ACCENT)
para(doc, "复习清单：PPO clip 手推 / GAE / AMP 判别器与参考数据 / DR 权衡。把自训数字讲熟："
          "「我训到 ___ iter 达到 ___ m/s，中间踩了 flatdict 兼容坑、用回合长度判读早期曲线」——细节即说服力。", 10.5)

para(doc, "速查：W2 最容易翻车的点", 13, True, ACCENT)
simple_table(doc, ["坑", "症状", "对策"], [
    ("训练中断", "实例被平台回收/关机", "tmux+完成即关机看门狗；重要 checkpoint 及时 scp 回本地"),
    ("IP 又变", "SSH 连不上", "以控制台实时 IP 为准，发助手更新配置"),
    ("显存爆", "4096 环境 CUDA OOM", "降 2048/1024，或缩短 rollout 长度"),
    ("训练不学", "回合长度不涨", "对照 D3 形态判断；检查 reward 符号与命令范围"),
    ("资源售罄", "开不了机", "3090 降级跑 / AutoDL 备选 / 复原脚本重建"),
], [3.0, 5.0, 7.2])

para(doc, "每日完成判定（打勾制）", 13, True, ACCENT)
for line in [
    "D5：4090 就位 + 4096 压测数据 + run1 挂 tmux + 保险关机 ✓",
    "D6：曲线健康判断 + 中间 checkpoint 回放 ≥1000 步 + 截图归档 ✓",
    "D7：run1 判定回放 + 消融 B/C 数据表 ✓",
    "D8：自训策略本地 MuJoCo 数字产出 ✓",
    "D9：Dockerfile v1 + W2 周报 + 简历更新 + 镜像 + 关机 ✓",
]:
    para(doc, "☐ " + line, 10.5)

doc.save(OUT)
print("[ok] 已生成", OUT)
