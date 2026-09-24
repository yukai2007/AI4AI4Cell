"""Trusted, development-only six-slot execution boundary for public harnesses.

The native controller supplies JSON data, never executable code. Production
fits use the unchanged V3 trainer and registered task adapters. Importing this
module does not import torch, start workers, or inspect held-out responses.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import fcntl
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
UNIFIED = ROOT / "extensions/unified_bio_20260918"
BASE = ROOT / "results/unified_bio_20260918"
CLIENTS = list(range(10))
ROUNDS = 100
SLOTS = 6
ROLE = "retrospective held-out; prior historical exposure; not blind confirmation"
TASK_DESCRIPTIONS = {
    "native_tapb": "BindingDB binary classification with pinned TAPB architecture, fresh task weights, frozen public ESM features and the shared client0-training-only dictionary; primary equal-client AUROC, log-loss tiebreak.",
    "ptpc_neural": "PTPC efficacy prediction from observed 6h and 24h proteomes and Morgan fingerprints, using the randomly initialized ProteinTalks-derived efficacy head (not full ppODE); primary equal-client AP, BCE tiebreak.",
    "vcc_corrected": "VCC single-gene identification using the mask-corrected frozen scDEBART backbone and trainable response head; primary equal-client intervention-macro five-option Top-1, cross-entropy tiebreak.",
    "norman_double_corrected": "Norman double-gene identification using the mask-corrected frozen scDEBART backbone and trainable response head; primary equal-client intervention-macro five-option Top-1, cross-entropy tiebreak.",
    "tahoe_drug_corrected": "Tahoe drug identification at fixed context/dose using the mask-corrected frozen scDEBART backbone and registered chemical-conditioning adapter; primary equal-client intervention-macro five-option Top-1, cross-entropy tiebreak.",
}
NUMERICAL_ERRORS = (
    "Non-finite training objective", "probabilities must contain only finite values",
    "Non-finite local model update", "Non-finite aggregated state",
)


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def json_copy(value):
    return json.loads(json.dumps(value, allow_nan=False))


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    with temporary.open("w") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _assignment(path, name):
    for node in ast.parse(Path(path).read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return node.value
    raise ValueError(f"Missing trusted assignment {name}")


def _config_literal(node, default=None):
    # Only the literal dict syntax in the registered V3 menu is accepted.
    # No eval/exec/import of the LLM controller (or its torch dependency).
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "dict":
        raise ValueError("Unexpected trusted menu syntax")
    result = {}
    if node.args:
        if len(node.args) != 1 or not isinstance(node.args[0], ast.Name) or node.args[0].id != "DEFAULT" or default is None:
            raise ValueError("Unexpected trusted menu base")
        result.update(default)
    for keyword in node.keywords:
        if keyword.arg is None:
            raise ValueError("Unexpected menu keyword expansion")
        result[keyword.arg] = ast.literal_eval(keyword.value)
    return result


def load_v3_designs():
    default = _config_literal(_assignment(UNIFIED / "core.py", "DEFAULT"))
    node = _assignment(UNIFIED / "research_v2.py", "DESIGNS")
    if not isinstance(node, ast.Dict):
        raise ValueError("Unexpected V3 menu container")
    menu = {ast.literal_eval(k): _config_literal(v, default) for k, v in zip(node.keys, node.values)}
    if set(menu) != {f"D{i:02d}" for i in range(12)} or menu["D00"] != default:
        raise ValueError("The registered twelve-design V3 menu changed")
    if any(config.get("prox_mu") != 0 for config in menu.values()):
        raise ValueError("Unexpected FedProx search variation")
    return menu


DESIGNS = load_v3_designs()


class BudgetExhausted(RuntimeError):
    pass


class InfrastructureFailure(RuntimeError):
    """An infrastructure failure aborts the run; it is not negative evidence."""


@dataclass(frozen=True)
class BrokerConfig:
    task: str
    seed: int
    harness: str
    output_dir: str
    upstream_repo: str
    upstream_commit: str
    native_trace_path: str
    gpu_ids: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7)
    adapter_paths: tuple[str, ...] = ()

    def __post_init__(self):
        if self.task not in TASK_DESCRIPTIONS or type(self.seed) is not int or self.seed not in (42, 43, 44):
            raise ValueError("Use a registered main-table task and seed 42, 43, or 44")
        if not self.harness or not self.upstream_commit or not self.native_trace_path:
            raise ValueError("Harness, pinned upstream commit and native trace path are required")
        if not self.gpu_ids or any(type(g) is not int or g < 0 for g in self.gpu_ids):
            raise ValueError("gpu_ids must contain nonnegative logical CUDA device IDs")
        object.__setattr__(self, "gpu_ids", tuple(self.gpu_ids))
        object.__setattr__(self, "adapter_paths", tuple(self.adapter_paths))
        for name in ("output_dir", "upstream_repo", "native_trace_path"):
            object.__setattr__(self, name, str(Path(getattr(self, name)).resolve()))
        object.__setattr__(self, "adapter_paths", tuple(str(Path(p).resolve()) for p in self.adapter_paths))
        if Path(self.output_dir) in (ROOT, HERE, BASE, Path("/")):
            raise ValueError("A dedicated run output directory is required")


def _verify_files(expected):
    for path, digest in expected.items():
        if sha(path) != digest:
            raise ValueError(f"Registered source/data binding changed: {path}")


def _git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE)


def _upstream_binding(config):
    repo = Path(config.upstream_repo)
    head = _git(repo, "rev-parse", "HEAD").decode().strip()
    if head != config.upstream_commit:
        raise ValueError("Upstream HEAD does not match the explicitly pinned full commit")
    tracked = _git(repo, "ls-files", "-z").decode().split("\0")
    files = {str(repo / p): sha(repo / p) for p in tracked if p and (repo / p).is_file()}
    return {"repository": str(repo), "commit": head, "tracked_file_sha256": files,
            "tracked_diff_sha256": hashlib.sha256(_git(repo, "diff", "--binary", "HEAD", "--")).hexdigest()}


def _native_source_files(source):
    """Match the canonical loader: some upstream files exist only as git blobs."""
    repo = ROOT / "references/performance_first_20260913/TAPB"
    if _git(repo, "rev-parse", "HEAD").decode().strip() != source["commit"]:
        raise ValueError("Pinned native TAPB source commit changed")
    present = {}
    for relative, expected in source["files"].items():
        blob = _git(repo, "show", f"{source['commit']}:{relative}")
        if hashlib.sha256(blob).hexdigest() != expected:
            raise ValueError("Pinned native TAPB git source changed")
        path = repo / relative
        if path.exists():
            if sha(path) != expected:
                raise ValueError("Native TAPB worktree differs from pinned source")
            present[str(path)] = expected
    return present


def production_binding(config):
    """Hash train/dev/public artifacts only; do not hash or decode test responses."""
    data = BASE / config.task / "data"
    manifest = read(data / "manifest.json")
    if manifest.get("test_read") is not False:
        raise ValueError("Task manifest must declare test_read=false")
    data_files = {str(data / "manifest.json"): sha(data / "manifest.json")}
    source_paths = [HERE / "broker.py", HERE / "runtime_worker.py",
                    ROOT / "extensions/core_ablation_20260922/common.py"]
    source_paths += [UNIFIED / name for name in (
        "core.py", "core_v3.py", "adapters.py", "run_v3.py", "research_v2.py", "native_run.py",
        "run_native_tapb.py", "run_ptpc_neural.py", "tapb_native_adapter.py", "ptpc_neural_adapter.py")]
    source_paths += [ROOT / "extensions/federated_bio_20260918" / name for name in ("engine.py", "scdebart.py")]
    source_paths += [ROOT / "extensions/proteomics" / name for name in ("ptpc_model.py", "scoring.py")]
    source_paths += [ROOT / "runtime/experiments/drugevolve_transfer/scoring.py"]
    registration = {"kind": manifest["kind"], "data_path": str(data)}
    if config.task == "native_tapb":
        data_files.update({str(data / relative): value for relative, value in manifest["data_sha256"].items()})
        source_paths += [ROOT / "extensions/tapb_reference_20260913/prepare.py"]
        native_hashes = _native_source_files(manifest["source"])
        source_paths += [Path(p) for p in native_hashes]
        registration.update(worker_python=manifest["worker_python"], source=manifest["source"],
                            dictionary_scope=manifest["dictionary_scope"], dictionary_seed=manifest["dictionary_seed"],
                            public_feature_root=manifest["public_feature_root"],
                            public_feature_sha256=manifest["public_feature_sha256"])
        if not Path(manifest["worker_python"]).is_file():
            raise ValueError("Registered native worker interpreter is unavailable")
    elif config.task == "ptpc_neural":
        data_files.update({str(data / relative): value for relative, value in manifest["shard_sha256"].items()})
        data_files[manifest["source"]] = manifest["source_sha256"]
        registration.update(model=manifest["model"], feature_version=manifest["feature_version"],
                            model_version="ptpc-observed-6h24h-head-v1", initialization=manifest["initialization"])
    else:
        source = Path(manifest["data_root"])
        expected = BASE / "corrected_features" / config.task / "data"
        if source.resolve() != expected.resolve():
            raise ValueError("Corrected cell task must use its exact registered data path")
        data_files[str(source / "manifest.json")] = manifest["source_manifest_sha256"]
        cell = read(source / "manifest.json")
        if cell["biological_test_responses_read"] is not False:
            raise ValueError("Corrected features consumed biological test responses")
        data_files.update({str(source / relative): digest for relative, digest in cell["preserved_training_shards"].items()})
        data_files[str(source / "public_hidden.npy")] = manifest["feature_sha256"]
        data_files[str(source / "initial_head.pt")] = cell["initial_head_sha256"]
        for filename in ("scoring_mask.npy", "gene_ids.npy"):
            data_files[str(source / filename)] = sha(source / filename)
        correction = ROOT / "extensions/scdebart_maskfix_20260918"
        correction_hashes = {str(correction / name): digest for name, digest in cell["feature_generator_sha256"].items()}
        _verify_files(correction_hashes)
        source_paths += [Path(p) for p in correction_hashes]
        registration.update(adapter="mask-corrected scDEBART adaptation", data_root=str(source),
                            correction_source_sha256=correction_hashes, biological_test_responses_read=False)
    _verify_files(data_files)
    source_paths += [Path(p) for p in config.adapter_paths]
    sources = {str(p): sha(p) for p in source_paths}
    versions = {}
    for name in ("torch", "transformers", "numpy", "pandas"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return {"data_manifest_sha256": sha(data / "manifest.json"), "data_files_sha256": data_files,
            "source_sha256": sources, "task_registration": registration,
            "upstream": _upstream_binding(config),
            "runtime": {"python": sys.version, "executable": sys.executable, "platform": platform.platform(),
                        "packages": versions, "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
                        "gpu_ids": list(config.gpu_ids)}}


def _trace_receipt(path, required=False):
    path = Path(path).resolve()
    if path.is_file():
        return {"path": str(path), "sha256": sha(path)}
    if path.is_dir():
        files = {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob("*")) if p.is_file()}
        if files:
            return {"path": str(path), "files_sha256": files}
    if required:
        raise ValueError("A nonempty native trace must exist before sealing development selection")
    return {"path": str(path), "status": "NOT_YET_WRITTEN"}


class _CanonicalFitter:
    def __init__(self, config):
        # Lazy: import-only/API/status/tests never load torch or touch GPUs.
        if str(HERE) not in sys.path:
            sys.path.insert(0, str(HERE))
        import runtime_worker
        self.federation = runtime_worker.make_federation(BASE / config.task / "data", CLIENTS, config.gpu_ids)

    def fit(self, config, clients, out, seed, rounds):
        return self.federation.fit(config, clients, out, seed=seed, rounds=rounds)

    def close(self):
        self.federation.close()


def _evidence(record):
    development = record["best"]["development"]
    clean = {key: development[key] for key in ("primary", "loss", "worst_client", "clients") if key in development}
    if any(not math.isfinite(float(clean[key])) for key in ("primary", "loss")):
        raise ValueError("Non-finite development evidence")
    curve = [row for row in record["history"] if "development" in row]
    def point(row):
        return {"round": row["round"], "train_loss": row.get("train_loss"),
                "development": {key: row["development"][key] for key in ("primary", "loss", "worst_client", "clients") if key in row["development"]}}
    return {"config": json_copy(record["config"]), "development": clean, "best_round": record["best"]["round"],
            "training_diagnostics": {"first": point(curve[0]), "last": point(curve[-1]),
                "primary_gain_last_minus_first": curve[-1]["development"]["primary"] - curve[0]["development"]["primary"],
                "loss_change_last_minus_first": curve[-1]["development"]["loss"] - curve[0]["development"]["loss"]}}


class Broker:
    """One immutable run; injected fitters are explicitly test-only evidence."""
    def __init__(self, config: BrokerConfig | dict, fitter=None, *, test_binding=None):
        self.config = BrokerConfig(**config) if isinstance(config, dict) else config
        self.output = Path(self.config.output_dir)
        self.output.mkdir(parents=True, exist_ok=True)
        self._fitter = fitter
        self._injected = fitter is not None
        if test_binding is not None and not self._injected:
            raise ValueError("Synthetic provenance is allowed only with an injected test fitter")
        self._test_binding = test_binding
        self.designs = load_v3_designs()

    @contextmanager
    def _lock(self):
        with (self.output / ".broker.lock").open("a") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def _state(self):
        return read(self.output / "state.json")

    def _verify(self, definition, *, data=False):
        if definition["config"] != json_copy(asdict(self.config)) or definition["designs"] != self.designs:
            raise ValueError("Cannot use a changed run configuration or design menu")
        if definition["execution_kind"] == "injected-test-fitter":
            if not self._injected:
                raise ValueError("Test artifacts cannot be resumed as a production run")
            return
        binding = definition["binding"]
        _verify_files(binding["source_sha256"])
        if sha(BASE / self.config.task / "data/manifest.json") != binding["data_manifest_sha256"]:
            raise ValueError("Task manifest changed during execution")
        if _upstream_binding(self.config) != binding["upstream"]:
            raise ValueError("Native upstream source changed during execution")
        if self.config.task == "native_tapb":
            _native_source_files(binding["task_registration"]["source"])
        if data:
            _verify_files(binding["data_files_sha256"])

    def _fit(self, config, target):
        if target.exists():
            raise InfrastructureFailure("Fresh fitting required: target already exists; no cache replay or overwrite")
        if self._fitter is None:
            self._fitter = _CanonicalFitter(self.config)
        started = time.monotonic()
        record = self._fitter.fit(json_copy(config), list(CLIENTS), target, seed=self.config.seed, rounds=ROUNDS)
        if record.get("status") == "NUMERICAL_FAILURE":
            return record
        if (record.get("config") != config or record.get("clients") != CLIENTS or record.get("seed") != self.config.seed
                or record.get("rounds") != ROUNDS or len(record.get("history", [])) != ROUNDS or record.get("test_read") is not False):
            raise InfrastructureFailure("Fitter returned a different protocol or incomplete fit")
        if not (target / "best.pt").is_file() or not (target / "fit.json").is_file():
            raise InfrastructureFailure("Completed fitting requires immutable fit.json and best.pt")
        if read(target / "fit.json") != record:
            raise InfrastructureFailure("Fitter return differs from its persisted metadata")
        _evidence(record)
        record = dict(record, checkpoint=str(target / "best.pt"))
        dump(target / "execution_receipt.json", {"fresh_fit": True, "cache_hit": False,
             "wall_seconds": time.monotonic() - started, "training_seconds": record.get("training_seconds"),
             "model_update_bytes": record.get("model_update_bytes"), "checkpoint_sha256": sha(target / "best.pt"),
             "fit_sha256": sha(target / "fit.json"), "completed_unix": time.time(), "test_read": False})
        return record

    def initialize(self):
        with self._lock():
            if (self.output / "definition.json").exists():
                definition = read(self.output / "definition.json")
                if definition["config"] != json_copy(asdict(self.config)) or definition["designs"] != self.designs:
                    raise ValueError("Cannot resume a changed run definition")
                self._verify(definition)
                if not (self.output / "state.json").exists():
                    raise InfrastructureFailure("Interrupted initialization; preserve artifacts and use a fresh run directory")
                return self._public_status(self._state())
            if self._injected:
                binding = json_copy(self._test_binding or {"test_only": True})
            else:
                binding = production_binding(self.config)
            definition = {"schema": "public-harness-development-v1", "config": json_copy(asdict(self.config)),
                "task_description": TASK_DESCRIPTIONS[self.config.task], "rounds": ROUNDS, "slots": SLOTS,
                "clients": CLIENTS, "designs": self.designs, "selection": "development_primary_then_lower_loss",
                "execution_kind": "injected-test-fitter" if self._injected else "fresh-canonical-v3",
                "cache_policy": "disabled; each accepted novel request executes a fresh fit",
                "heldout_role": ROLE, "test_read": False, "feedback_to_controller": "development_only",
                "binding": binding, "created_unix": time.time()}
            dump(self.output / "definition.json", definition)
            self._verify(definition)
            fixed = self._fit(self.designs["D00"], self.output / "fits/fixed_D00")
            if fixed.get("status") == "NUMERICAL_FAILURE":
                raise InfrastructureFailure("Fixed reference failed; no valid baseline")
            state = {"status": "READY", "used_slots": 0, "seen": ["D00"], "incumbent": fixed,
                     "baseline": fixed, "requests": [], "test_read": False}
            dump(self.output / "state.json", state)
            return self._public_status(state)

    def _public_status(self, state):
        return {"status": state["status"], "task": self.config.task, "seed": self.config.seed,
                "harness": self.config.harness, "budget": SLOTS, "used_slots": state["used_slots"],
                "remaining_slots": SLOTS - state["used_slots"], "baseline": _evidence(state["baseline"]),
                "incumbent": _evidence(state["incumbent"]),
                "available_designs": {key: json_copy(value) for key, value in self.designs.items() if key not in state["seen"]},
                "test_read": False}

    def status(self):
        with self._lock():
            if not (self.output / "state.json").exists():
                return {"status": "NOT_INITIALIZED", "budget": SLOTS, "used_slots": 0, "remaining_slots": SLOTS, "test_read": False}
            return self._public_status(self._state())

    def evaluate(self, request: Any, *, native_trace_path=None, model_receipts=None):
        with self._lock():
            state = self._state()
            if state["used_slots"] >= SLOTS or state["status"] == "DEVELOPMENT_SEALED":
                raise BudgetExhausted("All six proposal slots have been consumed")
            if state["status"] != "READY":
                raise InfrastructureFailure("Run is not ready; interrupted/infrastructure-failed fits are not silently replayed")
            definition = read(self.output / "definition.json")
            self._verify(definition)
            slot = state["used_slots"] + 1
            state.update(used_slots=slot, status="FIT_IN_PROGRESS")
            dump(self.output / "state.json", state)  # Durable budget charge before any execution.
            target = self.output / "requests" / f"slot_{slot:02d}.json"
            try:
                raw = json_copy(request)
                receipts = json_copy(model_receipts or [])
            except (TypeError, ValueError):
                raw, receipts = {"invalid_serialization": True}, []
            design_id = raw.get("design_id") if isinstance(raw, dict) else None
            trace_path = Path(native_trace_path or self.config.native_trace_path).resolve()
            trace_root = Path(self.config.native_trace_path).resolve()
            trace_valid = trace_path == trace_root or trace_root in trace_path.parents
            trace = _trace_receipt(trace_path) if trace_valid else {"status": "OUTSIDE_CONFIGURED_TRACE_BOUNDARY"}
            receipt = {"slot": slot, "request": raw, "model_receipts": receipts,
                       "native_trace": trace, "submitted_unix": time.time(), "test_read": False, "cache_hit": False}
            dump(target, receipt)
            result_status, diagnosis, record = "COMPLETE", None, None
            fields = {"design_id", "hypothesis", "experiment", "expected_effect"}
            if (not trace_valid or not isinstance(raw, dict) or set(raw) != fields or
                    any(not isinstance(raw[k], str) or not raw[k].strip() for k in fields) or design_id not in self.designs):
                result_status, diagnosis = "INVALID", "Exactly four nonempty strings, a registered design_id and a trace inside the configured boundary are required"
            elif design_id in state["seen"]:
                result_status, diagnosis = "DUPLICATE", "Previously tried designs cannot be submitted again"
            else:
                state["seen"].append(design_id)
                dump(self.output / "state.json", state)
                try:
                    record = self._fit(self.designs[design_id], self.output / "fits" / f"slot_{slot:02d}_{design_id}")
                    if record.get("status") == "NUMERICAL_FAILURE":
                        result_status, diagnosis = "NUMERICAL_FAILURE", "Candidate failed the finite-number checks"
                except (ValueError, RuntimeError) as error:
                    if any(text in str(error) for text in NUMERICAL_ERRORS):
                        result_status = "NUMERICAL_FAILURE"
                        diagnosis = next(text for text in NUMERICAL_ERRORS if text in str(error))
                        self.close()  # Failed canonical workers are recreated for the next candidate.
                    else:
                        receipt.update(status="INFRASTRUCTURE_FAILURE", error_type=type(error).__name__, error=str(error), completed_unix=time.time())
                        dump(target, receipt)
                        state.update(status="INFRASTRUCTURE_FAILURE")
                        dump(self.output / "state.json", state)
                        raise InfrastructureFailure("Candidate infrastructure failure; see trusted execution receipt") from error
            accepted = False
            if result_status == "COMPLETE":
                metric = record["best"]["development"]
                best = state["incumbent"]["best"]["development"]
                accepted = (metric["primary"], -metric["loss"]) > (best["primary"], -best["loss"])
                if accepted:
                    state["incumbent"] = record
            reply = {"slot": slot, "design_id": design_id if isinstance(design_id, str) else None,
                     "status": result_status, "accepted": accepted, "diagnosis": diagnosis,
                     "candidate": _evidence(record)["development"] if result_status == "COMPLETE" else None,
                     "candidate_evidence": _evidence(record) if result_status == "COMPLETE" else None,
                     "incumbent": _evidence(state["incumbent"]), "remaining_slots": SLOTS - slot, "test_read": False}
            receipt.update(status=result_status, reply=reply, completed_unix=time.time())
            if record is not None:
                receipt["fit"] = record
            dump(target, receipt)
            state["requests"].append({"path": str(target), "sha256": sha(target), "slot": slot})
            state["status"] = "READY"
            dump(self.output / "state.json", state)
            return reply

    request = evaluate

    def evaluate_design(self, design_id, hypothesis, experiment, expected_effect, **kwargs):
        return self.evaluate(dict(design_id=design_id, hypothesis=hypothesis, experiment=experiment,
                                  expected_effect=expected_effect), **kwargs)

    def seal_selection(self):
        with self._lock():
            state = self._state()
            if state["used_slots"] != SLOTS or len(state["requests"]) != SLOTS or state["status"] not in ("READY", "DEVELOPMENT_SEALED"):
                raise ValueError("Exactly six completed/charged requests are required before selection can be sealed")
            definition = read(self.output / "definition.json")
            self._verify(definition, data=True)
            _verify_files({entry["path"]: entry["sha256"] for entry in state["requests"]})
            record = state["incumbent"]
            checkpoint = Path(record["checkpoint"])
            execution = read(checkpoint.parent / "execution_receipt.json")
            if sha(checkpoint) != execution["checkpoint_sha256"] or sha(checkpoint.parent / "fit.json") != execution["fit_sha256"]:
                raise ValueError("Selected checkpoint or fitting metadata changed after execution")
            selected = {"task": self.config.task, "seed": self.config.seed, "harness": self.config.harness,
                        "selected_on": "development_primary_then_lower_loss", "record": record, "test_read": False}
            selection_path, seal_path = self.output / "selected_development.json", self.output / "selection_seal.json"
            if seal_path.exists():
                seal = read(seal_path)
                if sha(selection_path) != seal["selection_sha256"] or sha(checkpoint) != seal["checkpoint_sha256"]:
                    raise ValueError("Sealed selection/checkpoint changed")
                return {**self._public_status(state), "seal_sha256": sha(seal_path)}
            if read(checkpoint.parent / "fit.json") != {k: v for k, v in record.items() if k != "checkpoint"}:
                raise ValueError("Selected fitting metadata changed")
            trace = _trace_receipt(self.config.native_trace_path, required=True)
            dump(selection_path, selected)
            seal = {"schema": "public-harness-development-selection-seal-v1", "task": self.config.task,
                    "seed": self.config.seed, "harness": self.config.harness, "role": ROLE,
                    "definition_sha256": sha(self.output / "definition.json"), "selection_sha256": sha(selection_path),
                    "checkpoint": str(checkpoint), "checkpoint_sha256": sha(checkpoint), "fit_sha256": sha(checkpoint.parent / "fit.json"),
                    "request_receipts": state["requests"], "native_trace": trace, "sealed_unix": time.time(),
                    "test_read": False, "feedback_to_controller": False, "heldout_evaluation_performed": False,
                    "execution_kind": definition["execution_kind"]}
            dump(seal_path, seal)
            state["status"] = "DEVELOPMENT_SEALED"
            dump(self.output / "state.json", state)
            return {**self._public_status(state), "seal_sha256": sha(seal_path)}

    def close(self):
        if self._fitter is not None and hasattr(self._fitter, "close"):
            self._fitter.close()
        if not self._injected:
            self._fitter = None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Trusted BrokerConfig JSON file, not controller-generated code")
    parser.add_argument("command", choices=("init", "evaluate", "status", "seal"))
    parser.add_argument("--request", help="JSON request file; stdin when omitted for evaluate")
    parser.add_argument("--model-receipts", help="Optional JSON list of model/token usage receipts")
    args = parser.parse_args()
    broker = Broker(BrokerConfig(**read(args.config)))
    try:
        if args.command == "init":
            value = broker.initialize()
        elif args.command == "evaluate":
            request = read(args.request) if args.request else json.load(sys.stdin)
            value = broker.evaluate(request, model_receipts=read(args.model_receipts) if args.model_receipts else None)
        elif args.command == "seal":
            value = broker.seal_selection()
        else:
            value = broker.status()
        print(json.dumps(value, allow_nan=False))
    finally:
        broker.close()


if __name__ == "__main__":
    main()
