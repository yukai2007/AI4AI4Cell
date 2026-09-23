# 2026-09-22 bounded source-provenance follow-up

This note supplements the original audit. It does not change manuscript text, experiment records, or the main bibliography.

## Resolved: scDEBART identity

The official [ICML 2026 poster page](https://icml.cc/virtual/2026/poster/61521) returned HTTP 200. Its JSON-LD explicitly identifies the title, authors Jieun Sung and Wankyu Kim, `creditText=ICML 2026`, `datePublished=2026-05-05`, and `dateModified=2026-07-21`. The active bibliography is correct. The latest retrieval body SHA-256 was `c23cb2ae534c5587ead1917104fe814f0e67ee9a5473dd4fd607e229b6f6e1b4`; a previous retrieval differed because conference HTML is dynamic. The normalized title/authors were identical. OpenReview full text still returned 403, so this check verifies publication identity, not an unseen full text.

## Resolved: DrugBAN implementation pin

`extensions/unified_bio_20260918/drugban_adapter.py` loads the legacy official repository at `/liziqing/yukai/project_collab_auto_research_cell_federated/third_party/DrugBAN`.

- `git rev-parse HEAD`: `9923f8c99959e00263103ff9ac61ba0eaccc8e02` (matches active bibliography).
- `git status --short`: empty (clean).
- Remote: `https://github.com/peizhenbai/DrugBAN.git`, matching the publisher-linked author repository.

This resolves the exact local implementation version; it does not imply that every source file was reviewed.

## VCC: actual data source and split semantics

The manifest chain is:

1. `results/unified_bio_20260918/vcc_corrected/data/manifest.json`.
2. `results/unified_bio_20260918/corrected_features/vcc_corrected/data/manifest.json`.
3. `results/federated_bio_20260918/vcc_pilot/data/manifest.json` (SHA-256 `66cd9aae49f378ad07ae1c1d350f0c37e05d6e4eee55424c9756feaeb6b61919`).
4. `extensions/federated_bio_20260918/prepare_vcc.py` consumes UMM's `outputs/vccpert_adapted_v1_public_cache_20260830_attempt002/model_cache`.
5. Its `curator_receipt.json` identifies `/liziqing/VitaCode_Dataset/CellUMM/VccPert` as the source.
6. Source `00_manifest/_SUCCESS.json` (SHA-256 `4d2ca7af1c46fd07c47a6984e3054316d7ad41fcb054d5325baa374079460ca9`) names `/ssdwork/zhoujingbo/Datasets/vcc_data/adata_Training.h5ad`, 221273 source cells, 18080 genes, 150 observed interventions. Stored source-h5ad SHA-256 is `a09977104fefb622368ca74b50c9d3c1e891733e6c83db07acfca49b0219c02b` (reported by manifest, not rehashed in this audit).

The [official Arc Atlas README](https://github.com/ArcInstitute/arc-virtual-cell-atlas/tree/4f7bb170c61d2fafce70f67db6e52c7d9af1be4b/virtual-cell-challenge) and Python tutorial identify this filename as the **2025 training release**. Current official location: `gs://arc-institute-virtual-cell-atlas/virtual-cell-challenge/2025/train/adata_Training.h5ad`.

UMM first makes an internal 100/50 intervention split from that 150-intervention training file, then divides the 100-intervention portion into train80/validation20. The present inverse-identification task uses these 80+20 interventions (the 20-intervention internal validation partition supplies its test queries). Thus the experiment manifest phrase `original VCC validation20` must be understood and described as **UMM internal validation20**, not official VCC validation. The official [data-generation account](https://arcinstitute.org/news/behind-the-data-virtual-cell-challenge) gives 150/50/100 official training/validation/test interventions. The paper's five-option inverse-identification score is also distinct from official PDS/DES/MAE scores.

Recommended wording: “a VCC-derived H1-hESC genetic-perturbation identification task, constructed from the 2025 public training release with internal intervention-disjoint partitions.” Use `arc2025vcc` from the proposed bib additions. Do not call the result an official VCC leaderboard score.

## Tahoe: actual release and subset

The manifest chain is:

1. `results/unified_bio_20260918/tahoe_drug_corrected/data/manifest.json`.
2. `results/unified_bio_20260918/corrected_features/tahoe_drug_corrected/data/manifest.json`.
3. `results/federated_bio_20260918/tahoe_drug_pilot/data/manifest.json` (SHA-256 `c849819a1737028bc761d1f9196549c5011c8cc26f40955b32123f6a39973b3b`).
4. `prepare_tahoe.py` consumes `UMM_Cell/outputs/joint_multitask_20260910_tahoe_replogle_data_attempt001/conditions.parquet`, `/liziqing/VitaCode_Dataset/CellUMM/Pert/02_bulk/bulk.h5`, and `embeddings/chemical/tahoe100m_drug_smiles.json`.
5. UMM's `audit.json` records its source metadata and splitting; `CellUMM/Pert/00_manifest/source_manifest.parquet` (SHA-256 `cbbc5113b637baac49b5b22ce8531d8537a50cab64295b76dae47ce518e65784`) records 14 local plate files under `/liziqing/vcc/arc-ctc-tahoe100/2025-02-25/h5ad/plate{1..14}_filt_Vevo_Tahoe100M_WServicesFrom_ParseGigalab.h5ad`.

The [official Arc Tahoe tutorial](https://github.com/ArcInstitute/arc-virtual-cell-atlas/blob/4f7bb170c61d2fafce70f67db6e52c7d9af1be4b/tahoe-100M/tutorial-py.ipynb) confirms the 2025-02-25 release. The current bucket is `gs://arc-institute-virtual-cell-atlas/tahoe100M/2025-02-25/`; the previous bucket was retired in March 2026. Local cache paths still use the historical bucket name, which is not an error in release identity. No data was downloaded or uploaded during this audit.

The present task selects A549 (`CVCL_0023`) at 5 micromolar, 307 compounds, split 180/60/67, with canonical-SMILES deduplication, from UMM's designated training pool. It is a derived inverse-identification task, not the whole Tahoe atlas or an original author-defined prediction benchmark. The raw-file content hashes were not recomputed; the lineage is verified from metadata and official release documentation.

For the dataset study use `zhang2025tahoe`, DOI `10.1101/2025.02.20.639398`. The [official data card](https://huggingface.co/datasets/tahoebio/Tahoe-100M) and [Arc README](https://github.com/ArcInstitute/arc-virtual-cell-atlas/blob/4f7bb170c61d2fafce70f67db6e52c7d9af1be4b/tahoe-100M/README.md) directly connect the data to that paper. Full publisher text returned 403; data attribution is supported by these primary release sources. The [bioRxiv API](https://api.biorxiv.org/details/biorxiv/10.1101/2025.02.20.639398) confirms v1 2025-02-24, v2 2025-04-23, v3 2025-05-10. Author lists vary by version: v3 has John D. Thompson and omits Ian Lai; Crossref still includes both. The proposed BibTeX matches **v3**, using the API's author order and Crossref's unabbreviated names.

## Consequence for the external-source experiment

The same metadata-only source manifest confirms HepG2/Jurkat come from `GSE264667_*` (Nadig et al. 2025), whereas K562 and RPE1 are the Replogle 2022 study. This independently supports using both references rather than treating UMM's container label `replogle` as one study.

## Remaining boundaries

All four requested follow-up items are resolved at the publication-identity/release-lineage level. Original scDEBART/Tahoe publisher full text remains inaccessible, and large raw datasets were not byte-rehashed against live cloud objects. No DOI has been guessed; VCC is cited as an official dataset release rather than an invented research-paper citation.
