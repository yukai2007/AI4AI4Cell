# BioCoLoop manuscript

**BioCoLoop: Collaborative Agentic Research for Biological Model Improvement**

BioCoLoop combines **biology**, **collaboration** and an iterative **research loop**. Historical releases retain their original names. The existing repository URL and storage paths remain stable for Overleaf and result provenance.

## Current revision — author-final PDF synchronized, 30 September 2026

The manuscript sources now follow the author's final submitted `5046_BioCoLoop_Collaborative_A (4).pdf`, not the earlier Overleaf draft. The rebuilt [English manuscript](output/pdf/BioCoLoop_manuscript.pdf) has **31 pages, with the main text ending on page 9**. The [unaltered submitted reference](provenance/author_final_pdf_20260930/author_submitted.pdf) is retained separately.

The [section-by-section synchronization report](provenance/author_final_pdf_20260930/CHANGES.zh-CN.md) explains the final abstract, introduction, method, results and appendix revisions. Only three additional errata were applied: the next evidence-card index in Equation (4), the five-option random-ranking MRR expectation (45.67 on the percentage scale), and removal of a stale failed-run example inconsistent with the current completed Qwen AI-Scientist-v2 DTI row.

No experiment was rerun and no result table, snapshot or figure asset was modified. The main table retains the Qwen2.5-7B-Instruct and GPT-5.6 Luna blocks, task-adapted AI-Scientist-v2/AI-Researcher baselines, standard deviations, and explicit partial/unscored/extended-context marks. The final text distinguishes history-guided proposal revision from the independently tested training-allocation policy; the main-table candidate schedule remains 100 rounds.

[Verification](provenance/author_final_pdf_20260930/verification.json) checks the entire rebuilt PDF against the submitted reference after the three declared corrections, preserves scientific-asset hashes and records the main-text boundary. Run:

```bash
python tools/verify_author_final_sync.py --pdf output/pdf/BioCoLoop_manuscript.pdf
python -m unittest discover -s tools -p 'test_*.py'
```

The Statistical Supplement is unchanged. The Chinese companion and older dated review records remain historical reading/provenance material, not a new translation or a verification of the submission-platform attachments. A GitHub push does not confirm that Overleaf has pulled or compiled the revision, or that OpenReview has been updated.

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

All five current figures have [editable PowerPoint entry points and a Chinese editing guide](figure_editing/README.zh-CN.md). Figures 3–5 expose native charts with embedded data; Figures 1–2 are now the author-supplied editable decks, so the earlier `figure_editing` counterparts for them are retained as historical alternatives rather than active artwork. These editing counterparts do not replace the active paper artwork until an edited deck has been reviewed and exported.

Figure 1 contrasts biological-AI research settings using the author-supplied editable deck (`paradigm_comparison_editable.pptx`), adopted with two declared, geometry-only layout repairs recorded in `assets/paradigm_comparison_v3.provenance.json`: the slide canvas is trimmed so the bottom margin matches the top margin, and the sparse middle panel is re-centred between its title row and the canvas bottom. No object is clipped, rescaled or re-labelled, and the author source file is unchanged; assets and checks are in `assets/paradigm_comparison_v3.*` and `tools/adapt_paradigm_v3.py`. Figure 2 is the author-supplied editable PowerPoint architecture deck (`0925_repaired_v3.pptx`), adopted with six declared repairs: the two Office-2010 alternate-content wrappers are flattened onto their vector text, the two math runs become ordinary italic text, the Propose card body is re-sized so `design id` is no longer clipped, the fixed-model label is darkened, the clipped screenshot fallbacks are dropped, and the `Raw data remain within each laboratory` note is removed as requested. The author source deck is unchanged; the adopted assets, declared repairs and structural checks are in `figures/biocoloop_framework_v3.*` and `tools/adapt_framework_v3.py`. Figure 3 shows laboratory-count sensitivity; Figure 4 shows development and held-out search trajectories.
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
