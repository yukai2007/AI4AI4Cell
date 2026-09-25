"""Independent unchanged metric recomputation with capped-slot validation."""
from __future__ import annotations

import argparse
from pathlib import Path

import budget_cap_protocol_v4 as protocol
import heldout_public
import verify_public as original


def verify(output):
    previous = heldout_public.validate_run
    heldout_public.validate_run = protocol.validate_run
    try:
        return original.verify(output)
    finally:
        heldout_public.validate_run = previous


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    receipt = verify(args.output)
    print({"status": receipt["status"], "task": receipt["task"], "seed": receipt["seed"]})
