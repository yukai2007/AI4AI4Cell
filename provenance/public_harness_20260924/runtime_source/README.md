# Public harnesses on the BioCoLoop main-table tasks

This extension connects pinned native AI-Scientist-v2 and AI-Researcher research
controllers to the existing biological fitting/scoring interface. The original
training source, task registrations, held-out rosters and six-arm factorial
comparison are unchanged. It is an explicitly **task-adapted** comparison.

## Runtime pieces

- `aiscientist_adapter.py` / `airesearcher_adapter.py`: native controller flow
  with recorded domain/transport adaptations; no generated Python is executed.
- `qwen_backend.py`: local Qwen2.5-7B-Instruct generation, complete call receipts.
- `broker.py` / `runtime_worker.py`: fresh D00, a six-proposal maximum,
  twelve registered designs, ten clients, 100 rounds per valid new design.
- `run_baseline.py`: one controller/task/seed run; development only.
- `heldout_public.py` / `verify_public.py`: separate frozen-checkpoint evaluation
  and independent rescoring from saved predictions.
- `supervise.py`: bounded queue, owned-process cleanup, failure reporting and
  progress-table refresh. It does not modify or push the submission manuscript.

The shared native model backend uses the same sampling settings and 512-token
per-call limit as the original main-table controller. Native workflows make
different numbers of calls; these inference costs are reported separately.
Matched budgets here refer to a common proposal cap and identical candidate
fits. A native controller may stop early; `budget_cap_protocol_v4.py` seals and
audits the requests it actually made without imputing an additional candidate.

The final AI-Researcher path is `airesearcher_budget_cap_v4.py`, with
`heldout_public_budget_cap_v4.py` and `verify_public_budget_cap_v4.py` retaining
the original task scorers while validating one through six immutable proposal
receipts. `prioritize_seed42_dti_v3.py` reserves the seven fitting GPUs for the
final DTI run only after the active AI-Scientist DTI score is sealed.

## Environment

Use the dedicated `.venv` based on the existing LDA environment, with adapter
packages pinned in `requirements-adapters.txt`. Native TAPB workers/evaluation
use the interpreter already registered in that task's data manifest. Do not
replace the original environments or install these packages globally.

The two upstream repositories are checked out at the commits in
`run_baseline.py:PINS`. Detailed controller mappings are documented in
`README_aiscientist.md` and `README_airesearcher.md`; scoring in
`README_heldout.md`. Upstream checkouts remain clean. Source, task artifacts,
configuration, model calls, proposals, checkpoints and predictions are linked
through per-run receipts.

## Commands (from project root)

One fresh development run:

```sh
extensions/public_harness_20260924/.venv/bin/python -B \
  extensions/public_harness_20260924/run_baseline.py \
  --harness ai_scientist_v2 --task ptpc_neural --seed 42 \
  --gpus 1,2,3,4,5,6,7 --model-device cuda:0 --output /absolute/new/run
```

Bounded full comparison, using a new output directory:

```sh
extensions/public_harness_20260924/.venv/bin/python -B \
  extensions/public_harness_20260924/supervise.py \
  --base /absolute/new/matrix --max-gpu-hours 180 --max-wall-hours 24 --detach
```

The 30-job queue covers two controllers, five task endpoints and seeds 42–44.
It prioritizes the complete seed-42 sweep before additional repetitions. GPU
accounting conservatively charges reserved devices times child wall time; it
is not a measurement of actual GPU arithmetic utilization. Failed runs are
preserved for investigation, not automatically retried or converted to scores.

Inspect `supervisor_status.json`, then the current run's `run_status.json`,
`development/state.json`, `model_calls/usage.json` and native trace. An old
heartbeat alone does not establish that its recorded process is still alive.

Tests use explicitly marked synthetic fitters; they do not count as experiments:

```sh
extensions/public_harness_20260924/.venv/bin/python -B -m unittest discover \
  -s extensions/public_harness_20260924 -p 'test_*.py' -v
/opt/conda/envs/LDA/bin/python -B -m unittest discover \
  -s paper/tools -p 'test_public_harness_publication.py' -v
```

The separate paper publisher writes
`paper/tables/public_harness_preview/main_public_harness.tex`. A cell has a
three-seed mean and SD only after all three runs independently pass verification;
otherwise it remains N/A. Single-seed values remain visible in the JSON
snapshot. `main_public_harness_seed42.tex` provides a second view in which
every method, including the original references, uses seed 42 alone. This
supports the main-table-first workflow without mixing a new single run with
older three-seed means. Main-table integration is a separate authoring step
after reviewing the completed comparison.

## Engineering pilots

`pilot_v1` exposed a native structured-review formatting mismatch; `formal_v1`
was withdrawn before held-out evaluation when native file-generation prompts
conflicted with the task interface. Their traces, valid training records and
costs are retained. `formal_v2` was withdrawn before scoring while adapting
AI-Researcher's native planning/tool transport. Real-model, fake-fitter checks
are stored separately as `engineering_transport_airesearcher_v*`; these never
supply biological scores. None of these directories supplies publication
scores. Four successful AI-Scientist-v2 seed-42 studies remain sealed in
`formal_v3`; incomplete AI-Researcher runs exposed an adapter-only argument
schema check and a text-codec format mismatch. The final queue, `formal_v5`,
references the four successful studies without rewriting or retraining them
and starts AI-Researcher afresh with native parameter binding and recorded
single-call syntax normalization. `formal_v5/ADOPTION.md` records evidence
locations and prior compute accounting. The queue's immutable
`--continue-controller-failures` option leaves narrowly identified unscorable
controller failures as N/A while independent jobs continue; it never retries
them or assigns a scientific score.
