#!/usr/bin/env python3
"""Build the Chinese reading companion for the AI4AI4Bio manuscript."""

from pathlib import Path

import fitz
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf" / "AI4AI4Bio_中文伴读版.pdf"
TMP = ROOT / "tmp" / "pdfs"

NAVY = colors.HexColor("#17365D")
BLUE = colors.HexColor("#376694")
TEAL = colors.HexColor("#167C6B")
GOLD = colors.HexColor("#A36A21")
INK = colors.HexColor("#1F2D3D")
MUTED = colors.HexColor("#61738A")
PALE_BLUE = colors.HexColor("#EEF4FA")
PALE_TEAL = colors.HexColor("#EAF6F2")
PALE_GOLD = colors.HexColor("#FFF5E8")
PALE_RED = colors.HexColor("#FBEDEF")
LINE = colors.HexColor("#CBD7E3")
WHITE = colors.white


pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
pdfmetrics.registerFontFamily(
    "STSong-Light",
    normal="STSong-Light",
    bold="STSong-Light",
    italic="STSong-Light",
    boldItalic="STSong-Light",
)


class CompanionDoc(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=17 * mm,
            rightMargin=17 * mm,
            topMargin=18 * mm,
            bottomMargin=17 * mm,
            title="AI4AI4Bio 中文伴读版",
            author="Anonymous",
            subject="AI4AI4Bio manuscript Chinese reading companion",
        )
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="normal",
        )
        self.addPageTemplates(PageTemplate(id="all", frames=[frame], onPage=self._page))

    @staticmethod
    def _page(canvas, doc):
        canvas.saveState()
        if doc.page > 1:
            canvas.setStrokeColor(LINE)
            canvas.setLineWidth(0.5)
            canvas.line(17 * mm, A4[1] - 12 * mm, A4[0] - 17 * mm, A4[1] - 12 * mm)
            canvas.setFont("STSong-Light", 8)
            canvas.setFillColor(MUTED)
            canvas.drawString(17 * mm, A4[1] - 9.5 * mm, "AI4AI4Bio 中文伴读版")
            canvas.drawRightString(A4[0] - 17 * mm, 9 * mm, str(doc.page))
        canvas.restoreState()


styles = {
    "cover_kicker": ParagraphStyle(
        "cover_kicker", fontName="STSong-Light", fontSize=12, leading=18,
        textColor=TEAL, alignment=TA_CENTER, spaceAfter=8,
    ),
    "cover_title": ParagraphStyle(
        "cover_title", fontName="STSong-Light", fontSize=28, leading=38,
        textColor=NAVY, alignment=TA_CENTER, spaceAfter=10,
    ),
    "cover_sub": ParagraphStyle(
        "cover_sub", fontName="STSong-Light", fontSize=14, leading=22,
        textColor=MUTED, alignment=TA_CENTER, spaceAfter=12,
    ),
    "h1": ParagraphStyle(
        "h1", fontName="STSong-Light", fontSize=20, leading=28,
        textColor=NAVY, spaceBefore=2, spaceAfter=12,
    ),
    "h2": ParagraphStyle(
        "h2", fontName="STSong-Light", fontSize=13, leading=20,
        textColor=BLUE, spaceBefore=8, spaceAfter=6,
    ),
    "h3": ParagraphStyle(
        "h3", fontName="STSong-Light", fontSize=10.5, leading=16,
        textColor=TEAL, spaceBefore=5, spaceAfter=3,
    ),
    "body": ParagraphStyle(
        "body", fontName="STSong-Light", fontSize=9.5, leading=15.5,
        textColor=INK, alignment=TA_LEFT, wordWrap="CJK", spaceAfter=6,
    ),
    "small": ParagraphStyle(
        "small", fontName="STSong-Light", fontSize=8.2, leading=13,
        textColor=INK, wordWrap="CJK", spaceAfter=3,
    ),
    "tiny": ParagraphStyle(
        "tiny", fontName="STSong-Light", fontSize=7.2, leading=10.8,
        textColor=INK, wordWrap="CJK",
    ),
    "note": ParagraphStyle(
        "note", fontName="STSong-Light", fontSize=8.7, leading=14,
        textColor=MUTED, wordWrap="CJK",
    ),
    "center": ParagraphStyle(
        "center", fontName="STSong-Light", fontSize=9, leading=14,
        textColor=INK, alignment=TA_CENTER, wordWrap="CJK",
    ),
    "quote": ParagraphStyle(
        "quote", fontName="STSong-Light", fontSize=11.2, leading=18,
        textColor=NAVY, alignment=TA_CENTER, wordWrap="CJK",
    ),
}


def p(text, style="body"):
    return Paragraph(text, styles[style])


def title(number, text, subtitle=None):
    items = [p(f"{number}  {text}", "h1")]
    if subtitle:
        items.append(p(subtitle, "note"))
        items.append(Spacer(1, 3 * mm))
    return items


def bullets(items, color=BLUE):
    rows = [[p("●", "small"), p(item, "body")] for item in items]
    result = Table(rows, colWidths=[5 * mm, 165 * mm], hAlign="LEFT")
    result.setStyle(TableStyle([
        ("TEXTCOLOR", (0, 0), (0, -1), color),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return result


def callout(head, body, fill=PALE_BLUE, border=BLUE):
    result = Table(
        [[p(head, "h3")], [p(body, "body")]],
        colWidths=[171 * mm],
        hAlign="LEFT",
    )
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fill),
        ("BOX", (0, 0), (-1, -1), 0.8, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return KeepTogether(result)


def table(data, widths, header=True, font="small", row_bgs=None):
    cooked = [[p(str(cell), font) for cell in row] for row in data]
    result = Table(cooked, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        commands += [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ]
    for row, color in row_bgs or []:
        commands.append(("BACKGROUND", (0, row), (-1, row), color))
    result.setStyle(TableStyle(commands))
    return result


def render_asset(name):
    TMP.mkdir(parents=True, exist_ok=True)
    source = ROOT / "assets" / f"{name}.pdf"
    target = TMP / f"zh_{name}.png"
    doc = fitz.open(source)
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(2.2, 2.2), alpha=False)
    pix.save(target)
    return target


def figure(name, width_mm, caption):
    path = render_asset(name)
    pix = fitz.Pixmap(str(path))
    ratio = pix.height / pix.width
    image = Image(str(path), width=width_mm * mm, height=width_mm * ratio * mm)
    image.hAlign = "CENTER"
    return [image, Spacer(1, 2 * mm), p(caption, "note")]


def build_story():
    story = []

    story += [Spacer(1, 30 * mm), p("ICLR 2027 稿件内部伴读材料", "cover_kicker")]
    story += [p("AI4AI4Bio 中文伴读版", "cover_title")]
    story += [p("协作式证据引导的生物模型改进", "cover_sub")]
    story += [Spacer(1, 5 * mm), HRFlowable(width="72%", thickness=1.2, color=TEAL, hAlign="CENTER")]
    story += [Spacer(1, 12 * mm)]
    story += [callout(
        "这份文件怎么用",
        "它不是对英文稿的逐句替换，而是一份覆盖全部正文和附录的中文导读。先读第 2、8、9、10、18 页即可掌握核心结论，再根据第 13-16 页定位英文稿中的技术细节。",
        PALE_TEAL,
        TEAL,
    )]
    story += [Spacer(1, 12 * mm)]
    cover_stats = [
        [p("3", "cover_title"), p("5", "cover_title"), p("6", "cover_title"), p("3", "cover_title")],
        [p("生物任务族", "center"), p("主评测端点", "center"), p("因子对照组", "center"), p("预设随机种子", "center")],
    ]
    stats = Table(cover_stats, colWidths=[42 * mm] * 4)
    stats.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.8, BLUE),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 1), (-1, 1), 2),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
    ]))
    story += [stats, Spacer(1, 16 * mm)]
    story += [p("实验状态：全部主实验已完成 | 版本日期：2026-09-22", "center")]
    story += [p("定位：帮助作者快速理解论证结构、结果边界和答辩要点", "center")]
    story.append(PageBreak())

    story += title("01", "30 秒读懂这篇论文", "先理解论文真正证明了什么，再看实现细节。")
    summary = [
        ["问题", "不同生物实验室持有互补数据，但原始测量往往不能集中共享；已有研究通常只解决本地模型训练，或只让 agent 在可访问数据上改方案。"],
        ["方法", "AI4AI4Bio 把两层过程接起来：内层在数据所属实验室本地训练并聚合更新；外层根据聚合开发集证据提出、执行并筛选可复现的模型设计。"],
        ["实验", "统一测试 DTI、蛋白组学疗效预测、细胞扰动识别三类任务；细胞任务进一步分为单基因、双基因和药物扰动，共五个主端点。"],
        ["主结果", "十实验室完整系统在五个端点中的四个取得三种主配置里的最高分；相对单实验室 direct search 的提升为 +3.87、+16.85、+10.45、+8.10、+6.97 个百分点。"],
        ["最重要消融", "更多实验室参与在五个端点上都带来正增益；但 matched-access 下 loop 与 direct search 的结果全部持平，当前尚未证明迭代反馈本身的独立增益。"],
        ["结论边界", "论文支持的是 expanded participation 带来的 access-enabled system gain；不是新联邦优化算法，不是正式隐私系统，也不是全局 SOTA 或前瞻湿实验验证。"],
    ]
    story += [table([["要点", "中文解释"]] + summary, [28 * mm, 143 * mm])]
    story += [Spacer(1, 6 * mm), callout(
        "一句话版本",
        "我们提供了一套让多个数据持有方共同训练模型、并用聚合证据共同评估模型设计的统一研究接口；当前实验证明多方参与有用，但尚未证明研究反馈循环本身优于同预算的直接搜索。",
        PALE_GOLD,
        GOLD,
    )]
    story.append(PageBreak())

    story += title("02", "论文的论证链", "正文不是在证明一个万能 agent，而是在验证一个统一协作研究接口。")
    chain = [
        ["1. 现实约束", "数据分散在实验室，原始响应受隐私、所有权或未公开工作限制。"],
        ["2. 方法缺口", "参数聚合通常固定模型设计；研究 agent 通常要求数据或 evaluator 可直接访问。"],
        ["3. 我们的接口", "数据留在 worker；共享参数更新和聚合开发证据；外层 agent 只修改受约束的可执行配置。"],
        ["4. 可检验问题", "更多参与方是否提高结果？反馈历史是否优于无反馈搜索？选中的改动是否能泛化到 held-out 测试？"],
        ["5. 证据", "三任务族、五端点、六臂因子设计、三 seed、统一预算和同一 scorer。"],
        ["6. 结论", "participation 效果稳定为正；feedback 效果当前为零；search 效果因任务而异。"],
    ]
    for idx, (head, body) in enumerate(chain):
        fill = PALE_TEAL if idx in (2, 4) else PALE_BLUE
        border = TEAL if idx in (2, 4) else BLUE
        story += [callout(head, body, fill, border), Spacer(1, 3 * mm)]
    story += [Spacer(1, 3 * mm), p(
        "贡献应当写成“共同接口 + 跨任务执行证据 + 因子化归因”，而不是把四个最好结果包装为五个任务全部 SOTA。",
        "quote",
    )]
    story.append(PageBreak())

    story += title("03", "研究范式：为什么需要这项工作")
    story += figure(
        "paradigm_comparison",
        171,
        "英文主稿图 1。左：传统 bio-agent 能迭代模型设计，但依赖可访问数据。中：协作训练让原始数据留在本地，但设计固定。右：AI4AI4Bio 同时连接本地参数学习与共享研究循环。",
    )
    story += [Spacer(1, 4 * mm)]
    paradigm = [
        ["范式", "优点", "局限"],
        ["可访问数据上的 bio-agent", "能根据实验反馈迭代代码或模型设计", "新增实验室通常需要把测量交给 agent 或中心环境"],
        ["固定设计的协作训练", "原始数据可留在各 worker，本地更新后聚合", "训练的模型结构和研究方案预先固定"],
        ["AI4AI4Bio", "参数更新与模型设计都能利用分布式证据", "当前是同机模拟；没有正式隐私保护；反馈增益尚未建立"],
    ]
    story += [table(paradigm, [40 * mm, 65 * mm, 66 * mm], row_bgs=[(3, PALE_TEAL)])]
    story.append(PageBreak())

    story += title("04", "方法：一套核心流程贯穿三个任务")
    story += figure(
        "unified_pipeline",
        171,
        "英文主稿图 2。外层 Qwen2.5-7B 提出假设和配置；内层所有任务共享训练、聚合、打分与保留规则，仅预测 adapter 不同。",
    )
    story += [Spacer(1, 3 * mm)]
    story += [bullets([
        "假设：提出一个可检验的配置改动，并声明预期作用。",
        "实例化：design ID 被编译为统一十二项候选库中的可执行配置。",
        "训练：每个候选从相同 seed 的公共初始化重新开始，训练 100 个协作 round。",
        "评估：每五轮由本地开发 worker 返回标量指标；测试集从不进入训练、提案或选择。",
        "保留或拒绝：按主指标优先、开发损失破平；失败和负结果保留在历史中。",
    ])]
    story.append(PageBreak())

    story += title("05", "内层训练与外层研究循环分别在做什么")
    story += [p("内层：本地参数学习", "h2")]
    story += [bullets([
        "实验室 worker 只读取自己的 train/dev shard，完成一个本地 epoch，再返回参数更新和样本数。",
        "协调器按本地训练样本量加权平均。server momentum 为 0 时等价于 sample-weighted FedAvg。",
        "所有任务使用 AdamW、梯度裁剪、每轮重置本地 optimizer，并按相同 checkpoint 规则运行。",
        "一实验室对照走完全相同代码路径，只是参与集合大小为 1。",
    ], TEAL)]
    story += [p("外层：证据引导的设计修改", "h2")]
    story += [bullets([
        "loop 和 direct 都有六个 proposal slot、同一 Qwen checkpoint、同一候选设计库和同一训练预算。",
        "direct 只能看到尝试过的配置，不能看到评估结果；loop 能看到先前分数、训练诊断、是否接受或失败。",
        "研究模型不查看原始表达谱、相互作用行或测试标签；它只接收配置与聚合标量历史。",
        "当前候选空间较小，direct 和 loop 经常覆盖同一组设计，这解释了 feedback 对照全部持平。",
    ], BLUE)]
    story += [Spacer(1, 5 * mm), callout(
        "术语口径",
        "论文主线称为 collaborative evidence-guided research。FedAvg 只用于精确描述内层聚合实现；论文不声称提出新的联邦优化器，也不把数据本地化等同于隐私保证。",
        PALE_GOLD,
        GOLD,
    )]
    story.append(PageBreak())

    story += title("06", "实验设计：三个任务族，五个主端点", "主表的五行不是五套互不相干的实验，而是三类生物问题的统一协议实例。")
    design = [
        ["任务族", "预测问题与数据", "模型接口", "主指标"],
        ["DTI", "输入化合物与蛋白序列，判断是否互作。BindingDB train/dev 为 50,149/5,604 对；主测试 random split 为 5,505 对。", "TAPB 架构；冻结公开 ESM2 蛋白特征，训练药物、融合和分类模块。", "AUROC"],
        ["蛋白组学疗效", "输入处理后 6h/24h 蛋白响应和药物 Morgan 特征，预测二元 efficacy；最终角色含 148 个条件。", "ProteinTalks-derived efficacy head；不是完整 ppODE 或前向蛋白轨迹模型。", "Average Precision"],
        ["VCC 单基因", "从五个候选单基因扰动中识别真实扰动；whole-intervention 60/20/20。", "冻结、mask 修正后的 scDEBART 表征，训练 response MLP。", "Macro Top-1"],
        ["Norman 双基因", "从五个候选双基因过表达中识别真实组合；70/20/27。", "同一 cell adapter 和 scorer。", "Macro Top-1"],
        ["Tahoe 药物", "固定细胞背景和剂量，从五个候选药物中识别真实处理；180/60/67。", "scDEBART response head 加固定 Morgan 投影条件。", "Macro Top-1"],
    ]
    story += [table(design, [27 * mm, 64 * mm, 55 * mm, 25 * mm], font="tiny")]
    story += [Spacer(1, 5 * mm), callout(
        "统一性在哪里",
        "三任务共享：十客户端划分、训练调度、研究模型、十二项设计库、六次 proposal、选择规则、三个 seed 和 held-out 冻结流程。不同的只有输入表示、预测头和任务指标。",
        PALE_TEAL,
        TEAL,
    )]
    story.append(PageBreak())

    story += title("07", "主结果：完整系统在五项中的四项最高")
    main = [
        ["主端点", "Fixed 1 lab", "Direct 1 lab", "Ours 10 labs", "Ours - Direct"],
        ["DTI: TAPB random AUROC", "82.83", "89.89", "<b>93.76</b>", "+3.87"],
        ["Proteomics efficacy AP", "25.05", "20.13", "<b>36.99</b>", "+16.85"],
        ["VCC single-gene Top-1", "29.94", "21.09", "<b>31.54</b>", "+10.45"],
        ["Norman double-gene Top-1", "<b>25.56</b>", "14.15", "22.25", "+8.10"],
        ["Tahoe drug Top-1", "19.40", "15.42", "<b>22.39</b>", "+6.97"],
    ]
    story += [table(main, [56 * mm, 28 * mm, 28 * mm, 30 * mm, 29 * mm], row_bgs=[(1, PALE_TEAL), (2, PALE_TEAL), (3, PALE_TEAL), (5, PALE_TEAL)])]
    story += [Spacer(1, 4 * mm), p("数值为 seeds 42/43/44 的 held-out 均值乘以 100。粗体只表示三种展示配置中最高，不表示统计显著或全球 SOTA。", "note")]
    story += [Spacer(1, 5 * mm), callout(
        "如何解读",
        "最直观的产品级结论是：允许十个实验室参与的完整系统，相比只使用一个实验室数据的直接优化，在五项上都更高。但这个差异同时包含更多训练数据、更多开发证据和更多计算，不能解释成纯算法优势。",
        PALE_BLUE,
        BLUE,
    )]
    story += [Spacer(1, 4 * mm), callout(
        "不能回避的例外",
        "Norman 上单实验室 fixed 为 25.56，高于我们的 22.25。论文保留了这个结果；这也是为什么英文稿写 four of five，而不是声称全部任务最优。",
        PALE_RED,
        colors.HexColor("#A33A4B"),
    )]
    story.append(PageBreak())

    story += title("08", "关键消融：增益来自哪里")
    effects = [
        ["主端点", "Search: loop - fixed<br/>(10 labs)", "Feedback: loop - direct<br/>(10 labs)", "Participation: 10 - 1 labs<br/>(loop)"],
        ["DTI", "+1.96", "+0.00", "+3.87"],
        ["Proteomics", "-0.08", "+0.00", "+16.85"],
        ["VCC", "+0.00", "+0.00", "+11.32"],
        ["Norman", "+6.77", "+0.00", "+8.10"],
        ["Tahoe", "-3.48", "+0.00", "+6.97"],
    ]
    story += [table(effects, [43 * mm, 42 * mm, 43 * mm, 43 * mm])]
    story += [Spacer(1, 5 * mm)]
    story += [p("三个列分别回答不同问题", "h2")]
    story += [bullets([
        "Search：完整 loop 相对固定配方是否有价值？答案随任务变化，DTI 和 Norman 为正，Tahoe 为负。",
        "Feedback：给 proposer 看历史评估证据，是否比不看证据的 direct search 更好？当前五项全部为 0.00。",
        "Participation：保持 loop 机制不变，从一个实验室扩展到十个实验室是否有价值？五项全部为正，这是最稳定的事实。",
    ])]
    story += [Spacer(1, 5 * mm), callout(
        "论文最稳妥的主张",
        "统一接口能让更多实验室的数据和开发证据在不交给研究 LLM 的情况下改善共享模型。当前 bounded loop 提供了可执行、可追踪的设计研究机制，但尚未展示独立的反馈驱动性能收益。",
        PALE_GOLD,
        GOLD,
    )]
    story.append(PageBreak())

    story += title("09", "三个任务分别说明了什么")
    story += [p("DTI：最强的正向算法案例", "h2")]
    story += [bullets([
        "主端点是 TAPB random-split AUROC；我们的十实验室 loop 为 93.76。",
        "十实验室 loop 相对十实验室 fixed 提升 1.96 点，说明在这个任务上 bounded design search 有正收益。",
        "unseen-drug 和 unseen-protein 被强制保留为次要端点，避免只展示随机划分。",
    ], TEAL)]
    story += [p("蛋白组学：最强的参与增益案例", "h2")]
    story += [bullets([
        "任务是 observed-response efficacy classification，不是从药物预测完整蛋白响应。",
        "我们的 AP 为 36.99，相对单实验室 direct 高 16.85 点。",
        "十实验室 loop 与 fixed 基本相同，search 效果为 -0.08；主要收益来自参与数据扩展。",
    ], TEAL)]
    story += [p("细胞扰动：跨 intervention 类型的压力测试", "h2")]
    story += [bullets([
        "VCC 单基因、Norman 双基因、Tahoe 药物统一为五选一逆向识别，随机 Top-1 为 20%。",
        "VCC 和 Tahoe 的完整系统最高；Norman 则由单实验室 fixed 最高。",
        "任务是从观察到的响应识别扰动，不等价于标准 forward-expression leaderboard。",
    ], TEAL)]
    story.append(PageBreak())

    story += title("10", "Harness 到底做了什么，为什么方便审计")
    harness = [
        ["阶段", "实际产物", "审计价值"],
        ["提出假设", "结构化记录假设、预期影响、实验计划和 design ID", "能区分事前假设与事后解释"],
        ["实例化方案", "design ID 编译为受约束、可执行配置", "减少任意代码漂移，保证不同任务共享同一候选菜单"],
        ["训练与评估", "固定预算的本地训练、checkpoint 选择和聚合开发指标", "失败也消耗预算，不会免费重试直到成功"],
        ["保留或拒绝", "主指标优先、loss 破平的 ratchet 规则", "避免人工凭测试结果挑模型"],
        ["传递证据", "下一轮只接收配置、分数、训练诊断和接受/失败历史", "不向研究 LLM 暴露原始生物响应"],
        ["冻结测试", "先封存配置、checkpoint 和 hash，再开启 held-out scorer", "测试结果不能反向影响 proposal"],
    ]
    story += [table(harness, [31 * mm, 69 * mm, 71 * mm])]
    story += [Spacer(1, 5 * mm), callout(
        "审计不等于防御性写作",
        "审计机制的价值是让“agent 提出了什么、试了什么、为什么接受、哪里失败”都可复核，从而支持可信的性能结论。它是方法能力的一部分，但论文主贡献仍应围绕协作模型改进和实验结果，而不是只强调风险。",
        PALE_BLUE,
        BLUE,
    )]
    story.append(PageBreak())

    story += title("11", "数据边界：哪些信息被共享，哪些没有")
    boundary = [
        ["对象", "实验室本地", "返回协调器", "返回研究 LLM"],
        ["原始训练响应", "是", "否", "否"],
        ["原始开发响应", "是", "否", "否"],
        ["模型参数更新", "本地产生", "是", "否"],
        ["样本数与聚合统计", "本地计算", "是", "仅聚合标量"],
        ["开发指标与训练诊断", "本地计算", "聚合", "聚合历史"],
        ["候选配置和研究历史", "接收并执行", "是", "是"],
        ["held-out 测试结果", "独立评估", "最终报告", "从不反馈"],
    ]
    story += [table(boundary, [43 * mm, 36 * mm, 43 * mm, 49 * mm])]
    story += [Spacer(1, 6 * mm)]
    story += [callout(
        "现在可以说什么",
        "原始 response shard 不发送给研究模型；本地 worker 可以通过参数更新和聚合开发证据参与共同模型和设计选择。",
        PALE_TEAL,
        TEAL,
    ), Spacer(1, 3 * mm)]
    story += [callout(
        "现在不能说什么",
        "同机模拟不构成 adversarial isolation；没有 secure aggregation 或 differential privacy；协调基础设施仍参与离线打包和完整性验证。因此不应写成已获得密码学或制度级隐私保证。",
        PALE_RED,
        colors.HexColor("#A33A4B"),
    )]
    story.append(PageBreak())

    story += title("12", "英文正文逐节导读")
    main_sections = [
        ["部分", "在讲什么", "读者应带走什么"],
        ["Abstract", "现实问题、双层框架、三任务验证、主要数值和因子消融。", "四项最佳，但反馈独立增益未建立。"],
        ["1 Introduction", "数据分散与 agent 研究之间的缺口；定义三项贡献。", "贡献是接口、跨任务执行和可归因实验。"],
        ["2 Related work", "定位自动研究、协作训练、FedEx、Helmsman、DrugEvolve 等。", "不声称第一个组合两者，也不混用不可比协议。"],
        ["3 Method", "双层优化、FedAvg 实现、Qwen proposal、数据与证据边界。", "同一 core，task-specific adapters。"],
        ["4 Experimental design", "三个任务、五端点、六臂、三个 seed、冻结和评分规则。", "主表是 access-enabled system comparison；消融负责归因。"],
        ["5 Results", "主表、participation/search/feedback 分解、执行证据与历史支持实验。", "participation 稳定为正，feedback 为零。"],
        ["6 Discussion", "解释为什么 loop 未显示额外收益，以及下一步如何验证。", "小设计库和六次预算可能让 direct 与 loop 重合。"],
        ["7 Conclusion", "总结方法可行性、实证结论与仍未解决的问题。", "不把负结果藏起来。"],
        ["Reproducibility / Ethics / AI", "说明产物、数据许可、隐私边界和 AI 辅助。", "所有成绩来自真实 scorer，不是 LLM 估计。"],
    ]
    story += [table(main_sections, [33 * mm, 75 * mm, 63 * mm], font="tiny")]
    story.append(PageBreak())

    story += title("13", "附录导读：A 到 J", "这些部分主要回答复现、历史比较和 scorer 细节。")
    app_a_i = [
        ["附录", "内容", "为什么存在"],
        ["A Secondary metrics", "完整 seed 级主指标和次要 ranking 指标。", "防止主表只给均值或只挑单一指标。"],
        ["B Infrastructure continuation", "中断、重试、恢复和预算记账规则。", "证明基础设施故障没有带来额外搜索机会。"],
        ["C Historical PTPC", "早期 ProteinTalks observed-response source-editing 协议。", "保留历史证据，但明确不与当前 100-round 主协议混用。"],
        ["D Search costs and audits", "DTI 搜索成本、失败率、校准信息 replay 和审计案例。", "展示调用、训练和负结果的完整性。"],
        ["E Historical DTI architecture search", "harness、direct、DrugEvolve 的历史 native-system 比较。", "回答与 DrugEvolve 的关系，但不伪装成完全同构复现。"],
        ["F Full historical DTI metrics", "历史十二 epoch 训练的全量指标。", "保留所有端点，避免只报最好项。"],
        ["G/H PTPC supplements", "蛋白组学次要指标、成本、案例和来源解释。", "支持 efficacy 结论与可解释性边界。"],
        ["I Cell scorer contracts", "Norman archive、逆向识别、sequential/CEX 的精确定义。", "防止把不同细胞问题误认为同一 benchmark。"],
        ["J PTPC diagnostics", "标签平衡、固定 head 和历史预测诊断。", "区分数据难度、校准问题与研究 loop 的实际贡献。"],
    ]
    story += [table(app_a_i, [22 * mm, 79 * mm, 70 * mm], font="tiny")]
    story.append(PageBreak())

    story += title("14", "附录导读：K 到 Q")
    app_k_q = [
        ["附录", "内容", "当前稿件中的角色"],
        ["K Local training and data availability", "本地 logistic fitting、中心化等价检查、matched access 和完整 PTPC 对照。", "说明 local update 实现正确，但不声称优于同数据中心训练。"],
        ["L Full-training DTI", "冻结 architecture roster 后的完整 DTI 重训、现代 fixed reference 和成本。", "把低预算搜索与最终 full fit 区分开。"],
        ["M Research over fixed DTI predictors", "固定预测器上的 program search、TAPB transfer 和互补性解释。", "检验 research program 是否能跨预测器迁移。"],
        ["N Historical studies", "早期 cell policy、DTI native package、PTPC matched study。", "作为 supporting evidence，不进入当前主表。"],
        ["O Training-CV-guided feature research", "training-only CV、Helmsman adaptation、冻结和成本。", "记录另一路反馈研究，包括没有 loop superiority 的结果。"],
        ["P Strong-start optimization", "更强起点下的 DTI/proteomics 研究矩阵与 client scaling。", "排除“只因起点太弱才有提升”的部分解释。"],
        ["Q Trainable cell pilots", "已完成的早期 20-round cell pilot。", "历史协议；不等同于当前 Appendix R 的 100-round 三 seed 结果。"],
    ]
    story += [table(app_k_q, [21 * mm, 85 * mm, 65 * mm], font="tiny")]
    story.append(PageBreak())

    story += title("15", "附录 R：当前结果的事实底座")
    story += [p("Appendix R 是阅读当前主表时最重要的附录。它集中给出：", "body")]
    story += [bullets([
        "当前 uniform protocol 的版本、完整十二项候选库与六次 proposal 规则。",
        "三个 seed 下六个 arm 的全因子 held-out 结果，而不是只给主表三列。",
        "Search、Feedback、Participation 的完整 effect table 和 seed-level 不确定性。",
        "DTI random、unseen-drug、unseen-protein 三个 frozen endpoint。",
        "所有任务的 AP、AUROC、BCE、MRR、Top-3、cross-entropy 等次要指标。",
        "独立重算、hash 绑定、checkpoint seal 和 publication test 结果。",
    ])]
    story += [Spacer(1, 4 * mm)]
    audit = [
        ["审计项目", "数量 / 状态"],
        ["task-seed studies", "15，全部完成"],
        ["primary arm-seed cells", "90，全部完成"],
        ["development audits", "15，全部通过"],
        ["held-out audits / verifications", "30，全部通过"],
        ["independently rescored arm-endpoints", "135，全部通过"],
        ["publication tests", "29，全部通过"],
    ]
    story += [table(audit, [90 * mm, 81 * mm], row_bgs=[(1, PALE_TEAL), (2, PALE_TEAL), (3, PALE_TEAL), (4, PALE_TEAL), (5, PALE_TEAL), (6, PALE_TEAL)])]
    story += [Spacer(1, 5 * mm), callout(
        "为什么主表不放 seed 数",
        "主表只承担“一眼看懂五个端点”的任务。每项都是预设 seeds 42/43/44 的均值；样本标准差、精确 seed 数和不确定性统一放 Appendix R，既不隐瞒，也不破坏主图表的信息层级。",
        PALE_BLUE,
        BLUE,
    )]
    story.append(PageBreak())

    story += title("16", "可声称、不可声称，以及可能被追问的问题")
    claims = [
        ["可以直接声称", "需要谨慎表述或不能声称"],
        ["一个统一接口已在三类生物任务、五个端点上完整执行。", "不能说所有任务都达到全球 SOTA；当前比较是稿内三配置和特定 task reference。"],
        ["十实验室参与相对单实验室 loop 在五项上均有正 held-out 增益。", "不能把 10-vs-1 全部归因于优化算法，因为数据、开发证据和计算同时增加。"],
        ["研究模型不接收原始生物响应，只接收配置和聚合诊断。", "不能声称 differential privacy、secure aggregation 或对抗性数据隔离。"],
        ["所有主实验、三 seed、审计与独立重算已完成。", "不能把 retrospective held-out 称为新的 blind confirmation。"],
        ["DTI 和 Norman 上 search 相对 fixed 有正向结果。", "不能说 feedback loop 已经优于 matched-budget direct；五项当前都持平。"],
    ]
    story += [table(claims, [85.5 * mm, 85.5 * mm])]
    story += [Spacer(1, 5 * mm), p("高概率追问", "h2")]
    qas = [
        ["为什么不用同数据 centralized baseline？", "这是当前最重要的补充实验之一。现稿通过等价检查说明聚合目标正确，但没有把所有主任务都做成 same-data centralized 对照。"],
        ["为什么 loop 没有优于 direct？", "候选库只有十二项且预算六次，两者往往尝试相同配置；下一步应扩大可修改空间并设置真正需要连续证据更新的任务。"],
        ["单实验室为什么固定为 client 0？", "这是预先指定的 operational comparator，但可能受 client 代表性影响；更强版本应做 client rotation。"],
        ["隐私贡献是什么？", "当前贡献是 data-local execution boundary 与 information-flow contract，而不是形式化隐私机制。"],
    ]
    story += [table([["问题", "建议回答"]] + qas, [57 * mm, 114 * mm], font="tiny")]
    story.append(PageBreak())

    story += title("17", "建议阅读顺序与投稿状态")
    story += [p("如果只有 15 分钟", "h2")]
    story += [bullets([
        "先看英文稿 Figure 1 和 Figure 2，理解范式差异与统一 pipeline。",
        "看正文 Table 1：五个主端点和三种 operational configuration。",
        "看正文 Table 2：把 Participation、Search、Feedback 三种效应拆开。",
        "读 Discussion：理解为什么 strongest evidence 是 participation，而不是 feedback。",
        "需要查数字或复现时直接去 Appendix R；历史方法比较再查 Appendices E、L、M、N、O、P、Q。",
    ])]
    story += [Spacer(1, 5 * mm)]
    readiness = [
        ["项目", "当前状态"],
        ["主实验", "完成：3 个任务族、5 个端点、6 个 arm、3 个 seed"],
        ["主表与关键消融", "完成：正文 clean table + effect table"],
        ["一致性与结果审计", "完成：29 tests，135 个 endpoint 独立重算"],
        ["英文 PDF", "完成：正文 9 页，参考文献从第 10 页开始"],
        ["仍需作者操作", "Overleaf 最终编译；OpenReview 作者信息；AI-use 表单；匿名代码材料"],
    ]
    story += [table(readiness, [52 * mm, 119 * mm], row_bgs=[(1, PALE_TEAL), (2, PALE_TEAL), (3, PALE_TEAL), (4, PALE_TEAL)])]
    story += [Spacer(1, 8 * mm), callout(
        "最终判断",
        "稿件已经是完整、可提交、结果可追溯的 ICLR 论文版本。它最有说服力的贡献是跨任务的协作研究接口和稳定 participation 增益；如果有时间继续增强，优先级应是 same-data centralized baseline、client rotation、独立数据集验证，以及能真正区分 feedback 与 direct search 的更大设计空间。",
        PALE_GOLD,
        GOLD,
    )]
    story += [Spacer(1, 10 * mm), p("对应英文稿版本：Git commit ea0a6faf8696d3dc12d90f004bbad22d28300cff", "note")]
    story += [p("本伴读版只解释已执行结果，不生成或替代任何实验分数。", "note")]
    return story


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    doc = CompanionDoc(str(OUT))
    doc.build(build_story())
    print(OUT)


if __name__ == "__main__":
    main()
