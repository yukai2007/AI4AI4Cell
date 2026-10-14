"""Verify and publish the additive configuration-search manuscript revision."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

import fitz

PAPER = Path(__file__).resolve().parents[1]
OUT = PAPER / "provenance/single_lab_search_20261014"
BASE = "18145a0"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def base_text(path):
    return subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=PAPER).decode()


def verify(pdf, log):
    document = fitz.open(pdf)
    text = "\n".join(page.get_text() for page in document)
    main_pages = [i+1 for i,page in enumerate(document) if "5. CONCLUSION" in page.get_text()]
    reproducibility_pages = [i+1 for i,page in enumerate(document) if "REPRODUCIBILITY STATEMENT" in page.get_text()]
    appendix_pages = [i+1 for i,page in enumerate(document) if "APPENDIX D." in page.get_text()]
    assert main_pages == [9], ("Main text must still end on page 9", main_pages)
    assert reproducibility_pages == [10], ("Conclusion must finish before page 10", reproducibility_pages)
    assert appendix_pages and appendix_pages[0] >= 32
    assert "Single-laboratory" in text or "SINGLE-LABORATORY" in text
    # Unnumbered appendix headings do not populate a numeric LaTeX label.
    # Verify the visible reference, not merely the absence of TeX warnings.
    assert re.search(r"Additional single-laboratory random search.{0,500}\(Appendix D\)\.", re.sub(r"\s+", " ", text))
    assert not any(list(page.annots() or []) for page in document)
    assert not document.metadata.get("author")
    for identifier in ("/liziqing/", "yukai2007", "Kai Yu", "Westlake University"):
        assert identifier not in text
    assert not re.search(r"Overfull|undefined|^!", log.read_text(), re.M)
    source = (PAPER / "biocoloop-main.tex").read_text()
    addition = "\\input{sections/25_appendix_single_lab_search}\n\n"
    assert source.count(addition) == 1
    assert source.replace(addition, "") == base_text("biocoloop-main.tex")
    results = (PAPER / "sections/05_results.tex").read_text()
    paragraphs = [p for p in results.split("\n\n") if p.startswith("Additional single-laboratory random search")]
    assert len(paragraphs) == 1
    assert results.replace(paragraphs[0]+"\n\n", "") == base_text("sections/05_results.tex")
    old_manifest = json.loads((PAPER / "provenance/author_final_pdf_20260930/verification.json").read_text())
    for path,digest in old_manifest["scientific_asset_sha256"].items():
        assert sha(PAPER/path) == digest, path
    for path in subprocess.check_output(["git","ls-tree","-r","--name-only",BASE,"sections"],cwd=PAPER).decode().splitlines():
        if path != "sections/05_results.tex":
            assert (PAPER/path).read_text() == base_text(path), path
    files = [PAPER/"main.tex",PAPER/"biocoloop-main.tex",PAPER/"latexmkrc",Path(__file__),
             PAPER/"tools/publish_single_lab_search.py"]
    files += list((PAPER/"sections").glob("*.tex"))
    files += list((PAPER/"tables/single_lab_search").glob("*"))
    files += list(PAPER.glob("references*.bib"))
    return dict(status="PASS",base_commit=BASE,total_pages=len(document),main_text_ends_page=9,
        appendix_d_starts_page=appendix_pages[0],manuscript_sha256=sha(pdf),build_log_sha256=sha(log),
        original_scientific_assets_unchanged=True,original_abstract_and_methods_unchanged=True,
        original_sections_preserved_except_additive_result_paragraph=True,
        new_training_performed_by_publication=False,overfull_boxes=0,undefined_references=0,
        source_sha256={str(p.relative_to(PAPER)):sha(p) for p in sorted(files) if p.is_file()},
        preserved_author_reference_sha256=sha(PAPER/"provenance/author_final_pdf_20260930/author_submitted.pdf"),
        interpretation="New one-laboratory search controls compared with historical Qwen BioCoLoop one/ten-laboratory references; not a same-access loop-only comparison",
        previous_exact_author_release="provenance/author_exact_pdf_20261007/verification.json")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf",type=Path,required=True)
    parser.add_argument("--log",type=Path,required=True)
    parser.add_argument("--publish",action="store_true")
    args=parser.parse_args()
    receipt=verify(args.pdf,args.log)
    if args.publish:
        OUT.mkdir(parents=True,exist_ok=True)
        shutil.copy2(args.pdf,PAPER/"output/pdf/BioCoLoop_manuscript.pdf")
        shutil.copy2(args.pdf,PAPER/"manuscript.pdf")
        (OUT/"build_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps({k:v for k,v in receipt.items() if k!="source_sha256"},indent=2))


if __name__ == "__main__":
    main()
