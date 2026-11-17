# Thread 4: occlusion maps, what the models use

Read `README.md` of this folder first (rules).

## What the user wants to understand

What occlusion is; whether the corners of a patch carry information ("patches are part of an image, don't the corners contain relevant information?"); and whether overlapping patches can be used to tell tissue from position ("if they overlap we could create parts of an image where the overlapping patches concatenate").

## Method (all inference, runs on the Mac in minutes)

A window of a quarter of the patch (128 pixels on a patch of 512) covered with white (or with the patch's mean colour, `--baseline mean`) slides in steps of an eighth (64 pixels): 7 x 7 positions, 50 passes of the model per patch. The map is the drop of the score of the class the model predicts: the probability (default) or the log-odds (`--score logit`, does not saturate). Models: VGG16, DenseNet-121, Swin-T, fold run 3 of each (chosen by the highest validation balanced accuracy at the epoch of the kept checkpoint, test fold not used: 0.7228, 0.7381, 0.7508), from Experiment 2 (artifact folder `2` of MLflow). Four groups of patches from `panel_patches.csv` (30 each, at most 3 per picture, seed 0): labeled with dysplasia and called OSCC like their OSCC picture ("agrees with the parent", 24 patches), the same with a with-dysplasia picture ("genuine error", only 3 patches: no conclusion), labeled with dysplasia and right for all 12 models (30), wrong for all 12 (30). The covering colour is a choice (white, mean colour); a reader will ask.

## Code

`src/select_checkpoints.py` (picks the fold per model, prints the `aws s3 cp` commands to restore the checkpoints; already run, files restored), `src/occlusion.py`, `src/occlusion_overlap.py`, `tests/test_select_checkpoints.py`, `tests/test_occlusion.py`, `tests/test_occlusion_overlap.py`, README sections. Commands (from the training repository, `--results ../ndb_ufes_data_organizer/results/experiments/experiment_2`):

- `uv run python -m src.occlusion --results ... [--score logit] [--baseline mean]` writes `occlusion[_logit][_mean]_{summary,grids,agreement}.csv`, `_<model>.png`, `_mean_maps.png`.
- `uv run python -m src.occlusion_overlap --results ...` writes `occlusion_logit_overlap_pairs.csv` and `occlusion_logit_overlap.png`.

## What was found

- Probability run: the largest drop in a map is only 0.03-0.25; agreement (Spearman) between the maps of two models on the same patch is about 0 (-0.09 to +0.13) in every group.
- Correction: saturation does NOT explain the near-zero agreement. Within one patch, probability and log-odds are monotone transforms of each other, so the windows get the same ranking; the log-odds run gave identical Spearman values. Log-odds drops are large (0.9-1.6) and spread over most windows (21-35 of 49 above 0.1; not comparable with the probability threshold).
- Confidence: mean probability of the predicted class 0.88 on "no model right", 0.78 on "all models right": models are as sure when all of them are wrong (shared confident errors; see Thread 3).
- VGG16 when it predicts OSCC (groups "agrees with the parent" and "genuine error"): the evidence is at the corners and edges of the patch, the centre is near zero (centre share 0.009 and 0.000 with the mean-colour covering; 0.18 would be uniform; top 3 windows hold about half of the drop). The mean-colour covering did not remove it, so it is not a white-border artifact. When VGG16 predicts with dysplasia its evidence is in the middle and spread. DenseNet-121 broad, Swin-T weak and patchy.
- Correction of the first reading: corners are not "less tissue"; a patch is a crop, its corners carry real tissue and the pathologist labeled the whole patch. What stands out is that the hot windows are in the same places on every patch.
- Overlap test (97% of patches have a neighbour sharing at least a quarter of their area, 81% half; all pairs are in the same fold in the new folds; every patch is an exact 512 x 512 crop at known `x, y, x2, y2`, `match_status` exact for all 3,763): for 108 pairs of neighbouring patches (84 anchors) `content_rho` (maps put in picture coordinates, correlated over the shared tissue) is 0.20-0.42 for DenseNet-121 and Swin-T and 0.23-0.34 for VGG16: the same tissue matters partly wherever it sits in the patch. `position_rho` (maps correlated in patch coordinates) is higher than `content_rho` for VGG16 in every group (0.61, 0.37, 0.40) and random pairs from different pictures correlate 0.31 for VGG16 on OSCC-called patches against about 0 for the other models.
- Flaw found in that test: the baseline for `position_rho` was a patch from a different picture, so it cannot tell "same place" from "same picture/stain/tissue" (neighbours share both). Fixed in code: `same_picture_position_rho` (a non-overlapping patch of the same picture, `far_patch`). THE RERUN WITH THE FIXED BASELINE HAS NOT BEEN PASTED YET: `caffeinate -dimsu uv run python -m src.occlusion_overlap --results ../ndb_ufes_data_organizer/results/experiments/experiment_2` (about 7 minutes, prints model x group means including `same_picture_position_rho`). If `position_rho` is well above `same_picture_position_rho`, the extra is shared tissue; if VGG16's `same_picture_position_rho` stays high (about 0.3 on OSCC-called patches), the place effect is real.

## Pending, in order

1. The rerun above, then read it with the user.
2. Confidence intervals that resample pictures (the pairs are not independent: several per picture, 84 anchors; 3 patches belong to two groups and are counted in the later one).
3. Another fold copy of each architecture (extend `select_checkpoints` to list a second fold; the user restores two or three more checkpoints from S3): if two copies of the same architecture also disagree, the maps are not reproducible on single patches and say nothing about architecture.
4. The randomisation control (Adebayo et al. 2018): re-initialise the model block by block from the classifier backwards, recompute the maps on a fixed patch set, report signed and absolute Spearman against the original map; skip the label-randomisation test and disclose it.
5. A larger "genuine error" group: only 3 patches in the test fold; the validation-fold predictions could provide more (needs checkpoints of all folds).

What can be said now: occlusion maps of three equally accurate architectures show different, mutually uncorrelated patterns; VGG16 relies on the periphery for OSCC predictions and the covering colour does not change that; maps describe what each model uses, not what a pathologist calls evidence; describe where only structurally (centre or border, focal or spread), never with histological names; do not say "nuclei".

## Files this thread owns

`src/select_checkpoints.py`, `src/occlusion.py`, `src/occlusion_overlap.py`, their tests, `results/experiments/experiment_2/occlusion_*` and `representative_checkpoints.csv`. Thread 5 may import from `src/occlusion.py` (`explain_on_device`, `pixel_map`, `groups`); changes there are exact-string edits.
