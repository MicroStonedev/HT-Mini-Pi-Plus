# -*- coding: utf-8 -*-
"""生成《项目掌握与面试备战计划》Word 文档（详细版）"""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.oxml.ns import qn

OUT = r"D:\zcodeproject\HT-Mini-Pi-Plus-Robot\docs\项目掌握与面试备战计划.docx"
ACCENT = RGBColor(0x1F, 0x4E, 0x79)
GREEN = RGBColor(0x2E, 0x75, 0x3B)


def set_font(run, size=10.5, bold=False, color=None):
    run.font.name = "Calibri"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = color


def para(doc, text, size=10.5, bold=False, color=None, indent=0):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.left_indent = Cm(indent)
    r = p.add_run(text)
    set_font(r, size, bold, color)
    return p


def code(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    r = p.add_run(text)
    r.font.name = "Consolas"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor(0x8B, 0x2F, 0x2F)
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

para(doc, "项目掌握与面试备战计划（七天精读 + 四档理论）", 16, True, ACCENT)
para(doc, "")
para(doc, "适用背景：具身智能/强化学习实习面试。项目素材：Mini Pi+ AMP 运控（Isaac 训练 + MuJoCo 验证）。")
para(doc, "掌握的三个验收标准（先定义终点）：", 11, True)
para(doc, "① 能画出全景图——从 checkpoint 到机器人走路，每个箭头说清是什么；", 10.5)
para(doc, "② 能追一条数据的一生——一次训练迭代里数字怎么流动；", 10.5)
para(doc, "③ 能改参数预测结果——动手改一个东西，猜对会发生什么。", 10.5)
para(doc, "每日固定动作：晚 21:30–21:45 复盘三问（写不出=当天没懂）。所有概念必须在项目里找到实物对照。", 10.5, True)

# ============ Day 1 ============
para(doc, "Day 1 · 全景图：把项目装进一张图里（1.5h）", 13, True, ACCENT)
para(doc, "任务 1（30min）：精读 play_log.py 主循环", 11, True)
code(doc, "文件：tools/play_log.py 第 260–285 行（仅 25 行）")
para(doc, "读懂四件事：① policy(obs) 这一行发生了什么；② command_generator 的三个数字是什么（x速度/y速度/转向速率）；"
          "③ env.step 返回的四个值各是什么；④ episode_length_buf 为什么能用来判断跌倒。", 10.5, indent=0.5)
para(doc, "任务 2（45min）：手画链路图（纸/画图软件均可）", 11, True)
para(doc, "8 个框、7 个箭头，每个框旁写一句话「它是什么、为什么需要」：", 10.5)
code(doc, "checkpoint(1.3MB神经网络) → 观测345维 → MLP(512/256/128) → 动作20维\n"
          "  → PD力矩控制 → 关节力矩 → 物理仿真(50Hz) → 奖励+下一帧观测 → 回到开头")
para(doc, "任务 3（15min）：自测两问", 11, True)
para(doc, "① 观测为什么是 345 维（里面装了什么）？② 动作为什么是 20 维（对应什么）？答不出就带着问题进 Day 2。", 10.5)
para(doc, "当日产出：全景图 v1（发助手批改）。", 10.5, True, GREEN)

# ============ Day 2 ============
para(doc, "Day 2 · 配置精读：观测、奖励、命令——最重要的一天（2h）", 13, True, ACCENT)
para(doc, "任务 1（60min）：pi_plus_amp_sym_cfg.py 逐段读", 11, True)
code(doc, "文件：云端 ~/Mini-Pi-Plus_AMP/legged_lab/envs/pi_plus/pi_plus_amp_sym_cfg.py\n"
          "（本地对照：third_party/Mini-Pi-Plus_AMP/ 同路径）")
para(doc, "按三个主题找答案：", 10.5, True)
para(doc, "观测：本体感受有哪些（关节位置/速度、姿态、速度估计）？命令占几维？历史帧几帧？", 10.5, indent=0.5)
para(doc, "奖励：找出 28 个分项里的 5 个核心——速度跟踪、姿态保持、关节限位、足部接触、动作变化率；"
          "每个分清楚是「任务项」（奖励做对事）还是「正则项」（惩罚坏习惯）", 10.5, indent=0.5)
para(doc, "命令：速度范围是多少？文件名里的 sym（对称性）体现在哪个配置？", 10.5, indent=0.5)
para(doc, "任务 2（30min）：对照 TensorBoard 的 Episode_Reward 28 条曲线，把每条曲线与配置文件里的一项对应起来", 11, True)
para(doc, "任务 3（30min）：自测三问", 11, True)
para(doc, "① 哪个奖励项鼓励前进？哪项惩罚能耗？② 如果把速度跟踪奖励权重调到 0，机器人会怎么走？"
          "③ 低摩擦消融里奖励反而最高（0.0883），猜测原因？", 10.5)
para(doc, "当日产出：奖励分项分类表（任务项/正则项两栏）。", 10.5, True, GREEN)

# ============ Day 3 ============
para(doc, "Day 3 · 训练迭代解剖：一次 iter 的五个阶段（2h）", 13, True, ACCENT)
para(doc, "任务 1（60min）：读 train.py 主流程 + rsl_rl 的 AmpOnPolicyRunner", 11, True)
code(doc, "云端 ~/Mini-Pi-Plus_AMP/legged_lab/scripts/train.py\n"
          "云端 ~/Mini-Pi-Plus_AMP/rsl_rl/rsl_rl/runners/ 下的 AMP runner")
para(doc, "梳理一次迭代的五个阶段并画出「iter 解剖图」：", 10.5)
para(doc, "① Rollout 采样（4096 环境 × 24 步 ≈ 10 万条转移）→ ② GAE 算优势 → ③ PPO 更新（clip 目标）"
          "→ ④ 价值网络回归 → ⑤ AMP 判别器更新（策略动作 vs 参考动作）", 10.5, indent=0.5)
para(doc, "任务 2（30min）：把五个阶段对应到 TensorBoard 五条曲线（surrogate/value_function/amp/entropy/learning_rate）", 11, True)
para(doc, "任务 3（30min）：自测三问", 11, True)
para(doc, "① 为什么先采样后更新（on-policy 的含义）？② 旧数据为什么不能复用？"
          "③ 判别器在 Loss/amp_policy_pred 和 amp_expert_pred 两条曲线上的「拉锯」说明了什么？", 10.5)
para(doc, "当日产出：一页 iter 解剖图。", 10.5, True, GREEN)

# ============ Day 4 ============
para(doc, "Day 4 · 动作到物理：从 20 个数字到关节力矩（1.5h）", 13, True, ACCENT)
para(doc, "任务 1（45min）：读本地 mujoco_pi_plus_walk.py 的 pd_control 函数与主循环 decimation 部分", 11, True)
code(doc, "文件：tools/mujoco_pi_plus_walk.py（搜 pd_control 和 decimation）")
para(doc, "搞清：动作是「位置目标」不是力矩本身；PD 公式 τ = Kp(目标角-当前角) − Kd·角速度；"
          "Kp/Kd 从模型哪里读；控制频率 50Hz 与物理仿真频率的关系（一个控制步内物理走几小步）。", 10.5)
para(doc, "任务 2（45min）：自测+画动作链路图", 11, True)
para(doc, "① 策略输出的是绝对角度还是增量？② decimation 存在的意义（策略看 50Hz 世界，物理要 200Hz 细节）？"
          "③ 为什么关节限位很重要（联系奖励里的 limit 项）？", 10.5)
para(doc, "当日产出：动作链路一页笔记（20维→缩放→PD→力矩→关节）。", 10.5, True, GREEN)

# ============ Day 5 ============
para(doc, "Day 5 · 动手实验日：预测→验证（3h，含等待）", 13, True, ACCENT)
para(doc, "实验规则：改之前先写下预测，跑完对照，错了找原因——对上=真懂，没对=找到知识洞。", 11, True)
para(doc, "实验 1（90min）：命令速度上限 1.2 → 0.3", 11, True)
code(doc, "云端改 pi_plus_amp_sym_cfg.py 命令 ranges 后：500 iter 短训（约 20 分钟）")
para(doc, "预测点：回合长度会更高还是更低？速度跟踪奖励占比变化？sim2sim 回放速度会变成多少？", 10.5, indent=0.5)
para(doc, "实验 2（90min）：任选一个正则项奖励权重 ×10", 11, True)
para(doc, "预测点：动作会变得保守/激进？回合长度受影响吗？TensorBoard 哪条曲线先变化？", 10.5, indent=0.5)
para(doc, "当日产出：实验记录表（预测/实际/差异原因三栏）。", 10.5, True, GREEN)

# ============ Day 6 ============
para(doc, "Day 6 · 重建考试：不看记录从零复原 + 费曼讲解（3h）", 13, True, ACCENT)
para(doc, "任务 1（90min）：云实例从零环境复原", 11, True)
para(doc, "不开聊天记录，只拿 tools/install_isaac_recovery.sh 当参考答案，独立把环境装到能跑回放。"
          "每卡壳一次记一个盲区（这就是你最真实的知识清单）。", 10.5)
para(doc, "任务 2（90min）：给赵胤泽完整讲 pipeline", 11, True)
para(doc, "从「为什么选 AMP」讲到「sim2sim 为什么有说服力」，40 分钟版。他听懂=你毕业；他问倒你的题记下来。", 10.5)
para(doc, "当日产出：盲区清单（次日逐个消灭）。", 10.5, True, GREEN)

# ============ Day 7 ============
para(doc, "Day 7 · 压力测试：模拟面试 + 错题本（2h）", 13, True, ACCENT)
para(doc, "对助手说「模拟面试」：四档各抽一题 + 一条五层为什么连问。结束后整理错题本与补强顺序。", 10.5)
para(doc, "当日产出：薄弱点清单 + 一周补强计划。", 10.5, True, GREEN)

# ============ 理论四档 ============
para(doc, "面试理论四档清单（与精读并行，每天 2h）", 13, True, ACCENT)
para(doc, "第一档·项目理论（必考，你有独家数据）", 11, True)
table(doc, ["知识点", "自测标准", "项目实物"], [
    ("PPO clip 目标", "白纸手推损失函数；说清 ε 裁剪为何防突变；与 TRPO 关系", "Loss/surrogate 曲线"),
    ("GAE 优势估计", "λ 的偏差-方差权衡；为何用优势不用原始回报", "rsl_rl 中的实现"),
    ("AMP 判别器", "与 GAN/BC/reward shaping 的区别；两条 pred 曲线拉锯的含义", "Loss/amp_* 双曲线"),
    ("Domain Randomization", "覆盖部署分布原理与代价", "C 组摩擦消融数据"),
    ("on vs off policy", "为何 locomotion 主流用 PPO", "4096 envs 采样吞吐"),
], [3.8, 6.2, 5.5])
para(doc, "第二档·Sim2Real 与机器人学（具身岗分水岭）", 11, True)
table(doc, ["知识点", "项目实物"], [
    ("sim2real gap 四分类（动力学/驱动器/延迟/传感）", "MuJoCo vs Isaac 双引擎实测差异"),
    ("PD 位控→力矩", "mujoco_pi_plus_walk.py 的 pd_control"),
    ("观测/动作空间设计 + 对称性先验", "345 维 obs、20 维 action、任务名 sym"),
    ("奖励设计配比（任务项+正则项）", "28 分项曲线全家福"),
], [7.5, 8.0])
para(doc, "第三档·工程技能（聊深度的弹药）", 11, True)
para(doc, "GPU 并行仿真原理（4096 环境为何单卡跑得动）；策略部署链路（checkpoint→TorchScript→推理，含 torch.jit 的坑）；"
          "Docker（W3-D9 做 Dockerfile 时顺手学）；三层备份+看门狗自动化体系（现成叙事）。", 10.5)
para(doc, "第四档·通用基础（笔试防翻车）", 11, True)
para(doc, "BN/LN 区别、Adam、过拟合对策；PyTorch autograd、no_grad vs inference_mode（训练代码里见过）；"
          "手写高频：PPO loss 的 PyTorch 实现、简化版 REINFORCE。", 10.5)

# ============ 软技能 ============
para(doc, "软技能：三条必须背熟的叙事线", 13, True, ACCENT)
para(doc, "① 一句话项目：基于 Isaac Sim 在 4096 并行环境自训 AMP 人形运控策略，sim2sim 跨引擎验证达官方基线 88%。", 10.5)
para(doc, "② 一个踩坑故事（STAR）：推荐 S3 资产那条——症状诡异（curl 通但引擎加载失败）、定位靠日志、修复优雅（本地化+改路径）。", 10.5)
para(doc, "③ 诚实边界：「复现与自训的边界在哪、差距多少、为什么」——答好这题比漂亮数字更加分。", 10.5)

# ============ 验收表 ============
para(doc, "每日验收打勾表", 13, True, ACCENT)
for line in [
    "Day 1 ☐ 读主循环25行 ☐ 全景图v1发批改",
    "Day 2 ☐ 奖励分类表 ☐ 曲线-配置对应完成",
    "Day 3 ☐ iter解剖图 ☐ 五阶段对应五曲线",
    "Day 4 ☐ 动作链路笔记 ☐ PD公式默写",
    "Day 5 ☐ 实验记录表（两组预测/实际/原因）",
    "Day 6 ☐ 从零复原成功 ☐ 队友讲解40分钟 ☐ 盲区清单",
    "Day 7 ☐ 模拟面试完成 ☐ 错题本+补强计划",
    "每日 ☐ 21:30 复盘三问（零缺席）",
]:
    para(doc, line, 10.5)

doc.save(OUT)
print("[ok] 已生成", OUT)
