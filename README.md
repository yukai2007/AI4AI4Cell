# AI4AI4Bio manuscript

**AI4AI4Bio: Federated Evidence-Guided Research for Biological Model Improvement**

## Current version: three-row main comparison with six-arm attribution, 18 September 2026

The main text follows three parallel biological task families: TAPB-based DTI, ProteinTalks-derived observed-response efficacy, and mask-corrected scDEBART-head perturbation identification (VCC single-gene, Norman double-gene, Tahoe drug strata). These are task-adapted model references, not certified global-SOTA reproductions. All use the same V3 federated core, local Qwen proposer, design library, training schedule and selection rule.

The main table has **fixed model (1 lab), direct optimize / harness-free (1 lab), and our harness (10 labs)**. This is an access-enabled system comparison. A separate full factorial ablation crosses one vs ten laboratories with fixed / direct / loop, isolating feedback effects at matched data access from additional laboratory participation.

The snapshot includes **executed retrospective held-out tests** for completed seeds, with per-column counts. Proteomics, VCC and the completed TAPB DTI seed show access-enabled gains; other outcomes and matched-data loop effects are retained irrespective of direction. DTI currently has one of three completed seeds; remaining seed cells stay **N/A**, not extrapolated from development or earlier protocols. Selected checkpoints/configurations/data are frozen before held-out response decoding; the audit distinguishes complete pre-decode registration from a supplemental post-hoc source-integrity receipt. Predictions and scores are independently recomputed. Previously exposed benchmark roles are not called blind validation.

- Main tables: `tables/strong_v3/main.tex`, `effects.tex`.
- Full six-arm ablations, secondary metrics and uncertainty: Appendix R and `tables/strong_v3/`.
- Older linear-head, uncorrected-cell and DrugBAN diagnostic versions: `tables/unified_v3/`, retained separately in Appendix R.
- Secondary metrics and protocol: Appendix R, `sections/22_appendix_unified_protocol.tex`.
- Machine-readable aggregate snapshots and receipt hashes: `tables/strong_v3/snapshot.json` and `tables/unified_v3/snapshot.json`.
- First figure: editable `assets/paradigm_comparison.svg` and vector PDF; detailed pipeline follows as Figure 2.
- Abstract/result numbers: generated `tables/strong_v3/snapshot_stats.tex`, never copied from development scores or mixed across model versions.
- Model versions, asset hashes, proposal/selection records and metadata locations: [provenance index](provenance/README.md).
- Previous source-search, strong-start and held-out studies remain in the historical appendices under their original protocols. Their scores are not inserted into new uniform-protocol N/A cells.

Bold marks all best displayed values in each task column, including ties. It does not denote significance or global SOTA. Mean-client AUROC/AP, intervention-macro Top-1, development scores and final-test results are explicitly distinguished.

## Editing and compilation

Select `main.tex` as the Overleaf entry and **XeLaTeX** as compiler. `latexmkrc` also redirects the default pdfLaTeX command to XeLaTeX for the bundled fonts. Edit `ai4ai4cell-main.tex` and files under `sections/`; bibliography is `references.bib`.

Local build with the populated TeX cache:

```bash
tectonic --only-cached --keep-intermediates --keep-logs --outdir build main.tex
```

The reading copy is `manuscript.pdf`; temporary compilation output is under `build/`. The ICLR 2027 template does not imply submission or acceptance.

## Refreshing the aggregate snapshot

First run `extensions/unified_bio_20260918/audit_v3.py` in the separate parent research workspace. Then, from this writing repository:

```bash
python tools/publish_unified_snapshot.py --results /path/to/results/unified_bio_20260918
python tools/publish_strong_snapshot.py --results /path/to/results/unified_bio_20260918
python -m unittest discover -s tools -p 'test_*.py'
```

The publisher reads completed, audited aggregate records and independently verified held-out receipts. It does not train models, read raw biological arrays or perform test evaluation. Final-test cells require complete paired evaluations with valid seals; otherwise they stay N/A. A refresh requires checking the narrative and snapshot date, compiling, and reviewing the rendered PDF. Figures remain vector/editable assets.

## Scope and publication

This writing repository does not include the full experiment runtime, raw biological data, model checkpoints or the supplied Nature PDF. It is not a standalone reproducible benchmark release. Federated training is a one-host laboratory simulation, not differential privacy or secure aggregation. Existing benchmark test roles were previously examined in historical studies.

The user's Overleaf-linked writing repository is `https://github.com/yukai2007/AI4AI4Cell`, branch `main`. The local configured origin may still point to the historical `_ICLR` repository; verify the explicit destination before publication. Fetch collaborator changes, review and compile the diff, and use normal fast-forward pushes. A GitHub push alone does not establish an Overleaf pull or remote compilation. Do not publish editable Overleaf sharing links.

The template, bibliography styles and bundled TeX Gyre fonts retain their original licenses. Current and historical pipeline figures are original project vector artwork and contain no raw biological measurements.
