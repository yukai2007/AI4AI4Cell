"""Release the expanded-recipe follow-up; protect every previous result."""
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
BASE = "b80eeea553a5610a5819e4cc790a71287c04fb9e"
DEST = PAPER / "provenance/recipe_expansion_20261110"
VERSIONED = "output/pdf/BioCoLoop_recipe_expansion_revision_20261110.pdf"
REPLIES = "output/pdf/BioCoLoop_reviewer_responses_recipe_expansion_20261110.pdf"


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
        "output/pdf/BioCoLoop_panel_feedback_revision_20261110.pdf",
        "provenance/panel_feedback_20261110/build_receipt.json",
    ]
    updated_replies = {
        "provenance/rebuttal_20261109/RESPONSE_FBhK.md",
        "provenance/rebuttal_20261109/RESPONSE_AfJB.md",
        "provenance/rebuttal_20261109/RESPONSE_cR5g.md",
        "provenance/fbhk_followup_20261109/RESPONSE_FBhK_SHORT.md",
    }
    previous_evidence = [name for name in tracked if name.startswith("provenance/") and name not in updated_replies]
    for name in assets + protected_versions + previous_evidence:
        checks.require((PAPER / name).read_bytes() == original(name), "Previous result/version changed: " + name)
    # Every earlier included table remains included; permit only the two new
    # expanded-recipe tables in the LaTeX input graph.
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
    checks.require(new-old == {"tables/recipe_expansion_20261110/results.tex", "tables/recipe_expansion_20261110/resources.tex"}, "Unexpected new included content")
    for name in old:
        pattern = r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}"
        checks.require(re.findall(pattern, original(name).decode()) == re.findall(pattern, (PAPER/name).read_text()),
                       "Previous figure inclusion changed: " + name)
    return dict(previous_revision=BASE, previous_assets_unchanged=len(assets),
                previous_evidence_files_unchanged=len(previous_evidence),
                previous_included_files_retained=len(old), old_result_cells_changed=0,
                protected_versions={name:checks.sha(PAPER/name) for name in protected_versions})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    subprocess.run([sys.executable, str(PAPER / "tools/package_recipe_compact.py"), "--check"], check=True, cwd=PAPER)
    receipt = checks.verify(args.pdf, args.log)
    receipt.update(integrity())
    summary = checks.load(DEST / "summary.json")
    checks.require(summary["new_fits"] == 216 and summary["development_pilot_fits"] == 110,
                   "Recipe fit coverage incomplete")
    labels = table_map(args.pdf.with_suffix(".aux"))
    for label in ("tab:expanded-recipe-results", "tab:expanded-recipe-cost"):
        checks.require(label in labels, "New recipe table not compiled: " + label)
    for name in ("results.tex", "resources.tex"):
        checks.require((PAPER / "tables/recipe_expansion_20261110" / name).stat().st_mtime <= args.pdf.stat().st_mtime+1,
                       "New recipe table is newer than supplied PDF")
    reply_lengths = {}
    for reviewer in ("FBhK", "AfJB", "cR5g"):
        path = PAPER / f"provenance/rebuttal_20261109/RESPONSE_{reviewer}.md"
        text = path.read_text()
        for term in ("216", "36", "20", "warm-start", "random"):
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
    files += [PAPER / "tables/recipe_expansion_20261110/results.tex",
              PAPER / "tables/recipe_expansion_20261110/resources.tex",
              PAPER / "tools/report_recipe_compact.py",
              PAPER / "tools/package_recipe_compact.py", Path(__file__),
              PAPER / "tools/build_rebuttal_responses.py", PAPER / REPLIES]
    for path in files:
        receipt["source_sha256"][str(path.relative_to(PAPER))] = checks.sha(path)
    receipt.update(schema="expanded-recipe-revision-v1", status="PASS",
        created_utc=datetime.now(timezone.utc).isoformat(),
        new_full_budget_head_fits=216, development_pilot_fits=110,
        new_llm_calls=summary["physical_llm_calls"], new_retrospective_heldout_inference=True,
        new_blind_split=False, success_on_both_new_tasks=summary["success_on_both_new_tasks"],
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
        "previous_assets_unchanged", "old_result_cells_changed", "new_full_budget_head_fits",
        "success_on_both_new_tasks", "manuscript_sha256", "reply_lengths")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
