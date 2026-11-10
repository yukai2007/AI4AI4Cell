# Response to Reviewer cR5g

Thank you for the concrete concerns about conventional tuning, laboratory heterogeneity and the interpretation of the baseline comparison. We have added the missing controls and reorganized the evidence around those questions.

## 1. Conventional hyperparameter optimization

Appendix E.1-E.2 adds the original same-access table comparing random search without replacement, fixed GP-EI Bayesian optimization, direct LLM search and history-guided LLM search. All use ten laboratories, identical development panels, the same twelve-design library and a six-proposal cap after the initial configuration. Exact enumeration of 462 candidate subsets reports random search's expected outcome and search-policy variability; it does not count these subsets as independent training seeds.

For example, DTI AUROC is 94.60 for GP-EI, 94.45 in expectation for random search and 94.27 for history-guided search. On Norman, Luna history reaches 23.11 Top-1, versus 22.30 for GP-EI/direct and 22.66 for random search. Other endpoints include ties and cases where the fixed configuration is already competitive. Thus the new evidence supports task-dependent search behavior, not general superiority to conventional tuning. We also report controls matching the actual number of valid fits when an LLM proposal fails.

A separate three-seed, gene-disjoint study adds 48 fresh fits over 16 designs and four Replogle/Nadig study-cell contexts (Appendix E.6). With six requests and matched fitting counts, structured history reaches 22.888 Top-1, direct/raw 22.625, random 22.668 and GP-EI 23.152. Structured-minus-direct is +0.263 points, with a conditional paired gene-cluster 95% interval [-1.022, 1.568]. We report every control and do not claim that this study establishes superiority to ordinary tuning.

## 2. Laboratories defined by different studies

The main ten-client experiment partitions one source dataset; it is not ten independently operated institutions. We now make this explicit and separate it from the source-defined laboratory experiments.

The proteomic experiment treats PTPC, Lin, Ruprecht and decryptE as four laboratories. Their different response objectives use source-specific heads and a shared representation; the same target development panels select checkpoints. In the fixed-design transfer comparison, adding the three external studies increases target AP from 34.41 to 37.53.

The cell control compares four same-source VCC groups with VCC, Replogle/K562, Nadig/HepG2 and Jiang/IFNB/K562 as four source-defined laboratories. Each arm has four laboratories and 60 training interventions, with the same target anchor. The external-source arm scores 28.82 Top-1 versus 30.70 for the same-source arm. Underlying cell counts and gene panels remain different and are documented. DTI likewise reports each auxiliary source: Davis/Human improve the fixed target model, while BioSNAP and the combined-source setting do not.

These experiments test real differences between released studies, although execution is simulated on one host. We do not present heterogeneous data as automatically beneficial. Appendix E also reports the completed three-seed direct/history controls within the source-defined protein and cell settings, including their negative results.

Appendix E.8 separately audits a repaired feedback payload for these source-defined adapters. Originally, ten target panels were averaged inside one returning worker, so the outer worst-client field incorrectly described that mean rather than the true worst panel. The repair retains panel labels, scores and dispersion without changing primary/loss selection. Reconstructing 72 saved checkpoints yields identical primary/loss and restores 720 panel scores; eight paired ten-round CPU canaries preserve training trajectories and selected weights. The published source-defined search results remain unchanged, and a search benefit from this repair has not yet been measured.

## 3. Why direct search can be worse than the fixed model

“Direct” denotes feedback-free LLM configuration search, not training one model once. Every method ultimately deploys one selected predictor; ten laboratories are data holders contributing to fitting, not a ten-model ensemble. Both direct and history search retain the model with the best development score, whereas “fixed” is a single predefined configuration. Retaining a better development model therefore need not retain a better test model.

We investigated this failure rather than changing the reported test selection. Reconstructed VCC/Tahoe predictions show that equal-laboratory and pooled-intervention macro aggregation agree exactly. Small gains on 20 VCC or 60 Tahoe development interventions can accompany much larger test decreases. Re-evaluation under 20 new paired development-option rosters further shows that Qwen/VCC and Tahoe's original development advantages are not stable to distractor/option-order changes. No models were retrained or reselected in this diagnostic.

The new source-defined panel diagnostic also retains mixed outcomes. Selecting among saved checkpoints on five fixed panels improves cell seeds 61/62 by 17.13/13.58 points on those panels but decreases the complementary five by 2.68/8.54 points. The checkpoints were already selected using all ten panels, so this is descriptive evidence of sensitivity, not independent confirmation or a new biological split. The larger gene-disjoint study improves all terminal searches over their fitted D00 references but still includes an interim and a context-specific development/test reversal; validation error is not eliminated.

## 4. Scope and presentation of the contribution

The original access comparison now has an explicit Labs column and is no longer used to attribute the benefit of additional data to the LLM loop. The same-access search table addresses that attribution directly. We describe the method as a common biological model-development interface with four editable configuration factors, distinct from open-ended model invention. Related work now discusses Virtual Biotech, AutoScientists and Helmsman. A separate 360-fit allocation comparison adds ordinary score-only and random promotion: it reproduces the original benefit over uniform allocation but shows that much of it is also attained by simpler policies. The revised conclusion states these results separately from collaborative fitting and proposal history.

We additionally fitted fixed D00 independently at every laboratory identity on four endpoints: 40 fresh CPU fits at one seed (Appendix E.7). Laboratory 0 is the best on Norman and below the independent-laboratory mean on protein/VCC. We therefore report the full identity distribution separately from the original multi-seed workflow comparison. Full controller rotations, the DTI rotation and one-laboratory training matched to ten-laboratory optimizer steps remain outstanding; equal communication rounds alone do not equalize computation.

## 5. Increased recipe freedom under matched access and request budgets

Appendix E.9 expands the library to 36 recipes, with 216 fresh fits over two tasks and three head-training/controller seeds. Besides learning rate, the search can choose the original fitted head or a 32/128-wide residual, ordinary BCE or BCE plus ranking loss, and constant/cosine scheduling. DTI adapts the classifier on the same frozen original TAPB encoder; protein can update the complete original observed-response predictor or learn a residual from all original inputs. This warm-start comparison is separate from the original end-to-end study. Each policy has the same ten laboratories, development rows, six requests and 20 rounds per valid fit; equal steps/exposures do not imply equal FLOPs across head choices.

Luna reaches 94.368 DTI AUROC in direct/raw/structured modes versus random's 94.316. Protein direct reaches 39.017 AP versus random's 38.655, whereas structured/raw history reaches 38.572. Random exactly integrates all 1,623,160 six-design subsets, and both original GP-EI and an additional zero-offset GP-EI control are retained. Original GP-EI matches protein direct using the same selected predictors. We therefore report improved model-performance options without recasting ordinary tuning as a unique history benefit. All twelve selections are sealed and all 216 scores independently verified; these historically exposed tests remain retrospective, not an independent new split.
