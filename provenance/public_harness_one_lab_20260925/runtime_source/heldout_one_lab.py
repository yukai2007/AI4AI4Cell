"""Seal, score and independently verify a lab-0 public-controller run."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent / "public_harness_20260924"
if str(ORIGINAL) not in sys.path:
    sys.path.insert(1, str(ORIGINAL))

import broker
import budget_cap_protocol_v4 as capped_protocol
import heldout_public as original

ORIGINAL_PREPARE = original.prepare_seal
ORIGINAL_VALIDATE = original.validate_run


def _prepare(run_dir, output, device, *, capped):
    seal, record = ORIGINAL_PREPARE(run_dir, output, device)
    path = Path(output).resolve() / "seal.json"
    if seal.get("clients") != [0]:
        raise ValueError("Held-out seal is not bound to lab 0 only")
    expected = {
        str(Path(broker.__file__).resolve()): broker.sha(broker.__file__),
        str(Path(__file__).resolve()): broker.sha(__file__),
    }
    changed = False
    for source, digest in expected.items():
        if seal["evaluation_sources_sha256"].get(source) != digest:
            seal["evaluation_sources_sha256"][source] = digest
            changed = True
    additions = {"laboratory_access": "lab 0 only", "collaborative_aggregation": False}
    if capped:
        state = broker.read(Path(run_dir).resolve() / "state.json")
        additions.update(proposal_slots_used=state["used_slots"], proposal_slots_available=6,
                         native_early_stop_retained=state["used_slots"] < 6)
    for key, value in additions.items():
        if seal.get(key) != value:
            seal[key] = value
            changed = True
    if changed:
        if (Path(output).resolve() / "results.json").exists():
            raise ValueError("Never mutate a held-out seal after response access")
        broker.dump(path, seal)
    return broker.read(path), record


def evaluate(run_dir, output, device, *, capped):
    validator = capped_protocol.validate_run if capped else ORIGINAL_VALIDATE
    previous_prepare, previous_validate = original.prepare_seal, original.validate_run
    original.validate_run = validator
    original.prepare_seal = lambda run, out, dev: _prepare(run, out, dev, capped=capped)
    try:
        return original.evaluate(run_dir, output, device)
    finally:
        original.prepare_seal, original.validate_run = previous_prepare, previous_validate


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--budget-capped", action="store_true")
    args = parser.parse_args()
    result = evaluate(args.run_dir, args.output, args.device, capped=args.budget_capped)
    print({"status": "VERIFIED", "task": result["task"], "harness": result["harness"],
           "seed": result["seed"], "primary": result["primary"], "clients": [0]})
