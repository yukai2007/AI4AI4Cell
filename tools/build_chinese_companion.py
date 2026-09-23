#!/usr/bin/env python3
"""Build a concise Chinese reading companion for the current manuscript."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import statistics
import tempfile

import fitz
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from fontTools import subset
from fontTools.ttLib import TTFont as SourceFont
from fontTools.varLib.instancer import instantiateVariableFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, PageBreak, PageTemplate, Paragraph,
    Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf" / "AI4AI4Cell_中文伴读版.pdf"
TMP = Path(tempfile.mkdtemp(prefix="ai4ai4cell-zh-pdf-"))


def main_score_rows():
    """Use actual seed scores, including paired-seed Overall dispersion."""
    data = json.loads((ROOT / 'tables/strong_v3/snapshot.json').read_text())
    tasks = ['native_tapb', 'ptpc_neural', 'vcc_corrected', 'norman_double_corrected', 'tahoe_drug_corrected']
    common = set.intersection(*(set(seed for seed, run in data['tasks'][task]['runs'].items()
                                    if run is not None) for task in tasks))
    rows = [["方法 / access", "DTI", "Protein", "VCC", "Norman", "Tahoe", "平均"]]
    numeric_means = []
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
        numeric_means.append([statistics.mean(samples) if samples else float('-inf') for samples in values])
    for column in range(len(tasks)+1):
        best = max(values[column] for values in numeric_means)
        for index, values in enumerate(numeric_means):
            if abs(values[column]-best) < 1e-12:
                rows[index+1][column+1] = f'<b>{rows[index+1][column+1]}</b>'
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

FONT_SOURCE = Path('/liziqing/yukai/.local/share/fonts/NotoSansSC-Variable.ttf')


def register_chinese_fonts():
    # Subset before instantiating to keep the generated PDF portable and small.
    # Dynamic table labels are ASCII; all Chinese prose lives in this source.
    source = SourceFont(FONT_SOURCE)
    subsetter = subset.Subsetter()
    subsetter.populate(unicodes=set(map(ord, Path(__file__).read_text())) | set(range(32, 127)))
    subsetter.subset(source)
    for name, weight in [('CompanionSC', 400), ('CompanionSC-Bold', 700)]:
        font = instantiateVariableFont(source, {'wght': weight}, inplace=False)
        # Distinct PostScript names prevent ReportLab from aliasing both
        # static instances to the variable font's original "Thin" face.
        names = {1: 'CompanionSC', 2: 'Bold' if weight == 700 else 'Regular',
                 3: f'CompanionSC-{weight}', 4: name, 6: name}
        for record in font['name'].names:
            if record.nameID in names:
                record.string = names[record.nameID].encode(record.getEncoding())
        font['OS/2'].usWeightClass = weight
        font['OS/2'].fsSelection = ((font['OS/2'].fsSelection & ~0x60)
                                   | (0x20 if weight == 700 else 0x40))
        font['head'].macStyle = ((font['head'].macStyle & ~1) | int(weight == 700))
        target = TMP / f'{name}.ttf'
        font.save(target)
        pdfmetrics.registerFont(TTFont(name, str(target)))
    pdfmetrics.registerFontFamily('CompanionSC', normal='CompanionSC', bold='CompanionSC-Bold',
                                 italic='CompanionSC', boldItalic='CompanionSC-Bold')


register_chinese_fonts()


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
            canvas.setFont("CompanionSC", 8)
            canvas.setFillColor(MUTED)
            canvas.drawString(17*mm, A4[1]-9.5*mm, "AI4AI4Cell 中文伴读版")
            canvas.drawRightString(A4[0]-17*mm, 9*mm, str(doc.page))
        canvas.restoreState()


STYLES = {
    "cover": ParagraphStyle("cover", fontName="CompanionSC", fontSize=28,
                            leading=39, textColor=NAVY, alignment=TA_CENTER),
    "subtitle": ParagraphStyle("subtitle", fontName="CompanionSC", fontSize=14,
                               leading=22, textColor=MUTED, alignment=TA_CENTER),
    "h1": ParagraphStyle("h1", fontName="CompanionSC", fontSize=20,
                         leading=29, textColor=NAVY, spaceAfter=10),
    "h2": ParagraphStyle("h2", fontName="CompanionSC", fontSize=13,
                         leading=20, textColor=BLUE, spaceBefore=6, spaceAfter=5),
    "body": ParagraphStyle("body", fontName="CompanionSC", fontSize=9.6,
                           leading=15.5, textColor=INK, wordWrap="CJK", spaceAfter=6),
    "small": ParagraphStyle("small", fontName="CompanionSC", fontSize=8.2,
                            leading=12.5, textColor=INK, wordWrap="CJK"),
    "tiny": ParagraphStyle("tiny", fontName="CompanionSC", fontSize=7.3,
                           leading=10.5, textColor=INK, wordWrap="CJK"),
    "center": ParagraphStyle("center", fontName="CompanionSC", fontSize=9.2,
                             leading=14, textColor=INK, alignment=TA_CENTER),
    "note": ParagraphStyle("note", fontName="CompanionSC", fontSize=8.4,
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


def figure(name, width_mm, source=None):
    TMP.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(source or ROOT / "assets" / f"{name}.pdf")
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(2.1, 2.1), alpha=False)
    target = TMP / f"zh_{name}.png"
    pix.save(target)
    ratio = pix.height / pix.width
    return Image(str(target), width=width_mm*mm, height=width_mm*ratio*mm)


TASKS = [('native_tapb', 'DTI'), ('ptpc_neural', 'PTPC'),
         ('vcc_corrected', 'VCC'), ('norman_double_corrected', 'Norman'),
         ('tahoe_drug_corrected', 'Tahoe')]


def completed_review():
    """Validate the publication aggregate against its sealed input receipts."""
    path = ROOT / 'tables/completed_ablation/snapshot.json'
    data = json.loads(path.read_text())
    for relative, expected in data['source_sha256'].items():
        source = ROOT.parent / relative
        actual = hashlib.sha256(source.read_bytes()).hexdigest()
        assert actual == expected, f'Completed-ablation input changed: {relative}'
    delivery_path = ROOT.parent / 'results/tonight_completion_20260923/final_delivery/summary.json'
    delivery = json.loads(delivery_path.read_text())
    assert delivery['status'] == 'COMPLETE' and not delivery['pending_groups']
    assert not delivery['third_external_proteomics_source_complete']
    assert len(data['laboratory']) == 10
    assert {r['task'] for r in data['laboratory']} == {t for t, _ in TASKS}
    assert all(set(r['by_k']) == {'1', '2', '5', '10'} for r in data['laboratory'])
    for protocol, count in [('short6', 10), ('long24', 8)]:
        runs = [r for r in data['loops'] if r['protocol'] == protocol]
        assert len(runs) == count
        assert len({(r['task'], r['backend']) for r in runs}) == count
    assert not any(r['task'] == 'native_tapb' for r in data['loops'] if r['protocol'] == 'long24')
    return data, hashlib.sha256(path.read_bytes()).hexdigest()


def display_samples(samples, signed=False):
    values = [100*x for x in samples]
    mean = statistics.mean(values)
    result = f'{mean:+.2f}' if signed else f'{mean:.2f}'
    return result + f' ± {statistics.stdev(values):.2f}' if len(values)>1 else result


def protocol_runs(data, protocol):
    rank = {task: i for i, (task, _) in enumerate(TASKS)}
    return sorted([r for r in data['loops'] if r['protocol'] == protocol],
                  key=lambda r: (rank[r['task']], r['backend']))


def final_prefix(run):
    return next(r for r in run['prefixes'] if r['budget'] == run['slots'])


def paired_counts(runs):
    delta = [final_prefix(r)['loop_minus_direct_pp'] for r in runs]
    return {'positive': sum(x>1e-10 for x in delta),
            'tie': sum(abs(x)<=1e-10 for x in delta),
            'negative': sum(x < -1e-10 for x in delta)}


def backend_validity(runs, backend):
    rows = [r for r in runs if r['backend'] == backend]
    valid = sum(r['modes'][m]['valid'] for r in rows for m in ('direct', 'loop'))
    total = sum(2*r['slots'] for r in rows)
    return valid, total


def sensitivity_pages(data, core):
    """Five readable pages from the completed publication snapshot."""
    s = [p('7  实验室数：参与度与分区分开看', 'h1'),
         p('五个端点都已完成 K=1、2、5、10 的两种设置。默认设计与 100 轮训练保持固定；DTI 为 seed 61，四个轻任务为 seeds 61-63 的均值 ± 样本标准差。分数均乘以 100。', 'body')]
    for family, title, explanation in [
            ('participation', '参与度：增加实验室，也增加可用数据',
             '使用原始十份分区中的前 K 份；这是更多实验室愿意参与时，实际获得更多训练数据的情景。'),
            ('partition', '固定全池：总数据相同，仅改变 K 个训练组',
             '将全部目标训练数据重分为 K 组，保留原始十个开发面板等权评价。这里 K=1 使用全部数据，不是主表仅一份数据的单实验室。')]:
        rows = [['端点 / 指标', 'K=1', 'K=2', 'K=5', 'K=10']]
        for r in data['laboratory']:
            if r['family'] == family:
                rows.append([f"{r['label']} / {r['metric']}",
                             *[display_samples(r['by_k'][str(k)]) for k in (1, 2, 5, 10)]])
        s += [p(title, 'h2'), p(explanation, 'note'),
              table(rows, [43*mm, 32*mm, 32*mm, 32*mm, 32*mm], font='tiny'), Spacer(1, 3*mm)]
    norman = next(r for r in data['laboratory'] if r['task']=='norman_double_corrected' and r['family']=='partition')
    s += [callout('K 不是越大越好',
                 f"Norman 固定全池 K=1 的均值为 {100*statistics.mean(norman['by_k']['1']):.2f}，K=10 为 {100*statistics.mean(norman['by_k']['10']):.2f}。分区改变本地优化以及细胞任务的对比学习负样本池；更多数据与更多训练分区是不同机制。因此需要同时保留两类 K 曲线。", PALE_ORANGE, ORANGE), PageBreak()]

    source_rows = [['目标', '附加独立来源', '分数', '相对 target-only']]
    for r in data['independent_transfer']:
        source_rows.append([r['task'].replace(' auxiliary', '辅助'), r['label'],
                            display_samples(r['scores']), display_samples(r['deltas'], True)])
    low, high = core['transfer_uncertainty']['cell']['intervals']['plus_jiang']['delta_percentile95']
    contexts = next(r for r in data['context_transfer'] if r['case']=='plus_all')
    context_base = next(r for r in data['context_transfer'] if r['case']=='target_only')
    s += [p('8  不同来源的数据能否增益目标任务', 'h1'),
          p('DTI 使用 3 个独立来源，VCC 使用 3 项独立研究；蛋白组新增共享编码器 pilot 使用 Lin、Ruprecht 两项独立研究。所有来源条件及其组合均保留。分数为同一目标留出集的 AUROC（DTI）、macro Top-1（VCC）或 AP（PTPC），均乘以 100。', 'body'),
          table(source_rows, [30*mm, 49*mm, 44*mm, 48*mm], font='tiny'), Spacer(1, 3*mm),
          p(f'DTI：Davis / Human 为正向点估计，BioSNAP 与三源组合下降。VCC：Jiang 提升 3.58 点，但扰动簇 bootstrap 95% CI 为 [{low:.2f}, {high:.2f}]；三源合并下降 2.15 点。来源兼容性比简单堆叠来源更重要。', 'small'),
          p('蛋白组：新增共享编码器及来源专属 head，保留目标原有十客户端，外源各为独立客户端；连续 viability / EC50 不改成目标二分类标签。只与同架构 target-only 配对。Ruprecht 提升 0.52 AP 点，药物簇 95% CI 为 [-1.46, 2.64]；四组两槽位 Luna pilot 的 loop-minus-fixed 均为 0。DTI / cell 跨源实验则把目标全池作为一个客户端。', 'small'),
          p(f"同研究背景迁移另列：mtPTDS 的三个细胞背景不是三个独立研究。全部加入时 AP 从 {display_samples(context_base['scores'])} 变为 {display_samples(contexts['scores'])}；配对区间 [{contexts['ci_pp'][0]:.2f}, {contexts['ci_pp'][1]:.2f}]。decryptE 尚未参与训练，因此独立蛋白来源数仍为 2。", 'note'), PageBreak()]

    short = protocol_runs(data, 'short6')
    counts = paired_counts(short)
    short_rows = [['端点 / 后端', 'Fixed', 'Direct@6', 'Loop@6', 'Loop - Direct']]
    for run in short:
        fixed = next(r for r in run['prefixes'] if r['budget']==0)['direct_heldout_primary']
        end = final_prefix(run)
        short_rows.append([f"{dict(TASKS)[run['task']]} / {run['backend'].title()}", f'{100*fixed:.2f}',
                           f"{100*end['direct_heldout_primary']:.2f}", f"{100*end['loop_heldout_primary']:.2f}",
                           f"{end['loop_minus_direct_pp']:+.2f}"])
    rate_rows = [['提案后端', '有效槽位 / 总槽位', '有效率']]
    for backend in ('qwen', 'luna'):
        valid, total = backend_validity(short, backend)
        rate_rows.append([backend.title(), f'{valid} / {total}', f'{100*valid/total:.1f}%'])
    s += [p('9  双后端短预算：五个端点已跑齐', 'h1'),
          p('同一原始 12 设计菜单、6 个提案槽位、每候选 100 轮。Direct 不接收开发反馈，loop 接收历史证据；双方均使用十个实验室。DTI 为 seed 42，其余四端点为 seed 61。这里是单 seed 机制实验，不替换主表三 seed 结果。', 'body'),
          table(short_rows, [51*mm, 29*mm, 30*mm, 30*mm, 31*mm], font='small'), Spacer(1, 4*mm),
          callout('实验完成后的直接答案',
                  f"十个成对终点为 {counts['positive']} 项提升、{counts['negative']} 项下降、{counts['tie']} 项持平。Norman/Luna 提升 0.81 点，DTI/Luna 下降 0.33 点。该计数描述当前任务-后端单 seed 结果，不是显著性检验。", PALE_BLUE, BLUE),
          Spacer(1, 3*mm), table(rate_rows, [51*mm, 73*mm, 47*mm], font='small'),
          Spacer(1, 3*mm), p('有效率按快照重新计算，排除初始 fixed 配方，语法失败仍消耗提案槽位；它度量执行可靠性，不等价于预测质量。Luna 指实际使用的 gpt-5.6-luna API 后端，不推测未披露的参数规模。', 'note'),
          p('预先记录 0、1、2、4、6 槽位前缀；完整前缀、开发轨迹和每次设计变更均在英文附录 B。DTI 的 20 个前缀分数已从相同 5,505 对测试样本的预测独立重算。', 'note'), PageBreak()]

    long = protocol_runs(data, 'long24')
    counts = paired_counts(long)
    long_rows = [['端点 / 后端', 'Direct@24', 'Loop@24', '共同开发目标<br/>首次 D / L', '有效槽位<br/>D / L']]
    for run in long:
        end = final_prefix(run)
        modes = run['modes']
        first = ' / '.join('--' if modes[m]['first_common_target'] is None else str(modes[m]['first_common_target']) for m in ('direct', 'loop'))
        valid = ' / '.join(str(modes[m]['valid']) for m in ('direct', 'loop'))
        long_rows.append([f"{dict(TASKS)[run['task']]} / {run['backend'].title()}",
                          f"{100*end['direct_heldout_primary']:.2f}", f"{100*end['loop_heldout_primary']:.2f}", first, valid])
    rates = []
    for backend in ('qwen', 'luna'):
        valid, total = backend_validity(long, backend)
        rates.append(f'{backend.title()} {valid}/{total} = {100*valid/total:.1f}%')
    s += [p('10  长预算：何时搜索有效，何时饱和', 'h1'),
          p('36 设计菜单、24 槽位、100 轮候选训练，四个轻任务 × 两后端均为 seed 61；DTI 未运行该协议。它与短预算的菜单不同，不能把二者当作只改变 loop 次数的直接消融。预算影响应看同一轨迹内的预设前缀。', 'body'),
          table(long_rows, [46*mm, 28*mm, 28*mm, 38*mm, 31*mm], font='tiny'), Spacer(1, 3*mm),
          p(f"最终留出结果为 {counts['positive']} 项提升、{counts['negative']} 项下降、{counts['tie']} 项持平。Norman/Luna 的 loop 在第 4 槽达到共同开发目标，direct 第 22 槽才到，但最终均为 23.11；Tahoe/Luna 则是 direct 更快（5 对 13）。共同目标取双方最终开发主分数较小者，即双方均能达到的目标；更高终点的到达记录另存，不混比。", 'small'),
          figure('completed_budget_examples', 171), Spacer(1, 2*mm),
          p('图左为 Norman、图右为 VCC 的开发轨迹，均保留 Qwen/Luna 的 direct/loop 四条曲线。另看完整留出前缀：VCC/Qwen 的测试 Top-1 从第 6 槽 31.50 降至第 24 槽 19.61；开发分数变好不必然带来最终测试提升。', 'note'),
          p('有效提案：' + '；'.join(rates) + '。曲线平台期只表示有限预算内不再改善，不是数学收敛；所有预设测试前缀均保留，不按测试高点截断。', 'note'), PageBreak()]

    s += [p('11  完成范围与剩余工作', 'h1'),
          table([['实验组', '当前覆盖', '可以回答的问题'],
                 ['主表与六臂对照', '5 端点，seeds 42-44，完成', '完整系统、参与度和设计搜索'],
                 ['固定候选预算分配', '4 轻任务，seeds 53-55，完成', '早期轨迹如何分配同等训练预算'],
                 ['双后端短预算', '5 端点 × Qwen/Luna，10 对，完成', '六槽位内提案反馈的独立影响'],
                 ['双后端长预算', '4 轻任务 × Qwen/Luna，8 对，完成', '有限预算搜索动态；不含 DTI'],
                 ['实验室 K 两种设置', '5 端点 × 4 档 × 2 设置，完成', '更多数据与固定数据分区的差异'],
                 ['DTI / cell 独立来源', 'DTI 3 源；VCC 3 源，完成', '目标数据不变时外部研究的影响'],
                 ['Protein 独立来源 pilot', 'Lin、Ruprecht 两源，完成', '新共享编码器上的匹配来源迁移'],
                 ['未计入本次完成范围', '第三蛋白源 decryptE 未训练；DTI long24 未做；更多 seed 待扩展', '不填估计值，不计为独立重复']],
                [42*mm, 65*mm, 64*mm], font='small'), Spacer(1, 5*mm),
          callout('论文中三种不同的证据',
                  '完整系统结果回答整体工作流是否有用；固定候选 racing 回答证据是否改善算力分配；双后端 short6 / long24 回答 LLM 提案历史是否带来更好的搜索或终点。Norman 的 +10.84 点属于固定候选预算分配对照，不能移作提案反馈在所有任务均有效的结论。',
                  PALE_PURPLE, PURPLE), Spacer(1, 4*mm),
          p('本轮定义好的可运行实验矩阵已经完成并复核。更多 seed、DTI 长预算和第三蛋白源属于扩展范围；“完成矩阵”不意味着已经获得所有场景一致的 loop 增益，或所有外源组合的正迁移。', 'body'),
          p('本稿所有新增表均来自与英文附录 B 相同的 completed_ablation 出版快照；与原主实验分开报告，不混合不同任务指标、模型架构或候选菜单计算新的平均优势。', 'note'), PageBreak()]
    return s

def annotation_page():
    return [p('12  师姐批注如何落实', 'h1'),
            p('原 PDF 共 29 个标记，其中 24 条有文字意见；相邻空白高亮与便笺共同定位修改位置。以下按写作问题归并说明，逐项原文保留在批注记录中。', 'body'),
            table([['意见类型', '这次修改', '阅读位置'],
                   ['动机与定义太跳跃', '先说明反复提案、实验和设计改进的需要；定义 client 为实验室计算 worker，再讲内外循环。', 'Introduction'],
                   ['computational changes 太抽象', '具体到预测头、学习率、正则化和聚合设置；分别解释参数拟合与设计决策。', 'Introduction / Method'],
                   ['贡献不能泛称已有 harness', '贡献聚焦历史证据打包、提案反馈和按学习轨迹分配验证预算；两类决策分开验证。', 'Method / Results 5.2'],
                   ['相关工作分类与引用', '分 collaborative learning 与 AI for AI in bio 两部分；逐项核对引用，并区分任务模型与研究控制器。', 'Related work / 引用审计'],
                   ['方法层级与技术细节混杂', '方法先给输入、模块、流程、输出和核心 loop；去掉步骤式正文，训练细节与 JSON schema 移至附录。', 'Method / Appendix A'],
                   ['主图存在不存在的数据、固定10和指标', '范式图只保留实际可用数据；方法图使用用户提供的可编辑架构图，保留原文字，图注说明实验的10对应一般K。', 'Figures 1-2'],
                   ['主表基线名不清楚', '使用 Task model / Qwen direct，表注写明 TAPB、ProteinTalks-derived 与 scDEBART；生物预测来自任务模型。', 'Main table'],
                   ['效果表不知道检验什么', '改为明确的问题：早期证据能否改善训练分配？列名 Uniform / Evidence-guided；DTI 开发回放移至附录。', 'Results 5.2'],
                   ['Discussion 与结尾冗长', '归并为简洁 Conclusion；复现、伦理与 AI 使用声明分开；附录 B 更新已完成的K、独立来源、双后端及预算分析。', 'Conclusion / Statements / B']],
                  [36*mm, 101*mm, 34*mm], font='small'),
            Spacer(1, 5*mm),
            callout('修改后的叙述口径',
                    '积极陈述已经得到的结果，并把每个结果对应到实际实验。完整系统优势、固定候选训练分配收益、LLM 提案效率、来源迁移和执行可靠性分别讲清楚，不互相替代。',
                    PALE_PURPLE, PURPLE), PageBreak()]


def story():
    core, _ = core_review()
    completed, completed_sha = completed_review()
    s = [Spacer(1, 38*mm), p("AI4AI4Cell 中文伴读版", "cover"),
         p("协作式证据引导的生物模型改进", "subtitle"), Spacer(1, 12*mm),
         callout("核心问题",
                 "多个生物实验室拥有互补数据。AI4AI4Cell 让这些数据在本地参与两件事：一是训练共享预测模型，二是为外层研究循环评价和选择下一版可执行设计。",
                 PALE_TEAL, TEAL), Spacer(1, 10*mm),
         table([["任务族", "主端点", "实验配置", "随机种子"],
                ["DTI / 蛋白组学 / 细胞扰动", "5", "六配置对照，已完成", "42 / 43 / 44"],
                ["蛋白组学 / 3 类细胞扰动", "4", "同预算训练分配，已完成", "53 / 54 / 55"],
                ["K / 独立来源 / 双后端", "见附录 B", "本轮实验矩阵已完成", "DTI short:42；其余见表"]],
               [55*mm, 32*mm, 45*mm, 39*mm]), Spacer(1, 12*mm),
         p("对应英文稿：2026-09-23 已完成消融修订版", "center"),
         p("正文六节 + 附录 A/B；本文件用于快速伴读，不替代英文全文。", "center"),
         p(f"附录 B 同源快照 SHA-256：{completed_sha[:16]}…", "note"), PageBreak()]

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

    s += [p("3  架构总览", "h1"),
          figure('user_framework', 171,
                 ROOT / 'figures/framework_user_20260923_readable_original_labels.pdf'),
          Spacer(1, 4*mm),
          p("架构图使用用户提供的可编辑原图，仅修复字体与文字框排版，保留原文字。图中的 10 个实验室对应当前实验实例；一般方法使用 K 个参与实验室。", "note"),
          callout("读图顺序",
                  "上方外层由研究模型提出、实例化、评价和修订设计；中部各实验室执行本地参数拟合，协调器聚合更新与开发诊断；下方显示三个任务族及输出。研究模型本身保持固定，反馈用于下一轮可执行设计。",
                  PALE_BLUE, BLUE), PageBreak(),
          p("3  Harness 外层到底做什么（续）", "h1"),
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
                  "五个端点共享同一个 inner trainer、proposal schema、evidence card、研究历史和 finalizer；任务差异只通过 adapter 和 scorer 进入。主实验使用 seeds 42-44；固定候选预算分配实验在四个轻任务上使用 seeds 53-55；双后端提案反馈的单 seed 配置另列。",
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

    s += sensitivity_pages(completed, core)
    s += annotation_page()
    s += [p("13  当前论文如何阅读", "h1"),
          table([["部分", "核心内容"],
                 ["Abstract / Introduction", "提出 collaborative biological research 问题，解释两层反馈与贡献。"],
                 ["Related Work", "把 AIDE、AI Scientist、DrugEvolve、协作训练、FedEx、Helmsman 放入统一坐标。"],
                 ["Method", "定义 task contract、proposal schema、inner trainer、evidence card 和 research history。"],
                 ["Experiments", "明确五个端点、模型、划分、指标与六臂比较。"],
                 ["Results", "5.1 完整系统；5.2 固定候选预算分配；5.3 实验室数与独立来源；5.4 研究模型与搜索预算。"],
                 ["Conclusion", "概括已验证贡献，并说明来源兼容性、分区与反馈泛化的研究方向。"],
                 ["Appendix A", "完整 design library、proposal JSON、优化设置、六配置结果、次指标与不确定性。"],
                 ["Appendix B", "已完成 K、独立来源、双后端短/长预算、全部前缀曲线、设计变更与有效提案率。"]],
                [43*mm, 128*mm]), Spacer(1, 6*mm),
          callout("目前最强的论文信息",
                  "主比较已完整：同一套研究接口跨三个生物任务族完成训练与评价，完整系统领先所展示的五个端点中的四个。固定候选的同预算实验在 Norman 上给出 +10.84 点的正向证据。新的敏感性实验同时揭示了分区影响、负迁移以及开发选择不一定转化为测试增益；这些事实构成对机制的进一步分析。",
                  PALE_ORANGE, ORANGE), Spacer(1, 6*mm),
          p("当前写作已吸收师姐对逻辑、方法层级、模型名称、图示及段落结构的意见。本轮可运行消融矩阵已经完成；更多 seed、DTI long24 与第三独立蛋白源未计入完成范围。投稿前仍需共同确认贡献表述、来源迁移的统计精度，以及单 seed 提案反馈结果的解释。", "body"),
          p("复现 / 伦理 / AI 使用声明分别说明实验材料、数据本地边界及 AI 辅助范围。多机构真实部署仍需明确的安全与隐私方案；本研究没有新增受试者或湿实验。", "note")]
    return s


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    bound_snapshot = ROOT / 'tables/completed_ablation/snapshot.json'
    before_sha = hashlib.sha256(bound_snapshot.read_bytes()).hexdigest()
    rendered = TMP / 'companion.pdf'
    Doc(str(rendered)).build(story())
    completed, snapshot_sha = completed_review()
    assert snapshot_sha == before_sha, 'Publication snapshot changed during rendering; rerun cleanly'
    inputs = [ROOT / 'tables/strong_v3/snapshot.json',
              ROOT / 'tables/core_review/snapshot.json',
              ROOT / 'tables/completed_ablation/snapshot.json',
              ROOT.parent / 'results/tonight_completion_20260923/final_delivery/summary.json',
              ROOT.parent / 'results/proteomics_external_pilot_20260923/RESULT.zh-CN.md',
              ROOT / 'assets/paradigm_comparison.pdf',
              ROOT / 'assets/completed_budget_examples.pdf',
              ROOT / 'figures/framework_user_20260923_readable_original_labels.pdf']
    with fitz.open(rendered) as document:
        page_count = len(document)
    provenance = {
        'schema': 'ai4ai4cell-chinese-companion-v2',
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'embedded_font_source_sha256': hashlib.sha256(FONT_SOURCE.read_bytes()).hexdigest(),
        'input_sha256': {str(path.relative_to(ROOT.parent)): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in inputs},
        'publication_snapshot_sha256': snapshot_sha,
        'verified_source_receipts': len(completed['source_sha256']),
        'paired_terminal_signs': {protocol: paired_counts(protocol_runs(completed, protocol))
                                  for protocol in ('short6', 'long24')},
        'valid_proposal_counts': {protocol: {backend: backend_validity(protocol_runs(completed, protocol), backend)
                                            for backend in ('qwen', 'luna')}
                                  for protocol in ('short6', 'long24')},
        'page_count': page_count,
        'output_sha256': hashlib.sha256(rendered.read_bytes()).hexdigest(),
        'uncompleted_extensions': ['additional seeds', 'DTI long24', 'third independent protein source decryptE'],
        'original_results_modified': False,
    }
    # Stage the generated artifacts beside their targets before atomic rename.
    # A failed render/source check/quota write must not truncate the last PDF.
    outputs = [(OUT, rendered.read_bytes()),
               (OUT.with_suffix('.provenance.json'),
                (json.dumps(provenance, ensure_ascii=False, indent=2)+'\n').encode())]
    staged = []
    try:
        for path, payload in outputs:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.zh-companion-', delete=False) as f:
                staged.append((Path(f.name), path))
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
        for temporary, target in staged:
            temporary.replace(target)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)
    print(OUT)
    print(json.dumps({'pages': page_count, 'terminal_signs': provenance['paired_terminal_signs']}, ensure_ascii=False))


if __name__ == "__main__":
    main()
