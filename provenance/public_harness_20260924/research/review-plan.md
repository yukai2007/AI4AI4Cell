# Public research-harness baseline review

## Review contract

- Working title: Faithful task-adapted AI-Scientist-v2 and AI-Researcher baselines for BioCoLoop.
- Review question: Which released experimental-control mechanisms can be connected to the same biological prediction and evaluation interface, and what adaptations must be disclosed?
- Intended reader: Authors implementing and checking the additional main-table baselines.
- Retrieval cutoff: 2026-09-24.
- Unit of analysis: Pinned official repository release and its executable research controller.
- Meaning of "all": The two user-requested frameworks across the five existing main-table endpoints, not every public research agent.

## Scope

- Include: SakanaAI/AI-Scientist-v2 and HKUDS/AI-Researcher official source, licenses, execution dependencies, controller/state/history APIs and linked primary papers where needed.
- Exclude: New biological tasks, new metrics, different held-out rosters, substitute lookalike controllers, unrelated ideation/publication benchmarks.
- Date range: Releases available through the retrieval cutoff.
- Languages: English source documentation; Chinese implementation handoff.
- Source types: Version-pinned official repositories and primary papers.
- Runtime access: Both pinned sources and isolated adapter dependencies are available. The local Qwen transport and fresh task fitting have run. The task execution boundary accepts structured design requests rather than arbitrary generated code.

User decision (2026-09-24): task-adapted experimental controllers, prioritizing the main-table comparison; use the common ten-laboratory fitter/scorer and disable literature retrieval and paper generation. Native experimental proposal/revision/management flow must be retained. The confirmed scope is not an end-to-end autonomous paper-generation reproduction.

Follow-up decision (2026-09-24): explicitly distinguish verified context/tool/pipeline failures from pending work, and deliver the comparison on `comparison/public-harness-20260924` for user approval before any merge to main. The three-seed primary table retains original means; the matched seed-42 view and execution outcomes are reported separately. Completed comparisons may include recorded controller failures, but this does not make all methods' predictive scores available.

Writing workflow note: the literature-review skill's optional sibling paper-writing and general-writing packages are absent in this environment. Source verification, manual prose review, citation checks and rendered-PDF inspection are used with the existing manuscript structure.

## Comparison axes

1. Authentic proposal, revision, experiment selection and history mechanisms preserved from upstream.
2. Shared biological predictor, legal design surface, local-fit schedule and original scorer.
3. Same laboratory/data access as BioCoLoop for the public-harness comparison.
4. Same research-model backend, candidate/training budget and recorded model-call costs.
5. Pinned source/patches, executed trials, failures, development-selected checkpoint and independent result verification.

## Search map

| Framework | Primary source | Status |
| --- | --- | --- |
| AI-Scientist-v2 | https://github.com/SakanaAI/AI-Scientist-v2 | Pinned `96bd51617cfdbb494a9fc283af00fe090edfae48`; native tree/controller integration tested; live pilot exposed domain-prompt conflicts, corrected before scored comparison |
| AI-Researcher | https://github.com/HKUDS/AI-Researcher | Pinned `f9a6f8480860c193afff600eeffe3defcee8a978`; native multi-stage integration tested with the actual broker and an explicitly synthetic fitter |

## Planned synthesis

- Source finding: Both frameworks require explicit experimental-tool and domain-prompt adaptation. Native source-level control and history mechanisms can be retained while replacing execution with the common biological fitting interface. Transformations and executed native methods are recorded per run.
- Main comparison: New public-harness rows should use the same ten-laboratory fitting interface as the BioCoLoop row; one-laboratory references retain their explicit access labels.
- Current main protocol to preserve: Five endpoints, seeds 42–44, 100 training rounds per candidate, six proposal slots and the registered 12-design library. Start with a recorded single-seed pilot before extending; do not mix an incomplete seed set into the existing three-seed mean without labeling it.
- Most important disclosure gap: Whether task adaptation can preserve native control flow without giving a framework extra training, data or evaluation feedback.
- Expected limitations: End-to-end paper-generation benchmarks and a fixed-task model-optimization benchmark answer different questions. Results must be labeled by the actually executed adaptation.

## Deliverables

- Manuscript format: Update existing manuscript only after verified comparable scores are available; no synthetic scores or completion claims.
- Evidence tables: Source/control-flow mapping and matched-budget experiment contract.
- Source ledger path: `source-ledger.csv`.
- Claim-evidence matrix path: `claim-evidence-matrix.csv`.
- Build and publication path: Existing paper tools and source-linked main-table publisher, with independent verification for any new row.
