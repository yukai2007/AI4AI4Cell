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
    BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate, Paragraph,
    Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf" / "BioCoLoop_中文伴读版.pdf"
TMP = Path(tempfile.mkdtemp(prefix="biocoloop-zh-pdf-"))


def main_score_rows():
    """Display task-specific references and never average heterogeneous metrics."""
    data = json.loads((ROOT / 'tables/strong_v3/snapshot.json').read_text())
    tasks = ['native_tapb', 'ptpc_neural', 'vcc_corrected', 'norman_double_corrected', 'tahoe_drug_corrected']
    rows = [["方法 / 数据范围", "DTI<br/>AUROC", "Protein<br/>AP",
             "VCC<br/>Top-1", "Norman<br/>Top-1", "Tahoe<br/>Top-1"]]
    definitions = [
        ('single_fixed', 'TAPB (1 lab)', {0}),
        ('single_fixed', 'ProteinTalks-derived head (1 lab)', {1}),
        ('single_fixed', 'scDEBART head (1 lab)', {2, 3, 4}),
        ('single_direct', 'Qwen direct (1 lab)', set(range(5))),
        ('federated_loop', '<b>BioCoLoop (10 labs)</b>', set(range(5))),
    ]
    numeric = []
    for arm, label, columns in definitions:
        cells, means = [], []
        for index, task in enumerate(tasks):
            values = [100*run['scores'][arm]['primary'] for run in data['tasks'][task]['runs'].values()
                      if run is not None] if index in columns else []
            means.append(statistics.mean(values) if values else None)
            if values:
                sd = f'{statistics.stdev(values):.2f}' if len(values)>1 else 'N/A'
                cells.append(f'{statistics.mean(values):.2f} ± {sd}')
            else:
                cells.append('—')
        rows.append([label, *cells])
        numeric.append(means)
    for column in range(len(tasks)):
        rank = sorted({row[column] for row in numeric if row[column] is not None}, reverse=True)
        for index, values in enumerate(numeric):
            if values[column] is None:
                continue
            if abs(values[column]-rank[0]) < 1e-12:
                rows[index+1][column+1] = f'<b>{rows[index+1][column+1]}</b>'
            elif len(rank)>1 and abs(values[column]-rank[1]) < 1e-12:
                rows[index+1][column+1] = f'<u>{rows[index+1][column+1]}</u>'
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
                         bottomMargin=16*mm, title="BioCoLoop 中文伴读版",
                         subject="BioCoLoop: Collaborative Agentic Research for Biological Model Improvement")
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
            canvas.drawString(17*mm, A4[1]-9.5*mm, "BioCoLoop 中文伴读版")
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
    # Preserve this closed historical batch; supplemental coverage is read separately.
    assert len(data['laboratory']) == 10
    assert {r['task'] for r in data['laboratory']} == {t for t, _ in TASKS}
    assert all(set(r['by_k']) == {'1', '2', '5', '10'} for r in data['laboratory'])
    for protocol, count in [('short6', 10), ('long24', 8)]:
        runs = [r for r in data['loops'] if r['protocol'] == protocol]
        assert len(runs) == count
        assert len({(r['task'], r['backend']) for r in runs}) == count
    assert not any(r['task'] == 'native_tapb' for r in data['loops'] if r['protocol'] == 'long24')
    return data, hashlib.sha256(path.read_bytes()).hexdigest()


PROTEOMICS_SUPPLEMENT = ROOT.parent / 'results/supplemental_20260923/proteomics/seed61_slots0_cpu'


def proteomics_supplement():
    """Load verified aggregate scores; do not rescore or select held-out predictions."""
    receipt = PROTEOMICS_SUPPLEMENT / 'independent_rescore.json'
    data = json.loads(receipt.read_text())
    assert data['status'] == 'COMPLETE_VERIFIED'
    assert data['fixed_design_only'] and data['proposal_slots'] == 0
    assert data['independent_auxiliary_studies'] == 3
    assert data['rounds'] == 100 and data['seed'] == 61 and data['n_target_rows'] == 148
    assert set(data['results']) == {'target_only_fixed', 'plus_decrypte_fixed',
                                   'plus_existing2_fixed', 'plus_all3_fixed'}
    for name, key in [('definition.json', 'definition_sha256'), ('heldout/results.json', 'results_sha256')]:
        assert hashlib.sha256((PROTEOMICS_SUPPLEMENT / name).read_bytes()).hexdigest() == data[key]
    assert all(r['max_absolute_error'] == 0 and r['prediction_sha256'] and r['checkpoint_sha256']
               for r in data['results'].values())
    return data, hashlib.sha256(receipt.read_bytes()).hexdigest()


def supplemental_protein_page(data):
    rows = [['来源配置', 'AP ×100', 'AUROC ×100', 'AP 相对目标单独训练']]
    baseline = data['results']['target_only_fixed']['metrics']['ap']
    comparison_means = []
    for key, label in [('target_only_fixed', '仅目标 ProteinTalks'),
                       ('plus_decrypte_fixed', '+ decryptE'),
                       ('plus_existing2_fixed', '+ Lin + Ruprecht'),
                       ('plus_all3_fixed', '+ Lin + Ruprecht + decryptE')]:
        metrics = data['results'][key]['metrics']
        comparison_means.append((metrics['ap'], metrics['auroc']))
        rows.append([label, f"{100*metrics['ap']:.2f}", f"{100*metrics['auroc']:.2f}",
                     f"{100*(metrics['ap']-baseline):+.2f}"])
    for metric, column in ((0, 1), (1, 2)):
        best = max(values[metric] for values in comparison_means)
        for row, values in enumerate(comparison_means):
            if abs(values[metric]-best) < 1e-12:
                rows[row+1][column] = f'<b>{rows[row+1][column]}</b>'
    contrast = data['paired_point_estimate_contrasts']
    all_gain = contrast['plus_all3_fixed_minus_target_only_fixed']['ap_percentage_points']
    added_gain = contrast['plus_all3_fixed_minus_plus_existing2_fixed']['ap_percentage_points']
    return [p('8.3  三个独立蛋白来源：新补实验', 'h1'),
            p('Lin、Ruprecht、decryptE 是三项独立辅助研究。本节保留 ProteinTalks 目标的十个训练片，各外源再对应一个模拟实验室；最多为 13 个训练实验室，而不是每个研究只对应一个实验室。共享编码器吸收不同测量信息，各来源保留自己的预测头和损失；严格的一来源一实验室设置见第 8.4 节。四个配置使用相同设计、seed 61 和 100 轮训练，并在同一目标开发集上选 checkpoint。', 'body'),
            table(rows, [67*mm, 29*mm, 31*mm, 44*mm], highlights=[(4, PALE_TEAL)]),
            Spacer(1, 5*mm),
            callout('已经完成的第三来源结果',
                    f'加入三个辅助来源后，目标 AP 相对 target-only 提高 {all_gain:.2f} 点；相对已有 Lin + Ruprecht 两源提高 {added_gain:.2f} 点。decryptE 单独加入的 AP 变化较小，组合结果提示其信息可能与已有来源互补。',
                    PALE_TEAL, TEAL),
            Spacer(1, 4*mm),
            p('该补实验已全部完成，并根据 148 个目标测试条件的冻结预测独立重算。表内保留 AP 与 AUROC：三源组合提高主指标 AP，而 AUROC 略低于 target-only，因此“增益”具体指 AP 的点估计。', 'body'),
            p('本次使用 slots=0，检验固定模型设计下的来源迁移；研究 LLM 的历史反馈另设对照。已有双来源 Luna 两槽位 pilot 与本次三来源固定设计实验分开报告。多 seed 以及三来源条件下的提案历史对照可进一步量化稳定性和交互作用。', 'note'),
            PageBreak()]


SCENARIO_SUPPLEMENT = ROOT.parent / 'results/scenario_labs_20260923'


def scenario_review():
    """Read completed source-as-laboratory aggregates and verify their seal chain."""
    base = SCENARIO_SUPPLEMENT
    campaign = json.loads((base / 'completion_v2.json').read_text())
    data = json.loads((base / 'heldout/independent_rescore_v2.json').read_text())
    protocol = json.loads((base / 'protocol.json').read_text())
    results = json.loads((base / 'heldout/results.json').read_text())
    seal = json.loads((base / 'heldout/seal.json').read_text())
    digest = lambda name: hashlib.sha256((base / name).read_bytes()).hexdigest()
    assert campaign['status'] == 'COMPLETE' and data['status'] == 'PASS'
    assert data['prediction_only_rescore']
    assert campaign['validated_fit_count'] == 12
    assert campaign['independent_rescore_sha256'] == digest('heldout/independent_rescore_v2.json')
    assert data['original_campaign_sha256'] == campaign['original_campaign_sha256'] == digest('campaign.json')
    assert data['protocol_sha256'] == digest('protocol.json')
    assert data['results_sha256'] == digest('heldout/results.json')
    assert results['seal_sha256'] == digest('heldout/seal.json')
    assert seal['protocol_sha256'] == campaign['protocol_sha256'] == digest('protocol.json')
    assert protocol['seeds'] == [61, 62, 63] and protocol['rounds'] == 100
    keys = ('target15_k1', 'target60_k1', 'same_source60_k4', 'cross_scenario60_k4')
    assert set(data['arms']) == set(protocol['arms']) == set(keys)
    assert len(data['scores']) == 12
    for arm in keys:
        values = [data['scores'][f'seed{seed}/{arm}']['macro_accuracy'] for seed in (61, 62, 63)]
        recorded = data['arms'][arm]
        assert len(recorded['per_seed']) == 3
        assert all(abs(x-y) < 1e-12 for x, y in zip(values, recorded['per_seed']))
        assert abs(statistics.mean(values)-recorded['mean']) < 1e-12
        assert abs(statistics.stdev(values)-recorded['sample_std']) < 1e-12
    delta = [x-y for x, y in zip(data['arms']['cross_scenario60_k4']['per_seed'],
                                data['arms']['same_source60_k4']['per_seed'])]
    assert abs(statistics.mean(delta)-data['matched_k4_n60_delta']['mean']) < 1e-12
    return data, digest('heldout/independent_rescore_v2.json')


def scenario_page(data):
    rows = [['训练组成', 'K', '干预数', 'Top-1 (%)', 'MRR ×100']]
    comparison_means = []
    for arm, label, k, count in [
            ('target15_k1', '目标来源的 15 个锚点', 1, 15),
            ('target60_k1', '目标来源的全部 60 条件', 1, 60),
            ('same_source60_k4', '同一目标来源分成 4 组', 4, 60),
            ('cross_scenario60_k4', '目标与 3 个外源各 15 条件', 4, 60)]:
        entry = data['arms'][arm]
        mrr = [data['scores'][f'seed{seed}/{arm}']['mrr'] for seed in (61, 62, 63)]
        comparison_means.append((entry['mean'], statistics.mean(mrr)))
        rows.append([label, str(k), str(count),
                     f"{100*entry['mean']:.2f} ± {100*entry['sample_std']:.2f}",
                     f"{100*statistics.mean(mrr):.2f} ± {100*statistics.stdev(mrr):.2f}"])
    for metric, column in ((0, 3), (1, 4)):
        best = max(values[metric] for values in comparison_means)
        for row, values in enumerate(comparison_means):
            if abs(values[metric]-best) < 1e-12:
                rows[row+1][column] = f'<b>{rows[row+1][column]}</b>'
    delta = 100*data['matched_k4_n60_delta']['mean']
    mrr_delta = 100*statistics.mean(
        data['scores'][f'seed{seed}/cross_scenario60_k4']['mrr'] -
        data['scores'][f'seed{seed}/same_source60_k4']['mrr'] for seed in (61, 62, 63))
    return [p('8.2  实验室即数据场景：四臂受控比较', 'h1'),
            p('以 VCC 单基因扰动识别为目标，保留相同的 15 个目标锚点条件。额外 45 个训练条件可以来自原目标来源，也可以分别来自 Replogle/K562、Nadig/HepG2 和 Jiang/IFNB/K562。所有条件共享原 scDEBART 预测头初始化、固定设计和 100 轮训练；目标原有开发面板选择 checkpoint。', 'body'),
            table(rows, [65*mm, 14*mm, 20*mm, 36*mm, 36*mm]),
            Spacer(1, 5*mm),
            callout('这组对照分别回答什么',
                    '15→60 个目标条件：更多目标训练条件的作用；同样 60 个目标条件由 1→4 个实验室持有：分区的作用；同样 K=4、N=60 时改为四种场景：来源组成的作用。这里 N 统计训练干预条件；原始细胞数与基因面板不属于这项配对约束。',
                    PALE_BLUE, BLUE),
            Spacer(1, 4*mm),
            p(f'在 K=4、N=60 的主配对对照中，跨场景相对同源分区的 macro Top-1 均值变化为 {delta:+.2f} 个百分点。MRR 变化为 {mrr_delta:+.2f} 点。所有四臂使用 seeds 61–63，在同一 20 个目标干预、360 个查询上评价；表中为均值 ± 样本标准差。', 'body'),
            p('这项实验将不同研究或生物背景直接对应为实验室。匹配条件数与实验室数后，多源组合的 Top-1 仍低于同源对照，说明来源的任务适配性需要单独评价。它检验固定设计的来源迁移，不能替代 LLM 历史反馈对照。跨场景三个 seed 对应不同 checkpoint，交叉熵略有不同，但 Top-1/MRR 汇总相同；离散排序指标没有区分出这些较小的预测变化。', 'note'),
            PageBreak()]


STRICT_PROTEOMICS = ROOT.parent / 'results/proteomics_scenario_labs_20260924'


def strict_proteomics_review():
    """Verify the completed one-training-worker-per-study protein comparison."""
    base = STRICT_PROTEOMICS
    read = lambda name: json.loads((base / name).read_text())
    digest = lambda name: hashlib.sha256((base / name).read_bytes()).hexdigest()
    status, protocol, receipt = read('status.json'), read('protocol.json'), read('independent_rescore.json')
    arms = ('target_only', 'plus_decrypte', 'plus_existing2', 'plus_all3')
    assert status['status'] == 'COMPLETE' and receipt['status'] == 'PASS'
    assert tuple(status['completed_arms']) == arms and set(receipt['results']) == set(arms)
    assert status['seed'] == protocol['seed'] == 61
    assert status['rounds'] == protocol['rounds'] == 100
    assert status['proposal_slots'] == protocol['proposal_slots'] == 0
    assert status['cpu_only'] and status['gpu_hours'] == status['api_calls'] == 0
    assert protocol['target_dev_panels'] == list(range(10))
    assert status['protocol_sha256'] == receipt['protocol_sha256'] == digest('protocol.json')
    assert status['results_sha256'] == receipt['results_sha256'] == digest('heldout/results.json')
    assert receipt['seal_sha256'] == digest('heldout/seal.json')
    assert status['binding_sha256'] == digest('binding.json')
    assert status['independent_rescore_sha256'] == digest('independent_rescore.json')
    assert receipt['all_four_arms'] and receipt['manual_prediction_level_rescore']
    for arm, k, n in zip(arms, (1, 2, 3, 4), (386, 881, 491, 986)):
        assert protocol['arms'][arm]['K'] == k and protocol['arms'][arm]['n_train'] == n
        assert len(protocol['arms'][arm]['studies']) == len(protocol['arms'][arm]['worker_ids']) == k
        row = receipt['results'][arm]
        assert 0 <= row['max_absolute_error'] <= 1e-12
        assert row['predictions_sha256'] and row['checkpoint_sha256']
        assert all(0 <= row['metrics'][metric] <= 1 for metric in ('ap', 'auroc'))
    return {'verification': receipt, 'protocol': protocol, 'status': status}, digest('independent_rescore.json')


def strict_proteomics_page(study):
    receipt, protocol, status = study['verification'], study['protocol'], study['status']
    rows = [['参与研究', '实验室数', '训练条件', 'AP ×100', 'AUROC ×100']]
    points = []
    for arm, label in [('target_only', '仅目标 ProteinTalks'),
                       ('plus_decrypte', '+ decryptE'),
                       ('plus_existing2', '+ Lin + Ruprecht'),
                       ('plus_all3', '+ Lin + Ruprecht + decryptE')]:
        config, metrics = protocol['arms'][arm], receipt['results'][arm]['metrics']
        points.append((metrics['ap'], metrics['auroc']))
        rows.append([label, str(config['K']), str(config['n_train']),
                     f"{100*metrics['ap']:.2f}", f"{100*metrics['auroc']:.2f}"])
    for metric, column in ((0, 3), (1, 4)):
        best = max(values[metric] for values in points)
        for row, values in enumerate(points):
            if abs(values[metric]-best) < 1e-12:
                rows[row+1][column] = f'<b>{rows[row+1][column]}</b>'
    ap_gain = 100*(points[-1][0]-points[0][0])
    auroc_gain = 100*(points[-1][1]-points[0][1])
    return [p('8.4  严格按研究来源定义实验室', 'h1'),
            p('本节让每个训练实验室与一个研究来源一一对应：把 ProteinTalks 的 386 个目标训练条件合并到一个实验室；Lin、Ruprecht、decryptE 各自对应一个独立实验室。四种配置因此对应 K=1、2、3、4，不再把目标研究拆成十个训练实验室。各来源共享编码器，并保留自己的预测头和损失。', 'body'),
            table(rows, [66*mm, 22*mm, 27*mm, 28*mm, 28*mm], highlights=[(4, PALE_TEAL)]),
            Spacer(1, 5*mm),
            callout('按来源协作后的实际增益',
                    f"全部三个外源参与后，目标 AP 从 {100*points[0][0]:.2f} 提高到 {100*points[-1][0]:.2f}，增加 {ap_gain:.2f} 点；AUROC 从 {100*points[0][1]:.2f} 提高到 {100*points[-1][1]:.2f}，增加 {auroc_gain:.2f} 点。",
                    PALE_TEAL, TEAL),
            Spacer(1, 4*mm),
            p('四臂均使用 seed 61、固定配置和 100 轮训练。目标原有十个开发面板保持不变并等权选择 checkpoint；最终在同一 148 个目标测试条件上评价。训练实验室数与开发面板数因此是两个独立定义的量。', 'body'),
            p('这组对照回答新增独立实验室及其数据参与时，是否能改善目标预测器。K 与训练条件数随参与一起增加；固定总数据下的分区效应另见第 7 节。8.3 保留目标的十个训练片，本节合并为一个来源实验室，两种协议分别配对，不能交叉混算增益。', 'body'),
            p(f"本次四臂已训练并独立重算通过，CPU 墙钟耗时 {status['wall_seconds']:.2f} 秒，GPU 和 API 使用均为 0。proposal_slots=0：这些数值证明当前单 seed 的固定设计来源迁移效果，不计作 LLM 提案反馈的收益。", 'note'),
            PageBreak()]


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


def sensitivity_pages(data, core, supplement, scenario, strict_protein):
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

    s += [p('7  参与度与搜索反馈：图示', 'h1'),
          figure('laboratory_sensitivity_v2', 171), Spacer(1, 2*mm),
          p('上：实线增加参与实验室与可用训练数据；虚线固定全部数据，仅改变分区。测试 K=1、2、5、10 按类别等距显示；各任务的合适 K 不同。', 'small'),
          figure('completed_short6_search', 143), Spacer(1, 2*mm),
          p('下：预设提案前缀的开发指标与留出指标。Qwen/Luna 的 direct 与 loop 分开画，显示反馈对搜索路径的影响；相同终点说明不同路径最终选择了相同预测器。具体数值和分析见第 9 部分。', 'note'),
          PageBreak()]

    source_rows = [['目标', '附加独立来源', '分数', '相对 target-only']]
    for r in data['independent_transfer']:
        source_rows.append([r['task'].replace(' auxiliary', '辅助'), r['label'],
                            display_samples(r['scores']), display_samples(r['deltas'], True)])
    low, high = core['transfer_uncertainty']['cell']['intervals']['plus_jiang']['delta_percentile95']
    contexts = next(r for r in data['context_transfer'] if r['case']=='plus_all')
    context_base = next(r for r in data['context_transfer'] if r['case']=='target_only')
    s += [p('8.1  不同来源的数据能否增益目标任务', 'h1'),
          p('DTI 使用 3 个独立来源，VCC 使用 3 项独立研究；蛋白组先用 Lin、Ruprecht 进行共享编码器 pilot，并已补齐 decryptE 第三独立来源。所有来源条件及其组合均保留。分数为同一目标留出集的 AUROC（DTI）、macro Top-1（VCC）或 AP（PTPC），均乘以 100。', 'body'),
          table(source_rows, [30*mm, 49*mm, 44*mm, 48*mm], font='tiny'), Spacer(1, 3*mm),
          p(f'DTI：Davis / Human 为正向点估计，BioSNAP 与三源组合下降。VCC：Jiang 提升 3.58 点，但扰动簇 bootstrap 95% CI 为 [{low:.2f}, {high:.2f}]；三源合并下降 2.15 点。来源兼容性比简单堆叠来源更重要。', 'small'),
          p('蛋白组：新增共享编码器及来源专属 head，保留目标原有十个实验室，外源各对应独立实验室；连续 viability / EC50 不改成目标二分类标签。只与同架构 target-only 配对。Ruprecht 提升 0.52 AP 点，药物簇 95% CI 为 [-1.46, 2.64]；四组两槽位 Luna pilot 的 loop-minus-fixed 均为 0。DTI / cell 跨源实验则把目标全池作为一个实验室的数据。', 'small'),
          p(f"同研究背景迁移另列：mtPTDS 的三个细胞背景不是三个独立研究。全部加入时 AP 从 {display_samples(context_base['scores'])} 变为 {display_samples(contexts['scores'])}；配对区间 [{contexts['ci_pp'][0]:.2f}, {contexts['ci_pp'][1]:.2f}]。这三个背景属于同研究的不同场景；三独立来源的固定设计对照见第 8.3 节；严格按研究来源定义实验室的结果见第 8.4 节。", 'note'), PageBreak()]

    s += scenario_page(scenario)
    s += supplemental_protein_page(supplement)
    s += strict_proteomics_page(strict_protein)

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
                 ['同源与跨场景受控对照', 'VCC 4 臂 × 3 seeds，完成', '分开控制条件数、实验室数和来源组成'],
                 ['Protein 独立来源', 'Lin、Ruprecht pilot + 三来源固定设计，完成', '共享编码器及来源专属 head 的目标迁移'],
                 ['Protein 严格来源实验室', '4 臂，K=1/2/3/4，seed 61，完成', '每个训练实验室对应一项真实研究'],
                 ['后续扩展', 'DTI long24 未做；更多 seed 待扩展', '扩大预算与独立重复']],
                [42*mm, 65*mm, 64*mm], font='small'), Spacer(1, 5*mm),
          callout('已验证的收益与进一步的机制分析',
                  '协作访问与证据驱动训练分配分别获得受控实验支持：前者在相同提案策略下改善五个端点，后者在 Norman 上实现同预算 +10.84 点。双后端 short6 / long24 进一步分析 LLM 提案历史对搜索路径与最终选择的影响。三类实验各有明确作用；训练分配的收益属于证据闭环，但不是提案历史的收益。',
                  PALE_PURPLE, PURPLE), Spacer(1, 4*mm),
          p('本轮主表、实验室数、双后端短预算与轻任务长预算均已完成；第三独立蛋白来源及严格一来源一训练实验室的四臂对照也已补齐。结果支持按任务和来源选择研究策略：不同来源的互补性、搜索路径与最终泛化需要分别分析。DTI 长预算与更多 seed 仍属后续扩展；“8 卡 × 1 天”的已执行结果范围不包含尚未运行的 DTI 24-slot 扩展。', 'body'),
          p('既有消融与英文附录 B 共享 completed_ablation 出版快照；第三蛋白来源使用独立复核 receipt。各协议分别报告，主表不把不同含义的指标合成 Overall。', 'note'), PageBreak()]
    return s

GROUPED_HARNESS_SNAPSHOT = ROOT / 'tables/public_harness_comparison/snapshot_llm_grouped_three_seed.json'
GROUPED_TASKS = (('native_tapb', 'DTI AUROC'), ('ptpc_neural', 'PTPC AP'),
                 ('vcc_corrected', 'VCC Top-1'), ('norman_double_corrected', 'Norman Top-1'),
                 ('tahoe_drug_corrected', 'Tahoe Top-1'))
GROUPED_METHODS = (('single_fixed', '固定配方（1 lab）'), ('single_direct', 'direct（1 lab）'),
                   ('ai_scientist_v2', 'AI-Scientist-v2（1 lab）'),
                   ('ai_researcher', 'AI-Researcher（1 lab）'),
                   ('federated_loop', '<b>BioCoLoop</b>（10 labs）'))
GROUPED_MODELS = (('qwen', 'Qwen2.5-7B-Instruct'), ('luna', 'GPT-5.6 Luna（low reasoning）'))
GROUPED_TOKENS = (('ctx', 'F_ctx'), ('svc', 'F_svc'), ('tool', 'F_tool'), ('pipe', 'F_pipe'))


def grouped_token_label(token):
    for key, label in GROUPED_TOKENS:
        if key in token:
            return label
    return token


def grouped_cell(record):
    """Render one controller cell without imputing an unsealed selection.

    Mirrors the English main table: a partial cell keeps its mean and SD with a
    dagger, an endpoint with no scored run shows a dash, and every completed
    count and typed failure is listed in the note below the block.
    """
    if not record.get('complete'):
        if not record.get('completed'):
            return '–'
        value = f"{100*record['mean']:.2f}"
        if record.get('sd') is not None:
            value += f" ± {100*record['sd']:.2f}"
        return value + ' †'
    return f"{100*record['mean']:.2f} ± {100*record['sd']:.2f}"


def grouped_harness_page():
    """Grouped Qwen2.5/GPT-5.6 Luna public-controller comparison from the frozen snapshot."""
    snapshot = json.loads(GROUPED_HARNESS_SNAPSHOT.read_text())
    protocol = snapshot['protocol']
    flow = [
        p("5（续）公开 harness 基线：Qwen2.5 与 GPT-5.6 Luna 双模型对照", "h1"),
        p(f"英文 4.3 节的主表把两个公开科研框架的任务适配版本纳入同一协议，使用 seeds "
          f"{'–'.join(map(str, protocol['seeds']))}。AI-Scientist-v2 与 AI-Researcher 保留各自的原生科研控制流程"
          "（实验管理、树搜索与评审，以及 idea 选择、规划、实现与迭代分析），但接入与 BioCoLoop 相同的"
          f"生物拟合和留出评分服务。两个公开框架只访问实验室 {protocol['public_controller_laboratories']}，"
          f"BioCoLoop 使用十个实验室；同一模型块内的所有行共享 {protocol['designs']} 设计库、至多 "
          f"{protocol['candidate_cap']} 个候选提案、每个有效候选 {protocol['candidate_rounds']} 轮训练和同一个"
          "留出评分器。", "body"),
    ]
    for model, label in GROUPED_MODELS:
        rows = [['方法'] + [name for _, name in GROUPED_TASKS]]
        ranking = {}
        for task, _ in GROUPED_TASKS:
            complete = sorted({round(100 * snapshot['models'][model][task][method]['mean'], 2)
                               for method, _ in GROUPED_METHODS
                               if snapshot['models'][model][task][method].get('complete')},
                              reverse=True)
            ranking[task] = complete
        for method, method_label in GROUPED_METHODS:
            row = [method_label]
            for task, _ in GROUPED_TASKS:
                record = snapshot['models'][model][task][method]
                shown = grouped_cell(record)
                if record.get('complete'):
                    rounded = round(100 * record['mean'], 2)
                    if rounded == ranking[task][0]:
                        shown = f"<b>{shown}</b>"
                    elif len(ranking[task]) > 1 and rounded == ranking[task][1]:
                        shown = f"<u>{shown}</u>"
                row.append(shown)
            rows.append(row)
        flow += [p(f"{label} 块", "h2"),
                 table(rows, [45*mm, 25.2*mm, 25.2*mm, 25.2*mm, 25.2*mm, 25.2*mm],
                       font="tiny", highlights=[(5, PALE_TEAL)]), Spacer(1, 4*mm)]
    flow += [
        PageBreak(),
        bullets([
            "分数为 seeds 42–44 的均值 ± 样本标准差，乘以 100；加粗与下划线表示该模型块内该端点的最优与"
            "次优完整结果。Norman 的最高分仍属于单实验室固定配方（25.56），BioCoLoop 在其余四个端点领先。",
            "公开控制器在封存开发选择前终止的单元格不以均值填补：† 表示部分完成，– 表示该端点没有计分运行。"
            "各单元格的完成计数与类型化失败标记为：Qwen2.5 AI-Researcher 的 VCC 完成 2/3（F_tool）；"
            "Luna AI-Scientist-v2 的 Tahoe 完成 2/3（F_svc）；Luna AI-Researcher 在五个端点均完成 0/3"
            "（F_ctx，DTI 与 Tahoe 另有 F_svc）。F_ctx 为声明的上下文上限终止，F_svc 为 Luna 服务/传输终止，"
            "F_tool 为原生工具传输终止，F_pipe 为原生流程终止。",
            "Qwen 使用已登记的生成种子；Luna 服务不暴露生成种子，因此 seed 标签只标识训练/搜索重复，"
            "相同提案与候选训练预算不代表相同的语言模型开销。",
            "每个计分单元格在开发选择封存后由独立复核器重新载入保存的预测、重算指标并核对所选取的"
            "检查点与产物哈希；DTI 重算与存储指标的差不超过 1e-15。",
            "控制器适配、transport 修订与逐运行 receipt 见英文 Appendix C；失败是执行结果，不用于事后"
            "修改控制器或替换分数。",
        ]), Spacer(1, 4*mm),
        KeepTogether(callout("公开基线对照的结论",
                "在两个研究模型块中，BioCoLoop 都在五个主要端点中的四个取得最优；唯一例外是 Norman，"
                "其最高分由单实验室固定配方保持。公开框架受实验室 0 访问限制，且 AI-Researcher 在 Luna 块"
                "触及上下文上限而未能完成任何端点（0/3）。该表因此把研究模型身份、数据访问、控制器身份与"
                "执行覆盖放在同一张主表内，而不是把未完成的运行换算成分数。",
                PALE_TEAL, TEAL))]
    return flow


def annotation_page():
    return [p('12  第二轮师姐批注如何落实', 'h1'),
            p('第二版批注 PDF 共 27 个标记，其中 25 条有文字意见；两个空文字高亮保留为定位锚点。以下按阅读问题归并，逐项原文与处理说明保留在第二轮批注目录。', 'body'),
            table([['阅读问题', '新版处理', '英文位置'],
                   ['动机跳跃、像 A+B 拼接', '围绕分散生物证据的两种用途组织主线：协作访问改进预测器，聚合反馈支持设计选择与训练分配。', 'Introduction'],
                   ['贡献只是列实验', '分点陈述框架、证据驱动研究决策及其受控收益；将已验证的训练分配与提案历史分析明确区分。', 'Introduction'],
                   ['输入输出与更新不清楚', '定义本地 train/dev、设计和参数，再给拟合/聚合、开发选择、提案历史更新与固定候选训练分配规则。', 'Method 3.1–3.4'],
                   ['架构图模糊、内外脱节', '重绘为可编辑矢量；标出设计下行、开发证据上行和历史反馈，Lab K 与任务全称取代固定 10 和缩写。', 'Figure 2'],
                   ['任务和基线不明确', '逐项说明输入、输出、数据和指标；主表把 TAPB、ProteinTalks-derived、scDEBART 各列一行，不适用处写横线。', '4.1–4.3'],
                   ['结果不应另起大章', '实验设置与结果合并为 Experiments；移除异质 Overall，按具体问题解释每项比较。', 'Section 4'],
                   ['敏感性需要图与解释', '实验室数用两类曲线区分数据量与分区；短预算开发/测试轨迹移入正文；说明相同终点来自搜索选中同一配置。', '4.6–4.7'],
                   ['D 编号、复现与附录', 'D 明确为设计编号；补完整候选菜单、JSON、五选项构造、宏平均单位和执行算法；删去进度流水账。', 'Appendix A/B'],
                   ['源码、匿名链接与 AI 声明', '材料说明区分可复现代码、模型和数据接口；按会议要求管理匿名材料与 AI 辅助披露，链接发布状态由主稿说明。', 'Statements']],
                  [37*mm, 102*mm, 32*mm], font='small'),
            Spacer(1, 5*mm),
            callout('两个需要明确的科学边界',
                    '跨场景互相增益指同一任务的兼容数据源共享参数或表示；三个任务族仍各有预测器，并未改成一个跨模态大模型。历史引导提案与固定候选训练分配也分别评价，避免把一个机制的收益记到另一个机制。',
                    PALE_PURPLE, PURPLE), PageBreak()]


def story():
    core, _ = core_review()
    completed, completed_sha = completed_review()
    supplement, supplement_sha = proteomics_supplement()
    scenario, scenario_sha = scenario_review()
    strict_protein, strict_protein_sha = strict_proteomics_review()
    s = [Spacer(1, 38*mm), p("BioCoLoop 中文伴读版", "cover"),
         p("面向生物模型改进的协作式智能体研究", "subtitle"),
         p("Collaborative Agentic Research for Biological Model Improvement", "center"),
         Spacer(1, 12*mm),
         callout("核心问题",
                 "面对同一个生物预测任务，如何让分散的实验室证据同时服务模型学习与研究决策？BioCoLoop 在原始测量保留本地的条件下组织协作训练，并将聚合反馈用于候选设计选择和训练预算分配。",
                 PALE_TEAL, TEAL), Spacer(1, 10*mm),
         table([["任务族", "主端点", "实验配置", "随机种子"],
                ["DTI / 蛋白组学 / 细胞扰动", "5", "六配置对照，已完成", "42 / 43 / 44"],
                ["蛋白组学 / 3 类细胞扰动", "4", "同预算训练分配，已完成", "53 / 54 / 55"],
                ["K / 独立来源 / 双后端", "见附录 B", "本轮实验矩阵已完成", "DTI short:42；其余见表"]],
               [55*mm, 32*mm, 45*mm, 39*mm]), Spacer(1, 12*mm),
         p("对应英文稿：2026-09-24 协作访问与证据驱动研究决策修订版", "center"),
         p("正文五节 + 附录 A/B；本文件用于快速伴读，不替代英文全文。", "center"),
         p(f"消融快照：{completed_sha[:16]}…；第三蛋白来源复核：{supplement_sha[:16]}…", "note"), PageBreak()]

    s += [p("1  论文主线", "h1"),
          callout("一句话贡献",
                  "我们提出一个协作式研究框架，让分散的生物数据既改善共享预测器，也为下一步研究决策提供证据；受控实验分别验证了协作访问和轨迹驱动训练分配的收益。",
                  PALE_PURPLE, PURPLE), Spacer(1, 5*mm),
          p("背景与目标", "h2"),
          p("生物模型研究正在从人工调整模型走向自动提出、验证并修订设计。真实测量来自不同实验室及实验场景；当原始数据保留在本地时，研究经验如何继续互相增益？BioCoLoop 使同一预测任务的多个数据持有者共享参数更新与聚合开发证据。DTI、蛋白组学、细胞扰动分别使用任务预测器，但遵循同一研究流程。", "body"),
          p("框架将实验室证据用于两个层次：", "body"),
          bullets([
              "参数层：每个实验室在本地训练候选模型，协调器聚合更新，得到共享预测器。",
              "研究决策层：聚合开发证据支持选择下一项候选设计，也支持把训练预算分配给有潜力的候选。提案历史与固定候选训练分配作为两种决策策略分别评价。",
          ]), Spacer(1, 4*mm),
          p("论文的三项贡献", "h2"),
          table([["贡献", "具体内容"],
                 ["协作研究框架", "把实验室本地参数拟合与分布式候选评价连接起来，使同一任务的实验室共同改进预测器。"],
                 ["证据驱动的研究决策", "通过证据历史选择候选，通过早期学习轨迹分配训练预算。两种策略分别受控评估，同预算训练分配已给出正向机制证据。"],
                 ["跨任务实证", "完整系统在五端点中的四个领先所列单实验室参考方法；协作访问改善五个端点，训练分配提高 Norman 表现，来源与提案实验进一步刻画适用条件。"]],
                [42*mm, 129*mm]), PageBreak()]

    s += [p("2  三种研究范式", "h1"), figure("paradigm_comparison", 171),
          Spacer(1, 3*mm),
          p("绿色表示本地数据，蓝色表示预测模型，紫色表示研究 harness，橙色表示聚合。K 是参与实验室数。灰色虚线对应不启用 harness 的固定设计配置；集中式面板展示可访问数据，完整框架由跨实验室聚合证据推动设计修订。", "note"),
          Spacer(1, 5*mm),
          table([["范式", "具备的能力", "关键差异"],
                 ["Centralized bio-agent", "在集中可访问数据上训练、评价并迭代设计", "缺少多实验室聚合"],
                 ["Collaborative training", "多实验室本地训练并聚合共享模型", "可执行设计保持固定"],
                 ["BioCoLoop", "共享模型学习与证据驱动研究决策", "聚合诊断用于设计选择和训练分配"]],
                [43*mm, 65*mm, 63*mm], highlights=[(3, PALE_TEAL)]), PageBreak()]

    s += [p("3  架构总览", "h1"),
          figure('framework_v3', 171,
                 ROOT / 'figures/biocoloop_framework_v3.pdf'),
          Spacer(1, 4*mm),
          p("新版架构图使用作者给的可编辑幻灯片：淡蓝为外层研究循环、绿色为内层协同训练、紫色为可复用产出、底部为三个生物学任务族。候选设计向下送达协调器，聚合开发证据向上返回外层，历史再流向下一次提案。Lab 1、2、K 表示同一任务下的不同实验室或场景。", "note"),
          callout("读图顺序",
                  "外层提出、实例化、评价和修订设计；中部实验室本地拟合，协调器聚合更新与诊断；右侧输出选定设计、预测器和历史；底部是三个任务族。研究 LLM 通过新的证据上下文调整下一提案，其权重保持固定。",
                  PALE_BLUE, BLUE), PageBreak(),
          p("3  Harness 外层到底做什么（续）", "h1"),
          p("一个 design_id 对应四个选择：学习率、weight decay、协调器动量、是否启用残差预测模块。D 是 design 编号，例如 D06 只命名确定配置，不编码 epoch 数。外层从统一菜单中提出候选，任务 adapter 提供输入、预测头与损失。", "body"),
          table([["阶段", "输入", "输出 / 作用"],
                 ["1. Hypothesize", "任务契约、incumbent、历史 evidence cards", "提出一个聚焦且可检验的假设"],
                 ["2. Instantiate", "结构化 proposal", "验证 design_id 并编译为可执行配置"],
                 ["3. Train + evaluate", "候选设计、各实验室 train/dev shard", "共享 predictor 与聚合开发诊断"],
                 ["4. Retain + remember", "候选与 incumbent 的证据", "保留较优设计；记录成功、拒绝与失败"],
                 ["5. Next proposal", "全部 trial 的有序摘要历史", "利用前轮结果形成下一假设；是否有效由独立对照检验"]],
                [35*mm, 64*mm, 72*mm]), Spacer(1, 6*mm),
          p("每个 proposal 的固定 JSON 字段", "h2"),
          table([["字段", "含义"],
                 ["hypothesis", "解释为什么值得尝试这个可编辑因素"],
                 ["experiment", "说明改变什么、与保留设计比较什么"],
                 ["expected_effect", "记录预期结果，供与实际诊断对照"],
                 ["design_id", "唯一确定执行配置；前三项文字供解释和复盘，实际保留由开发指标决定"]],
                [48*mm, 123*mm]), Spacer(1, 6*mm),
          callout("为什么历史记录重要",
                  "下一轮 loop 接收各 trial 的配置、假设、接受状态、best round 与开发 metric/loss，以及首末训练/开发诊断和差值。这些 evidence cards 是全部试验的摘要历史；逐轮学习曲线另存于 fit 记录，不直接作为整条曲线输入 LLM。",
                  PALE_ORANGE, ORANGE), Spacer(1, 3*mm),
          p("Qwen direct 始终接收固定起始配方及未尝试的 design_id，不接收开发反馈；loop 接收当前保留配置和全部 trial 的摘要历史。第一个提案按无反馈方式生成并共享，第二个槽位起 loop 才读取历史。研究 LLM 不微调；学习发生在任务预测器的梯度训练，以及证据上下文驱动的后续设计选择中。", "note"), PageBreak()]

    s += [p("3  本地拟合、开发评价与训练预算（续）", "h1"),
          p("训练时长由评价调度器单独设置，不由 design_id 或 LLM 提案决定。主表和 proposal-history 实验中，每个有效候选均按相同任务和 seed 的初始化规则重新训练 100 轮。这里一轮指所有参与实验室各完成一次本地 epoch，然后协调器聚合参数；不是一个 loop 槽位。", "body"),
          table([["过程", "执行规则"],
                 ["本地拟合", "各实验室接收当前参数，重新初始化 AdamW，以 batch size 64 完成本地一次 epoch，梯度范数裁剪到 1。协调器按本地训练样本数加权聚合；协调器动量决定聚合更新是否累积前轮速度。"],
                 ["开发评价", "每 5 轮及最后一轮评价，指定开发面板等权平均。主比较用参与实验室的面板，fixed-pool 和跨来源对照保留目标原开发面板；主分数优先、loss 破平，选最佳 checkpoint。"],
                 ["外层选择", "用候选的最佳开发证据与保留设计比较。选定设计和 checkpoint 后，由固定留出 scorer 评价。"],
                 ["异源目标", "蛋白来源可有不同目标：编码器共享，各专属 head 只在拥有它的实验室间聚合；目标原有开发面板选择 checkpoint。"],
                 ["信息边界", "实验室返回参数更新、样本数和开发诊断；研究 LLM 读取聚合 evidence cards，原始测量留在实验室内。"]],
                [35*mm, 136*mm], font="small"), Spacer(1, 4*mm),
          p("两种决策策略：提案修订与训练分配（英文 3.3–3.4）", "h2"),
          p("英文第 3.4 节的轨迹驱动训练分配用于独立的固定候选对照，结果见英文第 4.4 节及本伴读版第 6 节；该策略未用于主表，主表仍为每候选 100 轮。", "note"),
          table([["实验", "候选训练安排", "作用"],
                 ["提案修订", "每个候选 100 轮", "历史证据影响下一次尝试的设计，不缩短候选训练。"],
                 ["均匀预算分配", "10 个固定候选各 80 轮", "共 800 个聚合轮、8,000 个本地 epoch。"],
                 ["证据引导分配", "10 个候选各筛选 20 轮；6 个晋级者重新训练 100 轮", "共 800 个聚合轮；4 个只筛选，6 个晋级者从相同初始化重新训练。"]],
                [35*mm, 63*mm, 73*mm], font="small"), Spacer(1, 4*mm),
          callout("轨迹驱动训练分配：可复现的晋级规则",
                  "将固定十候选按三档学习率分组。每组先保留筛选最佳 checkpoint 的开发主分数最高者，再从其余候选中保留第 5 至第 20 轮开发主分数涨幅最大者，共六个不同候选。前者用该最佳 checkpoint 的开发 loss 破平，后者用第 20 轮的开发 loss 破平。晋级后从共同初始化重新训练，并重新选择开发 checkpoint。",
                  PALE_ORANGE, ORANGE), Spacer(1, 3*mm),
          p("主实验在同一主机上将一个任务数据集划成十个互不重叠的组，模拟各实验室的本地训练和评价，控制数据参与度；它不等同于十项真实独立研究。来源实验另将不同研究或场景对应为实验室。参数聚合按训练样本数加权，开发选择按实验室等权。", "note"), PageBreak()]

    s += [p("4  三个任务如何统一", "h1"),
          table([["任务", "预测契约", "任务参考模型", "主指标"],
                 ["DTI", "compound + protein → interaction", "TAPB + frozen ESM2 protein features", "AUROC"],
                 ["Proteomics", "observed 6h/24h proteome + drug → efficacy", "ProteinTalks-derived efficacy head", "AP"],
                 ["VCC", "response + 5 single-gene options → identity", "corrected scDEBART head", "Macro Top-1"],
                 ["Norman", "response + 5 double-gene options → identity", "corrected scDEBART head", "Macro Top-1"],
                 ["Tahoe", "response + 5 drug options → identity", "scDEBART + Morgan conditioning", "Macro Top-1"]],
                [30*mm, 70*mm, 48*mm, 23*mm], font="tiny"), Spacer(1, 4*mm),
          p("细胞五选项按干预构造：一个真实扰动加同一开发或测试池中的四个不同干扰项，随机打乱顺序。同一干预的全部查询和全部方法使用同一选项名单。Top-1 先在每个干预内求准确率，再对干预等权平均；因此大量重复细胞不会让某个干预占据更大权重。", "small"),
          Spacer(1, 3*mm),
          callout("一致性",
                  "五个端点共享同一个 inner trainer、proposal schema、evidence card、研究历史和 finalizer；任务差异只通过 adapter 和 scorer 进入。主实验使用 seeds 42-44；固定候选预算分配实验在四个轻任务上使用 seeds 53-55；双后端提案反馈的单 seed 配置另列。",
                  PALE_BLUE, BLUE), Spacer(1, 5*mm),
          p("六配置因子对照", "h2"),
          bullets([
              "参与度：1 个实验室 vs 10 个实验室。",
              "研究模式：固定配方、无历史 direct search、有历史 proposal loop；这里的 loop 专指 LLM 提案策略。",
              "主表比较完整系统；因子对照分别估计参与度、设计搜索和提案反馈的差异。",
          ]), PageBreak()]

    s += [p("5  主结果", "h1"),
          table(main_score_rows(),
                [49*mm, 24.4*mm, 24.4*mm, 24.4*mm, 24.4*mm, 24.4*mm],
                font="small", highlights=[(5, PALE_TEAL)]), Spacer(1, 4*mm),
          p("主表比较完整系统与所列单实验室参考方法，参考预测器具名，“—”表示不适用。所列最高值加粗，第二名加下划线；AUROC、AP、Top-1 分开报告。分数为 seeds 42–44 的均值 ± 样本标准差，乘以 100。BioCoLoop 在五端点中的四个领先这些单实验室参考；Norman 仍由单实验室 scDEBART 固定配方领先。", "note"),
          Spacer(1, 6*mm),
          callout("完整系统的跨任务收益",
                  "完整系统在分子互作、蛋白响应和细胞扰动三类任务上都取得正向结果；相对于单实验室 direct optimization，五个端点的增益分别为 +3.87、+16.85、+10.45、+8.10 和 +6.97 个百分点。",
                  PALE_TEAL, TEAL), Spacer(1, 4*mm),
          p("六臂对照进一步定位收益：保持有历史提案策略，从一个实验室扩展到十个实验室后，五个端点均提高。同为十个实验室时，direct 与有历史提案选中相同检查点；单实验室 VCC 则不同。十实验室固定配方在蛋白与 Tahoe 的均值更高，完整对照保留于英文附录 A。", "small"), PageBreak()]

    s += grouped_harness_page()

    s += [p("6  证据如何改进训练预算分配", "h1"),
          p("早期学习轨迹能够指导后续训练投入。本页报告英文第 3.4 节策略的独立对照：固定十个设计，检验证据驱动训练分配是否在相同预算下优于均匀分配。该策略未用于主表；主表各候选均训练 100 轮，LLM 提案历史另行检验下一次尝试什么设计。", "body"),
          table([["端点", "均匀分配", "证据分配", "增益", "胜/平/负"],
                 ["Proteomics（留出）", "37.47", "37.47", "+0.00", "0/3/0"],
                 ["VCC（留出）", "20.01", "20.01", "+0.00", "0/3/0"],
                 ["Norman（留出）", "11.48", "22.32", "<b>+10.84</b>", "3/0/0"],
                 ["Tahoe（留出）", "20.90", "22.89", "+1.99", "1/2/0"]],
                [49*mm, 29*mm, 29*mm, 32*mm, 32*mm], font="tiny",
                highlights=[(3, PALE_TEAL)]), Spacer(1, 5*mm),
          bullets([
              "双方使用同样十个设计、十个实验室和 160 次聚合开发评价；每次覆盖十个实验室，共 1,600 次本地开发评价。",
              "均匀分配给每个设计 80 轮；证据分配先各训练 20 轮，按三档学习率各晋级两名，共六个设计从共同初始化重新训练 100 轮，另四个仅做筛选；两者均为 800 个聚合轮，即 8,000 个本地 epoch。",
              "12 个新执行的留出 task-seed 对比为 4 胜、8 平、0 负。Norman 平均提升 10.84 点，95% CI 为 [4.54, 17.73]；Tahoe 平均提升 1.99 点，区间跨零。",
              "DTI 仅有已有开发轨迹回放：均匀分配 525、证据分配 520 个 candidate-round，开发 AUROC 相差 +0.39 点（2 胜、1 平），单列于附录 A。",
          ]), Spacer(1, 5*mm),
          callout("已经得到的机制结论",
                  "相同训练与开发评价预算下，早期证据改善了训练分配，Norman 三个种子均获益：这直接支持证据驱动研究决策的价值。旧记录中这组策略曾称为 loop/direct；此处统一称为证据分配/均匀分配，与第 9–10 节的有历史/无历史 LLM 提案明确区分。",
                  PALE_PURPLE, PURPLE), PageBreak()]

    s += sensitivity_pages(completed, core, supplement, scenario, strict_protein)
    s += annotation_page()
    s += [p("13  当前论文如何阅读", "h1"),
          table([["部分", "核心内容"],
                 ["Abstract / Introduction", "提出协作式生物研究问题，以协作访问与证据驱动研究决策组织贡献；并点名公开 harness 基线与匹配的 Qwen2.5/GPT-5.6 Luna 对照。"],
                 ["Related Work", "把 AIDE、AI Scientist、DrugEvolve、协作训练、FedEx、Helmsman 放入统一坐标。"],
                 ["Method", "定义实验室、设计和参数；给出拟合/聚合、开发选择、3.3 提案历史更新与 3.4 训练分配规则。"],
                 ["Experiments", "4.1–4.2 任务和协议；4.3 公开 harness 基线与 Qwen2.5/GPT-5.6 Luna 双模型主表；4.4 训练分配；4.5 来源；4.6 实验室数；4.7 提案轨迹。"],
                 ["Conclusion", "从既有模型出发，总结更多数据、固定数据量下方案搜索及独立训练分配的实际收益。"],
                 ["Appendix A", "设计菜单、proposal JSON、优化设置、六配置结果、次指标与统计方法。"],
                 ["Appendix B", "K、独立来源、双后端短/长预算、全部前缀曲线；用索引规则紧凑定义全部设计。"],
                 ["Appendix C", "公开框架的适配方式、统一任务接口、类型化失败与独立复核记录。"],
                 ["Statistical Supplement", "全部逐 seed 差值与置信区间，正、零、负结果均保留；与论文一并提交。"]],
                [43*mm, 128*mm]), Spacer(1, 6*mm),
          callout("目前最强的论文信息",
                  "同一研究接口支持三个生物任务族，完整系统在五端点中的四个领先所列单实验室参考方法。保持提案策略时，扩大协作访问改善五个端点；固定十实验室时，方案搜索相对固定配方提高 DTI 1.96 点、Norman 6.77 点。独立的同预算训练分配在 Norman 上另有 +10.84 点增益。这些是不同对照，不能相加；来源和提案轨迹实验刻画了适用条件。",
                  PALE_ORANGE, ORANGE), Spacer(1, 6*mm),
          p("本版按贡献与证据组织阅读顺序：协作学习与研究决策、两种决策策略、完整系统表现与等预算训练分配，再分析来源、分区和提案轨迹。第三独立蛋白源已完成复核；DTI long24 尚未执行。后续可扩展重复实验，以及来源兼容性对外层研究的影响。", "body"),
          p("复现 / 伦理 / AI 使用声明分别说明实验材料、数据本地边界及 AI 辅助范围。多机构真实部署仍需明确的安全与隐私方案；本研究没有新增受试者或湿实验。", "note")]
    return s


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    bound_snapshot = ROOT / 'tables/completed_ablation/snapshot.json'
    before_sha = hashlib.sha256(bound_snapshot.read_bytes()).hexdigest()
    grouped_before_sha = hashlib.sha256(GROUPED_HARNESS_SNAPSHOT.read_bytes()).hexdigest()
    _, supplement_before_sha = proteomics_supplement()
    _, scenario_before_sha = scenario_review()
    _, strict_protein_before_sha = strict_proteomics_review()
    rendered = TMP / 'companion.pdf'
    Doc(str(rendered)).build(story())
    completed, snapshot_sha = completed_review()
    assert snapshot_sha == before_sha, 'Publication snapshot changed during rendering; rerun cleanly'
    supplement, supplement_sha = proteomics_supplement()
    assert supplement_sha == supplement_before_sha, 'Protein supplemental receipt changed during rendering'
    scenario, scenario_sha = scenario_review()
    assert scenario_sha == scenario_before_sha, 'Scenario supplemental receipt changed during rendering'
    strict_protein, strict_protein_sha = strict_proteomics_review()
    assert strict_protein_sha == strict_protein_before_sha, 'Strict protein-source receipt changed during rendering'
    assert (hashlib.sha256(GROUPED_HARNESS_SNAPSHOT.read_bytes()).hexdigest()
            == grouped_before_sha), 'Grouped harness snapshot changed during rendering'
    inputs = [ROOT / 'tables/strong_v3/snapshot.json',
              ROOT / 'tables/core_review/snapshot.json',
              ROOT / 'tables/completed_ablation/snapshot.json',
              GROUPED_HARNESS_SNAPSHOT,
              ROOT / 'provenance/luna_main_core_20260925/independent_verification.json',
              ROOT.parent / 'results/tonight_completion_20260923/final_delivery/summary.json',
              ROOT.parent / 'results/proteomics_external_pilot_20260923/RESULT.zh-CN.md',
              ROOT / 'assets/paradigm_comparison.pdf',
              ROOT / 'assets/completed_budget_examples.pdf',
              ROOT / 'assets/laboratory_sensitivity_v2.pdf',
              ROOT / 'assets/completed_short6_search.pdf',
              ROOT / 'figures/biocoloop_framework_v3.pdf',
              ROOT / 'figures/biocoloop_framework_v3.provenance.json',
              ROOT / 'provenance/coauthor_review_v2_20260923/ANNOTATIONS.zh-CN.md',
              ROOT / 'sections/03_method.tex',
              ROOT / 'sections/04_experimental_design.tex',
              ROOT / 'sections/22_appendix_unified_protocol.tex',
              PROTEOMICS_SUPPLEMENT / 'independent_rescore.json',
              PROTEOMICS_SUPPLEMENT / 'definition.json',
              PROTEOMICS_SUPPLEMENT / 'heldout/results.json',
              SCENARIO_SUPPLEMENT / 'campaign.json',
              SCENARIO_SUPPLEMENT / 'completion_v2.json',
              SCENARIO_SUPPLEMENT / 'protocol.json',
              SCENARIO_SUPPLEMENT / 'heldout/independent_rescore_v2.json',
              SCENARIO_SUPPLEMENT / 'heldout/results.json',
              SCENARIO_SUPPLEMENT / 'heldout/seal.json',
              STRICT_PROTEOMICS / 'status.json',
              STRICT_PROTEOMICS / 'protocol.json',
              STRICT_PROTEOMICS / 'binding.json',
              STRICT_PROTEOMICS / 'independent_rescore.json',
              STRICT_PROTEOMICS / 'heldout/results.json',
              STRICT_PROTEOMICS / 'heldout/seal.json']
    # Figure PDFs are rasterized for this companion; inspect their source text
    # as well as the final PDF so visible labels cannot retain the retired name.
    retired = ''.join(('AI4', 'AI4', 'Cell')).lower()
    for source in (ROOT / 'assets/paradigm_comparison.pdf',
                   ROOT / 'figures/biocoloop_framework_v3.pdf'):
        with fitz.open(source) as figure_doc:
            figure_text = ''.join(page.get_text() for page in figure_doc)
            assert retired not in figure_text.lower(), f'Retired label remains in {source.name}'
    with fitz.open(rendered) as document:
        page_count = len(document)
        text = ''.join(page.get_text() for page in document)
        assert retired not in text.lower(), 'Retired brand remains in visible text'
        assert retired not in json.dumps(document.metadata).lower(), 'Retired brand remains in metadata'
        assert 'BioCoLoop' in document.metadata['title']
        out_of_bounds = []
        for index, page in enumerate(document):
            for block in page.get_text('dict')['blocks']:
                for line in block.get('lines', []):
                    for span in line['spans']:
                        box = fitz.Rect(span['bbox'])
                        if box.x0 < -0.5 or box.y0 < -0.5 or box.x1 > page.rect.width+0.5 or box.y1 > page.rect.height+0.5:
                            out_of_bounds.append(index+1)
        assert not out_of_bounds, f'Text crosses page bounds: {out_of_bounds}'
        embedded_fonts = sorted({font[3] for page in document for font in page.get_fonts()
                                 if font[1] not in ('n/a', '')})
        assert any('CompanionSC' in name for name in embedded_fonts), 'Chinese fonts are not embedded'
    provenance = {
        'schema': 'biocoloop-chinese-companion-v3',
        'display_brand': 'BioCoLoop',
        'display_title': 'BioCoLoop: Collaborative Agentic Research for Biological Model Improvement',
        'branding_verified': True,
        'embedded_fonts': embedded_fonts,
        'text_out_of_bounds_pages': out_of_bounds,
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'embedded_font_source_sha256': hashlib.sha256(FONT_SOURCE.read_bytes()).hexdigest(),
        'input_sha256': {str(path.relative_to(ROOT.parent)): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in inputs},
        'publication_snapshot_sha256': snapshot_sha,
        'grouped_harness_snapshot_sha256': grouped_before_sha,
        'grouped_harness_models': ['Qwen2.5-7B-Instruct', 'GPT-5.6 Luna (low reasoning)'],
        'supplemental_proteomics_receipt_sha256': supplement_sha,
        'scenario_laboratory_receipt_sha256': scenario_sha,
        'scenario_laboratory_status': scenario['status'],
        'strict_proteomics_source_laboratory_receipt_sha256': strict_protein_sha,
        'strict_proteomics_source_laboratory_status': strict_protein['verification']['status'],
        'strict_proteomics_training_K': [1, 2, 3, 4],
        'strict_proteomics_development_panels': 10,
        'strict_proteomics_proposal_slots': 0,
        'scenario_original_failure_preserved': True,
        'scenario_rescore_revision': 2,
        'supplemental_proteomics_status': supplement['status'],
        'supplemental_proteomics_fixed_design_only': supplement['fixed_design_only'],
        'coauthor_review_v2_markers': 27,
        'coauthor_review_v2_text_comments': 25,
        'verified_source_receipts': len(completed['source_sha256']),
        'paired_terminal_signs': {protocol: paired_counts(protocol_runs(completed, protocol))
                                  for protocol in ('short6', 'long24')},
        'valid_proposal_counts': {protocol: {backend: backend_validity(protocol_runs(completed, protocol), backend)
                                            for backend in ('qwen', 'luna')}
                                  for protocol in ('short6', 'long24')},
        'page_count': page_count,
        'output_sha256': hashlib.sha256(rendered.read_bytes()).hexdigest(),
        'uncompleted_extensions': ['additional seeds', 'DTI long24'],
        'third_independent_protein_source_status': 'COMPLETE_VERIFIED_FIXED_DESIGN_ONLY',
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
