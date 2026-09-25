"""Prioritize final budget-cap-v4 AI-Researcher DTI after verified AIS DTI."""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import airesearcher_budget_cap_v4 as v4
from broker import dump, read, sha
import prioritize_seed42_dti as common
import supervise as frozen

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TARGET = common.TARGET
FINAL = common.FINAL


def source_pins():
    result = v4.source_pins()
    result[str(Path(__file__).resolve())] = sha(__file__)
    return result


def coordinator(args):
    base, formal, short = map(lambda path: path.resolve(), (args.base, args.formal, args.short))
    base.mkdir(parents=True, exist_ok=True)
    with (base / ".coordinator.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (base / "queue_manifest.json").exists():
            raise ValueError("Versioned queue already registered")
        parent_manifest = read(formal / "queue_manifest.json")
        short_manifest = read(short / "queue_manifest.json")
        if parent_manifest["source_sha256"] != frozen.pinned_sources():
            raise ValueError("Frozen parent sources changed")
        if (short_manifest.get("schema") != "public-harness-budget-cap-repair-queue-v4"
                or short_manifest.get("source_sha256") != v4.source_pins()):
            raise ValueError("Short repair is not the registered final revision")
        deadline = parent_manifest["created_unix"] + parent_manifest["max_wall_hours"] * 3600
        manifest = {
            "schema": "public-harness-seed42-dti-priority-v3", "created_unix": time.time(),
            "source_sha256": source_pins(), "formal_queue": str(formal), "short_queue": str(short),
            "target_completed_before_preemption": TARGET, "final_job": FINAL,
            "max_gpu_hours": 48.0, "combined_hard_cap_gpu_hours": 192.0,
            "deadline_unix": deadline, "gpus": list(range(8)),
            "preemption_scope": "superseded continuation only after target heldout PASS",
            "fresh_training": True, "resume_partial": False, "automatic_retries": False,
            "proposal_budget": {"maximum": 6, "native_early_stop_retained": True},
        }
        dump(base / "queue_manifest.json", manifest)
        state = {"schema": "public-harness-seed42-dti-priority-status-v3",
                 "status": "WAITING_FOR_AIS_DTI", "pid": os.getpid(),
                 "started_unix": time.time(), "updated_unix": time.time(),
                 "reserved_gpu_hours": 0.0, "completed": [], "failed": []}
        dump(base / "supervisor_status.json", state)

        def interrupted(sig, frame):
            raise InterruptedError(f"Priority coordinator signal {sig}")
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, interrupted)

        def child(command, log, gpus):
            if source_pins() != manifest["source_sha256"]:
                raise ValueError("Priority runtime changed")
            frozen.run_child(command, log, base, state, reserved_gpus=gpus,
                             max_gpu_hours=48.0, deadline=deadline)

        try:
            target_key = (TARGET["harness"], TARGET["task"], TARGET["seed"])
            while True:
                formal_state = read(formal / "supervisor_status.json")
                completed = {(item["harness"], item["task"], item["seed"])
                             for item in formal_state.get("completed", [])}
                verification = formal / "ai_scientist_v2/native_tapb/seed42/heldout/verification.json"
                if (target_key in completed and verification.exists()
                        and read(verification).get("status") == "PASS"):
                    break
                if formal_state.get("status") != "RUNNING":
                    raise RuntimeError("Formal queue stopped before verified AI-Scientist DTI")
                if not common.process_matches(formal_state["pid"], "supervise.py", formal):
                    raise RuntimeError("Formal supervisor identity not verified")
                if time.time() >= deadline:
                    raise TimeoutError("Deadline before AI-Scientist DTI verification")
                state["updated_unix"] = time.time()
                dump(base / "supervisor_status.json", state)
                time.sleep(10)

            formal_state = read(formal / "supervisor_status.json")
            if formal_state.get("status") == "RUNNING":
                if not common.process_matches(formal_state["pid"], "supervise.py", formal):
                    raise RuntimeError("Refuse unverified formal PID")
                state.update(status="STOPPING_SUPERSEDED_CONTINUATION",
                             formal_pid=formal_state["pid"], updated_unix=time.time())
                dump(base / "supervisor_status.json", state)
                os.kill(formal_state["pid"], signal.SIGTERM)
            while True:
                formal_state = read(formal / "supervisor_status.json")
                alive = common.process_matches(formal_state.get("pid", 0), "supervise.py", formal)
                members = (frozen._token_members(formal_state.get("child_ownership", {}))
                           if formal_state.get("child_ownership") else [])
                if not alive and not members:
                    break
                if time.time() >= deadline:
                    raise TimeoutError("Superseded queue did not stop cleanly")
                time.sleep(2)

            state.update(status="WAITING_FOR_SHORT_REPAIR",
                         formal_terminal_status=formal_state.get("status"), updated_unix=time.time())
            dump(base / "supervisor_status.json", state)
            short_state = common.wait_terminal(short / "supervisor_status.json", deadline,
                allowed={"COMPLETE", "FINISHED_WITH_INCOMPLETE_RUNS"})
            if (short_state.get("child_ownership")
                    and frozen._token_members(short_state["child_ownership"])):
                raise RuntimeError("Short-repair queue still owns live children")
            consumed = formal_state.get("reserved_gpu_hours", 0.0) + short_state.get("reserved_gpu_hours", 0.0)
            for name in ("compact_repair_v1", "compact_repair_v2", "compact_repair_v3"):
                consumed += read(short.parent / name / "supervisor_status.json").get("reserved_gpu_hours", 0.0)
            if (not math.isfinite(consumed)
                    or consumed + manifest["max_gpu_hours"] > manifest["combined_hard_cap_gpu_hours"]):
                raise RuntimeError("No registered combined compute allowance remains")

            state.update(status="RUNNING", phase="DEVELOPMENT", current_job=FINAL,
                         prior_reserved_gpu_hours=consumed)
            run = base / "ai_researcher/native_tapb/seed42"
            child([str(HERE / ".venv/bin/python"), "-B",
                   str(HERE / "airesearcher_budget_cap_v4.py"), "--train",
                   "--task", "native_tapb", "--gpus", "1,2,3,4,5,6,7",
                   "--model-device", "cuda:0", "--output", str(run)],
                  base / "logs/ai_researcher_native_tapb_seed42.log", 8)
            if read(run / "run_status.json").get("status") != "DEVELOPMENT_COMPLETE":
                raise RuntimeError("Final DTI selection incomplete")
            state["phase"] = "HELDOUT_EVALUATION"
            worker = read(ROOT / "results/unified_bio_20260918/native_tapb/data/manifest.json")["worker_python"]
            child([worker, "-B", str(HERE / "heldout_public_budget_cap_v4.py"),
                   "--run-dir", str(run / "development"), "--output", str(run / "heldout"),
                   "--device", "cuda:1"], run / "evaluation.log", 1)
            state["phase"] = "INDEPENDENT_RESCORING"
            child([frozen.LDA, "-B", str(HERE / "verify_public_budget_cap_v4.py"),
                   str(run / "heldout")], run / "verification.log", 0)
            result = read(run / "heldout/results.json")
            state["completed"].append({**FINAL, "primary": result["primary"],
                                       "metric": result["primary_metric"], "output": str(run)})
            state.update(status="COMPLETE", phase="TERMINAL", completed_unix=time.time())
        except BaseException as exc:
            state.update(status="STOPPED_ON_FAILURE", error_type=type(exc).__name__, error=str(exc))
            raise
        finally:
            state["updated_unix"] = time.time()
            dump(base / "supervisor_status.json", state)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--formal", type=Path, required=True)
    parser.add_argument("--short", type=Path, required=True)
    parser.add_argument("--detach", action="store_true")
    args = parser.parse_args()
    if args.detach:
        args.base.mkdir(parents=True, exist_ok=True)
        with (args.base / "coordinator.log").open("ab") as log:
            process = subprocess.Popen(
                [sys.executable, "-B", __file__, "--base", str(args.base.resolve()),
                 "--formal", str(args.formal.resolve()), "--short", str(args.short.resolve())],
                stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                start_new_session=True)
        print(json.dumps({"pid": process.pid, "base": str(args.base.resolve())}))
    else:
        coordinator(args)
