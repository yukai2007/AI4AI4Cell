"""Export/inspect an authored native-vector PPTX; never rebuild presentation content."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZipFile

import fitz
from PIL import Image

from rename_framework_figure import render_environment

PAPER = Path(__file__).resolve().parents[1]
SKILL = Path('/liziqing/yukai/.codex/skills/slides/scripts')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    work = args.work_dir.resolve()
    source = work / 'biocoloop_framework_v2.pptx'
    old = PAPER / 'figures/biocoloop_framework.pptx'
    old_digest = sha(old)
    environment = render_environment()
    profile = Path(tempfile.mkdtemp(prefix='biocoloop-v2-soffice-'))
    subprocess.run(['soffice', f'-env:UserInstallation={profile.as_uri()}', '--headless',
                    '--convert-to', 'pdf:impress_pdf_Export', '--outdir', str(work), str(source)],
                   env=environment, check=True, timeout=90)
    pdf = source.with_suffix('.pdf')
    subprocess.run([sys.executable, str(SKILL / 'render_slides.py'), str(source),
                    '--output_dir', str(work / 'rendered')], env=environment, check=True, timeout=120)
    check = subprocess.run([sys.executable, str(SKILL / 'slides_test.py'), str(source)],
                           env=environment, text=True, capture_output=True, timeout=120)
    (work / 'slides_test.txt').write_text(check.stdout + check.stderr)
    if check.returncode:
        raise RuntimeError('Slide overflow test failed: ' + check.stdout + check.stderr)
    with ZipFile(source) as archive:
        images = [name for name in archive.namelist() if name.startswith('ppt/media/') and not name.endswith('/')]
        assert not images, images
    doc = fitz.open(pdf)
    page = doc[0]
    assert len(doc) == 1 and abs(page.rect.width / page.rect.height - 4/3) < .001
    words = page.get_text()
    required = ['Lab 1', 'Lab 2', 'Lab K', 'Scenario A', 'Scenario B', 'Scenario K',
                'Drug-target interactions', 'Proteomic efficacy', 'Cell perturbations',
                'Candidate design', 'Development', 'evidence', 'Research history', 'fitted predictor']
    missing = [value for value in required if value not in words]
    assert not missing, missing
    assert 'Programs' not in words and 'Policies' not in words and 'Laboratory 10' not in words
    outside = []
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines', []):
            for span in line.get('spans', []):
                if not (page.rect + (-.5, -.5, .5, .5)).contains(fitz.Rect(span['bbox'])):
                    outside.append(span['text'])
    assert not outside, outside
    png = source.with_suffix('.png')
    pix = page.get_pixmap(matrix=fitz.Matrix(1800/page.rect.width, 1800/page.rect.width), alpha=False)
    pix.save(png)
    view = page.get_pixmap(matrix=fitz.Matrix(1200/page.rect.width, 1200/page.rect.width), alpha=False)
    Image.frombytes('RGB', [view.width, view.height], view.samples).save(work / 'preview.jpg', quality=88)
    receipt = dict(status='STRUCTURAL_CHECKS_PASSED_VISUAL_REVIEW_REQUIRED',
        edition='coauthor-review-v2', authoring='PptxGenJS PowerPoint-native shapes and text',
        source_js=str(PAPER / 'tools/draw_framework_v2.js'), source_js_sha256=sha(PAPER / 'tools/draw_framework_v2.js'),
        exporter_sha256=sha(__file__), old_editable_source_unchanged=sha(old) == old_digest,
        old_editable_source_sha256=old_digest, aspect_ratio='4:3', embedded_raster_assets=images,
        pdf_embedded_images=len(page.get_images()), vector_path_count=len(page.get_drawings()),
        text_outside_canvas=outside, slides_test_returncode=check.returncode,
        slides_test_output=check.stdout.strip(), minimum_native_font_pt=13.2,
        artifacts={path.name: sha(path) for path in (source, pdf, png)},
        layout=Path(work / 'biocoloop_framework_v2.layout.json').name,
        visual_review_required=True)
    doc.close()
    target = work / 'biocoloop_framework_v2.provenance.json'
    target.write_text(json.dumps(receipt, indent=2) + '\n')
    if args.publish:
        for asset in (source, pdf, png, target, work / 'biocoloop_framework_v2.layout.json'):
            shutil.copyfile(asset, PAPER / 'figures' / asset.name)
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
