"""Verify final-PDF/source parity and record the three declared errata."""
import argparse
import difflib
import hashlib
import json
import re
import subprocess
from pathlib import Path

import fitz
from sync_final_pdf_20260930 import pages

PAPER = Path(__file__).resolve().parents[1]
AUTHOR_SHA = "3bdd4251d9b201a1e9fbf6b94ffd72fc7092b0cc33a3afdcf72b4150b4407ec8"
FOLDER = PAPER / "provenance/author_final_pdf_20260930"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(text):
    return " ".join(text.translate(str.maketrans({"–": "-", "−": "-"})).split())


def declared_errata(text):
    replacements = [
        ("appends the card et of Section 3.2", "appends the new card et+1 of Section 3.2"),
        ("Et+1 = Et ∥[et],", "Et+1 = Et ∥[et+1],"),
        ("MRR against a 46.00 chance level.",
         "MRR against a 45.67 chance level (scores multiplied by 100)."),
        ("The seed-42 Qwen AI-Scientistv2 DTI example trains three candidates before substage schema validation fails, leaving its incumbent unsealed and unscored.", ""),
    ]
    for old, new in replacements:
        if text.count(old) != 1:
            raise AssertionError(f"Author-PDF erratum anchor is not unique: {old}")
        text = text.replace(old, new)
    return normalize(text)


def verify(author, rebuilt):
    assert digest(author) == AUTHOR_SHA, "Wrong author-selected reference PDF"
    reference = normalize(" ".join(pages(author)))
    actual = normalize(" ".join(pages(rebuilt)))
    expected = declared_errata(reference)
    if expected != actual:
        matcher = difflib.SequenceMatcher(None, expected.split(), actual.split(), autojunk=False)
        mismatches = []
        a, b = expected.split(), actual.split()
        for kind, i, j, k, l in matcher.get_opcodes():
            if kind != "equal":
                mismatches.append({"expected": " ".join(a[i:j]), "actual": " ".join(b[k:l])})
        raise AssertionError(json.dumps(mismatches, ensure_ascii=False, indent=2))
    doc = fitz.open(rebuilt)
    assert len(doc) == 31
    assert "5. CONCLUSION" in doc[8].get_text()
    assert "REPRODUCIBILITY STATEMENT" in doc[9].get_text()
    assert "APPENDIX A." in doc[14].get_text()
    assert "APPENDIX C." in doc[30].get_text()
    assert not any(list(p.annots() or []) for p in doc)
    assert not doc.metadata.get("author")
    for identifier in ("/liziqing/", "yukai2007", "Kai Yu", "Westlake University"):
        assert identifier not in actual
    return {"status": "PASS", "author_pdf_sha256": AUTHOR_SHA,
            "rebuilt_pdf_sha256": digest(rebuilt), "total_pages": len(doc),
            "main_text_pages": 9, "normalized_text_matches_after_declared_errata": True,
            "declared_scientific_changes": "None: no experiment reruns or numerical result changes",
            "errata": ["New evidence-card index e_(t+1)",
                       "Five-option chance MRR = 100 * H_5 / 5 = 45.67",
                       "Remove stale unscored Qwen AI-Scientist-v2 DTI example; current row is complete"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=PAPER / "build/main.pdf")
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    result = verify(FOLDER / "author_submitted.pdf", args.pdf)
    log = (PAPER / "build/main.log").read_text()
    assert not re.search(r"Overfull|undefined|^!", log, re.M)
    result["overfull_boxes"] = 0
    result["undefined_references"] = 0
    assets = [p for folder in ("tables", "assets", "figures")
              for p in (PAPER / folder).rglob("*") if p.is_file() and
              p.suffix in (".tex", ".json", ".tsv", ".pdf", ".svg", ".pptx")]
    source = [PAPER / "main.tex", PAPER / "biocoloop-main.tex"]
    source += list((PAPER / "sections").glob("*.tex"))
    source += list(PAPER.glob("references*.bib"))
    result["source_sha256"] = {str(p.relative_to(PAPER)): digest(p) for p in sorted(source)}
    result["scientific_asset_sha256"] = {str(p.relative_to(PAPER)): digest(p) for p in sorted(assets)}
    result["base_commit"] = "3ce4b71"
    diff = subprocess.check_output(["git", "diff", "3ce4b71", "--", "tables", "assets", "figures"], cwd=PAPER)
    assert not diff, "Scientific artifacts changed during a writing-only synchronization"
    result["scientific_assets_unchanged_from_base"] = True
    if args.write_receipt:
        (FOLDER / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if not k.endswith("sha256") or isinstance(v, str)}, indent=2))


if __name__ == "__main__":
    main()
