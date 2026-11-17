# Thread 8: plan the redesign of the slides website (usability and how things are represented)

Read `README.md` of this folder first (rules). This thread starts as a PLAN: do not change code until the user has approved the plan.

## What the user wants (2026-11-14)

The website (the slides in the browser, `presentation/web/`, served with `python3 -m http.server 9410 --bind 127.0.0.1` from that folder, or the `presentation` entry of `.claude/launch.json`) is up and running. She wants it improved: easier to use and better at representing the material. Plan it first, thinking of usability and representation, using the design skills. The user edits her own slide wording; a design pass changes layout, structure, charts and interaction, not what a slide claims, unless she asks.

## What exists (facts, 2026-11-14)

- 62 slides in 13 sections (Motivation, Data, Linking, Linked Data, Folds, Experiments, Results, Statistical Analysis, Error Analysis, Explainability, Conclusion, References, plus title and outline). `index.html` (about 570 lines), `deck.js` (about 680), `deck.css` (about 185), Plotly in `vendor/`. Data comes from CSVs in `results/experiments/` and `results/phase0..2` through symlinks, read in the browser.
- Layout: 16:9 slides scaled by the viewport (`font-size: calc(min(100vw, 177.78vh) / 64)`, everything in `em`); keys: arrows, `F` full screen, `#n` in the address jumps to slide n. Slide titles must stay on one line.
- 25 charts or tables built in JS, 9 slides with controls (selects for experiment, model, class, fill) above the chart, 20 live numbers (`data-fact`), 24 images, source notes in a very small font under charts.
- Colours: class colours (without dysplasia blue, with dysplasia orange, OSCC aqua); experiment colours (Experiment 1 orange, Experiment 2 blue), which overlap with the class colours.
- Figures drawn by code for the slides: `ndb_ufes_data_organizer/scripts/phase2.py slides --out ../presentation/web/figures`.

## Things seen while building it (to check, not conclusions)

- Small figures on slides that have room for more; text-only slides next to figure slides; bullets in three densities (`tight`, `compact`, plain).
- Controls above charts make some slides feel like a web app, not a talk. Is the site for presenting, for exploring, or both?
- Two experiments are shown by a selector, one at a time; the comparison (the point of the study) is made by flipping.
- Evidence strength is invisible: a rate carried by 2 pictures looks like one carried by 20. Uncertainty is shown as mean ± sd in some places and not at all in others.
- The same colours mean classes on one slide and experiments on another.
- Navigation: no visible place in the talk (section, progress), no way to jump by section, no speaker view.
- Tiny source lines, Plotly ticks that are small at 1280 px, tables with many columns.
- Accessibility: contrast, colour-blind safe class colours, keyboard use, focus states, text size from the back of a room.

## Skills to use (in this order)

1. `superpowers:brainstorming` first (creative work: it decides the questions and the directions).
2. `design-skills:ux-strategy` and `design-skills:journey-mapping` (who watches, what they must understand at each point of the talk).
3. `design:design-critique` and `design-skills:design-critique` on screenshots of the current slides (1920 x 1080 and 1280 x 720, light room, projector), with the built-in browser (`preview_start` name `presentation`).
4. `design-skills:interaction-design`, `design-skills:ux-writing`, `dataviz` (chart forms, colour, uncertainty, small multiples), `design-skills:design-systems` (tokens: colours, type scale, spacing, slide templates).
5. `design-skills:accessibility-audit`, `design-skills:design-elevation`.
6. `frontend-design:frontend-design` only when building, after the plan is approved.

## Process

1. Audit: screenshots of every slide at two sizes, grouped by problem; what works and should not be touched.
2. Interview the user (questions below), then write the principles of the redesign (what the site is for, the one thing each section must make clear).
3. Two or three directions, each as a small HTML mock (a private Artifact is fine) of 3 representative slides: a text slide, a table, a chart with two experiments. The user picks.
4. A prioritised plan: tokens and templates first, then navigation, then the charts (evidence strength, uncertainty, both experiments side by side), then the details. Each step small, reviewable, tested in the browser (titles measured on one line, no overflow at 16:9).
5. Only then code, in small pieces; the user reviews and commits.

## Questions to ask the user first

1. Who is the audience, how long is the talk, and where (committee room, projector, screen share)? When is the date?
2. Is the site mainly a talk, or also something to explore afterwards (and to share by link)? A "present" mode (clean slides, no controls) and an "explore" mode (controls, hovers) is one option.
3. Public or private? The session of the portfolio site shows a Projects page; if any part becomes public, the rules of the SAB pictures apply (pixels with published patches may be shown; names, case ids and paths never).
4. Which slides are the ones the user is proudest of or worries about most?
5. Language of the slides (English) and of the speaker notes (Portuguese?).

## Constraints

- Private data (SAB names, case ids, paths) is never published. Weights are not shared. Say "dark regions" and "equivalent diameter", never "nuclei".
- Settings in YAML where the repository uses them; fewer files, no dead code; the user runs commands and commits; never `git add -A`.
- Port 8765 belongs to the user's Claude Science app; the deck uses 9410.
- Thread 6 owns `presentation/` (the Beamer deck and the integration of results); this thread owns the look and interaction of `presentation/web/` only. Content decisions stay with the user.

## First deliverable

The audit (screenshots and a list of problems), the answers to the questions above, and the principles, written to the "Plan" section below. No code before the user approves.

## Files this thread owns

`presentation/web/deck.css`, `presentation/web/deck.js` and the layout (not the wording) of `presentation/web/index.html`; mocks in the scratchpad or as private Artifacts.

## Plan (first session, 2026-11-14)

### The target changed: the patch playground, not the slides

Asked on 2026-11-14 by the user: this thread redesigns the **patch playground** (`ndb_ufes_training_pipeline/src/playground.html`, served by `src/playground.py` on `127.0.0.1:8870`, exported as a static copy by `src/playground_export.py`), not the slides of `presentation/web/`. Thread 7 built the playground and keeps its logic (server, endpoints, `data.json`, the export, the tests); this thread changes its look, layout and interaction, in `src/playground.html` only unless a step says otherwise. The slides redesign has not started; three things seen in passing are kept for it: the address `#n` and the footer number differ (64 sections, footer "/60"); some slides are blank until their chart draws (for example "What the linking revealed", "More severe than the picture"); the figure of "Template matching: result" prints a picture id in its title.

### Who it is for (the user's answers)

- **Tech people** who reach it from her resume, **HR people**, and **researchers** who follow the link from the thesis. Nobody is there to explain it: it must explain itself.
- The page is also evidence of her craft: a company working in this area (digital pathology, medical AI) should look at it and see a likely candidate. It must look **modern and serious**, finished, and informative.
- The one thing to leave with: **the models at work** (three models read a picture patch by patch; where they agree with the pathologists and how sure they are). The leakage story and the comparison of the models live in the wiki; the playground links to it.
- **One screen, no scrolling**, in the **light LabCIn theme of the wiki**. She likes seeing how the confidence threshold works: it stays a main feature.
- She looks at it in a window about 2000 x 1020 px: check every step at that size and at 1280 x 720, and the phone layout.

### Audit of the current page (2026-11-14)

What works and stays: the four ideas (patches, picture, grid, free crop), the threshold on every call, "No label here" for crops that are not labelled patches, the arrow keys, the fast live crop, the wiki colours, the logic of the picture call (checked against Python at load).

Problems, at her 2000 x 1020 window (and at 1024 x 768):
1. **The page scrolls.** The picture is 1428 x 1071 px, taller than the window: its bottom, the counter and the legend are below the fold (at 1024 px it is the opposite: 450 x 340 px, the outlines a tangle, grid labels 10 px). The gallery is 12 columns x 55 rows, a page of about 7,700 px.
2. **The right column** is one small card next to empty space until a patch is selected; in the picture view it grows to 1,321 px, longer than the window, so it cannot stay in place.
3. **Right or wrong is a 6 px strip** under a 119 px tile; in the inspector the call comes before the true label and below a large crop.
4. **Stale inspector:** while a grid is computed, the inspector still shows the previous view's card.
5. **Colours change meaning:** an outline is the models' call in the picture view, the true label in the free form, a filled tile in the grid. The class colours (blue, orange, green for OSCC) say OSCC is "good".
6. **Overlapping patches cannot be reached** with the mouse.
7. **The percentages are not explained:** the bars are the mean of the three models, the ribbons per model have no numbers, and in the picture view the picture's numbers and the selected patch's numbers sit one under the other, so they are easy to confuse.
8. **Plain language:** "picture diagnosis", "not in NDB-UFES", "possible zoom" lose the HR reader; nothing says who made it or links to the thesis or the wiki.

### Principles

1. **One screen.** Header, picture, readout and threshold always visible from 1280 x 720 up; nothing on the page scrolls except lists inside their own panel. On a phone the parts stack.
2. **The picture is the stage.** It always fits the space left; the pictures move like a deck of cards.
3. **One meaning per colour, everywhere.** A class colour is always the class the models give; the true label is said in words or by the wrong mark; uncertain is always hatched grey. Classes on a severity scale: without dysplasia amber `#d9a21b`, with dysplasia orange `#e06a2c` (the two leukoplakias in the middle), OSCC crimson `#a3123a`; darker with severity, so it also reads without colour vision. No green and no red for classes. A wrong call is a navy corner with a cross. (These differ from the deck's class colours; the deck is not changed.)
4. **Every number shows where it comes from.** Each model's percentage beside the mean that decides the call, and one line saying what is averaged over what.
5. **One scope at a time, named.** "This picture" or "This patch", never both open; the key of every mark sits next to the marks.
6. **Plain words first, the technical term a click away.** Honest limits (one test fold, about 10 patients, three models of one fold run for live crops, patches not independent, a class map is what the model says, not what a pathologist sees) in "How it works". "Dark regions" and "equivalent diameter", never "nuclei". No SAB names, case ids or paths.
7. **Craft in the details:** no stale content, visible progress, keyboard, focus rings, contrast, reduced motion, fast loading, her name and links.

### The design (mock B2, approved as the direction on 2026-11-14)

The mock is a throwaway file (`mock2_src.html` in the session's scratchpad, served for review on `127.0.0.1:8871`); it is not part of any repository and is rebuilt in `src/playground.html` step by step.

- **Header:** the wiki band (blue to green), the LabCIn mark, "Patch playground" and one sentence ("Three deep-learning models read oral tissue pictures one patch at a time."), the views (Pictures, All patches, Grid, Draw a crop), and links (How it works, The thesis, her name).
- **Body, three columns:** a narrow index of the 39 pictures (the current one lifted); the picture as the top card of a deck (two cards peek behind it; the next picture lifts the card up and away and the next rises; a plain switch with reduced motion); the readout panel (about 25rem).
- **Boxes on the picture:** colour of the class the models give; hatched grey when below the threshold; navy corner with a cross when wrong; when a patch is selected the others dim. Clicking again on overlapping boxes goes to the next one under the pointer; the patch panel has "‹ 1 of 18 ›".
- **Keys:** up and down go through the deck of pictures; left and right through the patches of the picture (reading order); Escape back to the picture.
- **Readout, "This picture":** the call large with its class dot, the diagnosis, a tag "Matches / Differs from the diagnosis / No published diagnosis", a table (rows: classes; columns: VGG16, DenseNet-121, Swin-T, **Mean**; the mean with a light bar, the leading row bold), a line "Each model's probability is its average over the N patches above the line; the call is the class with the highest mean of the three models", and the tally: sure and right, sure and wrong, uncertain.
- **Readout, "This patch":** the picture folds to one line with "Back to the picture"; the crop beside the call, the label, the verdict ("Right, 64% sure", "Uncertain, 54%: not counted"), the same table with "the mean of its five training runs".
- **The threshold bar at the bottom:** a slider whose track is a dot plot of the picture's patches at their confidence (colour of the call, hollow navy ring when wrong, grey below the line), the area below the line hatched, the value on the handle, the key right above the dots, ticks from "33%, a guess" to "100% sure". It replaces the slider in the header.

### Plan, in order (each step one small change the user reviews in the browser and commits)

Every step: edit `src/playground.html`; reload `http://127.0.0.1:8870/` (the server reads the page on every request: no restart); check at 2000 x 1020, 1280 x 720 and a phone width (no page scroll on the desktop sizes, no overflow, no console error); `uv run python -m pytest tests/test_playground.py -q` still passes. The assistant lists the files touched; the user commits.

1. **Tokens and theme.** Light LabCIn tokens of the wiki (`labcin.css`), Roboto, the severity class colours, the wrong mark and the hatch in one place; remove the dark scheme for now (the user asked for the light version). Nothing else moves.
2. **The one-screen shell.** Header band with the views and links; the three columns; the threshold bar at the bottom; the picture fits its space (container size, 4:3); the readout scrolls inside itself only if it must; the phone layout stacks.
3. **The deck.** The index of pictures, the card animation, up and down keys, previous and next buttons; reduced motion.
4. **The boxes.** One colour rule, hatched uncertain, the wrong corner, dimming on selection, click again to go deeper, left and right through the patches.
5. **The readout.** The two named scopes, the table with the mean and its explanation line, the tally, the patch panel folding the picture; the stale-panel bug goes away because every view writes its own panel at once ("Classifying…" in place of the old card).
6. **The threshold bar.** The dot plot slider, its key, the handle; the picture call recomputed live.
7. **All patches.** The gallery inside one screen: grouped by picture, filters in plain words (the dataset term in a tooltip), a clear right, wrong or uncertain mark on each tile; a click opens the patch on its picture.
8. **Grid** as a layer on the same card (tiles in the class colour, hatched when uncertain, labels sized to the tile), the same readout.
9. **Draw a crop** as a layer on the same card; on the static copy it says plainly that it needs the models and is local only.
10. **First visit and "How it works".** The dismissible hint; a short "How it works" panel (what a patch is, the three models, how a call is made, the threshold, the limits) with links to the wiki and the thesis.
11. **Accessibility and polish pass.** Contrast of every text, focus states, a keyboard path through every control, labels for screen readers, reduced motion, loading states; screenshots at the three sizes for the user.
12. **The static copy.** Run the export, check the folder for leaks (the export already refuses names, case ids and paths), open it without the server, confirm every view except the free crop works.

### Open, for the user before the step that needs it

- **Step 5:** in the mock the picture's call counts only the patches above the line (all of them if none is); the current page counts all of them unless "count only patches above the threshold" is ticked. Which rule should the public page use, and should the switches that leave a patch or a whole class out stay?
- **Step 1:** is light only fine, or should a dark scheme come back later?
- **Step 10:** the links (beamaia.com page, thesis PDF or repository, wiki address) and how her name appears.
- **Step 12:** where the static copy goes on beamaia.com, and whether publishing the per-patch predictions before the defence is fine (still open from thread 7).
