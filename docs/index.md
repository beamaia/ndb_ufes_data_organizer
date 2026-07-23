# NDB-UFES Data Organizer

<div class="ndb-hero" markdown>
This repository organizes the public NDB-UFES oral histopathology dataset, keeps related patches together, and publishes the final thesis experiment assignments, results, and source-image linkage.
</div>

## AI-Assisted Documentation Note

This wiki was prepared with assistance from Codex (GPT-5), following instructions and guidelines written by a human. Published pages are reviewed and validated by a human before release.

## Final Dataset Scope

Both experiments use all **3,763 P-NDB-UFES patches**. The validated linkage assigns every patch to one of **251 source-image groups**:

| Source-image role | Groups | Patches |
| --- | ---: | ---: |
| Public NDB-UFES + SAB evidence | 203 | 3,111 |
| SAB-only evidence | 48 | 652 |
| **Total** | **251** | **3,763** |

The 3,111 patches in both-source groups are the public NDB-UFES-linked set used throughout this wiki. The 652 SAB-only patches remain in both final experiments and are grouped by their validated SAB source-image relationships.

## Download the Fold Assignments

Most users should download **Experiment 2**, the patient-first grouped split. Use Experiment 1 only when the patch-level reference comparison is required.

- [Download Experiment 2 fold assignments — patient-first grouped CSV](https://raw.githubusercontent.com/beamaia/ndb_ufes_data_organizer/main/release/v1.0.0/public/tables/experiment2_patch_assignments.csv)
- [Download Experiment 1 fold assignments — reference CSV](https://raw.githubusercontent.com/beamaia/ndb_ufes_data_organizer/main/release/v1.0.0/public/tables/experiment1_patch_assignments.csv)

Each CSV contains all 3,763 patches. Use the provided `fold` and `role` columns rather than creating a new random split.

## Choose a Reading Path

| If you want to... | Start here |
| --- | --- |
| understand the released dataset and linkage | [Factsheet](factsheet.md) |
| understand the two final experiment splits | [Thesis Experiment Design](thesis-experiment-batches.md) |
| inspect the completed model comparison | [Canonical Experiment Results](experiment-results.md) |
| inspect files, columns, and counts | [Data Dictionary](data-dictionary.md) |
| reproduce the final public outputs | [Reproducibility](reproducibility.md) |
| preview or build the wiki | [Setup & Installation](setup.md) |
| understand the contamination-risk example | [Contamination Checks](contamination-analysis.md) |

## Final Outputs

- Two 3,763-row experiment assignment tables.
- A 251-row public source-image index.
- Canonical results from six parent runs and 30 child-fold evaluations.
- Public figures, machine-readable metrics, and provenance.
- A data dictionary, factsheet, reproducibility guide, and validation report.

The public site loads text-first documentation and sanitized research artifacts. Private source identifiers, private crosswalks, local paths, checkpoints, and raw MLflow storage are excluded.

The published documentation site is:

```text
https://beamaia.github.io/ndb_ufes_data_organizer/
```

## Lab Attribution

This work is attributed to the [Nature-inspired Computing Lab, Labcin](https://www.researchgate.net/lab/Nature-inspired-Computing-Lab-Labcin-Renato-Krohling), and is documented here as part of the lab's reproducible research material.

## Citation

Falcao Ribeiro de Assis, Maria Clara. Lima, Leandro Muniz de. de Barros, Liliana Aparecida Pimenta. Velloso, Tania Regina. Krohling, Renato. Camisasca, Danielle. 2023. "NDB-UFES: An oral cancer and leukoplakia dataset composed of histopathological images and patient data." Mendeley Data, V4. doi: 10.17632/bbmmm4wgr8.4.
