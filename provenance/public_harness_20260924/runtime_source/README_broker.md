# Shared public-harness execution broker

Implementation groundwork only. No public baseline result is implied by these
files or their synthetic unit tests. Native AI-Scientist-v2/AI-Researcher control
flow must actually execute and retain its own traces before any method can be
reported as evaluated.

`broker.py` exposes `Broker`, `BrokerConfig`, `BudgetExhausted`, `DESIGNS`, and
`TASK_DESCRIPTIONS`. Import is CPU/GPU-free. The production fitter is lazy and
uses `common.VariableFederation` and unchanged `core_v3`; `runtime_worker.py`
only ensures task adapters register in spawned workers. No ablation proposer
is imported, and no controller-generated Python is evaluated by this broker.

Protocol: ten original clients, seeds 42/43/44, original twelve-design V3 menu,
100 rounds per fit, D00 reference plus six proposal slots. Pilot seed is 42.
Malformed, duplicate, and numerically failed requests consume slots. A syntax
repair must happen in the native controller before submission if it is meant
to be part of the same slot. Infrastructure failures abort; they are not
scientific negative evidence. Every valid novel candidate is freshly fitted;
no old checkpoint/cache supplies a pilot outcome.

## Python interface

```python
broker = Broker(BrokerConfig(**trusted_configuration))
baseline = broker.initialize()
reply = broker.evaluate_design(
    "D01", hypothesis="...", experiment="...", expected_effect="...",
    native_trace_path="/isolated/native/trace.jsonl",
    model_receipts=[{"model": "...", "input_tokens": 123, "output_tokens": 45}],
)
# Or broker.evaluate({...}) / broker.request({...}) with exactly the four fields.
status = broker.status()
# After six charged requests and after final native trace writes:
sealed = broker.seal_selection()
broker.close()
```

Responses contain aggregate development evidence, first/last development
trajectory diagnostics, acceptance and remaining budget. `candidate` is the
development metric dictionary; `candidate_evidence` and `incumbent` additionally
contain configuration and best round. They do not expose checkpoints, raw rows,
predictions, held-out files, or held-out scores. Higher primary wins, with lower
loss breaking ties; a strict complete tie keeps the incumbent. The native
controller cannot choose a different final checkpoint through this interface.

`BrokerConfig` fields: `task`, `seed`, `harness`, `output_dir`, `upstream_repo`,
`upstream_commit` (full current HEAD), `native_trace_path`; optional `gpu_ids`
(logical CUDA IDs), `adapter_paths` (all adapter/transport source files to bind).
Configuration is trusted operator input, not native generated text.

## CLI

```
python broker.py --config trusted_config.json init
python broker.py --config trusted_config.json evaluate --request candidate.json --model-receipts usage.json
python broker.py --config trusted_config.json status
python broker.py --config trusted_config.json seal
```

`init` executes D00; `evaluate` executes a valid novel candidate. Do not run them
until the native controllers and provenance configuration have been reviewed.
The JSON config cannot alter slots, rounds, clients, menu, or data roots.

Production bindings cover source files, pinned upstream tracked worktree,
adapter files, package/interpreter metadata, exact task manifest and train/dev
artifacts. Corrected cells use exactly
`results/unified_bio_20260918/corrected_features/<task>/data`; PTPC and native
TAPB use their registered task data directories. TAPB public feature hashes are
bound in the manifest and checked by the existing feature loader when used.

Fit/request records and `state.json` are trusted-private artifacts. Mount only
the native controller workspace and expose the broker through a narrow API or
subprocess bridge. This code is an execution boundary, **not** an OS sandbox:
do not give a code-writing native controller unrestricted repository access.

`selected_development.json` and `selection_seal.json` freeze the development-best
fit only. They are **not** held-out evaluation results and do not satisfy the
main publisher's audit/verification contract by themselves. A separate trusted
post-selection evaluator and independent rescoring are still required. Keep all
historical endpoints labeled retrospective held-out, never blind confirmation.

CPU-only tests:

```
python -B -m unittest discover -s extensions/public_harness_20260924 -p test_broker.py -v
```
