# Slide draft: data leakage and contamination

**Status 2026-11-09:** built in the deck as four slides ("Motivation - Leakage and contamination", "... in other fields", "... in pathology", "... in oral cancer"), with the references at the end of the deck ("References - SIFT", "References - Data leakage"). The deck differs from the draft below: the COVID-19 shortcut study (DeGrave et al. 2021) was dropped because a shortcut is not leakage by itself (only the site-on-both-sides case of Howard et al. 2021 stays); the sizes of the effects of Rosenblatt et al. 2024 (feature selection before the split: change in correlation 0.03 to 0.52, attention problems 0.01 to 0.48; 20% repeated subjects: 0.06 to 0.29) and the tasks and accuracies of Bussola et al. 2021 (8 breast-tumour subtypes: 0.96 with random tile splits against 0.68 by patient; no difference for tissue types) were read from the text of the papers by a subagent, so check them in the papers before presenting. The Kaggle version adds 3,968 augmented images (2,204 normal + 1,764 OSCC) to the 1,224 originals. The 2026 paper is cited as Nogueira and Gomes (first author Marcelo Nogueira), not Gomes et al.


For thread 6 (the presentation). Requested by the user on 2026-11-09: one slide on what data leakage and contamination are, with references, and examples outside and inside oral cancer (OSCC) and histopathology. The slide is dense: if it does not fit one slide with readable type, split it in two (A: what it is and where it happens in general; B: oral cancer and this thesis). One-line titles, measured at 1,400 px.

## How every reference below was checked

Marked **read**: taken from the text and the reference list of Nogueira and Gomes 2026 (SN Computer Science 7:530), which the assistant read in full text on 2026-11-09. Marked **web**: checked on 2026-11-09 against the publisher, PubMed or arXiv record (title, authors, venue, year; only the abstract or metadata was seen, not the full text). Nothing is quoted from the papers; the wording below is a paraphrase.

## Slide text

**Title:** Data leakage and contamination

**Definition (two lines)**
- Leakage: information from outside the training data, such as the test set, shapes the model, so the test result is better than the real performance.
- Contamination: test samples, or near copies of them, are present in the training data.

**Column 1: how it happens**
- Normalising or otherwise preparing all the data before splitting it (preprocessing leakage).
- Putting related samples on both sides of the split: the same patient, the same slide, augmented copies of one image, overlapping patches of one picture.
- Augmenting before splitting, or augmenting the test set.
- Size of the effect in oral cancer histopathology (Nogueira and Gomes 2026, 11 models): preprocessing leakage about +1.8% accuracy; original and augmented copies mixed across splits about +14.3% on average, up to +18%.

**Column 2: outside oral cancer**
- Many fields of machine-learning-based science: Kapoor and Narayanan 2023, Patterns 4(9):100804 (**read**: cited in the reference list as the review of leakage and the reproducibility crisis).
- Neuroimaging: Rosenblatt et al. 2024, Nature Communications, "Data leakage inflates prediction performance in connectome-based machine learning models" (**read**, as listed there; the listing gives a doi that looks mismatched, so take the doi from the journal).
- A catalogue of leakage scenarios: Sasse et al. 2025, Journal of Big Data (**read**, as listed).
- Digital pathology, tiles of one subject on both sides of a split: Bussola et al. 2021, "AI slipping on tiles: data leakage in digital pathology", ICPR 2021 Workshops, LNCS 12661, pp. 167-182, doi 10.1007/978-3-030-68763-2_13 (**web**). Its abstract reports scores inflated by up to 41% when tiles of the same subject are in both training and validation, over 4 tasks, 3 datasets, 374 subjects and more than 27,000 tiles.
- Shortcuts instead of tissue: DeGrave, Janizek and Lee 2021, "AI for radiographic COVID-19 detection selects shortcuts over signal", Nature Machine Intelligence 3:610-619, doi 10.1038/s42256-021-00338-7 (**web**); Howard et al. 2021, "The impact of site-specific digital histology signatures on deep learning model accuracy and bias", Nature Communications 12:4423, doi 10.1038/s41467-021-24698-1 (**web**).

**Column 3: inside oral cancer histopathology**
- The public dataset (Rahman et al. 2020, Data in Brief): 1,224 images from 230 patients, at 100x and 400x (**read**).
- A Kaggle copy of it has 5,192 images, grown by augmentation, and the page does not say so (**read**).
- Several Kaggle notebooks and papers put augmented copies of one image in both training and test, or augmented before splitting, or augmented the test set (5,000 test samples reported) (**read**; one notebook is titled with "98.7% accuracy").
- Leak-proof work: split first, then augment: Soni et al. 2024, BMC Oral Health, best 86% (EfficientNetB0); Nogueira and Gomes 2025, BIOSTEC, 87.1% (**read**).
- This thesis (P-NDB-UFES): patches cut next to each other overlap, and in the published folds 95% of the patches have a neighbour sharing at least a quarter of their area in another fold; about 84% of the overlapping pairs are split across folds. Retrained with folds that keep every patient, picture and group of related pictures together: balanced accuracy falls from about 90% to about 58% (mean of 12 models, Experiment 1 against Experiment 2).

**Footer:** one-line list of the references as short tags, in the order used.

## Notes for the speaker (what it says, what it does not show)

- It says: the same mechanism, near copies on both sides of a split, is documented in many fields and in oral cancer, and it can inflate results by many points. It does not show that every published OSCC result is wrong: some papers split correctly.
- The +14.3% of Nogueira and Gomes is accuracy on a two-class task (normal against OSCC) against baselines taken from published work; the thesis gap of about 32 points is balanced accuracy on a three-class task with the same 12 models retrained. The two numbers are not comparable one to one; say so if someone puts them side by side. The two thesis experiments also differ in test set, not only in leakage.
- Whether to show the thesis's own earlier article (DenseNet-121 91.91% on the published folds) is the user's decision: it is her own paper.

## Open points

1. Which references go on the slide. All of them are now checked (**read** or **web**); Claude Science can confirm them and add them to the user's own library.
2. One slide or two.
3. The Rosenblatt doi in the reference list looks wrong (it repeats the doi of Kapoor and Narayanan); use the journal's.
