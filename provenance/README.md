# Experiment provenance index

Verified from local records on 18 September 2026. This file is a compact,
non-sensitive index for the manuscript repository, **not a complete code,
data, or model release**. It contains no biological measurements, model
weights, credentials, or copied prompts. The underlying artifacts remain in
the companion research workspace and are not included in a paper-only clone.

Completion review on 21 September 2026 added the DTI cluster-bootstrap uncertainty analyses. Current verified seed counts come from the aggregate snapshot.

## Path convention and protocol decision

All paths below are relative to the **parent research workspace
`AI4AI4Cell/`**, which is `../` from this manuscript repository's root.
For example, `results/...` means `../results/...` when working in the paper
repository, not a file bundled in this Git repository. In the tables,
`U` abbreviates `extensions/unified_bio_20260918/`, `R` abbreviates
`results/unified_bio_20260918/`, and `C` abbreviates
`extensions/scdebart_maskfix_20260918/`. Braced seed/task names describe an
artifact layout; they do not assert that every planned run has finished.

The controlling decision is
`docs/model_selection_20260918/MAIN_PROTOCOL_DECISION.md`; implementation
details are in `docs/model_selection_20260918/IMPLEMENTATION_HANDOFF.md`.
The decision chooses task-aligned adaptations independently of their new
held-out scores and binds each task to one reference-model version.

The common V3 protocol uses 100 training rounds, six proposal slots per
direct/loop arm, a local Qwen2.5-7B controller, development-only retention,
and seeds 42/43/44. The clean main comparison is fixed/one lab,
direct optimization/one lab, and collaborative research loop/ten labs. All six
factorial arms are retained to separate participation, total search, and
feedback effects. All three prespecified seeds are complete for the five
main endpoints. Appendix A contains the complete six-arm comparison,
secondary metrics, proposal-prefix analysis and uncertainty.

### Compute-matched loop follow-up (22 September 2026)

The final feedback-isolation result uses the versioned V6 racing protocol at
`U/research_v6.py` and `U/run_v6.py`. For PTPC and the three cell strata,
direct and loop receive the same ten-design fractional-factorial slate. Direct
trains each design for 80 rounds. The loop screens each for 20 rounds and
promotes six, by current primary/loss rank and early improvement within each
learning-rate stratum, to fresh 100-round validation. Both arms therefore use
800 full-client rounds, 160 development measurements and ten candidate
hypotheses. Seeds 53/54/55 were executed after the rule was frozen.

Selected checkpoints were sealed and scored by `U/heldout_v6.py`; saved
predictions were independently recomputed by `U/summarize_v6.py`. The aggregate
receipt is `R/v6_loop_summary/summary.json` (SHA-256
`a33102a044f17a3b24b76ca57c19622994951d06ea49b9fc89b5ecb16858a113`).
Across 12 held-out task--seed comparisons, racing yields four wins, eight ties
and no losses. Norman improves by 10.84 Top-1 points on average with
hierarchical paired-bootstrap interval [4.54, 17.73] points. Tahoe improves by
1.99 points on average with one win and two ties; VCC and PTPC tie.

DTI uses a conservative development-only replay over the seven-design
intersection of completed TAPB trajectories. Direct receives 525
candidate-rounds and racing receives 520. The receipt
`R/native_tapb/v6_dti_replay/report.json` (SHA-256
`59a90170ff5b13859f20335c46ca1d9acb7d6844ab652af66c07a1e37db48e88`)
records two wins, one tie, no losses and +0.39 mean AUROC points. No new DTI
held-out claim is inferred from this replay.

An earlier V5 scalar-threshold controller was evaluated on development data
and rejected after it regressed on Tahoe and PTPC. Its results are not used in
the manuscript. V6 replaces that brittle threshold with stratified racing and
uses disjoint later training seeds.

## Task models and official source pins

| Task family | Intended main implementation | Official source and immutable commit |
| --- | --- | --- |
| Drug–target interaction | TAPB adaptation with fresh task weights; frozen public ESM features; one shared dictionary built only from client 0 training proteins | [TAPB](https://github.com/GaomingL1n/TAPB), `ac846b1463ecf4a031b84bd6caacb57b25d50d4f` |
| Proteomic efficacy | `ptpc-observed-6h24h-head-v1`: randomly initialized ProteinTalks-derived head using measured 6h/24h responses and Morgan features; **not** the full ppODE model or an author-pretrained head | [PTV-1 / ProteinTalks](https://github.com/guomics-lab/PTV-1), `1223e9401cc11ca2d2252ad0522fcf9604f0d305` |
| Cell perturbation identification | Mask-corrected scDEBART adaptation on VCC single-gene, Norman double-gene, and Tahoe drug perturbations; original public backbone retained | [scDEBART](https://github.com/Jieun-Sung/scDEBART), `8996c7ca8c336d636de4ba06a4d5d97b2bbe2ce8` |

The TAPB training recipe is the common client-local recipe, not the original
centralized benchmark recipe. The scDEBART version fixes three SDPA mask
call sites established by synthetic tests; weights, response targets,
splits, scoring masks, and option rosters are unchanged. Proteomics source
intake is documented in `references/proteomics/source_manifest.json`;
public supplementary material must not be described as receipt of the
complete restricted ProteinTalks portal package.

## Public assets: identities, not redistributed weights

| Asset | Public revision / local receipt | SHA-256 of weights |
| --- | --- | --- |
| ESM2 `facebook/esm2_t33_650M_UR50D` | Revision `08e4846e537177426273712802403f7ba8261b6c`; `references/performance_first_20260913/model_assets/esm2_t33_650M_UR50D/asset_manifest.json` | `a08adabb949fa67ad3c14b509d04fd60368b35007b0095e3358f81200c4f4db0` |
| Public scDEBART backbone | `data/scdebart_20260918/pretrained.pt`; pinned in corrected feature manifests below | `195962f5774a79922df454013dad5825124616a1c88266074e67d3e09e57935f` |
| Qwen2.5-7B-Instruct, shard 1/4 | Environment receipt below; `model-00001-of-00004.safetensors` | `a1333e6293854747c481288ea83b348226af178dd565c49b6f9495ba1966aba7` |
| Qwen2.5-7B-Instruct, shard 2/4 | `model-00002-of-00004.safetensors` | `f5d25a2772cb825164a2a2c0fb6d51a87e282abf21e4dd75bc5cfb3cd0ea6185` |
| Qwen2.5-7B-Instruct, shard 3/4 | `model-00003-of-00004.safetensors` | `8efdec4c1bc12317ae1a38dc42b595ce777738a64deea3fcb8a0a91381bcdfd5` |
| Qwen2.5-7B-Instruct, shard 4/4 | `model-00004-of-00004.safetensors` | `1a72d403cdf0c1ec3cb7f289f17b394a01e64394c2e9b3c0f94dbce3faf879bd` |

Qwen assets are at `../.cache/modelscope/Qwen2.5-7B-Instruct/` relative to
the parent research workspace; no upstream revision is inferred from a
directory name. The receipt fingerprints the actual local files. TAPB uses
the MoLFormer **tokenizer/config only**, not pretrained MoLFormer weights:
`ibm-research/MoLFormer-XL-both-10pct`, revision
`7b12d946c181a37f6012b9dc3b002275de070314`, documented in
`references/performance_first_20260913/model_assets/tapb_asset_manifest.json`
and `references/performance_first_20260913/model_assets/molformer_tokenizer/asset_manifest.json`.

## Local source, data, and study records

| Component | Existing artifact location |
| --- | --- |
| Shared optimizer, runner, and research controller | `U/core_v3.py`, `U/run_v3.py`, `U/research_v2.py`; exact additional dependencies are bound by each study's `definition.json` |
| TAPB adapter and preparation | `U/tapb_native_adapter.py`, `U/prepare_native_tapb.py`, `U/run_native_tapb.py` |
| TAPB manifest and registration | `R/native_tapb/data/manifest.json`; `R/native_tapb/study_v3_seed42/native_registration.json` binds official files, adapter sources, and worker interpreter |
| Proteomics adapter and preparation | `U/ptpc_neural_adapter.py`, `U/prepare_ptpc_neural.py`, `U/run_ptpc_neural.py`; model/scorer at `extensions/proteomics/ptpc_model.py` and `extensions/proteomics/scoring.py` |
| Proteomics manifest and registration | `R/ptpc_neural/data/manifest.json`; `R/ptpc_neural/study_v3_seed{42,43,44}/neural_registration.json` |
| Corrected cell implementation | `C/architecture.py`, `C/prepare_features.py`, `C/test_masks.py`, `C/run_corrected.py`; diagnosis in `C/DIAGNOSIS.md` |
| Corrected cell feature manifests | `R/corrected_features/{vcc_corrected,norman_double_corrected,tahoe_drug_corrected}/data/manifest.json` bind public weights, original manifests/shards, initial heads, and correction sources |
| Corrected cell study manifests and registration | `R/{vcc_corrected,norman_double_corrected,tahoe_drug_corrected}/data/manifest.json`; each existing `study_v3_seed*/maskfix_registration.json` |

Inside a study directory, `definition.json` records the seed, budgets,
controller, common-source hashes, and data-manifest hash.
`{single,federated}_{direct,loop}_proposal_*.json` retains each attempt's
`prompt`, `raw_response`, generation seed, token counts, and time, plus the
parsed hypothesis/design. Corresponding `*_history.json` files retain
candidate outcomes. `selected_development.json` points to selected
`fits/*/best.pt`; `fit.json` and trajectories preserve training/selection
details and communication accounting. These potentially sensitive local
artifacts are indexed here, **not copied into the manuscript repository**.

## Frozen evaluation and scorer records

| Family | Evaluator and output location |
| --- | --- |
| TAPB | `U/heldout_native_tapb.py`, original scorer `runtime/experiments/drugevolve_transfer/scoring.py`; existing watcher root `R/heldout_v3/native_tapb/`. Per-seed outputs are emitted only after complete six-arm selection. `R/native_tapb/development_prediction_parity.json` records mandatory adapter/scorer parity. |
| Proteomics | `U/heldout_ptpc_neural.py`; completed `R/heldout_ptpc_neural/seed{42,43,44}/` |
| Corrected cells | `C/evaluate_corrected.py` plus `C/version_proof.py`; ranking metrics in `U/heldout_v3.py::metrics_from_rows`; `R/heldout_v3/{vcc_corrected,norman_double_corrected,tahoe_drug_corrected}/seed*/` |

Completed evaluation directories contain `seal.json`, `results.json`,
`audit.json`, and `verification.json`. Seals bind selected checkpoint
SHA-256 values, study/selection/data hashes, and evaluator/scorer sources;
predictions remain local and are independently re-scored. Evaluation
follows development-only selection and does not send test results to the
controller. A watcher directory or training progress file alone is not
evidence of a completed evaluation. The manuscript's generated
`tables/strong_v3/snapshot.json` identifies the included verified records.

**First corrected VCC exception:**
`R/heldout_v3/vcc_corrected/seed42/version_proof.json` has
`phase=POSTHOC_INTEGRITY_CHECK`. The launcher checked the correction before
evaluation, but its original common seal did not directly bind the wrapper
registration. The later explicit integrity receipt was not backdated and
the original seal was not rewritten. It must not be presented as a
pre-evaluation wrapper-registration seal. Subsequent corrected runs use
`registration_seal.json` with
`phase=PRE_EVALUATION_REGISTRATION_SEAL`, bound to the same selection hash
and written before the common seal and held-out response decoding.

## Environment timing and selected immutable hashes

### Supplementary verification and uncertainty added 21 September 2026

- `U/verify_native_drugban_frozen.py` independently re-scores the retained native DrugBAN probabilities for seeds 42/43/44 and all three endpoints. Each `R/heldout_v3/native_dti/seed*/verification.json` binds the original results, seals, selected checkpoints, prediction rows and scorer. Its scores remain a separate historical-model control, never substituted into TAPB means.
- `U/bootstrap_native_tapb.py` and `U/bootstrap_native_drugban.py` add **post-hoc**, fixed-prediction paired cluster intervals. Their receipts are `R/uncertainty_native_tapb_v1/seed*.json` and `R/uncertainty_native_dti_v1/seed*.json`. Only completed, verified seeds receive receipts; a path pattern does not assert completion of seed 44.
- Each supplement uses 1,000 valid resamples with analysis seed 20260918, drug-identifier clusters on random/unseen-drug tests and protein-sequence clusters on unseen-protein tests. AUROC/AP, all three endpoints and all declared contrasts are retained, with source/prediction/result hashes. No checkpoint or design is reselected. These intervals condition on the fitted model and resampling groups, not on training-seed uncertainty or two-way drug/protein dependence.
- The aggregate publishers validate sidecar bindings before including intervals. The original results and seals are not rewritten to make this later analysis look prespecified. The main TAPB interval table is `tables/strong_v3/dti_uncertainty.tex`; historical DrugBAN's full endpoint intervals remain in the machine-readable diagnostic snapshot.

### Earlier environment receipts

`R/metadata/environment_1789717824.json` is an **observational snapshot
captured after some runs had started** (`captured_after_some_runs_started=true`),
not an initial-run preregistration. It records package versions, available
devices, source fingerprints, and local Qwen asset hashes. It describes the
controller/general environment; task-specific worker interpreters remain
in their registrations. Per-study `runtime_metadata.json`, where emitted
(including the three neural-proteomics studies), supplements this record.
Direct and loop use the same local Qwen model: bf16, temperature 0.7,
top-p 0.9, and at most 512 new tokens; actual attempt seeds are retained.

The following small-file hashes were rechecked against the local files for
this index. Full per-run bindings remain in the registrations and seals.

| Artifact (using prefixes above) | SHA-256 |
| --- | --- |
| `U/core_v3.py` | `ef53be48dfe17967e7d2faa20a200bc4c6e286ad21ef5406a694d07e26b663ae` |
| `U/run_v3.py` | `1abce301e0971c3778f279ee0a237104f0d5e4081d2e24657be23389714726d9` |
| `U/research_v2.py` | `ea0894213b6db722ad37f5541e11755dc2a351c80cf94c1906756f3d96d73184` |
| `C/run_corrected.py` | `fe4fcab1ef1a51b2fc15e39c6487a489769f0ab559f62e8d902e8622d6b4047f` |
| `R/native_tapb/data/manifest.json` | `399876d38731dcff057d233e967ed64fa2db0bc3af81d8d3449ce7b820ce7a0b` |
| `R/ptpc_neural/data/manifest.json` | `4cf60e630f3cf2754db61464e7f9dd6ab572ab914c87866991978d54deda4936` |
| `R/corrected_features/vcc_corrected/data/manifest.json` | `c9147016e65ad37d45c7dfdfab4ddeb6643303980208b8d8f1d32fe76aa7f227` |
| `R/corrected_features/norman_double_corrected/data/manifest.json` | `dacf076eec7d05325dbfd8fdc80f9a22470bf576b6231fcbc70b07dac4740b20` |
| `R/corrected_features/tahoe_drug_corrected/data/manifest.json` | `47c7e39e4fad2871e5d597618a97d95ef3fc16c24004cb22ae8e857676c26c26` |
| `R/metadata/environment_1789717824.json` | `047264ccbe27b41184ffc5c36ce24d7c02bee10d2d1d24dcfe3ffe4baade9679` |

Hashes identify the artifacts used; they do not independently certify
privacy guarantees or replace access-controlled reproducibility materials.

## Appendix A: executable-config case records

These three cases are indexed without copying raw responses or weights.
For **each** study directory below, the records are
`selected_development.json`, `federated_direct_history.json`, and
`federated_loop_history.json`. All twelve referenced files (these nine
records plus the three proposal records) were checked to exist.

| Case / study directory | Local proposal record and exact rationale field | Executed design |
| --- | --- | --- |
| `R/ptpc_neural/study_v3_seed42/` | `federated_loop_proposal_4.json`, `$.proposal.hypothesis` | D04; `$.proposal.config.residual=false` |
| `R/vcc_corrected/study_v3_seed43/` | `federated_loop_proposal_5.json`, `$.proposal.hypothesis` | D05; `$.proposal.config.residual=false` |
| `R/norman_double_corrected/study_v3_seed42/` | `federated_loop_proposal_5.json`, `$.proposal.hypothesis` | D10; `$.proposal.config.residual=false` |

In these records the generated hypothesis describes a residual adapter,
but the executable configuration disables it. The records therefore
illustrate a rationale/configuration mismatch, not reliable biological
diagnosis or evidence that a residual-adapter intervention was executed.
Selection and case interpretation follow the actual configuration and
measured development records, not the generated rationale alone.
