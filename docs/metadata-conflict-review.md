# Metadata Conflict Review

This page separates the complete patch-label layer from the reconstructed
metadata layer because they answer different questions. The linked report is
aggregate and public-safe; it does not expose patch IDs, SAB filenames, or a
private crosswalk.

## The short version

The complete NDB-UFES and SAB patch-label sources agree for all 3,763 atlas patches. The conflict is between those complete patch labels and the reconstructed metadata used by the thesis relationship/batch artifacts.

| Layer or status | Rows | Current interpretation |
| --- | ---: | --- |
| Complete patch-label sources agree | 3,763 | The NDB-UFES and SAB patch-label fields agree in the validated-linkage output. |
| Reconstructed metadata agrees with the complete patch label | 1,758 | No label disagreement is recorded at this comparison point. |
| Reconstructed metadata disagrees | 1,328 | A downstream label policy is needed before one source can be treated as canonical. |
| Reconstructed metadata is missing | 677 | These rows remain in the full thesis scope but cannot be treated as metadata-labeled by this layer. |
| Atlas metadata-conflict evidence cohort | 1,489 | This broader flag also includes conflicts in other metadata fields, not only patch-label disagreement. |

The last number is intentionally not the sum of only the direct label disagreements. It includes 59 rows whose reconstructed patch label agrees but whose other metadata still triggers the atlas conflict flag.

This 59-row metadata cohort is not the separate 59-row public-match
classification difference documented in
[Current Release Facts](release-facts.md#linkage-layer-reconciliation).
The two sets have zero patch rows in common.

## Interim use policy

The following interim policy preserves the current evidence before the final
thesis label decision:

- Use the atlas patch-label layer only to describe what the validated-linkage artifact contains. Keep the NDB-UFES and SAB source labels side by side; do not synthesize a new canonical label silently.
- Treat Batch 1 and Batch 2 as the frozen final experiment artifacts. Batch
  3 is an exploratory archive. Anyone reproducing one of these artifacts
  should use its stored labels and grouping fields rather than rewriting them
  from the atlas index.
- Retain the 677 missing-metadata rows in the full thesis scope. An analysis that requires recovered metadata must state its restricted denominator instead of quietly dropping those rows.
- Keep the 1,489 conflict flags as review evidence, not as an automatic exclusion rule. A conflict flag alone does not prove that a patch is unusable.
- For public source-image summaries, show source-level labels and patch-label counts separately. Do not collapse mixed labels into one source-image diagnosis until the thesis policy is approved.

This is a reproducibility policy, not a final clinical-label policy. Its
purpose is to prevent the evidence from changing while the scientific decision
remains open.

## What the direct label mismatches look like

These are the 1,328 rows where the complete patch label and reconstructed metadata label differ:

| Complete patch label | Reconstructed metadata label | Rows |
| --- | --- | ---: |
| OSCC | Leukoplakia with dysplasia | 66 |
| Leukoplakia with dysplasia | OSCC | 521 |
| Leukoplakia with dysplasia | Leukoplakia without dysplasia | 394 |
| Leukoplakia without dysplasia | OSCC | 64 |
| Leukoplakia without dysplasia | Leukoplakia with dysplasia | 283 |

This pattern shows that the disagreement is not only a missing-value problem.
It is a label-source and label-granularity problem that must be resolved at the
experiment level.

## Decisions still needed before the next thesis release

Neither the complete patch label nor the reconstructed metadata is treated as
automatically authoritative for every use. A policy for each use must be
recorded before the next thesis release:

| Decision | Recommended next comparison | Result that must be documented |
| --- | --- | --- |
| Training target | Run a sensitivity comparison using complete patch labels versus reconstructed metadata on the rows where both exist. | Which field enters each experiment and why. |
| Conflict handling | Start with keep-and-flag, then compare the effect of excluding a predeclared review subset. | Row counts before and after the rule. |
| Provenance | Preserve both source fields and add a derived field only after its rule is frozen. | Which source fields remain traceable. |
| Source-image/case summaries | Publish source-level labels and atlas patch-label counts side by side. | How mixed-label source images are represented. |
| Missing metadata | Keep missing rows in the full scope; restrict only analyses that explicitly require metadata. | Whether the restriction changes the thesis scope. |

Until those decisions are written down, the supported statement is: **the
atlas places all 3,763 patches on linked source images, while the metadata
layers require explicit interpretation.**

## Machine-readable report

- [Metadata-conflict summary (JSON)](assets/atlas/metadata_conflict_summary.json)
- [Atlas Guide](atlas-guide.md#two-linkage-layers)
- [Atlas Gap Map](atlas-gap-map.md)
- [Data Dictionary](data-dictionary.md#source-image-atlas-index)

The report is generated with the public atlas export command:

```bash
uv run python scripts/src/release/build_atlas_public_index.py
uv run python scripts/src/release/validate_atlas_public_index.py
```

The source artifact is `results/phase0/validated_linkage/validated_patch_wsi_linkage.csv`. The report contains aggregate counts only, so the deployment validator can check it without private data.
