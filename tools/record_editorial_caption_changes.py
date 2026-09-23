"""Record only caption changes; require non-caption content to match apart from trailing blank lines."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "564c211ef6360d665e3641a9b23fc5a88a7d3fb5"
PATHS = ["tables/completed_ablation/transfer_independent.tex", "tables/strong_v3/effects.tex"]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def numerical_body(data):
    return b"".join(line for line in data.splitlines(keepends=True)
                    if not line.startswith(b"\\caption{")).rstrip(b"\n") + b"\n"

def main():
    edits = {}
    for relative in PATHS:
        before = subprocess.check_output(["git", "show", BASELINE + ":" + relative], cwd=ROOT)
        after = (ROOT / relative).read_bytes()
        assert numerical_body(before) == numerical_body(after), relative
        edits[relative] = dict(before_sha256=sha(before), after_sha256=sha(after),
            unchanged_noncaption_sha256=sha(numerical_body(after)),
            before_caption=next(line for line in before.decode().splitlines() if line.startswith(r"\caption{")),
            after_caption=next(line for line in after.decode().splitlines() if line.startswith(r"\caption{")))
    report = dict(status="CAPTION_ONLY_VERIFIED", baseline_commit=BASELINE, files=edits)
    target = ROOT / "provenance/coauthor_review_v2_20260923/caption_changes.json"
    target.write_text(json.dumps(report, indent=2) + "\n")

if __name__ == "__main__":
    main()
