# Public-harness queue supervisor

`supervise.py` runs the same 30 registered jobs in seed → task → harness order.
Seeds are 42/43/44; the four smaller tasks precede native DTI. There are no
automatic development retries or manuscript edits/pushes.

By default, any failed controller stops the queue. A new queue may explicitly
set `--continue-controller-failures`; this boolean is frozen in its manifest and
must match on every resume (including detached launches). It permits only
`ai_researcher` runs with status `FAILED`, error type `NativeRunIncomplete`, and
an error beginning with one of these exact prefixes, optionally preceded by one
native `Error: ` wrapper:

- `Tool response remained invalid after`
- `Native required-tool stage ended`
- `Native stage exhausted with a failed completion/tool receipt`

Run identity and `fresh-canonical-v3` production identity are checked first.
New child failures qualify only after a positive exit, owned-descendant cleanup,
final accounting, and another frozen-source check. Existing failures must bind
to adopted or previously charged work; failure receipts retain status/definition
hashes and are revalidated on resume. Other model/controller errors, training or
infrastructure errors, source/integrity changes, signals and budget limits still
stop the queue. Failed runs with held-out access/artifacts are never skipped.

Each qualifying failure is retained in `supervisor_status.json` under `failed`
with its job, error, output directory and accounting evidence. It triggers no
held-out evaluation, verification, publishing, automatic retry or fallback D00
score. Independent later jobs continue, and pending/unscorable table cells
remain N/A. A queue containing any such failures ends with
`FINISHED_WITH_INCOMPLETE_RUNS`, never `COMPLETE`. This is a scheduling policy,
not a change to either baseline's experiment-selection policy or compute cap.

At first creation, completed production runs already under `--base` are adopted
from their status times, model usage and production definition. Each is charged
`8 × (completed_unix - started_unix) / 3600` reserved GPU-hours exactly once.
The manifest freezes these receipts and hashes. Active/unfinished runs, missing
receipts, or synthetic execution prevent queue creation; no prequeue PID is
signaled. Even a completed status must wait for its launcher cleanup to exit.

`--prior-reserved-gpu-hours` adds an explicit earlier engineering allocation
(default zero). Use the same value on resume. Both this allocation and adopted
runs count **inside** `--max-gpu-hours`, not in addition to it. For example,
`--max-gpu-hours 180 --prior-reserved-gpu-hours 1.0` reserves one hour of the 180
for earlier engineering work, before charging adopted runs. The wall deadline
starts at queue creation and is immutable on resume.

Before launching each child, persist a random inherited ownership nonce and
launch intent. Cleanup checks the nonce, boot ID and current process groups,
including detached descendants after the original leader exits. It never kills
an arbitrary saved PID. Restart charges uncertain crash gaps conservatively;
finding live owned orphans cleans them and stops for investigation. Legacy
unfinished records without ownership fail closed. Lost accounting never resets
to zero, and ownership/accounting recovery precedes source-drift validation.

Every verified run triggers the pinned publisher as an owned CPU-only child:
`paper/tools/publish_public_harness.py --base SAME_BASE --output-dir
paper/tables/public_harness_preview`. Publisher failure stops the queue before
marking the run complete. It does not replace manuscript tables.

CPU-only tests create and clean up only their own process fixtures:

```sh
extensions/public_harness_20260924/.venv/bin/python -B -W error::ResourceWarning \
  -m unittest discover -s extensions/public_harness_20260924 -p test_supervise.py -v
```

The tests cover descendant cleanup, crash recovery, ownership refusal,
accounting preservation, prequeue adoption, inclusive caps, fixed ordering, and
preview success/failure, plus the opt-in failure allowlist, immutable resume
policy, unchanged accounting, no retries/held-out fallback, and stop-on-infra
behavior. These tests do not perform biological training.
