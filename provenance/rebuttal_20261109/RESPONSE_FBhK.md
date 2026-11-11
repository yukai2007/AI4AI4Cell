# Response to Reviewer FBhK

Thank you for the close reading. We are glad that the practical problem, the common interface across task families and the appendix detail were useful, and that the budget-matched allocation result (+10.84 Top-1, 95% CI [4.54, 17.73]) read as a positive finding. Your two questions led to the main additions in this revision. In brief: at matched access, history-guided proposals help on some tasks but are not consistently better than direct, random or GP-EI search. Collaboration improves all five endpoint means, and collaborative design search and training allocation add task-specific gains. The revision reports both sides.

Table numbers changed in the revision. Your Tables B.10, B.12 and B.13 are now Tables B.9(a), B.9(b) and B.10.

## 1. Added value of the loop beyond collaborative fitting, and random/direct search at the same access (Weakness 1, Question 1)

**Collaborative fitting versus the loop.** We added the missing control: the fixed default design (D00) trained by all ten laboratories at the main seeds 42-44 (Appendix Table D.1; the D00 arm of Table A.1). Relative to it, the ten-laboratory loop adds 1.96 AUROC on DTI (93.76 vs 91.80) and 6.77 Top-1 points on Norman (22.25 vs 15.48), where the default design degrades as laboratories are added. It nearly matches the fixed model on proteomics (36.99 vs 37.07) and ties it on VCC (31.54 for both) and is 3.48 points lower on Tahoe. On DTI, proteomics and VCC, most of the gain from one to ten laboratories therefore comes from shared data; collaborative design search adds to it on DTI and Norman. Section 4.3 now states this decomposition.

**Same laboratories, panels, library and budget.** Appendix E.1-E.2 runs random search without replacement (the exact expectation over all 462 six-design subsets), GP-EI, and direct and history-guided Qwen and Luna. All share the ten laboratories, development panels, twelve configurations, six proposal slots and 100-round fits, and failed requests are charged. This is a single-seed study per task (DTI seed 42, others seed 61) replayed from a fixed candidate cache. Results:
- Norman: Luna history 23.11 Top-1, direct 22.30, random 22.66 (27 test interventions).
- DTI: direct Luna and GP-EI 94.60, history 94.27.
- Proteomics: all policies tie.
- VCC: language-model searches and GP-EI 31.50, random 27.53.

Two follow-ups use 20-round fits under separate protocols, summarized in Section 4.7: E.6 uses four gene-disjoint study-cell contexts, and E.9 uses 36 wider recipes, a shared historical seed-42 starting model and pooled development selection. Both originally had three seeds; for the revision we extended each to eight, with the analysis fixed before the new fits and no seeds excluded:
- E.6, gene-disjoint cells: structured history 22.75 Top-1, direct 22.34, random 22.69, GP-EI 23.28, fixed design 21.37. Structured history beats direct by +0.41 (seed-block 95% CI [0.09, 0.84]; four wins, four ties, no losses), is 0.06 points above random in mean (the registered primary contrast; CI [-0.33, 0.46], four wins and four losses, so no clear advantage) and trails GP-EI (-0.52).
- E.9, 36 wider recipes (Luna, eight seeds): on DTI, structured history reaches 94.37 AUROC against 94.32 for random (+0.053, CI [0.050, 0.055], eight wins of eight) and 94.29 for GP-EI; direct search selects the same designs. On protein, history is +0.21 AP above random (CI [-0.04, 0.44]; six wins, two losses), while direct search (38.99) and GP-EI (39.02) are higher. Qwen history is above random on DTI (+0.04) and below it on protein (-0.44).

A separate source-defined study (E.4; seeds 61-63, 100-round fits) finds no search policy exceeding the fixed design.

So at least one tested language-model policy exceeds the random expectation in mean in each family; the successful policy varies by task, and history has no consistent advantage over GP-EI or random search. In the separate 36-design, 24-slot study, final history and direct scores tie on seven of eight comparisons; history is lower on VCC/Luna (20.01 versus 20.23). Section 4.7 and Appendix B.3 now report the original eight ties, one gain and one loss in the main text as well.

**Efficiency and allocation.** The target crossings in Table B.10 are retrospective trajectory diagnostics: every scheduled proposal was executed, so they do not imply saved computation, and the revision now describes them that way. For allocation, a fresh 360-fit study (Table E.5) adds random and score-only promotion. Trajectory promotion beats uniform allocation in four task-seed pairs and loses none, and it beats score-only promotion in four pairs and loses one. Against random promotion it wins six pairs and loses six (mean -0.44). The robust ingredient is screening on early collaborative evidence and then training a few candidates longer; Section 4.4 now says this.

## 2. Development-test divergence in the extended VCC and Tahoe searches (Weakness 2, Question 2)

**Panel construction and weighting.** Development and test use disjoint interventions: VCC has 60/20/20 training/development/test interventions, and Tahoe has 180/60/67. The 20 VCC development interventions form ten panels of two, and the 60 Tahoe compounds form ten panels of six. Every panel holds the same number of interventions and Top-1 is macro-averaged over interventions, so equal panel weighting equals the pooled intervention-macro score exactly. Laboratory weighting and query counts therefore do not explain the divergence.

**Audit.** We reconstructed all 14 selected checkpoints and their 140 development panels, and we reproduced all 80 archived held-out prefix scores (Appendix E.3). The scores reproduce correctly. The roster audit below shows that the development advantage is sensitive to distractor choice, consistent with unstable selection on a small development population; biological development-test shift may also contribute. For example, Tahoe's +5.00 development points correspond to three more correct development compounds, while held-out Top-1 falls from 25.37 to 13.43.

**Roster sensitivity.** We re-scored the same initial and final checkpoints on 20 paired development-roster redraws without retraining. Qwen/VCC's +1.17 development advantage becomes -1.34 ± 7.37 (positive in 6/20 draws), and Tahoe's +5.00 becomes -1.33 ± 4.82 (7/20). Luna/VCC stays positive in 12/20 draws. The large held-out declines thus coincide with development gains that depend on the choice of distractors.

**Retrospective stability-rule replay.** We froze three stricter acceptance rules before this replay's held-out rescoring and applied them to the original fixed proposal traces (Appendix E.3), reusing previously exposed test sets:
- the gain must exceed its across-laboratory SD;
- at least 6 of 10 laboratories must improve;
- both laboratory halves must improve.

All three keep the default design on Tahoe (+3.48 Top-1) but also reject the helpful Norman design (-6.77). The net change is near zero (majority rule: three wins, nine ties, three losses; mean -0.64, 95% CI [-1.28, 0.02]). We therefore keep the original rule and report the trade-off. Testing larger development populations is a natural next step for stabilizing selection.

**Other grouped partitions.** Appendix E.6 uses four Replogle/Nadig study-cell contexts with gene-disjoint partitions (1,208/414/406 training/development/test genes). In the original three seeds every final search exceeds the fitted default (21.43 Top-1), and we report the one small interim reversal (seed 62, slot 2: +0.057 development, -0.257 test). In the eight-seed extension, structured history exceeds the fixed design in every seed, while direct search falls below it once (seed 67).

Thank you again; both questions changed what the paper now reports.
