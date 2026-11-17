# Thread 5: explainability by zoom (plan only)

Read `README.md` of this folder first (rules). This thread starts as a plan. Do not write analysis code until the user has finished judging the zoom (below); new ideas go to the Backlog of `notes/thesis_notes.md`.

## What "zoom" is in this project

- The images of NDB-UFES were taken from slides with the 10x and 40x objectives (`docs/about-the-data.md`). The pictures that show the same tissue, zoomed or shifted, are tied by SIFT into picture groups: 92 pairs of strongly related pictures in 75 groups (`results/phase2/tables/related_pictures.csv`: `picture_a`, `picture_b`, `zoom_factor`, `zoomed` = zoom above 1.25). 1,237 patches (33%) also appear, confirmed by projection, in a related picture (patch table columns `other_confirmed_pictures`, `other_confirmed_picture_ids`; picture table `overlap_with_group`: how much of one picture is seen in the other, and the scale between them). See `docs/data-dictionary.md` and `docs/factsheet-p-ndb-ufes.md`.
- `results/phase0/picture_relations/zoom_review.csv` (288 rows): for every picture of a group, the objective level derived from SIFT (`sift`, `relative_zoom` against `relative_to`, `derived`, `possible_zoom`, `evidence`) and the column `verdict` where THE USER records by eye whether they agree. The user judges the zoom themselves; the assistant only shows images and never decides it. An analysis by zoom may only use relations the user marked as agree.

## Two readings of "explainability by zoom" (the user did not say which; ask in the thread, probably both)

1. **Same tissue across zoom.** Like the overlap test of Thread 4, but across scale: for a patch that appears in a related picture at another zoom, take the same region from the other picture (crop at the right scale, resize to what the model sees), run the occlusion maps on both views, put them in a common coordinate system through the known projection, and correlate the importance of the same tissue. Also: does the model give the same class to the two views? Direct follow-up of `content_rho` (same tissue matters wherever it sits) with scale instead of position.
2. **Stratify by objective level.** Results and maps by 10x against 40x: accuracy per level, how focal the maps are, whether the evidence sits in the same kind of place. Only pictures in a group have a derived level; the other pictures have none, so say how many are covered.

## Things to check when the work starts

- How many patches have a confirmed projection into a picture with zoom at or above 1.25, and in which folds (the new folds keep a group in one fold, so both views are in the same fold; for Experiment 2 only test-fold patches are used for the test-set maps).
- That the patches are 512 x 512 crops at known positions (`x, y, x2, y2`, all `match_status` exact), in the pixel space of the SAB picture (`data/SAB`, private; never publish crops or names).
- The models see 224 x 224 (VGG16, DenseNet-121, Swin-T): a 512 crop is resized; a zoomed-out view must be cropped to the same tissue and resized the same way.
- Reuse `src/occlusion.py` (`explain_on_device`, `pixel_map` with `signed=True`) and `src/occlusion_overlap.py` (block-averaged Spearman in picture coordinates) and the three restored checkpoints (`results/experiments/experiment_2/representative_checkpoints.csv`).

## First deliverable

A short plan (what to measure, which patches and relations qualify, how many, what the figure would show) written to the Backlog of `notes/thesis_notes.md` with an exact-string edit, and the list of relations marked agree once the user has finished the review. No code before that.

## Files this thread owns

`src/zoom_*` and `results/experiments/experiment_2/zoom_*` (none yet).
