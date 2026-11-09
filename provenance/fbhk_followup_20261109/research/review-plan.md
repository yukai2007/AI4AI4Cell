# FBhK follow-up: search and validation evidence

## Review contract

- Working title: Matched search controls and development-selection generalization.
- Review question: Which controls isolate history feedback, and what can existing measurements establish about adaptive development selection?
- Intended reader: Reviewer FBhK and the BioCoLoop authors.
- Retrieval cutoff: 2026-11-09, Asia/Shanghai (session date).
- Unit of analysis: Original methodological paper and reproducible BioCoLoop experiment.
- Meaning of "all": All completed comparison arms in the in-scope experiments, not an exhaustive literature survey.

## Scope

- Include: Random configuration search; model-selection bias; adaptive validation; all original short/extended searches and the completed three-seed history-feedback study.
- Exclude: Unrelated reinforcement-learning analogies, claims of universal superiority, and selecting comparisons for favorable test outcomes.
- Date range: Sources available at the retrieval cutoff.
- Languages: English primary papers, Chinese internal notes.
- Source types: Original papers, official repositories, local versioned protocols and predictions.
- Known access limits: The literature skill's sibling paper-writing and general-writing files are unavailable. Preserve the existing manuscript structure and use manual prose and PDF verification.

## Comparison axes

1. Laboratory and development-data access.
2. Candidate library, unique queries, training rounds, optimizer steps, example exposures and language-model costs.
3. Development-only selection versus post-selection held-out diagnosis.
4. Training-seed, policy and biological-sample variability.
5. Positive, tied and negative results under the same reporting rules.

## Search map

| Topic | Candidate primary source | Status |
| --- | --- | --- |
| Random search | Bergstra and Bengio, 2012 | Verified original sections 1, 2.1 and 2.2 |
| Model-selection overfitting | Cawley and Talbot, 2010 | Verified original section 4.2 and conclusion |
| Adaptive holdout reuse | Dwork et al., 2015 | Not needed for the bounded claim; not cited |

## Planned synthesis

- Central finding: Separate the access-scenario benefit from same-access configuration search; diagnose rather than erase validation failures.
- Main comparison: Direct, history and non-LLM search with fixed access and budget.
- Most important disclosure gap: Additional data and revised evidence representation do not by themselves demonstrate a stable history-specific advantage.
- Expected limitations: Focused literature verification; fixed biological partitions; conditional confidence intervals.

## Deliverables

- Manuscript format: Revise the existing sectioned BioCoLoop LaTeX project on its rebuttal branch.
- Evidence tables: Merged old comparisons; new full three-seed controls; complete prefix diagnostics.
- Source ledger path: source-ledger.csv.
- Local experiment evidence: local-artifact-ledger.csv (not bibliographic references).
- Claim-evidence matrix path: claim-evidence-matrix.csv.
- Build and publication path: Compiled PDF, source revision and reviewer response on GitHub; no automatic OpenReview submission.
