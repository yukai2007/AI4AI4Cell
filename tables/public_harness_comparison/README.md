# Active public-harness table

The manuscript and the standalone comparison report include
`main_public_harness_three_seed.tex`. It is a grouped three-seed table with
matched local Qwen2.5-7B-Instruct and GPT-5.6 Luna blocks: fixed model,
direct optimization, AI-Scientist-v2, AI-Researcher and BioCoLoop. AI-Scientist-v2 and
AI-Researcher receive laboratory 0, while BioCoLoop receives all ten
laboratories. `snapshot_llm_grouped_three_seed.json` records source hashes, selected
checkpoints, independent verification and typed controller failures;
incomplete cells are marked ($\dagger$ partial, -- unscored) rather than imputed, and the
completed count and typed failure of every such cell is recorded in Section C.2. The final
column reports each method's mean rank over its complete endpoints and its colored change
against the fixed reference.

The other files in this directory are retained as historical artifacts from
earlier adapters. They are not included in the submitted manuscript and must
not be used as the current comparison.
