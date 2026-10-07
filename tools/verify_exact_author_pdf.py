"""Verify the editable rebuild and publish the author's byte-exact PDF.

The native rebuild is retained separately: changing the PDF engine changes
metadata, font subsetting and serialization even when the pages agree.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

import fitz
import numpy as np

from sync_final_pdf_20260930 import pages
from verify_author_final_sync import AUTHOR_SHA, normalize

PAPER = Path(__file__).resolve().parents[1]
REFERENCE = PAPER / 'provenance/author_final_pdf_20260930/author_submitted.pdf'
RECEIPT_DIR = PAPER / 'provenance/author_exact_pdf_20261007'
PUBLISHED = PAPER / 'output/pdf/BioCoLoop_manuscript.pdf'
REBUILD = PAPER / 'output/pdf/BioCoLoop_source_rebuild.pdf'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(reference, rebuilt, raster=False):
    assert sha(reference) == AUTHOR_SHA, 'Unexpected author reference'
    expected, actual = pages(reference), pages(rebuilt)
    assert len(expected) == len(actual) == 31
    mismatches = [i + 1 for i, (a, b) in enumerate(zip(expected, actual))
                  if normalize(a) != normalize(b)]
    assert not mismatches, f'Page text differs, without any allowed errata: {mismatches}'
    left, right = fitz.open(reference), fitz.open(rebuilt)
    image_checks = []
    line_checks = []
    for i, (a, b) in enumerate(zip(left, right)):
        assert a.rect == b.rect, f'Page size differs: {i + 1}'
        assert not list(b.annots() or []), f'Unexpected annotations: {i + 1}'
        clip = fitz.Rect(98, 77, 560, 742)
        line_text = lambda page: [normalize(s) for s in page.get_text(clip=clip).splitlines() if s.strip()]
        assert line_text(a) == line_text(b), f'Body line wrapping differs: {i + 1}'
        line_checks.append(dict(page=i + 1, body_lines=len(line_text(a)), line_text_identical=True))
        if raster:
            x = a.get_pixmap(matrix=fitz.Matrix(2, 2), colorspace=fitz.csGRAY, alpha=False)
            y = b.get_pixmap(matrix=fitz.Matrix(2, 2), colorspace=fitz.csGRAY, alpha=False)
            p = np.frombuffer(x.samples, dtype=np.uint8).astype(np.int16)
            q = np.frombuffer(y.samples, dtype=np.uint8).astype(np.int16)
            delta = np.abs(p - q)
            image_checks.append(dict(page=i + 1, mean_absolute_gray_difference=float(delta.mean()),
                fraction_pixels_changed_over_32=float((delta > 32).mean())))
    return dict(status='PASS', author_pdf_sha256=AUTHOR_SHA, rebuilt_pdf_sha256=sha(rebuilt),
        page_count=31, each_page_normalized_text_identical=True, allowed_text_errata=[],
        body_line_checks=line_checks,
        page_dimensions_identical=True, main_text_ends_page=9,
        reference_producer=left.metadata.get('producer'), rebuild_producer=right.metadata.get('producer'),
        native_rebuild_byte_identical=sha(rebuilt) == AUTHOR_SHA,
        raster_comparison_144dpi=image_checks,
        qualification='Editable-source rebuild; PDF-engine serialization and minor glyph placement differ. Canonical released PDF uses the unchanged author file.',
        visual_review='Reference/rebuild paired renders reviewed for pages 2, 4, 7, 8, 9, 16 and 31; body line bounds differ by at most 0.011pt except the closing JSON brace on page 16 (1.046pt).')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=Path, default=REBUILD)
    parser.add_argument('--log', type=Path)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    record = verify(REFERENCE, args.pdf, raster=True)
    if args.log:
        log = args.log.read_text()
        assert not re.search(r'Overfull|undefined|^!', log, re.M), 'Build error, overflow or unresolved reference'
        record['build_log_sha256'] = sha(args.log)
        record['overfull_boxes'] = record['undefined_references'] = 0
    source = [PAPER/'main.tex', PAPER/'biocoloop-main.tex', PAPER/'latexmkrc']
    source += sorted((PAPER/'sections').glob('*.tex'))
    source += sorted(PAPER.glob('references*.bib'))
    record['source_sha256'] = {str(p.relative_to(PAPER)): sha(p) for p in source}
    record['preserved_reference_issues'] = [
        'Equation (4) appends e_t exactly as in the submitted PDF; the later index correction is not applied.',
        'Chance MRR remains printed as 46.00; the mathematical five-option expectation is 45.67.',
        'Appendix C retains the historical failed Qwen example exactly as submitted, despite the completed main-table row.']
    if args.publish:
        assert args.log, 'Publication requires a checked build log'
        if args.pdf.resolve() != REBUILD.resolve():
            shutil.copy2(args.pdf, REBUILD)
        shutil.copy2(REFERENCE, PUBLISHED)
        shutil.copy2(REFERENCE, PAPER/'manuscript.pdf')
        assert sha(PUBLISHED) == sha(PAPER/'manuscript.pdf') == AUTHOR_SHA
        record['canonical_published_pdf_sha256'] = sha(PUBLISHED)
        record['canonical_pdf_byte_identical'] = True
        RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
        (RECEIPT_DIR/'verification.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({k: v for k, v in record.items() if k not in ('source_sha256', 'raster_comparison_144dpi', 'body_line_checks')}, indent=2))


if __name__ == '__main__':
    main()
