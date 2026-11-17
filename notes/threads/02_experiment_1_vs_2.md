# Thread 2: Experiment 1 against Experiment 2

Read `README.md` of this folder first (rules).

## What the user wants to understand

Claude Science (the user's literature assistant) said that the ranking of the 12 models inverts between the two experiments (Spearman rho = -0.406; swin_base 1st then 9th, resnet50 2nd then 11th, vit_small 12th then 2nd), that performance under the published folds "carries no usable information" about which architecture is better, and that the dysplasia difficulty was invisible under the published folds (with-dysplasia recall 87.4-92.2% in Experiment 1 against 45.0-53.3% in Experiment 2; dysplasia the worst class in 3 of 12 models against 12 of 12), adding that the hard part "coincides with where expert agreement is lowest".

## Checked against `results/experiments/*/summary.csv`

- rho = -0.406 is correct (sum of squared rank differences 402, n=12; p about 0.19, not significant); the three rank examples, the recall ranges and the 3-of-12 / 12-of-12 counts are all correct (in Experiment 1 the three are swin_base, resnet50 and mobilenetv2).
- Experiment 2 patch balanced accuracy 54.5-61.4%, Experiment 1 88.2-91.3%; AUC in Experiment 2 71.5-75.9.

## Wording that was suggested instead

1. "The ranking inverts" is too strong: both rankings are mostly ties. Experiment 1: only ViT-S is separable from the best (Swin-B). Experiment 2: only EfficientNet-B3 and ResNet-50 are separable from the best (Swin-T). Say "the ranking does not reproduce, and the few models that can be separated from the best differ between the experiments". ResNet-50 is tied for best in Experiment 1 and below the best in Experiment 2, ViT-S the reverse; but "significant in one and not in the other" is not "the difference between experiments is significant" (a direct per-model test between experiments is needed: Mann-Whitney as in the old analysis).
2. The two experiments differ in more than contamination: different test sets (published sixth fold against fold 5 of the new folds) and different training sets. The comparison shows the published folds do not predict the ranking under clean folds; it does not isolate the leak as the cause.
3. "12 of 12" is not 12 independent confirmations: all 12 models are tested on the same patches and err together. Say "consistently across architectures on this test fold". The test fold has one without-dysplasia patient, so "without" recall is based on very few patients.
4. "Where expert agreement is lowest" is a literature claim to be confirmed and cited by the literature search (inter-observer variability of oral epithelial dysplasia grading is documented; whether it is lowest for the with/without distinction used here is not verified).
5. Experiment 1 comparison output (Thread 1) shows CNN against transformer equal under the published folds (p=0.45, as in the article) and transformers ahead under clean folds (p=0.0022, over-confident because of pooling). Describe as an observation.

## Related analyses already done (all from stored predictions)

`src/panel.py` writes to `results/experiments/experiment_2/`: `panel_patches.csv` (what each model says, `n_correct`, consensus, mean severity), `panel_n_correct.csv`, `parent_vs_label.csv` (the patch label against the diagnosis of its picture, all 3,763 patches; the number 522 = OSCC pictures holding with-dysplasia patches, 34.4%, comes from the October table, not from the July `research_ready_tables/` that Claude Science read before and that was deleted), `label_authority.csv`. Earlier results: severity skipping 1.92%, 88% of errors between with-dysplasia and OSCC, with-dysplasia patches whose parent picture is OSCC are called OSCC by 94% of models, escalation of mean predicted severity (1.258 for with-dysplasia, pushed upward). The notebook `notebooks/exp2_explainability.ipynb` still defines these functions itself; swap them for imports from `src/panel.py` once the user has saved the notebook.

## Pending

1. Cross-experiment rank correlation and direct per-model tests between experiments as repeatable code (the rho was computed by hand), probably as an addition to `src/model_comparison.py` (coordinate with Thread 1, edit one passage only).
2. Thesis wording for the paragraph above.
3. Optionally the same panel export for Experiment 1: `uv run python -m src.panel --experiment ndb_ufes_exp1 --out ../ndb_ufes_data_organizer/results/experiments/experiment_1`.

## Files this thread owns

`src/panel.py` (and the notebook swap), `results/experiments/*/panel_*`, `parent_vs_label.csv`, `label_authority.csv`.
