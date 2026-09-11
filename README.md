# AI4AI4Cell manuscript

Title: **AI4AI4Cell: An Auditable Harness for Evidence-Gated Agentic Research in Cell Biology**.

This is an editable research draft, not a submitted/accepted article or a claim that every planned experiment is complete. It preserves the completed Cell and native-system DTI results from the 2026-09-11 V3 study. Official public supplementary proteomics datasets have now been obtained; task harmonization and prospective evaluation remain unfinished, and contribute no results to this manuscript.

## Editing and compiling

- Select `main.tex` as the Overleaf main document and **XeLaTeX** as compiler.
- The bundled `latexmkrc` also redirects the default pdfLaTeX command to XeLaTeX, so a newly synchronized project with its old pdfLaTeX setting can load `fontspec` and the bundled OpenType fonts. This uses Overleaf's supported project-level command configuration, not a change to the web UI's compiler setting. If needed, explicitly select XeLaTeX and use Recompile from scratch. Local Perl configuration checks passed; the current remote Overleaf compilation has not been independently verified.
- `main.tex` is a compatibility entry. Edit the descriptive `ai4ai4cell-main.tex` orchestration file and prose under `sections/`.
- Bibliography: `references.bib`. Editable figure source: `assets/method_diagram.svg`; the manuscript includes its vector PDF.
- Local build: `tectonic -X compile --only-cached --keep-logs --outdir build main.tex` with Tectonic 0.16.0. Without a populated TeX cache, omit `--only-cached` to obtain compiler packages. Alternatively use XeLaTeX, BibTeX, and two further XeLaTeX passes.
- The named reading copy is `manuscript.pdf`; compiler output lives under `build/`. Export tools exclude both from the paper-only source ZIP.

## Scope and source migration

The source was migrated from the legacy `paper/final_study/final_20260911_v3` release without changing any of its eight inline tables. The title and methodological wording were clarified; a future-extension paragraph and the supplied Sun et al. paper citation were added. DrugEvolve is a native controller comparison with disclosed promotion differences, not a same-selector or equal-token causal experiment. Federated evidence updates research artifacts while leaving the research LLM fixed; it is not FedAvg or a privacy guarantee.

Detailed local migration, claim/evidence records, compilation and visual-review receipts live outside this paper-only project under `docs/overleaf/`. Full experiment/data manifests remain in the parent project's `results/` and `runtime/`; they are deliberately absent from this source bundle. Do not overwrite the frozen historical results to match future protocols.

## Asset provenance

The ICLR 2027 style, bibliography style, `natbib.sty`, and `fancyhdr.sty` are unchanged assets from the earlier project. The draft status text is explicitly patched in the orchestration file; using this style does not imply submission or acceptance. Four unchanged TeX Gyre Termes OpenType fonts (2.501) are bundled with their GUST Font License. The method figure is original project vector artwork and contains no raw biological measurements.

The paper-only source excludes raw biological data, checkpoints, runtime logs, credentials, and the supplied Nature PDF. This working tree tracks the user-designated public repository https://github.com/yukai2007/AI4AI4Cell on branch `main`. The user has linked that repository to Overleaf; GitHub pushes must be pulled through Overleaf's GitHub integration. Always pull collaborator changes before editing, review and compile the diff, and use a normal fast-forward push. Do not publish an editable Overleaf sharing link in this public repository.
