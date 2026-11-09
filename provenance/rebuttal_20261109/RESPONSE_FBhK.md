# Response to Reviewer FBhK

Thank you for identifying two questions that need separate evidence: whether history improves search at fixed access and budget, and whether development-selected changes generalize. We have added the requested random/direct controls, a fresh three-seed history-representation experiment, and a direct diagnosis of the validation failures. The original results remain visible in consolidated tables.

## 1. Same ten laboratories, configuration library and search budget (Weakness 1; Q1)

Section 4.7 and Appendix E.1-E.2 now compare random search without replacement, GP-EI, and direct/history-guided Qwen and Luna using the same ten training laboratories, ten development panels, twelve configurations, initialization and checkpoint-selection rule. Each search receives six proposal slots beyond D00, with 100 rounds per fit and a 700-round cap. Random search receives the loop's search budget, not the fixed model's single-fit budget.

We verified all 60 task/configuration fits. Enumerating all 462 six-design subsets gives the exact expected outcome of random search conditional on this cache, with selection based only on development evidence. This is not 462 independent training repetitions. Shared-first-proposal and realized-fit-count controls additionally account for failed LLM proposals; for example, four-valid-proposal random search reaches 26.30 on Tahoe versus Qwen's 25.37 under the same realized fit count.

The comparison identifies a positive case without implying a universal gain: Norman/Luna history reaches 23.11 Top-1, versus 22.30 for direct/GP-EI and 22.66 for random search. DTI favors direct Luna/GP-EI (94.60 versus history's 94.27); proteomics ties throughout. On VCC, direct/history and GP-EI retain the fixed reference at 31.50, while random search averages 27.53. We report all five endpoints and all controls.

The main access-scenario table answers a different question: what a laboratory gains by participating in collaborative research instead of developing a model with only its own measurements. Broader access adds training data, development evidence and local computation. We now distinguish this workflow comparison explicitly from the same-access search table; it is not evidence for history alone.

## 2. Fresh history-representation experiment

Appendix E.6 adds 48 newly trained design/seed fits and new paired Qwen2.5-7B-Instruct search runs. Four study-cell contexts from Replogle and Nadig provide 1,208 training genes, 414 development genes and 406 held-out genes, with gene-disjoint partitions. This is a separate mechanism benchmark, not a replacement score for the original cell endpoints.

Direct, raw-history and structured-history search share the first proposal and six-request budget. Raw and structured history observe the same queried development facts; structured cards explicitly organize configuration changes, reference comparisons and expected-versus-observed outcomes. Direct, structured history, random search and GP-EI each use seven full fits, 16,940 optimizer steps and 532,840 training-example exposures per seed. We report additional LLM costs separately. Raw history has three invalid slots across the three runs, which remain charged rather than silently replaced.

Mean held-out Top-1 is 22.625 for direct, 22.625 for raw history, 22.888 for structured history, 22.668 for random search and 23.152 for GP-EI. Structured versus direct yields two gains and one tie, averaging +0.263 points; its paired gene-cluster 95% interval is [-1.022, 1.568]. Thus the revised representation changes candidate selection and has a positive point estimate, but does not establish stable superiority over simpler search. These complete controls define the scope of our history claim.

The separate 10.84-point Norman result compares training allocation with uniform fitting, not LLM history. New promotion controls show that random promotion reaches 22.63 versus 22.32 for the trajectory policy. We retain that comparison and do not use it as evidence of a unique history mechanism.

## 3. What explains the development-test divergence? (Weakness 2; Q2)

We reconstructed all 14 distinct checkpoints selected in the extended VCC/Tahoe searches, re-evaluated their 140 development panels, and independently reproduced all 80 archived prefix test scores. There is no aggregation mismatch in these cases: each VCC panel contains two development interventions and each Tahoe panel six, so equal-panel macro Top-1 is exactly the pooled intervention-macro score, even when query counts differ.

The development population is small: 20 VCC interventions and 60 Tahoe compounds. Qwen/VCC's +1.17 development points accompanies -11.89 test points; Tahoe's +5.00 development points represents three additional correct development compounds, while test performance decreases by 11.94 points. To test dependence on the option sets, we evaluated the same initial/final checkpoints on 20 paired development-roster redraws, without training or reselection. Their mean advantages become -1.34 and -1.33 points, positive in only 6/20 and 7/20 redraws. This is direct evidence of roster sensitivity, not proof that one particular cause explains all failures. Finite-sample selection instability is a known model-selection concern [Cawley and Talbot, 2010](https://jmlr.org/papers/v11/cawley10a.html).

The larger follow-up retains every development/test prefix for all methods and three seeds. All final search outcomes exceed their fully fitted D00 references, so the earlier large terminal decreases do not recur. A small interim reversal remains: in seed 62, raw and structured history select D05 at slot 2, improving development by 0.057 points but reducing test by 0.257; later selections recover. A context-specific reversal also remains on K562. Because the data, response panel and candidate library differ, we do not attribute this change to feedback formatting alone or claim that selection error is eliminated. The follow-up supplies a new gene-disjoint study, not repeated regroupings of the original VCC/Tahoe partitions.

## 4. What changed in the manuscript

Appendix E.7 also adds 40 fresh fixed-design fits, rotating the single participating laboratory through all ten identities on proteomics and the three cell endpoints. Laboratory 0 is below the independent-laboratory mean for protein/VCC but is the best on Norman, showing why its identity cannot stand for all laboratories. This one-seed CPU sensitivity is reported separately from the three-seed GPU workflow table; it does not substitute for rotating every controller or for the same-ten-laboratory search comparison.

The original B.10/B.12 outcomes are consolidated into two clearly separated protocol panels; B.11/B.13 trajectory statistics are consolidated likewise. All positive, tied and negative outcomes remain. The targets are explicitly retrospective, and all six or 24 slots were executed: earlier target attainment is not described as realized compute saving. A redundant two-source pilot table is condensed into text while retaining every source-specific result and the absence of a loop gain. Sections 4.7-4.8 and Appendix E now connect the matched controls, fresh experiment and validation diagnosis directly to the two questions raised in your review.
