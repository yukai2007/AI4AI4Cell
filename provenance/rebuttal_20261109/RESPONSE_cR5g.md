# Response to Reviewer cR5g

Thank you for the concrete concerns about conventional tuning, laboratory heterogeneity and the interpretation of the baseline comparison. We have added the missing controls and reorganized the evidence around those questions.

## 1. Conventional hyperparameter optimization

The revision adds a same-access table comparing random search without replacement, fixed GP-EI Bayesian optimization, direct LLM search and history-guided LLM search. All use ten laboratories, identical development panels, the same twelve-design library and a six-proposal cap after the initial configuration. Exact enumeration of 462 candidate subsets reports random search's expected outcome and search-policy variability; it does not count these subsets as independent training seeds.

For example, DTI AUROC is 94.60 for GP-EI, 94.45 in expectation for random search and 94.27 for history-guided search. On Norman, Luna history reaches 23.11 Top-1, versus 22.30 for GP-EI/direct and 22.66 for random search. Other endpoints include ties and cases where the fixed configuration is already competitive. Thus the new evidence supports task-dependent search behavior, not general superiority to conventional tuning. We also report controls matching the actual number of valid fits when an LLM proposal fails.

## 2. Laboratories defined by different studies

The main ten-client experiment partitions one source dataset; it is not ten independently operated institutions. We now make this explicit and separate it from the source-defined laboratory experiments.

The proteomic experiment treats PTPC, Lin, Ruprecht and decryptE as four laboratories. Their different response objectives use source-specific heads and a shared representation; the same target development panels select checkpoints. In the fixed-design transfer comparison, adding the three external studies increases target AP from 34.41 to 37.53.

The cell control compares four same-source VCC groups with VCC, Replogle/K562, Nadig/HepG2 and Jiang/IFNB/K562 as four source-defined laboratories. Each arm has four laboratories and 60 training interventions, with the same target anchor. The external-source arm scores 28.82 Top-1 versus 30.70 for the same-source arm. Underlying cell counts and gene panels remain different and are documented. DTI likewise reports each auxiliary source: Davis/Human improve the fixed target model, while BioSNAP and the combined-source setting do not.

These experiments test real differences between released studies, although execution is simulated on one host. We do not present heterogeneous data as automatically beneficial. Appendix E also reports the completed three-seed direct/history controls within the source-defined protein and cell settings, including their negative results.

## 3. Why direct search can be worse than the fixed model

“Direct” denotes feedback-free LLM configuration search, not training one model once. Every method ultimately deploys one selected predictor; ten laboratories are data holders contributing to fitting, not a ten-model ensemble. Both direct and history search retain the model with the best development score, whereas “fixed” is a single predefined configuration. Retaining a better development model therefore need not retain a better test model.

We investigated this failure rather than changing the reported test selection. Reconstructed VCC/Tahoe predictions show that equal-laboratory and pooled-intervention macro aggregation agree exactly. Small gains on 20 VCC or 60 Tahoe development interventions can accompany much larger test decreases. Re-evaluation under 20 new paired development-option rosters further shows that Qwen/VCC and Tahoe's original development advantages are not stable to distractor/option-order changes. No models were retrained or reselected in this diagnostic.

## 4. Scope and presentation of the contribution

The original access comparison now has an explicit Labs column and is no longer used to attribute the benefit of additional data to the LLM loop. The same-access search table addresses that attribution directly. We describe the method as a common biological model-development interface with four editable configuration factors, distinct from open-ended model invention. Related work now discusses Virtual Biotech, AutoScientists and Helmsman. A separate 360-fit allocation comparison adds ordinary score-only and random promotion: it reproduces the original benefit over uniform allocation but shows that much of it is also attained by simpler policies. The revised conclusion states these results separately from collaborative fitting and proposal history.
