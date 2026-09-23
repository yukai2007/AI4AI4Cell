"""Extract every second-round annotation and full page text without overwriting v1."""
from pathlib import Path
import hashlib
import json
import fitz

PAPER = Path(__file__).resolve().parents[1]
SOURCE = PAPER.parent / "AI4AI4Cellv2-yc.pdf"
OUT = PAPER / "provenance/coauthor_review_v2_20260923"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    document = fitz.open(SOURCE)
    records, pages = [], []
    for page in document:
        pages.append(dict(page=page.number + 1, text=page.get_text()))
        words = page.get_text("words")
        for annotation in page.annots() or []:
            vertices = annotation.vertices or []
            selected = []
            for start in range(0, len(vertices), 4):
                rect = fitz.Quad(vertices[start:start + 4]).rect
                selected.extend(w[4] for w in words if rect.contains(
                    fitz.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)))
            box = annotation.rect
            records.append(dict(page=page.number + 1, xref=annotation.xref,
                kind=annotation.type[1], author=annotation.info.get("title", ""),
                comment=annotation.info.get("content", ""),
                highlighted_text=" ".join(selected), rect=list(box), vertices=vertices,
                nearby_text=page.get_textbox(fitz.Rect(55, max(0, box.y0 - 45),
                    min(page.rect.width, 560), min(page.rect.height, box.y1 + 45))),
                metadata=annotation.info))
    payload = dict(source_name=SOURCE.name, sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                   pages=len(document), annotations=records)
    (OUT / "annotations.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    (OUT / "page_text.json").write_text(json.dumps(pages, ensure_ascii=False, indent=2) + "\n")
    lines = ["# 第二轮批注原文与锚点", "", f"来源：{SOURCE.name}", "",
             f"SHA-256：`{payload['sha256']}`", "",
             f"共 {len(document)} 页；{len(records)} 个批注对象。空文字高亮也全部保留。", ""]
    for number, record in enumerate(records, 1):
        lines += [f"## V2-{number:02d} / P{record['page']} / xref {record['xref']} / {record['kind']}", "",
                  "批注：" + (record["comment"] or "（无文字，保留高亮锚点）"), "",
                  "锚点：" + (record["highlighted_text"] or record["nearby_text"]), ""]
    (OUT / "ANNOTATIONS.zh-CN.md").write_text("\n".join(lines) + "\n")
    render = PAPER / "tmp/pdfs/coauthor_review_v2_20260923"
    render.mkdir(parents=True, exist_ok=True)
    for number in sorted({record["page"] - 1 for record in records} | {0}):
        document[number].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), annots=True).save(
            render / f"annotated_page_{number + 1:02d}.png")
    print(json.dumps(dict(pages=len(document), annotations=len(records),
        text_comments=sum(bool(record["comment"]) for record in records), output=str(OUT)), ensure_ascii=False))


if __name__ == "__main__":
    main()
