"""Adopt the author-supplied repaired deck as Figure 2 (framework v3).

``/liziqing/yukai/AI4AI4Cell/0925_repaired_v3.pptx`` becomes the active Figure 2.
The author's original file is never modified; declared, geometry-preserving
repairs are applied only to the copy stored in this repository:

1. the two ``mc:AlternateContent`` wrappers around the text blocks that contain
   the in-text math variable ``S`` are flattened.  Each wrapper offers an
   Office-2010 ``a14`` choice (the real text) and a fallback that is a clipped
   screenshot of the same block; the exporter followed the fallback, so the
   flattened choice branch carries the vector text and the screenshots are
   dropped.
2. the two OMML math runs are rewritten as ordinary italic text runs at the
   same size and colour, so no Office-2010 math extension is required.
3. the ``Propose`` card body text is set to 11 pt and its box is enlarged so
   that the final line (``design id``) is no longer clipped.
4. the ``Fixed research language model`` label is darkened from 65 % to 45 %
   luminance so it stays legible after journal-size scaling.
5. the standalone italic caption ``Raw data remain within each laboratory`` is
   deleted at the authors' request: data locality is already stated in the
   manuscript text and carried by the lock icons and ``private data`` labels of
   the laboratory cards, so the caption only repeated it.
Steps 1 and 2 together remove every Office-2010 math extension and every
clipped screenshot from the figure.

The tool renders the PDF/PNG used by the manuscript, runs the slide-overflow
check and records a provenance receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile

import fitz

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parent
SKILL = Path('/liziqing/yukai/.codex/skills/slides/scripts')
DEFAULT_SOURCE = ROOT / '0925_repaired_v3.pptx'

SLIDE_MEMBER = 'ppt/slides/slide1.xml'
SP_RE = re.compile(r'<p:sp>.*?</p:sp>', re.S)
ALTERNATE_RE = re.compile(
    r'<mc:AlternateContent[^>]*>\s*<mc:Choice[^>]*>(.*?)</mc:Choice>\s*'
    r'<mc:Fallback>(.*?)</mc:Fallback>\s*</mc:AlternateContent>', re.S)
MATH_RE = re.compile(
    r'<a14:m><m:oMath[^>]*><m:r>(<a:rPr[^>]*>.*?</a:rPr>)<m:t>(.*?)</m:t>'
    r'</m:r></m:oMath></a14:m>', re.S)
PROPOSE_BOX = ('<a:off x="1359582" y="1703828"/><a:ext cx="1400353" cy="771818"/>',
               '<a:off x="1359582" y="1663700"/><a:ext cx="1400353" cy="905000"/>')
REQUIRED_WORDS = [
    'OUTER RESEARCH LOOP', 'INNER COLLABORATIVE TRAINING', 'Propose', 'Instantiate',
    'Train + evaluate', 'Retain / revise', 'Shared coordinator', 'Laboratory 1',
    'Laboratory 2', 'Laboratory K', 'private', 'model', 'OUTPUTS', 'Designs',
    'Programs', 'Policies', 'BIOLOGICAL VALIDATION SETTINGS', 'Drug–target',
    'Proteomic efficacy', 'Cell perturbations',
    'generates new hypothesis', 'design id', 'Fixed research language model',
]


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def render_environment() -> dict[str, str]:
    env = os.environ.copy()
    local = Path('/liziqing/yukai/.local/opt')
    env['PATH'] = ':'.join(str(local / item) for item in [
        'libreoffice-26.2.5/opt/libreoffice26.2/program', 'poppler/usr/bin',
        'fontconfig/usr/bin']) + ':' + env['PATH']
    env['LD_LIBRARY_PATH'] = ':'.join(str(local / item) for item in [
        'lo-deps/usr/lib/x86_64-linux-gnu', 'poppler/usr/lib/x86_64-linux-gnu',
        'fontconfig/usr/lib/x86_64-linux-gnu'])
    env['FONTCONFIG_FILE'] = str(local / 'fontconfig/etc/fonts/fonts.conf')
    env['FONTCONFIG_PATH'] = str(local / 'fontconfig/etc/fonts')
    return env


def apply_declared_repairs(xml: str) -> tuple[str, list[dict]]:
    edits: list[dict] = []

    dropped_rids = []
    while True:
        match = ALTERNATE_RE.search(xml)
        if match is None:
            break
        dropped_rids.extend(re.findall(r'<a:blip r:embed="(rId\d+)"/>', match.group(2)))
        xml = xml[:match.start()] + match.group(1) + xml[match.end():]
    assert sorted(dropped_rids) == ['rId14', 'rId19'], dropped_rids
    edits.append({'id': 'flatten_alternate_content', 'shape': 'mc:Choice (a14)',
                  'change': 'unwrap mc:AlternateContent, keep a14 choice, drop fallback',
                  'dropped_fallback_screenshots': sorted(dropped_rids),
                  'reason': 'fallback screenshots were clipped and hid the vector text'})

    for block in SP_RE.findall(xml):
        match = MATH_RE.search(block)
        if match is None:
            continue
        run_props = re.sub(r'\s+smtClean="\d+"', '', match.group(1))
        assert 'i="1"' in run_props, run_props
        replacement = f'<a:r>{run_props}<a:t>{match.group(2)}</a:t></a:r>'
        xml = xml.replace(block, block.replace(match.group(0), replacement))
        edits.append({'id': 'math_run_to_text', 'shape': 'oMath run',
                      'change': 'OMML math run "S" -> italic text run (same size and colour)',
                      'reason': 'removes the Office-2010 math extension dependency'})
    assert sum(e['id'] == 'math_run_to_text' for e in edits) == 2, edits

    for block in SP_RE.findall(xml):
        if 'generates new hypothesis' not in block:
            continue
        assert PROPOSE_BOX[0] in block, 'Propose card geometry changed upstream'
        repaired = block.replace(*PROPOSE_BOX)
        sizes = set(re.findall(r'sz="(\d+)"', repaired))
        assert sizes == {'1200'}, sizes
        xml = xml.replace(block, repaired.replace('sz="1200"', 'sz="1100"'))
        edits.append({'id': 'propose_card_fit', 'shape': 'Text 32',
                      'change': 'box height 0.84 in -> 0.99 in, body 12 pt -> 11 pt',
                      'reason': 'final line "design id" was clipped by the text box'})

    for block in SP_RE.findall(xml):
        if 'Fixed research language model' not in block:
            continue
        assert block.count('lumMod val="65000"') == 4, block.count('lumMod val="65000"')
        xml = xml.replace(block, block.replace('lumMod val="65000"', 'lumMod val="45000"'))
        edits.append({'id': 'fixed_model_label_contrast', 'shape': 'Text 3',
                      'change': 'label luminance 65 % -> 45 %',
                      'reason': 'label was near-invisible after figure scaling'})

    removed_note = False
    for block in SP_RE.findall(xml):
        if 'Raw data remain within each laboratory' not in block:
            continue
        assert 'name="Text 83"' in block, 'local-data caption shape changed upstream'
        xml = xml.replace(block, '')
        removed_note = True
        edits.append({'id': 'drop_local_data_note', 'shape': 'Text 83',
                      'change': 'delete the standalone caption '
                                '"Raw data remain within each laboratory"',
                      'reason': 'authors asked to drop it; locality is stated in the text and '
                                'carried by the lock icons and private-data labels'})
    assert removed_note, 'local-data caption not found'

    assert '<a:blipFill>' not in xml, 'unexpected picture-filled shape remains'
    assert '<a14:m>' not in xml and 'mc:AlternateContent' not in xml
    return xml, edits


def build_copy(source: Path, dest: Path) -> tuple[list[dict], list[str]]:
    with ZipFile(source) as archive:
        original = {info.filename: archive.read(info) for info in archive.infolist()}
    assert SLIDE_MEMBER in original, 'Single-slide deck expected'
    repaired, edits = apply_declared_repairs(original[SLIDE_MEMBER].decode('utf-8'))
    rels = original['ppt/slides/_rels/slide1.xml.rels'].decode('utf-8')
    rid_to_media = {rid: 'ppt/' + name for rid, name in re.findall(
        r'Id="(rId\d+)"[^>]*Target="\.\./(media/[^"]+)"', rels)}
    placed = sorted({rid_to_media[rid] for rid in re.findall(r'r:embed="(rId\d+)"', repaired)
                     if rid in rid_to_media})
    updated = dict(original)
    updated[SLIDE_MEMBER] = repaired.encode('utf-8')
    with ZipFile(dest, 'w', ZIP_DEFLATED) as archive:
        for name, data in updated.items():
            archive.writestr(name, data)
    with ZipFile(dest) as archive:
        assert set(archive.namelist()) == set(original)
        for name, data in original.items():
            if name != SLIDE_MEMBER:
                assert archive.read(name) == data, name
    return edits, placed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--output-dir', type=Path, default=PAPER / 'figures')
    parser.add_argument('--work-dir', type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    work = args.work_dir or Path(tempfile.mkdtemp(prefix='biocoloop-v3-'))
    work.mkdir(parents=True, exist_ok=True)
    source_sha = sha(source)

    dest = work / 'biocoloop_framework_v3.pptx'
    edits, placed = build_copy(source, dest)
    assert source_sha == sha(source), 'Source deck must not be altered'

    env = render_environment()
    subprocess.run(['soffice', f'-env:UserInstallation={(work / "render_profile").as_uri()}',
                    '--headless', '--convert-to', 'pdf:impress_pdf_Export',
                    '--outdir', str(work), str(dest)], env=env, check=True, timeout=180)
    check = subprocess.run([sys.executable, str(SKILL / 'slides_test.py'), str(dest)],
                           env=env, text=True, capture_output=True, timeout=300)
    (work / 'slides_test.txt').write_text(check.stdout + check.stderr)
    if check.returncode:
        raise RuntimeError('Slide overflow test failed: ' + check.stdout + check.stderr)

    with ZipFile(dest) as archive:
        media = sorted(name for name in archive.namelist()
                       if name.startswith('ppt/media/') and not name.endswith('/'))
    doc = fitz.open(dest.with_suffix('.pdf'))
    assert len(doc) == 1, len(doc)
    page = doc[0]
    assert abs(page.rect.width / page.rect.height - 4 / 3) < 5e-3, page.rect
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

    metadata = doc.metadata
    metadata.update(title='BioCoLoop: collaborative evidence-guided research framework',
                    creator='BioCoLoop', author='')
    doc.set_metadata(metadata)
    pdf = output / 'biocoloop_framework_v3.pdf'
    doc.save(pdf, garbage=4, deflate=True)
    png = output / 'biocoloop_framework_v3.png'
    page.get_pixmap(matrix=fitz.Matrix(2000 / page.rect.width, 2000 / page.rect.width),
                    alpha=False).save(png)
    embedded = len(page.get_images())
    vector_paths = len(page.get_drawings())
    doc.close()

    editable = output / 'biocoloop_framework_v3.pptx'
    editable.write_bytes(dest.read_bytes())
    receipt = {
        'status': 'STRUCTURAL_CHECKS_PASSED_VISUAL_REVIEW_REQUIRED',
        'figure': 'Figure 2 (BioCoLoop framework)',
        'authoring': 'author-supplied PowerPoint-native deck (icons are embedded raster assets)',
        'source_deck': str(source), 'source_deck_sha256': source_sha,
        'source_deck_unchanged': source_sha == sha(source),
        'declared_repairs': edits,
        'aspect_ratio': '4:3',
        'required_labels_present': REQUIRED_WORDS,
        'embedded_raster_assets': media,
        'placed_raster_assets': placed,
        'pdf_embedded_images': embedded,
        'vector_path_count': vector_paths,
        'text_outside_canvas': [],
        'slides_test_returncode': 0,
        'slides_test_output': check.stdout.strip(),
        'artifacts': {
            'biocoloop_framework_v3.pptx': sha(editable),
            'biocoloop_framework_v3.pdf': sha(pdf),
            'biocoloop_framework_v3.png': sha(png),
        },
        'visual_review_required': True,
    }
    (output / 'biocoloop_framework_v3.provenance.json').write_text(
        json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'status': 'EXPORTED', 'edits': [e['id'] for e in edits],
                      'media': len(media), 'vector_paths': vector_paths}, indent=2))


if __name__ == '__main__':
    main()
