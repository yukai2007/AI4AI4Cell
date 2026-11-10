"""Publish a concise author-review revision without changing experimental assets."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

import fitz
import finalize_fbhk_followup as checks
from publish_focused_revision import table_map

ROOT = Path(__file__).resolve().parents[1]
BASE = "7323c9f61745a3bd47057f27eb11c7758686b30a"
DEST = ROOT / "provenance/author_review_20261110"
VERSIONED = "output/pdf/BioCoLoop_author_review_20261110.pdf"
REPLIES = "output/pdf/BioCoLoop_reviewer_responses_author_review_20261110.pdf"
GUIDE = "https://iclr.cc/Conferences/2027/AuthorGuidelines"
OFFICIAL_ZIP = DEST / "iclr2027-style-files.zip"


def git(*args, data=None):
    return subprocess.check_output(["git", *args], input=data, cwd=ROOT)


def original(name):
    return git("show", BASE+":"+name)


def graph(previous=False):
    seen = set()
    def visit(name):
        if name in seen:
            return
        seen.add(name)
        raw = original(name) if previous else (ROOT/name).read_bytes()
        text = re.sub(r"(?m)(?<!\\)%.*$", "", raw.decode())
        for child in re.findall(r"\\input\{([^}]+)\}", text):
            visit(child if child.endswith(".tex") else child+".tex")
    visit("main.tex")
    return seen


def integrity():
    entries = {}
    for record in git("ls-tree", "-rz", BASE).split(b"\0"):
        if record:
            meta, name = record.split(b"\t", 1)
            entries[name.decode()] = meta.decode().split()[2]
    allowed = {f"provenance/rebuttal_20261109/RESPONSE_{r}.md" for r in ("FBhK", "AfJB", "cR5g")}
    protected = [name for name in entries if
        name.startswith(("tables/", "figures/", "assets/", "provenance/")) and name not in allowed
        or name.startswith("output/pdf/") and name.endswith(".pdf") and name != "output/pdf/BioCoLoop_manuscript.pdf"]
    current = git("hash-object", "--stdin-paths", data=("\n".join(protected)+"\n").encode()).decode().splitlines()
    checks.require(len(current) == len(protected), "Incomplete protected-file check")
    for name, digest in zip(protected, current):
        checks.require(digest == entries[name], "Previous evidence or version changed: "+name)
    before, after = graph(True), graph()
    checks.require(before-after == {"tables/rebuttal_20261109/matched_search_main.tex"}, "Unexpected omitted source")
    checks.require(after-before == {"tables/author_review_20261110/current_search.tex"}, "Unexpected added source")
    # The old main table duplicates the full original comparison, which stays
    # compiled unchanged. Every other result table and figure remains included.
    checks.require("tables/rebuttal_20261109/matched_search_full.tex" in after, "Original complete controls absent")
    for name in before & after:
        pattern = r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}"
        checks.require(re.findall(pattern, original(name).decode()) ==
                       re.findall(pattern, (ROOT/name).read_text()), "Figure inclusion changed: "+name)
    return dict(base_commit=BASE, protected_files_unchanged=len(protected),
                original_result_tables_retained=len([n for n in before & after if n.startswith("tables/")]),
                replaced_duplicate_main_table="Original complete comparison retained in Appendix E.2",
                result_cells_changed=0, original_figures_retained=True)


def verify(args):
    subprocess.run([sys.executable, "tools/build_author_review_tables.py", "--check"], cwd=ROOT, check=True)
    result = {**checks.verify_pdf(args.pdf), **integrity()}
    log = args.log.read_text(errors="replace")
    checks.verify_log(log)
    checks.require(not re.search(r"Font shape .*undefined|defaults substituted", log), "Font fallback in final build")
    style_hashes = {}
    with zipfile.ZipFile(OFFICIAL_ZIP) as official:
        for name in ("iclr2027_conference.sty", "iclr2027_conference.bst", "natbib.sty", "fancyhdr.sty"):
            checks.require((ROOT/name).read_bytes() == official.read("iclr2027/"+name), "Official style differs: "+name)
            style_hashes[name] = checks.sha(ROOT/name)
    preamble = (ROOT/"biocoloop-main.tex").read_text().split(r"\begin{document}")[0]
    checks.require(r"\usepackage{iclr2027_conference,times}" in preamble and r"\usepackage[T1]{fontenc}" in preamble,
                   "Expected official Times setup absent")
    for setting in ("textwidth", "textheight", "baselineskip", "abovecaptionskip", "belowcaptionskip",
                    "textfloatsep", "floatsep", "intextsep", "parskip"):
        checks.require(not re.search(r"\\(?:setlength|addtolength)\{\\"+setting+r"\}", preamble), "Custom layout override: "+setting)
    included = graph()
    for name in included:
        checks.require((ROOT/name).stat().st_mtime <= args.pdf.stat().st_mtime+1, "PDF older than input: "+name)
    with fitz.open(args.pdf) as doc:
        text = "\n".join(p.get_text() for p in doc)
        for term in ("AI USE STATEMENT", "REPRODUCIBILITY STATEMENT", "CURRENT LIMITATIONS"):
            checks.require(term in text.upper(), "Required/current section absent: "+term)
        fonts = Counter()
        for page in list(doc)[:result["main_text_ends_page"]]:
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        if 9.8 < span["size"] < 10.1:
                            fonts[span["font"]] += len(span["text"])
        checks.require(sum(n for f,n in fonts.items() if "NimbusRom" in f or "Times" in f) > 10000,
                       "Times body font not found in rendered PDF")
        checks.require(sum(n for f,n in fonts.items() if "LMRoman" in f) == 0, "Fallback body font found")
    with fitz.open(ROOT/REPLIES) as doc:
        reply_pages = len(doc)
        text = "\n".join(p.get_text() for p in doc)
        for reviewer in ("FBhK", "AfJB", "cR5g"):
            checks.require("Response to Reviewer "+reviewer in text, "Missing reviewer reply")
    labels = table_map(args.pdf.with_suffix(".aux"))
    old_labels = json.loads((ROOT/"provenance/recipe_expansion_20261110/build_receipt.json").read_text())["compiled_number_map"]
    checks.require(set(old_labels)-set(labels) == {"tab:rebuttal-matched-search-main"}, "Old result label omitted")
    checks.require("tab:author-review-current-search" in labels, "Current overview not compiled")
    files = [ROOT/n for n in included] + [ROOT/"references.bib", ROOT/"references_v2.bib", ROOT/REPLIES,
        ROOT/"tools/build_author_review_tables.py", Path(__file__)]
    files += [p for p in DEST.iterdir() if p.is_file() and p.name not in ("build_receipt.json", "TABLE_MAP.zh-CN.md")]
    files += list((ROOT/"tables/author_review_20261110").glob("*"))
    files += [ROOT/f"provenance/rebuttal_20261109/RESPONSE_{r}.md" for r in ("FBhK", "AfJB", "cR5g")]
    result.update(schema="author-review-release-v1", status="PASS", created_utc=datetime.now(timezone.utc).isoformat(),
        main_page_limit=10, formatting_source=GUIDE, official_style_sha256=style_hashes,
        official_style_zip_sha256=checks.sha(OFFICIAL_ZIP), body_font_10pt_characters=dict(fonts),
        custom_global_spacing=False, font_fallback=False, overfull_boxes=0, undefined_references=0,
        compiled_number_map=labels, manuscript_sha256=checks.sha(args.pdf), build_log_sha256=checks.sha(args.log),
        source_sha256={str(p.relative_to(ROOT)):checks.sha(p) for p in sorted(set(files))},
        new_training=0, new_test_scoring=False, reply_pages=reply_pages,
        openreview_posted=False, overleaf_updated=False, main_merged=False)
    return result


def main():
    p = argparse.ArgumentParser(); p.add_argument("--pdf", type=Path, required=True)
    p.add_argument("--log", type=Path, required=True); p.add_argument("--publish", action="store_true"); args=p.parse_args()
    result = verify(args)
    if args.publish:
        paths = [VERSIONED, "output/pdf/BioCoLoop_manuscript.pdf", "manuscript.pdf"]
        for name in paths:
            shutil.copy2(args.pdf, ROOT/name)
            checks.require(checks.sha(ROOT/name) == result["manuscript_sha256"], "PDF copy mismatch")
        result["published_paths"] = paths
        (DEST/"build_receipt.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
        rows=["# 本轮图表位置", "", "| Label | 编号 | PDF页码 |", "| --- | --- | --- |"]
        for name, v in result["compiled_number_map"].items():
            rows.append(f"| `{name}` | {v['number']} | {v['pdf_page']} |")
        (DEST/"TABLE_MAP.zh-CN.md").write_text("\n".join(rows)+"\n")
    print(json.dumps({k:result[k] for k in ("status", "total_pages", "main_text_ends_page", "protected_files_unchanged",
          "result_cells_changed", "font_fallback", "manuscript_sha256")}, indent=2))


if __name__ == "__main__":
    main()
