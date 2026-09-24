# AI-Scientist-v2 (task-adapted experimental controller)

This adapter imports SakanaAI/AI-Scientist-v2 at commit
`96bd51617cfdbb494a9fc283af00fe090edfae48`. It is **not** an end-to-end paper-generation
reproduction and is not a hand-written imitation of its tree policy.

## Native mechanisms retained

The actual `AgentManager.run`, stage creation/completion methods,
`ParallelAgent.step`, `_select_parallel_nodes`, tuning/ablation idea generation,
`MinimalAgent` draft/debug/improve/tuning/ablation generation and plan/code parsing,
native execution-result review, `Journal.get_best_node` (LLM selection with native
fallback), memory summaries, and `Node` parent/child serialization are invoked.
`native_trace.jsonl` records fixed commit, imported function/module SHA-256 hashes,
exact function line locators, requests/replies, node relationships, broker outcomes,
stage history and termination. `native_stdout.log` captures upstream diagnostics.
The tests profile actual upstream Python frames to establish these calls occur.

## Explicit task adaptations

- The broker exposes the same registered 12-design menu and trusted 100-round
  fitter used by the shared comparison. The baseline is public task context;
  candidate designs must pass the broker's availability checks.
- Generated Python is **never executed**. Exactly one assignment named `design`
  with four literal string fields (`design_id`, `hypothesis`, `experiment`,
  `expected_effect`) is parsed structurally. Calls/imports/extra statements are
  rejected, consume a candidate slot, and never reach training. Native code-block
  extraction and generation retries remain active before this boundary.
- The executor implements upstream `submit`/`Future.result` synchronously, with
  one worker so the global six-slot budget cannot overshoot. Native `num_drafts=3`,
  debug probability/depth, stage limits and search policy are unchanged.
- Task goals and incompatible instruction **fields** are adapted to the fixed
  design task at the native query boundary. The original `MinimalAgent` and its
  prompt-building methods run unchanged. For every query, `prompt_transformation`
  events record original/effective hashes and each field's exact before/after
  text, rule name and adapter version (`literal-design-fields-v2`). Only execution
  requirements for full scripts, GPU code, synthetic data, saved NumPy data or
  plotting are replaced with the literal-request contract. Coding responses use
  2–4 concise planning sentences plus the four-field request. Native idea-format
  keywords, candidate code/history, measured evidence and memory are preserved.
- Tuning/ablation idea prompts retain native formats but cannot ask for extra
  epochs or new datasets. Stage-completion methods remain native; their prompt
  criteria map unavailable plots/multiple datasets to actual finite development
  evidence from the fixed 100-round, 10-client task. The LLM still decides stage
  completion; no verdict or evidence is fabricated. The six-slot run may end
  within a native stage. No four-stage
  completion is fabricated and an early native stop is an error, not auto-filled.
- The fixed-baseline prompt includes only fixed config, development metrics,
  best round and training diagnostics. Availability and remaining budget appear
  only in the current broker state, never an obsolete initialization snapshot.
- Scores are taken only from broker development evidence; native LLM review may
  flag an otherwise executable candidate as buggy but cannot change its score.
  Final selection follows the shared **development-best checkpoint** rule, not
  the native LLM's preferred node. Test evidence is not available to the controller.
- Plot-generation/VLM feedback are removed. `is_buggy_plots=False` explicitly
  means this modality is disabled/not applicable, not that a VLM approved plots.
- Native extra multi-seed evaluations use `num_seeds=0`; formal task seed
  repetitions are scheduled externally. No literature or manuscript phase runs.
- Native pickle checkpoint output is replaced by transparent JSON trace snapshots.
- Native query call sites use the shared `text_backend(messages, purpose=...)`
  callable. It returns a receipt containing `raw_response`, token counts, latency,
  seed/model/call ID. Native FunctionSpecs become validated JSON-output requests
  for this text backend. All model calls, not only proposal calls, are recorded.
- Each native FunctionSpec query has at most **three total formatting attempts**
  (initial request plus two retries) using the same text backend. A retry retains
  the original context, actual failed response and schema/parse error, and asks
  for formatting correction only. Trace events identify native query ID, attempt,
  limit, error, and all raw receipts. Formatting retries do not rerun training or
  consume extra candidate slots, but all their model cost is counted. Exhaustion
  raises an error; no review/selection/completion verdict is invented. Native
  callers' existing error handling (including selection fallback) remains native.

These are material scope restrictions and must accompany any reported baseline
label/result. Especially, task adaptation removes unconstrained code development,
visual reasoning, multi-dataset exploration and internal seed repetition.

## API

```python
from aiscientist_adapter import run_aiscientist

result = run_aiscientist(
    broker, text_backend,
    trace_dir=output_dir / "native_controller",
    registered_designs=DESIGNS,
    task_description=TASK_DESCRIPTIONS[task],
    task_name=task,
    seed=seed,
)
```

The broker must be fresh (`used_slots=0`, `remaining_slots=6`) and implement
`initialize`, `status`, `evaluate_design`, and `seal_selection`. Its candidate
results supply a development `primary` scalar. It alone owns fitting, invalid or
duplicate proposal accounting, and checkpoint sealing. Existing native traces
are not overwritten. In-process concurrent runs are prohibited because upstream
uses module-bound imports; separate experiment processes are safe.

## Native import dependencies and tests

Python 3.10+ syntax is sufficient for these imports (upstream recommends 3.11).
Required import distributions: `numpy pandas anthropic openai backoff funcy rich
humanize dataclasses-json omegaconf coolname shutup python-igraph black genson
jsonschema`. Several are incidental upstream imports even with code execution
disabled. Full upstream training/writeup requirements are not needed here.

```sh
cd extensions/public_harness_20260924
.venv/bin/python -m unittest -v test_aiscientist_adapter.py
```

The native-controller smoke uses the **real imported upstream controller** with
a fake text backend and fake broker, performs no training or LLM requests, and is
not scientific benchmark evidence. It is skipped, never replaced with a fake
controller, when upstream/import dependencies are missing.

## License and disclosure

The pinned upstream is under **The AI Scientist Source Code License v1.0,
December 2025**, not MIT. Retain the complete upstream license when distributing
its source or derivative works. Its scientific-manuscript clause requires
prominent disclosure that AI Scientist was used. Cite the AI-Scientist-v2 paper
and explain the task adaptations above. No upstream source is modified here.
