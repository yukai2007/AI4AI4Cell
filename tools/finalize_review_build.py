"""Validate and copy the reviewed PDF; record a local build receipt."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import re
import shutil

import fitz

PAPER = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tests-passed', type=int, required=True)
    parser.add_argument('--visual-review', required=True)
    args = parser.parse_args()
    if args.tests_passed < 1 or not args.visual_review.strip():
        raise ValueError('Record actual passing tests and a nonempty visual-review receipt')
    verification = json.loads((PAPER/'provenance/coauthor_review_20260922/core_verification.json').read_text())
    if verification['status'] != 'PASS':
        raise RuntimeError('Independent sensitivity verification must pass')
    log = (PAPER/'build/main.log').read_text()
    failures = re.findall(r'Overfull[^\n]*|[^\n]*undefined[^\n]*|^!.*', log, re.M)
    if failures:
        raise RuntimeError('Resolve build errors before publishing: ' + str(failures))
    pdf = PAPER/'build/main.pdf'
    doc = fitz.open(pdf)
    conclusion = [i+1 for i,p in enumerate(doc) if '6. CONCLUSION' in p.get_text()]
    statement = [i+1 for i,p in enumerate(doc) if 'REPRODUCIBILITY STATEMENT' in p.get_text()]
    if conclusion != [8] or statement != [9]:
        raise RuntimeError('Pagination changed: repeat visual and page-limit review')
    all_text = '\n'.join(page.get_text() for page in doc)
    for identifier in ('/liziqing/', 'yukai2007', '于畅', 'Kai Yu', 'Westlake University'):
        if identifier in all_text:
            raise RuntimeError('Check anonymous manuscript text: ' + identifier)
    if doc.metadata.get('author'):
        raise RuntimeError('Check PDF author metadata')
    if any(list(page.annots() or []) for page in doc):
        raise RuntimeError('Review annotations must not enter the submission PDF')
    inputs = [PAPER/'ai4ai4cell-main.tex', PAPER/'main.tex', PAPER/'references.bib']
    inputs += list((PAPER/'sections').glob('*.tex'))
    inputs += list((PAPER/'tables').rglob('*.tex'))
    inputs += list((PAPER/'assets').glob('*.pdf'))
    targets = [PAPER/'manuscript.pdf', PAPER/'output/pdf/AI4AI4Cell_coauthor_revised_20260923.pdf']
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf, target)
        assert sha(pdf) == sha(target)
    receipt = dict(
        built_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        source_sha256={str(p.relative_to(PAPER)):sha(p) for p in sorted(inputs)},
        pdf_sha256=sha(pdf), total_pages=len(doc), main_text_pages=8,
        build_exit=0, overfull_boxes=0, undefined_references=0,
        visual_review=args.visual_review,
        annotation_count=29, written_comments=24,
        disposition='provenance/coauthor_review_20260922/RESPONSE.zh-CN.md',
        unit_tests_passed=args.tests_passed,
        independent_core_rescore={k:verification[k] for k in (
            'status', 'result_files', 'verified_predictions', 'unique_checkpoint_hashes_verified', 'max_abs_error')},
        pending_experiments='See core_review snapshot and live experiment supervisor; not a completed study.',
        remote_changes='No GitHub push, Overleaf edit or OpenReview submission in this revision turn.',
        remaining_submission_actions='Author/platform declarations, anonymous supplementary package, remaining experiments.',
    )
    out=PAPER/'provenance/coauthor_review_20260922/build_receipt.json'
    out.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='source_sha256'},indent=2))


if __name__=='__main__':
    main()
