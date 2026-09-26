# Diagnostics behind the second revision pass (2026-09-26)

Two questions were raised about the reviewed manuscript. Both were answered from the frozen
records; no training, generation or scoring was re-run, and no result was replaced.

## 1. Why the ten-laboratory loop-minus-direct terminal contrast is exactly zero

Source: `paper/tables/strong_v3/snapshot.json` (`federated_direct` vs `federated_loop`),
`results/unified_bio_20260918/<task>/study_v3_seed{42,43,44}/federated_{direct,loop}_proposal_*.json`.

- Ten laboratory: the terminal development-selected primary is identical for both policies in
  **15 of 15** task--seed trajectories (five tasks x three seeds). One laboratory: 13 of 15,
  and the only nonzero loop-minus-direct differences in the whole factorial are two one-laboratory
  VCC seeds, one positive and one negative.
- The proposal traces show the two policies do visit different design sequences in 12 of 15
  trajectories, but both draw six candidates from the same twelve-design menu and the development
  rule retains the best *visited* design, so the terminal recipe coincides. Verified by reading
  `proposal` entries of all six slots per arm and by the shared per-design fit directories
  (`fits/federated_<design-hash>`, reused across arms by design identity).
- The contrast is informative only when the budget truncates the search: at the two-proposal
  prefix the history-guided policy is better in 2 of 15 trajectories, tied in 13 and worse in 0
  (mean +0.78 development-primary points, `tables/strong_v3/loop_prefix.tex`); over the 36-design,
  24-slot library the common development target is reached at slot 4 with feedback against slot 22
  without it (Appendix B).

Consequence for the manuscript: the terminal zero is a protocol property, not a measurement of the
research loop. The run is not evidence that the loop is inert, and it is not evidence that it helps
either. Because the fixed and feedback-free direct references are single-site methods, they are no
longer reported at ten laboratories anywhere in the paper: the ten-laboratory arm is the collaborative
configuration reached under the research loop. Appendix A.1 states the protocol reason for the terminal
identity, Section 4.7 reports search efficiency and Section 4.4 reports training allocation.
