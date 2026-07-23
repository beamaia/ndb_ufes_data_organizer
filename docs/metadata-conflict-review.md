# Metadata Conflict Review

This is the page I use before making a label claim from the atlas. I am keeping the complete patch-label layer and the reconstructed metadata layer separate because they answer different questions. The report linked below is aggregate and public-safe; it does not expose patch IDs, SAB filenames, or a private crosswalk.

## The short version

The complete NDB-UFES and SAB patch-label sources agree for all 3,763 atlas patches. The conflict is between those complete patch labels and the reconstructed metadata used by the thesis relationship/batch artifacts.

| Layer or status | Rows | What I can say now |
| --- | ---: | --- |
| Complete patch-label sources agree | 3,763 | The NDB-UFES and SAB patch-label fields agree in the validated-linkage output. |
| Reconstructed metadata agrees with the complete patch label | 1,758 | No label disagreement is recorded at this comparison point. |
| Reconstructed metadata disagrees | 1,328 | A downstream label policy is needed before I call one source canonical. |
| Reconstructed metadata is missing | 677 | These rows remain in the full thesis scope but cannot be treated as metadata-labeled by this layer. |
| Atlas metadata-conflict evidence cohort | 1,489 | This broader flag also includes conflicts in other metadata fields, not only patch-label disagreement. |

The last number is intentionally not the sum of only the direct label disagreements. It includes 59 rows whose reconstructed patch label agrees but whose other metadata still triggers the atlas conflict flag.

## Interim use policy

I can make the following policy explicit now, even before the final thesis label decision:

- I use the atlas patch-label layer to describe what the validated-linkage artifact contains. I keep the NDB-UFES and SAB source labels side by side and do not synthesize a new canonical label silently.
- I treat Batch 1 and Batch 2 as the frozen final experiment artifacts. Batch
  3 is an exploratory archive. Anyone reproducing one of these artifacts
  should use its stored labels and grouping fields rather than rewriting them
  from the atlas index.
- I retain the 677 missing-metadata rows in the full thesis scope. An analysis that requires recovered metadata must state its restricted denominator instead of quietly dropping those rows.
- I keep the 1,489 conflict flags as review evidence, not as an automatic exclusion rule. A conflict flag alone does not prove that a patch is unusable.
- For public WSI summaries, I show source-level labels and patch-label counts separately. I do not collapse mixed labels into one WSI diagnosis until the thesis policy is approved.

This is a reproducibility policy, not a final clinical-label policy. It tells me how to avoid changing the current evidence while the scientific decision is still open.

## What the direct label mismatches look like

These are the 1,328 rows where the complete patch label and reconstructed metadata label differ:

| Complete patch label | Reconstructed metadata label | Rows |
| --- | --- | ---: |
| OSCC | Leukoplakia with dysplasia | 66 |
| Leukoplakia with dysplasia | OSCC | 521 |
| Leukoplakia with dysplasia | Leukoplakia without dysplasia | 394 |
| Leukoplakia without dysplasia | OSCC | 64 |
| Leukoplakia without dysplasia | Leukoplakia with dysplasia | 283 |

This pattern tells me that the disagreement is not just a missing-value problem. It is a label-source and label-granularity problem that needs to be resolved at the experiment level.

## Decisions still needed before the next thesis release

I am not treating the complete patch label as automatically canonical for every use, and I am not treating the reconstructed metadata as automatically authoritative. Before the next thesis release, I need to record a policy for each use:

| Decision | Recommended next comparison | Result that must be documented |
| --- | --- | --- |
| Training target | Run a sensitivity comparison using complete patch labels versus reconstructed metadata on the rows where both exist. | Which field enters each experiment and why. |
| Conflict handling | Start with keep-and-flag, then compare the effect of excluding a predeclared review subset. | Row counts before and after the rule. |
| Provenance | Preserve both source fields and add a derived field only after its rule is frozen. | Which source fields remain traceable. |
| WSI/patient summaries | Publish source-level labels and atlas patch-label counts side by side. | How mixed-label WSIs are represented. |
| Missing metadata | Keep missing rows in the full scope; restrict only analyses that explicitly require metadata. | Whether the restriction changes the thesis scope. |

Until those decisions are written down, the safe statement is: **the atlas validates patch-to-WSI placement for all 3,763 patches, while the metadata layers require explicit interpretation.**

## Machine-readable report

- [Metadata-conflict summary (JSON)](assets/atlas/metadata_conflict_summary.json)
- [Atlas Guide](atlas-guide.md#two-linkage-layers)
- [Atlas Gap Map](atlas-gap-map.md)
- [Data Dictionary](data-dictionary.md#validated-wsi-atlas-index)

The report is generated with the public atlas export command:

```bash
uv run python scripts/src/release/build_atlas_public_index.py
uv run python scripts/src/release/validate_atlas_public_index.py
```

The source artifact is `results/phase0/validated_linkage/validated_patch_wsi_linkage.csv`. The report contains aggregate counts only, so the deployment validator can check it without private data.
