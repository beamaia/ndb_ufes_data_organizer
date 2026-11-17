# Thread 6: the presentation (the last thread, integrates the others)

Read `README.md` of this folder first (rules). This thread owns the deck and builds the slides from what the other threads deliver; it starts last because there is a lot of material, and it begins with an inventory, not with writing slides.

## Where the deck is

`thesis_organization/presentation/` (the umbrella repository, listed in its `.gitignore` as "private LaTeX presentation, only for me, holds private images": never commit, publish or copy it). It holds two things:

- A LaTeX Beamer deck with the LabCIn/UFES theme: `main.tex`, `beamerthemelabcinufes.sty`, `labcinufes-example.bib`, `seções/` (`01-intro`, `02-autoencoders`, `03-vae`, `04-metrics`, `05-future_work`, `exemplos/`), `img/`. It started as a VAE thesis presentation (`vae_tcc_presentation.zip`, shared 2026-10-27) and contains one SAB picture whose file name carries a SAB case identifier (`img/assets/<case>-<uuid>.png`, 8 MB): private.
- A web deck, `web/index.html`, whose titles are `h2` elements. The figures for it that use SAB pictures are made by `ndb_ufes_data_organizer/scripts/phase2.py slides --out <folder>` (`scripts/src/phase2_report/slides.py`) and written only to the folder given, never to the wiki.

Another session (the fork "Thesis dataset organization and contamination") has been working on the web deck with the user (all slide titles brought to one line; the user is walking through the dataset topics one by one: morphology clusters first, then the others, after judging the zoom by hand in `results/phase0/picture_relations/zoom_review.csv`). Find out in the first turn which deck is the target for the new material (probably the web deck, the Beamer deck being the older VAE one), and do not undo or duplicate what that session did: read `web/index.html` and the git-ignored folder as they are now.

## Material the other threads produce (slide-worthy)

- Thread 1 (model comparison): the critical-difference diagrams (`results/experiments/experiment_N/model_critical_difference.png`), `model_selection.md`; one slide on why Wilcoxon cannot work with five folds, one on "the models cannot be told apart" with the numbers (Experiment 2: Kruskal-Wallis p=0.023, only Swin-T separable from EfficientNet-B3 and ResNet-50).
- Thread 2 (Experiment 1 against 2): published folds 88.2-91.3% against new folds 54.5-61.4% (balanced accuracy); the ranking does not reproduce (rho = -0.406, not significant; say "does not reproduce", not "inverts"); with-dysplasia recall 87-92% against 45-53%; the panel figures (`panel_n_correct.csv`), the label-authority table.
- Thread 3 (AUC against balanced accuracy): per-class AUC.
- Thread 4 (occlusion): `occlusion_logit_mean_maps.png`, `occlusion_logit_vgg16.png` and the other examples, the overlap scatter `occlusion_logit_overlap.png`; one slide on what occlusion is (a window covered with white slides over the patch; the drop of the class score is its importance; 7 x 7 positions).
- Thread 5 (zoom): only after the user's zoom review.
- Dataset slides already in the deck: regions of whole patches, joined regions, clusters, zoom (do not rewrite them).

## Rules specific to this thread

- A slide title is ONE line: measure `h2` in the browser at a slide width of 1,400 px after every edit (the fork reported all titles fit, the longest at 91% of the width). Keep titles short ("Joined Regions - Regions of whole patches").
- Say "dark regions" and "equivalent diameter", never "nuclei". Describe maps only structurally (centre or border, focal or spread).
- Private pictures (SAB, case names in file names) stay inside `presentation/`; never put them in a repository. Figures from `results/experiments/` (public tables) are fine to copy into the deck.
- She understands and defends every slide: for each new slide, write two plain sentences of what it says and what it does not show (the limits listed in the README rules), as notes for her.
- She runs commands and commits; the deck is not versioned. Change `main.tex` or `web/index.html` with exact-string edits.

## First turn

1. Inventory: list the slides of the web deck (titles only) and the Beamer sections, and what each thread has delivered so far (files in `results/experiments/`).
2. Propose an outline of the model-results part of the talk in the order: what was trained, the two experiments and why the leak matters, the comparison and its limit, AUC against balanced accuracy, what the models use (occlusion), zoom; mark what is missing for each.
3. Ask which deck, then build slides one at a time, waiting for her review of each.

## Files this thread owns

Everything under `presentation/` (not versioned) and any figure script it adds for the slides (`scripts/src/phase2_report/slides.py` is the dataset side; coordinate by exact-string edits).
