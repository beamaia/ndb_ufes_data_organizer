# Final Output Status

Last verified: 23 July 2026.

## Source-Image Linkage

The validated linkage is complete for all 3,763 patches. It contains 251 source-image groups: 203 both-source groups with 3,111 patches and 48 SAB-only groups with 652 patches. Coordinates are available for every represented patch.

Status: **complete and validated**.

## Experiment Assignments

The final release contains two 3,763-row assignment tables. Experiment 1 is the patch-level reference split. Experiment 2 is the patient-first grouped split, with no validated source-image or patient/case group crossing folds.

Status: **complete and validated**.

## Canonical Results

The release contains six canonical parent runs and 30 child-fold evaluations for MobileNetV2, DenseNet-121, and ResNet-50. Stored metrics were checked against the frozen dataset hashes, fold contract, run status, and balanced-accuracy definition.

Status: **complete and validated**.

## Public Bundle

The sanitized public bundle contains:

- two final assignment tables,
- the public source-image index,
- canonical result and validation tables,
- confusion-matrix and loss figures,
- a machine-readable manifest and validation report,
- public documentation and licensing.

Private source identifiers, private crosswalks, checkpoints, raw MLflow storage, local absolute paths, direct patient/lesion identifiers, and secrets are excluded.

Status: **ready for public use**.

## Documentation

The wiki builds in strict mode and its generated site is checked for local links, search assets, downloads, forbidden fields, and payload size.

Status: **validated before deployment**.
