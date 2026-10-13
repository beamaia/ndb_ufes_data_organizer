# NDB-UFES Data Organizer

<div class="ndb-hero" markdown>
This repository rebuilds the dataset behind the P-NDB-UFES oral histopathology patches. It ties every patch to the parent picture it was cut from, keeps related pictures and patients together, and publishes folds that do not leak between patients.
</div>

## What is here

- **Every patch traced to its image.** Each of the 3,763 P-NDB-UFES patches is tied to the parent picture it was cut from, found by exact pixel matching. Most of those pictures are NDB-UFES images; the others come from internal datasets that are described in [About the Data](about-the-data.md).
- **Cases and case groups.** Pictures and patients that share evidence are tied into case groups, and a case group is never split across folds.
- **Six folds.** Balanced at once on the patch label, the NDB-UFES diagnosis of the picture, gender, age group and three morphology clusters. See [New Folds](folds.md) for the numbers.
- **Nothing relabeled.** Where the patch label and the picture's diagnosis disagree, the disagreement is recorded, not corrected. A disagreement is not necessarily bad: a picture labeled OSCC can also contain dysplasia, so a with-dysplasia patch in it is expected. The problem is the other direction, a picture labeled with dysplasia that has an OSCC patch.

## Download

The tables are small CSV files in this repository:

- [Fold assignments](https://raw.githubusercontent.com/beamaia/ndb_ufes_data_organizer/main/results/phase1/folds/fold_assignments.csv): the fold of every patch. **Use this file to train and evaluate.**
- [Patch table](https://raw.githubusercontent.com/beamaia/ndb_ufes_data_organizer/main/results/phase0/dataset_tables/patch_table_public.csv): label, parent picture, position and checks for every patch.
- [Picture table](https://raw.githubusercontent.com/beamaia/ndb_ufes_data_organizer/main/results/phase0/dataset_tables/picture_table_public.csv): one row per parent picture.
- [Case table](https://raw.githubusercontent.com/beamaia/ndb_ufes_data_organizer/main/results/phase0/dataset_tables/case_table_public.csv): the masked cases and their case groups.

Every column is explained in the [data dictionary](data-dictionary.md). The images themselves are not published here: the patches are in P-NDB-UFES and the origin images in NDB-UFES (Mendeley Data). Some parent images come from an internal dataset, SAB, which is private; see [About the Data](about-the-data.md).

## Using the folds

- Use `fold_assignments.csv` instead of a random patch-level split. Patches of one case group are always in one fold, so patches of the same patient never sit on both sides of an evaluation.
- Each fold is held out in turn. There is no separate train/test split.
- Skip the three patches with an empty `fold`: they are exact duplicates of another patch, which stays in the folds.
- The label to predict is `patch_diagnosis`. `ndb_diagnosis` belongs to the whole picture and is context, not a target.

## Where to look

- To see how the four datasets differ and how they relate, read [About the Data](about-the-data.md).
- For the factsheet of NDB-UFES, read [Factsheet: NDB-UFES](factsheet-ndb-ufes.md).
- For the factsheet of P-NDB-UFES, read [Factsheet: P-NDB-UFES](factsheet-p-ndb-ufes.md).
- To see how patches and pictures were matched, and to open the atlases, read [Matching and Atlases](matching-and-atlases.md).
- For the old fold configuration and how contaminated it was, read [Old Folds and Contamination](old-folds.md).
- For the new fold configuration, read [New Folds](folds.md).
- For every column and value of the tables, read the [Data Dictionary](data-dictionary.md).
- To install, preview the wiki and rebuild the dataset, read [Setup and Installation](setup.md) and [Reproducibility](reproducibility.md).

## AI-Assisted Documentation Note

This wiki was prepared with the help of AI tools, following instructions written by a human. Pages are reviewed and validated by a human before release.
