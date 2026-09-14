# AI4AI4Cell manuscript

Title: **AI4AI4Cell: Federated Evidence-Guided Research for Biological Model Improvement**.

This is an editable, result-bearing research draft, not a submitted/accepted article. The completed performance-first revision connects executable-design research with actual client-local gradient training. It includes all 21 full-data, 100-epoch BAN-family refits, five complete TAPB fits, DTI probability-program research, unchanged-program transfer to TAPB, matched training-pool cosine references and a 24-trajectory comparison with native Helmsman. The ten-method DTI overview uses the original scorer and all three test splits. Our selected BAN architectures lead that family in mean AUROC; program transfer improves TAPB without new training or search. Direct-generation and manual-fusion controls identify where those gains arise, and do not establish universal loop superiority or broad SOTA. The earlier Cell, DTI and PTPC studies remain preserved. The named local PDF is updated only after the corresponding manuscript build and review.

## Editing and compiling

The 14 September coauthor integration sharpens the two-level method and retained-source/failure-feedback case, adds biological-FL and Chiron related work, and distinguishes a reconstructed historical no-LLM calibration reference from direct LLM generation. Existing scientific tables and selected experimental artifacts are unchanged. Unverified coauthor FL scores are not included.

- Select `main.tex` as the Overleaf main document and **XeLaTeX** as compiler.
- The bundled `latexmkrc` also redirects the default pdfLaTeX command to XeLaTeX, so a newly synchronized project with its old pdfLaTeX setting can load `fontspec` and the bundled OpenType fonts. This uses Overleaf's supported project-level command configuration, not a change to the web UI's compiler setting. If needed, explicitly select XeLaTeX and use Recompile from scratch. Local Perl configuration checks passed; the current remote Overleaf compilation has not been independently verified.
- `main.tex` is a compatibility entry. Edit the descriptive `ai4ai4cell-main.tex` orchestration file and prose under `sections/`.
- Bibliography: `references.bib`. Editable figure source: `assets/method_diagram.svg`; the manuscript includes its vector PDF.
- Local build: `tectonic -X compile --only-cached --keep-logs --outdir build main.tex` with Tectonic 0.16.0. Without a populated TeX cache, omit `--only-cached` to obtain compiler packages. Alternatively use XeLaTeX, BibTeX, and two further XeLaTeX passes.
- The named reading copy is `manuscript.pdf`; compiler output lives under `build/`. Export tools exclude both from the paper-only source ZIP.

## Scope and source migration

The source was initially migrated from the legacy final-study release. All 28 historical numeric table rows remain unchanged. The main method distinguishes outer executable-design research from inner task-weight fitting. Earlier partner-card studies only evaluated centrally fitted candidates; the new local-training study executes fixed logistic objectives through actual client loss/gradient aggregation. Direct and loop receive identical training access within each client-count condition. The research LLM remains fixed. Same-host execution and bounded diagnostics do not constitute differential privacy or secure aggregation.

Detailed local migration, claim/evidence records, compilation and visual-review receipts live outside this paper-only project under `docs/overleaf/`. Full experiment/data manifests remain in the parent project's `results/` and `runtime/`; they are deliberately absent from this source bundle. Do not overwrite the frozen historical results to match future protocols.

## Asset provenance

The ICLR 2027 style, bibliography style, `natbib.sty`, and `fancyhdr.sty` are unchanged assets from the earlier project. The draft status text is explicitly patched in the orchestration file; using this style does not imply submission or acceptance. Four unchanged TeX Gyre Termes OpenType fonts (2.501) are bundled with their GUST Font License. The method figure is original project vector artwork and contains no raw biological measurements.

The paper-only source excludes raw biological data, checkpoints, runtime logs, credentials, and the supplied Nature PDF. The working-tree origin is https://github.com/yukai2007/AI4AI4Cell_ICLR; the user also requested a copy at https://github.com/yukai2007/AI4AI4Cell, their Overleaf-linked writing repository. Both use branch main. Check collaborator changes before publication, review and compile the diff, and use normal fast-forward pushes. A GitHub push does not establish an Overleaf pull or remote compilation. Do not publish an editable Overleaf sharing link in this public repository.
