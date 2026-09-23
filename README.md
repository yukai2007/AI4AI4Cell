# AI4AI4Cell manuscript

**AI4AI4Cell: Collaborative Evidence-Guided Research for Biological Model Improvement**

## Current version: coauthor-reviewed collaborative research, 23 September 2026

The detailed annotated manuscript has been addressed point by point. The internal [response register](provenance/coauthor_review_20260922/RESPONSE.zh-CN.md) links all 24 written comments and their five associated highlight anchors to revisions. Introduction and method now separate the two-level mechanism from implementation details; the two main figures use a general laboratory count K, and the main table explicitly names the task predictors and Qwen direct. The redundant discussion is merged into the conclusion.

Appendix B adds independently rescored laboratory-count, external-source and proposer-budget evidence. Its [frozen snapshot](tables/core_review/snapshot.json) is separate from the main three-seed comparison. Pending evaluations remain N/A. The new evidence distinguishes proposal-history search from fixed-slate compute allocation and retains negative transfer and non-monotone budget effects. Internal review annotations contain collaborator information and are not anonymous submission material.

For a section-by-section Chinese reading guide with the main results, ablations, claim boundaries and appendix map, run `python3 tools/build_chinese_companion.py`. The generated file is `output/pdf/AI4AI4Cell_中文伴读版.pdf`; it is a concise companion rather than a second submission manuscript.

The main text follows three parallel biological task families: TAPB-based DTI, ProteinTalks-derived observed-response efficacy, and mask-corrected scDEBART-head perturbation identification (VCC single-gene, Norman double-gene, Tahoe drug strata). All use the same V3 training pipeline, local Qwen proposer, twelve-design library, training schedule, evidence-card history and selection rule, with task-specific adapters.

The framing is **collaborative evidence-guided research**. The inner training pipeline uses sample-weighted local-update aggregation; the outer harness structures proposals, executes candidates, records aggregate evidence cards and passes accepted, rejected and failed outcomes into the next proposal.

The main table has **task model (1 lab), Qwen direct (1 lab), and AI4AI4Cell (10 labs)**. Qwen proposes configurations; biological predictions come from TAPB, the ProteinTalks-derived efficacy head, or a corrected scDEBART response head. A separate full factorial comparison crosses one vs ten laboratories with fixed / direct / loop. The matched-compute experiment evaluates allocation over a fixed ten-design slate, 800 full-client rounds and 160 development measurements; its four wins, eight ties and no losses, including +10.84 Top-1 points on Norman, are evidence for allocation rather than for LLM-generated design quality.

The snapshot includes executed held-out tests for seeds 42--44. The clean main table presents five explicit endpoints; Appendix A reports sample variation, all six arms, proposal prefixes, uncertainty and secondary metrics. Selected checkpoints, configurations and data hashes bind each score to an executed run, and predictions are independently recomputed.

- Main tables: `tables/strong_v3/main.tex`, `effects.tex`; the latter is the compute-matched loop comparison.
- Full six-arm ablations, secondary metrics and uncertainty: Appendix A and `tables/strong_v3/`.
- Proposal schema, design library and protocol: Appendix A, `sections/22_appendix_unified_protocol.tex`.
- Machine-readable aggregate snapshot and receipt hashes: `tables/strong_v3/snapshot.json`.
- First figure: editable `assets/paradigm_comparison.svg` and vector PDF; detailed pipeline follows as Figure 2.
- Abstract/result numbers: generated `tables/strong_v3/snapshot_stats.tex`, never copied from development scores or mixed across model versions.
- Model versions, asset hashes, proposal/selection records and metadata locations: [provenance index](provenance/README.md).
Bold marks all best displayed values in each task column, including ties. Mean-client AUROC/AP, intervention-macro Top-1, development scores and final-test results are explicitly distinguished.

## Editing and compilation

Select `main.tex` as the Overleaf entry and **XeLaTeX** as compiler. `latexmkrc` also redirects the default pdfLaTeX command to XeLaTeX for the bundled fonts. Edit `ai4ai4cell-main.tex` and files under `sections/`; bibliography is `references.bib`.

Local build with a compatible Tectonic installation and populated TeX cache:

```bash
tectonic --only-cached --keep-intermediates --keep-logs --outdir build main.tex
```

On the research host, the compatible binary is the cached Tectonic 0.17.0 package, not the default executable in `~/.local/bin`. Use its matching cached shared libraries; the exact host-specific invocation is recorded with the local completion/build receipt. These environment paths are not a requirement for Overleaf.

The reading copy is `manuscript.pdf`; temporary compilation output is under `build/`. The ICLR 2027 template does not imply submission or acceptance.

## Refreshing the aggregate snapshot

First run `extensions/unified_bio_20260918/audit_v3.py` in the separate parent research workspace. Then, from this writing repository:

```bash
python tools/publish_strong_snapshot.py --results /path/to/results/unified_bio_20260918
python -m unittest discover -s tools -p 'test_*.py'
```

The main-score publisher reads completed aggregate records and verified held-out receipts. Its separate racing verifier additionally reads saved predictions and fixed scoring labels to recompute the reported metrics. Neither path trains models or performs new model inference. Final-test cells require complete paired evaluations with valid seals; otherwise they stay N/A. A refresh requires checking the narrative and snapshot date, compiling, and reviewing the rendered PDF. Figures remain vector/editable assets.

The main allocation table has its own `publish_racing_snapshot.py` path, invoked by the strong-snapshot publisher. It verifies saved predictions and the pinned V6 protocol before rendering, so a main-table refresh cannot silently replace it with the V3 factorial contrast table. The sensitivity publisher, `tools/publish_core_review.py`, requires a passing independent `core_verification.json` and unchanged completed-result hashes. It publishes only the verified snapshot; collecting new runs requires renewed verification and review of the narrative.

The 23 September sensitivity revision verifies 26 completed studies and 286 selected outcomes. It includes eight complete proposer/backend jobs and a paired search-dynamics table (Appendix B, Table B.5). The table distinguishes valid proposal count, time to a common development target, and unexplored configurations. To refresh this analysis after changing the core snapshot, rerun `extensions/core_ablation_20260922/budget_saturation.py --snapshot paper/tables/core_review/snapshot.json` from the parent research workspace, then run `python tools/publish_budget_analysis.py` here. The publication test rejects a trajectory analysis bound to an older snapshot. The Chinese companion uses the same frozen results.

The live completion checklist is `results/core_ablation_20260922/analysis/COMPLETION.zh-CN.md` in the parent workspace, not this frozen paper snapshot. A persistent queue now schedules the remaining DTI seeds, while the original lightweight studies continue. Three same-study proteomic cell contexts do not complete the independent-source requirement; separately retrieved external studies require an explicit assay/endpoint alignment protocol before fitting.

The current one-day-budget handoff is summarized in [SINGLE_SEED_DELIVERY_20260923.zh-CN.md](provenance/SINGLE_SEED_DELIVERY_20260923.zh-CN.md). It distinguishes the locked three-seed main paper from the still-optional native-DTI short-loop and external-proteomics-source extensions; those extensions must not be represented as completed results.

## Scope and publication

This writing repository contains the manuscript, aggregate snapshot, figure sources and publication checks. The experiment workspace retains the runtime, biological arrays and model checkpoints. Client-local roles are simulated by ten same-host workers; the interface can be combined with secure aggregation or differential privacy for deployments requiring formal protection.

The user's Overleaf-linked writing repository is `https://github.com/yukai2007/AI4AI4Cell`, branch `main`. Fetch collaborator changes, review and compile the diff, and use normal fast-forward pushes. A GitHub push alone does not establish an Overleaf pull or remote compilation. Do not publish editable Overleaf sharing links.

The template, bibliography styles and bundled TeX Gyre fonts retain their original licenses. Pipeline figures are original project vector artwork and contain no raw biological measurements.
