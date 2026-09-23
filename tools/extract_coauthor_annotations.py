"""Preserve every review annotation and its on-page anchor before editing."""
from pathlib import Path
import hashlib
import json

import fitz

PAPER = Path(__file__).resolve().parents[1]
SOURCE = PAPER.parent / "AI4AI4Cell (7)(1).pdf"
OUT = PAPER / "provenance/coauthor_review_20260922"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(SOURCE)
    records = []
    for page in doc:
        words = page.get_text("words")
        for annot in page.annots():
            selected = []
            vertices = annot.vertices or []
            for start in range(0, len(vertices), 4):
                rect = fitz.Quad(vertices[start:start + 4]).rect
                selected.extend(w[4] for w in words
                                if rect.contains(fitz.Point((w[0] + w[2]) / 2,
                                                           (w[1] + w[3]) / 2)))
            records.append({
                "page": page.number + 1, "xref": annot.xref,
                "kind": annot.type[1], "author": annot.info.get("title", ""),
                "comment": annot.info.get("content", ""),
                "highlighted_text": " ".join(selected),
                "rect": list(annot.rect), "vertices": vertices,
                "nearby_text": page.get_textbox(fitz.Rect(
                    95, max(0, annot.rect.y0 - 25), 510,
                    min(page.rect.height, annot.rect.y1 + 25))),
                "metadata": annot.info,
            })
    payload = {"source_name": SOURCE.name,
               "sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
               "pages": len(doc), "annotations": records}
    (OUT / "annotations.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    lines = ["# 师姐批注原文与锚点", "", f"来源：{SOURCE.name}",
             f"SHA-256：`{payload['sha256']}`", "",
             f"共 {len(doc)} 页，{len(records)} 个批注标记；保留空文本高亮以便与旁边便笺配对。", ""]
    for rec in records:
        lines += [f"## P{rec['page']} / xref {rec['xref']} / {rec['kind']}", "",
                  "批注：" + (rec["comment"] or "（无文字高亮，见相邻便笺）"), "",
                  "锚点：" + (rec["highlighted_text"] or rec["nearby_text"]), ""]
    (OUT / "ANNOTATIONS.zh-CN.md").write_text("\n".join(lines))
    render = PAPER / "tmp/pdfs/coauthor_review_20260922"
    render.mkdir(parents=True, exist_ok=True)
    for p in (0, 1, 2, 3, 4, 6, 7, 8, 9):
        doc[p].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), annots=True).save(
            render / f"annotated_page_{p + 1:02}.png")
    print(f"Preserved {len(records)} annotations; "
          f"{sum(bool(r['comment']) for r in records)} with text.")


if __name__ == "__main__":
    main()
