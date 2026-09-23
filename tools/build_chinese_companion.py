#!/usr/bin/env python3
"""Build a concise Chinese reading companion for the current manuscript."""
from pathlib import Path
import hashlib
import json
import statistics

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


def main_score_rows():
    """Use actual seed scores, including paired-seed Overall dispersion."""
    data = json.loads((ROOT / 'tables/strong_v3/snapshot.json').read_text())
    tasks = ['native_tapb', 'ptpc_neural', 'vcc_corrected', 'norman_double_corrected', 'tahoe_drug_corrected']
    common = set.intersection(*(set(seed for seed, run in data['tasks'][task]['runs'].items()
                                    if run is not None) for task in tasks))
    rows = [["方法 / access", "DTI", "Protein", "VCC", "Norman", "Tahoe", "平均"]]
    for arm, label in [('single_fixed', 'Task model (1 lab)'), ('single_direct', 'Qwen direct (1 lab)'),
                       ('federated_loop', '<b>AI4AI4Cell (10 labs)</b>')]:
        values = [[100*run['scores'][arm]['primary'] for run in data['tasks'][task]['runs'].values()
                   if run is not None] for task in tasks]
        values.append([100*statistics.mean(data['tasks'][task]['runs'][seed]['scores'][arm]['primary']
                                           for task in tasks) for seed in sorted(common)])
        cells = []
        for samples in values:
            if not samples:
                cells.append('N/A')
            else:
                sd = f'{statistics.stdev(samples):.2f}' if len(samples)>1 else 'N/A'
                cells.append(f'{statistics.mean(samples):.2f} ± {sd}')
        rows.append([label, *cells])
    return rows


def core_review():
    """Read the same frozen, verified aggregate snapshot as English Appendix B."""
    path = ROOT / 'tables/core_review/snapshot.json'
    data = json.loads(path.read_text())
    assert data['verification_sha256'] and data['studies']
    return data, hashlib.sha256(path.read_bytes()).hexdigest()


def studies(data, prefix, task=None, backend=None):
    return [s for s in data['studies']
            if s['relative_path'].startswith(prefix)
            and (task is None or s['task'] == task)
            and (backend is None or f'/{backend}/' in s['relative_path'])]


def score_mean(rows, key):
    values = [100*s['scores'][key]['primary'] for s in rows]
    return statistics.mean(values) if values else None


def score_cell(rows, key, dispersion=True):
    values = [100*s['scores'][key]['primary'] for s in rows]
    if not values:
        return 'N/A'
    mean = f'{statistics.mean(values):.2f}'
    return mean + f' ± {statistics.stdev(values):.2f}' if dispersion and len(values)>1 else mean


def valid_slots(data, rows, mode):
    events = [r for s in rows for r in data['curves'][s['relative_path']]
              if r['mode'] == mode and r['slot'] > 0]
    return sum(bool(r['valid']) for r in events), len(events)


def first_best_slot(data, task, backend, mode, seed='seed61'):
    rows = [r for r in studies(data, 'model_loop/', task, backend) if r['seed'] == seed]
    assert len(rows) == 1, 'This explanatory case names a single completed seed'
    events = [r for r in data['curves'][rows[0]['relative_path']] if r['mode'] == mode]
    best = max(r['primary'] for r in events)
    return min(r['slot'] for r in events if r['primary'] == best)

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
    cooked = [[p(f'<font color="#FFFFFF">{cell}</font>' if index == 0 else str(cell), font)
               for cell in row] for index, row in enumerate(rows)]
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


def sensitivity_pages(data):
    """Two pages from Appendix B's frozen snapshot, never live partial runs."""
    names = [('ptpc_neural', 'PTPC'), ('vcc_corrected', 'VCC'),
             ('norman_double_corrected', 'Norman'), ('tahoe_drug_corrected', 'Tahoe')]
    lab_rows = [['固定全池，默认配方', 'K=1', 'K=2', 'K=5', 'K=10']]
    for task, label in names:
        runs = studies(data, 'lab_count/', task)
        lab_rows.append([label, *[score_cell(runs, f'partition_k{k}') for k in (1, 2, 5, 10)]])
    norman = studies(data, 'lab_count/', 'norman_double_corrected')
    cell_sources = studies(data, 'cross_source/cell/')
    protein_sources = studies(data, 'cross_source/proteomics/')
    source_rows = [['VCC 来源设置', 'Top-1', '差值', '配对 95% CI']]
    for key, label in [('target_only', '仅目标数据'), ('plus_replogle', '+ Replogle'),
                       ('plus_nadig', '+ Nadig'), ('plus_jiang', '+ Jiang'), ('plus_all', '+ 全部三项研究')]:
        difference = score_mean(cell_sources, key) - score_mean(cell_sources, 'target_only')
        low, high = data['transfer_uncertainty']['cell']['intervals'][key]['delta_percentile95']
        source_rows.append([label, score_cell(cell_sources, key, False),
                            f'{difference:+.2f}', f'[{low:.2f}, {high:.2f}]'])
    jiang_delta = score_mean(cell_sources, 'plus_jiang') - score_mean(cell_sources, 'target_only')
    s = [p('7  敏感性：实验室数与数据来源', 'h1'),
         p('这两组实验使用默认配方，不替换主表的搜索协议。参与度实验把原始前 K 个客户端加入训练，数据量随 K 增加；固定全池实验把全部数据合并成 K 个训练组，保持原始十个开发面板等权评价。', 'body'),
         table(lab_rows, [43*mm, 32*mm, 32*mm, 32*mm, 32*mm], font='tiny', highlights=[(3, PALE_ORANGE)]),
         Spacer(1, 3*mm),
         p(f"Norman 全池数据放入一个客户端时为 {score_cell(norman, 'partition_k1', False)}，拆成十个客户端时为 {score_cell(norman, 'partition_k10', False)}。这里的 K=1 使用全部目标训练数据，不是主表只有一份数据的单实验室基线。分组同时改变局部优化步骤及细胞任务的 contrastive negative pool，所以 K 的效果并不单调。", 'note'),
         p('异源更新是否有用？', 'h2'),
         table(source_rows, [57*mm, 34*mm, 28*mm, 52*mm], font='small'),
         Spacer(1, 3*mm),
         p(f'Jiang 的三种子点估计提高 {jiang_delta:.2f} 点，但按目标扰动重采样的区间跨零；全部来源同时加入反而下降。VCC 的三个来源属于独立研究，这组结果强调来源兼容性，而非来源越多越好。', 'body'),
         p(f"蛋白组：目标全池 AP 为 {score_cell(protein_sources, 'target_only', False)}，加入全部 mtPTDS 细胞背景后为 {score_cell(protein_sources, 'plus_all', False)}。这些来源是同一研究中的三个背景，不是三个独立研究。全部来源组合的差值 95% CI 为 [{data['transfer_uncertainty']['proteomics']['intervals']['plus_all']['delta_percentile95'][0]:.2f}, {data['transfer_uncertainty']['proteomics']['intervals']['plus_all']['delta_percentile95'][1]:.2f}]。", 'note'),
         p('完整 More-data 与 Fixed-pool 对照、每个来源、样本标准差与不确定性见英文附录 B；缺失的 DTI 评价保留 N/A。', 'note'), PageBreak()]

    loop_rows = [['任务 / proposer', '完成', 'Direct@6 / Loop@6', 'Direct@24 / Loop@24', '有效提案 D / L']]
    task_names = [('native_tapb', 'DTI'), *names]
    for task, label in task_names:
        for backend, proposer in [('qwen', 'Qwen'), ('luna', 'Luna')]:
            runs = studies(data, 'model_loop/', task, backend)
            paired = [f'{score_cell(runs, f"direct_b{budget}", False)} / {score_cell(runs, f"loop_b{budget}", False)}'
                      for budget in (6, 24)]
            counts = [valid_slots(data, runs, mode) for mode in ('direct', 'loop')]
            valid = ' / '.join(f'{a}/{b}' for a, b in counts) if runs else 'N/A'
            loop_rows.append([f'{label} / {proposer}', f'{len(runs)}/3', *paired, valid])
    norman_luna = [r for r in studies(data, 'model_loop/', 'norman_double_corrected', 'luna') if r['seed'] == 'seed61']
    luna_direct = first_best_slot(data, 'norman_double_corrected', 'luna', 'direct')
    luna_loop = first_best_slot(data, 'norman_double_corrected', 'luna', 'loop')
    validity = {}
    for backend in ('qwen', 'luna'):
        rows = studies(data, 'model_loop/', backend=backend)
        pieces = [valid_slots(data, rows, mode) for mode in ('direct', 'loop')]
        validity[backend] = tuple(sum(values) for values in zip(*pieces))
    qvalid, qtotal = validity['qwen']; lvalid, ltotal = validity['luna']
    lab_count = len(studies(data, 'lab_count/'))
    source_count = len(studies(data, 'cross_source/'))
    loop_count = len(studies(data, 'model_loop/'))
    differences = [r['scores']['loop_b24']['primary'] - r['scores']['direct_b24']['primary']
                   for r in studies(data, 'model_loop/')]
    wins = sum(d > 1e-12 for d in differences)
    ties = sum(abs(d) <= 1e-12 for d in differences)
    losses = sum(d < -1e-12 for d in differences)
    s += [p('8  提案预算、执行可靠性与完成状态', 'h1'),
          p('两后端使用相同 36 配置空间与 24 个提案槽位；槽位失败也计入预算。每个有效候选从共同初始化训练 100 轮。以下只纳入完整跑完 24 槽位并已验证的轨迹；一条 job 同时包含 direct 与 loop。', 'body'),
          table(loop_rows, [31*mm, 15*mm, 42*mm, 43*mm, 40*mm], font='tiny'),
          Spacer(1, 3*mm),
          p(f"Norman seed 61：Luna 使用反馈时在第 {luna_loop} 槽达到共同开发目标，direct 在第 {luna_direct} 槽才达到；但 24 槽位测试终点均为 {score_cell(norman_luna, 'loop_b24', False)}。Tahoe/Luna 则是 direct 更早达到共同目标（5 对 13 槽）。全部完整 job 的最终测试对照为 loop {wins} 胜、{ties} 平、{losses} 负；这是描述计数，不是独立显著性检验。搜索更快、开发曲线变平和最终测试增益应分别讨论。", 'body'),
          p(f'已完成轨迹的有效提案：Qwen {qvalid}/{qtotal} = {100*qvalid/qtotal:.1f}%；Luna {lvalid}/{ltotal} = {100*lvalid/ltotal:.1f}%。分母排除初始 fixed 配方，仅计实际提案槽位。两种后端不能假定拥有相同的解码控制；Luna 的参数规模没有被此接口披露。', 'note'),
          callout('已完成不等于整个扩展研究完成',
                  f'冻结快照中：K 实验 {lab_count}/15 个任务-种子，跨源 {source_count}/9 个目标-种子，提案研究 {loop_count}/30 个任务-种子-后端已完成并验证。DTI 与其余种子的未完成评价保留 N/A。主表 seeds 42-44 及四任务 racing seeds 53-55 已完成；新研究单独报告，不覆盖主表。',
                  PALE_ORANGE, ORANGE),
          Spacer(1, 3*mm), p('状态来自与英文附录 B 相同的已验证出版快照，并非实时队列或估计得分。', 'note'), PageBreak()]
    return s


def annotation_page():
    return [p('9  师姐批注如何落实', 'h1'),
            p('原 PDF 共 29 个标记，其中 24 条有文字意见；相邻空白高亮与便笺共同定位修改位置。以下按写作问题归并说明，逐项原文保留在批注记录中。', 'body'),
            table([['意见类型', '这次修改', '阅读位置'],
                   ['动机与定义太跳跃', '先说明反复提案、实验和设计改进的需要；定义 client 为实验室计算 worker，再讲内外循环。', 'Introduction'],
                   ['computational changes 太抽象', '具体到预测头、学习率、正则化和聚合设置；分别解释参数拟合与设计决策。', 'Introduction / Method'],
                   ['贡献不能泛称已有 harness', '贡献聚焦历史证据打包、提案反馈和按学习轨迹分配验证预算；两类决策分开验证。', 'Method / Results 5.2'],
                   ['相关工作分类与引用', '分 collaborative learning 与 AI for AI in bio 两部分；逐项核对引用，并区分任务模型与研究控制器。', 'Related work / 引用审计'],
                   ['方法层级与技术细节混杂', '方法先给输入、模块、流程、输出和核心 loop；去掉步骤式正文，训练细节与 JSON schema 移至附录。', 'Method / Appendix A'],
                   ['主图存在不存在的数据、固定10和指标', '集中式图只保留可用数据；框架用 K labs；任务示意不塞指标；统一语义配色与无交叉走线。', 'Figures 1-2'],
                   ['主表基线名不清楚', '使用 Task model / Qwen direct，表注写明 TAPB、ProteinTalks-derived 与 scDEBART；生物预测来自任务模型。', 'Main table'],
                   ['效果表不知道检验什么', '改为明确的问题：早期证据能否改善训练分配？列名 Uniform / Evidence-guided；DTI 开发回放移至附录。', 'Results 5.2'],
                   ['Discussion 与结尾冗长', '归并为简洁 Conclusion；复现、伦理与 AI 使用声明分开；新增附录 B 明确已完成与 N/A。', 'Conclusion / Statements / B']],
                  [36*mm, 101*mm, 34*mm], font='small'),
            Spacer(1, 5*mm),
            callout('修改后的叙述口径',
                    '积极陈述已经得到的结果，并把每个结果对应到实际实验。完整系统优势、固定候选训练分配收益、LLM 提案效率、来源迁移和执行可靠性分别讲清楚，不互相替代。',
                    PALE_PURPLE, PURPLE), PageBreak()]


def story():
    core, core_sha = core_review()
    s = [Spacer(1, 38*mm), p("AI4AI4Cell 中文伴读版", "cover"),
         p("协作式证据引导的生物模型改进", "subtitle"), Spacer(1, 12*mm),
         callout("核心问题",
                 "多个生物实验室拥有互补数据。AI4AI4Cell 让这些数据在本地参与两件事：一是训练共享预测模型，二是为外层研究循环评价和选择下一版可执行设计。",
                 PALE_TEAL, TEAL), Spacer(1, 10*mm),
         table([["任务族", "主端点", "实验配置", "随机种子"],
                ["DTI / 蛋白组学 / 细胞扰动", "5", "六配置对照，已完成", "42 / 43 / 44"],
                ["蛋白组学 / 3 类细胞扰动", "4", "同预算训练分配，已完成", "53 / 54 / 55"],
                ["参与度 / 来源 / 提案预算", "见附录 B", "按完成记录报告", "61 / 62 / 63"]],
               [55*mm, 32*mm, 45*mm, 39*mm]), Spacer(1, 12*mm),
         p("对应英文稿：2026-09-22 师姐批注修订版", "center"),
         p("正文六节 + 附录 A/B；本文件用于快速伴读，不替代英文全文。", "center"),
         p(f"附录 B 同源快照 SHA-256：{core_sha[:16]}…", "note"), PageBreak()]

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
                 ["证据引导的 loop 机制", "把提案结果打包为可复用历史；把早期学习轨迹用于后续训练分配。这两类作用分别验证。"],
                 ["跨任务实证", "共享训练与研究接口，并用匹配预算、参与度、来源和提案预算分析解释效果。"]],
                [42*mm, 129*mm]), PageBreak()]

    s += [p("2  三种研究范式", "h1"), figure("paradigm_comparison", 171),
          Spacer(1, 3*mm),
          p("绿色表示本地数据，蓝色表示预测模型，紫色表示研究 harness，橙色表示聚合与门控。K 是参与实验室数，不固定为 10。灰色虚线 harness 表示图中的固定设计配置，并非断言所有已有协作学习工作都没有 agent。集中式面板仅画实际可访问的数据源。", "note"),
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
                 ["5. Next proposal", "完整有序研究历史", "利用前轮结果形成下一假设；是否有效由独立对照检验"]],
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
                  PALE_ORANGE, ORANGE), Spacer(1, 3*mm),
          p("Qwen direct 始终接收固定起始配方及未尝试的 design_id，不接收开发反馈；loop 接收当前保留配置和完整历史。二者的首个提案相同。", "note"), PageBreak()]

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
          p("六配置因子对照", "h2"),
          bullets([
              "参与度：1 个实验室 vs 10 个实验室。",
              "研究模式：fixed recipe vs feedback-free direct search vs feedback-guided loop。",
              "主表比较完整系统；因子对照分别估计参与度、设计搜索和提案反馈的差异。",
          ]), PageBreak()]

    s += [p("5  主结果", "h1"),
          table(main_score_rows(),
                [42*mm, 21.5*mm, 21.5*mm, 21.5*mm, 21.5*mm, 21.5*mm, 21.5*mm],
                font="tiny", highlights=[(3, PALE_TEAL)]), Spacer(1, 4*mm),
          p("当前主表为已完成的 3 个 seed：held-out 均值 ± 样本标准差，均乘以 100。标准差反映固定数据划分上的训练／搜索波动，不是标准误或置信区间；总体分先按每个 seed 平均五项指标，再计算标准差。新增重复实验尚未计入。AI4AI4Cell 在五个主端点中的四个最高，五端点描述性均值为 41.39。Norman 的最高值来自单实验室 fixed recipe。", "note"),
          Spacer(1, 6*mm),
          callout("整体结论",
                  "完整系统在分子互作、蛋白响应和细胞扰动三类任务上都取得了有竞争力的结果；相对于单实验室 direct optimization，五个端点分别变化 +3.87、+16.85、+10.45、+8.10 和 +6.97 个百分点。",
                  PALE_TEAL, TEAL), PageBreak()]

    s += [p("6  证据如何改进训练预算分配", "h1"),
          p("先区分两个实验：主实验的 LLM 提案反馈决定下一次尝试什么设计；本页的固定候选 racing 则决定哪些设计值得继续训练。后者固定十个设计，不依赖 LLM 生成新设计。", "body"),
          table([["端点", "均匀分配", "证据分配", "增益", "胜/平/负"],
                 ["Proteomics（留出）", "37.47", "37.47", "+0.00", "0/3/0"],
                 ["VCC（留出）", "20.01", "20.01", "+0.00", "0/3/0"],
                 ["Norman（留出）", "11.48", "22.32", "<b>+10.84</b>", "3/0/0"],
                 ["Tahoe（留出）", "20.90", "22.89", "+1.99", "1/2/0"]],
                [49*mm, 29*mm, 29*mm, 32*mm, 32*mm], font="tiny",
                highlights=[(3, PALE_TEAL)]), Spacer(1, 5*mm),
          bullets([
              "均匀分配与证据分配使用相同的十个设计、十个实验室和 160 次开发评估。",
              "均匀分配给每个设计 80 轮；证据分配先各训练 20 轮，按当前得分及上升趋势选出六个设计，从共同初始化重新训练 100 轮；两者总计都是 800 个全客户端训练轮。",
              "12 个新执行的留出 task-seed 对比为 4 胜、8 平、0 负。Norman 平均提升 10.84 点，95% CI 为 [4.54, 17.73]；Tahoe 平均提升 1.99 点，区间跨零。",
              "DTI 仅有已有开发轨迹回放：均匀分配 525、证据分配 520 个 candidate-round，开发 AUROC 相差 +0.39 点（2 胜、1 平），单列于附录 A。",
          ]), Spacer(1, 5*mm),
          callout("已经得到的机制结论",
                  "早期证据可以改善训练预算的分配，Norman 上三个种子均受益。它不等于 LLM 提案历史已经带来独立的最终分数增益：原六槽位主实验的 direct 与 loop 选中了相同终点；更大预算的提案研究见下一部分。",
                  PALE_PURPLE, PURPLE), PageBreak()]

    s += sensitivity_pages(core)
    s += annotation_page()
    s += [p("10  当前论文如何阅读", "h1"),
          table([["部分", "核心内容"],
                 ["Abstract / Introduction", "提出 collaborative biological research 问题，解释两层反馈与贡献。"],
                 ["Related Work", "把 AIDE、AI Scientist、DrugEvolve、协作训练、FedEx、Helmsman 放入统一坐标。"],
                 ["Method", "定义 task contract、proposal schema、inner trainer、evidence card 和 research history。"],
                 ["Experiments", "明确五个端点、模型、划分、指标与六臂比较。"],
                 ["Results", "5.1 完整系统；5.2 固定候选预算分配；5.3 实验室数、来源和搜索预算敏感性。"],
                 ["Conclusion", "概括已验证贡献，并说明来源兼容性、分区与反馈泛化的研究方向。"],
                 ["Appendix A", "完整 design library、proposal JSON、优化设置、六配置结果、次指标与不确定性。"],
                 ["Appendix B", "K/跨来源/双后端的原始指标、有效提案率及明确的完成/待跑状态。"]],
                [43*mm, 128*mm]), Spacer(1, 6*mm),
          callout("目前最强的论文信息",
                  "主比较已完整：同一套研究接口跨三个生物任务族完成训练与评价，完整系统领先所展示的五个端点中的四个。固定候选的同预算实验在 Norman 上给出 +10.84 点的正向证据。新的敏感性实验同时揭示了分区影响、负迁移以及开发选择不一定转化为测试增益；这些事实构成对机制的进一步分析。",
                  PALE_ORANGE, ORANGE), Spacer(1, 6*mm),
          p("当前写作已吸收师姐对逻辑、方法层级、模型名称、图示及段落结构的意见。尚未完成的实验不填估计分数，按附录 B 保留 N/A；整体投稿准备程度还取决于剩余实验、所有引用和最终全文核验。", "body"),
          p("复现 / 伦理 / AI 使用声明分别说明实验材料、数据本地边界及 AI 辅助范围。多机构真实部署仍需明确的安全与隐私方案；本研究没有新增受试者或湿实验。", "note")]
    return s


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    Doc(str(OUT)).build(story())
    print(OUT)


if __name__ == "__main__":
    main()
