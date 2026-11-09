# Response to Reviewer FBhK: concise posting draft

Thank you. We have added matched-access search controls and directly investigated the validation failures. The revision separates the benefits of collaboration from those of history-guided search.

## Weakness 1 / Q1: matched random and direct search

Section 4.7 and Appendix E.1-E.2 compare random search without replacement, GP-EI, and direct/history-guided Qwen and Luna with the same ten laboratories, development panels, twelve configurations and checkpoint rule. All searches receive six proposal slots after D00 and 100 rounds per fit: a 700-round cap, rather than the fixed model's one-fit budget. Exact integration over all 462 six-design subsets removes random-policy sampling error conditional on the verified training cache. Shared-first-proposal and realized-fit-count controls also account for failed proposals.

Norman/Luna history scores 23.11 Top-1, compared with 22.30 for direct/GP-EI and 22.66 for random search. DTI instead favors direct Luna/GP-EI; proteomics ties. On VCC, direct/history and GP-EI retain the fixed reference at 31.50, versus random search's 27.53. We report every endpoint. The main ten-versus-one-laboratory table now explicitly measures the complete collaboration/access scenario, not a history-only effect.

Appendix E.6 adds a fresh three-seed mechanism experiment with 48 newly trained candidates on four study-cell contexts from Replogle and Nadig. Training/development/test partitions contain 1,208/414/406 distinct perturbation genes. Direct, structured history, random and GP-EI share the 16-design library, six requests, 16,940 optimizer steps and 532,840 example exposures per seed. Structured history reorganizes the same queried facts into reference/configuration differences and expected-versus-observed outcomes.

Held-out Top-1 is 22.625 for direct, 22.888 for structured history, 22.668 for random and 23.152 for GP-EI. Structured-minus-direct is +0.263 points (two gains, one tie), with paired gene-cluster 95% CI [-1.022, 1.568]. The new evidence therefore supports changed decisions and a positive point estimate, not stable superiority. Raw history ties direct; its three failed slots and lower realized training cost are reported. We also distinguish the separate Norman allocation gain from history: random promotion reaches 22.63 versus trajectory promotion's 22.32.

## Weakness 2 / Q2: development-test divergence

We reconstructed 14 selected checkpoints, re-evaluated 140 development panels and independently reproduced all 80 archived prefix test scores. Each VCC panel contains two development interventions; each Tahoe panel six. Equal-panel macro Top-1 consequently equals pooled intervention-macro Top-1 exactly. Aggregation mismatch does not explain the decline.

The development sets contain only 20 VCC interventions and 60 Tahoe compounds. Across 20 new paired option-roster draws, Qwen/VCC's original +1.17-point development advantage becomes -1.34 on average (positive in 6/20 draws); Tahoe's +5.00 becomes -1.33 (7/20). No model is retrained or reselected. This identifies distractor-roster sensitivity alongside limited intervention coverage, without uniquely attributing the failure to repeated selection or biological shift.

The larger follow-up reports every development/test prefix and all three seeds. Every final search outcome improves on its fitted D00 reference, so the earlier large terminal decreases do not recur. A small interim reversal remains: seed 62's raw/structured history gains 0.057 development points but loses 0.257 test points at slot 2, then recovers. Context-specific reversals also remain. This is a separate gene-disjoint study, not repeated regroupings of the original splits or proof that one change eliminates selection error.

Appendix E.8 repairs the older source-defined adapters' lost panel diagnostics: 72 saved checkpoints reproduce primary/loss exactly, now retaining 720 labelled panel scores; eight paired ten-round CPU canaries preserve training and selected weights. This is an engineering audit, not a new history-effect estimate. Fixed complementary development-panel diagnostics still reverse on two cell seeds, and reused all-panel-selected checkpoints prevent interpreting the complements as independent confirmation. Robustness across new biological partitions remains unestablished.

Original B.10/B.12 results are consolidated into separate protocol panels, and B.11/B.13 trajectory summaries are merged without dropping unfavorable outcomes. We explicitly label targets as retrospective: all six or 24 slots were executed, so earlier crossing is not realized compute saving. The revised claims follow these controlled results rather than the unequal-access main comparison.
