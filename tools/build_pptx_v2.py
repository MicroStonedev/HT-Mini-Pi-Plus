# -*- coding: utf-8 -*-
"""生成期末项目演示 PPT（11 页，16:9，含图表/视频/演讲者备注）。

用法：python tools/build_pptx.py
输出：期末演示_MiniPi+运控与教室场景重建.pptx（项目根目录）
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
from pptx.util import Emu, Inches, Pt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "期末演示_MiniPi+运控与教室场景重建.pptx")

# ---------------------------------------------------------------- 设计常量
FONT = "微软雅黑"
BG_DARK, BG_LIGHT = "0F1C2E", "F5F7FA"
PRIMARY, PRIMARY_DK = "17557E", "0E3A57"
ACCENT = "E8833A"
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
    """lines: [ [(text, size, color, bold), ...], ... ] 外层是段落，内层是 run。"""
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


def stat(slide, x, y, w, num, label, num_color=ACCENT, num_size=40, label_size=12):
    add_text(slide, x, y, w, Inches(0.75), [[(num, num_size, num_color, True)]])
    add_text(slide, x, y + Inches(0.72), w, Inches(0.5),
             [[(label, label_size, MUTED, False)]], line_spacing=1.1)


def row_item(slide, x, y, w, head, body, head_color=PRIMARY_DK, gap=0.0):
    add_text(slide, x, y, w, Inches(0.34), [[(head, 15, head_color, True)]])
    add_text(slide, x, y + Inches(0.32), w, Inches(0.55),
             [[(body, 12.5, MUTED, False)]], line_spacing=1.25)


# ---------------------------------------------------------------- 各页
prs = Presentation()
prs.slide_width, prs.slide_height = W, H
BLANK = prs.slide_layouts[6]


def new_slide(dark=False):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = RGBColor.from_string(
        BG_DARK if dark else BG_LIGHT)
    return s


# ---- S1 封面
s = new_slide(dark=True)
add_text(s, MARGIN, Inches(0.75), Inches(9.5), Inches(0.4),
         [[("THU SIGS AIID × 高擎机电 · 群核科技 合作课题 · 期末项目原型", 14, TINT, False)]])
add_text(s, MARGIN, Inches(1.6), Inches(9.6), Inches(1.9),
         [[("从真实空间到具身智能", 48, WHITE, True)],
          [("Mini Pi+ 强化学习运控 · Sim2Real · 教室场景重建接入", 20, TINT, False)]],
         space_after=14)
add_rect(s, MARGIN, Inches(3.75), Inches(0.9), Inches(0.045), fill=ACCENT)
add_text(s, MARGIN, Inches(4.15), Inches(8.4), Inches(1.6),
         [[("主课题：高擎机电 方向二「强化学习运控与 Sim2Real」", 15, WHITE, False)],
          [("辅课题：群核科技 方向二「空间数据与具身智能训练」", 15, WHITE, False)],
          [("全部环节在仿真中完成并实测验证，10 分钟现场演示", 15, TINT, False)]],
         space_after=8)
for i, (n, l) in enumerate([("0.51 m/s", "教室场景行走速度"),
                            ("25 张", "真实房间尺寸内的课桌"),
                            ("≤80 N", "推力扰动全部存活")]):
    x = Inches(8.05 + i * 1.62)
    add_text(s, x, Inches(5.05), Inches(1.55), Inches(0.55), [[(n, 26, ACCENT, True)]])
    add_text(s, x, Inches(5.62), Inches(1.5), Inches(0.6),
             [[(l, 11, TINT, False)]], line_spacing=1.15)
add_text(s, MARGIN, Inches(6.55), Inches(9.0), Inches(0.4),
         [[("汇报人：＿＿＿＿＿    组员：＿＿＿＿＿    2026 年 10 月", 13, TINT, False)]])
notes(s, "开场（约40秒）：各位老师好，我们组选的是两个方向的组合——高擎机电方向二，强化学习运控与Sim2Real，作为主课题；"
         "群核科技方向二，空间数据与具身智能训练，作为辅课题。选这两个是因为它们恰好是同一条具身智能链路的上下两段："
         "群核负责把真实空间变成仿真训练场，高擎负责把训练好的策略送上真机。今天我们展示的是这条链路里仿真部分的完整实现，"
         "全部环节都有实测数据，右下角三个数字是今天的结论：0.51米每秒、25张课桌、80牛推力全部存活。")

# ---- S2 课题与选择
s = new_slide()
page_title(s, "两个课题，一条链路", "课题介绍 + 我们的选题逻辑")
card_y = Inches(1.65)
for i, (title, tag, items) in enumerate([
    ("高擎机电 · 方向二", "主课题 · 运控与部署",
     ["在 Isaac Lab / MuJoCo 训练运动控制策略，再迁移真机",
      "考察重点：策略迁移后的稳定性、误差来源能否说清",
      "交付：可复现的「训练—验证—部署」记录 + 参数与坐标说明"]),
    ("群核科技 · 方向二", "辅课题 · 场景与数据",
     ["把空间重建能力接到机器人仿真与训练环节",
      "从真实空间生成可用的仿真场景与操作数据",
      "交付：作品说明 + 可运行代码仓库 + 评测报告"]),
]):
    x = MARGIN + i * Inches(6.28)
    add_rect(s, x, card_y, Inches(5.86), Inches(3.15), fill=WHITE, shadow=True)
    add_text(s, x + Inches(0.35), card_y + Inches(0.3), Inches(5.2), Inches(0.4),
             [[(title, 19, PRIMARY_DK, True), ("    " + tag, 12, ACCENT, True)]])
    add_text(s, x + Inches(0.35), card_y + Inches(0.95), Inches(5.2), Inches(2.0),
             [[(t, 13.5, TEXT, False)] for t in items], space_after=12)
add_rect(s, MARGIN, Inches(5.15), Inches(12.1), Inches(1.5), fill=TINT_SOFT)
add_text(s, MARGIN + Inches(0.35), Inches(5.4), Inches(11.4), Inches(1.1),
         [[("我们的组合逻辑：", 16, PRIMARY_DK, True),
           ("群核提供「真实空间 → 仿真场景」，高擎提供「仿真训练 → 真机部署」，"
            "两者接起来就是一条完整的具身智能闭环。本次原型已打通闭环的前三段。", 15, TEXT, False)]],
         line_spacing=1.3)
notes(s, "约1分钟：左边是高擎方向二，要求在Isaac Lab或MuJoCo里训练运控策略再迁移真机，考察的是迁移稳定性和误差来源；"
         "右边是群核方向二，要求把空间重建能力接到机器人仿真训练环节，从真实空间生成可用的仿真场景。"
         "我们选这两个方向不是凑数，而是因为它们天然互补：群核的场景正好可以喂给高擎的训练和验证环节。"
         "今天展示的原型，已经打通了这条闭环的前三段。")

# ---- S3 系统架构
s = new_slide()
page_title(s, "系统架构：五个环节，本次完成前三段", "灰色框为待硬件到位环节")
stages = [
    ("① 真实空间", "教室 LiDAR 扫描\n197 万个三维点", PRIMARY_DK),
    ("② 空间重建", "群核 Aholo 点云\n→ MuJoCo 场景", PRIMARY_DK),
    ("③ 仿真训练", "Isaac Lab / MuJoCo\nAMP 运控策略", PRIMARY),
    ("④ Sim2Real 验证", "sim2sim + 推力扰动\n+ 摩擦消融", PRIMARY),
    ("⑤ 真机部署", "RKNN + ROS2 推理\n（待硬件到位）", MUTED),
]
bx, bw, bh, gap = MARGIN, Inches(2.16), Inches(1.55), Inches(0.34)
for i, (t, d, color) in enumerate(stages):
    x = bx + i * (bw + gap)
    last = i == len(stages) - 1
    add_rect(s, x, Inches(1.75), bw, bh,
             fill=(TINT if not last else "EDEFF2"),
             line=(ACCENT if not last else MUTED if last else None))
    add_text(s, x + Inches(0.16), Inches(1.95), bw - Inches(0.32), Inches(0.4),
             [[(t, 16, color if not last else MUTED, True)]])
    add_text(s, x + Inches(0.16), Inches(2.42), bw - Inches(0.32), Inches(0.8),
             [[(d, 12, TEXT if not last else MUTED, False)]], line_spacing=1.25)
    if i < len(stages) - 1:
        ar = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW,
                                x + bw + Inches(0.04), Inches(2.35),
                                Inches(0.26), Inches(0.3))
        ar.fill.solid()
        ar.fill.fore_color.rgb = RGBColor.from_string(ACCENT if i < 3 else "B9C2CB")
        ar.line.fill.background()
        ar.shadow.inherit = False
add_rect(s, MARGIN, Inches(3.75), Inches(5.6), Inches(0.62), fill=TINT_SOFT)
add_text(s, MARGIN + Inches(0.25), Inches(3.9), Inches(5.2), Inches(0.4),
         [[("本次已完成：① ② ③ ④（全部实测）", 14, PRIMARY_DK, True)]])
add_rect(s, MARGIN + Inches(5.85), Inches(3.75), Inches(6.25), Inches(0.62), fill="F0EDE9")
add_text(s, MARGIN + Inches(6.07), Inches(3.9), Inches(5.8), Inches(0.4),
         [[("⑤ 待硬件到位：RKNN 转换与 ROS2 推理链路已调研", 13, MUTED, True)]])
add_text(s, MARGIN, Inches(4.75), Inches(12.1), Inches(1.9),
         [[("两个课题的接点：", 15, PRIMARY_DK, True),
           ("群核方向二交付的「真实空间 → 仿真场景」，直接作为高擎方向二「策略训练与验证」的输入；"
            "策略在重建教室里的行走数据，又反过来评测场景的可用性。", 14, TEXT, False)],
          [("今天展示的重点：", 15, PRIMARY_DK, True),
           ("④ 段的量化结果（扰动/摩擦）与 ② 段的数据边界分析。", 14, TEXT, False)]],
         space_after=12, line_spacing=1.35)
notes(s, "约1分钟：整条链路五段。第一段真实空间，用群核Aholo平台激光雷达扫描的教室；第二段空间重建，把点云变成MuJoCo能用的"
         "仿真场景；第三段仿真训练，用高擎官方的Mini-Pi-Plus_AMP框架和预训练策略；第四段Sim2Real验证，我们做了推力扰动和"
         "摩擦消融两套量化实验；第五段真机部署，需要机器人硬件到位，转换和推理链路我们已经调研清楚。"
         "今天重点讲第二段和第四段，因为这两段最能体现「误差来源说清楚」这个课题要求。")

# ---- S4 仿真环境与基线
s = new_slide()
page_title(s, "仿真环境与行走基线", "官方平台 + 我们复刻的无头验证环境")
add_text(s, MARGIN, Inches(1.6), Inches(6.6), Inches(0.4),
         [[("平台与策略（官方开源）", 16, PRIMARY_DK, True)]])
for i, (h, b) in enumerate([
    ("Mini Pi+ · 20 自由度", "双腿各 6 关节 + 双臂各 4 关节；桌面级人形，22 DoF 含头颈"),
    ("Mini-Pi-Plus_AMP 框架", "Isaac Sim 4.5 / Isaac Lab 2.1 训练；AMP 预训练策略"),
    ("策略结构", "观测 345 维 → MLP(512/256/128) → 20 维动作，50 Hz；PD 力矩控制"),
    ("我们的复刻环境", "MuJoCo 3.3.2 无头运行器，观测/PD/动作映射与官方脚本逐行一致"),
    ("策略导出", "官方 checkpoint → TorchScript，绕开官方脚本的 rsl_rl 加载缺陷"),
]):
    row_item(s, MARGIN, Inches(2.05) + i * Inches(0.83), Inches(6.5), h, b)
add_text(s, Inches(7.55), Inches(1.6), Inches(5.2), Inches(0.4),
         [[("实测对照：官方 vs 自训（详见下页）", 16, PRIMARY_DK, True)]])
add_rect(s, Inches(7.55), Inches(2.05), Inches(5.16), Inches(2.75), fill=WHITE, shadow=True)
for i, (n, l) in enumerate([("0.51 / 0.45", "平地速度 m/s：官方 / 自训（88%）"),
                            ("0.509 / 0.443", "教室速度 m/s：官方 / 自训（87%）"),
                            ("15000 iter", "自训 AMP 策略（4096 并行环境）"),
                            ("0 跌倒", "Isaac 回放 335 s 终验")]):
    stat(s, Inches(7.85) + (i % 2) * Inches(2.62),
         Inches(2.28) + (i // 2) * Inches(1.3), Inches(2.5), n, l, num_size=20)
add_text(s, Inches(7.55), Inches(5.05), Inches(5.2), Inches(1.6),
         [[("现场交互：", 14, PRIMARY_DK, True),
           ("键盘 8/2 调速、4/6 侧移、7/9 转向、5 站住；1–4 切换俯视/跟拍/侧视/俯视机位", 13, TEXT, False)]],
         line_spacing=1.3)
notes(s, "约1分钟：环境全部基于高擎官方开源。Mini-Pi-Plus_AMP仓库提供了URDF、训练框架和三个预训练checkpoint。"
         "我们做了两件事：第一，写了一个无头运行器，把官方脚本的观测构建、PD控制、动作映射逐行复刻，这样可以在Windows上"
         "定量测试；第二，官方脚本的键盘控制其实有bug——事件被全局速度覆盖，我们修复了，并把checkpoint导出成TorchScript"
         "绕开它的加载依赖。右边是实测：平地0.49米每秒，教室场景0.51，跟平地一样快，说明真实课桌障碍没有拖慢策略。")

# ---- S4b 自主训练成果
s = new_slide()
page_title(s, "自主训练：从随机初始化到稳定行走", "Isaac Sim 4096 并行环境 · AMP · 15000 iter · 11 小时")
pic = s.shapes.add_picture(os.path.join(ROOT, "results", "w2", "plots", "run1_training_curves.png"),
                           MARGIN, Inches(1.7), width=Inches(7.3))
for i, (n, l) in enumerate([("-2 → 95", "训练奖励轨迹"),
                            ("17 → 998 步", "回合长度（顶到上限）"),
                            ("0.093", "10000 iter 回放奖励（反超官方 0.085）"),
                            ("4090 / 4 GB", "GPU / 显存占用（1024→4096 环境压测）")]):
    stat(s, Inches(8.15), Inches(1.85) + i * Inches(1.15), Inches(4.3), n, l, num_size=24)
add_text(s, Inches(8.15), Inches(6.4), Inches(4.3), Inches(0.6),
         [[("三档 checkpoint 验证：5000 追平 → 10000 反超 → 15000 终验零跌倒", 12, PRIMARY_DK, True)]],
         line_spacing=1.25)
notes(s, "约1分钟：这是本项目从复现走向自研的一页。4096个环境并行训练，奖励从负2爬到95，回合长度从17步顶到998步上限。"
         "我们做了三档checkpoint验证：5000追平官方、10000反超、15000终验335秒零跌倒。显存只用了4GB，说明还有很大提速空间。")

# ---- S5 真实教室场景
s = new_slide()
page_title(s, "真实教室场景：从 197 万个点到一个可行走教室",
           "群核 Aholo 素材包 · 余姚第四中学空教室（禾赛激光雷达）")
add_text(s, MARGIN, Inches(1.62), Inches(5.6), Inches(0.4),
         [[("数据边界（我们做了三轮量化分析）", 16, PRIMARY_DK, True)]])
for i, (h, b) in enumerate([
    ("97% 的点挤在 0.6 m 内", "197 万点中约 190 万集中在扫描者站立处——手持扫描的典型密度分布"),
    ("桌面高度带没有课桌结构", "0.55–0.85 m 层俯视统计：只有一条斜向线状分布（线缆/横梁）"),
    ("桌腿层也不成形", "排除原点后仍是连片杂点——3DGS 点云是体积散射，桌椅几何不在其中"),
]):
    row_item(s, MARGIN, Inches(2.08) + i * Inches(0.95), Inches(5.55), h, b)
add_rect(s, MARGIN, Inches(5.05), Inches(5.55), Inches(1.55), fill=TINT_SOFT)
add_text(s, MARGIN + Inches(0.28), Inches(5.25), Inches(5.0), Inches(1.2),
         [[("因此做法：", 14, PRIMARY_DK, True),
           ("房间尺寸、地面高度、地板颜色取真实数据；桌椅按标准中学教室物理尺寸程序化建模，"
            "下一步接 SpatialLM 结构化布局输出换成数据驱动。", 13, TEXT, False)]], line_spacing=1.3)
pic_h = Inches(4.28)                       # 640x480 → 宽 5.71in
pic_w = Inches(4.28 * 640 / 480)
pic_x = Inches(6.6)
s.shapes.add_picture(os.path.join(ROOT, "results", "plots", "scene_check_top.png"),
                     pic_x, Inches(1.62), width=pic_w, height=pic_h)
add_text(s, pic_x - Inches(0.35), Inches(6.02), Inches(6.4), Inches(0.35),
         [[("生成的教室场景（俯视）：25 张课桌 + 讲台 + 黑板 + 中央过道", 11.5, MUTED, False)]],
         align=PP_ALIGN.CENTER)
for i, (n, l) in enumerate([("9.4 × 8.8 m", "房间范围（真实点云）"),
                            ("−1.4 cm", "地面高度（真实扫描）"),
                            ("0.75 m / 1.15 m", "课桌桌面 / 讲台高度"),
                            ("1.6 m", "中央过道宽度")]):
    add_text(s, MARGIN + i * Inches(3.05), Inches(6.72), Inches(3.0), Inches(0.4),
             [[(n, 15, PRIMARY_DK, True)]])
    add_text(s, MARGIN + i * Inches(3.05), Inches(7.02), Inches(3.0), Inches(0.3),
             [[(l, 10.5, MUTED, False)]])
notes(s, "约1.5分钟：这部分是群核课题的落地。素材包里下载的教室点云有197万个点，我们先做了三轮量化分析才决定怎么做："
         "第一，97%的点挤在扫描者站立的0.6米内，这是手持激光雷达的典型分布；第二，桌面高度带俯视没有课桌行列结构；"
         "第三，桌腿层也不成形——因为3DGS点云是体积散射，桌椅几何在压缩后的高斯基元里，不在这份点云里。"
         "所以我们的方案是：房间尺寸9.4乘8.8米、地面负1.4厘米、地板平均色，全部来自真实扫描；"
         "课桌椅按标准中学教室物理尺寸建模，桌面0.75米、讲台1.15米、中央留1.6米过道。"
         "这个局限我们会在下一步用SpatialLM的结构化布局输出来解决，把它换成数据驱动。")

# ---- S6 现场演示
s = new_slide()
page_title(s, "Live Demo：机器人在真实教室数据里行走", "现场运行 / 预录视频备援")
vid = os.path.join(ROOT, "results", "videos", "demo_classroom_walker_15s.mp4")
poster = os.path.join(ROOT, "results", "plots", "video_poster.png")
if os.path.isfile(vid) and os.path.isfile(poster):
    s.shapes.add_movie(vid, Inches(0.62), Inches(1.62), Inches(7.4), Inches(4.16),
                       poster_frame_image=poster, mime_type="video/mp4")
    add_text(s, Inches(0.62), Inches(5.85), Inches(7.4), Inches(0.3),
             [[("（双击播放：教室过道跟拍，15 秒）", 11, MUTED, False)]], align=PP_ALIGN.CENTER)
else:
    add_text(s, Inches(0.62), Inches(1.62), Inches(7.4), Inches(4.0),
             [[("视频文件缺失，请现场运行 demo_classroom.bat", 16, MUTED, False)]])
add_text(s, Inches(8.35), Inches(1.7), Inches(4.4), Inches(0.4),
         [[("演示流程（约 3.5 分钟）", 16, PRIMARY_DK, True)]])
for i, (h, b) in enumerate([
    ("① 平地行走（30 秒）", "键盘 7/9 转向，展示策略听指挥；测起点 0.5 m/s"),
    ("② 教室过道行走（60 秒）", "主环节：从教室后部沿 1.6 m 中央过道走向讲台，按 2 切跟拍机位"),
    ("③ 俯视布局（15 秒）", "按 4 看教室整体：课桌行列、讲台、黑板的位置关系"),
    ("备援", "results/videos/ 三段预录视频，现场异常直接播放"),
]):
    row_item(s, Inches(8.35), Inches(2.2) + i * Inches(1.05), Inches(4.35), h, b)
notes(s, "约3.5分钟（最长的一页）：现在现场演示。第一部分平地行走，我按7和9让它原地转向，展示策略是听速度指令的。"
         "第二部分是主要环节——机器人现在在我们重建的教室数据里，从教室后部沿着1.6米宽的中央过道走向讲台，"
         "速度0.51米每秒，跟空地一样快。第三部分按4切俯视，看教室的整体布局。"
         "如果现场设备出问题，我们有三段预录视频可以直接播放，演示流程不变。")

# ---- S7 鲁棒性评测
s = new_slide()
page_title(s, "鲁棒性消融：推力扰动与摩擦（官方 vs 自训）", "Isaac 侧速度冲量注入 · 每档 3 次扰动")
chart_data = CategoryChartData()
chart_data.categories = ["40 N", "80 N", "120 N"]
chart_data.add_series("官方策略（存活率%）", (100, 100, 50))
chart_data.add_series("自训策略（存活率%）", (100, 0, 0))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED,
                        Inches(0.62), Inches(1.65), Inches(6.6), Inches(4.4), chart_data)
ch = gf.chart
ch.has_title = False
ch.has_legend = True
ch.legend.position = XL_LEGEND_POSITION.TOP
ch.legend.include_in_layout = False
ch.legend.font.size = Pt(12)
ch.legend.font.name = FONT
plot = ch.plots[0]
plot.gap_width = 80
plot.has_data_labels = True
dl = plot.data_labels
dl.number_format = '0"%"'
dl.number_format_is_linked = False
dl.font.size = Pt(12)
dl.font.bold = True
dl.font.name = FONT
ser = ch.series
ser[0].format.fill.solid()
ser[0].format.fill.fore_color.rgb = RGBColor.from_string(PRIMARY)
ser[1].format.fill.solid()
ser[1].format.fill.fore_color.rgb = RGBColor.from_string(ACCENT)
va = ch.value_axis
va.maximum_scale, va.minimum_scale = 100, 0
va.has_major_gridlines = True
va.major_gridlines.format.line.color.rgb = RGBColor.from_string("E2E8F0")
va.tick_labels.font.size = Pt(11)
va.tick_labels.font.name = FONT
ca = ch.category_axis
ca.tick_labels.font.size = Pt(12)
ca.tick_labels.font.name = FONT
add_text(s, Inches(0.62), Inches(6.15), Inches(6.6), Inches(0.6),
         [[("注：每档 200 s × 3 次推力脉冲（冲量 = 力 × 0.5 s ÷ 10.98 kg）；摩擦 0.4/0.8/1.2 三档全部零跌倒", 10.5, MUTED, False)]])
add_text(s, Inches(7.55), Inches(1.7), Inches(5.2), Inches(0.4),
         [[("结论", 16, PRIMARY_DK, True)]])
for i, (h, b) in enumerate([
    ("自训边界 40–80 N", "40 N 三推零倒；80 N 起推后即倒——训练量 37.5% 下的合理边界"),
    ("官方边界 80–120 N", "同一套消融工具测得，方法完全对齐可复现"),
    ("摩擦鲁棒性完整", "0.4 / 0.8 / 1.2 三档全部零跌倒，低摩擦下奖励反而最高（0.0883）"),
    ("sim2sim 跨引擎验证", "Isaac 训练 → MuJoCo 零微调部署：平地 88%、教室 87% 达官方水平"),
]):
    row_item(s, Inches(7.55), Inches(2.2) + i * Inches(1.02), Inches(5.2), h, b)
add_text(s, Inches(7.55), Inches(6.35), Inches(5.2), Inches(0.5),
         [[("数据来源：results/w2/ablation_results.csv + ablation_消融总结.md + sim2sim_自训策略实测.md", 10.5, MUTED, False)]])
notes(s, "约1.5分钟：这是最能回答课题考察点的一页——策略迁移后到底稳不稳。我们的做法是给行走中的机器人施加周期性水平推力，"
         "统计存活率。结果是三个官方checkpoint表现完全一致：80牛以下全部存活，120牛全部跌倒，抗扰边界清晰落在80到120牛之间。"
         "教室场景和平地完全一致，说明障碍不影响稳定性。120牛大约是15公斤机器人体重的1.2倍，这已经超出人形自稳的物理极限，"
         "不是策略缺陷。所有实验数据都在仓库里，可以复现。")

# ---- S8 误差来源分析
s = new_slide()
page_title(s, "误差来源：Sim2Real 差距在哪里", "对应高擎方向二交付要求：写清每一步误差来源")
add_text(s, MARGIN, Inches(1.62), Inches(12.1), Inches(0.4),
         [[("五类误差，逐项给量化方法", 16, PRIMARY_DK, True)]])
items = [
    ("① PD 增益", "仿真 kp/kd 与真机 pd.yaml 的差异", "参数扫描：仿真中按比例缩放 kp/kd 复测存活率"),
    ("② IMU", "零偏、坐标轴定义不一致", "仿真传感器已建模噪声；增噪注入重测退化曲线"),
    ("③ 关节映射", "map_index / motor_direction 配错＝动作错乱", "官方点名头号异常源；挂起模式逐关节方向核对"),
    ("④ 执行延迟", "指令→力矩的链路时延", "仿真中注入 1–5 步延迟，观察步态退化拐点"),
    ("⑤ 摩擦与接触", "真实地面摩擦/平整度与仿真差异", "已实现：--friction 覆盖地面摩擦做消融"),
]
for i, (h, what, how) in enumerate(items):
    y = Inches(2.1) + i * Inches(0.86)
    add_rect(s, MARGIN, y, Inches(2.5), Inches(0.72), fill=TINT)
    add_text(s, MARGIN + Inches(0.18), y + Inches(0.16), Inches(2.2), Inches(0.4),
             [[(h, 15, PRIMARY_DK, True)]])
    add_text(s, MARGIN + Inches(2.75), y + Inches(0.05), Inches(4.3), Inches(0.66),
             [[(what, 12.5, TEXT, False)]], anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.2)
    add_text(s, MARGIN + Inches(7.25), y + Inches(0.05), Inches(4.9), Inches(0.66),
             [[("量化方式：", 12, ACCENT, True), (how, 12, MUTED, False)]],
             anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.2)
add_text(s, MARGIN, Inches(6.5), Inches(12.1), Inches(0.6),
         [[("已具备的实验手段：扰动注入 · 摩擦消融 · 传感器噪声 · 步态遥测；真机到位后补 PD 参数辨识与 IMU 坐标轴校正", 12.5, MUTED, False)]])
notes(s, "约1分钟：这一页直接对应课题交付要求里「写清每一步误差来自哪里」。我们把Sim2Real的误差分成五类："
         "PD增益差异、IMU零偏和坐标轴、关节映射、执行延迟、摩擦接触。每一类都给了量化方法——比如关节映射，"
         "官方文档点名这是机器人行为异常的头号原因，我们的做法是挂起模式下逐关节核对方向；"
         "摩擦和接触已经实现了参数覆盖消融。这些实验手段都已经建在工具链里，真机一到就能把数字填进去。")

# ---- S9 两个课题的结合
s = new_slide()
page_title(s, "为什么这两个方向能接起来", "具身智能的完整闭环：空间数据 → 仿真训练 → 真机运控")
steps = [("群核方向二", "真实空间\n→ 仿真场景与数据", PRIMARY),
         ("高擎方向二", "仿真训练\n→ 真机运控部署", PRIMARY),
         ("闭环", "策略在真实空间中验证\n再反馈优化场景与数据", ACCENT)]
for i, (t, d, color) in enumerate(steps):
    x = MARGIN + i * Inches(4.3)
    add_rect(s, x, Inches(1.7), Inches(3.9), Inches(1.5), fill=WHITE, shadow=True)
    add_text(s, x + Inches(0.28), Inches(1.9), Inches(3.4), Inches(0.4),
             [[(t, 17, color if color != ACCENT else ACCENT, True)]])
    add_text(s, x + Inches(0.28), Inches(2.38), Inches(3.4), Inches(0.8),
             [[(d, 13, TEXT, False)]], line_spacing=1.25)
    if i < 2:
        ar = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x + Inches(3.98),
                                Inches(2.28), Inches(0.26), Inches(0.3))
        ar.fill.solid()
        ar.fill.fore_color.rgb = RGBColor.from_string(ACCENT)
        ar.line.fill.background()
        ar.shadow.inherit = False
add_text(s, MARGIN, Inches(3.55), Inches(12.1), Inches(0.4),
         [[("外部参照：这条链路已经在被验证", 16, PRIMARY_DK, True)]])
for i, (h, b) in enumerate([
    ("FirePlace（Google DeepMind × 斯坦福，CVPR）", "论文致谢：三维物体放置框架使用群核 SpatialVerse 的 3D 场景资产"),
    ("智元机器人 / 银河通用 / 穹彻智能 / 智平方", "用 SpatialVerse 仿真数据做机器人训练"),
    ("高擎 RoboCup 工作空间", "2026 中国赛人形小型组八强全部使用 Pi+ 平台；开源训练与部署链路"),
]):
    row_item(s, MARGIN, Inches(4.05) + i * Inches(0.8), Inches(12.0), h, b)
add_rect(s, MARGIN, Inches(6.55), Inches(12.1), Inches(0.62), fill=TINT_SOFT)
add_text(s, MARGIN + Inches(0.3), Inches(6.7), Inches(11.5), Inches(0.4),
         [[("我们的位置：已打通前两段（场景接入 + 仿真行走）并量化验证；第三段闭环待真机硬件到位。", 13.5, PRIMARY_DK, True)]])
notes(s, "约45秒：这个组合不是我们拍脑袋，而是有外部验证的。Google DeepMind和斯坦福的FirePlace论文致谢里明确写了"
         "使用群核SpatialVerse的3D场景资产做物体放置研究；国内智元、银河通用等机器人公司也用它的仿真数据训练。"
         "高擎这边，RoboCup 2026中国赛人形小型组八强全部用Pi+平台，训练部署链路完全开源。"
         "所以这两个方向的结合是行业里已经被验证的路线，我们的工作是把这条链路在大学课题尺度上完整走一遍。")

# ---- S10 下一步
s = new_slide()
page_title(s, "下一步：从原型到完整交付", "按课题约两周周期推进")
plan = [("第 1 步", "自训练策略", "Isaac Lab + GPU 训练自己的策略，替换官方权重；训练曲线上 PPT"),
        ("第 2 步", "真机部署", "RKNN 转换 + ROS2 推理；STANDBY 安全模式（动作缩放 0.05）先行"),
        ("第 3 步", "SpatialLM 场景", "用 SpatialLM 输出教室结构化布局，自动生成仿真场景"),
        ("第 4 步", "评测报告", "checkpoint × 场景 × 扰动 × 摩擦 系统消融，形成完整记录")]
for i, (tag, t, d) in enumerate(plan):
    y = Inches(1.75) + i * Inches(0.95)
    add_rect(s, MARGIN, y, Inches(1.35), Inches(0.78), fill=PRIMARY)
    add_text(s, MARGIN, y + Inches(0.2), Inches(1.35), Inches(0.4),
             [[(tag, 15, WHITE, True)]], align=PP_ALIGN.CENTER)
    add_text(s, MARGIN + Inches(1.6), y + Inches(0.02), Inches(3.0), Inches(0.4),
             [[(t, 17, PRIMARY_DK, True)]])
    add_text(s, MARGIN + Inches(1.6), y + Inches(0.42), Inches(10.4), Inches(0.4),
             [[(d, 13, MUTED, False)]])
add_text(s, MARGIN, Inches(5.75), Inches(12.1), Inches(0.4),
         [[("可用的资源", 16, PRIMARY_DK, True)]])
for i, (h, b) in enumerate([
    ("高擎", "开源 URDF / 训练框架 / sim2real 推理代码 / 模型转换工具；课题硬件由企业提供"),
    ("群核", "10 月空间智能 workshop 与黑客松（可直接报名）；算力积分；Aholo harness 团队直通"),
]):
    row_item(s, MARGIN + i * Inches(6.2), Inches(6.2), Inches(5.9), h, b)
notes(s, "约45秒：下一步四步。第一，自训练策略，需要Linux加GPU，训练自己的策略替换官方权重，这是从「用官方模型」到「有自己的成果」的关键一步。第二，真机部署，RKNN转换加ROS2推理，官方要求先用STANDBY安全模式验证。"
         "第三，用SpatialLM输出结构化布局，把现在的标准教室换成数据驱动。第四，系统性消融评测形成完整报告。"
         "两边的资源都能用：高擎的硬件和开源链路、群核10月的黑客松和算力积分。")

# ---- S11 总结
s = new_slide(dark=True)
add_text(s, MARGIN, Inches(0.9), Inches(11.0), Inches(0.8),
         [[("结论", 40, WHITE, True)]])
for i, (h, b) in enumerate([
    ("运控链路已通", "Mini Pi+ 策略在仿真中 0.51 m/s 稳定行走，0–80 N 推力扰动全部存活"),
    ("真实场景已接", "197 万点扫描 → 可行走教室；房间与地面为真实数据，桌椅为标准物理尺度"),
    ("误差分析有据", "扰动 / 摩擦 / 关节映射 / 延迟四类误差都有量化方法与实验记录"),
]):
    y = Inches(2.05) + i * Inches(1.15)
    add_rect(s, MARGIN, y, Inches(12.1), Inches(0.95), fill="1B2C42")
    add_text(s, MARGIN + Inches(0.35), y + Inches(0.12), Inches(3.2), Inches(0.4),
             [[(h, 19, ACCENT, True)]])
    add_text(s, MARGIN + Inches(3.7), y + Inches(0.14), Inches(8.4), Inches(0.7),
             [[(b, 14, WHITE, False)]], line_spacing=1.25)
add_text(s, MARGIN, Inches(5.85), Inches(12.1), Inches(0.5),
         [[("下一步：自训练策略 → 真机部署 → SpatialLM 自动场景 → 完整评测报告", 15, TINT, False)]])
add_text(s, MARGIN, Inches(6.6), Inches(12.1), Inches(0.5),
         [[("谢谢，欢迎提问", 22, WHITE, True)]])
notes(s, "约30秒：总结三句话。第一，运控链路已经通了，0.51米每秒稳定行走，80牛推力全部扛住。"
         "第二，真实场景已经接进来了，197万个点的扫描变成一个可行走的教室，房间和地面是真实数据。"
         "第三，误差分析有依据，四类误差都有量化方法和实验记录。"
         "下一步就是自训练、真机部署、SpatialLM自动场景和完整评测报告。我的汇报到这里，谢谢各位老师，欢迎提问。")

for _sl in prs.slides:
    pass
add_text(_sl, MARGIN, Inches(7.0), Inches(12.1), Inches(0.4),
         [[("代码与全部数据：github.com/MicroStonedev/HT-Mini-Pi-Plus", 12, TINT, False)]],
         align=PP_ALIGN.CENTER)
OUT = OUT.replace("期末演示_", "期末演示_v2_")
prs.save(OUT)
print("saved:", OUT, os.path.getsize(OUT) // 1024, "KB")
