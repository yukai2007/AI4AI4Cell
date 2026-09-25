"""Isolated lab-0 view of the frozen public-harness broker.

The ten-laboratory broker remains byte-for-byte unchanged so its completed
receipts stay verifiable.  This module loads that implementation under a
private name, changes only the registered client roster to ``[0]``, and
re-exports the same API.  Broker methods retain the private module globals, so
every fit, definition check and development aggregate consistently uses lab 0.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent / "public_harness_20260924" / "broker.py"
MODULE_NAME = "_biocoloop_public_harness_broker_lab0"

spec = importlib.util.spec_from_file_location(MODULE_NAME, ORIGINAL)
if spec is None or spec.loader is None:
    raise ImportError(f"Cannot load frozen broker: {ORIGINAL}")
core = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = core
spec.loader.exec_module(core)
core.CLIENTS = [0]

for key in dir(core):
    if not key.startswith("__"):
        globals()[key] = getattr(core, key)

CLIENTS = [0]
SINGLE_LAB_PROTOCOL = "lab-0-only-v1"
ORIGINAL_BROKER_PATH = str(ORIGINAL)
