# BioCoLoop manuscript

**BioCoLoop: Collaborative Agentic Research for Biological Model Improvement**

BioCoLoop combines **biology**, **collaboration** and an iterative **research loop**. Historical releases retain their original names. The existing repository URL and storage paths remain stable for Overleaf and result provenance.

## Current revision — 26 September 2026

This is the near-final pre-deadline handoff. The submission PDF has nine pages of main text (31 pages including statements, references and appendices); the Chinese companion has 22 pages. A separate five-page anonymous Statistical Supplement retains all per-seed confidence intervals. The [latest build receipt](provenance/figure2_table_redesign_20260926/build_receipt.json) records PDF/source hashes, the nine-page main-text boundary, automated figure checks and 157 passing publication tests. Further changes before the deadline should focus on factual corrections, submission requirements or explicitly requested edits.

The Overleaf revision at `e9855b1` supplies the abstract, introduction and method prose that is retained here. The abstract and the introduction's evaluation sentence now name the newer task-adapted AI-Scientist-v2/AI-Researcher baselines alongside the matched Qwen2.5/GPT-5.6 Luna blocks, and the third contribution keeps its original wording; the method keeps the requested terminology clarifications. Float separation was tightened so that restoring the longer Overleaf introduction still ends the main text on page 9. The grouped main table is regenerated from `tools/publish_llm_grouped_main.py`, and a test now pins the committed table to that generator. The main-results table is redesigned as a grouped results block: `DTI`/`Proteomics`/`Cell perturbation` column groups under a `Model / method` column, per-model row bands, bold best/underlined runner-up cells, grey `--`/`†` marks for unscored/partial cells and a mean-rank `Average` column with blue `↑`/red `↓` deltas against the block's fixed reference, so failed runs no longer read as missing numbers. Figure 2 now uses the author's repaired editable slide deck (`/liziqing/yukai/AI4AI4Cell/0925_repaired_v3.pptx`), adapted by `tools/adapt_framework_v3.py` into `figures/biocoloop_framework_v3.pdf` with five declared, geometry-preserving repairs recorded in its provenance sidecar; the original deck is left untouched. The Chinese companion now adds a grouped Qwen2.5/GPT-5.6 Luna public-controller page rendered from `tables/public_harness_comparison/snapshot_llm_grouped_three_seed.json`, with the same incomplete-cell marks and the same typed failure tokens and completion counts as the English table and its Appendix C; its provenance record binds that snapshot and the independent Luna verification.

The main table contains matched Qwen2.5-7B-Instruct and GPT-5.6 Luna blocks over seeds 42--44: fixed model, direct optimization, AI-Scientist-v2, AI-Researcher and BioCoLoop. The public controllers use laboratory 0; BioCoLoop uses ten laboratories. All rows share the twelve-design library, candidate-training schedule and held-out scorer. Independently verified predictions, model-call receipts and typed controller failures are retained; incomplete cells are marked rather than imputed, their completed counts and typed failures are recorded in Section C.2, and a mean-rank column summarizes each method against the fixed reference. The [comparison report](output/pdf/public-harness-comparison.pdf) mirrors the final manuscript table. The public baselines are task-adapted control workflows: they retain their research-controller logic but use the common biological fitting interface, laboratory-0 access, candidate library, compute cap and held-out scorer. Typed context, tool and service failures remain visible as marked incomplete outcomes with their completed counts rather than being converted into scores.

**Overleaf-to-new-version migration.** The latest Overleaf revision (commit `e9855b1`) rewrote the abstract and introduction around a sharper distinction between collaborative parameter fitting and evidence-guided model development; it made the three contributions explicit and shortened the motivation. Its active method changes define a complete executable candidate recipe, the shared coordinator, the local state/score returns and the structured evidence card. Those changes are now applied to this branch while retaining the newer public-controller comparison, Qwen2.5 block, GPT-5.6 Luna block, and typed failure records. The commented draft text from Overleaf was not carried into the submission source.

The active narrative is **collaborative access plus evidence-guided research decisions**. The abstract states the four-of-five advantage over single-laboratory references; absolute task scores remain in the results with their comparison context. The introduction and conclusion separate gains from more participating laboratories, design search at fixed access, and independently evaluated training allocation. Method Section 3.4 identifies the allocation study, with matched-budget results in Section 4.4; the main comparison uses 100 training rounds per candidate. Same-access fixed/direct controls, proposal-history dynamics, source compatibility and laboratory count remain in the paper. The [appendix compaction note](provenance/appendix_compaction_20260924/RESPONSE.zh-CN.md) records the outcome-independent reduction from 21 to 16 appendix pages; numerical tables, predictions and experiment snapshots are unchanged.

The second annotated review remains addressed in a [27-item response](provenance/coauthor_review_v2_20260923/RESPONSE.zh-CN.md). The first proposal is shared without development feedback; feedback begins at the second proposal. Allocation and proposal-history policies are evaluated independently, not presented as a newly tested joint algorithm. Experiments and results form one section, with named task-model rows, laboratory-count curves and research trajectories in the main text.

The main three-seed benchmark remains a within-study partition experiment. Source-defined clients are reported separately, and the new matched comparison uses four cell scenarios, four clients and 60 perturbation conditions. Matching condition count does not match underlying cell count or gene panels. All twelve new fits and independent score checks are complete: same-source K4/N60 reaches 30.70% Top-1, versus 28.82% for cross-scenario K4/N60. This fixed-design comparison does not establish beneficial cross-scenario transfer. The third independent proteomics source, decryptE, completes four fixed-design controls: all three sources raise AP from 34.98 to 35.68, while target-only retains the higher AUROC. A further strict one-study-per-client comparison merges the target training shards into one lab: adding Lin, Ruprecht and decryptE raises AP from 34.41 to 37.53 and AUROC from 72.33 to 74.39. Both source protocols are reported; neither result is a proposal-loop effect.

The [independent review](provenance/coauthor_review_v2_20260923/RESPONSE.zh-CN.md) distinguishes supported claims from remaining gaps. Anonymous code hosting is not yet established; the manuscript includes a release commitment. Native DTI long24 and proposal-history comparisons on the new matched source partition remain outside the completed scope.

## Completed-experiment revision — 23 September 2026

The English manuscript incorporates the completed laboratory-count, independent-source, research-model and loop-budget experiments. The original three-seed main comparison and compute-matched allocation study remain unchanged; follow-up protocols are reported separately.

- Main results: five endpoints across DTI, observed-response proteomics and cell perturbation; seeds 42–44; `tables/strong_v3/`.
- Research-model ablation: Qwen2.5-7B-Instruct and the `gpt-5.6-luna` service, all five endpoints, direct versus feedback loop, 12 designs and six proposal slots.
- Laboratory count: K=1/2/5/10 for every endpoint, separately increasing participation and repartitioning a fixed total pool. DTI uses seed 61; lighter endpoints use seeds 61–63.
- Independent sources: three DTI collections, three cell collections and a two-study proteomics protocol, now supplemented by a separate three-study fixed-design extension. The new proteomics adapter has matched target-only controls. Three additional proteomic cell-line contexts from one study are reported separately.
- Extended loop: four lighter endpoints, two backends, 36 designs and 24 slots. This is a different design space from the short study. DTI has the completed six-slot comparison, not a 24-slot run.
- Traceability: all 504 attempted short/long proposal slots, design configurations, development evidence, prefix scores and source hashes are published in `tables/completed_ablation/`.

Completing an experiment matrix does not establish a universal loop benefit. Short-loop feedback gives one held-out gain, one decrease and eight ties; extended search gives seven ties and one decrease. Separately, compute-matched allocation yields four wins, eight ties and no losses, including +10.84 Top-1 points on Norman. These evaluate different research decisions and are not conflated.

The readable [completion audit](provenance/completed_ablation_20260923/research/ACCEPTANCE.zh-CN.md) identifies the exact coverage. The [coauthor response register](provenance/coauthor_review_20260922/RESPONSE.zh-CN.md) preserves all 24 written comments and their five highlight anchors. Internal review records contain collaborator information and are not anonymous submission material.

## Figures and reading copies

All five current figures have [editable PowerPoint entry points and a Chinese editing guide](figure_editing/README.zh-CN.md). Figures 1–2 expose native text, shapes and arrows; Figures 3–5 expose native charts with embedded data. These editing counterparts do not replace the active paper artwork until an edited deck has been reviewed and exported.

Figure 1 contrasts biological-AI research settings. Figure 2 is the author-supplied editable PowerPoint architecture deck (`0925_repaired_v3.pptx`), adopted with five declared repairs: the two Office-2010 alternate-content wrappers are flattened onto their vector text, the two math runs become ordinary italic text, the Propose card body is re-sized so `design id` is no longer clipped, the fixed-model label is darkened, and the clipped screenshot fallbacks are dropped. The author source deck is unchanged; the adopted assets, declared repairs and structural checks are in `figures/biocoloop_framework_v3.*` and `tools/adapt_framework_v3.py`. Figure 3 shows laboratory-count sensitivity; Figure 4 shows development and held-out search trajectories.
The [English completed-experiment PDF](output/pdf/BioCoLoop_manuscript.pdf) is also copied locally to `manuscript.pdf`. Upload the [anonymous Statistical Supplement](output/pdf/BioCoLoop_statistical_supplement.pdf) alongside the manuscript: its two complete tables contain all 162 per-seed contrast rows, including zero and negative results. The [Chinese section-by-section companion](output/pdf/BioCoLoop_中文伴读版.pdf) is regenerated with:

```bash
python3 tools/build_chinese_companion.py
```

The companion explains the methods, numerical results, completed ablations and remaining experimental scope. It is a reading guide, not a second submission manuscript.

## Editing and compilation

Select `main.tex` as the Overleaf entry and **XeLaTeX** as compiler. `latexmkrc` redirects the default pdfLaTeX command for the bundled fonts. Edit `biocoloop-main.tex` and `sections/`; citations live in `references.bib` and `references_v2.bib`. The official ICLR template and its spacing are unchanged.

```bash
tectonic --only-cached --keep-intermediates --keep-logs --outdir build main.tex
tectonic --only-cached --keep-intermediates --keep-logs --outdir build statistical-supplement.tex
python -m unittest discover -s tools -p 'test_*.py'
```

The research host requires its compatible cached Tectonic 0.16.0 binary and matching shared libraries, rather than the default local binary. This host-specific setup is not required on Overleaf. The final build receipt is in `provenance/final_submission_20260926/`; second-review records remain in `provenance/coauthor_review_v2_20260923/`, and the historical naming-only receipt remains in `provenance/rename_biocoloop_20260923/`.

## Data-to-paper publication

The writing repository contains manuscript sources, aggregate records, figure assets and publication checks. Runtime code, biological arrays and checkpoints remain in the parent research workspace. Each table is generated from completed evaluation records with frozen source hashes; development-selected checkpoints and held-out results are distinct.

- `tools/publish_strong_snapshot.py`: original main study; also invokes the independent compute-matched racing publisher.
- `tools/publish_completed_ablation.py`: final completed follow-up snapshot, figures, tables and proposal traces. It reads verified results and does not train or run inference.
- `tools/publish_core_review.py`: historical coauthor-review snapshot, retained for provenance; it is not the source of the current Appendix B.
- `tables/completed_ablation/provenance.json`: bindings between completed source records and published outputs.
- `tools/publish_supplemental_proteomics.py`: independently verified third-source controls, kept separate from the earlier two-source loop study.
- `tables/proteomics_scenario_labs_v2/`: completed one-study-per-lab proteomics controls, separately verified with four CPU fits.
- `tables/scenario_labs_v2/`: matched source-as-scenario comparison; publication requires twelve completed fits and independent prediction-level rescoring.
- `tables/completed_ablation/proposal_trace.tsv`: all 504 attempted slots; the manuscript presents representative decisions instead of printing the full log.

The active narrative is collaborative evidence-guided research. The inner process uses sample-weighted local-update aggregation; the outer harness proposes executable configurations and returns accepted, rejected and failed outcomes as evidence for subsequent decisions. Same-host workers simulate laboratory boundaries. Raw-data locality alone is not a formal privacy guarantee.

## Synchronization and submission

The user's Overleaf-linked writing repository is `https://github.com/yukai2007/AI4AI4Cell`, branch `main`. Fetch collaborator changes, review and compile the diff, and use a normal fast-forward push. A GitHub push does not verify an Overleaf pull or remote compilation. Do not publish editable Overleaf sharing links.

Authors must confirm the submission-platform declarations and upload the final anonymous artifacts. The template does not imply submission or acceptance. The template, bibliography styles and bundled fonts retain their original licenses.

Submit the main PDF plus the Statistical Supplement. The Chinese companion and internal provenance/review notes are author reading material, not anonymized submission supplements.
