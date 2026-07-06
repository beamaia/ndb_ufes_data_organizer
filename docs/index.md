# NDB-UFES Data Organizer

<div class="ndb-hero" markdown>
This repository organizes the public NDB-UFES oral histopathology dataset into leakage-safe fold assignments, documentation, and reproducibility material. It does not train a downstream diagnostic model.
</div>

## AI-Assisted Documentation Note

This wiki was prepared with assistance from Codex (GPT-5), following instructions and guidelines written by a human. Published pages are reviewed and validated by a human before release.

## Current Release State

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

</div>

## Start Here

| Page | Use It For |
| --- | --- |
| [Factsheet](factsheet.md) | Public dataset context, task labels, fold status, caveats, and citation language. |
| [Data Dictionary](data-dictionary.md) | File relationships, columns, counts, labels, and field-level cautions. |
| [Pipeline](pipeline.md) | Short explanation of Phase 1, Phase 2, Phase 3, and leakage boundaries. |
| [Phase 1 Results](phase1-results.md) | Feature extraction outputs and exploratory embedding visualizations. |
| [Phase 2 Results](phase2-results.md) | Virchow selection, eligibility constraints, and model comparison. |
| [Phase 3 Results](phase3-results.md) | Fold assignment results, validation metrics, and generated fold figures. |

## What The Repository Publishes

- Origin-level fold assignments.
- Patch-level fold assignments.
- A data dictionary and public factsheet.
- Reproducibility and audit guidance.
- Exploratory quality-control notes.
- Thesis-ready static figures generated from current outputs.

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
