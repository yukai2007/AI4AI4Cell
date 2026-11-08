"""Validate the review revision and install versioned, hash-bound deliverables."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys

import fitz

PAPER = Path(__file__).resolve().parents[1]
BASE = '7764441764dea9d59713fe26286e84aff45aac19'
PROVENANCE = PAPER / 'provenance/rebuttal_20261109'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(pdf, log):
    for script in ('publish_rebuttal_access_table.py', 'publish_rebuttal_evidence.py',
                   'publish_rebuttal_allocation.py'):
        subprocess.run([sys.executable, str(PAPER / 'tools' / script), '--check'], check=True)
    document = fitz.open(pdf)
    texts = [p.get_text() for p in document]
    conclusion = [i + 1 for i, text in enumerate(texts) if '5. CONCLUSION' in text]
    repro = [i + 1 for i, text in enumerate(texts) if 'REPRODUCIBILITY STATEMENT' in text]
    assert conclusion and max(conclusion) <= 10, conclusion
    assert repro and min(repro) >= max(conclusion), repro
    if min(repro) == max(conclusion):
        last_main = texts[max(conclusion) - 1]
        assert last_main.index('5. CONCLUSION') < last_main.index('REPRODUCIBILITY STATEMENT')
    assert any('APPENDIX E.' in t for t in texts)
    text = '\n'.join(texts)
    for forbidden in ('/liziqing/', 'yukai2007', 'Kai Yu', 'Westlake University'):
        assert forbidden not in text, forbidden
    assert not document.metadata.get('author')
    assert not any(list(page.annots() or []) for page in document)
    bad = re.findall(r'^.*(?:Overfull|undefined|Missing character|^!|Citation .*undefined).*$',
                     log.read_text(), re.M)
    assert not bad, bad
    for page in document:
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines', []):
                for span in line['spans']:
                    x0, y0, x1, y1 = span['bbox']
                    assert -1 <= x0 <= x1 <= page.rect.width + 1
                    assert -1 <= y0 <= y1 <= page.rect.height + 1
    # Prior numbers, submission reference and experimental assets remain intact.
    original = subprocess.check_output(['git', 'show', BASE + ':tables/public_harness_comparison/main_public_harness_three_seed.tex'], cwd=PAPER)
    assert original == (PAPER / 'tables/public_harness_comparison/main_public_harness_three_seed.tex').read_bytes()
    archived = PAPER / 'provenance/author_final_pdf_20260930/author_submitted.pdf'
    assert sha(archived) == '3bdd4251d9b201a1e9fbf6b94ffd72fc7092b0cc33a3afdcf72b4150b4407ec8'
    files = [PAPER / 'biocoloop-main.tex', PAPER / 'references.bib']
    files += sorted((PAPER / 'sections').glob('*.tex'))
    files += sorted((PAPER / 'tables/rebuttal_20261109').glob('*'))
    files += sorted(PROVENANCE.glob('RESPONSE_*.md'))
    files += sorted((PAPER / 'tools').glob('*rebuttal*.py'))
    files += [PROVENANCE / name for name in ('CHANGES.zh-CN.md', 'REVIEW_ACTIONS.zh-CN.md',
        'experiment_sources.zip', 'experiment_sources.manifest.json')]
    bundle = json.loads((PROVENANCE / 'experiment_sources.manifest.json').read_text())
    assert bundle['status'] == 'PASS'
    assert bundle['archive_sha256'] == sha(PROVENANCE / 'experiment_sources.zip')
    return dict(status='PASS', base_commit=BASE, total_pages=len(document),
        main_text_ends_page=max(conclusion), rebuttal_main_page_limit=10,
        page_limit_source='https://iclr.cc/Conferences/2027/AuthorGuidelines',
        manuscript_sha256=sha(pdf), build_log_sha256=sha(log),
        reviewer_responses_pdf_sha256=sha(PAPER / 'output/pdf/BioCoLoop_reviewer_responses_20261109.pdf'),
        original_access_score_cells_changed=0, author_submitted_reference_preserved=True,
        aggregate_publication_checks='PASS: access table, search/validation and allocation',
        overfull_boxes=0, undefined_references=0, page_geometry_check='PASS',
        source_sha256={str(p.relative_to(PAPER)): sha(p) for p in files},
        openreview_posted=False, overleaf_remote_build_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=Path, required=True)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    receipt = verify(args.pdf, args.log)
    if args.publish:
        for destination in ('output/pdf/BioCoLoop_revised_20261109.pdf',
                            'output/pdf/BioCoLoop_manuscript.pdf', 'manuscript.pdf'):
            shutil.copy2(args.pdf, PAPER / destination)
        (PROVENANCE / 'build_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'source_sha256'}, indent=2))


if __name__ == '__main__':
    main()
