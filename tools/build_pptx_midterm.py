# -*- coding: utf-8 -*-
"""生成《中期检查报告》PPT（11 页，16:9）+ 演讲者备注。

用法：python tools/build_pptx_midterm.py
输出：中期检查报告_第7组.pptx（项目根目录）
"""
from __future__ import annotations

import os

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "中期检查报告_第7组.pptx")

# ---------------------------------------------------------------- 设计常量
FONT = "微软雅黑"
BG_DARK, BG_LIGHT = "0F1C2E", "F5F7FA"
PRIMARY, PRIMARY_DK = "17557E", "0E3A57"
ACCENT = "E8833A"
OK_GREEN = "2E7D4F"
TINT = "DCE7EF"
TINT_SOFT = "EAF1F7"
TEXT, MUTED, WHITE = "1B2733", "5C6B7A", "FFFFFF"

W, H = Inches(13.333), Inches(7.5)
MARGIN = Inches(0.62)


def _set_run(run, size, color=TEXT, bold=False, name=FONT, italic=False):
    f = run.font
    f.size, f.bold, f.italic, f.name = Pt(size), bold, italic, name
    f.color.rgb = RGBColor.from_string(color)
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {})
            rPr.append(el)
        el.set("typeface", name)


def add_text(slide, x, y, w, h, lines, align=PP_ALIGN.LEFT,
             anchor=MSO_ANCHOR.TOP, space_after=6, line_spacing=1.15):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, runs in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        p.line_spacing = line_spacing
        for (t, size, color, bold) in runs:
            r = p.add_run()
            r.text = t
            _set_run(r, size, color, bold)
    return box


def add_rect(slide, x, y, w, h, fill=None, line=None, radius=None, shadow=False):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    sp = slide.shapes.add_shape(shape_type, x, y, w, h)
    if radius is not None:
        sp.adjustments[0] = radius
    if fill:
        sp.fill.solid()
        sp.fill.fore_color.rgb = RGBColor.from_string(fill)
    else:
        sp.fill.background()
    if line:
        sp.line.color.rgb = RGBColor.from_string(line)
        sp.line.width = Pt(1.0)
    else:
        sp.line.fill.background()
    sp.shadow.inherit = False
    if shadow:
        el = sp._element.spPr
        effect = el.makeelement(qn("a:effectLst"), {})
        outer = el.makeelement(qn("a:outerShdw"),
                               {"blurRad": "90000", "dist": "38100", "dir": "5400000",
                                "rotWithShape": "0"})
        clr = el.makeelement(qn("a:srgbClr"), {"val": "1B2733"})
        alpha = el.makeelement(qn("a:alpha"), {"val": "16000"})
        clr.append(alpha)
        outer.append(clr)
        effect.append(outer)
        el.append(effect)
    sp.text_frame.word_wrap = True
    return sp


def page_title(slide, text, sub=None):
    add_text(slide, MARGIN, Inches(0.42), Inches(11.6), Inches(0.6),
             [[(text, 30, PRIMARY_DK, True)]])
    if sub:
        add_text(slide, MARGIN, Inches(1.02), Inches(11.6), Inches(0.34),
                 [[(sub, 13, MUTED, False)]])


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def stat(slide, x, y, w, num, label, num_color=ACCENT, num_size=34, label_size=11.5):
    add_text(slide, x, y, w, Inches(0.7), [[(num, num_size, num_color, True)]])
    add_text(slide, x, y + Inches(0.62), w, Inches(0.5),
             [[(label, label_size, MUTED, False)]], line_spacing=1.15)


def row_item(slide, x, y, w, head, body, head_color=PRIMARY_DK):
    add_text(slide, x, y, w, Inches(0.32), [[(head, 14.5, head_color, True)]])
    add_text(slide, x, y + Inches(0.30), w, Inches(0.5),
             [[(body, 12, MUTED, False)]], line_spacing=1.2)


def table(slide, x, y, w, headers, rows, col_w=None, row_h=0.42,
          head_h=0.4, font_size=10.5):
    """简单表格：深色表头 + 浅色隔行。"""
    n_rows, n_cols = len(rows) + 1, len(headers)
    shp = slide.shapes.add_table(n_rows, n_cols, x, y, w,
                                 Inches(head_h + row_h * len(rows)))
    tbl = shp.table
    tbl.first_row = True
    if col_w:
        total = sum(col_w)
        for j, cw in enumerate(col_w):
            tbl.columns[j].width = Inches(w.inches * cw / total)
    for j, h in enumerate(headers):
        cell = tbl.cell(0, j)
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor.from_string(PRIMARY)
        cell.margin_left = cell.margin_right = Inches(0.07)
        cell.margin_top = cell.margin_bottom = Inches(0.03)
        tf = cell.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = h
        _set_run(r, 10.5, WHITE, True)
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            cell = tbl.cell(i + 1, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor.from_string(
                "FFFFFF" if i % 2 == 0 else TINT_SOFT)
            cell.margin_left = cell.margin_right = Inches(0.07)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            r = p.add_run()
            r.text = str(v)
            _set_run(r, font_size, TEXT, False)
    return tbl


# ---------------------------------------------------------------- 演示文稿
prs = Presentation()
prs.slide_width, prs.slide_height = W, H
BLANK = prs.slide_layouts[6]


def new_slide(dark=False):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = RGBColor.from_string(
        BG_DARK if dark else BG_LIGHT)
    return s


# ============================== P1 封面
s = new_slide(dark=True)
add_text(s, MARGIN, Inches(0.8), Inches(10.0), Inches(0.4),
         [[("THU SIGS AIID × 高擎机电 · 群核科技 合作课题 · 中期检查", 14, TINT, False)]])
add_text(s, MARGIN, Inches(1.75), Inches(10.5), Inches(1.8),
         [[("强化学习运控与 Sim2Real", 44, WHITE, True)],
          [("从真实空间数据到自主训练：仿真链路的完整打通", 20, TINT, False)]],
         space_after=14)
add_rect(s, MARGIN, Inches(3.85), Inches(0.9), Inches(0.045), fill=ACCENT)
add_text(s, MARGIN, Inches(4.2), Inches(8.6), Inches(1.5),
         [[("主课题：高擎机电 方向二「强化学习运控与 Sim2Real」", 15, WHITE, False)],
          [("辅课题：群核科技 方向二「空间数据与具身智能训练」", 15, WHITE, False)],
          [("报告周期：第 1–3 周（10/19 – 10/27）", 15, TINT, False)]],
         space_after=8)
for i, (n, l) in enumerate([("15000", "自主训练迭代"),
                            ("365 s", "回放零跌倒"),
                            ("88%", "跨引擎达官方")]):
    x = Inches(8.75 + i * 1.5)
    add_text(s, x, Inches(4.95), Inches(1.5), Inches(0.45), [[(n, 20, ACCENT, True)]])
    add_text(s, x, Inches(5.48), Inches(1.45), Inches(0.4),
             [[(l, 10.5, TINT, False)]], line_spacing=1.1)
add_text(s, MARGIN, Inches(6.5), Inches(9.0), Inches(0.4),
         [[("第 7 组：赵小刚 / 赵胤泽    2026 年 10 月 27 日", 13, TINT, False)]])
notes(s, "开场（20秒）：各位老师好，第七组中期检查汇报。主课题高擎方向二强化学习运控，辅课题群核方向二空间数据，"
         "报告覆盖前三周进度。右下三个数字：自主训练一万五千次迭代、回放三百六十五秒零跌倒、跨引擎达到官方水平的百分之八十八。")

# ============================== P2 课题与链路
s = new_slide()
page_title(s, "课题定位：一条链路，两段职责", "为什么这两个方向能接起来")
add_text(s, MARGIN, Inches(1.62), Inches(5.6), Inches(0.34),
         [[("主课题 · 高擎机电 方向二", 15, PRIMARY_DK, True)]])
add_text(s, MARGIN, Inches(2.0), Inches(5.7), Inches(1.5),
         [[("强化学习运控与 Sim2Real", 20, TEXT, True)]],
         space_after=6)
add_text(s, MARGIN, Inches(2.5), Inches(5.7), Inches(1.6),
         [[("考察点：策略能否在仿真中稳定行走、迁移后是否鲁棒、每一步误差来源是否写清。", 12.5, MUTED, False)]],
         line_spacing=1.3)
add_text(s, Inches(6.7), Inches(1.62), Inches(5.6), Inches(0.34),
         [[("辅课题 · 群核科技 方向二", 15, PRIMARY_DK, True)]])
add_text(s, Inches(6.7), Inches(2.0), Inches(5.8), Inches(1.5),
         [[("空间数据与具身智能训练", 20, TEXT, True)]], space_after=6)
add_text(s, Inches(6.7), Inches(2.5), Inches(5.8), Inches(1.6),
         [[("考察点：真实空间数据能否转成可训练的仿真场景、数据边界在哪里。", 12.5, MUTED, False)]],
         line_spacing=1.3)
add_rect(s, MARGIN, Inches(3.85), Inches(12.1), Inches(0.02), fill=TINT)
add_text(s, MARGIN, Inches(4.05), Inches(12.1), Inches(0.34),
         [[("本次中期交付的六段链路", 14, PRIMARY_DK, True)]])
chain = [("① 官方策略复现", "MuJoCo 定量评测"), ("② 教室场景重建", "真实点云 + 程序化布局"),
         ("③ Isaac 环境搭建", "4090 云端全栈"), ("④ 自主训练", "15000 iter / 4096 envs"),
         ("⑤ 消融实验", "扰动 + 摩擦"), ("⑥ sim2sim 验证", "跨引擎回流")]
for i, (h, b) in enumerate(chain):
    x = MARGIN + Inches(i * 2.02)
    add_rect(s, x, Inches(4.5), Inches(1.88), Inches(1.7),
             fill=WHITE if i < 6 else TINT_SOFT, shadow=True)
    add_text(s, x + Inches(0.12), Inches(4.62), Inches(1.66), Inches(0.5),
             [[(h, 12, PRIMARY_DK, True)]], line_spacing=1.1)
    add_text(s, x + Inches(0.12), Inches(5.12), Inches(1.66), Inches(0.9),
             [[(b, 10, MUTED, False)]], line_spacing=1.2)
notes(s, "约40秒：课题定位先说清。高擎方向二考察三件事——仿真能不能稳定走、迁移后是否鲁棒、误差来源能不能写清。"
         "群核方向二考察真实空间数据能不能转成可训练场景。这两件事天然是一条链：群核提供在哪里练，高擎解决怎么练。"
         "中期我们打通了六段：复现、场景、环境、训练、消融、跨引擎验证。下面逐段看。")

# ============================== P3 计划 vs 实际（核心页）
s = new_slide()
page_title(s, "六周计划 vs 实际进度", "原计划 10/19 启动 · 实际执行到第 3 周完成 4 周工作量")
table(s, MARGIN, Inches(1.55), Inches(12.1),
      ["周次", "原计划内容", "实际完成", "状态"],
      [("W1", "环境搭建 + 判定项（回放 300s 不倒）", "D0–D4 全部完成，含 365s 回放证据", "✅ 完成"),
       ("W2", "自主训练 + 消融实验 + sim2sim", "15000 iter 训练、B/C 组消融、跨引擎 87–88%", "✅ 完成"),
       ("W3", "DR 实验 + 误差量化 + 中期检查", "素材制作 + PPT v2 + 本文档（DR 实验待补）", "🔵 进行中"),
       ("W4", "误差量化收尾 + 真机前置准备", "未开始（依赖硬件）", "⬜ 待启动"),
       ("W5–W6", "真机部署 + 完整评测报告", "未开始（依赖硬件）", "⬜ 待启动")],
      col_w=[0.7, 4.3, 5.2, 1.6], row_h=0.62, font_size=11)
add_rect(s, MARGIN, Inches(5.55), Inches(5.9), Inches(1.45), fill=TINT_SOFT)
add_text(s, MARGIN + Inches(0.2), Inches(5.68), Inches(5.5), Inches(1.2),
         [[("进度判断", 13, PRIMARY_DK, True)],
          [("仿真侧（W1–W2）提前一周完成；W3 起转入交付与误差量化，整体进度可控。", 11.5, MUTED, False)]],
         line_spacing=1.3)
add_rect(s, Inches(6.8), Inches(5.55), Inches(5.92), Inches(1.45), fill="FDF1E7")
add_text(s, Inches(7.0), Inches(5.68), Inches(5.5), Inches(1.2),
         [[("主要偏差与原因", 13, ACCENT, True)],
          [("平台 GPU 三次售罄 + 网络故障 + 本地硬件升级（SSD），累计损失约 2 天；已用 W2 的超前完成吸收。", 11.5, MUTED, False)]],
         line_spacing=1.3)
notes(s, "约80秒：这一页是中期检查的核心——计划对实际。原计划六周，目前执行到第三周。W1 的原定判定项是官方策略在 Isaac 里连续走 300 秒不摔倒，"
         "我们实际做到 365 秒、零跌倒，提前完成。W2 原计划做自主训练和消融，实际完成了 15000 次迭代训练、扰动和摩擦两组消融，"
         "还额外做了跨引擎验证，等于把第四周的部分工作提前做了。也就是说仿真侧整体提前约一周。"
         "偏差主要来自平台侧：GPU 三次售罄、网络间歇故障，加上本地换了固态硬盘，累计损失两天，已经被提前量吸收。"
         "诚实的部分：W3 原计划的域随机化实验还没做，这个和误差量化一起排在下一步。")

# ============================== P4 阶段一：复现与评测
s = new_slide()
page_title(s, "阶段一：官方策略复现与定量评测", "在 MuJoCo 建立可复现的验证环境")
add_text(s, MARGIN, Inches(1.6), Inches(6.4), Inches(0.34),
         [[("做了什么", 14, PRIMARY_DK, True)]])
for i, (h, b) in enumerate([
    ("无头验证运行器", "观测构建 / PD 控制 / 动作映射与官方脚本逐行对齐，可在无显示器环境定量测试"),
    ("策略导出", "checkpoint → TorchScript，绕开官方脚本的加载依赖，GUI 与无头共用"),
    ("推力扰动评测", "周期性水平推力 + 采样相位随机，统计存活率与速度退化"),
    ("教室场景接入", "同一份策略在空地/真实教室双场景对照"),
]):
    row_item(s, MARGIN, Inches(2.02) + i * Inches(0.92), Inches(6.2), h, b)
add_text(s, Inches(7.3), Inches(1.6), Inches(5.4), Inches(0.34),
         [[("实测结果", 14, PRIMARY_DK, True)]])
for i, (n, l) in enumerate([("0.51 m/s", "教室场景行走速度（平地 0.49）"),
                            ("6.1 m / 12 s", "沿中央过道从后部到讲台"),
                            ("80–120 N", "官方策略抗扰边界（三 checkpoint 一致）")]):
    stat(s, Inches(7.3), Inches(2.05) + i * Inches(1.05), Inches(5.2), n, l, num_size=30)
add_rect(s, Inches(7.3), Inches(5.3), Inches(5.4), Inches(1.5), fill=TINT_SOFT)
add_text(s, Inches(7.5), Inches(5.45), Inches(5.0), Inches(1.2),
         [[("价值", 12.5, PRIMARY_DK, True)],
          [("建立了不依赖 GPU 的快速验证通道：策略出问题先在 MuJoCo 定位，再回 Isaac 复查。", 11.5, MUTED, False)]],
         line_spacing=1.3)
notes(s, "约50秒：阶段一。高擎官方提供了 URDF、训练框架和三个预训练 checkpoint。我们做了两件事让它可以被定量测试："
         "一是写无头运行器，把官方脚本的观测构建、PD 控制、动作映射逐行复刻，这样在没有显示器的服务器上也能跑；"
         "二是把 checkpoint 导出成 TorchScript，绕开官方脚本对训练库的加载依赖。右边是实测：教室场景 0.51 米每秒，"
         "跟平地 0.49 基本一致，说明课桌障碍没拖慢策略；抗扰边界在 80 到 120 牛之间，三个 checkpoint 结果完全一致。"
         "这套环境的价值是：后面所有实验都先在 MuJoCo 快速验证，再回 Isaac 复查，省 GPU 时间。")

# ============================== P5 阶段二：教室场景
s = new_slide()
page_title(s, "阶段二：群核教室场景重建", "真实点云 + 程序化布局：数据边界的量化结论")
add_text(s, MARGIN, Inches(1.6), Inches(5.5), Inches(0.34),
         [[("数据边界（三轮量化分析）", 14, PRIMARY_DK, True)]])
for i, (h, b) in enumerate([
    ("97% 的点集中在 0.6 m 内", "197 万点中约 190 万在扫描者站立处——手持激光雷达的典型分布"),
    ("桌面高度带无桌椅上结构", "0.55–0.85 m 层俯视只有一条斜向线状分布（线缆/横梁）"),
    ("桌腿层同样不成形", "3DGS 点云是体积散射，桌椅几何不在其中"),
]):
    row_item(s, MARGIN, Inches(2.02) + i * Inches(0.95), Inches(5.5), h, b)
pic = os.path.join(ROOT, "results", "plots", "scene_check_top.png")
if os.path.exists(pic):
    s.shapes.add_picture(pic, Inches(6.5), Inches(1.6), width=Inches(5.4))
add_text(s, Inches(6.5), Inches(5.95), Inches(5.5), Inches(0.9),
         [[("方案：真实数据（房间 9.4×8.8 m、地面高度、地板色）+ 程序化布局（25 张课桌 0.75 m、讲台 1.15 m、中央 1.6 m 过道）",
            11, MUTED, False)]], line_spacing=1.25)
notes(s, "约50秒：阶段二是群核辅线的落地。素材包是余姚四中的空教室点云，197 万个点。我们做了三轮统计才敢动手："
         "第一，97% 的点挤在扫描者站立的 0.6 米范围内，这是手持雷达的典型分布；第二，桌面高度带俯视看不到课桌行列；"
         "第三，桌腿层也不成形——因为 3DGS 点云是体积散射，桌椅几何在压缩后的高斯基元里，不在这份点云里。"
         "所以方案是真实数据加程序化布局：房间尺寸、地面高度、地板颜色来自真实扫描，课桌椅按标准中学尺寸建模。"
         "下一步接 SpatialLM 的结构化输出，换成数据驱动的真实布局。")

# ============================== P6 阶段三：Isaac 环境
s = new_slide()
page_title(s, "阶段三：Isaac 训练环境搭建", "云端 4090 全栈 + 26 项关键技术问题")
add_text(s, MARGIN, Inches(1.6), Inches(6.3), Inches(0.34),
         [[("环境构成", 14, PRIMARY_DK, True)]])
for i, (h, b) in enumerate([
    ("Isaac Sim 4.5 + Isaac Lab 2.1", "源码安装（pip 版为骨架包，envs 需源码）"),
    ("4096 并行环境", "单卡 4090，显存占用 10.6 GB / 24 GB"),
    ("自愈式部署", "复原脚本 v2：任意新实例 20–40 分钟重建全栈"),
    ("版本锁定", "conda env + pip freeze，环境可精确复现"),
]):
    row_item(s, MARGIN, Inches(2.02) + i * Inches(0.92), Inches(6.1), h, b)
add_text(s, Inches(7.2), Inches(1.6), Inches(5.5), Inches(0.34),
         [[("过程中的技术问题（已归档 26 项）", 14, PRIMARY_DK, True)]])
for i, (h, b) in enumerate([
    ("依赖链：10 项", "flatdict 构建失败 / setuptools 兼容 / API 改名（quat_apply_inverse）"),
    ("平台网络：6 项", "GitHub 不可达（本地上传中转）/ S3 资产加载失败（本地化修补）/ pip 涓流卡死（自愈循环）"),
    ("渲染栈：6 项", "Vulkan ICD 缺失 / EULA 交互 / 相机观测污染 / pycache 幽灵"),
]):
    row_item(s, Inches(7.2), Inches(2.02) + i * Inches(1.05), Inches(5.4), h, b)
add_rect(s, Inches(7.2), Inches(5.35), Inches(5.4), Inches(1.45), fill=TINT_SOFT)
add_text(s, Inches(7.4), Inches(5.48), Inches(5.0), Inches(1.2),
         [[("为什么值得记录", 12.5, PRIMARY_DK, True)],
          [("每项都有「症状 → 根因 → 修法」，已写入复原脚本与误差追踪表——这是环境可复现的前提。", 11.5, MUTED, False)]],
         line_spacing=1.3)
notes(s, "约60秒：阶段三是环境搭建，也是本期最大的工程量。Isaac Sim 4.5 加 Isaac Lab 2.1，在云端 4090 上跑 4096 个并行环境。"
         "这里遇到并解决了 26 项技术问题，分三类：依赖链问题——比如一个旧依赖在新 setuptools 下构建失败、框架 API 改名；"
         "平台网络问题——GitHub 不可达、官方资产从海外 S3 加载失败、大文件下载涓流卡死，分别用本地上传中转、资产本地化、自愈循环解决；"
         "渲染栈问题——云平台的 GPU 驱动分「计算型」和「完整型」，前者没有 Vulkan，Isaac 的渲染初始化会直接段错误。"
         "这些全部写成了复原脚本，现在任何一台新机器 20 到 40 分钟能重建，这是后面所有实验的前提。")

# ============================== P7 阶段四：自主训练
s = new_slide()
page_title(s, "阶段四：自主训练成果", "4096 并行环境 · AMP 算法 · 15000 次迭代 · 11 小时")
curve = os.path.join(ROOT, "results", "w2", "plots", "run1_training_curves.png")
if os.path.exists(curve):
    s.shapes.add_picture(curve, MARGIN, Inches(1.65), width=Inches(7.2))
for i, (n, l) in enumerate([("-2 → 95", "训练平均奖励"),
                            ("17 → 998 步", "回合长度（触顶）"),
                            ("0.093", "10000 iter 回放奖励（超官方 0.085）"),
                            ("4.0 GB", "显存占用 @1024 envs")]):
    stat(s, Inches(8.15), Inches(1.75) + i * Inches(1.15), Inches(4.4), n, l, num_size=22)
add_text(s, Inches(8.15), Inches(6.35), Inches(4.4), Inches(0.7),
         [[("三档 checkpoint 验证：5000 追平 → 10000 反超 → 15000 终验 335 s 零跌倒",
            11.5, PRIMARY_DK, True)]], line_spacing=1.25)
notes(s, "约50秒：阶段四是本次的核心成果——从「用官方的策略」到「训练自己的策略」。4096 个环境并行、AMP 算法、15000 次迭代、11 小时。"
         "左图两条曲线：奖励从负 2 爬到 95，回合长度从 17 步涨到 998 步的上限。回合长度是学习进度最直接的指标——"
         "从一步就摔到能稳定走到回合结束。我们做了三档 checkpoint 验证：5000 次时追平官方、10000 次反超、"
         "15000 次终验跑了 335 秒零跌倒。显存只用了 4 GB，说明还有很大提速空间。")

# ============================== P8 阶段五：消融
s = new_slide()
page_title(s, "阶段五：消融实验（鲁棒性边界）", "同一套自研工具，对官方与自训策略做对照")
abl = os.path.join(ROOT, "results", "w2", "plots", "ablation_BC.png")
if os.path.exists(abl):
    s.shapes.add_picture(abl, MARGIN, Inches(1.65), width=Inches(6.9))
add_text(s, Inches(7.8), Inches(1.65), Inches(5.0), Inches(0.34),
         [[("结论", 14, PRIMARY_DK, True)]])
for i, (h, b) in enumerate([
    ("自训边界 40–80 N", "40 N 三次推力全部存活，80 N 起被推倒"),
    ("官方边界 80–120 N", "同工具测得，方法对齐可复现"),
    ("差距归因：训练量", "自训为官方 37.5%（15000 vs 40000 iter），边界下移一档符合预期"),
    ("摩擦鲁棒性完整", "0.4 / 0.8 / 1.2 三档零跌倒，低摩擦下奖励最高"),
]):
    row_item(s, Inches(7.8), Inches(2.05) + i * Inches(1.15), Inches(4.9), h, b)
notes(s, "约45秒：阶段五消融。我们写了一套参数化的扰动/摩擦注入工具，两种策略用同一套方法测，结果可比。"
         "左边两组柱状图：推力测试里，自训策略 40 牛三次全部存活，80 牛起被推倒；官方策略的边界在 80 到 120 牛。"
         "这个差距是训练量决定的——我们训了 15000 次，官方是 40000 次，只有 37.5%，边界低一档在预期内。"
         "右边摩擦：0.4 到 1.2 三档全部零跌倒，说明策略对地面材质不敏感。")

# ============================== P9 阶段六：sim2sim
s = new_slide()
page_title(s, "阶段六：sim2sim 跨引擎验证", "Isaac 训练 → MuJoCo 零微调部署")
table(s, MARGIN, Inches(1.6), Inches(11.2),
      ["测试项", "官方策略", "自训策略（15000 iter）", "达成率", "说明"],
      [("MuJoCo 平地 10 s", "0.51 m/s", "0.45 m/s", "88%", "存活全程，基高 0.364 m"),
       ("MuJoCo 教室 12 s", "0.509 m/s（6.1 m）", "0.443 m/s（5.31 m）", "87%", "课桌布局不构成阻碍"),
       ("40 N 推力", "存活", "存活（0.40 m/s）", "—", "速度降 11%，姿态稳定"),
       ("80 N 推力", "存活", "存活（0.23 m/s）", "—", "降 49% 但仍能行走"),
       ("摩擦 0.4–1.2", "—", "零跌倒", "—", "工具局限：本地摩擦注入未见差异，以 Isaac 侧数据为准")],
      col_w=[2.3, 2.5, 2.8, 1.1, 4.3], row_h=0.55, font_size=10.5)
add_rect(s, MARGIN, Inches(5.55), Inches(11.2), Inches(1.2), fill=TINT_SOFT)
add_text(s, MARGIN + Inches(0.2), Inches(5.68), Inches(10.8), Inches(1.0),
         [[("为什么这一步重要：", 12.5, PRIMARY_DK, True),
           ("Isaac 与 MuJoCo 是两套独立的物理引擎（接触求解、积分器都不同）。策略跨引擎零微调保持 87–88% 性能，"
            "说明学到的是运动能力本身，而不是拟合了某个引擎的物理特性——这正是 Sim2Real 需要验证的性质。", 12, MUTED, False)]],
         line_spacing=1.3)
notes(s, "约45秒：阶段六是跨引擎验证，也是最能说明问题的一步。我们在 Isaac 里训练，把策略导出成 TorchScript，"
         "拿到本地 MuJoCo 里零微调直接跑。结果：平地 0.45 米每秒、教室 0.443，都达到官方水平的 87 到 88%；"
         "加 40 牛推力还能走，80 牛速度掉一半但没摔。"
         "为什么重要：两个引擎的接触动力学完全不同，策略还能走，说明它学到的是运动能力，不是拟合某个引擎。"
         "最后一行是诚实披露：本地摩擦参数注入没观察到差异，所以摩擦结论以 Isaac 侧数据为准。")

# ============================== P10 误差追踪表 v1（核心交付）
s = new_slide()
page_title(s, "误差追踪表 v1", "Proposal Next Actions 第 7 条交付：Sim2Real 各环节误差来源与量化状态")
table(s, MARGIN, Inches(1.55), Inches(12.1),
      ["类别", "误差来源", "当前状态", "量化 / 证据"],
      [("动力学", "引擎差异（Isaac ↔ MuJoCo）", "✅ 已量化", "跨引擎 87–88%，接触求解器与积分器不同"),
       ("场景", "点云数据边界（无桌椅几何）", "✅ 已量化", "三轮统计：97% 点集中于原点、桌面/桌腿层无结构"),
       ("地形/材质", "地面摩擦变化", "✅ 已量化", "Isaac 侧 0.4 / 0.8 / 1.2 三档零跌倒"),
       ("扰动", "外部推力", "✅ 已量化", "自训 40–80 N 边界；官方 80–120 N"),
       ("驱动器", "PD 增益误差（kp/kd）", "⬜ 待测", "计划：±20% / ±50% 缩放 → 行走退化曲线"),
       ("传感器", "IMU 噪声", "⬜ 待测", "计划：噪声注入 → 存活率/速度退化"),
       ("延迟", "控制与观测延迟", "⬜ 待测", "计划：延迟注入 → 退化曲线"),
       ("建模", "质量/质心参数误差", "⬜ 待测", "计划：参数扰动 → 敏感度分析")],
      col_w=[1.5, 3.8, 1.6, 6.2], row_h=0.5, font_size=10.5)
add_text(s, MARGIN, Inches(6.55), Inches(12.1), Inches(0.5),
         [[("说明：前四项已量化（本期完成）；后四项为下一步计划，对应六周计划的 W3–W4「误差量化」阶段。",
            11.5, MUTED, False)]])
notes(s, "约60秒：这一页是 Proposal Next Actions 第七条要求交付的误差追踪表初版。我们按 Sim2Real 的误差来源分四类加两个工程维度。"
         "已经量化的四项：引擎差异——跨引擎 87 到 88%；点云数据边界——三轮统计的结论；地面摩擦——三档零跌倒；外部推力——自训和官方各自的边界。"
         "还待测的四项：PD 增益误差、IMU 噪声、控制延迟、质量与质心参数误差。这四项都在仿真内可做，不需要真机，是下一步 W3 到 W4 的重点。"
         "这张表的价值在于：它把「Sim2Real 为什么会有差距」拆成了可逐项量化的清单，而不是笼统说一句「仿真和现实有差距」。")

# ============================== P11 问题、风险与下一步
s = new_slide()
page_title(s, "问题、风险与下一步", "已解决 / 待解决 / 依赖外部")
add_text(s, MARGIN, Inches(1.6), Inches(3.85), Inches(0.34),
         [[("已解决", 14, OK_GREEN, True)]])
for i, t in enumerate([
    "环境可复现：复原脚本 20–40 分钟重建全栈",
    "官方策略与自训策略双线验证通路",
    "跨引擎迁移可信（87–88%）",
    "26 项技术问题全部归档",
]):
    add_text(s, MARGIN, Inches(2.05) + i * Inches(0.62), Inches(3.8), Inches(0.55),
             [[("· " + t, 11.5, MUTED, False)]], line_spacing=1.2)
add_text(s, Inches(4.72), Inches(1.6), Inches(3.85), Inches(0.34),
         [[("待解决（本期可完成）", 14, ACCENT, True)]])
for i, t in enumerate([
    "域随机化对照实验（DR 开/关短程对比）",
    "误差量化四项：PD / IMU / 延迟 / 参数",
    "演示素材：Isaac 侧画面质量待提升",
    "系统化性能评测报告成稿",
]):
    add_text(s, Inches(4.72), Inches(2.05) + i * Inches(0.62), Inches(3.8), Inches(0.55),
             [[("· " + t, 11.5, MUTED, False)]], line_spacing=1.2)
add_text(s, Inches(8.82), Inches(1.6), Inches(3.9), Inches(0.34),
         [[("依赖外部条件", 14, PRIMARY_DK, True)]])
for i, t in enumerate([
    "真机 Mini Pi+ 与吊装保护架（向高擎申请中）",
    "真机部署需 RKNN 转换 + ROS2 推理",
    "场地时段与安全演练流程",
]):
    add_text(s, Inches(8.82), Inches(2.05) + i * Inches(0.62), Inches(3.85), Inches(0.55),
             [[("· " + t, 11.5, MUTED, False)]], line_spacing=1.2)
add_rect(s, MARGIN, Inches(4.75), Inches(12.1), Inches(1.85), fill=WHITE, shadow=True)
add_text(s, MARGIN + Inches(0.25), Inches(4.9), Inches(11.6), Inches(0.34),
         [[("下一步时间表", 13, PRIMARY_DK, True)]])
steps = [("本周内", "DR 对照 + 误差量化四项启动"), ("11 月上旬", "误差表 v2 + 评测报告成稿"),
         ("硬件到位后", "真机部署（STANDBY 安全模式先验）"), ("11/19", "期末演示")]
for i, (when, what) in enumerate(steps):
    x = MARGIN + Inches(0.25 + i * 2.95)
    add_text(s, x, Inches(5.3), Inches(2.8), Inches(0.32),
             [[(when, 12, ACCENT, True)]])
    add_text(s, x, Inches(5.65), Inches(2.8), Inches(0.75),
             [[(what, 11, MUTED, False)]], line_spacing=1.2)
notes(s, "约40秒：最后是问题清单。已经解决的四项，重点是环境可复现和双线验证通路。"
         "本期还要做的：域随机化对照实验、误差量化四项、以及 Isaac 侧演示画面质量。"
         "依赖外部的：真机申请中，需要硬件到位才能做真机部署。"
         "时间表：本周内做 DR 和误差量化，11 月上旬出误差表第二版和评测报告，硬件到位后做真机，最终 11 月 19 日期末演示。汇报完毕，谢谢老师。")

prs.save(OUT)
print("saved:", OUT, os.path.getsize(OUT) // 1024, "KB", "| slides:", len(prs.slides._sldIdLst))
