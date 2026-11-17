# Thesis notes

Observations and decisions to carry into the thesis. Numbers come from repo commands; rerun them before quoting.

## Quote

> "the fact that there are disagreements makes so that the models also has difficulties later on."

(2026-10-11, about disagreeing labels between whole images and their patches.)

## Decisions

- **No label is changed.** The thesis shows the data we have: its strong points and its problems. Disagreements are flagged and represented, not corrected.
- **Patch labels carry more weight of truth than picture labels.** The patches were labelled more recently and are smaller. This is still a point of attention to represent in the thesis.
- **Duplicate patches are dropped when the folds are built (phase 1).** Three pairs of patches (p1146/p1147, p1148/p1149, p1150/p3356) have exactly the same pixels: SAB saved the same crop as `_N.png` and `_N(1).png`. Both copies belong to the same picture, case and label. The patch table keeps every patch and flags the twins in `identical_patch_ids`; the folds stage keeps one patch of each pair, so the dataset has 3,757 distinct patch images, not 3,763.
- **NDB-UFES is the reference** for the pictures it contains, since it was checked and published. SAB-only pictures (every picture in the SAB `benigno` folder, 49 files, none of them in NDB-UFES) are checked afterwards.

- **Zoom is a *possible* zoom (2026-11-04).** No magnification metadata exists. Each picture's `possible_zoom` (10x / 40x) is a non-expert reading by eye, helped by the SIFT relative scale and by other pictures of the same patient; it was not checked by a pathologist. The `evidence` column grades each value (`by_eye_agrees_with_sift`, `derived_from_sift`, `by_eye_in_sift_group`, `by_eye_against_sift`, `by_eye_only`), and `relative_zoom` is the measured SIFT scale against the widest linked picture. Sheet: `results/phase0/picture_relations/zoom_review.csv`. Report it as an estimate, with the counts per evidence level.
- **Published folds are not copied into the tables (2026-11-04).** The patch table keeps the P-NDB-UFES patch name as `patch_id` (`p0000`, unique), so a user can join it to the published fold files themselves; the old `sab_split_folder` column (committed once from uncommitted code) is not restored.

## Severity rule

An image has many regions, so a patch may differ from its picture's label. A patch can be **less severe** than its picture (accepted; it only counts). A patch **more severe** than its picture is flagged: the picture's label is then too mild for part of its content, a false negative for that picture. Order: without dysplasia < with dysplasia < OSCC.

Why it matters: dysplasia grading is contested between specialists, and the patches were labelled by different people from the whole-picture labels. These are the pictures where annotators disagreed, and the disagreement is expected to make the classification harder for the models.

## Where to find the evidence

`uv run python scripts/phase0.py patch-table` writes `results/phase0/dataset_tables/` and prints the counts below in its summary:

- `patch_table_*.csv`: one row per patch. `patch_vs_picture_diagnosis` says whether the patch label matches, is less severe or is more severe than the NDB-UFES diagnosis of its picture (the flagged patches are the `patch_more_severe` rows).
- `picture_table_*.csv`: one row per picture, with its SAB folder, NDB-UFES diagnosis, patch label counts, related-picture group, case group, and the columns `group_conflicts` and `overlap_with_group` (pictures whose group disagrees on folder or patch label).
- `case_table_*.csv` and `private_lab/case_flags_lab.csv`: the cases, their groups, and the pending flags.
- The `lab` versions (in `private_lab`, git-ignored) carry case prefixes and file paths; the `public` versions carry pseudonyms only.

Run of 2026-10-11: 3,111 patches in NDB-UFES pictures; 1,334 differ from their picture (885 less severe, 449 more severe, in 42 pictures). The 449 are 54 OSCC patches in with-dysplasia pictures and 395 with-dysplasia patches in without-dysplasia pictures.

## Old linkage against the rebuilt tables (2026-10-12)

The old validated linkage (251 pictures) and the rebuilt patch table (247 pictures with patches) agree on all 3,763 patches: same patch ids, same box coordinates, same labels. The only difference is 4 pairs of old "pictures" that are one picture: two SAB files with identical pixels under different names. The rebuild merges them by pixel hash. Three pairs belong to one case, one pair is filed under two case prefixes (the single pending flag in `case_flags_lab.csv`).

## Folds (phase 1, 2026-10-12)

`uv run python scripts/phase1.py folds` writes `results/phase1/folds/fold_assignments.csv` (patch id, case group, fold, patch label, and for a dropped duplicate the patch kept in its place) and `fold_summary.csv` (a row per fold with every count, the ideal share and the largest gap). Measured against the rebuilt links, the old Experiment 2 splits 31 of 64 cases across folds (Experiment 1 splits 63; an earlier count of 17 is not reproduced by this measurement); here the unit of assignment is the case group, and the run stops if any case group, picture or group of related pictures would be in more than one fold, if a fold lacks a class, or if the largest fold exceeds 1.10 times the smallest.

- 3,760 patches (3 duplicate patches dropped) in 63 case groups, 6 folds.
- What is balanced, all equally weighted: the patch label (OSCC, with dysplasia, without dysplasia), the NDB-UFES diagnosis of the patch's picture (with "not in NDB-UFES" as a fourth category), gender and age group of the NDB-UFES patient ("unknown" for pictures not in NDB-UFES), and 3 morphology clusters (Virchow embedding of each patch, PCA to 2 components, KMeans, seed 42; silhouette 0.636, the best of 2 to 9 clusters and the same choice as the last research).
- Search: the case groups, largest first, each go to the fold where they add the least squared relative deviation from an equal share (greedy); then single groups are moved and pairs exchanged while that lowers the total cost. The same improvement is run from 200 seeded random starting points and the lowest cost is kept (seed 156; cost 3.95, against 4.74 for greedy alone and a median of 4.20 over all starts). Deterministic: two runs give identical files.
- Result, range over the 6 folds (largest gap from an equal share): patches 605 to 656 (ratio 1.084); OSCC 170 to 208 (10.8%); with dysplasia 280 to 355 (13%); without dysplasia 112 to 123 (4.8%); NDB-UFES diagnosis OSCC 230 to 279, with dysplasia 138 to 167, without dysplasia 100 to 116, not in NDB-UFES 99 to 124; gender F 181 to 226, M 292 to 336; age group 1 208 to 258, age group 2 228 to 271; clusters 0, 1, 2: 250 to 307, 204 to 246, 123 to 145.
- Known limit: age group 0 has only 199 patches in few case groups, so two folds hold none of it; this one count contributes 3.51 of the total cost of 3.95. It was kept in the balance as it is (decision 2026-10-12).
- Without balancing metadata and clusters, the same folds had one fold with 390 female patients and another with 78, so balancing them was necessary.
- Patches of pictures in the SAB `benigno` folder (595) stay in the folds with their patch labels, 68 to 110 per fold (reported, not balanced). One benign picture has a similar picture in another folder (20 patches, in fold 5; its twin is NDB-UFES picture 0041); it is only reported.
- Balancing the patch label alone gives tighter label counts but very uneven NDB-UFES diagnosis, gender and age, which is why all of them are balanced. The patch label and the NDB-UFES diagnosis disagree for 1,334 patches, so they cannot all be perfect.

## Open points to observe later

- Pictures whose SAB folder differs from related pictures of the same case, e.g. a `benigno` picture that overlaps (88%) a `leucoplasia` picture, with patches labelled OSCC (14) and with dysplasia (6). Listed by the `group_conflicts` column of the picture table.
- 18 pictures in both datasets whose SAB folder disagrees with the NDB-UFES diagnosis (10 NDB-UFES OSCC under `leucoplasia`, 8 with dysplasia under `carcinoma`).

## Backlog

- **Hematoxylin-dense attention (explainability, after the topic walkthrough and the zoom review).** Per patch: share of occlusion importance inside a hematoxylin-dense mask divided by the share of area the mask covers (1 = no preference). Use one fixed hematoxylin threshold for the whole dataset, not per-image Otsu (Otsu adapts per patch, so its fractions are not comparable). Compare Experiment 1 vs 2, correct vs wrong panel calls, per class, within zoom groups. Prior work: Graziani et al. 2018 (regression concept vectors), Kim et al. 2018 (TCAV). Later check: a handcrafted hematoxylin/texture baseline, also tested for predicting `case_group` (stain as a slide shortcut).
- **Correct by possible zoom and class (explainability).** With `possible_zoom` in `patch_table_public.csv`, the panel export (`ndb_ufes_training_pipeline/src/panel.py`, which already reads that table) can report per class: share of patches the panel gets right, and balanced accuracy, split by 10x / 40x; also for the SIFT-backed subset only (`zoom_evidence` other than `by_eye_only`). Question: is a class easier at one zoom (zoom as a shortcut), and does it differ between Experiment 1 and 2? Check first how zoom is spread over classes and folds, or the comparison mixes the two.
