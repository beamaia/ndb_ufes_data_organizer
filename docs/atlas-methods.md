# Atlas Methods

This implementation-level companion to the [Atlas Guide](atlas-guide.md)
records the calculations used by the atlas, the exploratory review thresholds,
and the remaining method-contract limitations.

## Scope and source code

The methods apply to recovered patch coordinates and patch pairs assigned to
the same source image. The current implementation is split across:

```text
scripts/src/phase0/sab_patch_coordinate_recovery.py
scripts/src/phase0/dataset_alignment_report.py
scripts/src/phase0/validated_linkage.py
```

The compact [methods contract (JSON)](assets/atlas/atlas_methods.json) is
generated beside the public source-image index, manifest, schema, and conflict
report. The index carries coordinate-derived area and overlap fields for each
source-image group while keeping theoretical coordinate-pair counts separate
from available similarity rows.

## Coordinate recovery

A patch location is recovered by searching for the patch inside its candidate
SAB source image with OpenCV `TM_SQDIFF_NORMED` after grayscale conversion.
When the images have the same dimensions, the candidate location is `(0, 0)`.

| Result | Implemented rule | Meaning |
| --- | --- | --- |
| `exact_pixel_match` | Mean absolute error ≤ 0 and maximum absolute channel difference = 0 | Every compared pixel agrees exactly. |
| `near_pixel_match` | Mean absolute error ≤ 1 and maximum absolute channel difference ≤ 5 | A near match retained by the recovery code. |
| `no_reliable_pixel_match` | Neither rule passes | The coordinate should not be treated as validated by this method. |

The current atlas summary reports exact recovered coordinates for all 3,763 represented patches. A coordinate match supports placement evidence; it does not establish a diagnosis or clinical representativeness.

## Same-source-image pair measurements

For a source image with `n` patches, each unordered pair is compared once:
`n × (n − 1) / 2` pairs.

| Measure | Implemented calculation | Reading rule |
| --- | --- | --- |
| IoU | `intersection_area / union_area` for the two recovered coordinate boxes | `IoU > 0` is `spatially_overlapping`; `IoU = 0` is `spatially_distinct`. |
| Visual fingerprint similarity | Resize each patch to 32×32; concatenate RGB values scaled to `[0, 1]` with OpenCV LAB values; mean-center and L2-normalize; take the dot product | Higher values mean more similar compact color/texture fingerprints. |
| LAB mean delta | Euclidean distance between the two patches' mean LAB vectors | Lower values mean more similar average LAB color. |

The current feature rule calls a pair `feature_similar` when visual fingerprint similarity is at least `0.995` and LAB mean delta is at most `6.0`. These are review thresholds chosen for the current exploratory report. They are not diagnostic thresholds.

## Pair-relation decision order

The readable `pair_relation` field is derived in this order:

1. If coordinates require review, retain `feature_similar_coordinate_requires_review` only when the feature rule passes; otherwise use `coordinate_unavailable_or_requires_review`.
2. If coordinates overlap and the feature rule passes, use `feature_similar_and_spatially_overlapping`.
3. If coordinates are spatially distinct and the feature rule passes, use `feature_similar_without_spatial_overlap`.
4. Otherwise retain `spatially_overlapping` when IoU is positive, or `spatially_distinct` when IoU is zero.

This review vocabulary describes repeated or similar image content. It does not
prove that two patches are duplicates, that they came from the same tissue
event, or that they are diagnostically equivalent.

## Atlas-panel area measures

The atlas definitions and a coordinate fixture cross-check establish these denominators:

| Measure | Formula |
| --- | --- |
| Mapped image area | `area(union of all clipped patch boxes) / area(displayed source image)` |
| Repeated sampled area | `area(pixels covered by at least two patch boxes) / area(union of all clipped patch boxes)` |
| Repeated full-image area | `area(pixels covered by at least two patch boxes) / area(displayed source image)` |

The reusable helper in `scripts/src/release/atlas_methods.py` and its fixture
cross-check cover these denominators. The 15-patch atlas panel for the
corresponding source image reproduces approximately 63.6% mapped area, 59.8%
repeated sampled area, and 38.0% repeated full-image area from the recovered
coordinates.

## Remaining method-contract work

The formulas are now explicit, but the original atlas panel
renderer/configuration is not yet connected to this helper. The next methods
update should therefore add:

- the generator/configuration version that produced each atlas panel;
- a regeneration path that uses the helper directly;
- a fixture comparison against a small exported public-PDF atlas panel.

## Renderer provenance review

The ignored editable source used to export
`NDB_UFES_SAB_atlas_public.pdf` was inspected. Its package metadata says `python-docx`
generated the document and Microsoft Word last handled it, but it contains no
custom properties, external relationships, generator reference, or
source-script path. The available repository builder at
`scripts/src/reports/build_validated_linkage_factsheet_docx.py` renders source-image
context images and patch thumbnails, but it does not calculate the three area
measures.

The denominators and values can be checked against recovered coordinates, but
the root-level 587-page public PDF cannot be regenerated byte-for-byte from
this repository. Its privacy and release scope are independently checked by
`scripts/src/release/validate_public_atlas_pdf.py`.

## Current reproducibility boundary

The current release has a reproducible machine-readable atlas layer:

- the public CSV, manifest, schema, conflict summary, and methods contract are generated and validated together;
- the area denominators are implemented in a reusable helper and checked with a fixture;
- the 15-patch coordinate cross-check reproduces the atlas values to the documented rounding;
- the root-level public PDF is checked for its 251 retained source-image
  pseudonyms, 64 case groups, size limit, and forbidden private content.

The public PDF remains a reviewed evidence snapshot, not a byte-for-byte
reproducible build product. Until the original renderer is recovered or
formally replaced, the public CSV/JSON export is the reproducible data surface
and the PDF is the validated human-readable atlas release artifact.

## Related artifacts

- [Atlas Guide](atlas-guide.md)
- [Atlas Index](atlas-index.md)
- [Atlas Gap Map](atlas-gap-map.md)
- [Metadata Conflict Review](metadata-conflict-review.md)
- [Methods contract (JSON)](assets/atlas/atlas_methods.json)
