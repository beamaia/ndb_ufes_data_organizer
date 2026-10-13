# Data Dictionary

This page defines every column of the public tables, the folds, and the labels and checks they use. The columns of the original NDB-UFES metadata are on the [NDB-UFES factsheet](factsheet-ndb-ufes.md#columns-of-the-metadata). The tables are small CSV files in this repository, produced by the pipeline described under Reproducibility. Tables that carry case prefixes or file paths are kept private and are listed at the end.

## Files

| File | Rows | What it is |
| --- | ---: | --- |
| `results/phase0/dataset_tables/patch_table_public.csv` | 3,763 | One row per patch: label, parent picture, position, case, checks. |
| `results/phase0/dataset_tables/picture_table_public.csv` | 288 | One row per distinct parent picture, including pictures with no patches. |
| `results/phase0/dataset_tables/case_table_public.csv` | 64 | One row per case (masked patient) and the case group it belongs to. |
| `results/phase1/folds/fold_assignments.csv` | 3,763 | The fold of every patch. **Use this file to train and evaluate.** |
| `results/phase1/folds/fold_summary.csv` | 9 | The six folds, the totals, the ideal share of one fold and the largest gap from it. |
| `results/phase1/clusters/patch_clusters.csv` | 3,763 | The morphology cluster of every patch. |

## Core terms

| Term | Meaning |
| --- | --- |
| Patch | A 512 × 512 pixel crop of a parent picture; one row of the patch table. |
| Parent picture | The whole image a patch was cut from. The code calls it a *histopath image*. Two files with identical pixels are one picture, even if they have different names or come from different datasets. |
| Case | One SAB patient prefix, shown as a masked `case_NNN`. |
| Case group | Cases tied together by shared evidence (the same picture filed under two prefixes, related pictures under two prefixes, or one NDB-UFES patient under two prefixes). All patches of a case group are in one fold. |
| Related pictures | Pictures that show the same tissue, zoomed or shifted, found by matching SIFT features and checking the geometry. They form a *picture group*. |
| Fold | One of folds 0 to 5. There is no separate train/test split: every fold is used as the held-out part in turn. |

## Identifiers

| Identifier | Form | Meaning |
| --- | --- | --- |
| `patch_id` | `p0000` to `p3762` | Name of the patch image in P-NDB-UFES (`data/ndb_ufes/patch_level/images/<patch_id>.png`). |
| `histopath_id` | `hp_` and 12 hex digits | One distinct parent picture: the first 12 digits of the SHA-256 of its decoded pixels. The same picture gets the same id on every run. |
| `ndb_origin_id` | four digits, e.g. `0041` | The picture's number in the NDB-UFES origin images. Empty when the picture is not in NDB-UFES. |
| `picture_group` | a `histopath_id` | A group of related pictures, named by one of its members. A picture with no related picture is its own group. |
| `case_pseudonym` | `case_001` to `case_064` | A masked case. The SAB prefix it stands for is private. |
| `case_group` | `group_001` to `group_063` | A group of cases; the unit the folds are cut on. |

## Patch table

`patch_table_public.csv`, one row per patch.

| Column | Meaning |
| --- | --- |
| `patch_id` | The patch. |
| `patch_path` | Repository-relative path of the patch image. |
| `patch_diagnosis` | The label of the patch: `OSCC`, `Leukoplakia with dysplasia` or `Leukoplakia without dysplasia`. This is the training label. |
| `case_pseudonym` | The case the patch belongs to. |
| `histopath_id` | The parent picture of the patch. |
| `picture_datasets` | Where the parent picture exists: `ndb+sab` (in both datasets) or `sab` (only in SAB). |
| `ndb_origin_id` | The NDB-UFES number of the parent picture; empty for `sab`. |
| `sab_folder` | The SAB folder the parent picture is filed under: `carcinoma`, `leucoplasia` or `benigno`. |
| `picture_group` | The group of related pictures of the parent picture. |
| `case_group` | The case group of the patch. |
| `x`, `y` | Top-left pixel of the patch in the parent picture. |
| `x2`, `y2` | Bottom-right pixel of the patch in the parent picture (`x2 = x + 512`). |
| `match_status` | `exact` when every pixel of the patch equals the picture at that position. All 3,763 are exact. |
| `ndb_diagnosis` | The NDB-UFES diagnosis of the parent picture; empty when the picture is not in NDB-UFES. |
| `patch_vs_picture_diagnosis` | How the patch label relates to `ndb_diagnosis`; see the vocabulary below. |
| `other_confirmed_pictures` | In how many other pictures the content of this patch is confirmed. |
| `other_confirmed_picture_ids` | Those pictures, space separated. |
| `sab_crop_check` | Pixel check of the patch against the SAB crop with the recorded file name; see the vocabulary below. |
| `identical_patch_ids` | Other patches whose images have exactly the same pixels; empty for all but 6 patches. |
| `parent_image_check` | Whether the template search found the parent picture named in the SAB file name; see the vocabulary below. |

## Picture table

`picture_table_public.csv`, one row per parent picture.

| Column | Meaning |
| --- | --- |
| `histopath_id` | The picture. |
| `datasets` | `ndb`, `sab` or `ndb+sab`: the datasets in which a file of this picture exists. |
| `ndb_origin_id` | Its NDB-UFES number, if any. |
| `ndb_diagnosis` | Its NDB-UFES diagnosis, if any. |
| `sab_folders` | The SAB folder or folders its files are filed under, space separated; empty for `ndb`. |
| `case_pseudonym` | The case or cases of its SAB files, space separated; empty for pictures only in NDB-UFES. |
| `picture_group` | Its group of related pictures. |
| `case_group` | Its case group. A picture with no SAB file takes the case group of its related pictures when there is exactly one, and is otherwise empty (20 pictures). |
| `n_patches` | How many patches were cut from it. |
| `patch_diagnoses` | Its patches by label, as `label: count; label: count`. |
| `group_conflicts` | Disagreements inside its group of related pictures; see the vocabulary below. Empty when there is none. |
| `overlap_with_group` | For each related picture: how much of this picture is seen in it, how much of it is seen in this one, and the scale between them. Empty when the picture has no related picture. |

## Case table

`case_table_public.csv`, one row per case.

| Column | Meaning |
| --- | --- |
| `case_pseudonym` | The case. |
| `case_group` | Its case group. |
| `n_pictures` | The pictures filed under the case. |
| `n_patches` | The patches of the case. |

## Fold assignments

`fold_assignments.csv`, one row per patch.

| Column | Meaning |
| --- | --- |
| `patch_id` | The patch. |
| `case_group` | Its case group. |
| `fold` | Its fold, 0 to 5. Empty for a dropped duplicate. |
| `patch_diagnosis` | Its label. |
| `dropped_duplicate_of` | For the three dropped duplicates (`p1147`, `p1149`, `p3356`), the identical patch that stays in the folds; empty otherwise. |

The three duplicates are patches saved twice by SAB as `_N.png` and `_N(1).png`. The lower patch id of each pair is kept, so 3,760 patches are in the folds.

## Fold summary

`fold_summary.csv` has one row per fold (0 to 5), then `total`, `ideal per fold` and `largest gap %`.

| Column | Meaning |
| --- | --- |
| `groups` | Case groups in the fold. |
| `OSCC`, `Dys+`, `Dys-` | Patches by label: OSCC, with dysplasia, without dysplasia. |
| `NDB OSCC`, `NDB Dys+`, `NDB Dys-` | Patches whose parent picture has that NDB-UFES diagnosis. |
| `no NDB` | Patches whose parent picture is not in NDB-UFES. |
| `gender F`, `gender M`, `gender unknown` | Patches by the gender of the NDB-UFES patient; `unknown` when the picture is not in NDB-UFES. |
| `age group 0`, `age group 1`, `age group 2`, `age group unknown` | The same by age group: 0 is under 40 years, 1 is 40 to 60 years and 2 is over 60 years. |
| `cluster 0`, `cluster 1`, `cluster 2` | Patches by morphology cluster. |
| `benigno` | Patches whose parent picture is in the SAB `benigno` folder. This count is reported but not balanced. |

## Morphology clusters

`patch_clusters.csv` has `patch_id` and `cluster_k3`. Each patch is embedded with the Virchow pathology model, the embeddings are reduced to two PCA components, and K-Means (seed 42) forms three clusters. Cluster 0 is the largest (1,632 patches), then 1 (1,345) and 2 (786). The clusters describe appearance, not diagnosis: each class spreads over several clusters.

## Vocabulary

**Labels, from least to most severe:** `Leukoplakia without dysplasia`, `Leukoplakia with dysplasia`, `OSCC`.

**`patch_vs_picture_diagnosis`**

| Value | Meaning | Patches |
| --- | --- | ---: |
| `match` | The patch label equals the NDB-UFES diagnosis of its picture. | 1,777 |
| `patch_less_severe` | The patch is less severe than its picture. This is expected, because a picture has many regions. | 885 |
| `patch_more_severe` | The patch is more severe than its picture; the picture's label is too mild for part of its content. | 449 |
| `not_in_ndb` | The picture is not in NDB-UFES, so there is no diagnosis to compare. | 652 |

No label is changed anywhere. These values only flag disagreement between two labelings, and a disagreement is not necessarily bad. A picture labeled OSCC can also contain dysplasia, so a with-dysplasia patch in it (`patch_less_severe`) is expected. The problem is the other direction: a picture labeled with dysplasia that has an OSCC patch, or a picture labeled without dysplasia that has a with-dysplasia patch (`patch_more_severe`), means the picture's label is too mild for part of its content.

**`sab_crop_check`**

| Value | Meaning | Patches |
| --- | --- | ---: |
| `verified` | Exactly one SAB crop has the same pixels, with the recorded file name and a class folder that agrees with the label. | 3,757 |
| `verified_among_identical_crops` | Several crops share the pixels, and the recorded name is among them with the right class. | 6 |
| `name_differs`, `class_differs`, `no_crop_with_these_pixels` | A crop has the pixels but not the recorded name, the name is in a different class folder, or no crop matches. None occurs. | 0 |
| `not_checked` | The SAB crops were not available when the table was built. | 0 |

**`parent_image_check`**

| Value | Meaning | Patches |
| --- | --- | ---: |
| `agrees` | The template search over all pictures found the patch in exactly the picture its SAB file name names. | 3,763 |
| `agrees_and_also_found_in_another_picture` | It found that picture and another with the same pixels. | 0 |
| `found_only_in_another_picture`, `not_found` | It found a different picture, or none. | 0 |

**`group_conflicts`**

| Value | Meaning |
| --- | --- |
| `sab_folder_differs_in_group` | Related pictures are filed under different SAB folders. |
| `patch_labels_differ_in_group` | The most common patch label differs between related pictures. |

## Statistics tables

The numbers and charts of the wiki come from these tables in `results/phase2/tables/`. Each is one small CSV file.

| File | Rows | What it is |
| --- | ---: | --- |
| `ndb_at_a_glance.csv` | 5 | Images, patients and lesions of NDB-UFES, and how many images have patches. |
| `ndb_columns.csv` | 17 | One row per column of the NDB-UFES metadata: how many images have a value and which values it takes. |
| `ndb_distributions.csv` | 29 | How many images take each value of each NDB-UFES variable. |
| `ndb_images_with_patches.csv` | 3 | NDB-UFES images with and without patches, by diagnosis. |
| `ndb_correlations.csv` | 8 | Cramér's V between every two NDB-UFES variables, as a square table. |
| `patch_correlations.csv` | 6 | Cramér's V between every two patch variables, as a square table. |
| `patches_per_picture.csv` | 3 | Patches per picture: mean, median, quartiles and range. |
| `sab_folder_vs_diagnosis.csv` | 3 | SAB folder against the NDB-UFES diagnosis of the pictures in both datasets. |
| `related_pictures.csv` | 92 | One row per pair of strongly related pictures and the zoom between them. |
| `fold_balance.csv` | 34 | For each value of each balanced variable, how far apart the folds are, for the new folds and the original folds. |
| `fold_spread.csv` | 22 | For each kind of unit, how many have their patches in one fold, in two folds, and so on, for the new folds and the original folds. |
| `fold_largest_groups.csv` | 140 | For the 12 largest case groups, how many of their patches are in each fold, for the new folds and the original folds. |
| `fold_distances.csv` | 45 | How far apart every two folds are in the plane of the first two PCA components of the patch embeddings, for the new folds, the original folds and a random division. |
| `overlapping_patches.csv` | 6 | Overlapping patch pairs of one picture and how many are in different folds. |

| Column | Meaning |
| --- | --- |
| `fold_set` | `new folds` or `original folds` (the six folds published with P-NDB-UFES, numbered here 0 to 5 like the new folds although the published files count from 1). |
| `variable` | The variable counted, or the row of a correlation table (the other columns of a correlation table are the same variables). |
| `column` | A column of the NDB-UFES metadata. |
| `gender`, `age_group`, `skin_color`, `localization`, `tobacco_use`, `alcohol_consumption`, `sun_exposure` | Besides `diagnosis`, the NDB-UFES variables that name the other columns of `ndb_correlations.csv`; see the NDB-UFES factsheet for their meaning. |
| `patch label`, `NDB-UFES diagnosis`, `age group`, `morphology cluster`, `SAB folder` | Besides `gender`, the patch variables that name the other columns of `patch_correlations.csv`: the label of the patch, the NDB-UFES diagnosis of its picture, the age group of the patient, the morphology cluster and the SAB folder of the picture. |
| `filled` | How many images have a value in that column. |
| `values` | The values the column takes, or how many distinct values when there are many. |
| `unit` | What is counted as a unit: `cases`, `case groups`, `parent pictures` or `groups of related pictures`. |
| `folds` | In how many folds the patches of a unit are found. |
| `units` | How many units have their patches in that many folds. |
| `value` | The value of an item, or the value of the variable that a row of `fold_balance.csv` is about. |
| `patches` | Patches in the fold, or in the fold set. |
| `case_group` | A case group. |
| `fold` | A fold of the fold set. |
| `fold_a`, `fold_b` | Two folds of a fold set. |
| `distance` | How far apart the two folds are: the energy distance between their patches, which is 0 when they cover the space in the same way. |
| `spread_points` | The percentage of the fold with the highest share of that value minus that of the fold with the lowest, in percentage points. |
| `item` | The row of the at-a-glance table. |
| `images` | NDB-UFES images with the value. |
| `share` | Fraction of the images. |
| `diagnosis` | A diagnosis of NDB-UFES. |
| `with patches`, `without patches` | NDB-UFES images with and without patches. |
| `shared_area_at_least` | The part of their area two patches share: 25%, 50% or 75%. |
| `pairs` | Pairs of patches of one picture that share that much. |
| `pairs_in_different_folds` | Those pairs whose patches are in different folds. |
| `patches_with_neighbour` | Patches that are in at least one such pair. |
| `patches_in_different_folds` | Patches that have such a neighbour in a different fold. |
| `share_in_different_folds` | The same as a fraction of the pairs. |
| `pictures` | The group of pictures a row summarizes. |
| `count`, `mean`, `median`, `q1`, `q3`, `smallest`, `largest` | Patches per picture: number of pictures, mean, median, first and third quartile, and range. |
| `picture_a`, `picture_b` | Two related pictures. |
| `zoom_factor` | How many times larger one picture shows the tissue than the other. |
| `zoomed` | Whether the zoom differs (above 1.25). |
| `sab_folders` | The SAB folder. |
| `Leukoplakia without dysplasia`, `Leukoplakia with dysplasia`, `OSCC` | Pictures (or, for `benigno`, patches) with that diagnosis. |

## Private tables

These tables are kept by DVC in `private_lab` folders and are never published in git, because they carry masked-but-real SAB case prefixes and file paths: the lab versions of the three tables above (with `case_prefix`, `photo_uuid`, `sab_patch_filename`, `sab_picture_path`, `sab_files`), the case flags table (`case_flags_lab.csv`, one row per tie between case prefixes, with a pending review status), and `data/ndb_ufes/patch_level/csvs/sab_patch_names.csv` (the SAB file name of each patch).
