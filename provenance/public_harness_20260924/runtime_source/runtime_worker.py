"""Spawn-safe adapter registration; delegates all optimization to frozen V3."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "extensions/core_ablation_20260922"))
# This imports native environment bootstrap before torch, and registers both
# TAPB and the neural PTPC adapter in every newly spawned interpreter.
import common
from core_v3 import local_worker as canonical_local_worker


def registered_local_worker(conn, path, client, device):
    return canonical_local_worker(conn, path, client, device)


def make_federation(path, clients, gpu_ids):
    # VariableFederation resolves its worker target from this global. A distinct
    # importable wrapper is needed because broker imports the runtime lazily.
    # Restore immediately; no training/core file or math is modified.
    previous = common.local_worker
    common.local_worker = registered_local_worker
    try:
        return common.VariableFederation(path, clients, gpu_ids)
    finally:
        common.local_worker = previous
