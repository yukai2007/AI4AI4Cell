#!/usr/bin/env python3
"""Export edited PPTX files to a separate preview directory; never publish artwork.

Usage: python3 figure_editing/export_preview.py path/to/Figure_2_edited.pptx
Requires LibreOffice, Poppler, PyMuPDF and the installed slides skill utilities.
Existing paper sources and edited PPTX files remain untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import fitz

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
SKILL = Path('/liziqing/yukai/.codex/skills/slides/scripts')


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_environment() -> dict[str, str]:
    if shutil.which('soffice') and shutil.which('pdftoppm'):
        return os.environ.copy()
    # Reuse this repository's local tool installation; no global font/config edits.
    sys.path.insert(0, str(PAPER / 'tools'))
    from rename_framework_figure import render_environment
    return render_environment()


def inspect_native(path: Path) -> dict:
    with ZipFile(path) as archive:
        names = archive.namelist()
        slide_names = [n for n in names if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
        chart_names = [n for n in names if n.startswith('ppt/charts/chart') and n.endswith('.xml')]
        sheets = [n for n in names if n.startswith('ppt/embeddings/') and n.endswith('.xlsx')]
        media = [n for n in names if n.startswith('ppt/media/') and not n.endswith('/')]
        roots = [ET.fromstring(archive.read(n)) for n in slide_names]
        ns = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
              'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
        return dict(slides=len(slide_names), native_shapes=sum(len(r.findall('.//p:sp', ns)) for r in roots),
                    native_charts=len(chart_names), editable_workbooks=len(sheets), embedded_media=media,
                    slide_fonts=sorted({e.get('typeface') for r in roots for e in r.findall('.//a:latin', ns)}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pptx', type=Path, nargs='+')
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    base = (args.output_dir or Path(tempfile.mkdtemp(prefix='biocoloop-figure-preview-'))).resolve()
    base.mkdir(parents=True, exist_ok=True)
    env = export_environment()
    results = []
    for source in args.pptx:
        source = source.resolve(strict=True)
        if source.suffix.lower() != '.pptx':
            raise ValueError('Expected .pptx: ' + str(source))
        target = base / source.stem
        target.mkdir(parents=True, exist_ok=True)
        if target == source.parent or target in (PAPER / 'assets', PAPER / 'figures'):
            raise ValueError('Preview directory must be separate from source and active artwork.')
        before = digest(source)
        pdf = target / (source.stem + '.pdf')
        if pdf.exists():
            raise FileExistsError('Choose a fresh output directory: ' + str(pdf))
        with tempfile.TemporaryDirectory(prefix='biocoloop-edit-export-') as profile:
            subprocess.run(['soffice', '-env:UserInstallation=' + Path(profile).as_uri(), '--headless',
                            '--convert-to', 'pdf:impress_pdf_Export', '--outdir', str(target), str(source)],
                           env=env, check=True, timeout=90)
        subprocess.run([sys.executable, str(SKILL / 'render_slides.py'), str(source),
                        '--output_dir', str(target / 'rendered')], env=env, check=True, timeout=120)
        check = subprocess.run([sys.executable, str(SKILL / 'slides_test.py'), str(source)],
                               env=env, capture_output=True, text=True, timeout=120)
        native = inspect_native(source)
        with fitz.open(pdf) as doc:
            exported = dict(pages=len(doc), embedded_images=sum(len(p.get_images()) for p in doc),
                            vector_paths=sum(len(p.get_drawings()) for p in doc),
                            fonts=sorted({f[3] for p in doc for f in p.get_fonts()}))
        assert digest(source) == before, 'The edited deck must remain unchanged.'
        result = dict(source=str(source), source_sha256=before, pdf=str(pdf), pdf_sha256=digest(pdf),
                      native=native, exported=exported, overflow_returncode=check.returncode,
                      overflow_output=check.stdout + check.stderr,
                      visual_review='REQUIRED', manuscript_artwork_replaced=False)
        (target / 'export_receipt.json').write_text(json.dumps(result, indent=2) + '\n')
        results.append(result)
        print(json.dumps(result, indent=2), flush=True)
        if check.returncode:
            raise RuntimeError('Overflow check failed; review ' + str(target))
    print('Preview only. Paper integration requires visual and numerical review.', flush=True)


if __name__ == '__main__':
    main()
