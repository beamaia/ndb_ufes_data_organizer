# Project summary, for the literature search

Written 2026-10-20 from the work done so far. Everything here comes from the repositories and their results; numbers are from the rebuilt dataset tables unless stated.

## The task

Classify oral histopathology patches into three classes: OSCC (oral squamous cell carcinoma), leukoplakia with dysplasia, and leukoplakia without dysplasia. The thesis compares convolutional networks and transformers (and, next, pathology foundation models), and later adds an explainability section.

## The data

- **NDB-UFES** (public, Mendeley Data): 237 whole images from 69 patients and 77 lesions, taken from slides with a camera at 10x and 40x objectives, 2048 x 1536 pixels, from UFES. Each image has a diagnosis (OSCC 91, with dysplasia 89, without dysplasia 57) and patient data (gender, age group, skin color, lesion site, tobacco, alcohol, sun exposure). "Not informed" is common in tobacco, alcohol, sun exposure and skin color. Gender is 132 male and 105 female. Age group under 40 is rare (15 images; 111 in each of the other two groups).
- **P-NDB-UFES** (public): 3,763 patches of 512 x 512 pixels cut from the images (at most 20 per image, with scikit-learn's patch extractor) and labeled one by one by pathologists: OSCC 1,126 (29.9%), with dysplasia 1,930 (51.3%), without dysplasia 707 (18.8%).
- **Two internal datasets** (not published): SAB, the parent images the patches were cut from, filed by a database into folders (carcinoma, leucoplasia, benigno) that do not match the three classes and were never re-validated; and patches_data, the patches with their original names.
- Linking: every patch was tied to its parent picture by exact pixel matching (3,763 of 3,763), and pictures that show the same tissue were tied by SIFT feature matching. There are 288 distinct pictures, 247 with patches. 217 pictures are in both NDB-UFES and SAB, 51 only in SAB (46 of them from the benigno folder), 20 only in NDB-UFES.

## Problems found in the data

1. **Labels disagree between the patch and its picture.** Of the 3,111 patches whose picture is in NDB-UFES: 57.1% have the picture's label, 28.4% are less severe (expected, a picture has many regions) and 14.4% (449) are more severe than the picture. Pictures labeled without dysplasia hold no OSCC patch, but 395 of their patches (60.0%) are labeled with dysplasia. Pictures labeled with dysplasia hold 54 OSCC patches (5.8%). The patches were labeled later, not necessarily by the team that labeled NDB-UFES, and the picture's diagnosis was not used and the labeling was not blind. Dysplasia versus no dysplasia is the hardest distinction.
2. **Leakage in the published folds.** The six folds published with P-NDB-UFES put patches of the same patient and picture in different folds: 63 of 64 cases (98%) and 245 of 247 pictures (99%) are split across folds, and 95% of the patches have a neighbour sharing at least a quarter of their area in another fold. Patches overlap because they were cut next to each other.
3. **Related pictures.** 92 pairs of pictures show the same tissue (a wide view and a close-up, about 4x apart, which fits the 10x and 40x objectives); 75 groups hold 160 of the 288 pictures. In 83 pairs the zoom differs.
4. **Duplicates:** 3 pairs of identical patches (one of each pair was dropped, so 3,760 patches are in the folds).
5. **Single centre, many "Not informed" values in the patient data, and an uneven age distribution.** The models use images only, but the metadata is a possible source of shortcuts if it is ever added.

## The new folds

Six folds made so that no case group (patient, with pictures that share evidence) is ever split, so no patient, picture or group of related pictures is on two sides. 63 case groups. Each fold balances, with equal weights: the patch label, the NDB-UFES diagnosis of the picture, gender, age group, and three morphology clusters (a Virchow embedding of each patch, reduced to two PCA components, K-Means with 3 clusters, silhouette 0.636). A greedy algorithm deals the groups largest first, then moves and exchanges groups, from 201 starting points, keeping the best. The largest fold is 1.084 times the smallest (the limit was 1.10).

Compared with the original folds: contamination is zero in the new folds, but the folds are less alike (widest gap between the highest and lowest share of a value 9.6 points against 5.7; mean distance between folds in the embedding plane 0.51 against 0.21, and 0.25 for a random division). Age group under 40 is absent from two folds. Fold 5 is the test fold.

## The training protocol (copy of the original experiments, with only the folds changed)

- Fold 5 is the test fold; folds 0 to 4 are a 5-fold cross-validation (each is the validation fold in turn); every fold model is tested on fold 5. Five trainings per model; results are the mean and standard deviation over them.
- Models of the article: ResNet-50, MobileNetV2, DenseNet-121, VGG16 (CNNs) and CoaT-lite-small, PiT-S distilled, ViT-S/16 at 384 px (transformers), all from ImageNet weights, trained end to end.
- Weighted cross-entropy, SGD (learning rate 0.001, momentum 0.9), batch size 30, up to 150 epochs, ReduceLROnPlateau (factor 0.1, patience 10), early stopping (patience 15) on the validation loss, the best checkpoint by validation loss. Images are augmented (imgaug) and normalised with ImageNet mean and standard deviation, at 224 px (384 for ViT-S/16).
- Planned additions: ConvNeXt-L, Swin, EfficientNet, and pathology foundation models (Virchow2, UNI2-h, CONCH, and Google's Path Foundation as frozen features). The folds were balanced on Virchow clusters, which matters if Virchow is also a classifier.
- Context: the article reported DenseNet-121 91.91% and CoaT 90.84% on the original folds. Those folds leak, so a main question is how much the new folds change the numbers. (The first 1-epoch ResNet-50 timing run gave test balanced accuracy of 47 to 59%, which says nothing about the real training.)

## What is measured and logged

Balanced accuracy, macro F1, precision and recall, the ROC AUC of each class, the confusion matrix as numbers, and the same per picture and per patient (mean of the patch probabilities), plus the comparison of the picture-level prediction with the NDB-UFES diagnosis. Everything goes to an MLflow server (parameters, tags, metrics per epoch and per fold, predictions with class probabilities, the folds file as a dataset, seconds and cost per run).

## Reproducibility

Settings are in versioned YAML files only. Every fold seeds Python, numpy, torch and the augmentation library (seed plus the fold number); the same seed gave identical results on the same machine in tests, and different hardware can differ in the last digits. Checkpoints describe themselves (model, classes, preprocessing, fold, seed, hash of the folds file), so an explainability tool can rebuild a model from the file alone. Code is shared, weights are not (non-commercial licences of some foundation models). 29 automated tests.

## Status

The dataset rebuild, the folds and the wiki are finished; the training pipeline is finished and tested. A timing run of the seven models is in progress on an Apple M5 (about 100 seconds per ResNet-50 epoch); the real training has not started.

## Questions for the literature search

- **Bias and medical data:** patient-level and picture-level leakage in patch datasets and how it inflates results; label noise and inter-observer variability in oral epithelial dysplasia grading; labels made without access to the image-level diagnosis; label disagreement between patch and slide level; selection and single-center bias; magnification, camera and staining shifts and shortcuts such as zoom or lesion site; class imbalance and weighted losses; small numbers of patients (63 case groups) and honest confidence intervals when samples are correlated; paired comparison of models on shared folds.
- **Explainability:** methods for histopathology patches with CNNs and transformers (Grad-CAM family, integrated gradients, attention-based methods for transformers); how to test that explanations are faithful (sanity checks, deletion and insertion tests); agreement with pathologists; explainability for foundation models; pitfalls such as explanations that highlight artifacts or the background.
- **Model training:** ImageNet versus pathology foundation models for small oral datasets; end-to-end fine-tuning versus frozen features; training with noisy labels; early stopping and model selection on the validation set; seed variance and how many runs to report; aggregation of patch predictions to slide or patient level.
