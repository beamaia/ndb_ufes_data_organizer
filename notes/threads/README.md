# Threads

Written 2026-11-06. The work on the trained models is split into threads, one for each point the user wants to understand. Each thread has a brief in this folder; a new session starts with "read notes/threads/README.md and then the brief of thread N, and continue". The user is Beatriz Maia (thesis, UFES / Labcin). Answer in the language the user writes in (Portuguese lately, English before); files in the repositories are in English.

| # | Brief | Thread |
|---|---|---|
| 1 | `01_model_comparison.md` | Comparing the models statistically: Wilcoxon, Nemenyi, the method of the article, the test fold, repeating the experiment |
| 2 | `02_experiment_1_vs_2.md` | Experiment 1 against Experiment 2: the ranking does not reproduce, dysplasia as the hard class |
| 3 | `03_auc_vs_balanced_accuracy.md` | AUC against balanced accuracy: decision boundary or label ambiguity |
| 4 | `04_occlusion.md` | Occlusion maps: what the models use, the corners of VGG16, overlapping patches |
| 5 | `05_explainability_by_zoom.md` | Explainability by zoom (plan only, waits for the zoom review of the user) |
| 6 | `06_presentation.md` | The presentation (last thread: integrates what the others deliver; owns `presentation/`) |
| 7 | `07_patch_playground.md` | A small local site to play with the test patches, how they classify the parent picture, and a sliding window (private pictures: local only) |
| 8 | `08_site_design.md` | Redesign of the patch playground (`src/playground.html`, the site of thread 7) for the public copy: one screen, the light LabCIn theme, the models at work; plan written 2026-11-14, no code until approved (first meant for the slides website, redirected by the user) |
| 9 | `09_literature_research.md` | Literature research for the thesis: checked sources and BibTeX for each section of the outline, no chapter text |

Closed, for reference only: storage, versioning and costs (see the memory note on storage and the layout in `results/experiments/`).

## Repositories

The folder `thesis_organization/` holds `ndb_ufes_data_organizer` (the dataset, the folds, the wiki, `results/experiments/` with the exported results), `ndb_ufes_training_pipeline` (training, the analysis code in `src/`, the notebooks) and `ndb_ufes_mlflow` (MLflow on this computer, checkpoints archived in `s3://ndb-ufes-mlflow/artifacts/`). Experiment 1 is trained on the folds published with the dataset (they leak), Experiment 2 on the new leakage-safe folds (the official one). Fold 5 is the test fold in both. MLflow experiments `ndb_ufes_exp1` and `ndb_ufes_exp2`. Results of both are in `ndb_ufes_data_organizer/results/experiments/experiment_1` and `experiment_2`.

## Rules for every thread

1. **The user runs commands and commits.** Write the code, test it with `uv run python -m pytest tests/<file> -q` (from the training repository), and give the user the command to run. Never commit, never delete, never `git add -A`. At the end of a turn, list the files touched, so the user can commit by topic with a short lowercase conventional message (`feat:`, `fix:`, `docs:`, `chores:`).
2. **Repeatable code only.** No scratch or inline analysis: put it in `src/` with a test, document it in the README of the training repository, and give the command. Fewer files and no dead code: join small modules, delete what is unused in the same pass.
3. **Several sessions share one working tree.** Each thread owns its files (named in its brief). Shared files (`README.md`, `pyproject.toml`, `uv.lock`, `src/occlusion.py`, `main.tex` of the deck) are changed only with an exact-string edit of one passage, never rewritten; read the file again before editing it. Output files are prefixed by topic (`model_*`, `panel_*`, `occlusion_*`, `zoom_*`).
4. **Never read or print `.env` values**, never ask for tokens. Private data (SAB, case names, the case-named picture in the deck) is never published. Trained weights are not shared.
5. **The presentation.** The deck is a private, gitignored LaTeX Beamer folder. A thread that wants a slide writes its own section file and adds only its own `\input` line to `main.tex`; it never touches the theme or other sections. Titles on one line (measure them), and say "dark regions" and "equivalent diameter", never "nuclei".
6. **Be honest about limits.** One test fold (about 10 patients, 39 pictures); the twelve models share data, folds and preprocessing, so their agreement is not independent evidence; patches of a picture are not independent observations. Name what a result does not show.
7. **New ideas** that are not part of the thread go to the Backlog section of `notes/thesis_notes.md` (this folder's parent), not into code.
