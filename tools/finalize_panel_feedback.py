"""Release a separate panel-feedback audit revision; protect all previous results."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import fitz
import finalize_fbhk_followup as checks
from publish_focused_revision import table_map

PAPER = Path(__file__).resolve().parents[1]
BASE = "8a5d320cf303e569a4324ce6e99439ebf6da1e88"
DEST = PAPER / "provenance/panel_feedback_20261110"
VERSIONED = "output/pdf/BioCoLoop_panel_feedback_revision_20261110.pdf"
REPLIES = "output/pdf/BioCoLoop_reviewer_responses_panel_feedback_20261110.pdf"


def original(name):
    return subprocess.check_output(["git", "show", BASE + ":" + name], cwd=PAPER)


def integrity():
    tracked = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", BASE], cwd=PAPER).decode().splitlines()
    assets = [name for name in tracked if name.startswith(("tables/", "figures/", "assets/"))]
    protected_versions = [
        "output/pdf/BioCoLoop_focused_revision_20261110.pdf",
        "output/pdf/BioCoLoop_FBhK_revision_20261109.pdf",
        "provenance/focused_revision_20261110/build_receipt.json",
        "provenance/fbhk_followup_20261109/build_receipt.json",
        "provenance/fbhk_followup_20261109/experiment_sources.zip",
    ]
    for name in assets + protected_versions:
        checks.require((PAPER / name).read_bytes() == original(name), "Previous result/version changed: " + name)
    # Every earlier included table remains included; permit only the one new
    # development-audit table in the LaTeX input graph.
    def graph(previous):
        seen = set()
        def visit(name):
            if name in seen:
                return
            seen.add(name)
            raw = original(name) if previous else (PAPER / name).read_bytes()
            text = re.sub(r"(?m)(?<!\\)%.*$", "", raw.decode())
            for child in re.findall(r"\\input\{([^}]+)\}", text):
                visit(child if child.endswith(".tex") else child + ".tex")
        visit("main.tex")
        return seen
    old, new = graph(True), graph(False)
    checks.require(old <= new, "Previous included content removed")
    checks.require(new-old == {"tables/panel_feedback_20261110/development_audit.tex"}, "Unexpected new included content")
    for name in old:
        pattern = r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}"
        checks.require(re.findall(pattern, original(name).decode()) == re.findall(pattern, (PAPER/name).read_text()),
                       "Previous figure inclusion changed: " + name)
    return dict(previous_revision=BASE, previous_assets_unchanged=len(assets),
                previous_included_files_retained=len(old), old_result_cells_changed=0,
                protected_versions={name:checks.sha(PAPER/name) for name in protected_versions})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    subprocess.run([sys.executable, str(PAPER / "tools/publish_panel_feedback.py"), "--check"], check=True, cwd=PAPER)
    receipt = checks.verify(args.pdf, args.log)
    receipt.update(integrity())
    summary = checks.load(DEST / "summary.json")
    checks.require(summary["aggregate_max_abs_error"] == 0 and summary["checkpoint_count"] == 72 and
                   summary["canary_new_fits"] == 8, "Repair audit incomplete")
    labels = table_map(args.pdf.with_suffix(".aux"))
    checks.require("tab:panel-feedback-audit" in labels, "New audit table not compiled")
    checks.require((PAPER / "tables/panel_feedback_20261110/development_audit.tex").stat().st_mtime <= args.pdf.stat().st_mtime+1,
                   "New audit table is newer than the PDF")
    reply_lengths = {}
    for reviewer in ("FBhK", "AfJB", "cR5g"):
        path = PAPER / f"provenance/rebuttal_20261109/RESPONSE_{reviewer}.md"
        text = path.read_text()
        for term in ("72", "720", "22.888", "23.152", "[-1.022, 1.568]", "40"):
            checks.require(term in text, "Reply is missing current evidence: " + reviewer + "/" + term)
        reply_lengths[reviewer] = dict(characters=len(text), whitespace_words=len(text.split()))
        receipt["source_sha256"][str(path.relative_to(PAPER))] = checks.sha(path)
    with fitz.open(PAPER / REPLIES) as replies:
        text = "\n".join(page.get_text() for page in replies)
        for reviewer in ("FBhK", "AfJB", "cR5g"):
            checks.require("Response to Reviewer " + reviewer in text, "Missing reviewer in reply PDF")
        checks.require("10 November 2026" in text, "Reply PDF has an obsolete revision date")
        reply_pages = len(replies)
    files = [path for path in DEST.iterdir() if path.is_file() and path.name not in ("build_receipt.json", "TABLE_MAP.zh-CN.md")]
    files += [PAPER / "tables/panel_feedback_20261110/development_audit.tex",
              PAPER / "tools/publish_panel_feedback.py", Path(__file__),
              PAPER / "tools/build_rebuttal_responses.py", PAPER / REPLIES]
    for path in files:
        receipt["source_sha256"][str(path.relative_to(PAPER))] = checks.sha(path)
    receipt.update(schema="panel-feedback-revision-v1", status="PASS",
        created_utc=datetime.now(timezone.utc).isoformat(),
        new_full_budget_search_fits=0, new_canary_fits=8, canary_rounds_per_fit=10,
        new_llm_calls=0, new_heldout_inference=False,
        repaired_checkpoint_scores_verified=72, labelled_panel_scores=720,
        compiled_number_map=labels, reply_lengths=reply_lengths, reply_pages=reply_pages,
        reply_length_limit_verified=False, source_archive_sha256=checks.sha(DEST / "experiment_sources.zip"))
    if args.publish:
        for name,digest in receipt["source_sha256"].items():
            checks.require(checks.sha(PAPER/name) == digest, "Source changed before publishing: " + name)
        checks.require(checks.sha(args.pdf) == receipt["manuscript_sha256"], "Manuscript changed before publishing")
        paths = [VERSIONED, "output/pdf/BioCoLoop_manuscript.pdf", "manuscript.pdf"]
        for name in paths:
            shutil.copy2(args.pdf, PAPER / name)
        receipt["published_paths"] = paths
        (DEST / "build_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        rows = ["# 本轮图表位置", "", "表格编号和附录小节编号分别核对，二者不一定相同。", "",
                "| Label | 图表编号 | PDF页码 |", "| --- | --- | --- |"]
        for label, row in labels.items():
            rows.append(f"| `{label}` | {row['number']} | {row['pdf_page']} |")
        (DEST / "TABLE_MAP.zh-CN.md").write_text("\n".join(rows) + "\n")
    print(json.dumps({key:receipt[key] for key in ("status", "total_pages", "main_text_ends_page",
        "previous_assets_unchanged", "old_result_cells_changed", "repaired_checkpoint_scores_verified",
        "new_canary_fits", "manuscript_sha256", "reply_lengths")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
