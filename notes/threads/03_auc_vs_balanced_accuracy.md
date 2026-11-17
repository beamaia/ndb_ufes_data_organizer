# Thread 3: AUC against balanced accuracy

Read `README.md` of this folder first (rules).

## What the user wants to understand

Claude Science said: Experiment 2 has AUC 71.5-75.9 against balanced accuracy 54.5-61.4; AUC ignores the decision threshold, so the representation carries signal and the conversion to a hard three-way decision fails, which "points at the decision boundary, not the features, as where the escalation bias lives".

## The assessment so far

1. The two numbers are not on the same scale: chance is 50% for AUC (one class against the other two) and 33% for a three-class balanced accuracy. An AUC of 74 is 24 points above chance (48% of the way to perfect); a BCC of 58 is 25 points above chance (37% of the way). The gap is smaller than "75 against 58" suggests, and three-way decisions are harder than one-against-rest rankings anyway.
2. A gap between AUC and BCC does not point at the boundary: it is also what class overlap gives, with no threshold that fixes it. The middle class (with dysplasia) cannot be separated from both neighbours by one monotone threshold.
3. The escalation result (mean predicted severity 1.258 for with-dysplasia, errors with-dysplasia to OSCC 38.5% against 12.7% to without) fits a biased boundary and fits label ambiguity equally: with-dysplasia patches whose parent picture is OSCC are called OSCC by 94% of the models, which looks like the models agreeing with the picture's context. The two explanations predict different things.
4. Supporting hint from the occlusion run (Thread 4): the models are confident when they are wrong. Mean confidence in the predicted class is 0.88 on the patches no model gets right, 0.78 on the patches every model gets right. Shared confident errors fit ambiguity better than a boundary offset.

## Tests that would separate the two

- **Per-class AUC.** Added to `src/experiment_table.py` (`summarize`: columns `AUC <class>`, each class against the other two). The summaries have to be exported again: `uv run python -m src.experiment_table --export ../ndb_ufes_data_organizer/results/experiments` (MLflow running). If OSCC and without-dysplasia AUCs are high and with-dysplasia is clearly the lowest, the middle class overlaps with its neighbours: a threshold cannot fix that.
- **Recalibration test** (not written): tune a bias for each class on the validation predictions, apply it to the test fold, and see how much balanced accuracy improves. A large gain supports the boundary; a small one supports overlap. Needs `notebooks/cache/ndb_ufes_exp2_validation.csv` (`uv run python -m src.validation_predictions --experiment ndb_ufes_exp2`, needs the checkpoints of all folds from S3, about 10 GB for Experiment 2, restore with `aws s3 sync` as in `ndb_ufes_mlflow/docs/backup-restore.md`), and a small script `src/recalibration.py` with a test. Report it as validation-fold based (optimistic: the validation fold chose the best epoch).

For Claude Science: phrase the boundary claim as a hypothesis with a test, not as a result.

## Pending

1. The user pastes the per-class AUC row after re-exporting.
2. Decide on the recalibration script (needs the validation predictions).

## Files this thread owns

`src/experiment_table.py` (the AUC columns; the rest of that file belongs to the export, coordinate by editing one passage), a future `src/recalibration.py` and its test.
