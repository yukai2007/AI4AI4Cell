"""Selection/evaluation invariants for native early stop under a six-slot cap."""
from __future__ import annotations

from pathlib import Path
import time

import broker as core


class BudgetCappedBroker(core.Broker):
    """Seal a genuine native trajectory that used one through six proposals."""

    def seal_selection(self):
        with self._lock():
            state = self._state()
            used = state["used_slots"]
            if (not 1 <= used <= core.SLOTS or len(state["requests"]) != used
                    or state["status"] not in ("READY", "DEVELOPMENT_SEALED")):
                raise ValueError("A bounded native trajectory is required before selection can be sealed")
            definition = core.read(self.output / "definition.json")
            self._verify(definition, data=True)
            core._verify_files({entry["path"]: entry["sha256"] for entry in state["requests"]})
            record = state["incumbent"]
            checkpoint = Path(record["checkpoint"])
            execution = core.read(checkpoint.parent / "execution_receipt.json")
            if (core.sha(checkpoint) != execution["checkpoint_sha256"]
                    or core.sha(checkpoint.parent / "fit.json") != execution["fit_sha256"]):
                raise ValueError("Selected checkpoint or fitting metadata changed after execution")
            selected = {"task": self.config.task, "seed": self.config.seed,
                        "harness": self.config.harness,
                        "selected_on": "development_primary_then_lower_loss",
                        "record": record, "test_read": False,
                        "proposal_slots_used": used, "proposal_slots_available": core.SLOTS}
            selection_path = self.output / "selected_development.json"
            seal_path = self.output / "selection_seal.json"
            if seal_path.exists():
                seal = core.read(seal_path)
                if (core.sha(selection_path) != seal["selection_sha256"]
                        or core.sha(checkpoint) != seal["checkpoint_sha256"]):
                    raise ValueError("Sealed selection/checkpoint changed")
                return {**self._public_status(state), "seal_sha256": core.sha(seal_path)}
            if core.read(checkpoint.parent / "fit.json") != {k: v for k, v in record.items() if k != "checkpoint"}:
                raise ValueError("Selected fitting metadata changed")
            trace = core._trace_receipt(self.config.native_trace_path, required=True)
            core.dump(selection_path, selected)
            seal = {
                "schema": "public-harness-development-selection-seal-v1",
                "task": self.config.task, "seed": self.config.seed,
                "harness": self.config.harness, "role": core.ROLE,
                "definition_sha256": core.sha(self.output / "definition.json"),
                "selection_sha256": core.sha(selection_path),
                "checkpoint": str(checkpoint), "checkpoint_sha256": core.sha(checkpoint),
                "fit_sha256": core.sha(checkpoint.parent / "fit.json"),
                "request_receipts": state["requests"], "native_trace": trace,
                "sealed_unix": time.time(), "test_read": False,
                "feedback_to_controller": False, "heldout_evaluation_performed": False,
                "execution_kind": definition["execution_kind"],
                "proposal_slots_used": used, "proposal_slots_available": core.SLOTS,
                "native_early_stop_retained": used < core.SLOTS,
            }
            core.dump(seal_path, seal)
            state["status"] = "DEVELOPMENT_SEALED"
            core.dump(self.output / "state.json", state)
            return {**self._public_status(state), "seal_sha256": core.sha(seal_path)}


def validate_run(run_dir):
    """Original held-out validator with proposal count interpreted as a cap."""
    import heldout_public as heldout

    run_dir = Path(run_dir).resolve()
    definition = core.read(run_dir / "definition.json")
    if definition.get("execution_kind") != "fresh-canonical-v3":
        raise ValueError("Only real fresh-canonical-v3 runs may be evaluated")
    if (definition.get("schema") != "public-harness-development-v1"
            or definition.get("rounds") != core.ROUNDS or definition.get("slots") != core.SLOTS
            or definition.get("clients") != core.CLIENTS or definition.get("test_read") is not False
            or definition.get("designs") != core.load_v3_designs()):
        raise ValueError("Not the registered six-candidate-maximum development protocol")
    config = core.BrokerConfig(**definition["config"])
    if Path(config.output_dir) != run_dir:
        raise ValueError("Run directory differs from its registered output location")
    core.Broker(config)._verify(definition, data=True)
    state, selection, seal = (core.read(run_dir / name) for name in
                              ("state.json", "selected_development.json", "selection_seal.json"))
    used = state.get("used_slots")
    if (state.get("status") != "DEVELOPMENT_SEALED" or not isinstance(used, int)
            or not 1 <= used <= core.SLOTS):
        raise ValueError("Native development selection lacks a valid bounded trajectory")
    if (seal.get("schema") != "public-harness-development-selection-seal-v1"
            or seal.get("role") != core.ROLE or seal.get("execution_kind") != "fresh-canonical-v3"
            or seal.get("test_read") is not False or seal.get("feedback_to_controller") is not False
            or seal.get("heldout_evaluation_performed") is not False
            or seal.get("proposal_slots_used") != used
            or seal.get("proposal_slots_available") != core.SLOTS
            or selection.get("proposal_slots_used") != used
            or selection.get("proposal_slots_available") != core.SLOTS):
        raise ValueError("Invalid budget-capped development-only selection seal")
    for key in ("task", "seed", "harness"):
        if selection.get(key) != getattr(config, key) or seal.get(key) != getattr(config, key):
            raise ValueError("Selection identity does not match the native run")
    core._verify_files({str(run_dir / "definition.json"): seal["definition_sha256"],
                        str(run_dir / "selected_development.json"): seal["selection_sha256"],
                        seal["checkpoint"]: seal["checkpoint_sha256"]})
    if core._trace_receipt(config.native_trace_path, required=True) != seal["native_trace"]:
        raise ValueError("Final native execution trace changed after selection was sealed")
    entries = seal["request_receipts"]
    if (len(entries) != used or [entry["slot"] for entry in entries] != list(range(1, used + 1))
            or entries != state["requests"]):
        raise ValueError("Immutable native submission receipts do not match the used proposal budget")
    menu = definition["designs"]
    incumbent = state["baseline"]
    if Path(incumbent["checkpoint"]).resolve() != run_dir / "fits/fixed_D00/best.pt":
        raise ValueError("Reference checkpoint is not the fresh fit in this run")
    heldout._check_fit(incumbent, menu["D00"], definition)
    seen = {"D00"}
    metadata = {str(run_dir / name): core.sha(run_dir / name) for name in
                ("definition.json", "state.json", "selected_development.json", "selection_seal.json")}
    for entry in entries:
        path = Path(entry["path"]).resolve()
        if (path != run_dir / "requests" / f"slot_{entry['slot']:02d}.json"
                or core.sha(path) != entry["sha256"]):
            raise ValueError("Submission receipt path or hash changed")
        metadata[str(path)] = entry["sha256"]
        request = core.read(path)
        if (request.get("slot") != entry["slot"] or request.get("test_read") is not False
                or request.get("cache_hit") is not False):
            raise ValueError("Submission receipt violates the execution contract")
        reply = request["reply"]
        if reply.get("remaining_slots") != core.SLOTS - entry["slot"] or reply.get("test_read") is not False:
            raise ValueError("Controller received inconsistent budget/evidence metadata")
        raw = request["request"]
        design_id = raw.get("design_id") if isinstance(raw, dict) else None
        status = request["status"]
        if status != reply["status"]:
            raise ValueError("Request/result status differs")
        if status == "INVALID":
            if reply.get("accepted") or request.get("fit"):
                raise ValueError("Invalid requests cannot select or fit models")
        elif status == "DUPLICATE":
            if design_id not in seen or reply.get("accepted") or request.get("fit"):
                raise ValueError("Duplicate receipt does not describe a prior design")
        elif status in ("COMPLETE", "NUMERICAL_FAILURE"):
            fields = {"design_id", "hypothesis", "experiment", "expected_effect"}
            if (not isinstance(raw, dict) or set(raw) != fields
                    or any(not isinstance(raw[key], str) or not raw[key].strip() for key in fields)):
                raise ValueError("Executed request did not satisfy the four-string submission schema")
            if design_id not in menu or design_id in seen:
                raise ValueError("An executed request is outside the legal untried menu")
            seen.add(design_id)
            if status == "NUMERICAL_FAILURE":
                if reply.get("accepted"):
                    raise ValueError("A numerical failure cannot replace the incumbent")
            else:
                candidate = request["fit"]
                expected = run_dir / "fits" / f"slot_{entry['slot']:02d}_{design_id}" / "best.pt"
                if Path(candidate["checkpoint"]).resolve() != expected:
                    raise ValueError("Candidate checkpoint is not the fresh native submission fit")
                heldout._check_fit(candidate, menu[design_id], definition)
                a, b = candidate["best"]["development"], incumbent["best"]["development"]
                accepted = (a["primary"], -a["loss"]) > (b["primary"], -b["loss"])
                if reply.get("accepted") != accepted or reply.get("candidate") != a:
                    raise ValueError("Candidate evidence/acceptance differs from measured development")
                if accepted:
                    incumbent = candidate
        else:
            raise ValueError("Incomplete requests cannot enter held-out evaluation")
        if (reply["incumbent"]["config"] != incumbent["config"]
                or reply["incumbent"]["development"] != incumbent["best"]["development"]):
            raise ValueError("Published controller development history is inconsistent")
    if (selection["record"] != incumbent or state["incumbent"] != incumbent
            or incumbent["checkpoint"] != seal["checkpoint"]):
        raise ValueError("Final checkpoint is not the reconstructed development incumbent")
    if core.sha(Path(incumbent["checkpoint"]).parent / "fit.json") != seal["fit_sha256"]:
        raise ValueError("Selected fitting record changed after selection seal")
    if definition["created_unix"] > seal["sealed_unix"]:
        raise ValueError("Selection seal preceded run registration")
    return definition, selection, seal, metadata
