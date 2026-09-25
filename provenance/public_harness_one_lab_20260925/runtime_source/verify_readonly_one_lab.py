"""Independently rescore a lab-0 held-out folder without rewriting receipts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent / "public_harness_20260924"
if str(ORIGINAL) not in sys.path:
    sys.path.insert(1, str(ORIGINAL))

import broker  # Lab-0 shim from HERE/PYTHONPATH.
import heldout_public
import verify_public


def verify_readonly(folder):
    folder = Path(folder).resolve()
    receipt_path = folder / "verification.json"
    prior = receipt_path.read_bytes()
    stored = json.loads(prior)
    seal = broker.read(folder / "seal.json")
    if seal.get("clients") != [0] or seal.get("laboratory_access") != "lab 0 only":
        raise ValueError("Verification target is not bound to lab 0")
    if seal.get("harness") == "ai_researcher":
        import budget_cap_protocol_v4
        heldout_public.validate_run = budget_cap_protocol_v4.validate_run
    captured = []
    original_dump = verify_public.dump

    def capture(path, value):
        if Path(path).resolve() != receipt_path:
            raise RuntimeError("Read-only verifier attempted an unexpected write")
        captured.append(value)

    verify_public.dump = capture
    try:
        computed = verify_public.verify(folder)
    finally:
        verify_public.dump = original_dump
    if captured != [computed] or receipt_path.read_bytes() != prior:
        raise ValueError("Independent verifier did not preserve stored evidence")
    stable = lambda value: {key: item for key, item in value.items()
                            if key != "verified_unix"}
    if stable(computed) != stable(stored):
        raise ValueError("Fresh independent rescoring differs from stored receipt")
    return computed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify_readonly(args.folder), sort_keys=True, allow_nan=False))
