# AI4AI4Bio manuscript

**AI4AI4Bio: Federated Evidence-Guided Research for Biological Model Improvement**

## Current version: uniform six-arm study, 18 September 2026

The main text now follows three parallel biological task families: native DrugBAN DTI, observed-response proteomic efficacy, and scDEBART-head perturbation identification (VCC single-gene, Norman double-gene, Tahoe drug strata). All use the same V3 federated core, local Qwen proposer, design library, training schedule and selection rule.

The six arms cross **one vs ten laboratories** with **fixed model / feedback-free direct search / feedback-guided loop**. Three contrasts are reported separately: loop minus fixed, loop minus matched-budget direct, and ten-laboratory loop minus one-laboratory loop.

The 18 September snapshot (exact UTC export time in `snapshot.json`) contains completed **seed-42 development** results for proteomics and all three cell strata. These show positive laboratory-participation contrasts, but loop and matched-budget direct tie on every available primary endpoint. Native DTI, three-seed summaries, new cosine references and uniform final-test scores are **N/A**, not extrapolated from earlier experiments. The training queue does not itself implement final-test scoring or the remaining reference reruns.

- Main tables: `tables/unified_v3/development.tex`, `effects.tex`, `final.tex`.
- Secondary metrics and protocol: Appendix R, `sections/22_appendix_unified_protocol.tex`.
- Machine-readable aggregate snapshot and receipt hashes: `tables/unified_v3/snapshot.json`.
- Current pipeline: editable `assets/unified_pipeline.svg` and vector PDF.
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
python -m unittest discover -s tools -p 'test_*.py'
```

The publisher reads only completed, audited aggregate records. It does not train models, read raw biological arrays or perform test evaluation. The current exporter deliberately keeps final-test cells N/A; adding measured test results requires a separately validated test-export implementation. A refresh also requires checking the narrative and snapshot date, compiling, and reviewing the rendered PDF. Figures remain vector/editable assets.

## Scope and publication

This writing repository does not include the full experiment runtime, raw biological data, model checkpoints or the supplied Nature PDF. It is not a standalone reproducible benchmark release. Federated training is a one-host laboratory simulation, not differential privacy or secure aggregation. Existing benchmark test roles were previously examined in historical studies.

The user's Overleaf-linked writing repository is `https://github.com/yukai2007/AI4AI4Cell`, branch `main`. The local configured origin may still point to the historical `_ICLR` repository; verify the explicit destination before publication. Fetch collaborator changes, review and compile the diff, and use normal fast-forward pushes. A GitHub push alone does not establish an Overleaf pull or remote compilation. Do not publish editable Overleaf sharing links.

The template, bibliography styles and bundled TeX Gyre fonts retain their original licenses. Current and historical pipeline figures are original project vector artwork and contain no raw biological measurements.
