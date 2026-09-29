"""Extract/render an author-selected PDF for source review; no result changes."""
import argparse
import difflib
import hashlib
import json
import re
import textwrap
from pathlib import Path
import fitz


def pages(path):
    result = []
    for page in fitz.open(path):
        raw = page.get_text(clip=fitz.Rect(98, 77, 560, 742))
        clean = raw.replace("\ufb01", "fi").replace("\ufb02", "fl").replace("\ufb00", "ff").replace("\ufb03", "ffi")
        result.append(re.sub(r"([A-Za-z])-\n([a-z])", r"\1\2", clean))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--compare", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    extracted = pages(args.source)
    record = {"source": str(args.source), "sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
              "page_count": len(extracted), "pages": extracted}
    (args.output / "pages.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    (args.output / "pages.txt").write_text("\n".join(f"\n=== PAGE {i + 1} ===\n{p}" for i, p in enumerate(extracted)))
    if args.compare:
        old = textwrap.wrap(" ".join(" ".join(pages(args.compare)).split()), 110)
        new = textwrap.wrap(" ".join(" ".join(extracted).split()), 110)
        (args.output / "text.diff").write_text("\n".join(difflib.unified_diff(old, new, fromfile=str(args.compare), tofile=str(args.source))) + "\n")
    if args.render:
        for i, page in enumerate(fitz.open(args.source)):
            page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(args.output / f"page_{i + 1:02d}.png")
    print(f"Extracted {len(extracted)} pages: {args.output}")


if __name__ == "__main__":
    main()
