"""Adopt the author-supplied editable paradigm deck as Figure 1.

``/liziqing/yukai/AI4AI4Cell/paradigm_comparison_editable.pptx`` becomes the
active Figure 1.  The author's original file is never modified; the copy stored
here carries two declared, content-preserving layout repairs that remove the
empty band the author deck left at the bottom of the canvas and centre the
middle panel in its own column:

1. ``trim_canvas``: the slide height is reduced from 7,045,325 EMU to
   6,714,176 EMU, so the bottom margin below the panel rules matches the top
   margin (187,372 EMU) instead of being 2.8x larger.  Nothing is clipped: the
   lowest drawn object ends at 6,526,804 EMU.
2. ``centre_middle_panel``: the nineteen movable objects of panel (b) below its
   title are translated down by 125,938 EMU, the amount that centres that
   panel's content between the panel title row and the canvas bottom.  Panel
   (b) holds less content than (a) and (c), so this distributes its slack
   instead of leaving it pooled below the panel.

The tool renders the PDF/PNG used by the manuscript, runs the slide-overflow
check and records a provenance receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adapt_framework_v3 import render_environment  # noqa: E402

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parent
SKILL = Path('/liziqing/yukai/.codex/skills/slides/scripts')
DEFAULT_SOURCE = ROOT / 'paradigm_comparison_editable.pptx'
STEM = 'paradigm_comparison_v3'
SLIDE_XML = 'ppt/slides/slide1.xml'
PRESENTATION_XML = 'ppt/presentation.xml'
SLIDE_SIZE = '<p:sldSz cx="12192000" cy="7045325"/>'
TRIMMED_SIZE = '<p:sldSz cx="12192000" cy="6714176"/>'
SLIDE_ASPECT = 12192000 / 6714176
# The middle panel holds less content than its neighbours, so its content band is
# centred between the panel-title row and the canvas bottom.
PANEL_B_SHIFT = 125938
PANEL_B_X_RANGE = (4100000, 8150000)
PANEL_B_MIN_Y = 1000000
PANEL_B_OBJECTS = 19
ELEMENT_RE = re.compile(r'<p:(sp|pic|cxnSp|graphicFrame)>')
OFF_RE = re.compile(r'<a:off x="(-?\d+)" y="(-?\d+)"/><a:ext cx="(-?\d+)" cy="(\d+)"/>')
REQUIRED_WORDS = [
    '(a)', 'Centralized bio-agent', '(b)', 'Collaborative training', '(c)', 'BioCoLoop',
    'Research / design loop', 'Accessible dataset', 'Accessible data', 'model parameters',
    'Design revision', 'Aggregate development evidence', 'Lab 1', 'Lab 2', 'Lab K',
    'Local update', 'Model', '(design fixed in advance)', '(design revised between rounds)',
]


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_copy(source: Path, dest: Path) -> list[dict]:
    """Apply the declared layout repairs to a copy of the author deck."""
    with ZipFile(source) as archive:
        original = {info.filename: archive.read(info) for info in archive.infolist()}
    for member in (SLIDE_XML, PRESENTATION_XML):
        assert member in original, member

    presentation = original[PRESENTATION_XML].decode('utf-8')
    assert presentation.count(SLIDE_SIZE) == 1, 'slide size changed upstream'
    presentation = presentation.replace(SLIDE_SIZE, TRIMMED_SIZE)

    xml = original[SLIDE_XML].decode('utf-8')
    starts = [match.start() for match in ELEMENT_RE.finditer(xml)]
    pieces, moved, cursor = [], 0, 0
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(xml)
        block = xml[start:end]
        match = OFF_RE.search(block)
        if match is None:
            continue
        x, y, cx, _ = (int(value) for value in match.groups())
        centre = x + cx / 2
        if not (y >= PANEL_B_MIN_Y and PANEL_B_X_RANGE[0] < centre < PANEL_B_X_RANGE[1]):
            continue
        replacement = (f'<a:off x="{x}" y="{y + PANEL_B_SHIFT}"/>'
                       f'<a:ext cx="{cx}" cy="{int(match.group(4))}"/>')
        pieces.append(xml[cursor:start + match.start()])
        pieces.append(replacement)
        cursor = start + match.end()
        moved += 1
    pieces.append(xml[cursor:])
    xml = ''.join(pieces)
    assert moved == PANEL_B_OBJECTS, moved

    updated = dict(original)
    updated[SLIDE_XML] = xml.encode('utf-8')
    updated[PRESENTATION_XML] = presentation.encode('utf-8')
    with ZipFile(dest, 'w', ZIP_DEFLATED) as archive:
        for name, data in updated.items():
            archive.writestr(name, data)
    with ZipFile(dest) as archive:
        assert set(archive.namelist()) == set(original)
    edits = [
        {'id': 'trim_canvas', 'shape': 'p:sldSz', 'change': 'cy 7045325 -> 6714176 EMU',
         'reason': 'bottom canvas margin matched to the 187372 EMU top margin; nothing clipped'},
        {'id': 'centre_middle_panel', 'shape': f'{PANEL_B_OBJECTS} panel-(b) objects',
         'change': f'translate down by {PANEL_B_SHIFT} EMU',
         'reason': 'centre the sparse middle panel between its title row and the canvas bottom'},
    ]
    return edits


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
    edits = build_copy(source, dest)
    assert sha(source) == source_sha, 'Source deck must not be altered'

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
        'declared_repairs': edits,
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
    print(json.dumps({'status': 'EXPORTED', 'repairs': [e['id'] for e in edits],
                      'media': embedded, 'vector_paths': vector_paths}, indent=2))


if __name__ == '__main__':
    main()
