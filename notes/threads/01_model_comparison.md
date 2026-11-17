# Thread 1: comparing the models statistically

Read `README.md` of this folder first (rules). This brief is what has been done and decided so far.

## What the user wants to understand

- Why the old analysis used Wilcoxon, and why it cannot work with five folds.
- What the published article did (and why it could reach significance).
- Why the comparison runs only on the test fold, and what it does and does not cover.
- Why the experiment is not repeated (other seeds, other test folds).

## The answers so far

- **Old thesis analysis** (deleted from the repository, still in git history of `ndb_ufes_data_organizer`, `results/thesis_experiment_analysis/analyze_canonical_mlflow_runs.py`): Friedman across three CNNs as a gate; Wilcoxon with Holm only if Friedman was significant. Friedman gave p=0.074 (Experiment 1) and 0.247 (Experiment 2), so the Wilcoxon step never ran (its table has only a header). It could never have flagged a pair anyway: paired over five folds, the smallest two-sided Wilcoxon p is 2/2^5 = 0.0625. Between experiments it used Mann-Whitney (unpaired, 5 against 5, smallest p 0.0079), which did reach significance (all three CNNs, Holm 0.024).
- **The article** (Maia et al., Expert Systems With Applications 241, 122418, 2024, section 3.3): all results of one architecture family pooled as one population, Shapiro-Wilk (not normal) and Levene (not equal spread), Kruskal-Wallis as the omnibus test, Conover-Iman post-hoc with Holm-Sidak, critical-difference diagrams; and a t-test best CNN (DenseNet-121 91.91%) against best transformer (CoaT 90.84%), p=0.02. Those tests treat fold scores as independent observations, which they are not quite (the fold models share most training data), so their p-values lean small. Pooled groups and unpaired tests are why significance was reachable there.
- **The test fold.** The metric is `test_patch/balanced_acc` of each of the five fold models of an architecture, all tested on the same test fold (fold 5). `fold` in `fold_metrics.csv` is the validation fold used while training that copy, not the data the score is computed on. What this does not cover: uncertainty from the test set itself (about 10 patients, 39 pictures); a different test fold could rank the models differently.
- **Why not repeat.** Other seeds on the same split cost about $5.50 for a full set of 12 and only reduce training noise. Rotating the test fold over six folds costs about six times that (about $33); the RunPod balance is about $3. The free alternative is the validation-fold predictions (`src/validation_predictions.py`: patients a model did not train on), optimistic because the validation fold chose the best epoch; it needs the checkpoints of every fold back from S3. The recommendation was to state in the thesis that only one test fold was used and why.

## Code and results

- `src/model_comparison.py`, `tests/test_model_comparison.py`, README section of the training repository. Main analysis = the article's (Shapiro, Levene, Kruskal-Wallis, Conover-Iman Holm-Sidak, critical-difference diagram, CNN against transformer pooled with Mann-Whitney); check = Friedman and Nemenyi (paired). Needs `scikit-posthocs` (dev dependency, added to `pyproject.toml`).
- Command: `uv run python -m src.model_comparison --results ../ndb_ufes_data_organizer/results/experiments/experiment_2` (and `experiment_1`). Writes `model_ranking.csv`, `model_pairs.csv`, `model_critical_difference.png`, `model_selection.md` there; reads `fold_metrics.csv`, no MLflow needed.
- Experiment 2: Kruskal-Wallis 22.19, p=0.0229; Friedman 22.17, p=0.0231; Nemenyi critical difference 7.45 rank units. Best CNN VGG16 58.7% (tied with the other six CNNs), best transformer Swin-T 61.4% (tied with the other four); Swin-T is separable only from EfficientNet-B3 and ResNet-50. CNN against transformer pooled: medians 56.3% against 59.8%, Mann-Whitney p=0.0022 (too small: 35 and 25 scores that are not independent).
- Experiment 1: Kruskal-Wallis 23.49, p=0.0151; Friedman 23.00, p=0.0177. Best Swin-B 91.3%, separable only from ViT-S. CNN against transformer: medians 90.1% against 90.0%, p=0.45 (like the article).
- Shapiro-Wilk with five scores almost never rejects: report it because the article did, do not read it as "normal".

## Pending

1. A bootstrap that resamples the test pictures (picture-cluster), pair by pair, as a second check that speaks to test-set uncertainty (the plan was to add it next to Friedman; the user was asked, not yet answered).
2. Reading note for Claude Science: `notes/statistics_and_explainability_for_literature.md` (reading list from memory, to be verified by Claude Science before anything is cited; least sure: Bussola et al. 2021).
3. The user may decide to use the validation-fold view as a second analysis.

## Files this thread owns

`src/model_comparison.py`, `tests/test_model_comparison.py`, `results/experiments/*/model_*`, the notes file above.
