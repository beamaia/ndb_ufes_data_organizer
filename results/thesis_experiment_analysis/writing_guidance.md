# Canonical experiment analysis

## Verification

- The six selected parent runs are finished.
- Every selected parent contains exactly five finished children, folds 0--4.
- Every selected run uses 3,763 rows and keeps fold 5 held out.
- The parent aggregate metrics exactly match the mean and population standard deviation recalculated from the five child folds.
- Shared configuration: SGD, learning rate 0.001, momentum 0.9, batch size 30, maximum 150 epochs, scheduler patience 10, and early-stopping patience 15.
- `batch2_densenet121_full_20260721_batch2_cnn` had 3 same-name attempts in MLflow; only the exact completed run ID in the audit table was used.
- `batch2_resnet50_full_20260721_batch2_cnn` had 2 same-name attempts in MLflow; only the exact completed run ID in the audit table was used.

## Methodology points to include

- State that MobileNetV2, DenseNet-121, and ResNet-50 were trained under the same relevant hyperparameters in both experiments.
- Explain that Experiment 1 reproduces the original-comparable patch division, while Experiment 2 changes the fold assignment so linked patient/case groups remain together.
- State that fold 5 was never used for training or validation. Five models were trained per architecture by rotating validation folds 0--4, and every model was evaluated on fold 5.
- Explain that reported test metrics are the mean and standard deviation of the five model evaluations on the held-out fold.
- Explain that the confusion matrix uses one checkpoint so each held-out patch appears once. DenseNet-121 was identified as the best-performing architecture from the completed test-result comparison. Within that architecture, fold 3 was selected only because it had the highest validation BCC; test fold 5 results were not used to select the representative fold checkpoint.
- Mention that early stopping monitored validation loss. Different fold curves therefore end at different epochs.

## Results points to include

- Compare Experiment 1 with the historical CNN results without claiming exact identity between implementations.
- Report the numerical decrease in Experiment 2 separately for each CNN, not only MobileNetV2.
- Use “lower contamination-risk split” rather than “contamination-free split.” Patient grouping reduces known overlap but cannot prove that every relationship was recovered.
- Describe whether the training loss continues decreasing while validation loss plateaus or increases before calling a curve overfitted.
- In the confusion matrices, compare the two leukoplakia classes in both directions and distinguish their error rates from OSCC errors.

## Discussion points to include

- The split definition is the main experimental change, which supports an association between grouping and the performance decrease. Avoid saying that the experiment proves every part of the decrease was caused only by leakage.
- Explain that related WSI, shifted or zoomed tissue views, and patches from linked patients can reduce effective visual diversity when separated across folds.
- Connect the class-specific confusion to the known subjectivity of epithelial dysplasia assessment.
- State that the statistical analysis is exploratory because only five folds are available and their training subsets overlap.
- The within-experiment Friedman tests evaluate whether the three CNNs have different fold-level BCC distributions. The between-experiment tests compare the same architecture across the two split strategies; they do not compare every model against every other model.

## Statistical interpretation

- Experiment 1: Friedman statistic 5.200, p=0.0743; no model difference was detected at alpha=0.05.
- Experiment 2: Friedman statistic 2.800, p=0.2466; no model difference was detected at alpha=0.05.
- MobileNetV2: U=25.0, raw p=0.0079, Holm-adjusted p=0.0238, experiment 1 higher.
- DenseNet-121: U=25.0, raw p=0.0079, Holm-adjusted p=0.0238, experiment 1 higher.
- ResNet-50: U=25.0, raw p=0.0079, Holm-adjusted p=0.0238, experiment 1 higher.
