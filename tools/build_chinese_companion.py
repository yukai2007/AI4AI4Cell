#!/usr/bin/env python3
"""Build a concise Chinese reading companion for the current manuscript."""
from pathlib import Path

import fitz
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, PageBreak, PageTemplate, Paragraph,
    Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf" / "AI4AI4Cell_中文伴读版.pdf"
TMP = ROOT / "tmp" / "pdfs"

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#356FA3")
TEAL = colors.HexColor("#238B7B")
PURPLE = colors.HexColor("#76539A")
ORANGE = colors.HexColor("#D97732")
INK = colors.HexColor("#243746")
MUTED = colors.HexColor("#6D7D8A")
LINE = colors.HexColor("#CBD5DC")
PALE_BLUE = colors.HexColor("#E8F1F8")
PALE_TEAL = colors.HexColor("#E7F5F2")
PALE_PURPLE = colors.HexColor("#F1EAF7")
PALE_ORANGE = colors.HexColor("#FBEDE3")

pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))


class Doc(BaseDocTemplate):
    def __init__(self, filename):
        super().__init__(filename, pagesize=A4, leftMargin=17*mm,
                         rightMargin=17*mm, topMargin=18*mm,
                         bottomMargin=16*mm, title="AI4AI4Cell 中文伴读版")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height)
        self.addPageTemplates(PageTemplate(id="main", frames=[frame], onPage=self._page))

    @staticmethod
    def _page(canvas, doc):
        canvas.saveState()
        if doc.page > 1:
            canvas.setStrokeColor(LINE)
            canvas.line(17*mm, A4[1]-12*mm, A4[0]-17*mm, A4[1]-12*mm)
            canvas.setFont("STSong-Light", 8)
            canvas.setFillColor(MUTED)
            canvas.drawString(17*mm, A4[1]-9.5*mm, "AI4AI4Cell 中文伴读版")
            canvas.drawRightString(A4[0]-17*mm, 9*mm, str(doc.page))
        canvas.restoreState()


STYLES = {
    "cover": ParagraphStyle("cover", fontName="STSong-Light", fontSize=28,
                            leading=39, textColor=NAVY, alignment=TA_CENTER),
    "subtitle": ParagraphStyle("subtitle", fontName="STSong-Light", fontSize=14,
                               leading=22, textColor=MUTED, alignment=TA_CENTER),
    "h1": ParagraphStyle("h1", fontName="STSong-Light", fontSize=20,
                         leading=29, textColor=NAVY, spaceAfter=10),
    "h2": ParagraphStyle("h2", fontName="STSong-Light", fontSize=13,
                         leading=20, textColor=BLUE, spaceBefore=6, spaceAfter=5),
    "body": ParagraphStyle("body", fontName="STSong-Light", fontSize=9.6,
                           leading=15.5, textColor=INK, wordWrap="CJK", spaceAfter=6),
    "small": ParagraphStyle("small", fontName="STSong-Light", fontSize=8.2,
                            leading=12.5, textColor=INK, wordWrap="CJK"),
    "tiny": ParagraphStyle("tiny", fontName="STSong-Light", fontSize=7.3,
                           leading=10.5, textColor=INK, wordWrap="CJK"),
    "center": ParagraphStyle("center", fontName="STSong-Light", fontSize=9.2,
                             leading=14, textColor=INK, alignment=TA_CENTER),
    "note": ParagraphStyle("note", fontName="STSong-Light", fontSize=8.4,
                           leading=13, textColor=MUTED, wordWrap="CJK"),
}


def p(text, style="body"):
    return Paragraph(text, STYLES[style])


def table(rows, widths, font="small", highlights=()):
    cooked = [[p(str(cell), font) for cell in row] for row in rows]
    t = Table(cooked, colWidths=widths, repeatRows=1)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for row, color in highlights:
        cmds.append(("BACKGROUND", (0, row), (-1, row), color))
    t.setStyle(TableStyle(cmds))
    return t


def callout(head, body, fill=PALE_BLUE, border=BLUE):
    t = Table([[p(head, "h2")], [p(body)]], colWidths=[171*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fill),
        ("BOX", (0, 0), (-1, -1), 0.8, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def bullets(items, color=TEAL):
    rows = [[p("●", "small"), p(item)] for item in items]
    t = Table(rows, colWidths=[5*mm, 166*mm])
    t.setStyle(TableStyle([
        ("TEXTCOLOR", (0, 0), (0, -1), color),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def figure(name, width_mm):
    TMP.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(ROOT / "assets" / f"{name}.pdf")
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(2.1, 2.1), alpha=False)
    target = TMP / f"zh_{name}.png"
    pix.save(target)
    ratio = pix.height / pix.width
    return Image(str(target), width=width_mm*mm, height=width_mm*ratio*mm)


def story():
    s = [Spacer(1, 38*mm), p("AI4AI4Cell 中文伴读版", "cover"),
         p("协作式证据引导的生物模型改进", "subtitle"), Spacer(1, 12*mm),
         callout("核心问题",
                 "多个生物实验室拥有互补数据。AI4AI4Cell 让这些数据在本地参与两件事：一是训练共享预测模型，二是为外层研究循环评价和选择下一版可执行设计。",
                 PALE_TEAL, TEAL), Spacer(1, 10*mm),
         table([["任务族", "主端点", "实验配置", "随机种子"],
                ["DTI / 蛋白组学 / 细胞扰动", "5", "6 臂因子设计", "42 / 43 / 44"],
                ["蛋白组学 / 3 类细胞扰动", "4", "同预算 loop 隔离", "53 / 54 / 55"]],
               [55*mm, 32*mm, 45*mm, 39*mm]), Spacer(1, 12*mm),
         p("对应英文稿：2026-09-22 当前统一实验版本", "center"), PageBreak()]

    s += [p("1  论文主线", "h1"),
          callout("一句话贡献",
                  "我们提出一个统一的协作研究框架：内层通过客户端本地训练更新模型参数，外层通过结构化 proposal、聚合开发证据和持续实验历史改进模型设计。",
                  PALE_PURPLE, PURPLE), Spacer(1, 5*mm),
          p("所谓 two levels 不是同一件事的两种说法，而是两个明确的反馈通道：", "body"),
          bullets([
              "参数层：每个实验室在本地训练候选模型，协调器聚合更新，得到共享预测器。",
              "设计层：每个实验室在本地开发集上评价候选模型，协调器形成 aggregate evidence card，决定保留哪一个设计，并把结果交给下一轮 proposer。",
          ]), Spacer(1, 4*mm),
          p("论文的三项贡献", "h2"),
          table([["贡献", "具体内容"],
                 ["协作研究框架", "把 client-local parameter fitting 与 distributed design evaluation 连接起来。"],
                 ["新的 evidence-guided harness", "统一 proposal schema、执行、保留规则和 accepted/rejected/failed 历史传递。"],
                 ["跨任务实证", "用同一 core 在 DTI、蛋白组学和三类细胞扰动上做六臂、三 seed 对照。"]],
                [42*mm, 129*mm]), PageBreak()]

    s += [p("2  三种研究范式", "h1"), figure("paradigm_comparison", 171),
          Spacer(1, 3*mm),
          p("图中的颜色有固定语义：绿色表示实验室本地数据，蓝色表示预测模型，紫色表示研究 harness，橙色表示模型更新与证据聚合门。灰色虚线表示该范式缺少的模块。", "note"),
          Spacer(1, 5*mm),
          table([["范式", "具备的能力", "关键差异"],
                 ["Centralized bio-agent", "在一份可访问数据上训练、评价并迭代设计", "缺少多实验室聚合"],
                 ["Collaborative training", "多实验室本地训练并聚合共享模型", "可执行设计保持固定"],
                 ["AI4AI4Cell", "同时更新共享模型与研究设计", "aggregate evidence card 闭合外层循环"]],
                [43*mm, 65*mm, 63*mm], highlights=[(3, PALE_TEAL)]), PageBreak()]

    s += [p("3  Harness 外层到底做什么", "h1"),
          table([["阶段", "输入", "输出 / 作用"],
                 ["1. Hypothesize", "任务契约、incumbent、历史 evidence cards", "提出一个聚焦且可检验的假设"],
                 ["2. Instantiate", "结构化 proposal", "验证 design_id 并编译为可执行配置"],
                 ["3. Train + evaluate", "候选设计、各实验室 train/dev shard", "共享 predictor 与聚合开发诊断"],
                 ["4. Retain + remember", "候选与 incumbent 的证据", "保留较优设计；记录成功、拒绝与失败"],
                 ["5. Next proposal", "完整有序研究历史", "避免重复无效方向，并利用前轮结果形成下一假设"]],
                [35*mm, 64*mm, 72*mm]), Spacer(1, 6*mm),
          p("每个 proposal 的固定 JSON 字段", "h2"),
          table([["字段", "含义"],
                 ["hypothesis", "关于一个可编辑因素的明确预测"],
                 ["experiment", "要执行的改变以及与 incumbent 的对照"],
                 ["expected_effect", "预期指标方向和训练/验证诊断特征"],
                 ["design_id", "可被机器解析并编译的候选标识"]],
                [48*mm, 123*mm]), Spacer(1, 6*mm),
          callout("为什么历史记录重要",
                  "下一轮 loop 不只看到当前最好分数，还看到配置、best round、开发 metric/loss、首末训练诊断以及接受/拒绝/失败状态。因此实验历史是研究策略的状态，而不只是日志。",
                  PALE_ORANGE, ORANGE), PageBreak()]

    s += [p("4  三个任务如何统一", "h1"),
          table([["任务", "预测契约", "任务参考模型", "主指标"],
                 ["DTI", "compound + protein → interaction", "TAPB + frozen ESM2 protein features", "AUROC"],
                 ["Proteomics", "observed 6h/24h proteome + drug → efficacy", "ProteinTalks-derived efficacy head", "AP"],
                 ["VCC", "response + 5 single-gene options → identity", "corrected scDEBART head", "Macro Top-1"],
                 ["Norman", "response + 5 double-gene options → identity", "corrected scDEBART head", "Macro Top-1"],
                 ["Tahoe", "response + 5 drug options → identity", "scDEBART + Morgan conditioning", "Macro Top-1"]],
                [30*mm, 70*mm, 48*mm, 23*mm], font="tiny"), Spacer(1, 6*mm),
          callout("一致性",
                  "五个端点共享同一个 inner trainer、proposal schema、evidence card、研究历史和 finalizer；任务差异只通过 adapter 和 scorer 进入。主实验使用 seeds 42–44；反馈隔离实验在四个可完整重训的端点上统一使用 seeds 53–55。",
                  PALE_BLUE, BLUE), Spacer(1, 5*mm),
          p("六臂因子设计", "h2"),
          bullets([
              "参与度：1 个实验室 vs 10 个实验室。",
              "研究模式：fixed recipe vs feedback-free direct search vs feedback-guided loop。",
              "因此可以分别计算 participation、design search 和 feedback 三种效应。",
          ]), PageBreak()]

    s += [p("5  主结果", "h1"),
          table([["方法 / access", "DTI", "Protein", "VCC", "Norman", "Tahoe", "平均"],
                 ["Fixed (1 lab)", "82.83", "25.05", "29.94", "<b>25.56</b>", "19.40", "36.55"],
                 ["Direct (1 lab)", "89.89", "20.13", "21.09", "14.15", "15.42", "32.14"],
                 ["<b>AI4AI4Cell (10 labs)</b>", "<b>93.76</b>", "<b>36.99</b>", "<b>31.54</b>", "22.25", "<b>22.39</b>", "<b>41.39</b>"]],
                [42*mm, 21.5*mm, 21.5*mm, 21.5*mm, 21.5*mm, 21.5*mm, 21.5*mm],
                font="tiny", highlights=[(3, PALE_TEAL)]), Spacer(1, 4*mm),
          p("所有数值都是 held-out 三 seed 均值乘以 100。AI4AI4Cell 在五个主端点中的四个最高，五端点描述性均值为 41.39。Norman 的最高值来自单实验室 fixed recipe。", "note"),
          Spacer(1, 6*mm),
          callout("整体结论",
                  "完整系统在分子互作、蛋白响应和细胞扰动三类任务上都取得了有竞争力的结果；相对于单实验室 direct optimization，五个端点分别变化 +3.87、+16.85、+10.45、+8.10 和 +6.97 个百分点。",
                  PALE_TEAL, TEAL), PageBreak()]

    s += [p("6  Loop 是否真的有效", "h1"),
          table([["端点", "Direct", "Loop", "增益", "胜/平/负"],
                 ["DTI（开发轨迹回放）", "93.63", "94.02", "+0.39", "2/1/0"],
                 ["Proteomics（留出）", "37.47", "37.47", "+0.00", "0/3/0"],
                 ["VCC（留出）", "20.01", "20.01", "+0.00", "0/3/0"],
                 ["Norman（留出）", "11.48", "22.32", "<b>+10.84</b>", "3/0/0"],
                 ["Tahoe（留出）", "20.90", "22.89", "+1.99", "1/2/0"]],
                [49*mm, 29*mm, 29*mm, 32*mm, 32*mm], font="tiny",
                highlights=[(4, PALE_TEAL)]), Spacer(1, 5*mm),
          bullets([
              "Direct 与 loop 使用相同的十个设计、十个实验室和 160 次开发评估。",
              "Direct 为每个设计平均分配 80 轮；loop 先为十个设计各训练 20 轮，再将剩余预算集中到六个由当前得分和学习趋势共同提升的设计；两者总计都是 800 个全客户端训练轮。",
              "12 个新执行的留出 task-seed 对比为 4 胜、8 平、0 负。Norman 平均提升 10.84 点，95% CI 为 [4.54, 17.73]；Tahoe 平均提升 1.99 点，区间跨零。",
              "DTI 使用已有开发轨迹做保守回放：Direct 反而多 5 个 candidate-round，loop 仍为 2 胜、1 平；该行不作为新的留出结论。",
          ]), Spacer(1, 5*mm),
          callout("Loop 的实证结论",
                  "证据历史不仅用于记录实验，还能成为预算分配的控制信号：在固定候选、数据、评估次数和训练预算后，它能保留 uniform search 的最优解，并在需要更长训练才能显现优势的设计上带来显著提升。",
                  PALE_PURPLE, PURPLE), PageBreak()]

    s += [p("7  当前论文如何阅读", "h1"),
          table([["部分", "核心内容"],
                 ["Abstract / Introduction", "提出 collaborative biological research 问题，解释两层反馈与贡献。"],
                 ["Related Work", "把 AIDE、AI Scientist、DrugEvolve、协作训练、FedEx、Helmsman 放入统一坐标。"],
                 ["Method", "定义 task contract、proposal schema、inner trainer、evidence card 和 research history。"],
                 ["Experiments", "明确五个端点、模型、划分、指标与六臂比较。"],
                 ["Results", "主表回答完整系统水平；effect table 与 proposal-prefix 分析负责归因。"],
                 ["Appendix A", "完整 design library、proposal JSON、15 条轨迹、六臂结果、次指标与不确定性。"]],
                [43*mm, 128*mm]), Spacer(1, 6*mm),
          callout("目前最强的论文信息",
                  "同一套协作研究接口已经跨三个生物任务族完成训练、选择与 held-out 评价；完整系统在主表五个端点中的四个最高。进一步的同预算隔离实验得到 4 胜、8 平、0 负，并在 Norman 上取得 +10.84 点且置信区间为正的提升，证明 evidence-guided loop 可以实际改善计算预算的分配。",
                  PALE_ORANGE, ORANGE), Spacer(1, 6*mm),
          p("后续增强方向：独立实验室队列、client rotation、same-data centralized reference、更大的 compositional design space，以及 secure aggregation / differential privacy 部署层。", "body")]
    return s


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    Doc(str(OUT)).build(story())
    print(OUT)


if __name__ == "__main__":
    main()
