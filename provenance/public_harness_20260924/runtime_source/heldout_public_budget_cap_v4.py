"""Held-out evaluation using the unchanged scorer and a capped-slot validator."""
from __future__ import annotations

import argparse
from pathlib import Path

import budget_cap_protocol_v4 as protocol
from broker import dump, read, sha
import heldout_public as original

ORIGINAL_PREPARE = original.prepare_seal


def prepare_seal(run_dir, output, device):
    previous = original.validate_run
    original.validate_run = protocol.validate_run
    try:
        seal, record = ORIGINAL_PREPARE(run_dir, output, device)
    finally:
        original.validate_run = previous
    path = Path(output).resolve() / "seal.json"
    state = read(Path(run_dir).resolve() / "state.json")
    expected = {str(Path(__file__).resolve()): sha(__file__),
                str(Path(protocol.__file__).resolve()): sha(protocol.__file__)}
    changed = False
    for source, digest in expected.items():
        if seal["evaluation_sources_sha256"].get(source) != digest:
            seal["evaluation_sources_sha256"][source] = digest
            changed = True
    additions = {"proposal_slots_used": state["used_slots"],
                 "proposal_slots_available": 6, "native_early_stop_retained": state["used_slots"] < 6}
    for key, value in additions.items():
        if seal.get(key) != value:
            seal[key] = value
            changed = True
    if changed:
        if (Path(output).resolve() / "results.json").exists():
            raise ValueError("Never mutate an evaluation seal after response access")
        dump(path, seal)
    return read(path), record


def evaluate(run_dir, output, device="cpu"):
    previous_prepare, previous_validate = original.prepare_seal, original.validate_run
    original.prepare_seal = prepare_seal
    original.validate_run = protocol.validate_run
    try:
        return original.evaluate(run_dir, output, device)
    finally:
        original.prepare_seal = previous_prepare
        original.validate_run = previous_validate


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--seal-only", action="store_true")
    args = parser.parse_args()
    target = args.output or args.run_dir.with_name(args.run_dir.name + "_heldout")
    if args.seal_only:
        prepare_seal(args.run_dir, target, args.device)
        print("Evaluation seal written; no held-out response read")
    else:
        result = evaluate(args.run_dir, target, args.device)
        print({"status": "VERIFIED", "task": result["task"], "seed": result["seed"],
               "output": str(target), "proposal_slots_used": read(Path(target)/"seal.json")["proposal_slots_used"]})
