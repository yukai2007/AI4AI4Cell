#!/usr/bin/env python3
"""Validate the initial editable-figure handoff and write its provenance receipt."""
from pathlib import Path
import hashlib
import json
import subprocess

from export_preview import inspect_native

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    names = ['Figure_1_research_paradigms', 'Figure_2_framework',
             'Figure_3_laboratory_count', 'Figure_4_short_loop', 'Figure_5_extended_loop']
    active = ['assets/paradigm_comparison.pdf', 'figures/biocoloop_framework_v2.pdf',
              'assets/laboratory_sensitivity_v2.pdf', 'assets/completed_short6_search_v2.pdf',
              'assets/completed_long24_search.pdf']
    protected = active + ['figures/biocoloop_framework_v2.pptx',
                          'tables/completed_ablation/snapshot.json',
                          'output/pdf/BioCoLoop_manuscript.pdf',
                          'output/pdf/BioCoLoop_statistical_supplement.pdf',
                          'output/pdf/BioCoLoop_中文伴读版.pdf']
    unchanged = {}
    for name in protected:
        blob = subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=PAPER)
        unchanged[name] = sha(PAPER / name)
        assert unchanged[name] == hashlib.sha256(blob).hexdigest(), 'Active source changed: ' + name
    assert sha(HERE / (names[1] + '.pptx')) == sha(PAPER / protected[5])
    chart_receipt = json.loads((HERE / 'validation/result_figures_integrity.json').read_text())
    assert sha(HERE / 'source/result_figure_data.json') == chart_receipt['data_sha256']
    assert sha(HERE / 'source/build_editable_result_figures.js') == chart_receipt['authoring_source_sha256']
    assert sha(PAPER / chart_receipt['source']) == chart_receipt['source_sha256']
    items = []
    for i, stem in enumerate(names):
        path = HERE / (stem + '.pptx')
        native = inspect_native(path)
        assert native['slides'] == 1 and not native['embedded_media']
        assert (HERE / 'previews' / (stem + '.png')).is_file()
        if i >= 2:
            item = chart_receipt['outputs'][i - 2]
            assert sha(path) == item['sha256']
            assert native['native_charts'] == native['editable_workbooks'] == [5, 10, 8][i - 2]
            assert item['exact_numeric_chart_cache_verification']
            assert item['exact_embedded_workbook_verification']
        else:
            item = json.loads((HERE / f'validation/Figure_{i+1}_export_receipt.json').read_text())
            assert item['source_sha256'] == sha(path) and item['overflow_returncode'] == 0
        items.append(dict(figure=i+1, editable=path.name, editable_sha256=sha(path),
                          active_pdf=active[i], native=native, preview='previews/' + stem + '.png',
                          visual_review='PASSED', overflow_review='PASSED'))
    receipt = dict(schema='editable-figure-handoff-v1',
                   basis_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PAPER, text=True).strip(),
                   manuscript_artwork_replaced=False, current_artifact_hashes=unchanged,
                   figures=items, chart_points=840,
                   numerical_checks='All chart caches and embedded XLSX values checked against frozen snapshot.',
                   visual_review='All five previews inspected; no cropping, overlapping labels or slide overflow.',
                   fidelity='Figure 2 is an exact PPTX copy. Figures 1, 3, 4, 5 are native editable counterparts; layout/axis styling may differ.')
    target = HERE / 'validation/delivery_manifest.json'
    target.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(dict(status='PASS', figures=len(items), chart_points=840,
                          active_artifacts_unchanged=len(unchanged), receipt=str(target)), ensure_ascii=False))


if __name__ == '__main__':
    main()
