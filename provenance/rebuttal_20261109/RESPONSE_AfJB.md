# Response to Reviewer AfJB

Thank you for the expert review, for pointing us to The Virtual Biotech, AutoScientists and Helmsman, and for your note on the matched-training-budget allocation experiment. We agree with your reading of the single-laboratory tables and of Section 4.7. The revision does not dispute these results. It clarifies the method's purpose: enable laboratories that cannot pool data to develop a predictor together, and measure the benefit relative to developing it alone. It also adds the control needed to separate shared data from collaborative design search.

Tables A.1-A.3 keep their numbers. The ten comparisons you cite from Section 4.7 are reported in Section 4.7 and in Appendix B.3.

## 1. Methodological novelty relative to The Virtual Biotech, AutoScientists and Helmsman

The revised related work discusses all three. In The Virtual Biotech and AutoScientists the collaborators are AI agents working on data they can access, and they share evidence, programs and experiment logs. In BioCoLoop the collaborators are data-holding laboratories. Each trains candidates on its own data and scores them on its own development panels, and only model updates and bounded per-laboratory evidence leave the site. Helmsman is directly related prior work: its agents synthesize and debug federated-learning system code in simulation. BioCoLoop instead keeps the federated protocol fixed and uses the laboratories' evidence to decide which predictor design to keep, what to try next and which candidates to train longer.

The revision also discusses federated hyperparameter search (FedEx), architecture search (FedNAS) and the FedHPO-Bench benchmark. FedEx and FedNAS optimize a predefined numerical space with a fixed algorithm; BioCoLoop contributes a common proposal, fitting and development-evidence interface that supports different biological task models and research agents. As a check of that interface, a seed-42 pilot in which AI-Scientist-v2 drives BioCoLoop's ten-laboratory interface (Appendix C.4) reaches 95.07 versus 94.60 DTI AUROC and matches BioCoLoop on the other four endpoints.

We do not claim the first agentic federated framework. The contributions we claim are:
- the collaborative model-development setting and its interface across three biological task families;
- early-evidence allocation, which improves Norman Top-1 by 10.84 points (95% CI [4.54, 17.73]) at matched training and evaluation budgets;
- controlled experiments that separate laboratory participation, the proposal policy and training allocation.

## 2. With one laboratory, BioCoLoop is essentially identical to direct optimization (Tables A.1-A.3)

Your reading is correct. Appendix D.1 now explains it. With one laboratory, every strategy, BioCoLoop included, selects designs on laboratory 0's small development panel alone. The designs selected differ across strategies and seeds but score similarly, and on proteomics and the cell tasks they fall below the single-laboratory fixed model (for example, Norman 14.15 for BioCoLoop versus 25.56 fixed), and their local-development rankings do not transfer reliably to the held-out set. At ten laboratories, the main direct and history-guided workflows attain the same primary score in every run, although their selected designs can differ. History is therefore not what separates the rows in these tables.

What separates them is collaboration. Changing only participation from one laboratory to ten, the same workflow moves:
- DTI AUROC from 89.89 to 93.76;
- proteomics AP from 20.13 to 36.99;
- VCC, Norman and Tahoe Top-1 from 20.22, 14.15 and 15.42 to 31.54, 22.25 and 22.39.

All five improve in mean (Appendix D.2). The three cell intervals against single-laboratory random search span zero, and Norman and Tahoe final Top-1 remain close to the 20% chance level. The secondary endpoints follow the same general pattern.

We also added a ten-laboratory fixed model (Appendix Table D.1) to separate shared data from design search. Relative to it, BioCoLoop adds 1.96 AUROC on DTI and 6.77 Top-1 on Norman, where the default design falls from 25.56 to 15.48 as laboratories are added. It nearly matches on proteomics (36.99 versus 37.07 AP), ties on VCC and is 3.48 lower on Tahoe. On DTI, proteomics and VCC, most of the collaboration gain is thus shared data; design search adds to it on DTI and Norman. Laboratory identity matters as well. A seed-42 fixed-model sensitivity over laboratory identities (Appendix E.7, Table E.9) places laboratory 0 below the average on proteomics and VCC; the mean VCC score across the ten single-laboratory fits is 32.50, compared descriptively with the main three-seed ten-laboratory mean of 31.54.

## 3. Table 1 gives BioCoLoop ten laboratories while the AI-scientist baselines use one

This is intended, and the revision now labels it clearly. Table 1 compares collaborative development with a laboratory working alone, which is the usual comparison in federated learning (cited in Section 4.2). Its caption now says that rows at the two access levels compare complete scenarios, not search methods. Section 4.3 explains why the reference row is the single-laboratory fixed model rather than the single-laboratory BioCoLoop run used elsewhere: the fixed model is the stronger local baseline (Norman 25.56 versus 22.25 for ten-laboratory BioCoLoop). Two additional controls separate collaborative fitting from design search and test another controller at matched access:
- the ten-laboratory fixed model above;
- the seed-42 pilot (Appendix C.4), which gives both agents the same ten laboratories. AI-Scientist-v2 matches BioCoLoop on four endpoints and reaches 95.07 versus 94.60 DTI AUROC; repaired AI-Researcher matches on proteomics, VCC and Norman, with DTI and Tahoe unscored. This supports the interface's portability across controllers.

## 4. In Section 4.7, eight of ten comparisons show identical final performance

We agree, and Section 4.7 now states this in its first paragraph. The original same-access study (single seed) has eight ties, a Norman gain for Luna history (+0.81) and a DTI loss (-0.33). In the separate 36-design, 24-slot study, final history and direct scores tie on seven of eight comparisons; history is lower on VCC/Luna (20.01 versus 20.23).

Two follow-ups use 20-round fits under separate protocols: E.6 (gene-disjoint study-cell contexts) and E.9 (36 wider recipes, a shared historical seed-42 start and pooled development selection). For the revision we extended both from three to eight seeds, with the analysis fixed before the new fits and no seeds excluded:
- E.6: structured history reaches 22.75 Top-1 against 22.34 for direct (paired +0.41, seed-block 95% CI [0.09, 0.84]; four wins, four ties, no losses) and 21.37 for the fixed design (eight wins of eight). Against random search, the registered primary contrast, it is +0.06 in mean (CI [-0.33, 0.46]; four wins, four losses), so no clear advantage; it trails GP-EI (23.28).
- E.9 (Luna): on DTI, structured history beats random by +0.053 AUROC (CI [0.050, 0.055]; eight of eight seeds) and GP-EI in every seed, but direct search selects the same designs, so history adds nothing there. On protein, history is +0.21 AP above random (CI [-0.04, 0.44]; six wins, two losses) and below direct search (-0.20, CI [-0.42, -0.01]) and GP-EI. Every history search exceeds the fitted starting design in all eight seeds.
- Two retrospective E.9 checks without new fits: most Qwen failures listed the changed fields incorrectly for a valid design; canonicalizing that redundant metadata cuts invalid requests from 102 to 5 of 288, after which Qwen selects the same DTI predictors as Luna in every seed and its direct search reaches 38.98 protein AP (random 38.58, GP-EI 39.02). Replacing the pooled development score by laboratory-level selection rules lowers protein AP in all eight seeds, so pooling evidence across laboratories is the better selection signal.
- E.4 (seeds 61-63, 100-round fits, source-defined laboratories): no search policy exceeds the fixed design.

At least one tested language-model policy exceeds the random expectation in mean in each family, but the successful policy varies by task. History is therefore one task-dependent component: where the evidence is clearest it improves on feedback-free proposals, but it is not consistently better than GP-EI or random search. The paper no longer presents it as the source of the main gain.

## 5. Allocation

In a fresh 360-fit study (Appendix E.5), trajectory promotion beats uniform allocation in four task-seed pairs and loses none. It beats score-only promotion four times and loses once, and it splits six-six against random promotion (mean -0.44). On Tahoe, trajectory promotion reaches 22.89 versus 20.90 for score-only and 21.95 for random, a task-specific benefit of the trajectory rule. The robust ingredient is screening candidates on early collaborative evidence and then training a few of them longer. The abstract and Section 4.4 now describe the result this way.

Thank you again; your comments made the paper's claims clearer.
