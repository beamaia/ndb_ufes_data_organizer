# Atlas Guide

This page is the short, public-facing way into the **NDB-UFES/SAB
Patch-to-Source-Image Atlas**. The sanitized atlas is released as
`NDB_UFES_SAB_atlas_public.pdf` at the repository root. It is not copied into
the wiki payload: the 587-page PDF repeats a full evidence panel for every
source-image group and would exceed the site's 55 MB release gate.

**Public artifact reviewed:** `NDB_UFES_SAB_atlas_public.pdf`, reviewed
23 July 2026.

!!! info "Download the full public atlas"
    [Download `NDB_UFES_SAB_atlas_public.pdf`](https://github.com/beamaia/ndb_ufes_data_organizer/raw/refs/heads/main/NDB_UFES_SAB_atlas_public.pdf)
    from the repository root. It is the direct 84.5 MB Word PDF export with no
    post-export compression.

## What the atlas shows

The atlas is a visual representation of which patches belong to each source
image. Recovered patch coordinates are displayed on the larger source image,
with the associated patch labels and descriptive overlap measures. The source
images are histopathology images, but they are not established here as
whole-slide images.

The atlas is organized in this order:

1. definitions and a validated-linkage summary;
2. dataset sources and their roles;
3. a short explanation of how to read a source-image entry;
4. same-source-image patch-evidence measures;
5. the full source-image atlas, grouped by a public-pseudonymous case number.

## Atlas snapshot

| Atlas item | Current atlas value | Interpretation |
| --- | ---: | --- |
| Patch rows | 3,763 / 3,763 | Every represented patch is assigned to a source-image group. |
| Recovered coordinates | 3,763 / 3,763 | Every represented patch has coordinates used to place it on the source-image figure. |
| Source-image groups | 251 | 203 groups have public NDB-UFES + SAB evidence; 48 are recovered from SAB only. |
| Patches by atlas source role | 3,111 both-source / 652 SAB-only | These are atlas classifications, not the current relationship-table partition. |
| Public-pseudonymous case groups | 64 | Related source-image entries are kept together for navigation. |
| Patch-label agreement | 3,763 / 3,763 | The atlas reports agreement for the labels carried by its patch records. |

These are atlas-level values. They should not be substituted automatically for the current thesis-batch or public NDB-UFES-matched-subset counts elsewhere in this wiki. The reconciliation is tracked in [Atlas Gap Map](atlas-gap-map.md).

## Two linkage layers

The 3,763 and 3,086/677 numbers answer different questions and are therefore
reported separately.

| Linkage layer | Current result | What it means |
| --- | ---: | --- |
| SAB/atlas source-image linkage | 3,763 patches assigned to 251 source-image groups; all 3,763 have recovered coordinates. The atlas source roles contain 3,111 patches in both-source groups and 652 in SAB-only groups. | SAB and pixel-containment evidence place every patch on a source image. This is the layer displayed by the atlas. |
| Public NDB-UFES origin matching | 3,086 rows match one of 203 public NDB-UFES origin images; 677 rows do not. | The current relationship table records whether each SAB-linked patch also has a public NDB-UFES origin match. All rows remain in the full thesis scope. |
| Patch-label agreement | 3,763 / 3,763 | The complete patch-label sources agree between NDB-UFES and SAB in the validated-linkage output. This is separate from the 677 rows whose reconstructed thesis metadata is missing and the 1,328 rows where reconstructed metadata differs from the complete patch-label source. |

The two public-origin layers contain the same set of 203 public origin IDs,
but they do not assign the same patch rows to the public-match category:

| Current relationship status | Atlas both-source | Atlas SAB-only | Row total |
| --- | ---: | ---: | ---: |
| Public NDB-UFES match | 3,069 | 17 | 3,086 |
| No public NDB-UFES match | 42 | 635 | 677 |
| Column total | 3,111 | 652 | 3,763 |

The off-diagonal cells contain 59 patches. This explains why the relationship
split is 3,086/677 while the atlas source-role split is 3,111/652. Neither
partition should be used as a substitute for the other.

This 59-row cross-layer difference is unrelated to the 59 metadata-conflict
rows whose reconstructed patch label agrees while another field triggers the
conflict flag. The two sets have zero overlap. The 677 current no-match rows,
by contrast, are the same 677 rows whose reconstructed metadata is missing.

The authoritative atlas summary is `results/phase0/validated_linkage/validated_linkage_summary.json`. The authoritative thesis relationship summary is `results/phase3/current_thesis_batches/relationship_update_summary.json`. The [Atlas Index](atlas-index.md) packages the public atlas layer without the LAB crosswalk.

## Levels represented in the atlas

| Level | Meaning in the atlas | Interpretation |
| --- | --- | --- |
| Patch | A 512 × 512 image extracted from a larger source image. | Patch IDs identify the displayed crops. |
| Source-image group | A larger histopathology source image linked to one or more patches. | This is the level represented by each atlas entry. |
| Case group | A public-pseudonymous grouping retained for navigation. The LAB source can expose a raw SAB case prefix. | The public release shows only the numbered grouping and does not establish patient identity. |

The existing machine-readable names `validated_wsi_id`, `public_ndb_wsi_*`,
and `sab_only_wsi_*` are retained for compatibility with generated artifacts.
In this wiki they identify source-image groups; they should not be interpreted
as proof that the underlying images are whole-slide images.

## How to read one source-image entry

Each source-image entry follows the same compact sequence:

- a metadata panel with source, source-level labels, patch count, and patch labels;
- a context figure showing where recovered patch boxes sit on the larger source image;
- a color strip that acts only as a patch-label key;
- patch thumbnails labeled by patch ID and diagnosis;
- a same-source-image evidence summary.

The evidence summary describes redundancy and overlap within one source image.
For `n` patches, the theoretical coordinate-pair count is
`n × (n - 1) / 2`. The available similarity artifact can contain fewer pair
rows for some groups, so the public index keeps `patch_pair_count` and
`similarity_pair_count` separate. Neither pair count is the same thing as the
number of patches with overlap, the proportion of the source image covered by
patches, or the amount of sampled area repeated by another patch.

## Measures used in the atlas

The exact implemented pair formulas and current exploratory thresholds are in
[Atlas Methods](atlas-methods.md). The table below provides a plain-language
interpretation.

| Measure | Plain-language reading | Caution |
| --- | --- | --- |
| IoU / overlap | How much two recovered patch boxes occupy the same area. | It describes spatial overlap, not clinical similarity. |
| Mapped image area | How much of the displayed source image is covered by at least one patch. | It is a coverage measure for the represented image, not a prevalence estimate. |
| Repeated sampled area | How much of the sampled patch area is present in more than one patch. | Read it separately from mapped image area. |
| Repeated full-image area | How much of the displayed source image is covered by overlapping patch regions. | It is not the same denominator as repeated sampled area. |
| Visual fingerprint similarity | Similarity of compact color/texture fingerprints. | Higher means more visually similar fingerprints; it is not a diagnosis score. |
| LAB mean delta | Difference between average LAB color values. | Lower means more similar average stain/color appearance. |
| Pair relation | A readable category derived from overlap, fingerprint similarity, and color difference. | It is a review label, not a biological conclusion. |

## Public versus LAB version

The root-level `NDB_UFES_SAB_atlas_public.pdf` is explicitly marked **PUBLIC
version**. It uses numbered case groups and the approved
`public_ndb_wsi_*` and `sab_only_wsi_*` pseudonyms. The release validator checks
all 587 pages for the expected 251 source-image IDs and 64 groups, and rejects raw SAB
case prefixes, local paths, emails, and common secret patterns.

The separate `NDB_UFES_SAB_atlas.pdf` is the LAB version. It retains raw SAB
case prefixes for internal review and is ignored. The editable public DOCX is
also ignored: v1.0.0 publishes the PDF only.

## Where this fits in the wiki

- Use [Data Dictionary](data-dictionary.md) for canonical file names and row-level fields.
- Use [Atlas Index](atlas-index.md) for the lightweight source-image download and manifest.
- Use [Thesis Experiment Design](thesis-experiment-batches.md) for the two
  final 3,763-row experiments and the separate 3,086-row public
  NDB-UFES-matched subset.
- Use [Atlas Gap Map](atlas-gap-map.md) before treating atlas values as release-ready data facts.
- Use [Validation Guide](validation-guide.md) for the checks required before accepting generated artifacts.

!!! note "Current boundary"
    The repository ships the root-level public PDF. The wiki itself loads only
    the small public-pseudonymous histopathology index and JSON contracts, so the Pages
    deployment stays fast and below 55 MB. Neither the LAB PDF, the editable
    DOCX source, nor the raw SAB crosswalk is part of the public release.
