# Public-harness table preview build

Built and visually inspected on 2026-09-24. This standalone two-page preview
shows the matched seed-42 pilot first and the formal three-seed preview second.
The seed-42 AI-Scientist-v2 results are PTPC 37.12, VCC 31.63, Norman 22.74,
and Tahoe 23.88 (metrics multiplied by 100), each tied with BioCoLoop. PTPC,
VCC, and Tahoe are bolded as best; Norman is underlined as second-best.
Other public result cells are N/A,
and both public three-seed rows remain N/A. No formal manuscript, frozen publisher,
runtime, training artifact, or evaluation artifact was modified by this refresh.

After the archival refresh to `formal_v5`, all three preview TeX input hashes
were checked against this receipt and were unchanged. The existing rendered
PDF was therefore retained; changing the queue base alone did not change the
four verified seed-42 cells or the page contents.

## Inputs and output

- Source: `paper/public-harness-preview.tex`
- Page 1 table: `paper/tables/public_harness_preview/main_public_harness_seed42.tex`
- Page 2 table: `paper/tables/public_harness_preview/main_public_harness.tex`
- Output: `paper/output/pdf/public_harness_preview.pdf`
- Temporary log: `paper/tmp/pdfs/public_harness_build/public-harness-preview.log`
- Inspected renderings: `paper/tmp/pdfs/public_harness_preview_poppler-1.png`
  and `paper/tmp/pdfs/public_harness_preview_poppler-2.png`

## Compiler and dependencies

No installation was needed, and no global binary was replaced. The existing
project-local compiler was used:

`/liziqing/yukai/project_collab_auto_research_cell_federated/.tools/tectonic-0.16.0/tectonic`

Compiler SHA-256:
`a6e1ebaba90536e527f2ecd47775a608d9a56bd584efa9f7eee25c1bc7b86349`

The build used only the existing Tectonic cache (`--only-cached`), the repository
ICLR 2027 style, and its local TeX Gyre Termes fonts. Existing bundle caches are
under `/liziqing/yukai/.cache/tectonic` and `/liziqing/yukai/.cache/Tectonic`;
the cached bundle content identity is
`6ffe055852f8faf66c0acbe1a7fb27f87b869a90bad1204f3bf4d9683f597c7c`.

The cached 0.15 compiler was tried first but could not resolve `fontspec.sty`
through its default cached bundle. The existing project compiler above resolved
all packages without network access. The incompatible global compiler was not
used or changed.

Rendering used existing Poppler `pdftoppm` 22.02.0 and its locally cached shared
libraries. PyMuPDF 1.28.0 supplied independent PDF text and vector-rule bounds
checks. No new fonts, packages, or TeX bundles were installed.

## Reproducible commands

Run in `/liziqing/yukai/AI4AI4Cell/paper`:

```sh
FONTCONFIG_FILE=/liziqing/yukai/.local/opt/fontconfig/etc/fonts/fonts.conf \
FONTCONFIG_PATH=/liziqing/yukai/.local/opt/fontconfig/etc/fonts \
/liziqing/yukai/project_collab_auto_research_cell_federated/.tools/tectonic-0.16.0/tectonic \
  --only-cached --keep-logs --outdir tmp/pdfs/public_harness_build \
  public-harness-preview.tex

FONTCONFIG_FILE=/liziqing/yukai/.local/opt/fontconfig/etc/fonts/fonts.conf \
FONTCONFIG_PATH=/liziqing/yukai/.local/opt/fontconfig/etc/fonts \
LD_LIBRARY_PATH=/liziqing/yukai/.local/opt/lo-deps/usr/lib/x86_64-linux-gnu:/liziqing/yukai/.local/opt/poppler/usr/lib/x86_64-linux-gnu:/liziqing/yukai/.local/opt/fontconfig/usr/lib/x86_64-linux-gnu \
/liziqing/yukai/.local/opt/poppler/usr/bin/pdftoppm \
  -r 180 -png \
  tmp/pdfs/public_harness_build/public-harness-preview.pdf \
  tmp/pdfs/public_harness_preview_poppler

cp tmp/pdfs/public_harness_build/public-harness-preview.pdf \
  output/pdf/public_harness_preview.pdf

python -B -m unittest discover -s tools -p test_public_harness_publication.py -v
```

## Inspection result

- Two US-letter PDF pages, each 612 x 792 PDF points.
- Actual table rules span x = 108 to 504 PDF points: exactly 396 points / 5.5
  inches on both pages, matching the manuscript style's text width.
- Zero overfull/underfull box warnings, missing-character warnings, or LaTeX
  warnings in the successful build log.
- Table labels, five metric columns, ranking marks, N/A cells, rules and caption
  are legible and aligned, with no clipping or overlap in the 180-dpi rendering.
- The manuscript's review line numbers remain visible. No layout fix was needed.
- Page 1 correctly shows the tied AI-Scientist-v2 and BioCoLoop PTPC, VCC, and
  Tahoe values in bold and their Norman values underlined; page 2 preserves the
  incomplete three-seed public cells as N/A.
- Twelve unchanged publisher tests passed after the build.

## Input/output integrity

| Artifact | SHA-256 |
|---|---|
| Preview TeX | `b1e97f4574f0cdd296150cb0c199ee8f5ae3c96a242521822cec8b46b7ba77b2` |
| Seed-42 table TeX | `93cb8f67b42ae0da1b6b425a6b205e56b8da06b47625122ff2cad594b969f1a3` |
| Three-seed table TeX | `cf9f97403db49cb96100994b06dffea3f381d0f9bd85f571cd96cdbff5262c5f` |
| Frozen publisher | `d99a84aba14730e4352d4c53f1145c5641ddb8aa8c4ec56905ba8b9be4fdfe68` |
| Preview PDF | `ac136103f1eb6ac0d0bc31bebd4b969dd87dd60f6b1232cd9c1712777676b345` |
