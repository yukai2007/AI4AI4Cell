# AI4AI4Cell manuscript

**AI4AI4Cell: Collaborative Evidence-Guided Research for Biological Model Improvement**

## Current version: collaborative research with six-arm attribution, 22 September 2026

For a section-by-section Chinese reading guide with the main results, ablations, claim boundaries and appendix map, run `python3 tools/build_chinese_companion.py`. The generated file is `output/pdf/AI4AI4Cell_中文伴读版.pdf`; it is a concise companion rather than a second submission manuscript.

The main text follows three parallel biological task families: TAPB-based DTI, ProteinTalks-derived observed-response efficacy, and mask-corrected scDEBART-head perturbation identification (VCC single-gene, Norman double-gene, Tahoe drug strata). All use the same V3 training pipeline, local Qwen proposer, twelve-design library, training schedule, evidence-card history and selection rule, with task-specific adapters.

The framing is **collaborative evidence-guided research**. The inner training pipeline uses sample-weighted local-update aggregation; the outer harness structures proposals, executes candidates, records aggregate evidence cards and passes accepted, rejected and failed outcomes into the next proposal.

The main table has **fixed model (1 lab), direct optimize / harness-free (1 lab), and our harness (10 labs)**. This is an access-enabled system comparison. A separate full factorial ablation crosses one vs ten laboratories with fixed / direct / loop, isolating feedback effects at matched data access from additional laboratory participation.

The snapshot includes executed held-out tests for seeds 42--44. The clean main table presents five explicit endpoints; Appendix A reports sample variation, all six arms, proposal prefixes, uncertainty and secondary metrics. Selected checkpoints, configurations and data hashes bind each score to an executed run, and predictions are independently recomputed.

- Main tables: `tables/strong_v3/main.tex`, `effects.tex`.
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

The publisher reads completed, audited aggregate records and independently verified held-out receipts. It does not train models, read raw biological arrays or perform test evaluation. Final-test cells require complete paired evaluations with valid seals; otherwise they stay N/A. A refresh requires checking the narrative and snapshot date, compiling, and reviewing the rendered PDF. Figures remain vector/editable assets.

## Scope and publication

This writing repository contains the manuscript, aggregate snapshot, figure sources and publication checks. The experiment workspace retains the runtime, biological arrays and model checkpoints. Client-local roles are simulated by ten same-host workers; the interface can be combined with secure aggregation or differential privacy for deployments requiring formal protection.

The user's Overleaf-linked writing repository is `https://github.com/yukai2007/AI4AI4Cell`, branch `main`. Fetch collaborator changes, review and compile the diff, and use normal fast-forward pushes. A GitHub push alone does not establish an Overleaf pull or remote compilation. Do not publish editable Overleaf sharing links.

The template, bibliography styles and bundled TeX Gyre fonts retain their original licenses. Pipeline figures are original project vector artwork and contain no raw biological measurements.
