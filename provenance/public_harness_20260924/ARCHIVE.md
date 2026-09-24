# Public-harness implementation snapshot

`runtime_source/` contains a source snapshot of the new, task-adapted baseline
implementation. Its canonical runtime location is
`AI4AI4Cell/extensions/public_harness_20260924/`; restore that layout before
running it. The snapshot is not a second training implementation.

Existing task adapters, prepared data, model weights and native task runtimes
remain in the project and are referenced by the per-run manifests. They are
not duplicated here. Likewise, clone the two official repositories at the
pinned commits in `run_baseline.py`; their complete upstream trees are not
vendored into the paper repository.

The AI-Scientist-v2 license is included as `AI-Scientist-v2.LICENSE`. See the
baseline protocol for source attribution and scope of use. AI-Researcher has
MIT metadata but no LICENSE text in the pinned checkout; no replacement
license has been invented.

Paper-side tooling:

- `tools/publish_public_harness.py` verifies new results and builds the separate
  table preview, leaving the original manuscript and six-arm ablation intact.
- `public-harness-preview.tex` renders the preview at the manuscript's width.
- `output/pdf/public_harness_preview.pdf` is a layout preview, not a replacement
  submission PDF. Pending scores are N/A.

Test results are software checks, not measured biological performance. Actual
benchmark completion requires a finished native research trace, fresh fits,
sealed development selection, held-out predictions and independent rescoring.
