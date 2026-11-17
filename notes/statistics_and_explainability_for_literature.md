# Statistics and explainability, for the literature search

Written 2026-10-25. It explains what the analysis of the trained models does and why, in plain words, and lists what to read. It is meant to be improved: the reading list is written from memory, so every reference must be checked (authors, year, venue) before it is cited, and anything missing should be added. Results are in `results/experiments/` of this repository; the code is in `ndb_ufes_training_pipeline`.

## What was done

Twelve architectures (7 CNNs: ConvNeXt-L, ResNet-50, DenseNet-121, VGG16, MobileNetV2, EfficientNet-B0 and B3; 5 transformers: Swin-T and Swin-B, ViT-S/16, PiT-S, CoaT-lite) were trained on P-NDB-UFES in two experiments with the same protocol. Experiment 1 uses the folds published with the dataset, which leak (patches of one picture and of one patient are in different folds). Experiment 2 uses new folds that keep every patient, picture and group of related pictures in one fold. Fold 5 is the test fold in both. Each architecture has five trained copies, one for each choice of validation fold among folds 0 to 4, and all five are tested on the same test fold. Balanced accuracy on the test fold goes from about 88 to 91% in Experiment 1 and from about 54 to 61% in Experiment 2.

## Questions the analysis answers, and the method used

1. **Do the architectures differ at all?** Method of the published article (Maia et al., Expert Systems With Applications 241, 2024): Shapiro-Wilk and Levene to check the assumptions, Kruskal-Wallis over the models, Conover-Iman for every pair with the Holm-Sidak correction, a critical-difference diagram, and CNNs against transformers with the scores of each family pooled. This treats the five fold scores of a model as independent observations. They are not quite: the five copies share most of their training data, so these p-values lean small.
2. **The same, as a paired check.** Friedman test (the five folds are blocks, the models are treatments) and the Nemenyi comparison with its critical difference. A paired Wilcoxon test was dropped because with five folds its smallest possible p-value is 2/2^5 = 0.0625.
3. **Which models to explain?** The best CNN and the best transformer by mean balanced accuracy, together with the models that cannot be told apart from each one. With a gap of a few points and a spread of 2 to 3 points between the copies of one model, the expected finding is "no model is clearly better", and the choice by mean is then stated as a choice.
4. **Do the models follow the label of the patch or the diagnosis of its picture?** The twelve models are treated as a panel. For each patch: how many models get it right, the consensus, the mean predicted severity. The patches of one label are then split by the diagnosis of their parent picture (the label-authority test).
5. **Where in the patch is the evidence?** Occlusion maps (a white square slides over the patch; the drop of the class probability is the importance of that square) on one CNN and one transformer, for four groups of patches: the model agrees with the parent picture, genuine model error, unanimously correct, unanimously wrong. Grad-CAM only for the CNNs. Maps are described structurally (epithelium, stroma, border), never with histological feature names.

## Known limits, to be stated in the thesis

- One test fold: about 10 patients and 39 pictures. Differences between models are measured on that one set, so a different test fold could rank them differently. Rotating the test fold would cost six times the training budget (about $33 against about $5.50), which was not available.
- The patches of one picture are not independent observations; the picture or the patient is the unit that counts.
- The twelve models share data, folds and preprocessing, so agreement between them measures how much the answer depends on the architecture with the data fixed. It is not agreement between independent observers (no Fleiss kappa).
- Validation-fold predictions (patients a model did not train on) are optimistic because the validation fold chose the best epoch.

## What to read

Written from memory; verify each one.

**Comparing classifiers statistically**
- Demšar, J. (2006). Statistical comparisons of classifiers over multiple data sets. Journal of Machine Learning Research 7, 1-30. (Friedman, Nemenyi, critical-difference diagrams; why not Wilcoxon over many comparisons.)
- Dietterich, T. G. (1998). Approximate statistical tests for comparing supervised classification learning algorithms. Neural Computation 10(7). (Why tests that treat cross-validation folds as independent are too liberal.)
- Nadeau, C., Bengio, Y. (2003). Inference for the generalization error. Machine Learning 52. (The corrected resampled t-test for overlapping training sets.)
- Bouckaert, R. R., Frank, E. (2004). Evaluating the replicability of significance tests for comparing learning algorithms. PAKDD.
- Benavoli, A., Corani, G., Mangili, F. (2016). Should we really use post-hoc tests based on mean-ranks? Journal of Machine Learning Research 17. (A reason to be careful with Nemenyi and mean ranks; Bayesian alternatives.)
- Varoquaux, G. (2018). Cross-validation failure: small sample sizes lead to large error bars. NeuroImage 180. (The limit of one small test fold.)
- Kruskal and Wallis (1952); Friedman (1937); Conover and Iman (1979, multiple-comparison procedures); Holm (1979); Šidák (1967). The original sources for the tests.
- Herbold, S. (2020). Autorank: a Python package for automated ranking of classifiers. Journal of Open Source Software. (Implements the decision tree between these tests.)

**Leakage and splitting in pathology**
- Kapoor, S., Narayanan, A. (2023). Leakage and the reproducibility crisis in machine-learning-based science. Patterns.
- Bussola, N. et al. (2021). AI slipping on tiles: data leakage in digital pathology. ICPR workshops. (Patch-level splits that put the same slide in training and test.)
- Anything on grouped or patient-level cross-validation in histopathology.

**Explaining with perturbation and attribution**
- Zeiler, M. D., Fergus, R. (2014). Visualizing and understanding convolutional networks. ECCV. (Occlusion.)
- Selvaraju, R. R. et al. (2017). Grad-CAM. ICCV.
- Adebayo, J. et al. (2018). Sanity checks for saliency maps. NeurIPS. (Randomising the model parameters as a control; why guided backpropagation and guided Grad-CAM are not used.)
- Samek, W. et al. (2017). Evaluating the visualization of what a deep neural network has learned. IEEE TNNLS. (Perturbation-based evaluation.)
- Hägele, M. et al. (2020). Resolving challenges in deep learning-based analyses of histopathological images using explanation methods. Scientific Reports. (The histopathology precedent.)
- Captum documentation (Occlusion, LayerGradCam) for the implementation.

## Questions for the literature search

1. Is a Kruskal-Wallis plus Conover-Iman analysis on fold scores still accepted for comparing deep models, or should the corrected resampled t-test or a Bayesian comparison be the main analysis? What do reviewers of histopathology papers expect?
2. How many test patients or pictures are needed for a ranking of models to be stable? Is there work on that for patch-based pathology classification?
3. Is "the models cannot be told apart" with this test power reported and worded in a standard way?
4. For perturbation-based attribution on H&E patches: which baseline for the occluded area (white, the patch mean, blur) and which window size are used, and how is the agreement between maps of different architectures measured?
5. Which published work compares maps between CNNs and transformers on the same patches, and how do they handle the different layers?
