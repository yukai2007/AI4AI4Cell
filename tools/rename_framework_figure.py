"""Apply the BioCoLoop name to an existing editable slide without rebuilding it.

Only explicit UTF-8 wording substitutions are made inside XML archive members.
All drawing geometry, text-run formatting, arrows, icons and source assets are
retained byte-for-byte apart from the three declared wording substitutions.
The supplied source and the historical readable derivative are never modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.ElementTree as ET

import fitz
from PIL import Image

PAPER = Path(__file__).resolve().parents[1]
MAPPING = {
    "AI4AI4Cell": "BioCoLoop",
    "Federated Evidence-Guided Research Framework":
        "Collaborative Evidence-Guided Research Framework",
    "federated learning": "collaborative learning",
}
DRAWING_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_nodes(data: bytes) -> list[str]:
    return [node.text or "" for node in ET.fromstring(data).iter(
        f"{{{DRAWING_NS}}}t")]


def masked_text_tree(data: bytes) -> bytes:
    root = ET.fromstring(data)
    for node in root.iter(f"{{{DRAWING_NS}}}t"):
        node.text = "[TEXT]"
    return ET.tostring(root)


def render_environment() -> dict[str, str]:
    env = os.environ.copy()
    local = Path("/liziqing/yukai/.local/opt")
    env["PATH"] = ":".join(str(local / item) for item in [
        "libreoffice-26.2.5/opt/libreoffice26.2/program", "poppler/usr/bin",
        "fontconfig/usr/bin"]) + ":" + env["PATH"]
    env["LD_LIBRARY_PATH"] = ":".join(str(local / item) for item in [
        "lo-deps/usr/lib/x86_64-linux-gnu", "poppler/usr/lib/x86_64-linux-gnu",
        "fontconfig/usr/lib/x86_64-linux-gnu"])
    env["FONTCONFIG_FILE"] = str(local / "fontconfig/etc/fonts/fonts.conf")
    env["FONTCONFIG_PATH"] = str(local / "fontconfig/etc/fonts")
    return env


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=PAPER / "figures" /
                        "framework_user_20260923_readable_original_labels.pptx")
    parser.add_argument("--output-dir", type=Path, default=PAPER / "figures")
    parser.add_argument("--work-dir", type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    work = args.work_dir or Path(tempfile.mkdtemp(prefix="biocoloop-figure-"))
    work.mkdir(parents=True, exist_ok=True)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    source_sha = sha(source)
    dest = work / "biocoloop_framework.pptx"
    with ZipFile(source) as archive:
        original = {info.filename: archive.read(info) for info in archive.infolist()}
    updated = dict(original)
    changed_members = {}
    for name, data in original.items():
        if not name.endswith(".xml"):
            continue
        replacement = data
        counts = {}
        for before, after in MAPPING.items():
            count = replacement.count(before.encode())
            if count:
                counts[before] = count
                replacement = replacement.replace(before.encode(), after.encode())
        if replacement != data:
            updated[name] = replacement
            changed_members[name] = counts
            if name.startswith("ppt/slides/"):
                assert masked_text_tree(data) == masked_text_tree(replacement), name
    assert changed_members, "The expected source labels were not found"
    assert source_sha == sha(source), "Source must not be altered"
    with ZipFile(dest, "w", ZIP_DEFLATED) as archive:
        for name, data in updated.items():
            archive.writestr(name, data)
    with ZipFile(dest) as archive:
        assert set(archive.namelist()) == set(original)
        for name, data in original.items():
            if name not in changed_members:
                assert archive.read(name) == data, name

    subprocess.run([
        "soffice", f"-env:UserInstallation={(work / 'render_profile').as_uri()}",
        "--headless", "--convert-to", "pdf:impress_pdf_Export",
        "--outdir", str(work), str(dest)], env=render_environment(),
        check=True, timeout=90)
    source_receipt_path = source.with_suffix(".provenance.json")
    historical_receipt = json.loads(source_receipt_path.read_text())
    doc = fitz.open(dest.with_suffix(".pdf"))
    assert len(doc) == 1
    page = doc[0]
    crop = fitz.Rect(historical_receipt["crop_box_points"])
    page.set_cropbox(crop)
    metadata = doc.metadata
    metadata.update(title="BioCoLoop: Collaborative Evidence-Guided Research Framework",
                    creator="BioCoLoop", author="")
    doc.set_metadata(metadata)
    pdf = output / "biocoloop_framework.pdf"
    doc.save(pdf, garbage=4, deflate=True)
    doc.close()
    editable = output / "biocoloop_framework.pptx"
    shutil.copyfile(dest, editable)

    doc = fitz.open(pdf)
    page = doc[0]
    final_text = page.get_text()
    assert "BioCoLoop" in final_text
    assert "Collaborative Evidence-Guided" in final_text
    assert "AI4AI4Cell" not in final_text and "federated" not in final_text.lower()
    text_outside_crop = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                box = fitz.Rect(span["bbox"])
                if not (page.rect + (-0.5, -0.5, 0.5, 0.5)).contains(box):
                    text_outside_crop.append(span["text"])
    assert not text_outside_crop, text_outside_crop
    png = output / "biocoloop_framework.png"
    page.get_pixmap(matrix=fitz.Matrix(1500/page.rect.width, 1500/page.rect.width),
                    alpha=False).save(png)
    pix = page.get_pixmap(matrix=fitz.Matrix(1100/page.rect.width, 1100/page.rect.width),
                         alpha=False)
    preview = work / "biocoloop_framework_preview.jpg"
    Image.frombytes("RGB", [pix.width, pix.height], pix.samples).save(preview, quality=82)
    original_user_source = Path(historical_receipt["source"])
    receipt = {
        "framework_name": "BioCoLoop", "source": str(source),
        "source_sha256": source_sha, "source_unchanged": source_sha == sha(source),
        "original_user_source": str(original_user_source),
        "original_user_source_sha256": sha(original_user_source),
        "original_user_source_unchanged": sha(original_user_source) ==
            historical_receipt["source_sha256"],
        "source_provenance": str(source_receipt_path),
        "text_mapping": MAPPING, "changed_xml_members": changed_members,
        "geometry_and_text_formatting_identical": True,
        "all_unmodified_archive_members_byte_identical": True,
        "source_text_identical": False,
        "labels_retained": ["Laboratory 10", "Designs", "Programs", "Policies"],
        "derived_editable_pptx": str(editable), "derived_pptx_sha256": sha(editable),
        "vector_pdf": str(pdf), "vector_pdf_sha256": sha(pdf),
        "png_preview": str(png), "png_sha256": sha(png),
        "small_preview": str(preview), "crop_box_points": list(crop),
        "vector_path_count": len(page.get_drawings()),
        "embedded_images": len(page.get_images()),
        "text_outside_crop": text_outside_crop,
        "final_visual_review_required": True,
    }
    doc.close()
    receipt_path = output / "biocoloop_framework.provenance.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
