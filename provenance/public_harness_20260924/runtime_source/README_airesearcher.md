# AI-Researcher fixed-task adapter

Label: **AI-Researcher (task-adapted experimental controller)**, not unmodified
upstream. Official checkout: `HKUDS/AI-Researcher`, commit
`f9a6f8480860c193afff600eeffe3defcee8a978`; tracked source remains unchanged.
`setup.cfg` declares MIT; this commit contains no tracked LICENSE/COPYING file.

## Preserved mechanisms

- Actual `MetaChain.get_chat_completion_async`, `run_async`, tool dispatch and
  agent handoffs; actual `AgentModule` state/cache behavior.
- Source-defined `InnoFlow.forward`: five idea drafts and selection, implementation
  survey, native dataset/training/testing planning, implementation, judge/code
  reviewer handoff, submission, experiment analysis and refinement.
- Native planning state setters, completion tools and experiment-report updates.
  Stage awaits/arguments, loops, branches and context stores are AST-checked.

## Explicit source/runtime transformations

- Load hash-verified factory/controller definitions without eager browser/Docker
  package imports. Exclude literature collection, downloads and paper writing.
- Replace domain prompts and resource tools with fixed-task descriptions,
  `read_task_artifact()` and the trusted `evaluate_design(...)` broker. No shell,
  file-path tool, generated-Python execution or held-out feedback is available.
- Preserve distinct messages but correct the native alias bug:
  `messages.extend([] if survey_messages is messages else survey_messages)`.
  `AgentModule` returns its input list; this avoids exponential self-duplication
  without truncating context, dropping unique messages or changing idea stages.
- Set `EXP_ITER_TIMES` from two to five; use `MAX_ITER_TIMES=0`. The nominal source
  sequence has implementation plus five refinement stages, but the budget is
  **six proposal slots globally**, never one slot per native stage. Native tools
  may make multiple attempts within a stage. All invalid/duplicate requests are
  charged. Exhaustion stops further model/evaluator calls and seals the best
  valid incumbent, including D00 if every proposal is invalid. Unreached native
  stages are not fabricated. Submission reports existing evidence without a fit.
- Original async completion entry point uses the shared text backend through a
  single-call JSON text codec (an explicit transport adaptation, not an unchanged
  native tool-calling API). Native **AUTO stages retain ordinary plain-text final
  answers unchanged**, including arbitrary JSON, arrays or fenced no-tool
  content; braces alone never claim a tool call. No envelope or repair is
  required for those answers.
  REQUIRED stages and claimed tool calls need one complete tool object (or an
  explicitly permitted final object). Malformed JSON/envelopes, unavailable tool
  names or non-object `arguments` receive at most **three total attempts**, including the
  initial response, from the same backend. Every raw receipt counts toward the
  global cap. No fragment extraction, argument filling, design or metric fallback.
- Equivalent explicit single-call forms are normalized: `tool`/`arguments`,
  `name`/`arguments`, a `function` wrapper containing `name`/`arguments` (optional
  string `id` and `type:"function"` metadata), or exactly one top-level key equal
  to a currently exposed tool name whose value is the argument object. Complete
  whole-response JSON fences and `<tool_call>...</tool_call>` wrappers are accepted.
  Standard name/function forms may encode the argument object as a JSON string,
  decoded exactly once. Canonical/keyed arguments remain object-only. All raw
  responses and `normalization_shape` metadata are retained. No action, name or
  data-bearing argument is inferred; prose, duplicate keys, multiple calls,
  ambiguous mixed forms and unknown explicit calls are rejected. Under AUTO,
  bare unrelated JSON remains ordinary content; only an exposed key denotes a
  shorthand tool call. Native invocation still handles argument values/bindings.
- Argument validation follows the original `MetaChain.handle_tool_calls`:
  `json.loads` followed by native `func(**args)`, not adapter JSON-schema checks.
  Missing/extra arguments and all JSON values, including `null`, pass unchanged
  to native dispatch. Owned context injection and genuine native invocation errors
  remain intact. Model-facing schemas are documentation; the broker still
  validates and charges design requests. No per-field nullable patches are used.
- An explicitly selected zero-arity tool may omit its empty `arguments` object
  only when the live schema has zero properties and zero required parameters.
  The transport records canonicalization to `{}`; it never fills an argument
  value, supplies native context, or relaxes a data-bearing tool's parameters.
- Planning schema descriptions request short natural-language references to the
  unchanged pipeline, never Python or invented paths. Native plan functions,
  signatures and state updates remain unchanged; their actual recorded/missing
  state is visible. `case_resolved` still checks native plan state itself.
- Correct four transport-only text schemas: unannotated `task_response`,
  `failure_reason`, `atomic_idea`, and `task_report` are incorrectly exposed as
  empty objects by native `inspect._empty` introspection. Their native documented
  report/handoff usage is textual. Python signatures/functions stay unchanged;
  exact before/after schema metadata is retained in the native trace.
- Reject native failed completion-tool receipts when the stage history cap is
  exhausted; a tool named `case_resolved` is not sufficient evidence of success.

Each run writes `provenance.json` with original and transformed source hashes,
full transformed definitions, edit locations and controller-structure checks.
`native_trace.jsonl` is frozen before the development selection seal.

## Fixed protocol and dependencies

Ten original clients; D00 reference plus six slots from the twelve-design V3 menu;
100 rounds per fresh fit; seeds 42/43/44. Model: shared local Qwen2.5-7B-Instruct,
temperature 0.7, top-p 0.9, 512 output tokens/call, 28,000 input tokens/call.
Limits: 160 model calls/run and 48 added native history messages/stage (the latter
is not a count of model calls). Exceeding limits fails clearly; no silent truncation.

Use the sibling `.venv`. Lightweight imports: `litellm==1.55.0`, OpenAI SDK,
inquirer, python-dotenv, tenacity, rich, pydantic, tiktoken, torch, Flask, httpx,
prompt-toolkit. No browser, Docker, docling or document-conversion installation
is needed. Upstream metadata states Python >=3.11; this source adaptation's
recorded smoke-test interpreter is Python 3.10.20.

## Validation and invocation

```sh
extensions/public_harness_20260924/.venv/bin/python -B \
  extensions/public_harness_20260924/airesearcher_adapter.py --self-test --broker-integration
```

CPU-only fake transport/fitter tests enter 21 native stages, use 31 completions,
six proposals plus D00, plan/analysis state, judge handoffs, alias correction,
and the actual broker's immutable trace/selection seal. These are integration
tests, **not** biological results or proof of live-model completion. Real runs
must independently complete `run_baseline.py`, post-selection held-out scoring,
and verification; only those artifacts support a reported benchmark cell.

Twenty-two additional CPU transport/budget regressions cover concatenated/prose/truncated
JSON, `auto` policy mistaken for a tool, unchanged argument-object dispatch, bounded
repair receipts/caps, unchanged planning functions, failed native completion,
the full Judge `suggestion:null` call through the actual native runner and real
native invocation errors for missing/extra arguments,
equivalent single-call codec forms and their shape receipts, strict one-time
argument-string decoding, ambiguous/unknown/multiple-call rejection, whole-response
wrappers and actual native Experiment Analysis dispatch of a keyed `case_resolved`,
unmodified AUTO plain-text completion semantics, multiple invalid/duplicate
attempts within a native stage, all-invalid D00 retention, no seventh evaluator
call, and natural native return at six slots.
Run them with `python -B -m unittest discover -s extensions/public_harness_20260924
-p test_airesearcher_transport.py -v` in the same environment.

`smoke_airesearcher_text.py` supports an explicitly marked real-Qwen/native-flow
check with an **injected fake fitter** in a fresh engineering-only directory.
It records model usage and wall time and is never publishable biological evidence.
The first real-Qwen/fake-fitter check (engineering transport v3) failed during
ideation because an over-strict AUTO envelope rejected legal native text; it is
retained as failed engineering evidence, not a baseline result. The AUTO
compatibility correction above addresses that failure without selecting actions.
Engineering transport v4 also failed before proposals because JSON-shaped AUTO
content (`{"design_id":"D07"}`) was misclassified as a tool claim; this case is
now explicitly covered alongside arrays and fenced ordinary content.
Engineering transport v5 completed all ideation/survey stages and recorded all
three native plans, but rejected an unambiguous zero-arity completion lacking an
empty argument object. The narrowly logged canonicalization above covers it.
Engineering transport v6 reached implementation, judge and refinement. It made
one valid fake-fit proposal and three invalid proposals, then hit the adapter's
incorrect per-stage one-slot assertion. That assertion is now removed: these
invalid proposals are ordinary charged negative results under the global budget,
not infrastructure failures. No further model-policy changes were made.

The preserved v3–v6 engineering probes total 65 real model calls, 595,692 input
tokens, 3,402 output tokens and 0.149370 reserved model-GPU-hours. Every probe used
an injected fake fitter; none is a biological score or a completed formal baseline.

The preserved formal-v3 PTPC attempt stopped after two charged proposals when
adapter-side type validation rejected Judge's legal native `suggestion:null`
call. The general native-dispatch compatibility correction above removes that
extra validation, without modifying any native function or search decision.
Its validation is CPU-only; no additional real-model probe was run for this fix.

The preserved formal-v4 PTPC attempt passed Judge and submission but stopped in
Experiment Analysis after returning prose plus a keyed `case_resolved`, then two
complete keyed calls. The old codec did not accept that explicit single-tool
serialization. The general codec above now covers equivalent forms without
changing the chosen tool, arguments, native control flow or search policy.
That attempt remains incomplete; the codec correction has CPU-only validation,
not a rerun or a completed biological result.

Launcher API: `run_airesearcher(broker, text_backend, *, trace_dir,
registered_designs, task_description, task_name, seed, upstream_repo)`.
