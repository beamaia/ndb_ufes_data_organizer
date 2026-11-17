# Thread 9: literature research for the thesis (references that back each section)

Read `README.md` of this folder first (rules). This thread finds, checks and records sources; it does not write the thesis text.

## What the user wants (2026-11-14)

A research thread for the thesis. The thesis outline the user gave (below) needs sources for each section; the slides already cite some. The goal is a bibliography that backs every claim she is likely to make, with each source checked, so she can write without searching.

## The thesis outline (from the user, 2026-11-14)

- **Introduction.** CAD in many areas; difficulties; data leakage exists in many datasets, medical and not (it is not exclusive); then OSCC and dysplasia levels and how they make analysis harder.
- **Motivation.** Models struggled on very large images; patches were introduced to help CAD (zoomed crops lose less information than shrunk images); data collection is dynamic, and a possible bias from data leakage in the patches crept in.
- **Objectives.** Link patches to their parent picture; investigate whether this introduced leakage and, if so, how much it may have influenced the results, by repeating the experiments with the previous folds and with new folds that ideally have no contamination.
- **Document structure.** Written last.
- **Theoretical background.** Data leakage; feature matching; template matching; SIFT; cross-correlation (?); mean-shifted (zero-mean) cross-correlation (?); sum of squared differences (?); neural networks, neuron, bias, fully connected, activation functions; convolutional networks, convolution, the types; transformers, how they work, the types; loss functions, entropy, cross-entropy; cross-validation; metrics (accuracy, precision, recall).
- **Datasets.** NDB-UFES, P-NDB-UFES, SAB, patches.
- **Data leakage chapter.** Go through all the information: template matching and SIFT; the kinds of contamination (patch level, patient level); multiple pictures linked to patches; the two experiments referenced as possible results, and the CSVs with the censored information; emphasis on the dysplasia problem; the zoom question; results on the new P-NDB-UFES folds.
- **Experimental results.** The two experiments with the two kinds of folds; parameters and machine; Experiment 1 against the original article; Experiment 2.
- **Discussion.** Differences and dysplasia.
- **Conclusion.** Contamination exists and can influence results, but dysplasia also played a role; more investigation (remove the problematic examples, drop the three-class problem); above all the data should be reviewed by specialists; progress is cooperation between specialists and computer scientists; to generalise, human-style information is needed (is this dysplasia, or a 60% chance of dysplasia): the human view is more subjective.

## What is already in the bibliography (`bibliografia.bib` of the Overleaf project, in `presentation/thesis_overleaf/tcc2_v1/`)

- From the thesis draft: cancer statistics, early cancer, OSCC and dysplasia confusion (Speight, El-Naggar, Awadellah), LLMs in medicine, health AI foundations, medical-imaging challenges, black box, adoption, data leakage in several areas (competitions, KDD, medical competitions), transfer learning, patch-based classification, autoencoders and VAEs, neurons and CNNs, the P-NDB-UFES work (`bucal`), the NDB-UFES dataset (`falcaosab`).
- Added 2026-11-14 from the slides: Bussola 2021, Kapoor and Narayanan 2023, Nogueira and Gomes 2026, Roberts 2021, Rosenblatt 2024, Samala 2020, Yagis 2021 (leakage); Kujan 2006, Ranganathan 2020, Gopinath 2025, Kallarakkal 2024 (dysplasia grading); Lowe 2004 and the two OpenCV tutorials (SIFT, template matching).
- Added the same day for the models: Vaswani 2017, Dosovitskiy 2021, Liu 2021 (Swin), Simonyan 2014, He 2016, Huang 2017, Sandler 2018, Liu 2022 (ConvNeXt), Heo 2021 (PiT), Xu 2021 (CoaT), Tan and Le 2019, Fischler and Bolles 1981 (RANSAC), Brodersen 2010.

## Gaps to research (check the bibliography before adding; do not duplicate)

1. Data leakage outside medicine (the definition, a taxonomy, examples in machine learning generally), and Kaufman et al. 2012, which several papers cite for the formal definition.
2. Template matching and its scores: sum of squared differences, cross-correlation, zero-mean normalised cross-correlation; a book or survey rather than only the OpenCV page.
3. Feature matching in general (before SIFT): descriptors, ratio test; and a source for the 0.7 ratio test, if Lowe's paper gives it.
4. Neural network basics (neuron, bias, fully connected layers, activation functions: sigmoid, ReLU and others) and convolution types (depthwise, dilated, residual and dense connections), each with a primary or textbook source.
5. Transformers: attention, the vision transformer family, hierarchical and hybrid types (Swin, PiT, CoaT are added; check that "types" is covered).
6. Loss functions, entropy, cross-entropy (Shannon is in the bibliography), class weighting.
7. Cross-validation (a primary or standard source, including why a fold per case group matters) and metrics: accuracy, precision, recall, balanced accuracy, ROC AUC.
8. CAD in different areas, and digital pathology and whole-slide images for OSCC (the user's introduction).
9. Specialist disagreement on dysplasia (done for four papers; look for oral-pathology guidance on grading and on binary systems) and human uncertainty representation (the conclusion: "60% chance of dysplasia").
10. Patch-based classification of whole slides: why patches, the loss of information when shrinking, and known problems when patches of one slide are split between training and test (Bussola 2021 is in; look for others).
11. The oral cancer datasets and the article the study repeats (`bucal`); other studies that used NDB-UFES or P-NDB-UFES, and whether they split by patient.

## Method

- Search the web, then CHECK each source: DOI in Crossref (`https://api.crossref.org/works/<doi>`), abstract in Europe PMC or the publisher page; never cite from memory or from a search snippet. Record only what the abstract or page supports; mark a claim "abstract only" when the full text was not read.
- Add each source to `bibliografia.bib` with its Crossref BibTeX (check the key does not exist; style `abntex2cite` with `alf`), and to a table in `notes/literature/sources.md`: key, one line on what it says, which section of the thesis it backs, how it was checked (DOI verified, abstract read, full text read), and a confidence note.
- Prefer primary and peer-reviewed sources; mark preprints. Say plainly when no good source was found.
- Do not send private data (case names, SAB paths, the user's email) in any query.

## Questions to ask the user first

1. How many sources per topic (a short list of the best, or broad coverage)? Is there a page or reference limit?
2. Portuguese-language sources (for example Brazilian oral pathology guidance) as well as English?
3. Which topics matter most for the committee, so those get depth first?
4. Is a short "reading list" (what to read in full, in order) wanted in addition to the bibliography?

## Deliverables

`notes/literature/sources.md` (the table above), additions to `bibliografia.bib` as a separate block with a date comment, and, at the end of each work session, a message to the user listing what was added and which topics are still thin. No text for the chapters.

## Files this thread owns

`notes/literature/` (new), the appended blocks of `presentation/thesis_overleaf/tcc2_v1/bibliografia.bib`. The user copies the bibliography back to Overleaf; the folder itself is not a repository.

## Plan

(empty: the first session fills it in)
