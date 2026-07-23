# Contamination Checks

<span class="status-pill">Conservative review</span>

This page documents image-level checks for duplicate-like patches and explains why the patient-first grouped experiment has lower contamination risk.

## Same-Case Source-Image Review

The same-case review compared 397 distinct public-image pairs within explicit source case groups. Seventy-two pairs passed the geometric screening rule and were included in a visual review document with original images, projected regions, perspective-rectified crops, overlays, scales, and coordinates.

The candidate label does not prove that two images are duplicates, that one was produced from the other, or that an experiment was contaminated. It identifies relationships that merit human review.

- [Visual review PDF](assets/contamination/same_patient_wsi_image_relationships.pdf)
- [Reproducible review notebook](https://github.com/beamaia/ndb_ufes_data_organizer/blob/main/notebooks/same_patient_wsi_image_relationships_review.ipynb)

The artifact filenames are technical identifiers. The review concerns related histopathology source images and does not assert complete digitized-slide status.

## Patch-Overlap Example

Patches `p0020` and `p0021` contain an effectively identical tissue region.

| Metric | Value |
| --- | ---: |
| Translation | `(246, 255)` pixels |
| Shared rectangle | 266 × 257 pixels |
| Normalized cross-correlation | 1.000 |

<figure class="figure-panel contamination-snippet" markdown>
![Patch-overlap bounding boxes](assets/contamination/origin_0011_overlap_bbox.png)
<figcaption>The full patches are shown in grayscale. The green boxes mark the estimated shared tissue region.</figcaption>
</figure>

The overlap was estimated with translation-only registration, initialized by phase correlation and refined with an integer-shift normalized cross-correlation search. This is technical quality-control evidence, not a biological conclusion.

## Final Experiment Interpretation

The example shows the practical difference between the two released assignments:

| Experiment | `p0020` fold | `p0021` fold | Interpretation |
| --- | ---: | ---: | --- |
| Experiment 1 | 4 | 2 | The patch-level reference split can place related tissue content in different folds. |
| Experiment 2 | 3 | 3 | Patient-first and source-image grouping keeps the related patches together. |

Experiment 2 has no validated source-image or patient/case group crossing folds. It is therefore the lower-contamination-risk split. It is not described as contamination-free because undocumented relationships may still exist.

## Review Limits

- Human review is not a complete disposition of every possible relationship.
- A high similarity or overlap score is a screening signal, not proof of duplication.
- Similar patches within one source-image group are expected.
- Broad contamination claims require case-by-case human disposition.

## Reuse Rule

Use the released fold assignments for reduced contamination. Do not randomly resplit patches, source-image groups, or patient/case groups across training and evaluation partitions in experiments.

<div class="ndb-next" markdown>
<strong>Related read:</strong> [Thesis Experiment Design](thesis-experiment-batches.md)
</div>
