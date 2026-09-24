# BioCoLoop manuscript

**BioCoLoop: Collaborative Agentic Research for Biological Model Improvement**

BioCoLoop combines **biology**, **collaboration** and an iterative **research loop**. Historical releases retain their original names. The existing repository URL and storage paths remain stable for Overleaf and result provenance.

## Current revision — 24 September 2026

This is the near-final pre-deadline handoff. The submission PDF has nine pages of main text (33 pages including statements, references and appendices); the Chinese companion has 20 pages. The frozen experimental scope and numerical tables are unchanged. The [latest build receipt](provenance/terminology_clarity_20260924/build_receipt.json) records PDF/source hashes, visual checks and 84 passing publication tests. Further changes before the deadline should focus on factual corrections, submission requirements or explicitly requested edits.

The active narrative is **collaborative access plus evidence-guided research decisions**. The abstract states the four-of-five advantage over single-laboratory references; absolute task scores remain in the results with their comparison context. The text consistently distinguishes laboratories, the coordinator and the research controller. Method Section 3.4 identifies trajectory-guided allocation as a separate controlled study, with matched-budget results in Section 4.4; the main comparison uses 100 training rounds per candidate. The main-results discussion also gives same-access fixed/direct controls. Proposal-history dynamics, source compatibility and laboratory count provide the subsequent mechanism analysis. The [targeted wording revision](provenance/terminology_clarity_20260924/RESPONSE.zh-CN.md) follows the [evidence-led revision](provenance/evidence_led_revision_20260924/RESPONSE.zh-CN.md); numerical tables, predictions and experiment snapshots are unchanged.

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

Figure 1 contrasts biological-AI research settings. Figure 2 is a new native-vector, editable PowerPoint diagram based on the earlier framework layout, with explicit inner/outer data flow, semantic colors, distinct lab scenarios and general K. Original slides remain unchanged. The new assets and structural/visual checks are in `figures/biocoloop_framework_v2.*`. Figure 3 shows laboratory-count sensitivity; Figure 4 shows development and held-out search trajectories.
The [English completed-experiment PDF](output/pdf/BioCoLoop_manuscript.pdf) is also copied locally to `manuscript.pdf`. The [Chinese section-by-section companion](output/pdf/BioCoLoop_中文伴读版.pdf) is regenerated with:

```bash
python3 tools/build_chinese_companion.py
```

The companion explains the methods, numerical results, completed ablations and remaining experimental scope. It is a reading guide, not a second submission manuscript.

## Editing and compilation

Select `main.tex` as the Overleaf entry and **XeLaTeX** as compiler. `latexmkrc` redirects the default pdfLaTeX command for the bundled fonts. Edit `biocoloop-main.tex` and `sections/`; citations live in `references.bib` and `references_v2.bib`. The official ICLR template and its spacing are unchanged.

```bash
tectonic --only-cached --keep-intermediates --keep-logs --outdir build main.tex
python -m unittest discover -s tools -p 'test_*.py'
```

The research host requires its compatible cached Tectonic 0.17.0 binary and matching shared libraries, rather than the default local binary. This host-specific setup is not required on Overleaf. The latest build receipt is in `provenance/terminology_clarity_20260924/`; second-review records remain in `provenance/coauthor_review_v2_20260923/`, and the historical naming-only receipt remains in `provenance/rename_biocoloop_20260923/`.

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
