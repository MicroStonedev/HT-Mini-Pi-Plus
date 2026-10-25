# -*- coding: utf-8 -*-
"""生成《学习资料清单》Word 文档（详细版）"""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.oxml.ns import qn

OUT = r"D:\zcodeproject\HT-Mini-Pi-Plus-Robot\docs\学习资料清单.docx"
ACCENT = RGBColor(0x1F, 0x4E, 0x79)
GREEN = RGBColor(0x2E, 0x75, 0x3B)
ORANGE = RGBColor(0xC5, 0x50, 0x0B)


def set_font(run, size=10.5, bold=False, color=None):
    run.font.name = "Calibri"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = color


def para(doc, text, size=10.5, bold=False, color=None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    set_font(r, size, bold, color)
    return p


def table(doc, headers, rows, widths=None):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    for j, h in enumerate(headers):
        c = t.rows[0].cells[j]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        set_font(r, 10, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
        shd = c._tc.get_or_add_tcPr()
        shd.append(shd.makeelement(qn("w:shd"), {qn("w:val"): "clear", qn("w:fill"): "1F4E79"}))
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

para(doc, "学习资料清单（配合七天精读与面试备战计划）", 16, True, ACCENT)
para(doc, "")
para(doc, "使用总则：资料服务于计划而非反过来——只按「配合哪天」的节奏看；视频 1.5 倍速且只看标注集数；"
          "论文只读方法部分；每份资料看完必须回到项目实物上验证（曲线/日志/代码）。", 10.5, True)
para(doc, "时间预算：第一优先约 6h ｜ 第二优先约 4h ｜ 第三优先约 3h ｜ 第四优先不限。两周内只需消化前三档。", 10.5, True, ORANGE)

# ============ 第一优先 ============
para(doc, "第一优先 · 直接配合七天精读（必看，约 6h）", 13, True, ACCENT)

para(doc, "1.1 李宏毅《深度强化学习》课程", 11, True)
table(doc, ["项", "内容"], [
    ("形式/语言", "B 站中文视频（搜「李宏毅 强化学习」）"),
    ("看什么", "Policy Gradient → PPO 相关的 3 集（每集约 40 分钟，共约 2h）"),
    ("配合哪天", "Day 3（训练迭代解剖）——读 rsl_rl 代码前看，等于先拿地图再进森林"),
    ("看完的验收", "能白纸手推 PPO clip 损失函数；能说清 ε 裁剪防的是什么"),
    ("为什么选它", "中文授课里 Policy 系列讲得最清楚的公开课，配图直观"),
], [3.2, 12.3])

para(doc, "1.2 OpenAI Spinning Up", 11, True)
table(doc, ["项", "内容"], [
    ("形式/语言", "英文网页 spinningup.openai.com（浏览器翻译插件辅助）"),
    ("看什么", "「Key Concepts in RL」全篇 + 「Algorithms: PPO」页（约 1.5h）"),
    ("配合哪天", "Day 3 与 Day 5——Day 5 动手改参数前把 PPO 页再看一遍"),
    ("看完的验收", "能解释 GAE 的 λ 权衡；能对照它的伪代码读懂 rsl_rl 的 update 循环"),
    ("为什么选它", "业界公认的深度 RL 标准入门，伪代码与工程实现一一对应"),
], [3.2, 12.3])

para(doc, "1.3 rsl_rl 源码（项目自带，最好的 AMP 教材）", 11, True)
table(doc, ["项", "内容"], [
    ("位置", "云端 ~/Mini-Pi-Plus_AMP/rsl_rl/rsl_rl/（本地 third_party 同路径）"),
    ("读什么", "runners/ 下 AMP runner 的 learn() 与 update() 两个函数（约 300 行）"),
    ("配合哪天", "Day 3 全程——对照 AMP 论文方法部分逐段读"),
    ("读完的验收", "说清一次 iter 里采样、GAE、PPO 更新、判别器更新四个阶段的代码位置"),
], [3.2, 12.3])

para(doc, "1.4 AMP 论文（Peng et al. 2021, Adversarial Motion Priors）", 11, True)
table(doc, ["项", "内容"], [
    ("形式", "英文 PDF（arXiv 搜 Adversarial Motion Priors）"),
    ("看什么", "只读方法部分 3–4 页 + 图 1（判别器架构图）"),
    ("配合哪天", "Day 3 下午"),
    ("看完的验收", "能画出「参考动作 vs 策略动作 → 判别器打分 → 奖励」的数据流"),
    ("面试关联", "被问「AMP 和 BC/GAN 的区别」时直接用论文图 1 的语言回答"),
], [3.2, 12.3])

para(doc, "1.5 项目自有数据（面试差异化的根本）", 11, True)
table(doc, ["资料", "用在哪"], [
    ("TensorBoard 28 条 reward 分项曲线", "Day 2 曲线-配置对应练习"),
    ("消融数据 ablation_results.csv + ablation_BC.png", "第一档 DR 与鲁棒性问答的一手证据"),
    ("训练曲线 run1_training_curves.png", "「训练是否收敛怎么看」的标准答案素材"),
    ("16 条踩坑记录（W1/W2 周报内）", "工程能力叙事弹药库"),
], [7.0, 8.5])

# ============ 第二优先 ============
para(doc, "第二优先 · Isaac 与仿真（约 4h）", 13, True, ACCENT)
para(doc, "2.1 B站【组会分享】Isaac Lab 代码讲解（BV1iABcB9E3C）——Day 3 读码前预习，约 1h", 10.5)
para(doc, "2.2 Isaac Lab 中文文档（docs.robotsfan.com/isaaclab）——当字典查概念，不通读", 10.5)
para(doc, "2.3 论文 Learning to Walk in Minutes（Rudin et al.）——4 页短文，约 40 分钟："
          "大规模并行训练的出处，正是你 4096 envs 打法的理论源头，面试提到极加分", 10.5)
para(doc, "2.4 B站「Isaac Sim 入门」系列（界面操作）——配合流式练习 Session 1，约 1h", 10.5)
para(doc, "2.5 CSDN/知乎 IsaacLab 环境配置系列（如 zhuanlan.zhihu.com/p/708194148）——"
          "与你的复原脚本互为印证，看他人口径补充细节", 10.5)

# ============ 第三优先 ============
para(doc, "第三优先 · Sim2Real 与领域视野（约 3h）", 13, True, ACCENT)
para(doc, "3.1 DeepMimic（Peng et al. 2018）——AMP 前身。只看摘要+方法概览（30 分钟）："
          "讲清「模仿学习→对抗模仿」的演进线，等于讲清 AMP 的动机", 10.5)
para(doc, "3.2 Domain Randomization 开山文（Tobin et al. 2017）——短文（20 分钟）："
          "配合你的 C 组摩擦消融数据，形成「原理+实测」完整答案", 10.5)
para(doc, "3.3 宇树/Unitree 与高擎官方开源仓库——浏览 README 与 release（1h）："
          "面试聊「业界人形运控现状」的谈资；高擎仓库本身就是你项目的上游", 10.5)

# ============ 第四优先 ============
para(doc, "第四优先 · 补基础（有余力再啃，不限时）", 13, True, ACCENT)
para(doc, "4.1 《动手学深度学习》（李沐，中文免费在线 zh.d2l.ai）——查漏式阅读 BN/LN、Adam、过拟合三节；"
          "笔试基础兜底", 10.5)
para(doc, "4.2 李沐论文精读系列（B站）——仅当面试官聊 Transformer/大模型时兜底", 10.5)
para(doc, "4.3 牛客/知乎「强化学习面经」帖——考前一周刷，建立真题感；重点看 PPO/值函数/探索类高频题", 10.5)
para(doc, "4.4 Modern Robotics 前 3 章（Lynch & Park，英文）——仅面机器人岗时补旋转矩阵/正运动学", 10.5)

# ============ 使用纪律 ============
para(doc, "使用纪律（比清单本身重要）", 13, True, ACCENT)
for line in [
    "① 映射到天：只按「配合哪天」的节奏看，不开新战线；",
    "② 视频只看标注集数、1.5 倍速；论文只读方法部分；",
    "③ 每份资料看完，立刻回项目实物验证（看完 PPO 视频→白纸默写 clip→对照 Loss/surrogate 曲线）；",
    "④ 记录：每份资料在清单上打勾并写一行「学到的一个点」，周日汇总复盘。",
]:
    para(doc, line, 10.5)

# ============ 进度打勾 ============
para(doc, "资料消化进度表", 13, True, ACCENT)
table(doc, ["资料", "预计", "完成", "学到一个点"], [
    ("李宏毅 RL 课程（3集）", "2h", "☐", ""),
    ("Spinning Up PPO 页", "1.5h", "☐", ""),
    ("rsl_rl AMP runner 源码", "1.5h", "☐", ""),
    ("AMP 论文方法部分", "40min", "☐", ""),
    ("Isaac Lab 代码讲解视频", "1h", "☐", ""),
    ("Learning to Walk in Minutes", "40min", "☐", ""),
    ("DeepMimic 摘要+概览", "30min", "☐", ""),
    ("DR 开山文", "20min", "☐", ""),
    ("Isaac Sim 入门视频", "1h", "☐", ""),
    ("宇树/高擎仓库浏览", "1h", "☐", ""),
    ("动手学深度学习（三节）", "选读", "☐", ""),
    ("面经帖刷题", "考前", "☐", ""),
], [6.2, 2.0, 1.6, 5.7])

doc.save(OUT)
print("[ok] 已生成", OUT)
