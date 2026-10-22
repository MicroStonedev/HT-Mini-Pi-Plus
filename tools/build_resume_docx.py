# -*- coding: utf-8 -*-
"""生成更新版实习简历 Word 文档（具身智能方向）。

用法：python tools/build_resume_docx.py
输出：D:\\研一上课程\\实习求职\\实习简历_更新版.docx
"""
import os

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = r"D:\研一上课程\实习求职\实习简历_具身智能_v4.docx"

DARK = RGBColor(0x17, 0x3A, 0x5E)   # 深蓝（节标题）
GRAY = RGBColor(0x5C, 0x6B, 0x7A)   # 次要信息
BODY, HEAD_FONT = "微软雅黑", "微软雅黑"


def set_font(run, size=10.5, bold=False, color=None, name=BODY):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color
    r = run._element.rPr
    rfonts = r.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = r.makeelement(qn("w:rFonts"), {})
        r.append(rfonts)
    rfonts.set(qn("w:eastAsia"), name)
    rfonts.set(qn("w:ascii"), name)
    rfonts.set(qn("w:hAnsi"), name)


def para(doc, runs, space_after=4, space_before=0, align=None, indent=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(space_before)
    pf.line_spacing = 1.0
    if align is not None:
        pf.alignment = align
    if indent is not None:
        pf.left_indent = Cm(indent)
    for text, size, bold, color in runs:
        set_font(p.add_run(text), size, bold, color)
    return p


def section_title(doc, text):
    p = para(doc, [(text, 12.5, True, DARK)], space_after=2, space_before=3)
    pPr = p._p.get_or_add_pPr()
    borders = pPr.makeelement(qn("w:pBdr"), {})
    bottom = pPr.makeelement(qn("w:bottom"), {
        qn("w:val"): "single", qn("w:sz"): "8",
        qn("w:space"): "2", qn("w:color"): "173A5E"})
    borders.append(bottom)
    pPr.append(borders)
    return p


def no_borders(tbl):
    """去掉表格所有边框（含内部线）。

    注意：OOXML 的 CT_TblPrBase 对子元素顺序有强制要求，
    tblBorders 必须位于 tblLayout / tblLook 之前——放错位置
    LibreOffice 会宽容渲染，但 WPS 会整段忽略，导致默认边框
    （虚线框）重新出现。因此这里按 schema 顺序插入。
    """
    tblPr = tbl._tbl.tblPr
    borders = tblPr.makeelement(qn("w:tblBorders"), {})
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = borders.makeelement(qn(f"w:{edge}"), {
            qn("w:val"): "none", qn("w:sz"): "0",
            qn("w:space"): "0", qn("w:color"): "auto"})
        borders.append(el)
    # 插到 tblLayout / tblCellMar / tblLook 之前（schema 顺序）
    anchor = None
    for tag in ("w:tblLayout", "w:tblCellMar", "w:tblLook"):
        anchor = tblPr.find(qn(tag))
        if anchor is not None:
            break
    if anchor is not None:
        anchor.addprevious(borders)
    else:
        tblPr.append(borders)
    # 双保险：每个单元格也显式声明无边框
    for row in tbl.rows:
        for cell in row.cells:
            tcPr = cell._tc.get_or_add_tcPr()
            if tcPr.find(qn("w:tcBorders")) is None:
                tcb = tcPr.makeelement(qn("w:tcBorders"), {})
                for edge in ("top", "left", "bottom", "right"):
                    el = tcb.makeelement(qn(f"w:{edge}"), {
                        qn("w:val"): "none", qn("w:sz"): "0",
                        qn("w:space"): "0", qn("w:color"): "auto"})
                    tcb.append(el)
                tcPr.append(tcb)


def row_table(doc, time_text, title_text, role_text):
    t = doc.add_table(rows=1, cols=3)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    widths = (Cm(3.4), Cm(9.6), Cm(3.6))
    for i, w in enumerate(widths):
        t.columns[i].width = w
        t.cell(0, i).width = w
    for i, txt in enumerate((time_text, title_text, role_text)):
        cell = t.cell(0, i)
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(1)
        set_font(p.add_run(txt), 9.5, i == 1,
                 DARK if i == 1 else GRAY)
    no_borders(t)
    return t


def bullet(doc, head, body, space_after=3):
    runs = [("■ ", 10.5, False, DARK)]
    if head:
        runs.append((head, 10.5, True, None))
    runs.append((body, 10.5, False, None))
    para(doc, [runs[0]] if not body else runs, space_after=space_after, indent=0.5)


def bullet_rich(doc, head, body, space_after=1):
    """head 加粗 + body 正文的单条经历。"""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(space_after)
    pf.line_spacing = 1.0
    pf.left_indent = Cm(0.5)
    set_font(p.add_run("• "), 9.5, False, DARK)
    if head:
        set_font(p.add_run(head), 9.5, True, None)
    set_font(p.add_run(body), 9.5, False, None)
    return p


doc = Document()
for sec in doc.sections:
    sec.top_margin = sec.bottom_margin = Cm(1.0)
    sec.left_margin = sec.right_margin = Cm(1.35)

# ---------------- 头部（左：姓名与联系方式；右：证件照）
PHOTO = r"D:\研一上课程\实习求职\photo.jpg"
header_tbl = doc.add_table(rows=1, cols=2)
header_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
header_tbl.autofit = False
header_tbl.columns[0].width = Cm(14.2)
header_tbl.columns[1].width = Cm(3.2)
header_tbl.rows[0].cells[0].width = Cm(14.2)
header_tbl.rows[0].cells[1].width = Cm(3.2)
no_borders(header_tbl)

left = header_tbl.rows[0].cells[0]
left.vertical_alignment = 1  # center
p0 = left.paragraphs[0]
p0.paragraph_format.space_after = Pt(2)
p0.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
set_font(p0.add_run("赵 小 刚"), 20, True, DARK)
p1 = left.add_paragraph()
p1.paragraph_format.space_after = Pt(1)
set_font(p1.add_run("求职方向：具身智能 / 机器人算法实习"), 10, True, DARK)
p2 = left.add_paragraph()
p2.paragraph_format.space_after = Pt(0)
set_font(p2.add_run("2000.09 丨 中共党员 丨 电话：18851871898 丨 邮箱：1565914951@qq.com"), 10, False, GRAY)

right = header_tbl.rows[0].cells[1]
right.vertical_alignment = 1
rp = right.paragraphs[0]
rp.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
if os.path.isfile(PHOTO):
    rp.add_run().add_picture(PHOTO, width=Cm(2.32), height=Cm(3.24))
para(doc, [("", 2, False, None)], space_after=0)

# ---------------- 教育背景
section_title(doc, "教育背景")
bullet_rich(doc, "2026.09–2028.06　清华大学　电子信息　硕士（在读）：",
            "方向为具身智能与机器人运动控制（企业合作课题组成员）")
bullet_rich(doc, "2018.09–2022.06　东南大学　机械工程　本科：",
            "绩点 3.22/4.0（前 40%）丨 国家励志奖学金 ×2 丨 校级创新体验竞赛一等奖丨核心课程：计算机综合课程设计（93）、计算方法（98）", space_after=1)

# ---------------- 项目经历
section_title(doc, "项目经历")

row_table(doc, "2026.09 – 至今", "人形机器人行走策略训练与真实场景仿真", "核心成员（2 人）")
para(doc, [("清华企业合作课题（高擎机电 × 群核科技）核心模块：负责人形机器人 Mini Pi+（20 关节）强化学习行走策略的 Sim2Real 全链路；前三周已完成策略复现、自训练、双引擎验证、DR 参数实验与误差量化，全部脚本化、结果可复现。", 9.5, False, None)],
     indent=0.5, space_after=2)
bullet_rich(doc, "W1 策略复现与评测基座：",
            "逐行复刻官方策略链路（345 维观测→MLP→20 维动作→PD 控制）；搭建 MuJoCo 无头评测环境，实测官方策略 0.51 m/s 与官方口径一致；修复官方脚本键盘控制缺陷，策略导出 TorchScript")
bullet_rich(doc, "W2 PPO 自训练与双引擎验证：",
            "Isaac Lab 训练 PPO 行走策略（官方奖励配置起步、并行 1024 环境），自训策略导出后 MuJoCo sim2sim 回放连续行走 ≥60 s、速度【实测】m/s；与官方策略做双引擎稳定性对照")
bullet_rich(doc, "W3 Domain Randomization 参数实验：",
            "针对“过宽策略保守、过窄真机易摔”的权衡，在摩擦与外力两维多档区间对照训练，以 sim2sim 存活率确定最终训练参数范围")
bullet_rich(doc, "W3 误差来源量化实验：",
            "单变量对照量化三类因素影响——PD 参数偏移 ±20%–50%、IMU 观测噪声、控制延迟注入，记录退化曲线并汇总为误差对照表，供真机调试排查")
bullet_rich(doc, "真实场景重建与鲁棒性评测：",
            "无头测试脚本施加周期性推力扰动（0–120 N 四档、方向随机）自动统计摔倒率，确定抗扰边界 80–120 N；解析激光雷达点云（197 万点）转 MuJoCo 可行走场景（真实房间 9.4×8.8 m），量化确认课桌几何不可恢复后采用混合建模", space_after=3)

row_table(doc, "2022.02 – 2022.06", "机器人紧凑组合关节模块设计（毕业设计）", "独立完成")
bullet_rich(doc, "",
            "面向膝关节假肢测试设计模拟人体下肢的测试平台：分析步态特征，完成躯干–大腿–髋关节结构与驱动方案设计，关键件通过强度/寿命校核，Adams 动力学仿真验证可行性", space_after=2)

# ---------------- 技能专长
section_title(doc, "技能专长")
bullet_rich(doc, "编程与数据：", "Python（PyTorch、NumPy）、C++；Git、Docker；Linux/Windows 双平台；CET-6（可读英文文献与文档）")
bullet_rich(doc, "机器人仿真：", "MuJoCo（策略验证与批量评测，自建无头测试框架）；Isaac Lab（PPO 强化学习训练）")
bullet_rich(doc, "具身智能链路：", "熟悉 Sim2Real 方法（Domain Randomization、PD 控制、误差归因）；了解 ROS 2 推理部署与 RKNN/TensorRT 模型转换链路")

# ---------------- 校园经历
section_title(doc, "其他")
bullet_rich(doc, "校园经历：", "2019.07–09 暑期社会实践项目负责人，调研成果发表于中青在线", space_after=1)
bullet_rich(doc, "自我评价：", "机械本科 + 电子信息硕士复合背景；方向：具身智能与人形机器人运动控制", space_after=1)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
doc.save(OUT)
print("saved:", OUT, os.path.getsize(OUT) // 1024, "KB")
