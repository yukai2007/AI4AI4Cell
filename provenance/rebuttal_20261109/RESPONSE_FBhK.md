# Response to Reviewer FBhK

We have added the requested same-access controls and validation diagnostics, and revised the claims to distinguish collaborative access from the value of research history.

## 1. Random and direct search with identical laboratory access

The new main-text search table compares fixed configuration, random search without replacement, GP-EI Bayesian optimization, and direct/history-guided Qwen and Luna search. Every method uses the same ten training laboratories, ten development panels, twelve-design library, initialization rule and checkpoint-selection rule. Searches have six proposal slots after D00 and a maximum of 700 aggregation rounds.

We verified all 60 task/configuration fits and sealed the development-only choices before scoring the additional controls. Exact integration over all 462 six-design subsets gives random search's expected score and policy variability. The study is retrospective and conditional on one training seed per endpoint (42 for DTI; 61 otherwise), not 462 independent training experiments.

The results distinguish the mechanisms clearly. On Norman, Luna history reaches 23.11 Top-1, versus 22.30 for direct Luna and GP-EI and 22.66 in expectation for random search. On DTI, GP-EI/direct Luna instead reach 94.60 AUROC, versus 94.27 for both history methods and 94.45 for random search. On VCC, all LLM rows and GP-EI reach 31.50, but the fixed configuration already reaches 31.50; proteomics is entirely tied. Thus these controls do not establish a general history advantage, and we no longer use the access-scenario table to imply one.

Appendix E also includes a shared-first-proposal random control and controls matching realized fit counts. This matters because Qwen's invalid proposals reduce actual training to 600 rounds for proteomic history search and 500 for both Tahoe searches. In the latter case, random search matched to four valid proposals still reaches 26.30 in expectation, versus Qwen's 25.37. Failure costs are preserved rather than replaced by additional valid proposals.

## 2. Development-test divergence

We reconstructed all 14 distinct checkpoints selected at the recorded VCC/Tahoe prefixes, re-evaluated 140 development panels, and independently rescored all 80 archived prefix test results. The original scores are reproduced.

Aggregation mismatch does not explain these cases. Each VCC development panel contains exactly two interventions and each Tahoe panel six, so equal-panel macro Top-1 is mathematically identical to pooled intervention-macro Top-1. The development sets nevertheless contain only 20 and 60 independent interventions. Qwen/VCC's 1.17-point development gain accompanies an 11.89-point test decrease; Tahoe's gain corresponds to three additional correct development compounds, while test Top-1 falls by 11.94 points.

We added a development-only sensitivity experiment with 20 newly fixed candidate-roster seeds. Each roster resamples four distractors within the same development pool and shuffles option order; initial and already selected final checkpoints receive identical rosters. No model is trained or reselected. Qwen/VCC's original +1.17-point advantage becomes -1.34 ± 7.37 points across rosters, positive in 6/20 draws; Tahoe's +5.00 becomes -1.33 ± 4.82, positive in 7/20. These are roster-draw standard deviations, not training-seed or biological replication uncertainty.

This identifies sensitivity to the fixed comparison sets, alongside limited development intervention coverage. It does not establish the separate causal contributions of repeated selection and intervention distribution shift. The new rosters reuse the original development interventions; robustness across independently regrouped train/development/test partitions remains unestablished.

## 3. Allocation controls and revised conclusions

Sections 4.3 and 4.7 now distinguish the access scenario from same-access search. Section 4.8 diagnoses the validation failure, and the efficiency discussion retains both Norman's favorable and Tahoe's unfavorable retrospective examples.

We also completed 360 fresh fits comparing uniform, score-only, learning-rate-stratified score-only, random and trajectory-based allocation, each at 800 rounds and 160 development evaluations. This reproduces the original 10.84-point Norman gain over uniform. However, score-only promotion reaches 21.70 and the exact random-promotion expectation is 22.63, versus 22.32 for the trajectory policy. On Tahoe the trajectory policy is better (22.89 versus 20.90 for score-only and 21.95 for random), while random is better on VCC. Section 4.4 and Appendix E.5 therefore attribute no universal advantage to the trajectory criterion. These results remain separate from LLM proposal history throughout the abstract and conclusions.
