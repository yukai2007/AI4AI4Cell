# Response to Reviewer AfJB

Thank you for identifying the relevant prior work and the need to separate model-development benefits from additional laboratory access. We have revised both the positioning and the experimental comparison rather than treating the original main table as evidence for the history mechanism.

## 1. Relation to existing collaborative research systems

The revised related-work section discusses all three systems explicitly. [The Virtual Biotech](https://virtualbiotech.ai/) coordinates specialist agents around biomedical evidence for therapeutic decisions. [AutoScientists](https://arxiv.org/html/2605.28655v1) maintains shared experimental state, including unsuccessful directions, and coordinates subsequent experimentation. [Helmsman](https://arxiv.org/html/2510.14512v2) is directly relevant to automated federated design: its planning, coding and simulation-based diagnosis already connect LLM agents to federated system construction and refinement. We have updated its citation to the ICLR 2026 publication.

BioCoLoop's contribution is the biological model-development interface and its controlled evaluation. Task adapters connect interaction, observed-response proteomic and perturbation predictors to the same local-fitting, development-evaluation and proposal interfaces. The coordinator distinguishes training-example-weighted parameter updates from equal-panel development evidence. Source-specific heads allow studies with different response objectives to contribute to a shared representation while the target development population remains explicit. The evaluation then separates laboratory participation, proposal-history conditioning and training allocation.

This is a narrower and more concrete contribution than inventing shared research memory or automated federated design. We now state the four-factor finite search space directly, and do not portray it as open-ended architecture or source-code discovery. The abstract, introduction and conclusion have been rewritten around the implemented framework and the evidence for each decision.

## 2. Does the history mechanism itself improve search?

We added random search without replacement and fixed GP-EI Bayesian optimization under the same ten-laboratory access as direct and history-guided LLM search. All methods use the same twelve configurations, development panels, initialization and six-proposal cap. The new main-text table reports all five endpoints; Appendix E provides exact random-search variability, shared-first-proposal and realized-fit-count controls.

The result is not a general history advantage. Qwen direct and history select equally scoring models on all five endpoints. Luna history improves Norman from 22.30 to 23.11 Top-1, versus a random expectation of 22.66, but decreases DTI from 94.60 to 94.27 AUROC. GP-EI matches direct Luna on DTI. Proteomics retains the starting configuration, and the VCC score attained by the LLM searches is already attained by the fixed configuration. These controls directly address the alternative explanation that conventional configuration search is sufficient in much of this small design space.

The comparison reuses verified complete candidate fits, with development-only selections sealed before additional scoring. It is a retrospective one-training-seed-per-endpoint study, not new multi-seed evidence. Three-seed source-defined laboratory controls are also reported separately: Qwen history is below direct on both proteomics and cell prediction, and the additional Luna feedback experiment yields only a small protein change and cell ties. We retain these results rather than extending the combined-system gain to unsupported component claims.

## 3. What the revised empirical contribution supports

The original main table is now explicitly an access-scenario comparison, with a Labs column. The new same-access table addresses search quality. Re-evaluation and new development-roster diagnostics identify validation sensitivities associated with poor held-out generalization.

We also completed 360 fresh fits to compare the allocation policy with uniform, ordinary score-only, learning-rate-stratified score-only and random promotion at identical training/evaluation counts. The original Norman gain over uniform is reproduced, but score-only promotion recovers most of it (21.70 versus 22.32), and the exact random-promotion expectation is 22.63. The trajectory policy improves Tahoe relative to both alternatives, while random is better on VCC. We report these mixed controls in Section 4.4 and Appendix E.5 rather than claiming a generally superior new allocation algorithm. The revised contribution is the implemented biological interface and its controlled empirical assessment, with data-access, search and allocation effects distinguished.
