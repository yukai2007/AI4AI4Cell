"""Final AI-Researcher run preserving native early stop under a six-slot cap."""
from __future__ import annotations

import argparse
import copy
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import airesearcher_budget_cap_v3 as v3
import budget_cap_protocol_v4 as protocol
from broker import dump, read, sha
import run_airesearcher_compact as runner
import supervise as frozen

HERE = Path(__file__).resolve().parent
VERSION = "airesearcher-task-transport-budget-cap-v4"
TASKS = ("norman_double_corrected", "vcc_corrected", "tahoe_drug_corrected")
TRAIN_TASKS = TASKS + ("native_tapb",)


class FinalAIResearcher(v3.BudgetCappedAIResearcher):
    def _provenance(self):
        super()._provenance()
        path = self.output / "provenance.json"
        record = read(path)
        record["transport_revision"].update(
            version=VERSION, source_sha256=sha(__file__),
            selection_boundary_source_sha256=sha(protocol.__file__),
            heldout_validator="same scorer; proposal receipts validated from slot 1 through native stop",
        )
        dump(path, record)


def controller(broker, backend, *, trace_dir, registered_designs, task_description,
               task_name, seed, upstream_repo):
    adapter = FinalAIResearcher(broker, backend, trace_dir, upstream=upstream_repo)
    adapter.task_description = task_description
    adapter.task_name = task_name
    adapter.registered_designs = copy.deepcopy(registered_designs)
    adapter.seed = seed
    return adapter.run()


def train(args):
    original_config = runner.BrokerConfig

    def config(**kwargs):
        kwargs["adapter_paths"] = tuple(kwargs["adapter_paths"]) + (
            str(Path(v3.__file__).resolve()), str(Path(protocol.__file__).resolve()),
            str(Path(__file__).resolve()))
        return original_config(**kwargs)

    runner.Broker = protocol.BudgetCappedBroker
    runner.BrokerConfig = config
    runner.run_airesearcher = controller
    runner.VERSION = VERSION
    runner.run(args)


def source_pins():
    result = v3.source_pins()
    for path in (Path(protocol.__file__).resolve(), Path(__file__).resolve(),
                 HERE / "heldout_public_budget_cap_v4.py", HERE / "verify_public_budget_cap_v4.py"):
        result[str(path)] = sha(path)
    return result


def queue(args):
    base, parent, formal = map(lambda path: path.resolve(), (args.base, args.parent, args.formal))
    base.mkdir(parents=True, exist_ok=True)
    with (base / ".repair.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (base / "queue_manifest.json").exists():
            raise ValueError("Versioned queue already registered")
        parent_manifest = read(parent / "queue_manifest.json")
        parent_state = read(parent / "supervisor_status.json")
        if (parent_manifest.get("schema") != "public-harness-budget-cap-repair-queue-v3"
                or parent_state.get("status") != "STOPPED_ON_FAILURE"):
            raise ValueError("Expected the immutable budget-cap-v3 predecessor")
        predecessor = Path(parent_manifest["parent_queue"]).resolve()
        ptpc = predecessor / "ai_researcher/ptpc_neural/seed42"
        if (read(ptpc / "run_status.json").get("status") != "DEVELOPMENT_COMPLETE"
                or read(ptpc / "heldout/verification.json").get("status") != "PASS"):
            raise ValueError("The predecessor's PTPC result is not independently verified")
        formal_manifest = read(formal / "queue_manifest.json")
        deadline = formal_manifest["created_unix"] + formal_manifest["max_wall_hours"] * 3600
        now = time.time()
        manifest = {
            "schema": "public-harness-budget-cap-repair-queue-v4", "created_unix": now,
            "jobs": [{"harness": "ai_researcher", "task": task, "seed": 42} for task in TASKS],
            "source_sha256": source_pins(), "max_gpu_hours": 2.0, "deadline_unix": deadline,
            "fitting_gpus": [0], "model_gpu": 0, "shared_gpu": True,
            "parent_queue": str(parent), "ptpc_queue": str(predecessor), "formal_queue": str(formal),
            "protocol_version": VERSION,
            "proposal_budget": {"maximum": 6, "minimum_before_native_early_stop": 1},
            "select_tasks_by_test_score": False, "development_retries": False,
        }
        dump(base / "queue_manifest.json", manifest)
        state = {"status": "RUNNING", "pid": os.getpid(), "started_unix": now,
                 "updated_unix": now, "reserved_gpu_hours": 0.0, "completed": [], "failed": []}
        dump(base / "supervisor_status.json", state)

        def interrupted(sig, frame):
            raise InterruptedError(f"Version-4 supervisor signal {sig}")
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, interrupted)

        def child(command, log, gpus):
            if source_pins() != manifest["source_sha256"]:
                raise ValueError("Versioned runtime changed")
            frozen.run_child(command, log, base, state, reserved_gpus=gpus,
                             max_gpu_hours=2.0, deadline=deadline)

        try:
            for job in manifest["jobs"]:
                run = base / "ai_researcher" / job["task"] / "seed42"
                state.update(current_job=job, phase="DEVELOPMENT")
                try:
                    child([str(HERE / ".venv/bin/python"), "-B", str(Path(__file__).resolve()),
                           "--train", "--task", job["task"], "--output", str(run)],
                          base / "logs" / f"{job['task']}.log", 1)
                except frozen.ChildExitedError:
                    failure = frozen.controller_failure(run, job, read(run / "run_status.json"))
                    if failure is None:
                        raise
                    state["failed"].append(failure)
                    dump(base / "supervisor_status.json", state)
                    continue
                state["phase"] = "HELDOUT_EVALUATION"
                child([frozen.LDA, "-B", str(HERE / "heldout_public_budget_cap_v4.py"),
                       "--run-dir", str(run / "development"), "--output", str(run / "heldout"),
                       "--device", "cpu"], run / "evaluation.log", 0)
                state["phase"] = "INDEPENDENT_RESCORING"
                child([frozen.LDA, "-B", str(HERE / "verify_public_budget_cap_v4.py"),
                       str(run / "heldout")], run / "verification.log", 0)
                result = read(run / "heldout/results.json")
                state["completed"].append({**job, "primary": result["primary"],
                                           "metric": result["primary_metric"], "output": str(run)})
                dump(base / "supervisor_status.json", state)
            state.update(status="FINISHED_WITH_INCOMPLETE_RUNS" if state["failed"] else "COMPLETE",
                         phase="TERMINAL")
        except BaseException as exc:
            state.update(status="STOPPED_ON_FAILURE", error_type=type(exc).__name__, error=str(exc))
            raise
        finally:
            state["updated_unix"] = time.time()
            dump(base / "supervisor_status.json", state)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--task", choices=TRAIN_TASKS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--gpus", default="0")
    parser.add_argument("--model-device", default="cuda:0")
    parser.add_argument("--base", type=Path)
    parser.add_argument("--parent", type=Path)
    parser.add_argument("--formal", type=Path)
    parser.add_argument("--detach", action="store_true")
    args = parser.parse_args()
    if args.train:
        train(args)
    elif args.detach:
        args.base.mkdir(parents=True, exist_ok=True)
        with (args.base / "supervisor.log").open("ab") as log:
            process = subprocess.Popen(
                [sys.executable, "-B", __file__, "--base", str(args.base.resolve()),
                 "--parent", str(args.parent.resolve()), "--formal", str(args.formal.resolve())],
                stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
        print(json.dumps({"pid": process.pid, "base": str(args.base.resolve())}))
    else:
        queue(args)
