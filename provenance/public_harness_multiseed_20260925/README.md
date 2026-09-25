# Public-harness comparison: three-seed delivery

This record publishes the matched public-controller comparison used in the
main manuscript table. The comparison uses the same held-out scorer, twelve
registered designs, six-candidate cap and 100-round candidate fits for every
row. Qwen2.5-7B-Instruct is the common research-model backend. Fixed, direct,
AI-Scientist-v2 and AI-Researcher receive laboratory 0 only; BioCoLoop uses
the ten-laboratory collaborative protocol.

The published values are means and sample standard deviations over seeds
42--44. A public-controller run that terminates before a valid held-out
selection is sealed is retained as a typed failure and shown with its
completed count `(n/3)`; it is not imputed or ranked. The source snapshot and
all per-seed bindings are in
`tables/public_harness_comparison/snapshot_multiseed.json`.

The supervisor verified 14 runs directly. Four DTI launcher failures were
recovered with the registered TAPB virtual environment and independently
rescored with unchanged seals and checkpoint hashes. Two native controller
failures remain in the published record: AI-Researcher on VCC (seed 43) and
AI-Scientist-v2 on Tahoe (seed 43). These are execution outcomes, not scores.

The final manuscript, standalone comparison report and statistical supplement
were rebuilt after publication. The source test suite passes 155 tests; the
main text ends on page 9, and the PDF visual review found no clipping or
overlap in the comparison table or supplement.
