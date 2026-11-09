"""Validate and optionally publish the versioned FBhK follow-up manuscript.

Validation is read-only. --publish is explicit and never changes the original
author PDF or the preceding rebuttal receipt. All controls and original rows
are required regardless of the direction of their results.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import zipfile

import fitz

PAPER = Path(__file__).resolve().parents[1]
PROJECT = PAPER.parent
PROVENANCE = PAPER / "provenance/fbhk_followup_20261109"
BASE = "7764441764dea9d59713fe26286e84aff45aac19"
AUTHOR_SHA = "3bdd4251d9b201a1e9fbf6b94ffd72fc7092b0cc33a3afdcf72b4150b4407ec8"
REPLY = PAPER / "provenance/rebuttal_20261109/RESPONSE_FBhK.md"
OLD_TABLES = ("short6.tex", "long24.tex", "dynamics_short6.tex", "dynamics_long24.tex")
NEW_TABLES = {
    "proposal_heldout_combined.tex": {"tab:proposal-heldout-combined", "tab:completed-short6", "tab:completed-long24"},
    "proposal_dynamics_combined.tex": {"tab:proposal-dynamics-combined", "tab:completed-dynamics-short6", "tab:completed-dynamics-long24"},
    "fresh_history.tex": {"tab:fresh-history-comparison"},
    "fresh_history_cost.tex": {"tab:fresh-history-cost"},
    "lab_identity.tex": {"tab:fbhk-lab-identity"},
}
POLICY_LABELS = ("Fully trained fixed D00", "Direct (no feedback)", "Raw history", "Structured history",
                 "Random without replacement", "GP--EI")
POLICY_KEYS = {"fixed_D00", "direct", "raw", "structured", "random", "gp_ei"}
FORBIDDEN = ("/liziqing/", "yukai2007", "Kai Yu", "Westlake University")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def git_original(relative):
    return subprocess.check_output(["git", "show", BASE + ":" + relative], cwd=PAPER)


def clean_cell(value):
    value = re.sub(r"\\+\s*$", "", value.strip())
    while re.search(r"\\(?:textbf|mathbf|underline)\{([^{}]*)\}", value):
        value = re.sub(r"\\(?:textbf|mathbf|underline)\{([^{}]*)\}", r"\1", value)
    return re.sub(r"\s+", "", value).replace("PTPC", "Proteomics")


def study_rows(text):
    rows = []
    for line in text.splitlines():
        fields = line.strip().split(" & ")
        if len(fields) >= 5 and fields[0] in {"DTI", "PTPC", "Proteomics", "VCC", "Norman", "Tahoe"} and fields[1] in {"Qwen", "Luna"}:
            rows.append([clean_cell(v) for v in fields])
    return rows


def verify_merged_rows(short_scores, long_scores, short_dynamics, long_dynamics, merged_scores, merged_dynamics):
    a, b, c, d = map(study_rows, (short_scores, long_scores, short_dynamics, long_dynamics))
    require([len(a), len(b), len(c), len(d)] == [10,8,10,8], "Original four-table study counts changed")
    expected_scores = [row + ["--", "--"] for row in a] + b
    expected_dynamics = c + d
    require(study_rows(merged_scores) == expected_scores, "Combined held-out table dropped/reordered/changed an original row")
    require(study_rows(merged_dynamics) == expected_dynamics, "Combined dynamics table dropped/reordered/changed an original row")
    return dict(original_score_rows_retained=18, original_dynamics_rows_retained=18)


def verify_control_rows(table_text):
    names = [line.split(" & ")[0] for line in table_text.splitlines() if " & " in line]
    require(all(names.count(name) == 1 for name in POLICY_LABELS), "A required new-study control is missing or duplicated")


def verify_lab_summary(report, checks):
    tasks = {"ptpc_neural", "vcc_corrected", "norman_double_corrected", "tahoe_drug_corrected"}
    require(report["new_fits"] == 40 and report["all_outcomes_included"] is True, "Incomplete lab-identity study")
    require({r["task"] for r in report["rows"]} == tasks and len(report["rows"]) == 4, "Missing lab-identity task")
    seen = {(r["task"],r["lab"]) for r in checks}
    require(seen == {(t,i) for t in tasks for i in range(10)} and len(checks) == 40, "Missing or duplicated laboratory outcomes")
    verified = {(r["task"],r["lab"]):r["verified_primary"]*100 for r in checks}
    for row in report["rows"]:
        values = row["lab_scores"]
        require(len(values) == 10 and all(abs(x-verified[row["task"],i]) < 1e-10 for i,x in enumerate(values)), "Lab scores disagree with independent verification")
        for key,expected in {"lab0":values[0], "mean":statistics.mean(values), "sd":statistics.stdev(values), "minimum":min(values), "maximum":max(values)}.items():
            require(abs(row[key]-expected) < 1e-10, "Lab summary statistic changed: " + row["task"] + "/" + key)


def main_text_bounds(document):
    """Find the actual last main-text page, not merely the conclusion heading.

Line-number/page-number-only strings and the ICLR running header are excluded.
Text carried from the conclusion onto the next page is therefore counted.
"""
    lines = []
    for page_index, page in enumerate(document):
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                text = "".join(span["text"] for span in line["spans"]).strip()
                if text:
                    lines.append((page_index+1, tuple(line["bbox"]), text, page.rect.height))
    repro = [(p,b) for p,b,t,h in lines if re.sub(r"\s+", " ", t).upper() == "REPRODUCIBILITY STATEMENT"]
    conclusion = [(p,b) for p,b,t,h in lines if re.fullmatch(r"5\.?\s+CONCLUSION", t.upper())]
    require(len(repro) == 1 and len(conclusion) == 1, "Expected exactly one conclusion and reproducibility heading")
    repro_page, repro_box = repro[0]
    content = []
    for page, box, text, height in lines:
        if page > repro_page or (page == repro_page and box[1] >= repro_box[1] - 0.5):
            continue
        if text.isdigit() or text.lower().startswith("under review as a conference paper"):
            continue
        if box[1] > height-30:
            continue
        content.append((page, box, text))
    require(content, "No main-text content found before reproducibility")
    last = max(p for p,b,t in content)
    require((conclusion[0][0],conclusion[0][1][1]) < (repro_page,repro_box[1]), "Conclusion is not before reproducibility")
    require(last <= 10, f"Main text actually continues to page {last}; limit is 10")
    return dict(main_text_ends_page=last, conclusion_heading_page=conclusion[0][0],
                reproducibility_starts_page=repro_page, main_page_rule="Last non-header/non-line-number text before reproducibility, including continued conclusion text")


def verify_log(text):
    patterns = (r"Overfull", r"\bundefined\b", r"Missing character", r"^!", r"multiply defined", r"(?:LaTeX|Package \w+) Error")
    bad = [line for line in text.splitlines() if any(re.search(p, line, re.I) for p in patterns)]
    require(not bad, "Build log has unresolved layout/reference/error messages: " + " | ".join(bad[:12]))


def verify_compiled_labels(aux_text):
    names = re.findall(r"\\newlabel\{([^}]+)\}", aux_text)
    expected = set().union(*NEW_TABLES.values()) | {"fig:fbhk-prefix"}
    require(all(names.count(label) == 1 for label in expected), "New tables/figure missing or duplicated in compiled labels")
    return dict(compiled_followup_labels=sorted(expected))


def verify_pdf(pdf):
    with fitz.open(pdf) as document:
        bounds = main_text_bounds(document)
        text = "\n".join(page.get_text() for page in document)
        for term in FORBIDDEN:
            require(term.casefold() not in text.casefold(), f"Identifying manuscript text: {term}")
        require(not document.metadata.get("author") or document.metadata["author"].lower() == "anonymous", "PDF author metadata identifies authors")
        require("APPENDIX E." in text.upper(), "Follow-up appendix not present")
        for page in document:
            require(not list(page.annots() or []), "Unremoved PDF annotations")
            for link in page.get_links():
                target = str(link.get("uri", ""))
                require(not any(t.casefold() in target.casefold() for t in FORBIDDEN), "Identifying external link")
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        x0,y0,x1,y1 = span["bbox"]
                        require(-1 <= x0 <= x1 <= page.rect.width+1 and -1 <= y0 <= y1 <= page.rect.height+1,
                                f"Text outside PDF page {page.number+1}")
        return dict(total_pages=len(document), anonymity_check="PASS: text, author metadata and links",
                    annotation_check="PASS", page_geometry_check="PASS", **bounds)


def check_sources():
    for script in ("publish_rebuttal_access_table.py", "publish_rebuttal_evidence.py", "publish_rebuttal_allocation.py", "package_fbhk_followup.py"):
        subprocess.run([sys.executable, str(PAPER / "tools" / script), "--check"], cwd=PAPER, check=True)
    table_root = PAPER / "tables/fbhk_followup_20261109"
    provenance = load(table_root / "provenance.json")
    generator = PROJECT / provenance["generator"]
    require(sha(generator) == provenance["generator_sha256"], "New-table generator changed")
    subprocess.run([sys.executable, str(generator), "--check"], cwd=PROJECT, check=True)
    for name,digest in provenance["artifact_sha256"].items():
        require(sha(table_root / name) == digest, f"New table/snapshot changed: {name}")
    for name,digest in provenance["source_sha256"].items():
        require(sha(PROJECT / name) == digest, f"New table evidence source changed: {name}")
    for name,labels in NEW_TABLES.items():
        actual = set(re.findall(r"\\label\{([^}]+)\}", (table_root / name).read_text()))
        require(actual == labels, f"Missing/unexpected table labels in {name}")
    for name in ("fresh_history.tex", "fresh_history_cost.tex"):
        verify_control_rows((table_root / name).read_text())
    source_tables = []
    for name in OLD_TABLES:
        relative = "tables/completed_ablation/" + name
        require((PAPER / relative).read_bytes() == git_original(relative), f"Original table modified: {name}")
        source_tables.append((PAPER / relative).read_text())
    retained = verify_merged_rows(*source_tables,
        (table_root / "proposal_heldout_combined.tex").read_text(),
        (table_root / "proposal_dynamics_combined.tex").read_text())
    original_access = "tables/public_harness_comparison/main_public_harness_three_seed.tex"
    require((PAPER / original_access).read_bytes() == git_original(original_access), "Original main scores changed")
    access = load(PAPER / "tables/rebuttal_20261109/access_scenario.provenance.json")
    require(access["numeric_score_cells_changed"] == 0 and access["source_sha256"] == sha(PAPER / original_access), "Access-table source mismatch")
    archive = PAPER / "provenance/author_final_pdf_20260930/author_submitted.pdf"
    require(sha(archive) == AUTHOR_SHA, "Original author PDF changed")
    snapshot = load(table_root / "snapshot.json")
    require({r["policy"] for r in snapshot["new_study"]["results"]} == POLICY_KEYS, "New study policies are incomplete")
    require(snapshot["new_study"]["training_controller_seeds"] == [61,62,63], "New study seed coverage changed")
    summary = load(PROVENANCE / "policy_summary.json")
    require(POLICY_KEYS | {"random_shared_first"} <= set(summary["policies"]), "Published aggregate controls incomplete")
    package = load(PROVENANCE / "experiment_sources.manifest.json")
    require(package["status"] == "PASS" and package["archive_sha256"] == sha(PROVENANCE / "experiment_sources.zip"), "Extension package hash/status mismatch")
    require(package["policy_summary_sha256"] == sha(PROVENANCE / "policy_summary.json"), "Aggregate summary hash mismatch")
    with zipfile.ZipFile(PROVENANCE / "experiment_sources.zip") as z:
        require(set(z.namelist()) == set(package["archive_member_sha256"]), "Package members differ")
        for name,digest in package["archive_member_sha256"].items():
            require(hashlib.sha256(z.read(name)).hexdigest() == digest, "Package member changed: " + name)
    prefix_path = PROJECT / "results/fbhk_followup_20261109/validation/prefix_audit.json"
    prefix = load(prefix_path)
    require(prefix["status"] == "COMPLETE" and len(prefix["per_seed"]) == 147, "New prefix diagnostic incomplete")
    require(prefix["source_sha256"] == sha(PROJECT / "extensions/fbhk_followup_20261109/validation/prefix_audit.py"), "Prefix generator changed")
    for name,digest in prefix["source_sha256s"].items():
        require(sha(PROJECT / name) == digest, f"Prefix evidence changed: {name}")
    lab = load(table_root / "lab_identity.provenance.json")
    lab_root = PROJECT / "results/fbhk_followup_20261109/lab_identity"
    require(lab["status"] == "PASS" and lab["new_fits_verified"] == lab["prediction_scores_verified"] == 40, "Laboratory study verification failed")
    require(lab["table_sha256"] == sha(table_root / "lab_identity.tex"), "Lab table changed after verification")
    require(lab["report_sha256"] == sha(lab_root / "report.json") == sha(table_root / "lab_identity.json"), "Lab report/copy changed")
    require(lab["protocol_sha256"] == sha(lab_root / "protocol.json"), "Lab protocol changed")
    require(lab["renderer_sha256"] == sha(PROJECT / "extensions/fbhk_followup_20261109/lab_identity/verify_and_render.py"), "Lab verification source changed")
    for name,digest in lab["prediction_bindings"].items():
        require(sha(Path(name)) == digest, "Lab prediction binding changed")
    verify_lab_summary(load(lab_root / "report.json"), lab["checks"])
    figure = PAPER / "figures/fbhk_followup_20261109/history_prefix_dev_test.pdf"
    with fitz.open(figure) as d:
        require(len(d) == 1 and not d[0].get_images(), "Expected one-page vector prefix figure without raster replacements")
        require("Development selection" in d[0].get_text(), "New figure does not contain the expected development panel")
    return dict(original_access_score_cells_checked=50, original_access_score_cells_changed=0,
                author_submitted_reference_preserved=True, new_study_controls="PASS: fixed/direct/raw/structured/random/GP-EI plus published sensitivities",
                source_archive_check="PASS", prefix_diagnostic_sha256=sha(prefix_path), figure_sha256=sha(figure),
                lab_identity_fits_verified=40, lab_identity_all_outcomes_retained=True, **retained)


def verify(pdf, log, reply=REPLY):
    pdf, log, reply = map(lambda p: Path(p).resolve(), (pdf,log,reply))
    evidence = check_sources()
    pdf_checks = verify_pdf(pdf)
    verify_log(log.read_text(errors="replace"))
    aux = pdf.with_suffix(".aux")
    require(aux.is_file(), "Keep the final build auxiliary file to verify compiled table/figure labels")
    label_checks = verify_compiled_labels(aux.read_text())
    require(reply.is_file() and len(reply.read_text().strip()) > 200, "English reviewer reply missing or empty")
    files = [PAPER / "main.tex", PAPER / "biocoloop-main.tex", PAPER / "references.bib", PAPER / "references_v2.bib", reply]
    files += sorted((PAPER / "sections").glob("*.tex"))
    for folder in ("tables/fbhk_followup_20261109", "tables/rebuttal_20261109", "figures/fbhk_followup_20261109"):
        files += [p for p in sorted((PAPER / folder).glob("*")) if p.is_file()]
    files += [p for p in sorted(PROVENANCE.glob("*")) if p.is_file() and p.suffix in (".md", ".txt", ".zip")]
    files += [PROVENANCE / name for name in ("experiment_sources.manifest.json", "policy_summary.json")]
    files += [PAPER / "tools/finalize_fbhk_followup.py", PAPER / "tools/test_finalize_fbhk_followup.py"]
    typeset = [p for p in files if p.suffix in (".tex", ".bib")]
    typeset.append(PAPER / "figures/fbhk_followup_20261109/history_prefix_dev_test.pdf")
    newer = [str(p.relative_to(PAPER)) for p in typeset if p.stat().st_mtime > pdf.stat().st_mtime+1]
    require(not newer, "Typesetting inputs newer than supplied PDF: " + ", ".join(newer))
    return dict(schema="fbhk-followup-release-v1", status="PASS", base_commit=BASE,
        created_utc=datetime.now(timezone.utc).isoformat(), manuscript_sha256=sha(pdf), build_log_sha256=sha(log),
        english_reply=str(reply.relative_to(PAPER)), english_reply_sha256=sha(reply),
        main_page_limit=10, page_limit_source="https://iclr.cc/Conferences/2027/AuthorGuidelines",
        overfull_boxes=0, undefined_references=0, source_inputs_newer_than_pdf=[],
        source_sha256={str(p.relative_to(PAPER)):sha(p) for p in sorted(set(files))},
        old_rebuttal_receipt_sha256=sha(PAPER / "provenance/rebuttal_20261109/build_receipt.json"),
        compiled_aux_sha256=sha(aux), openreview_posted=False, overleaf_remote_build_verified=False,
        **pdf_checks, **evidence, **label_checks)


def publish(pdf, receipt):
    for name,digest in receipt["source_sha256"].items():
        require(sha(PAPER / name) == digest, "Source changed between verification and publication: " + name)
    require(sha(pdf) == receipt["manuscript_sha256"], "PDF changed between verification and publication")
    destinations = ("output/pdf/BioCoLoop_FBhK_revision_20261109.pdf", "output/pdf/BioCoLoop_manuscript.pdf", "manuscript.pdf")
    for name in destinations:
        target = PAPER / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.resolve() != Path(pdf).resolve():
            shutil.copy2(pdf, target)
        require(sha(target) == receipt["manuscript_sha256"], "Published PDF copy differs")
    receipt["published_paths"] = list(destinations)
    require(sha(PAPER / "provenance/rebuttal_20261109/build_receipt.json") == receipt["old_rebuttal_receipt_sha256"], "Prior revision receipt changed")
    raw = json.dumps(receipt, indent=2, ensure_ascii=False) + "\n"
    (PROVENANCE / f"build_receipt_{receipt['manuscript_sha256'][:12]}.json").write_text(raw)
    (PROVENANCE / "build_receipt.json").write_text(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--reply", type=Path, default=REPLY)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    receipt = verify(args.pdf, args.log, args.reply)
    if args.publish:
        publish(args.pdf, receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k != "source_sha256"}, indent=2))


if __name__ == "__main__":
    main()
