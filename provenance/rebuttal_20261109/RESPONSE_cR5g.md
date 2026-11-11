# Response to Reviewer cR5g

Thank you for the review and for highlighting the setting we target: distributed training in medicine and biology when laboratories cannot share data. You are right that the original submission lacked random search and that its laboratories were simulated. The revision adds random, Bayesian and exhaustive search for one laboratory, random and Bayesian controls at matched ten-laboratory access, and a ten-laboratory fixed model. It also describes the simulated laboratories more precisely and reports the source-defined experiments with every result, favorable or not.

## 1. No comparison to traditional hyperparameter tuning or random search

**One laboratory.** Appendix D runs random search, GP-EI Bayesian optimization and exhaustive enumeration of the configuration menu on laboratory 0. None reaches the collaborative result. For example:
- DTI AUROC: 90.10 for the conventional controls versus 93.76 for ten-laboratory BioCoLoop.
- Proteomics AP: 20.13 for random search versus 36.99.

On the cell endpoints the gaps are smaller (chance is 20%), and their intervals against single-laboratory random search span zero.

**Ten laboratories.** Appendix E.1-E.2 compares random search without replacement (the exact expectation over all 462 six-design subsets), GP-EI, and direct and history-guided language-model search. All use the same laboratories, panels, configuration library and proposal budget, and failed requests are charged. This study replays a fixed candidate cache with one training seed per task: 42 for DTI and 61 otherwise. Conventional search is competitive:
- Proteomics: all policies tie.
- DTI: GP-EI and direct Luna 94.60, history 94.27.
- Norman: Luna history 23.11 Top-1, direct 22.30, random 22.66 (27 test interventions).

Two follow-ups use separate protocols: E.6 uses gene-disjoint study-cell contexts and 20-round fits; E.9 uses 36 wider recipes, 20-round warm-start fits and pooled selection. We extended both from three to eight seeds for the revision, with the analysis fixed before the new fits:
- E.6: GP-EI 23.28, structured history 22.75, random 22.69, direct 22.34. History beats direct (+0.41, seed-block 95% CI [0.09, 0.84]); against random it is +0.06 (CI [-0.33, 0.46]), with no clear advantage, and it trails GP-EI.
- E.9 (Luna): DTI structured history 94.37 AUROC, direct 94.37, random 94.32, GP-EI 94.29; history beats random by +0.053 (CI [0.050, 0.055]) in all eight seeds. Protein: GP-EI 39.02 AP, direct 38.99, history 38.79, random 38.58; history versus random is +0.21 (CI [-0.04, 0.44]; six wins, two losses).

At least one tested language-model policy exceeds the random expectation in mean in each family; the successful policy varies by task, margins over random are small, and the ranking against GP-EI depends on the task. Section 4.7 says so.

## 2. The laboratories are random splits of one dataset, not independent entities with domain shift

We agree that the main laboratories are simulated from one dataset per task, as in most federated-learning benchmarks (Section 4.2). They are grouped rather than random measurement splits:
- DTI laboratories are defined by canonical compounds;
- proteomic laboratories by compound groups;
- cell laboratories by disjoint training interventions.

No compound or intervention is shared between laboratories. Grouping does not create real batch effects or protocol differences, however, and the revision says so.

To test the case you describe, the source-defined experiments assign a different released study to each laboratory (Section 4.5, Appendix B.2). The results are mixed, and we report all of them:
- Proteomics: one study per laboratory (PTPC, Lin, Ruprecht and decryptE, with shared encoders and source-specific heads). For the revision we extended this study from one to eight seeds, with the analysis registered before the new fits. Target AUROC rises from 72.06 to 74.13 (paired +2.07, seed-block 95% CI [0.65, 3.38]; higher in seven of eight seeds). AP rises from 34.60 to 36.82 in mean (+2.22, CI [-1.19, 5.59]), but only four of eight seeds improve, so the AP gain is seed-dependent. Most of the benefit comes from decryptE; Lin and Ruprecht alone leave the target near its own level.
- DTI (seed 61): adding Davis or Human raises target AUROC from 85.47 to 87.86 and 87.95, but BioSNAP lowers it by 3.03 and all three sources together by 1.18.
- Cells (seeds 61-63): Jiang raises VCC Top-1 from 29.49 to 33.07, while Replogle, Nadig and all three sources lower it by 2.37, 2.55 and 2.15 points.

So the benefit of collaboration across real studies depends on their compatibility. With source-defined laboratories, no search policy beats the fixed design (Appendix E.4). Execution is simulated on shared compute, and we claim no formal privacy guarantee.

## 3. The pipeline's own "direct" search performs worse than a fixed model

"Direct" is configuration search without feedback from earlier evaluations: several candidates are trained and one is kept by development score. "Fixed" is the single default configuration. Both return one predictor; Section 4.2 now defines them.

With one laboratory, direct search, and every other search including BioCoLoop, selects on laboratory 0's small development panel. Its local-development rankings do not transfer reliably to the held-out set: single-laboratory BioCoLoop reaches 20.13 proteomics AP against 25.05 for the fixed model, and 14.15 Norman Top-1 against 25.56 (Appendix D.1). More laboratories enlarge both training data and the development population. Ten-laboratory BioCoLoop exceeds the single-laboratory fixed model on DTI, proteomics, VCC and Tahoe. On Norman, the single-laboratory fixed model (25.56) remains above it (22.25).

## 4. The baselines use one model while BioCoLoop uses ten laboratories

The ten laboratories hold data; they are not an ensemble. BioCoLoop, like every baseline, returns one predictor evaluated on the same test set. Table 1 compares developing that predictor with collaborators against developing it alone, the usual federated comparison. Its caption now says that rows at different access levels compare scenarios, not search methods.

Two controls hold access fixed:
- A ten-laboratory fixed model (Appendix Table D.1). Shared data explain most of the gain on DTI, proteomics and VCC. BioCoLoop adds 1.96 AUROC on DTI and 6.77 Top-1 on Norman, nearly matches on proteomics, ties on VCC and is 3.48 lower on Tahoe.
- A seed-42 pilot (Appendix C.4). Given the same ten laboratories, AI-Scientist-v2 matches BioCoLoop on four endpoints and exceeds it on DTI; repaired AI-Researcher matches on the three endpoints where it was scored.

## 5. "Asking an LLM to turn 4 knobs"

We do not claim a new optimizer over four hyperparameters, and the revision distinguishes BioCoLoop from federated hyperparameter search (including FedEx and evaluations using FedHPO-Bench) on this point. The contribution is a protocol and interface through which laboratories that cannot pool data jointly decide which predictor design to keep, what to try next and how to allocate further training, using only model updates and bounded per-laboratory development evidence. The same interface serves three task families and several research agents. The four-factor library is deliberately small so that the participation, proposal and allocation comparisons stay interpretable. Appendix E.9 widens it to 36 recipes that also vary the head, the loss and the schedule.

The clearest gain from collaborative decisions is allocation. At a fixed 800 aggregation rounds and 160 development evaluations, screening candidates on early collaborative evidence and training the promising ones longer raises Norman Top-1 from 11.48 to 22.32 (+10.84, 95% CI [4.54, 17.73]). Across 12 task-seed pairs it never loses to uniform allocation. Random promotion after the same screening performs comparably (6 wins, 6 losses), so the gain comes mainly from the screening-then-extend schedule (Appendix E.5).

Thank you again; these points led to the controls added in this revision.
