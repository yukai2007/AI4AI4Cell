"""Resume DTI scoring after a pre-response interpreter rejection.

The initial launcher wrote a durable held-out seal and then stopped before any
response access because it did not use the TAPB manifest interpreter. This
entry point revalidates the sealed development selection and the unchanged
held-out seal, then runs the original scorer under the registered interpreter.
It never rewrites or substitutes the existing seal.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent / "public_harness_20260924"
if str(ORIGINAL) not in sys.path:
    sys.path.insert(1, str(ORIGINAL))

import broker
import budget_cap_protocol_v4
import heldout_public


def resume(run_dir, output, device):
    run_dir, output = Path(run_dir).resolve(), Path(output).resolve()
    if (output / "results.json").exists():
        raise ValueError("A scored result must be verified, not resumed")
    definition, selection, development_seal, metadata = budget_cap_protocol_v4.validate_run(run_dir)
    seal_path = output / "seal.json"
    seal = broker.read(seal_path)
    if (seal.get("schema") != heldout_public.SEAL_SCHEMA
            or seal.get("task") != "native_tapb"
            or seal.get("harness") != "ai_researcher"
            or seal.get("clients") != [0]
            or seal.get("laboratory_access") != "lab 0 only"
            or seal.get("collaborative_aggregation") is not False
            or seal.get("run_dir") != str(run_dir)
            or seal.get("checkpoint") != selection["record"]["checkpoint"]
            or seal.get("checkpoint_sha256") != development_seal["checkpoint_sha256"]
            or seal.get("development_sealed_unix") != development_seal["sealed_unix"]
            or seal.get("sealed_unix", float("inf")) >= __import__("time").time()):
        raise ValueError("Existing DTI evaluation seal is not the frozen lab-0 selection")
    broker._verify_files(seal["study_metadata_sha256"])
    broker._verify_files(seal["evaluation_sources_sha256"])
    broker._verify_files({seal["checkpoint"]: seal["checkpoint_sha256"]})
    previous_prepare, previous_validate = heldout_public.prepare_seal, heldout_public.validate_run
    heldout_public.prepare_seal = lambda run, out, dev: (seal, selection["record"])
    heldout_public.validate_run = budget_cap_protocol_v4.validate_run
    try:
        return heldout_public.evaluate(run_dir, output, device)
    finally:
        heldout_public.prepare_seal, heldout_public.validate_run = previous_prepare, previous_validate


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()
    result = resume(args.run_dir, args.output, args.device)
    print({"status": "VERIFIED", "task": result["task"],
           "harness": result["harness"], "primary": result["primary"],
           "seal_unchanged": True})
