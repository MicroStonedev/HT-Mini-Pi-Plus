# -*- coding: utf-8 -*-
"""W1 详细执行步骤 Markdown → Word 转换。

用法：python tools/build_w1_docx.py
输出：W1详细执行步骤.docx（源 md 保持不动）
"""
import os

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "W1详细执行步骤.docx")

FONT, MONO = "微软雅黑", "Consolas"
DARK = RGBColor(0x0E, 0x3A, 0x57)
ACCENT = RGBColor(0xB0, 0x5A, 0x1E)
GRAY = RGBColor(0x5C, 0x6B, 0x7A)
HEAD_BG, ZEBRA, CODE_BG, CALLOUT = "17557E", "EAF1F7", "F2F4F7", "F0E9E2"


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


def para(doc, runs, size=10.5, align=WD_ALIGN_PARAGRAPH.LEFT,
         space_after=6, line=1.3, indent_cn=0):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = align
    pf.space_after = Pt(space_after)
    pf.line_spacing = line
    if indent_cn:
        pf.first_line_indent = Pt(size * indent_cn)
    for t_, b_, c_ in runs:
        set_font(p.add_run(t_), size, b_, c_)
    return p


def heading(doc, text, level=2):
    h = doc.add_heading(level=level)
    set_font(h.add_run(text), 13, True, DARK)
    h.paragraph_format.space_before = Pt(12)
    h.paragraph_format.space_after = Pt(5)
    return h


def code_block(doc, lines_):
    for i, ln in enumerate(lines_):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.space_after = Pt(1 if i < len(lines_) - 1 else 6)
        pf.space_before = Pt(2 if i == 0 else 0)
        pf.line_spacing = 1.15
        pf.left_indent = Cm(0.35)
        pf.right_indent = Cm(0.2)
        shd = p._p.get_or_add_pPr().makeelement(
            qn("w:shd"), {qn("w:val"): "clear", qn("w:fill"): CODE_BG})
        p._p.get_or_add_pPr().append(shd)
        set_font(p.add_run(ln), 9.5, False, RGBColor(0x1B, 0x27, 0x33), MONO)
    return


def callout(doc, runs, bg=CALLOUT):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(5)
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


def step(doc, label, body=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(4)
    pf.space_after = Pt(3)
    pf.line_spacing = 1.3
    set_font(p.add_run(label), 11, True, ACCENT)
    if body:
        set_font(p.add_run("　" + body), 10.5, False, None)
    return p


def table(doc, headers, rows, widths, font=9.5):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
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

    def fill(cell, text, bg=None, bold=False, white=False):
        if bg:
            cell._tc.get_or_add_tcPr().append(
                cell._tc.get_or_add_tcPr().makeelement(
                    qn("w:shd"), {qn("w:val"): "clear", qn("w:fill"): bg}))
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.15
        set_font(p.add_run(text), font, bold,
                 RGBColor(0xFF, 0xFF, 0xFF) if white else None)

    for j, htext in enumerate(headers):
        c = t.cell(0, j)
        c.width = Cm(widths[j])
        fill(c, htext, bg=HEAD_BG, bold=True, white=True)
    t.rows[0]._tr.get_or_add_trPr().append(
        t.rows[0]._tr.makeelement(qn("w:tblHeader"), {}))
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i + 1, j)
            c.width = Cm(widths[j])
            fill(c, val, bg=ZEBRA if i % 2 else None)
        t.rows[i + 1]._tr.get_or_add_trPr().append(
            t.rows[i + 1]._tr.makeelement(qn("w:cantSplit"), {}))
    return t


doc = Document()
for sec in doc.sections:
    sec.top_margin = sec.bottom_margin = Cm(2.0)
    sec.left_margin = sec.right_margin = Cm(2.2)

fp = doc.sections[0].footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = fp.add_run()
set_font(r, 9, False, GRAY)
f1 = r._r.makeelement(qn("w:fldChar"), {qn("w:fldCharType"): "begin"})
ins = r._r.makeelement(qn("w:instrText"), {})
ins.text = "PAGE \\* arabic \\* MERGEFORMAT"
f2 = r._r.makeelement(qn("w:fldChar"), {qn("w:fldCharType"): "end"})
r._r.append(f1)
r._r.append(ins)
r._r.append(f2)

# ---- 标题
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(2)
set_font(p.add_run("W1 详细执行步骤"), 20, True, DARK)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(10)
set_font(p.add_run("压缩版 ｜ 2026.10.19 – 10.23"), 12, False, GRAY)

callout(doc, [
    ("现实对齐：", True, DARK),
    ("今天 10/19，比原计划晚 10 天启动。W1 压缩为 5 天（10/19–10/23），W2/W3 顺延为 10/24–29 / 10/30–11/04，仍赶得上 11/19 期末。", False, None),
    ("执行环境：", True, DARK),
    ("并行智算云 RTX 3090（24GB 显存 / 32GB 内存，GT-Ubuntu22.04-CMD-V3.0 镜像）。", False, None),
    ("预算估计：", True, DARK),
    ("全程约 25–35 机时 ≈ 90–120 元；不用时关机省钱。", False, None),
    ("W1 判定标准（Proposal）：", True, DARK),
    ("官方策略在 Isaac 中连续行走 ≥5 分钟不跌倒 + 训练能启动。", False, None),
], bg=ZEBRA)

# ---- D0
heading(doc, "D0 · 今晚（10/19，2–3h）：实例开通与基线")
step(doc, "步骤 1：购买实例（5 分钟）",
     "机型 RTX 3090（10 核 32GB）｜镜像 GT-Ubuntu22.04-CMD-V3.0｜计费：按量。⚠️ 系统盘从默认 40GB 改为 ≥150GB（Isaac 全家桶约 15GB，40GB 必爆且不可扩容）。")
step(doc, "步骤 2：VS Code Remote-SSH 接入（10 分钟）",
     "本地 C:\\Users\\15659\\.ssh\\config 追加：")
code_block(doc, [
    "Host paratera",
    "    HostName <控制台给的公网IP>",
    "    User root",
    "    Port <端口>",
    "    IdentityFile ~/.ssh/id_rsa",
])
para(doc, [("之后 VS Code 左下角 → Connect to Host → paratera，终端操作全部在集成终端里做。", False, None)], space_after=6)
step(doc, "步骤 3：基线检查（必须全过再继续）")
code_block(doc, [
    "nvidia-smi          # 驱动版本 ≥525，看到 3090 24GB",
    "df -h /             # 根盘可用 ≥120GB",
    "free -h             # 32GB 内存",
])
step(doc, "步骤 4：基础工具链")
code_block(doc, [
    "apt update && apt install -y git tmux htop build-essential wget",
    "wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh",
    "bash Miniconda3-latest-Linux-x86_64.sh -b -p ~/miniconda3",
    "~/miniconda3/bin/conda init bash && exec $SHELL",
])
callout(doc, [("D0 完成 = 三个绿勾：", True, ACCENT),
              ("nvidia-smi 正常、SSH 顺畅、conda 可用。", False, None)])

# ---- D1
heading(doc, "D1 · 10/20（主攻日，6–8h）：Isaac Sim 4.5 + Isaac Lab 2.1 安装")
para(doc, [("全周最大风险点，预留一整天。所有长命令在 tmux 里跑（SSH 断线不中断）。", True, None)], space_after=5)
step(doc, "步骤 1：Python 3.10 环境")
code_block(doc, ["conda create -n isaaclab python=3.10 -y && conda activate isaaclab"])
step(doc, "步骤 2：安装 Isaac Lab（自带 Isaac Sim 4.5）")
code_block(doc, [
    "pip install --upgrade pip",
    'pip install "isaaclab[sim]"    # 自动拉 isaacsim 全家桶，约 15GB，耗时看网速',
])
para(doc, [("版本以 Isaac Lab 2.1 官方文档（docs.isaacsim.omniverse.nvidia.com）为准；如需显式版本：", False, None)], space_after=3)
code_block(doc, ['pip install isaaclab==2.1.0 isaacsim==4.5.0'])
step(doc, "步骤 3：冒烟验证（headless）")
code_block(doc, ["python -m isaaclab.scripts.tutorials 00_sim/create_empty --headless"])
para(doc, [("成功标志：正常退出、无 traceback、过程中 nvidia-smi 有 GPU 占用。"
            "常见缺库报错：", False, None),
           ("apt install -y libgl1 libxrender1 libxext6", False, GRAY),
           (" 后重试。", False, None)], space_after=6)
step(doc, "步骤 4：立刻打快照 #1",
     "控制台 → 快照 → 创建。此后任何翻车都能 1 分钟回滚到这里。")
callout(doc, [("熔断规则：", True, ACCENT),
              ("同一报错折腾超 6 小时 → ① 换 pip 安装方式（NGC 源/官方 tar 包）② 换 isaacsim 精确版本号 ③ 换 AutoDL 4090 重来（有快照清单，重装约 2h）。", False, None)])

# ---- D2
heading(doc, "D2 · 10/21（4–5h）：AMP 仓库跑通 + W1 判定项")
step(doc, "步骤 1：装仓库")
code_block(doc, [
    "git clone https://github.com/HighTorque-Robotics/Mini-Pi-Plus_AMP.git",
    "cd Mini-Pi-Plus_AMP",
    "pip install -e . && pip install -e rsl_rl",
])
step(doc, "步骤 2：官方策略 Isaac 回放（W1 判定项）")
code_block(doc, [
    "tmux new -s play",
    "python legged_lab/scripts/play.py --task=pi_plus_amp_sym_flat \\",
    "  --num_envs=1 --headless --video",
])
para(doc, [("checkpoint 用法按仓库 README（自带 Exported_policy/ 三个；--load_run/--checkpoint 参数路径以 README 示例为准）；"
            "--video 让它输出 mp4——这就是 Isaac 侧行走的证据素材；跑满 300 秒不摔倒 = W1 判定通过（tmux 里放着，断线不影响）。", False, None)],
     space_after=6)
step(doc, "步骤 3：证据归档")
code_block(doc, ["scp -r paratera:~/Mini-Pi-Plus_AMP/logs/ ./"])
callout(doc, [("判定通过证据 = ", True, ACCENT),
              ("视频 + 日志两样都存进本地 results/。", False, None)])

# ---- D3
heading(doc, "D3 · 10/22（3–4h）：训练试运行")
code_block(doc, [
    "tmux new -s train",
    "conda activate isaaclab",
    "python legged_lab/scripts/train.py --task=pi_plus_amp_sym_flat \\",
    "  --headless --logger=tensorboard --num_envs=1024",
])
para(doc, [("跑 200–500 iter（约 0.5–1.5h）后 Ctrl+C——只验证\u201c能训、曲线正常\u201d，不追求收敛。"
            "顺手 nvidia-smi 记录 1024 envs 的显存占用；若 <16GB，试 2048/4096（为 W2 提速摸底）。", False, None)], space_after=6)
step(doc, "看曲线（SSH 端口转发）")
code_block(doc, [
    "tensorboard --logdir logs --port 6006    # 云端",
    "# 本地另开终端：ssh -L 6006:localhost:6006 paratera",
    "# 浏览器打开 localhost:6006，截图 reward / loss 曲线存档",
])

# ---- D4
heading(doc, "D4 · 10/23（3–4h）：环境固化 + 同步 + 周报")
for label, body in [
    ("版本锁定（Docker 的最小替代，必做）：", None),
    ("Dockerfile v1（时间紧可推到 W2）：", "FROM nvcr.io/nvidia/isaac-sim:4.5.0 + COPY 仓库 + pip install -e ."),
    ("打快照 #2：", "一切装好并验证过的完整状态"),
    ("同步回本地：", "logs / mp4 / yml 全部 scp 回 Windows 备份"),
    ("W1 周报（半小时）：", "判定项打勾 + 曲线截图 + 踩坑记录写入误差追踪表第一行"),
]:
    step(doc, label, body)
code_block(doc, [
    "conda env export > environment-cloud.yml",
    "pip freeze > requirements-freeze.txt",
])

# ---- 面试并行
heading(doc, "与面试并行（若面试在 10/23–29）")
para(doc, [("每天节奏改为：白天环境/实验 4h + 晚上面试复习 2–3h。复习内容直接用三周计划里 W3 的冲刺清单"
            "（PPO clip 手推 / GAE / AMP 判别器 / DR 权衡），并把自己的实测数字讲熟：", False, None)], space_after=4)
for b in ["复现 0.51 m/s（MuJoCo，与官方口径一致）✅ 已有",
          "抗扰边界 80–120 N（三 checkpoint 一致）✅ 已有",
          "Isaac 训练环境搭建中，checkpoint 管线已打通 ✅ 诚实口径"]:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.3
    p.paragraph_format.left_indent = Cm(0.6)
    p.paragraph_format.first_line_indent = Cm(-0.42)
    set_font(p.add_run("• "), 10.5, False, ACCENT)
    set_font(p.add_run(b), 10.5, False, None)
callout(doc, [("已有 MuJoCo 成果就是面试底气，Isaac 进行中完全不用心虚。", True, DARK)])

# ---- 速查表
heading(doc, "速查：五个最容易翻车的点")
table(doc, ["坑", "症状", "对策"], [
    ("系统盘 40GB 没改", "装到一半 No space left", "买实例时就改 150GB+；已买错→重开实例（还没装东西损失小）"),
    ("Python 版本", "pip 装不上/运行报错", "必须 conda 3.10，不要用系统 python"),
    ("无显示器报错", "Vulkan/OpenGL 相关", "所有命令带 --headless"),
    ("SSH 断线任务死", "长安装/训练中断", "一律 tmux；tmux attach -t train 回到会话"),
    ("下载慢/超时", "NGC 源拉包慢", "夜间挂 tmux 下载；重试两次换时段"),
], widths=[3.2, 4.6, 8.2])

# ---- 打勾清单
heading(doc, "每日完成判定（打勾制）")
for d in ["D0：nvidia-smi ✓ + conda ✓ + VS Code 连通 ✓",
          "D1：headless 空场景跑通 ✓ + 快照 #1 ✓",
          "D2：官方策略 300s 行走视频 + 日志 ✓",
          "D3：训练曲线截图 + 显存记录 ✓",
          "D4：环境 yml + 快照 #2 + 周报 ✓"]:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.3
    p.paragraph_format.left_indent = Cm(0.6)
    p.paragraph_format.first_line_indent = Cm(-0.6)
    set_font(p.add_run("☐  "), 11, False, ACCENT)
    set_font(p.add_run(d), 10.5, False, None)

doc.save(OUT)
print("saved:", OUT, os.path.getsize(OUT) // 1024, "KB")
