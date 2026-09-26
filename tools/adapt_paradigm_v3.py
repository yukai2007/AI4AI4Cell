"""Adopt the author-supplied editable paradigm deck as Figure 1.

``/liziqing/yukai/AI4AI4Cell/paradigm_comparison_editable.pptx`` becomes the
active Figure 1.  The author's original file is never modified, and this deck
needs no repair: it is a single 13.33 in x 7.70 in slide whose three panels
(a) centralized bio-agent, (b) collaborative training and (c) BioCoLoop render
without clipped text, without legacy Office-2010 markup and without the retired
brand name.  The copy stored here is byte-identical to the source.

The tool renders the PDF/PNG used by the manuscript, runs the slide-overflow
check and records a provenance receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adapt_framework_v3 import render_environment  # noqa: E402

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parent
SKILL = Path('/liziqing/yukai/.codex/skills/slides/scripts')
DEFAULT_SOURCE = ROOT / 'paradigm_comparison_editable.pptx'
STEM = 'paradigm_comparison_v3'
SLIDE_ASPECT = 12192000 / 7045325
REQUIRED_WORDS = [
    '(a)', 'Centralized bio-agent', '(b)', 'Collaborative training', '(c)', 'BioCoLoop',
    'Research / design loop', 'Accessible dataset', 'Accessible data', 'model parameters',
    'Design revision', 'Aggregate development evidence', 'Lab 1', 'Lab 2', 'Lab K',
    'Local update', 'Model', '(design fixed in advance)', '(design revised between rounds)',
]


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--output-dir', type=Path, default=PAPER / 'assets')
    parser.add_argument('--work-dir', type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    work = args.work_dir or Path(tempfile.mkdtemp(prefix='biocoloop-paradigm-'))
    work.mkdir(parents=True, exist_ok=True)
    source_sha = sha(source)

    dest = work / f'{STEM}.pptx'
    shutil.copy2(source, dest)
    assert sha(dest) == source_sha, 'Copy must be byte-identical to the author deck'

    env = render_environment()
    subprocess.run(['soffice', f'-env:UserInstallation={(work / "render_profile").as_uri()}',
                    '--headless', '--convert-to', 'pdf:impress_pdf_Export',
                    '--outdir', str(work), str(dest)], env=env, check=True, timeout=180)
    check = subprocess.run([sys.executable, str(SKILL / 'slides_test.py'), str(dest)],
                           env=env, text=True, capture_output=True, timeout=300)
    (work / 'slides_test.txt').write_text(check.stdout + check.stderr)
    if check.returncode:
        raise RuntimeError('Slide overflow test failed: ' + check.stdout + check.stderr)

    doc = fitz.open(dest.with_suffix('.pdf'))
    assert len(doc) == 1, len(doc)
    page = doc[0]
    assert abs(page.rect.width / page.rect.height - SLIDE_ASPECT) < 5e-3, page.rect
    words = ' '.join(page.get_text().split())
    missing = [value for value in REQUIRED_WORDS if value not in words]
    assert not missing, missing
    assert 'AI4AI4Cell' not in words and 'federated' not in words.lower()
    outside = []
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines', []):
            for span in line.get('spans', []):
                if not (page.rect + (-0.5, -0.5, 0.5, 0.5)).contains(fitz.Rect(span['bbox'])):
                    outside.append(span['text'])
    assert not outside, outside

    aspect = page.rect.width / page.rect.height
    metadata = doc.metadata
    metadata.update(title='BioCoLoop: research settings for biological AI',
                    creator='BioCoLoop', author='')
    doc.set_metadata(metadata)
    pdf = output / f'{STEM}.pdf'
    doc.save(pdf, garbage=4, deflate=True)
    png = output / f'{STEM}.png'
    page.get_pixmap(matrix=fitz.Matrix(2000 / page.rect.width, 2000 / page.rect.width),
                    alpha=False).save(png)
    embedded = len(page.get_images())
    vector_paths = len(page.get_drawings())
    doc.close()

    editable = output / f'{STEM}.pptx'
    editable.write_bytes(dest.read_bytes())
    receipt = {
        'status': 'STRUCTURAL_CHECKS_PASSED_VISUAL_REVIEW_REQUIRED',
        'figure': 'Figure 1 (research settings for biological AI)',
        'authoring': 'author-supplied PowerPoint-native deck (icons are embedded raster assets)',
        'source_deck': str(source), 'source_deck_sha256': source_sha,
        'source_deck_unchanged': source_sha == sha(source),
        'declared_repairs': [],
        'aspect_ratio': f'{aspect:.4f}',
        'required_labels_present': REQUIRED_WORDS,
        'pdf_embedded_images': embedded,
        'vector_path_count': vector_paths,
        'text_outside_canvas': [],
        'slides_test_returncode': 0,
        'slides_test_output': check.stdout.strip(),
        'artifacts': {
            f'{STEM}.pptx': sha(editable),
            f'{STEM}.pdf': sha(pdf),
            f'{STEM}.png': sha(png),
        },
        'visual_review_required': True,
    }
    (output / f'{STEM}.provenance.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'status': 'EXPORTED', 'repairs': [], 'media': embedded,
                      'vector_paths': vector_paths}, indent=2))


if __name__ == '__main__':
    main()
