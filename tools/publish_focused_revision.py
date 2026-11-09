"""Validate and publish the outcome-independent prose consolidation.

All included table/figure assets must remain byte-identical to the preceding
review revision. Previous versioned PDFs and receipts are never overwritten.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess

import finalize_fbhk_followup as checks

ROOT = Path(__file__).resolve().parents[1]
BASE = "b9f17132efc35a2daf9802f011a30fadac149c29"
DEST = ROOT / "provenance/focused_revision_20261110"
OLD_PDF = "output/pdf/BioCoLoop_FBhK_revision_20261109.pdf"
VERSIONED = "output/pdf/BioCoLoop_focused_revision_20261110.pdf"


def original(name):
    return subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=ROOT)


def graph(previous):
    seen = set()

    def visit(name):
        if name in seen:
            return
        seen.add(name)
        raw = original(name) if previous else (ROOT / name).read_bytes()
        text = re.sub(r"(?m)(?<!\\)%.*$", "", raw.decode())
        for child in re.findall(r"\\input\{([^}]+)\}", text):
            visit(child if child.endswith(".tex") else child + ".tex")

    visit("main.tex")
    return seen


def integrity():
    old_graph, new_graph = graph(True), graph(False)
    checks.require(old_graph == new_graph, "Included LaTeX content was removed or added")
    protected = [name for name in new_graph if name.startswith("tables/")]
    assets = set()
    for name in new_graph:
        old_text = original(name).decode()
        new_text = (ROOT / name).read_text()
        pattern = r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}"
        old_figs, new_figs = re.findall(pattern, old_text), re.findall(pattern, new_text)
        checks.require(old_figs == new_figs, "Figure omitted or changed in " + name)
        assets.update(old_figs)
    protected += sorted(assets)
    protected += [OLD_PDF, "provenance/fbhk_followup_20261109/build_receipt.json"]
    for name in protected:
        checks.require((ROOT / name).read_bytes() == original(name), "Protected result/version changed: " + name)
    word_counts = {}
    for name in sorted(new_graph):
        if name.startswith("sections/"):
            before = len(original(name).decode().split())
            after = len((ROOT / name).read_text().split())
            if before != after:
                word_counts[name] = {"before": before, "after": after}
    return {
        "previous_revision": BASE,
        "included_tex_files_unchanged": len(new_graph),
        "table_assets_unchanged": len([n for n in protected if n.startswith("tables/")]),
        "figure_assets_unchanged": len(assets),
        "previous_pdf_preserved": True,
        "word_counts_whitespace_tokens": word_counts,
    }


def table_map(aux):
    pattern = r"\\newlabel\{([^}]+)\}\{\{([^}]+)\}\{([^}]+)\}"
    return {
        name: {"number": number, "pdf_page": int(page)}
        for name, number, page in re.findall(pattern, aux.read_text())
        if name.startswith(("tab:", "fig:")) and page.isdigit()
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    receipt = checks.verify(args.pdf, args.log, checks.REPLY)
    receipt.update(integrity())
    receipt["schema"] = "focused-prose-revision-v1"
    receipt["new_experiments"] = 0
    receipt["result_rows_removed"] = 0
    receipt["source_sha256"]["tools/publish_focused_revision.py"] = checks.sha(Path(__file__))
    for name in ("CHANGES.zh-CN.md", "REMAINING_ISSUES.zh-CN.md"):
        path = DEST / name
        receipt["source_sha256"][str(path.relative_to(ROOT))] = checks.sha(path)
    receipt["compiled_number_map"] = table_map(args.pdf.with_suffix(".aux"))
    if args.publish:
        for name, digest in receipt["source_sha256"].items():
            checks.require(checks.sha(ROOT / name) == digest, "Source changed before publishing: " + name)
        checks.require(checks.sha(args.pdf) == receipt["manuscript_sha256"], "PDF changed before publishing")
        destinations = [VERSIONED, "output/pdf/BioCoLoop_manuscript.pdf", "manuscript.pdf"]
        for name in destinations:
            shutil.copy2(args.pdf, ROOT / name)
            checks.require(checks.sha(ROOT / name) == receipt["manuscript_sha256"], "PDF copy mismatch")
        receipt["published_paths"] = destinations
        DEST.mkdir(parents=True, exist_ok=True)
        (DEST / "build_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        rows = ["# 精简稿图表定位", "", "按实际PDF页码；原41页版本保留为20261109修订稿。", "",
                "| Label | 编号 | PDF页码 |", "| --- | --- | --- |"]
        for name, position in receipt["compiled_number_map"].items():
            rows.append(f"| `{name}` | {position['number']} | {position['pdf_page']} |")
        (DEST / "TABLE_MAP.zh-CN.md").write_text("\n".join(rows) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k not in {"source_sha256", "compiled_number_map"}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
