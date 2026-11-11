"""Release the round-3 rebuttal revision; protect every previous result except registered regenerations.

Changed protected files are limited to tables rebuilt by their generators (ten-laboratory fixed-model rows,
captions, and the registered eight-seed proteomics extension). New eight-seed tables are rendered from saved
analyses. All arms, seeds and contrasts are required regardless of the direction of their results.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
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
BASE = "0416256"
DEST = ROOT / "provenance/round3_20261111"
VERSIONED = "output/pdf/BioCoLoop_round3_20261111.pdf"
REPLIES = "output/pdf/BioCoLoop_reviewer_responses_round3_20261111.pdf"
GUIDE = "https://iclr.cc/Conferences/2027/AuthorGuidelines"
OFFICIAL_ZIP = ROOT / "provenance/author_review_20261110/iclr2027-style-files.zip"
REGENERATED = {
    "tables/strong_v3/ablation.tex", "tables/strong_v3/dti_endpoints.tex", "tables/strong_v3/secondary.tex",
    "tables/single_lab_search/comparison.tex", "tables/rebuttal_20261109/access_scenario.tex",
    "tables/proteomics_scenario_labs_v2/build_table.py", "tables/proteomics_scenario_labs_v2/provenance.json",
    "tables/proteomics_scenario_labs_v2/results.csv", "tables/proteomics_scenario_labs_v2/summary.zh-CN.md",
    "tables/proteomics_scenario_labs_v2/table.tex",
    "tables/author_review_20261110/current_search.tex", "tables/author_review_20261110/current_search.provenance.json",
}
NEW_SOURCES = {"tables/rebuttal_round3_20261111/e6_eight_seed.tex", "tables/rebuttal_round3_20261111/e9_eight_seed.tex"}
NEW_LABELS = {"tab:fresh-history-eight-seed", "tab:recipe-expansion-eight-seed"}
SEEDS = [61, 62, 63, 64, 65, 66, 67, 68]
PROTEOMICS_ARMS = {"target_only", "plus_decrypte", "plus_existing2", "plus_all3"}


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
    allowed = {f"provenance/rebuttal_20261109/RESPONSE_{r}.md" for r in ("FBhK", "AfJB", "cR5g")} | REGENERATED
    protected = [name for name in entries if
        name.startswith(("tables/", "figures/", "assets/", "provenance/")) and name not in allowed
        or name.startswith("output/pdf/") and name.endswith(".pdf") and name != "output/pdf/BioCoLoop_manuscript.pdf"]
    current = git("hash-object", "--stdin-paths", data=("\n".join(protected)+"\n").encode()).decode().splitlines()
    checks.require(len(current) == len(protected), "Incomplete protected-file check")
    for name, digest in zip(protected, current):
        checks.require(digest == entries[name], "Previous evidence or version changed: "+name)
    changed = sorted(n for n in REGENERATED if (ROOT/n).read_bytes() != original(n))
    before, after = graph(True), graph()
    checks.require(before-after == set(), "Unexpected omitted source: "+str(sorted(before-after)))
    checks.require(after-before == NEW_SOURCES, "Unexpected added source: "+str(sorted(after-before)))
    checks.require("tables/rebuttal_20261109/matched_search_full.tex" in after, "Original complete controls absent")
    pattern = r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}"
    for name in before & after:
        checks.require(re.findall(pattern, (ROOT/name).read_text()) == re.findall(pattern, original(name).decode()),
                       "Figure inclusion changed: "+name)
    return dict(base_commit=BASE, protected_files_unchanged=len(protected), regenerated_files_changed=changed,
                added_sources=sorted(NEW_SOURCES), original_figures_retained=True)


def verify_extensions():
    """All registered arms, seeds and contrasts present; tables match the saved analyses."""
    here = ROOT/"tables/rebuttal_round3_20261111"
    rendered = {n: (here/n).read_bytes() for n in ("e6_eight_seed.tex", "e9_eight_seed.tex", "provenance.json")}
    stamps = {n: (here/n).stat() for n in rendered}
    subprocess.run([sys.executable, "build_eight_seed.py", "e6", "e9"], cwd=here, check=True)
    for name, raw in rendered.items():
        checks.require((here/name).read_bytes() == raw, name+": table differs from its generator output")
        os.utime(here/name, ns=(stamps[name].st_atime_ns, stamps[name].st_mtime_ns))
    prov = checks.load(here/"provenance.json")
    out = {}
    for study in ("e6", "e9"):
        path = here/f"{study}_eight_seed_analysis.json"
        checks.require(prov[study]["analysis_sha256"] == checks.sha(path), study+": analysis changed after rendering")
        data = checks.load(path)
        checks.require(data["status"] == "COMPLETE" and data["n_seeds"] == 8, study+": incomplete eight-seed analysis")
        out[study] = dict(analysis_sha256=checks.sha(path), groups=sorted(data["groups"]))
    prot = checks.load(ROOT/"tables/proteomics_scenario_labs_v2/eight_seed_analysis.json")
    checks.require(sorted(prot.get("seeds", SEEDS)) == SEEDS, "Proteomics seed set changed")
    table = (ROOT/"tables/proteomics_scenario_labs_v2/table.tex").read_text()
    checks.require("61--68" in table, "Proteomics table is not the eight-seed table")
    out["proteomics"] = dict(analysis_sha256=checks.sha(ROOT/"tables/proteomics_scenario_labs_v2/eight_seed_analysis.json"))
    return out


def verify(args):
    for tool in ("build_author_review_tables.py", "publish_single_lab_search.py", "publish_rebuttal_access_table.py"):
        subprocess.run([sys.executable, "tools/"+tool, "--check"], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    result = {**checks.verify_pdf(args.pdf), **integrity(), "extensions": verify_extensions()}
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
        for term in ("AI USE STATEMENT", "REPRODUCIBILITY STATEMENT", "COLLABORATIVE VERSUS SINGLE-LABORATORY"):
            checks.require(term in text.upper(), "Required/current section absent: "+term)
        checks.require("split-panel" not in text.lower(), "Unrequested split-panel study entered the manuscript")
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
    for r in ("FBhK", "AfJB", "cR5g"):
        reply = (ROOT/f"provenance/rebuttal_20261109/RESPONSE_{r}.md").read_text()
        checks.require("[[" not in reply, "Unfilled placeholder in reply "+r)
        for term in checks.FORBIDDEN:
            checks.require(term.casefold() not in reply.casefold(), f"Identifying reply text ({r}): {term}")
    with fitz.open(ROOT/REPLIES) as doc:
        reply_pages = len(doc)
        text = "\n".join(p.get_text() for p in doc)
        for reviewer in ("FBhK", "AfJB", "cR5g"):
            checks.require("Response to Reviewer "+reviewer in text, "Missing reviewer reply")
    labels = table_map(args.pdf.with_suffix(".aux"))
    old_labels = json.loads((ROOT/"provenance/final_figures_20261111/build_receipt.json").read_text())["compiled_number_map"]
    checks.require(set(old_labels)-set(labels) == set(), "Old result label omitted")
    checks.require(set(labels)-set(old_labels) == NEW_LABELS, "Unexpected label set: "+str(sorted(set(labels)-set(old_labels))))
    files = [ROOT/n for n in included] + [ROOT/"references.bib", ROOT/"references_v2.bib", ROOT/REPLIES, Path(__file__)]
    files += [ROOT/n for n in sorted(REGENERATED)]
    files += [p for p in (ROOT/"tables/rebuttal_round3_20261111").iterdir() if p.is_file() and p.suffix in (".py", ".json", ".tex")]
    files += [ROOT/"tables/proteomics_scenario_labs_v2/eight_seed_analysis.json"]
    files += [p for p in DEST.iterdir() if p.is_file() and p.name not in ("build_receipt.json", "TABLE_MAP.zh-CN.md")]
    files += [ROOT/f"provenance/rebuttal_20261109/RESPONSE_{r}.md" for r in ("FBhK", "AfJB", "cR5g")]
    files += [ROOT/"tools"/t for t in ("publish_strong_snapshot.py", "publish_single_lab_search.py",
                                       "publish_rebuttal_access_table.py", "build_rebuttal_responses.py",
                                       "build_author_review_tables.py")]
    result.update(schema="round3-rebuttal-release-v1", status="PASS", created_utc=datetime.now(timezone.utc).isoformat(),
        main_page_limit=10, formatting_source=GUIDE, official_style_sha256=style_hashes,
        official_style_zip_sha256=checks.sha(OFFICIAL_ZIP), body_font_10pt_characters=dict(fonts),
        custom_global_spacing=False, font_fallback=False, overfull_boxes=0, undefined_references=0,
        compiled_number_map=labels, manuscript_sha256=checks.sha(args.pdf), build_log_sha256=checks.sha(args.log),
        source_sha256={str(p.relative_to(ROOT)):checks.sha(p) for p in sorted(set(files))},
        new_seeds=[64, 65, 66, 67, 68], new_studies_extended=["E.6 cells", "E.9 DTI/protein", "B source-defined proteomics"],
        exclusions="none; analyses registered before the new fits", reply_pages=reply_pages,
        openreview_posted=False, overleaf_updated=False, main_merged=False)
    return result


def main():
    p = argparse.ArgumentParser(); p.add_argument("--pdf", type=Path, required=True)
    p.add_argument("--log", type=Path, required=True); p.add_argument("--publish", action="store_true"); args=p.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
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
          "regenerated_files_changed", "font_fallback", "manuscript_sha256")}, indent=2))


if __name__ == "__main__":
    main()
