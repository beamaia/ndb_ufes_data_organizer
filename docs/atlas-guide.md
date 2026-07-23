# Atlas Guide

This page is the short, public-facing way into the **NDB-UFES/SAB
Patient-First Patch-to-WSI Atlas**. The sanitized atlas is released as
`NDB_UFES_SAB_atlas_public.pdf` at the repository root. It is not copied into
the wiki payload: the 587-page PDF repeats a full evidence panel for every
validated WSI and would exceed the site's 55 MB release gate.

**Public artifact reviewed:** `NDB_UFES_SAB_atlas_public.pdf`, reviewed
23 July 2026.

!!! info "Download the full public atlas"
    [Download `NDB_UFES_SAB_atlas_public.pdf`](https://github.com/beamaia/ndb_ufes_data_organizer/raw/refs/heads/main/NDB_UFES_SAB_atlas_public.pdf)
    from the repository root. It is the direct 84.5 MB Word PDF export with no
    post-export compression.

## What the atlas is for

I use the atlas to answer one practical question: **which patches belong to which WSI and patient/case grouping, and what evidence supports that link?** It is an inspection and validation artifact. It is not a diagnostic model result, and its similarity measures should not be read as diagnosis scores.

The atlas is organized in this order:

1. definitions and a validated-linkage summary;
2. dataset sources and their roles;
3. a short explanation of how to read a WSI entry;
4. same-WSI patch-evidence measures;
5. the full validated WSI atlas, grouped by patient/case prefix.

## Atlas snapshot

| Atlas item | Current atlas value | How I interpret it |
| --- | ---: | --- |
| Patch rows | 3,763 / 3,763 | Every patch represented in this atlas is assigned to a validated WSI ID. |
| Recovered coordinates | 3,763 / 3,763 | Every represented patch has coordinates used to place it on the WSI context figure. |
| Validated WSI groups | 251 | 203 groups have public NDB-UFES + SAB evidence; 48 are SAB-only recovered WSI groups. |
| Patient/case groups | 64 | The atlas keeps related WSI entries together for review. |
| Patch-label agreement | 3,763 / 3,763 | The atlas reports agreement for the labels carried by its patch records. |

These are atlas-level values. They should not be substituted automatically for the current thesis-batch or SAB-linked-subset counts elsewhere in this wiki. The reconciliation is tracked in [Atlas Gap Map](atlas-gap-map.md).

## Two linkage layers

The 3,763 and 3,086/677 numbers describe different questions, so I keep both instead of forcing one to replace the other.

| Linkage layer | Current result | What it means |
| --- | ---: | --- |
| Atlas validated WSI linkage | 3,763 patches assigned to 251 validated WSI IDs; all 3,763 have recovered coordinates. | Pixel-containment evidence places every patch in a validated WSI context. This is the layer used by the atlas. |
| Thesis relationship metadata linkage | 3,086 rows with recovered public metadata linkage; 677 rows without it. | The current relationship table records whether the thesis batch has public NDB/SAB metadata linkage for each patch. Missing metadata rows remain in the full thesis scope. |
| Patch-label agreement | 3,763 / 3,763 | The complete patch-label sources agree between NDB-UFES and SAB in the validated-linkage output. This is separate from the 677 rows whose reconstructed thesis metadata is missing and the 1,328 rows where reconstructed metadata differs from the complete patch-label source. |

The authoritative atlas summary is `results/phase0/validated_linkage/validated_linkage_summary.json`. The authoritative thesis relationship summary is `results/phase3/current_thesis_batches/relationship_update_summary.json`. The [Atlas Index](atlas-index.md) packages the public atlas layer without the LAB crosswalk.

## The three levels I keep separate

| Level | Meaning in the atlas | Wiki implication |
| --- | --- | --- |
| Patient | A public or pseudonymous patient-level grouping when the evidence supports grouping several WSIs or patches. | Do not infer patient identity from clinical metadata alone. |
| Case | A pseudonymous patient/case grouping in the public PDF. The LAB source can expose a raw SAB case prefix. | Publish only the numbered public grouping; keep raw SAB case prefixes in the ignored LAB artifact. |
| Validated WSI | The repaired WSI identity used after duplicate collapse and patch-to-WSI linkage. | This should become the canonical join key for an atlas-backed public data dictionary. |

## How to read one WSI entry

Each WSI entry follows the same compact sequence:

- a metadata panel with source, WSI labels, patch count, and patch labels;
- a WSI context figure showing where recovered patch boxes sit on the larger image;
- a color strip that acts only as a patch-label key;
- patch thumbnails labeled by patch ID and diagnosis;
- a same-WSI evidence summary.

The evidence summary describes redundancy and overlap inside one WSI. For `n` patches, the theoretical coordinate-pair count is `n × (n - 1) / 2`. The available similarity artifact can contain fewer pair rows for some groups, so the public index keeps `patch_pair_count` and `similarity_pair_count` separate. Neither pair count is the same thing as the number of patches with overlap, the proportion of the WSI covered by patches, or the amount of sampled area repeated by another patch.

## Measures used in the atlas

The exact implemented pair formulas and current exploratory thresholds are in [Atlas Methods](atlas-methods.md). The table below is the plain-language reading I want readers to use first.

| Measure | Plain-language reading | Caution |
| --- | --- | --- |
| IoU / overlap | How much two recovered patch boxes occupy the same area. | It describes spatial overlap, not clinical similarity. |
| Mapped image area | How much of the displayed WSI is covered by at least one patch. | It is a coverage measure for the represented image, not a prevalence estimate. |
| Repeated sampled area | How much of the sampled patch area is present in more than one patch. | Read it separately from mapped image area. |
| Repeated full WSI image area | How much of the displayed WSI is covered by overlapping patch regions. | It is not the same denominator as repeated sampled area. |
| Visual fingerprint similarity | Similarity of compact color/texture fingerprints. | Higher means more visually similar fingerprints; it is not a diagnosis score. |
| LAB mean delta | Difference between average LAB color values. | Lower means more similar average stain/color appearance. |
| Pair relation | A readable category derived from overlap, fingerprint similarity, and color difference. | It is a review label, not a biological conclusion. |

## Public versus LAB version

The root-level `NDB_UFES_SAB_atlas_public.pdf` is explicitly marked **PUBLIC
version**. It uses numbered patient/case groups and the approved
`public_ndb_wsi_*` and `sab_only_wsi_*` pseudonyms. The release validator checks
all 587 pages for the expected 251 WSI IDs and 64 groups, and rejects raw SAB
case prefixes, local paths, emails, and common secret patterns.

The separate `NDB_UFES_SAB_atlas.pdf` is the LAB version. It retains raw SAB
case prefixes for internal review and is ignored. The editable public DOCX is
also ignored: v1.0.0 publishes the PDF only.

## Where this fits in the wiki

- Use [Data Dictionary](data-dictionary.md) for canonical file names and row-level fields.
- Use [Atlas Index](atlas-index.md) for the lightweight validated-WSI download and manifest.
- Use [Thesis Experiment Design](thesis-experiment-batches.md) for the two
  final 3,763-row experiments and the separate 3,086-row SAB-linked subset.
- Use [Atlas Gap Map](atlas-gap-map.md) before treating atlas values as release-ready data facts.
- Use [Validation Guide](validation-guide.md) for the checks required before accepting generated artifacts.

!!! note "Current boundary"
    The repository ships the root-level public PDF. The wiki itself loads only
    the small public-pseudonymous WSI index and JSON contracts, so the Pages
    deployment stays fast and below 55 MB. Neither the LAB PDF, the editable
    DOCX source, nor the raw SAB crosswalk is part of the public release.
