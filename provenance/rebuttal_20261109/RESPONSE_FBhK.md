# Response to Reviewer FBhK

Thank you for identifying two questions that need separate evidence: whether history improves search at fixed access and budget, and whether development-selected changes generalize. We have added the requested random/direct controls, a fresh three-seed history-representation experiment, and a direct diagnosis of the validation failures. The original results remain visible in consolidated tables.

## 1. Same ten laboratories, configuration library and search budget (Weakness 1; Q1)

Appendix E.1-E.2 reports the original matched-access comparison of random search without replacement, GP-EI, and direct/history-guided Qwen and Luna using the same ten training laboratories, ten development panels, twelve configurations, initialization and checkpoint-selection rule. Each search receives six proposal slots beyond D00, with 100 rounds per fit and a 700-round cap. Random search receives the loop's search budget, not the fixed model's single-fit budget.

We verified all 60 task/configuration fits. Enumerating all 462 six-design subsets gives the exact expected outcome of random search conditional on this cache, with selection based only on development evidence. This is not 462 independent training repetitions. Shared-first-proposal and realized-fit-count controls additionally account for failed LLM proposals; for example, four-valid-proposal random search reaches 26.30 on Tahoe versus Qwen's 25.37 under the same realized fit count.

The comparison identifies a positive case without implying a universal gain: Norman/Luna history reaches 23.11 Top-1, versus 22.30 for direct/GP-EI and 22.66 for random search. DTI favors direct Luna/GP-EI (94.60 versus history's 94.27); proteomics ties throughout. On VCC, direct/history and GP-EI retain the fixed reference at 31.50, while random search averages 27.53. We report all five endpoints and all controls.

The main access-scenario table answers a different question: what a laboratory gains by participating in collaborative research instead of developing a model with only its own measurements. Broader access adds training data, development evidence and local computation. We now distinguish this workflow comparison explicitly from the same-access search table; it is not evidence for history alone.

## 2. Fresh history-representation experiment

Appendix E.6 adds 48 newly trained design/seed fits and new paired Qwen2.5-7B-Instruct search runs. Four study-cell contexts from Replogle and Nadig provide 1,208 training genes, 414 development genes and 406 held-out genes, with gene-disjoint partitions. This is a separate mechanism benchmark, not a replacement score for the original cell endpoints.

Direct, raw-history and structured-history search share the first proposal and six-request budget. Raw and structured history observe the same queried development facts; structured cards explicitly organize configuration changes, reference comparisons and expected-versus-observed outcomes. Direct, structured history, random search and GP-EI each use seven full fits, 16,940 optimizer steps and 532,840 training-example exposures per seed. We report additional LLM costs separately. Raw history has three invalid slots across the three runs, which remain charged rather than silently replaced.

Mean held-out Top-1 is 22.625 for direct, 22.625 for raw history, 22.888 for structured history, 22.668 for random search and 23.152 for GP-EI. Structured versus direct yields two gains and one tie, averaging +0.263 points; its paired gene-cluster 95% interval is [-1.022, 1.568]. Thus the revised representation changes candidate selection and has a positive point estimate, but does not establish stable superiority over simpler search. These complete controls define the scope of our history claim.

The separate 10.84-point Norman result compares training allocation with uniform fitting, not LLM history. New promotion controls show that random promotion reaches 22.63 versus 22.32 for the trajectory policy. We retain that comparison and do not use it as evidence of a unique history mechanism.

## 3. Wider recipe choices at the same candidate budget

Appendix E.9 adds 216 fresh fits over 36 recipes and three head-training/controller seeds on DTI and proteomics. Recipes vary the fitted classifier or 32/128-wide residual, BCE versus BCE plus ranking loss, learning rate and constant/cosine scheduling. Every method shares ten laboratories, the original fixed-default seed42 starting predictor, development data and six requests; every valid fit completes 20 rounds. This is a separate warm-start study, conditional on one common historical starting model per task, not three new end-to-end backbone fits. DTI freezes the original TAPB encoder; protein can update its complete observed-response head or learn a residual from all original protein/drug inputs.

Luna structured history reaches DTI AUROC 94.368 versus random's 94.316 (+0.053 points; conditional 95% interval [0.031, 0.077], positive in all three runs). On protein, direct reaches 39.017 AP versus random's 38.655, while structured/raw history reaches 38.572. Thus wider recipes supply above-random model outcomes on both tasks, but the primary history comparison does not win both: protein structured-minus-random is -0.083 points [-2.025, 2.234]. Both Qwen and Luna, fixed/direct/raw/structured/random and GP-EI at two offsets remain visible. Protein direct and the original GP-EI select identical predictors in each seed.

Random search exactly integrates all 1,623,160 six-design subsets; its reported result is a selected single-model expectation. All twelve task/seed/proposer selections are sealed before scoring, and saved predictions independently reproduce all 216 scores. Common historical fitting, feature extraction, the 110-fit development pilot and interrupted engineering calls are separate costs. These original test sets were already exposed, so this follow-up is retrospective rather than a new blind or biological-split confirmation. We retain the unsuccessful protein history contrast and the stronger conventional-search outcomes.

## 4. What explains the development-test divergence? (Weakness 2; Q2)

We reconstructed all 14 distinct checkpoints selected in the extended VCC/Tahoe searches, re-evaluated their 140 development panels, and independently reproduced all 80 archived prefix test scores. There is no aggregation mismatch in these cases: each VCC panel contains two development interventions and each Tahoe panel six, so equal-panel macro Top-1 is exactly the pooled intervention-macro score, even when query counts differ.

The development population is small: 20 VCC interventions and 60 Tahoe compounds. Qwen/VCC's +1.17 development points accompanies -11.89 test points; Tahoe's +5.00 development points represents three additional correct development compounds, while test performance decreases by 11.94 points. To test dependence on the option sets, we evaluated the same initial/final checkpoints on 20 paired development-roster redraws, without training or reselection. Their mean advantages become -1.34 and -1.33 points, positive in only 6/20 and 7/20 redraws. This is direct evidence of roster sensitivity, not proof that one particular cause explains all failures. Finite-sample selection instability is a known model-selection concern [Cawley and Talbot, 2010](https://jmlr.org/papers/v11/cawley10a.html).

The larger follow-up retains every development/test prefix for all methods and three seeds. All final search outcomes exceed their fully fitted D00 references, so the earlier large terminal decreases do not recur. A small interim reversal remains: in seed 62, raw and structured history select D05 at slot 2, improving development by 0.057 points but reducing test by 0.257; later selections recover. A context-specific reversal also remains on K562. Because the data, response panel and candidate library differ, we do not attribute this change to feedback formatting alone or claim that selection error is eliminated. The follow-up supplies a new gene-disjoint study, not repeated regroupings of the original VCC/Tahoe partitions.

## 5. Source-defined panel feedback and remaining selection instability

Appendix E.8 repairs and audits a separate implementation issue in the older source-defined protein/cell adapters. Ten target development panels were averaged inside one worker, so the outer worst-client field equalled the mean instead of the true worst panel. This did not change the primary selection score. A new adapter/reducer/projection version preserves explicit panel labels, primary/loss and dispersion, gives raw/structured cards identical observed facts, and keeps direct free of outcome feedback.

We froze the audit before new development inference and reconstructed every saved best checkpoint: two tasks, twelve designs and three seeds, or 72 checkpoints and 720 labelled panel scores. Primary/loss reproduce exactly; mean and true worst-panel scores differ in all 72 cases. Eight new paired ten-round CPU canaries on D00/D07 preserve training losses, selected rounds, selected weights and final training states. These are engineering checks, not full-budget search repetitions or evidence of a new history gain.

Selection sensitivity remains. With even-indexed panels used to select among the saved checkpoints, cell seeds 61/62 gain 17.13/13.58 points on the proposal subset but lose 2.68/8.54 points on its odd-indexed complement; seed 63 improves both. We retain all six task/seed rows and all 252 five-panel subset diagnostics. Because these checkpoints were originally selected on all ten panels, the complements are descriptive, not independent confirmation. A new selection study must choose checkpoint rounds and candidates without consulting the confirmation panels; robustness across new biological partitions remains unestablished.

## 6. What changed in the manuscript

Appendix E.7 reports 40 fresh fixed-D00 fits over ten laboratory identities and four endpoints, with scores independently reproduced. Laboratory 0 is the best on Norman and below the independent-laboratory mean on protein/VCC. This one-seed diagnostic does not rotate search controllers or address DTI.

Consolidated tables retain all original short/extended outcomes and trajectory diagnostics. All six or 24 slots were executed, so retrospective target crossings are not realized compute savings. Sections 4.7-4.8 and Appendix E distinguish collaborative access, history, allocation and validation evidence.
