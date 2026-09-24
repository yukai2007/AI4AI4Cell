# Public-harness held-out evaluation

This evaluator is separate from native controllers and must run only after a
real broker run has completed six requests and sealed its development-best
selection. Test-fit injection, replay, incomplete slots, changed upstream code,
changed traces/checkpoints, and infrastructure-failed runs are rejected. Unit
tests are synthetic formula/gate tests and are not benchmark evidence.

`heldout_public.py` supports all five registered task versions. It copies only
the endpoint paths/hashes from the corresponding already-verified original
main-table seal (same seed); it does not copy scores. New predictions come from
the new native-controller-selected checkpoint. It preserves original TAPB
random/unseen-drug/unseen-protein rosters, PTPC's 148 conditions, and corrected
cell five-choice query rosters. The label remains **retrospective held-out**, not
blind confirmation.

## Invocation after a real completed native run

```
/opt/conda/envs/LDA/bin/python -B extensions/public_harness_20260924/heldout_public.py \
  --run-dir /absolute/path/to/broker_run --output /absolute/path/to/heldout_output \
  --device cpu --seal-only

/opt/conda/envs/LDA/bin/python -B extensions/public_harness_20260924/heldout_public.py \
  --run-dir /absolute/path/to/broker_run --output /absolute/path/to/heldout_output \
  --device cpu

/opt/conda/envs/LDA/bin/python -B extensions/public_harness_20260924/verify_public.py \
  /absolute/path/to/heldout_output
```

Use the **same device value** for seal-only and evaluation. CPU is sufficient
for PTPC/cell heads; a chosen CUDA device is also supported. TAPB must use the
`worker_python` interpreter declared in its data manifest (currently
`extensions/tapb_reference_20260913/.venv/bin/python`) and an appropriate device
for frozen ESM feature extraction. Never provide evaluation output to a
controller and never place it inside the sealed native trace directory.

`--seal-only` does not import torch or open/hash held-out response content.
Actual evaluation first persists `seal.json`, then checks response hashes and
decodes responses. Original model/prediction/scoring code is reused unchanged.
`verify_public.py` independently reopens saved predictions, checks exact source
row identities and uses tied-rank AUROC/AP and binary formulas without sklearn,
or stable five-option ranks and independent log-sum-exp for cell cross-entropy.

## Publication schema

- `seal.json`: `public-harness-heldout-seal-v1`; task/seed/harness, ten clients,
  100 rounds/six slots, selected checkpoint/hash, development/evaluation sealing
  timestamps, source/metadata hashes, reference seal and all endpoint hash pins.
- `results.json`: `public-harness-heldout-results-v1`; `execution_kind` must be
  `fresh-canonical-v3`; `role`, `feedback_to_controller=false`, `primary`,
  `primary_metric`, `primary_endpoint`, `metrics`, and `endpoints` map.
- Each endpoint contains `primary`, `metrics`, `rows`, `predictions`, and
  `predictions_sha256`. TAPB keys are `random`, `unseen_drug`, `unseen_protein`;
  all other tasks use `primary`.
- TAPB CSV predictions retain original row index, SMILES, Protein, Y and
  probability. PTPC NPZ retains original row index, condition/compound IDs,
  labels and probabilities. Cell JSON retains original row index, intervention,
  original ordered five choices, all scores and rank.
- `audit.json`: required `PASS` original-scorer/roster/selection-isolation checks.
- `verification.json`: `public-harness-heldout-verification-v1`, `status=PASS`,
  result/audit/seal hashes, independent `rescored` endpoint metrics and maximum
  error (tolerance 1e-12).

A later paper collector should require all those artifacts, verify their hashes
and identity, and include only complete seeds 42/43/44 for a formal row. A seed42
pilot is not a three-seed main-table result. Keep the original six factorial
arms and their publisher unchanged; do not insert fabricated old-arm records.

CPU-only validation:

```
python -B -m unittest discover -s extensions/public_harness_20260924 -p test_heldout_public.py -v
```
