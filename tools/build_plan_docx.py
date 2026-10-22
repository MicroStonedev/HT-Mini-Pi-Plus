# -*- coding: utf-8 -*-
"""三周详细计划 Markdown → Word 转换（按 docx 技能排版规范）。

用法：python tools/build_plan_docx.py
输出：三周详细计划.docx（项目根目录；源 md 保持不动）
"""
import os

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "三周详细计划.docx")

FONT = "微软雅黑"
DARK = RGBColor(0x0E, 0x3A, 0x57)
ACCENT = RGBColor(0xB0, 0x5A, 0x1E)
GRAY = RGBColor(0x5C, 0x6B, 0x7A)
HEAD_BG = "17557E"
ZEBRA = "EAF1F7"
CALLOUT = "F0E9E2"


def set_font(run, size=10.5, bold=False, color=None, name=FONT):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color
    rPr = run._element.get_or_add_rPr()
    rf = rPr.find(qn("w:rFonts"))
    if rf is None:
        rf = rPr.makeelement(qn("w:rFonts"), {})
        rPr.append(rf)
    for k in ("w:eastAsia", "w:ascii", "w:hAnsi"):
        rf.set(qn(k), name)


def para(doc, runs, size=10.5, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
         space_after=6, line=1.3, indent_cn=2):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = align
    pf.space_after = Pt(space_after)
    pf.line_spacing = line
    if indent_cn:
        pf.first_line_indent = Pt(size * indent_cn)
    for item in runs:
        t, bold, color = (item + (None,))[:3] if len(item) == 2 else item
        set_font(p.add_run(t), size, bold, color)
    return p


def heading(doc, text, level):
    h = doc.add_heading(level=level)
    size = 16 if level == 1 else 13
    set_font(h.add_run(text), size, True, DARK)
    h.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    h.paragraph_format.space_after = Pt(6)
    return h


def table(doc, headers, rows, widths, font=9.5):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    # 单元格边距 + 边框 + 表头跨页重复 + 行不拆分
    tblPr = t._tbl.tblPr
    mar = tblPr.makeelement(qn("w:tblCellMar"), {})
    for edge, v in (("top", 60), ("bottom", 60), ("left", 100), ("right", 100)):
        mar.append(mar.makeelement(qn(f"w:{edge}"), {qn("w:w"): str(v), qn("w:type"): "dxa"}))
    borders = tblPr.makeelement(qn("w:tblBorders"), {})
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        borders.append(borders.makeelement(qn(f"w:{edge}"), {
            qn("w:val"): "single", qn("w:sz"): "4",
            qn("w:space"): "0", qn("w:color"): "9DB2C6"}))
    anchor = tblPr.find(qn("w:tblLook"))
    if anchor is not None:
        anchor.addprevious(mar)
        anchor.addprevious(borders)
    else:
        tblPr.append(mar)
        tblPr.append(borders)

    def fill(cell, runs, bg=None, bold=False, white=False, size=font):
        if bg:
            shd = cell._tc.get_or_add_tcPr().makeelement(
                qn("w:shd"), {qn("w:val"): "clear", qn("w:fill"): bg})
            cell._tc.get_or_add_tcPr().append(shd)
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.15
        for t_, b_, c_ in runs:
            set_font(p.add_run(t_), size, bold or b_,
                     RGBColor(0xFF, 0xFF, 0xFF) if white else c_)

    for j, htext in enumerate(headers):
        c = t.cell(0, j)
        c.width = Cm(widths[j])
        fill(c, [(htext, False, None)], bg=HEAD_BG, bold=True, white=True)
    trPr = t.rows[0]._tr.get_or_add_trPr()
    trPr.append(trPr.makeelement(qn("w:tblHeader"), {}))
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i + 1, j)
            c.width = Cm(widths[j])
            fill(c, [(val, False, None)], bg=ZEBRA if i % 2 else None)
        t.rows[i + 1]._tr.get_or_add_trPr().append(
            t.rows[i + 1]._tr.makeelement(qn("w:cantSplit"), {}))
    return t


def bullet(doc, lead, body, sub=False, size=10.5):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(4)
    pf.line_spacing = 1.3
    pf.left_indent = Cm(1.0 if sub else 0.6)
    pf.first_line_indent = Cm(-0.42)
    mark = "– " if sub else "• "
    set_font(p.add_run(mark), size, False, ACCENT)
    if lead:
        set_font(p.add_run(lead), size, True, DARK)
    set_font(p.add_run(body), size, False, None)
    return p


def callout(doc, runs, bg=CALLOUT):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(6)
    pf.space_after = Pt(8)
    pf.line_spacing = 1.3
    pf.left_indent = Cm(0.3)
    pf.right_indent = Cm(0.3)
    shd = p._p.get_or_add_pPr().makeelement(
        qn("w:shd"), {qn("w:val"): "clear", qn("w:fill"): bg})
    p._p.get_or_add_pPr().append(shd)
    for t_, b_, c_ in runs:
        set_font(p.add_run(t_), 10.5, b_, c_)
    return p


doc = Document()
for sec in doc.sections:
    sec.top_margin = sec.bottom_margin = Cm(2.0)
    sec.left_margin = sec.right_margin = Cm(2.2)

# 页脚页码
fp = doc.sections[0].footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = fp.add_run()
set_font(r, 9, False, GRAY)
fld1 = r._r.makeelement(qn("w:fldChar"), {qn("w:fldCharType"): "begin"})
instr = r._r.makeelement(qn("w:instrText"), {})
instr.text = "PAGE \\* arabic \\* MERGEFORMAT"
fld2 = r._r.makeelement(qn("w:fldChar"), {qn("w:fldCharType"): "end"})
r._r.append(fld1)
r._r.append(instr)
r._r.append(fld2)

# ---- 标题区
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(2)
set_font(p.add_run("三周详细执行计划"), 20, True, DARK)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(10)
set_font(p.add_run("W1–W3 ｜ 2026.10.09 – 10.29"), 12, False, GRAY)

callout(doc, [
    ("依据：", True, DARK),
    ("两份 Proposal 的六周计划（W1 复现 / W2 自训 / W3 DR+误差），叠加目标——第三周（10/23–29）有实习面试。", False, None),
    ("时间预算：", True, DARK),
    ("Proposal A1 约定每人每周 ≥20h，按理论 7h + 工程 13h 分配（工程为主线，理论服务工程与面试）。", False, None),
    ("双线并行：", True, DARK),
    ("工程线产出简历/面试的\u201c一手数据\u201d；理论线保证面试深挖答得上来。", False, None),
], bg=ZEBRA)

# ---- W1
heading(doc, "W1（10/09–10/15）：Isaac Lab 环境与官方训练跑通", 2)
para(doc, [("工程目标（Proposal 判定标准：仿真中连续行走 ≥5 分钟不跌倒）", True, DARK)],
     indent_cn=0, space_after=4)
table(doc, ["日", "任务", "产出 / 判定"], [
    ("周四 10/09", "训练机安装 Ubuntu 22.04（双系统或 WSL2，优先双系统）；装 RTX 驱动 + CUDA", "nvidia-smi 正常"),
    ("周五 10/10", "安装 Isaac Sim 4.5 + Isaac Lab 2.1（官方 pip 方式）；克隆 Mini-Pi-Plus_AMP", "isaaclab.sh 示例跑通"),
    ("周六 10/11", "加载 Mini Pi+ URDF 与官方任务 pi_plus_amp_sym_flat；阅读仓库 README/环境配置", "官方示例策略在 Isaac 中行走"),
    ("周日 10/12", "用官方 checkpoint 跑 play.py（--num_envs=1），正式记录\u201c连续行走 ≥5 分钟\u201d（W1 判定项，录屏+日志存档）", "W1 判定通过证据"),
    ("周一 10/13", "小规模训练试运行：train.py --num_envs=1024，跑通 200 iter 观察损失/reward 曲线正常下降", "训练日志与曲线截图"),
    ("周二 10/14", "训练脚本 Docker 化（Proposal 交付物：Dockerfile 可复现）", "Dockerfile v1"),
    ("周三 10/15", "缓冲/补漏；整理 W1 实验记录入误差追踪表", "W1 周报"),
], widths=[2.2, 9.2, 4.6])
para(doc, [("理论学习（7h，本周主题：RL 基础与训练框架）", True, DARK)], indent_cn=0, space_after=3)
bullet(doc, "3h｜", "MDP、策略梯度、PPO 核心机制——资源：OpenAI Spinning Up 的 VPG→PPO 章节 + Schulman PPO 论文精读（重点 clip 目标函数）")
bullet(doc, "2h｜", "AMP（Adversarial Motion Priors）原理——本框架的奖励来自判别器而非手工 reward：读 Escontrela et al. 2021（重点：判别器输入输出、与 GAN 的关系、retarget 参考动作）")
bullet(doc, "2h｜", "Isaac Lab 架构——官方文档 RL 章节：env / task / runner 三层结构，对照 Mini-Pi-Plus_AMP 仓库目录理解")
callout(doc, [("验收：", True, ACCENT),
              ("官方策略 Isaac 中 5 分钟行走 + 训练已能启动。面试可讲：\u201c我复现了官方策略并在两个引擎里验证一致（0.51 m/s）\u201d。", False, None)])

# ---- W2
heading(doc, "W2（10/16–10/22）：平地自训基线 + 双引擎对照", 2)
para(doc, [("工程目标（判定：自训策略 MuJoCo 回放 ≥60 s、≥0.3 m/s；对照官方口径）", True, DARK)],
     indent_cn=0, space_after=4)
table(doc, ["日", "任务", "产出 / 判定"], [
    ("周四 10/16", "正式训练启动：官方 reward/超参原样，num_envs=1024（显存允许则 2048），后台挂跑", "训练任务开始"),
    ("周五 10/17", "训练监控日：每 2h 看一次 reward 曲线/命令跟踪误差；同时把 torch 训练日志脚本化（自动从 logs 提取指标画图）", "监控脚本 + 曲线"),
    ("周六 10/18", "训练中段检查：用中间 checkpoint 在 MuJoCo 无头环境回放（mujoco_pi_plus_walk.py），确认策略可用性随训练提升", "中段回放记录"),
    ("周日 10/19", "训练收敛判断（reward 平台期 + 命令跟踪误差稳定）；选最佳 checkpoint，play.py 导出 TorchScript", "自训 policy.pt"),
    ("周一 10/20", "双引擎对照实验：自训策略 vs 官方策略，各在 Isaac/MuJoCo 跑同一测试（速度跟踪、5 分钟不倒），记录差异", "双引擎对照表（Q1/Q2 的第一份答案）"),
    ("周二 10/21", "补测/复跑（若 W2 达标线未过：调 num_envs/iter 重训一次，这是唯一的重试窗口）", "达标确认"),
    ("周三 10/22", "W2 收尾：训练曲线、对比表、结论写入实验记录；简历第一条 bullet 填入实测值（替换【实测】占位）", "简历 v5"),
], widths=[2.2, 9.2, 4.6])
para(doc, [("理论学习（7h，本周主题：PPO 深入与训练诊断——面试高频区）", True, DARK)], indent_cn=0, space_after=3)
bullet(doc, "3h｜", "PPO 细节三件套：GAE（λ 的作用）、clip 范数、熵正则；资源：PPO 论文附录 + Spinning Up 的 PPO 页 + 任何一篇 PPO 调参指南博客")
bullet(doc, "2h｜", "训练诊断方法：reward 曲线看什么、常见失败模式（不收敛/震荡/策略保守）、超参敏感性（lr/clip/ent_coef）——结合自己 W1-W2 的训练日志对照学习")
bullet(doc, "2h｜", "Rudin et al. CoRL 2021（Learning to Walk in Minutes）：大规模并行训练的要点，解释为什么 1024 envs、为什么几分钟收敛")
callout(doc, [("验收：", True, ACCENT),
              ("自训策略回放达标 + 双引擎对照表。面试可讲：\u201c我训的策略在两个物理引擎里表现差 X%，主要差距来自接触模型\u201d。", False, None)])

# ---- W3
heading(doc, "W3（10/23–10/29）：DR 实验 + 误差量化 + 中期检查 + 面试", 2)
para(doc, [("工程目标（判定：DR 区间曲线 + 三组误差退化曲线 + 误差对照表 v1；周三中期检查）", True, DARK)],
     indent_cn=0, space_after=4)
table(doc, ["日", "任务", "产出 / 判定"], [
    ("周四 10/23", "摩擦 DR 实验：Isaac 中 3 档摩擦区间（窄/中/宽）各训一轮（可减小规模），导出后在 MuJoCo 测存活率", "摩擦维度\u201c区间→存活率\u201d曲线"),
    ("周五 10/24", "外力 DR 实验：同法 3 档外力随机化", "外力维度曲线"),
    ("周六 10/25", "PD 敏感性实验（仿真内，无需训练）：用无头环境对 kp/kd 做 ±20%/±50% 缩放，跑行走统计", "PD 退化曲线"),
    ("周日 10/26", "IMU 噪声注入 + 延迟注入实验（同法，改观测/控制循环）", "IMU/延迟退化曲线"),
    ("周一 10/27", "汇总误差对照表 v1；整理中期检查材料（进度 vs 六周计划、误差追踪表初版——Proposal Next Actions 第 7 条）", "中期汇报材料"),
    ("周二 10/28", "中期检查；下午开始面试冲刺复习（见下）", "—"),
    ("周三 10/29", "面试日（预计）：证据包最终检查——自训曲线、双引擎表、DR 曲线、误差表、抗扰图、disturbance_test.py 可现场跑", "面试证据包"),
], widths=[2.2, 9.2, 4.6])
para(doc, [("理论学习（7h，本周主题：Sim2Real 方法论 + 面试冲刺）", True, DARK)], indent_cn=0, space_after=3)
bullet(doc, "2h｜", "Tobin et al. IROS 2017（Domain Randomization 开山）：DR 的假设、为什么有效、随机化维度选择")
bullet(doc, "2h｜", "RMA（Kumar et al. RSS 2021）+ sim2real gap 综述性理解：三类 gap（物理参数/观测/延迟），各自对策（DR/adaptation/系统辨识）")
bullet(doc, "3h｜", "面试冲刺（对照自己实验复盘）：")
for sub in ["PPO：clip 目标函数手推、GAE 为什么降低方差、on-policy 的代价",
            "AMP：判别器怎么替代手工 reward、参考动作从哪来",
            "DR：区间怎么定（用你自己的曲线答）、过宽过窄各什么症状（你有实验证据）",
            "sim2sim 的意义与局限：能预测什么（策略鲁棒性）、不能预测什么（真机执行器/IMU 特性）",
            "每题准备 30 秒版 + 2 分钟版答案"]:
    bullet(doc, "", sub, sub=True)

# ---- 资源清单
heading(doc, "理论学习资源清单（按优先级）", 2)
for i, (lead, body) in enumerate([
    ("OpenAI Spinning Up（VPG→PPO 路径）", "——RL 基础主线"),
    ("Schulman et al. 2017, Proximal Policy Optimization", "——必精读"),
    ("Escontrela et al. 2021, Adversarial Motion Priors", "——本框架奖励来源，面试必被问"),
    ("Rudin et al. CoRL 2021", "——并行训练范式"),
    ("Tobin et al. IROS 2017", "——DR 原文"),
    ("Kumar et al. RSS 2021, RMA", "——自适应方向（加分项，读 intro 即可）"),
    ("Isaac Lab 官方文档 RL 章节 + 高擎从零搭建 Pi+ 教程", "（工具性查阅）"),
]):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.3
    p.paragraph_format.left_indent = Cm(0.6)
    p.paragraph_format.first_line_indent = Cm(-0.6)
    set_font(p.add_run(f"{i + 1}. "), 10.5, False, ACCENT)
    set_font(p.add_run(lead), 10.5, True, DARK)
    set_font(p.add_run(body), 10.5, False, None)

# ---- 三条纪律
heading(doc, "三条纪律", 2)
for i, (lead, body) in enumerate([
    ("训练不等理论：", "W1 周一训练试运行必须在理论学完前启动，理论用训练等待的碎片时间学"),
    ("每个实验先写判定标准再跑", "（指标先行），跑完立即存图存表，不留\u201c回头补\u201d"),
    ("每天结束 5 分钟：", "往误差追踪表里加一行当日数据——这是期末交付物\u201c训练—验证—部署记录\u201d的原材料"),
]):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.3
    p.paragraph_format.left_indent = Cm(0.6)
    p.paragraph_format.first_line_indent = Cm(-0.6)
    set_font(p.add_run(f"{i + 1}. "), 10.5, False, ACCENT)
    set_font(p.add_run(lead), 10.5, True, DARK)
    set_font(p.add_run(body), 10.5, False, None)

# ---- 风险与对策
heading(doc, "风险与对策", 2)
table(doc, ["风险", "对策"], [
    ("W2 训练不收敛", "官方配置原样跑基本不会失败；若失败，直接用官方 checkpoint 做 W3 实验（实验方法不变，简历如实写复现+评测）"),
    ("显存不足 1024 envs", "降到 512/256，iter 数加倍；W2 周二是唯一重试窗口"),
    ("环境安装卡死（Isaac Lab 常见）", "W1 前两天专项处理；不行切 WSL2；仍不行用云 GPU（按小时租）"),
    ("中期检查与实验冲突", "中期材料周一整理，只呈现已有数据，不为检查赶新实验"),
], widths=[4.2, 11.8])

doc.save(OUT)
print("saved:", OUT, os.path.getsize(OUT) // 1024, "KB")
