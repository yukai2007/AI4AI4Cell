"""Use up to eight GPUs concurrently for the ten seed-42 lab-0 comparisons."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TRAIN_PYTHON = ROOT / "extensions/public_harness_20260924/.venv/bin/python"
DTI_PYTHON = Path("/opt/conda/envs/LDA/bin/python")
TASKS = ("native_tapb", "ptpc_neural", "norman_double_corrected",
         "vcc_corrected", "tahoe_drug_corrected")
HARNESSES = ("ai_scientist_v2", "ai_researcher")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".tmp-{os.getpid()}")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temp.replace(path)


def read(path):
    return json.loads(Path(path).read_text())


def jobs():
    # Start both costly DTI runs first, then fill the first wave with short jobs.
    return [(harness, task) for task in TASKS for harness in HARNESSES]


def command(base, harness, task, gpu, phase):
    root = base / harness / task / "seed42"
    if phase == "train":
        return [str(TRAIN_PYTHON), "-B", str(HERE / "run_one_lab.py"),
                "--harness", harness, "--task", task, "--seed", "42",
                "--gpus", "0", "--model-device", "cuda:0", "--output", str(root)]
    python = DTI_PYTHON if task == "native_tapb" else TRAIN_PYTHON
    result = [str(python), "-B", str(HERE / "heldout_one_lab.py"),
              "--run-dir", str(root / "development"), "--output", str(root / "heldout"),
              "--device", "cuda:0"]
    if harness == "ai_researcher":
        result.append("--budget-capped")
    return result


def terminal(base, harness, task):
    root = base / harness / task / "seed42"
    verification = root / "heldout/verification.json"
    if verification.is_file() and read(verification).get("status") == "PASS":
        return "VERIFIED"
    status_path = root / "run_status.json"
    if status_path.is_file() and read(status_path).get("status") == "FAILED":
        return "FAILED"
    return None


def main(args):
    base = args.base.resolve()
    if base.exists():
        raise ValueError("Use a fresh output directory for the lab-0 matrix")
    base.mkdir(parents=True)
    sources = {str(path): sha(path) for path in sorted(HERE.glob("*.py"))}
    matrix = jobs()
    manifest = {"schema": "public-harness-one-lab-matrix-v1", "created_unix": time.time(),
                "seed": 42, "clients": [0], "collaborative_aggregation": False,
                "research_model": "Qwen2.5-7B-Instruct", "designs": 12,
                "candidate_cap": 6, "candidate_rounds": 100,
                "gpus": list(range(args.gpus)), "jobs": [dict(harness=h, task=t) for h, t in matrix],
                "source_sha256": sources, "scorer": "same frozen held-out scorer as core table"}
    dump(base / "queue_manifest.json", manifest)
    pending = list(matrix); active = {}; completed = []; failed = []
    started = time.time(); interrupted = False

    def stop(sig, frame):
        nonlocal interrupted
        interrupted = True
    signal.signal(signal.SIGINT, stop); signal.signal(signal.SIGTERM, stop)

    while pending or active:
        for gpu in range(args.gpus):
            if gpu in active or not pending or interrupted:
                continue
            harness, task = pending.pop(0)
            phase = "train"
            cmd = command(base, harness, task, gpu, phase)
            root = base / harness / task / "seed42"
            root.parent.mkdir(parents=True, exist_ok=True)
            log_path = root.parent / "seed42.launch.log"
            log = log_path.open("ab", buffering=0)
            env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu),
                       PYTHONPATH=str(HERE) + os.pathsep + str(HERE.parent / "public_harness_20260924")
                                  + os.pathsep + str(ROOT))
            process = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env,
                                       start_new_session=True)
            active[gpu] = dict(process=process, log=log, log_path=str(log_path), phase=phase,
                               harness=harness, task=task, command=cmd, started_unix=time.time())

        time.sleep(2)
        for gpu, item in list(active.items()):
            process = item["process"]
            code = process.poll()
            if code is None:
                continue
            item["log"].close()
            harness, task, phase = item["harness"], item["task"], item["phase"]
            root = base / harness / task / "seed42"
            if phase == "train" and code == 0 and read(root / "run_status.json").get("status") == "DEVELOPMENT_COMPLETE":
                cmd = command(base, harness, task, gpu, "heldout")
                log_path = root.parent / "seed42.heldout.log"
                log = log_path.open("ab", buffering=0)
                env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu),
                           PYTHONPATH=str(HERE) + os.pathsep + str(HERE.parent / "public_harness_20260924")
                                      + os.pathsep + str(ROOT))
                next_process = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT,
                                                env=env, start_new_session=True)
                active[gpu] = dict(process=next_process, log=log, log_path=str(log_path), phase="heldout",
                                   harness=harness, task=task, command=cmd, started_unix=time.time())
                continue
            outcome = terminal(base, harness, task)
            receipt = dict(harness=harness, task=task, gpu=gpu, phase=phase,
                           exit_code=code, outcome=outcome, finished_unix=time.time())
            (completed if outcome == "VERIFIED" else failed).append(receipt)
            del active[gpu]

        state = {"status": "INTERRUPTING" if interrupted else "RUNNING",
                 "started_unix": started, "updated_unix": time.time(),
                 "active": [{k: v for k, v in item.items() if k not in ("process", "log")}
                            | {"pid": item["process"].pid, "gpu": gpu}
                            for gpu, item in active.items()],
                 "pending": [dict(harness=h, task=t) for h, t in pending],
                 "completed": completed, "failed": failed}
        dump(base / "supervisor_status.json", state)
        if interrupted:
            for item in active.values():
                try: os.killpg(item["process"].pid, signal.SIGTERM)
                except ProcessLookupError: pass
            for item in active.values():
                try: item["process"].wait(timeout=30)
                except subprocess.TimeoutExpired:
                    try: os.killpg(item["process"].pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                item["log"].close()
            raise InterruptedError("Lab-0 matrix interrupted; no result was fabricated")

    final = {"status": "COMPLETE" if not failed else "COMPLETE_WITH_FAILURES",
             "started_unix": started, "completed_unix": time.time(),
             "wall_seconds": time.time() - started, "active": [], "pending": [],
             "completed": completed, "failed": failed}
    dump(base / "supervisor_status.json", final)
    print(json.dumps(final, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--gpus", type=int, choices=range(1, 9), default=8)
    main(parser.parse_args())
