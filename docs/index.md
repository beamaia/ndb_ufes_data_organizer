# NDB-UFES Data Organizer

<div class="ndb-hero" markdown>
I use this repository to organize the public NDB-UFES oral histopathology dataset, keep patches from the same specimen together, and make the decisions behind the current thesis batches inspectable. The wiki also records how the SAB-linked subset relates to the full P-NDB-UFES scope and to the patient-first WSI atlas.
</div>

## AI-Assisted Documentation Note

This wiki was prepared with assistance from Codex (GPT-5), following instructions and guidelines written by a human. Published pages are reviewed and validated by a human before release.

## What I am tracking

There are two valid thesis scopes. The full P-NDB-UFES patch dataset contains
3,763 patches and is used by both final experiments. The SAB-linked subset
contains 3,086 patches and documents the recovered WSI/source linkage and
embedding analyses. [Thesis Experiment Design](thesis-experiment-batches.md)
explains why both counts appear.

The root-level public atlas adds a patient/case-first view of 251 validated WSI
groups across 64 public-pseudonymous patient/case groups. Start with the
[Atlas Guide](atlas-guide.md), use the [Atlas Index](atlas-index.md) for
lookup, and check the [Atlas Gap Map](atlas-gap-map.md) before treating any
atlas value as a new thesis-release count.

!!! info "Full public atlas"
    [Download the 587-page public atlas PDF](https://github.com/beamaia/ndb_ufes_data_organizer/raw/refs/heads/main/NDB_UFES_SAB_atlas_public.pdf).
    This 84.5 MB file is the direct Word PDF export at repository root; it has
    not been post-export compressed. The LAB PDF and editable DOCX are not
    public release artifacts.

## Choose a reading path

| If you want to... | Start here |
| --- | --- |
| understand the final experiment design | [Thesis Experiment Design](thesis-experiment-batches.md) |
| inspect the completed model comparison | [Canonical Experiment Results](experiment-results.md) |
| inspect the atlas without the private LAB crosswalk | [Atlas Guide](atlas-guide.md), then [Atlas Index](atlas-index.md) |
| reproduce or deploy the documentation | [Setup & Installation](setup.md), then [Reproducibility](reproducibility.md) |
| review what is still unresolved | [Atlas Gap Map](atlas-gap-map.md) and [Metadata Conflict Review](metadata-conflict-review.md) |
| understand the older leakage-safe fold pipeline | [Pipeline](pipeline.md) and [Implementation Status](status.md) |

The short version of the scope is: **3,763 patches** is the full thesis batch starting point, **3,086 patches** is the SAB-linked metadata/embedding subset, and **251 validated WSI groups** is the atlas linkage view. I keep these numbers together here because they are related, but they are not interchangeable.

## SAB-Linked Subset Release State

<div class="ndb-card-grid" markdown>

<div class="ndb-card" markdown>
<span class="ndb-stat">203</span>
**Matched origins.** Origin-level parent images currently available for fold design.
</div>

<div class="ndb-card" markdown>
<span class="ndb-stat">3,086</span>
**Patch rows.** Patch-level rows assigned to leakage-safe folds.
</div>

<div class="ndb-card" markdown>
<span class="ndb-stat">6</span>
**Folds.** Deterministic cross-validation folds with one origin in one fold.
</div>

<div class="ndb-card" markdown>
<span class="ndb-stat">1.027</span>
**Patch ratio.** Maximum/minimum patch-count ratio after Phase 3 validation.
</div>

<div class="ndb-card" markdown>
<span class="ndb-stat">251</span>
**Validated WSIs.** Atlas groups with 3,763 patches assigned by recovered WSI evidence.
</div>

</div>

## Start Here

| Page | Use It For |
| --- | --- |
| [Thesis Experiment Design](thesis-experiment-batches.md) | Final two-experiment design and its relationship to the 3,086-patch SAB-linked subset. |
| [Canonical Experiment Results](experiment-results.md) | Validated results, figures, statistics, and stored-run provenance. |
| [Atlas Index](atlas-index.md) | Lightweight public-pseudonymous lookup for the 251 validated WSI groups. |
| [Current Release Facts](release-facts.md) | One readable snapshot of the atlas, relationship, and batch scopes. |
| [Factsheet](factsheet.md) | Public dataset context, task labels, fold status, caveats, and citation language. |
| [Data Dictionary](data-dictionary.md) | File relationships, columns, counts, labels, and field-level cautions. |
| [Pipeline](pipeline.md) | Short explanation of Phase 1, Phase 2, Phase 3, and leakage boundaries. |
| [Phase 1 Results](phase1-results.md) | Feature extraction outputs and exploratory embedding visualizations. |
| [Phase 2 Results](phase2-results.md) | Virchow selection, eligibility constraints, and model comparison. |
| [Phase 3 Results](phase3-results.md) | Fold assignment results, validation metrics, and generated fold figures. |

## What I publish

- Origin-level fold assignments.
- Patch-level fold assignments.
- A data dictionary and public factsheet.
- Reproducibility and validation guidance.
- Exploratory quality-control notes.
- Thesis-ready static figures generated from current outputs.

The public site does not load the 587-page root PDF. It loads the text-first
guide, the public-pseudonymous WSI index, and small JSON/CSV provenance files
instead. The repository release still provides
`NDB_UFES_SAB_atlas_public.pdf`; the LAB PDF, editable DOCX, and raw SAB
crosswalk remain excluded.

The published documentation site is:

```text
https://beamaia.github.io/ndb_ufes_data_organizer/
```

## Lab Attribution

This work is attributed to the [Nature-inspired Computing Lab, Labcin](https://www.researchgate.net/lab/Nature-inspired-Computing-Lab-Labcin-Renato-Krohling), and is documented here as part of the lab's reproducible research material.

## Implementation Status

Phases 1 through 3 are implemented and validated for the current matched subset.

| Phase | Current Status |
| --- | --- |
| Phase 1 | Complete. All 11 configured pretrained backbones were extracted with model-specific preprocessing. |
| Phase 2 | Complete. Virchow with PCA=2 and K=3 is the accepted eligible morphology signal. |
| Phase 3 | Complete. All 203 origins and 3,086 patches were assigned with no origin leakage. |
| Contamination checks | Paused. Human-in-the-loop validation is needed before stronger contamination claims are made. |

<div class="ndb-next" markdown>
<strong>Next read:</strong> [Factsheet](factsheet.md)
</div>

## Citation

Falcao Ribeiro de Assis, Maria Clara. Lima, Leandro Muniz de. de Barros, Liliana Aparecida Pimenta. Velloso, Tania Regina. Krohling, Renato. Camisasca, Danielle. 2023. "NDB-UFES: An oral cancer and leukoplakia dataset composed of histopathological images and patient data." Mendeley Data, V4. doi: 10.17632/bbmmm4wgr8.4.
