# Thread 7: a small local site to play with the test patches and a sliding window

Read `README.md` of this folder first (rules).

## What the user wants (2026-11-10)

"A little site where we can play around with the patches in the test fold and their class and how they would classify the parent image. We can use the patches as they are but also just a sliding window for fun." It is for understanding and for showing the models at work, not a result of the thesis: nothing here is a claim.

## What the site does

1. **Patches as they are.** A list of the test patches (fold 5 of Experiment 2: 656 patches, 39 pictures), filterable by patch label, picture diagnosis (NDB-UFES, or not in NDB-UFES), right or wrong call and possible zoom. For a patch: the crop, its label, the diagnosis of its picture, the probabilities of each model, and its box in the picture.
2. **The parent picture.** The picture with every test patch boxed and coloured by the class the models give it. The picture's call is made as in training (`results_summary.summarize_predictions`: the mean probabilities of its patches, the highest wins, the true class is the label most of its patches have). Switch patches on and off and watch the picture's call change; show the NDB-UFES diagnosis beside it. This is the "how would they classify the parent image" part.
3. **A sliding window, for fun.** A window the user drags over the picture (size and step adjustable; 512 is the size the models were trained on), classified live; and a scan that runs the window over the whole picture and paints the class (or the probability of one class) as a map, with the labelled patches drawn on top to compare. Say on the page that a window of another size is resized to 224 and is not what the models were trained on.

## Models

The three restored checkpoints of `results/experiments/experiment_2/representative_checkpoints.csv` (VGG16, DenseNet-121, Swin-T; fold run 3 of each, chosen on validation, not on the test fold). Load them with `src/checkpoint.py` and the preprocessing used by `src/occlusion.py` (`transform_and_white`). Optional: the stored predictions of all twelve models (`results/experiments/experiment_2/panel_patches.csv`, or the cache `notebooks/cache/ndb_ufes_exp2.csv`) for a "panel of twelve" view of the patch and picture calls, without running anything live. Experiment 1 only if its checkpoints are restored too; the pictures of its test fold also appear in training, so say so on the page.

## Design

- **A local server and one HTML page.** Python standard library or what is already in the environment; no new dependency unless needed. Bind to `127.0.0.1` only. The port 8765 belongs to the user's Claude Science app: use another (for example 8870). Settings in a YAML file or command-line flags, as in the rest of the repository.
- **The SAB pictures are private.** The server shows them only on this computer. Never write pictures, crops, case names or file names into a published place, the wiki or the deck; the page does not offer downloads.
- **Inference on the Mac** (`mps` or `cpu`, `src/config.resolve_device`). One crop takes a fraction of a second; a scan of a 2048 x 1536 picture with a step of 128 is about 100 crops; batch them and show a progress bar.
- **Reuse, do not copy.** `summarize_predictions`, `patch_table`, `load_predictions`, `occlude` geometry if a map is wanted. The aggregation and the window grid are functions with tests; the page only draws.
- **Honest limits on the page.** One test fold (about 10 patients, 39 pictures), three models of fold run 3, patches of a picture are not independent, the labels of patches and pictures disagree for some patches (patch more severe than its picture), and a class map is what the model says, not what a pathologist sees. Say "dark regions" or "equivalent diameter", never "nuclei".

## First deliverable

A short plan in this file's "Plan" section (pages, functions, what is precomputed and what is live, how the scan is batched) and the questions below, before any code. Then the code, the tests and the command for the user to run.

## Questions to ask the user first

1. Experiment 2 only, or also Experiment 1?
2. The three restored models only, or also the panel of twelve from the stored predictions?
3. For the window: a fixed size of 512 and a step the user picks, or free sizes (with the out-of-training warning)?
4. Should the page also show the occlusion map of a selected patch (the stored grids exist for the three models)?

## Files this thread owns

`src/playground.py`, `src/playground.html` (or a folder `src/playground/`), `tests/test_playground.py`, a section in the README of the training repository, and `playground.yaml` if settings are not flags. Nothing is exported to `results/experiments/` (the page works from the existing tables and the checkpoints).

## Plan (first session, 2026-11-10)

**Decided by the user (2026-11-10):** the three models only (VGG16, DenseNet-121, Swin-T); the window has a free size with the out-of-training warning; no occlusion layer in the first version; Experiment 2 only. The rest of this plan stands, with `--models` defaulting to the three and no twelve-model menu; the panel call of the twelve (`panel_patches.csv`) is shown only as a reference on the patch pages.

**What exists.** All twelve checkpoints of `representative_checkpoints.csv` are restored in `ndb_ufes_mlflow/var/mlflow/artifacts/2/` (the brief said three; VGG16 is 512 MB and ConvNeXt-L 749 MB, so models are loaded the first time they are asked for and kept). The 656 test patches are in 39 pictures (33 in NDB-UFES, 6 SAB-only); `patch_table_lab.csv` (private, git-ignored) has the SAB picture path and the box `x, y, x2, y2` of every patch. The test predictions of all models on every patch (probabilities of each fold run) are in the cache `notebooks/cache/ndb_ufes_exp2.csv` (`src.panel.load_predictions`).

**Precomputed, no inference.** At start the server builds, for every test patch and model, the mean probabilities over the 5 fold runs (what the study reports), the panel consensus, and the picture and patient groups. These feed pages 1 and 2. It reads the cache and says so if it is missing (`src.panel` fills it).

**Live, on the Mac.** Only page 3 runs a model, from the checkpoint of fold run 3 of the model chosen, with the preprocessing saved in the checkpoint (`transform_and_white`). Device from `resolve_device`, with the cpu fallback of `occlusion.explain_on_device`. The page says that this is one fold run, so its call on a labelled patch can differ from the stored mean of five.

**Pages (one HTML file, three tabs).**
1. *Patches.* Gallery and filters (label, picture diagnosis, right or wrong for the panel or a chosen model, possible zoom). A click shows the crop, the label, the picture diagnosis, the probabilities of each model as bars and the panel call.
2. *Picture.* The picture reduced for the screen with the boxes of its test patches coloured by the panel call (or one model's). A tick box for every patch: the picture's call is recomputed in the browser from the ticked patches with the training rule (mean probabilities, highest wins) for each model and the panel, beside the NDB-UFES diagnosis and the label most patches have. Untick all the patches of one class and watch the call move.
3. *Window.* A draggable box over the picture (size 128 to 1024, default 512; step set by the user) classified live by the chosen model; and a scan that classifies the window at every position (positions from the corner with the last one flush with the edge) and paints the class, or the probability of one class, as a map over the picture with the labelled patches outlined. Windows of another size are resized to the size of the model and the page says it is not what the model was trained on.

**Server.** `src/playground.py`, standard library (`http.server`), `127.0.0.1:8870`, flags `--results`, `--port`, `--device`, `--models`. The client never sends a path: it sends a picture id, a patch id, a model name and numbers, and the server looks the file up in its own table. Endpoints: patches table (JSON), picture (resized JPEG), patch crop, classify one window, scan (a job, polled for progress). `src/playground.html` is the page, plain JavaScript, no library from the network. No download buttons; the pictures stay on this computer.

**Batching.** A scan of 2048 x 1536 at size 512 and step 128 is 13 x 9 = 117 crops per model; the crops are cut with PIL, transformed, stacked in batches of 16 and run under `torch.no_grad`. Smaller windows have many more crops: the page shows the number before the scan starts and refuses more than a fixed limit unless the step is raised.

**Functions with tests (`tests/test_playground.py`).** `window_positions(width, height, size, step)` (covers the picture, last position flush with the edge, never outside it), `picture_call(probabilities)` (the same rule as `summarize_predictions`, checked against it), `scale_box` (picture pixels to the screen), the table of stored probabilities from a small fake cache, and the refusal of an unknown picture id. The page itself is checked by hand in the browser.

**Status (2026-11-10).** First version built: `src/playground.py`, `src/playground.html`, `tests/test_playground.py` (6 tests pass), README section "Playground". Checked once by the assistant on this computer: the 39 pictures and 656 patches load, unknown ids get 404, a window is 0.06 s on the Mac GPU once the model is loaded, a 35-window scan takes 2 s, and the three pages work in the browser with no console error. Not yet committed.

**Second version (2026-11-10), after the user found the first one clunky.** Redesigned in the colours of the data wiki (LabCIn blue `#365cc1` to green `#60aa26` header, navy viewer `#17315f`, soft `#f5f8fd`, Roboto, LabCIn mark), light and dark. Four views: Patches (filters as pills, tile strip = true label | models' call, inspector with previous/next), Picture (arrows between pictures, select an outline to inspect it, switch patches or classes off, "count only patches above the threshold"), Grid (replaced the window on the user's drawing: the picture cut into square tiles, 512 by default, each classified and painted with its class and percentage, striped when uncertain; select a tile or move with the arrow keys to see it in the inspector), Free form (draw a box, square by default). A global confidence threshold marks calls below it as uncertain. Crops show the true label when they overlap a labelled patch with IoU >= 0.9, otherwise "No label here" and the patches they overlap. All three models run on every crop. 8 tests pass; checked in the browser in light and dark.

**A public version on beamaia.com (asked 2026-11-10, not started).** The user wants it under Projects on her website. She clarified that the SAB pictures are not private once they hold published patches (they were left out of the publication only for lack of a picture label), so all 39 test pictures may be shown; SAB file names, case names, case prefixes and paths still never appear (use `histopath_id` or an index). A public page cannot run the models (the weights are not shared), so it would be static: an export script (`src/playground_export.py`) writes one self-contained folder (page, JSON with the stored predictions and precomputed grids at a few tile sizes, pictures and patches) that the website includes; the free form stays local only. Open: how the website is built and where its code is, whether publishing the per-patch predictions before the defence is fine, and whether the page takes the website's look (serif display headings, sans body, navy) or the wiki's.

**Not in the first version.** Occlusion maps of a patch (the stored grids exist for three models: a later layer), Experiment 1 (its checkpoints are not in the representative table; its test pictures also appear in training), anything that writes to `results/`.
