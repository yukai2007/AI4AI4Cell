# Queue v6: preserve the context-limited run, continue independent jobs

The four completed AI-Scientist-v2 seed-42 studies are symlinks to their
unchanged, verified `formal_v3` directories. The AI-Researcher/PTPC/seed42
directory is a symlink to the failed `formal_v5` run. No fit, proposal, source
binding, checkpoint or scientific result is rewritten or retried.

The AI-Researcher run ended with the declared 28,000-input-token context limit,
after four proposal slots. It has no selection seal or held-out evaluation and
remains N/A. The controller, transport, language model, training budget and
context limit are unchanged. The only runtime change is to recognize this
exact resource-limit failure in the supervisor's opt-in failure allowlist, so
it does not block independent jobs. Other unknown or infrastructure failures
still stop the queue. All original 30 jobs remain registered.

The completed AI-Scientist-v2 studies account for 3.392174570 reserved GPU-hours.
The failed AI-Researcher run accounts for
`8 * (1790253755.0315301 - 1790253338.8368437) / 3600 = 0.924877081` hours.
Both are adopted exactly once from original receipts. The prior provision is
4.02 hours: the previous 4.0 provision plus 0.02 covering v5's additional
launcher/cleanup overhead (approximately 0.013653247 hours). Initial total is
8.337051651 hours, above v5's final inclusive total of 8.330704898 hours.
The GPU budget is not reset; the cap remains 180 reserved GPU-hours.

The new wall-time limit is 23.75 hours, chosen to end no later than the
original v5 24-hour window. It does not authorize another full day of work.
Earlier engineering artifacts and detailed v5 accounting remain preserved.
