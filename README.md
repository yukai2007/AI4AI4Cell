# BioCoLoop manuscript

**BioCoLoop: Collaborative Agentic Research for Biological Model Improvement**

BioCoLoop combines **biology**, **collaboration** and an iterative **research loop**. This is a naming-only revision: experimental scores, designs, datasets and frozen identifiers are unchanged. Historical releases retain their original names. The existing repository URL and storage paths remain stable for Overleaf and result provenance.

## Completed-experiment revision — 23 September 2026

The English manuscript incorporates the completed laboratory-count, independent-source, research-model and loop-budget experiments. The original three-seed main comparison and compute-matched allocation study remain unchanged; follow-up protocols are reported separately.

- Main results: five endpoints across DTI, observed-response proteomics and cell perturbation; seeds 42–44; `tables/strong_v3/`.
- Research-model ablation: Qwen2.5-7B-Instruct and the `gpt-5.6-luna` service, all five endpoints, direct versus feedback loop, 12 designs and six proposal slots.
- Laboratory count: K=1/2/5/10 for every endpoint, separately increasing participation and repartitioning a fixed total pool. DTI uses seed 61; lighter endpoints use seeds 61–63.
- Independent sources: three DTI collections, three cell collections and **two** independent proteomics studies. The new proteomics adapter has matched target-only controls. Three additional proteomic cell-line contexts from one study are reported separately.
- Extended loop: four lighter endpoints, two backends, 36 designs and 24 slots. This is a different design space from the short study. DTI has the completed six-slot comparison, not a 24-slot run.
- Traceability: all 504 attempted short/long proposal slots, design configurations, development evidence, prefix scores and source hashes are published in `tables/completed_ablation/`.

The completed queue is not equivalent to three independent protein sources or a universal loop benefit. Short-loop feedback gives one held-out gain, one decrease and eight ties; extended search gives seven ties and one decrease. Separately, compute-matched allocation yields four wins, eight ties and no losses, including +10.84 Top-1 points on Norman. These evaluate different research decisions and are not conflated.

The readable [completion audit](provenance/completed_ablation_20260923/research/ACCEPTANCE.zh-CN.md) identifies the exact coverage. The [coauthor response register](provenance/coauthor_review_20260922/RESPONSE.zh-CN.md) preserves all 24 written comments and their five highlight anchors. Internal review records contain collaborator information and are not anonymous submission material.

## Figures and reading copies

Figure 1 compares the research paradigms. Figure 2 uses the user-supplied editable framework slide, converted to a vector PDF with layout-only font and text-box repairs. The original source is unchanged. The current editable derivative uses BioCoLoop and collaborative terminology, with the layout, modules and measurements preserved. The caption relates the illustrated ten laboratories to general K and states the evaluated design scope. The PDF, editable derivative and conversion receipt are in `figures/`.

The [English completed-experiment PDF](output/pdf/BioCoLoop_manuscript.pdf) is also copied locally to `manuscript.pdf`. The [Chinese section-by-section companion](output/pdf/BioCoLoop_中文伴读版.pdf) is regenerated with:

```bash
python3 tools/build_chinese_companion.py
```

The companion explains the methods, numerical results, completed ablations and remaining experimental scope. It is a reading guide, not a second submission manuscript.

## Editing and compilation

Select `main.tex` as the Overleaf entry and **XeLaTeX** as compiler. `latexmkrc` redirects the default pdfLaTeX command for the bundled fonts. Edit `biocoloop-main.tex` and `sections/`; citations live in `references.bib`. The official ICLR template and its spacing are unchanged.

```bash
tectonic --only-cached --keep-intermediates --keep-logs --outdir build main.tex
python -m unittest discover -s tools -p 'test_*.py'
```

The research host requires its compatible cached Tectonic 0.17.0 binary and matching shared libraries, rather than the default local binary. This host-specific setup is not required on Overleaf. Build and visual-review receipts are in `provenance/rename_biocoloop_20260923/`.

## Data-to-paper publication

The writing repository contains manuscript sources, aggregate records, figure assets and publication checks. Runtime code, biological arrays and checkpoints remain in the parent research workspace. Each table is generated from completed evaluation records with frozen source hashes; development-selected checkpoints and held-out results are distinct.

- `tools/publish_strong_snapshot.py`: original main study; also invokes the independent compute-matched racing publisher.
- `tools/publish_completed_ablation.py`: final completed follow-up snapshot, figures, tables and proposal traces. It reads verified results and does not train or run inference.
- `tools/publish_core_review.py`: historical coauthor-review snapshot, retained for provenance; it is not the source of the current Appendix B.
- `tables/completed_ablation/provenance.json`: bindings between completed source records and published outputs.

The active narrative is collaborative evidence-guided research. The inner process uses sample-weighted local-update aggregation; the outer harness proposes executable configurations and returns accepted, rejected and failed outcomes as evidence for subsequent decisions. Same-host workers simulate laboratory boundaries. Raw-data locality alone is not a formal privacy guarantee.

## Synchronization and submission

The user's Overleaf-linked writing repository is `https://github.com/yukai2007/AI4AI4Cell`, branch `main`. Fetch collaborator changes, review and compile the diff, and use a normal fast-forward push. A GitHub push does not verify an Overleaf pull or remote compilation. Do not publish editable Overleaf sharing links.

Authors must confirm the submission-platform declarations and upload the final anonymous artifacts. The template does not imply submission or acceptance. The template, bibliography styles and bundled fonts retain their original licenses.
