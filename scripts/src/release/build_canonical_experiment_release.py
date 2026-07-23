#!/usr/bin/env python3
"""Build and verify the public v1.0.0 experiment evidence package.

This script never contacts MLflow and never retrains a model. It verifies the
saved child-fold records, writes a sanitized manifest, copies the public result
tables/figures, and generates the two-experiment fold-distribution figure.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import statistics
from collections import defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "results/thesis_experiment_analysis"
DEFAULT_OUTPUT = ROOT / "docs/assets/experiments"

CANONICAL_MODELS = ("MobileNetV2", "DenseNet-121", "ResNet-50")
DATASET_HASHES = {
    "Experiment 1": "8c5df2eb6123ccea59a2f06932ea88abaa156b47de230d708c37b18aa19be567",
    "Experiment 2": "c7586918c67b92d832fa22c749eab6e792fff0d9879a7497a557bee8e33e3d83",
}
SPLITS = {
    "Experiment 1": {
        "batch": "batch1",
        "name": "Original-comparable patch split",
        "csv": ROOT / "results/phase3/current_thesis_batches/batch1_recovered_reference_patch_level.csv",
    },
    "Experiment 2": {
        "batch": "batch2",
        "name": "Patient-first grouped, lower-contamination-risk split",
        "csv": ROOT / "results/phase3/current_thesis_batches/batch2_patient_first_patch_level.csv",
    },
}
TRAINING_PROVENANCE = {
    "06429825d70c4664bd63c4b53e996a94": {
        "git_base_commit": "648b70866634abb3e0c7316016f07b6e3527883e",
        "git_worktree_state": "dirty",
    },
    "bff3f566eaaa44349f79b52413acb3ce": {
        "git_base_commit": "648b70866634abb3e0c7316016f07b6e3527883e",
        "git_worktree_state": "dirty",
    },
    "871b5389e4214e01a6f7d6d61ed82e21": {
        "git_base_commit": "648b70866634abb3e0c7316016f07b6e3527883e",
        "git_worktree_state": "dirty",
    },
    "42bffdc2d37d43818707164934fef82e": {
        "git_base_commit": "648b70866634abb3e0c7316016f07b6e3527883e",
        "git_worktree_state": "dirty",
    },
    "828be67ffd494debbf0a355630b8b3f0": {
        "git_base_commit": None,
        "git_worktree_state": "unavailable",
    },
    "188fc9fab12c4675a89381101c9beb01": {
        "git_base_commit": None,
        "git_worktree_state": "unavailable",
    },
}
PUBLIC_TABLES = (
    "canonical_run_validation.csv",
    "fold_test_metrics.csv",
    "results_summary.csv",
    "execution_times.csv",
    "statistics_within_experiment.csv",
    "statistics_between_experiments.csv",
    "confusion_matrix_selection.csv",
)
PUBLIC_FIGURES = (
    "fig_confusion_matrices.png",
    "fig_confusion_matrices.pdf",
    "fig_train_validation_loss.png",
    "fig_train_validation_loss.pdf",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def as_number(value: str) -> float:
    return float(value)


def verify_metrics(
    validations: list[dict[str, str]],
    fold_rows: list[dict[str, str]],
    summaries: list[dict[str, str]],
) -> None:
    if len(validations) != 6:
        raise ValueError(f"Expected six canonical parents, found {len(validations)}")
    if {row["model"] for row in validations} != set(CANONICAL_MODELS):
        raise ValueError("Canonical validation does not contain the three final CNNs")
    if {row["experiment"] for row in validations} != set(SPLITS):
        raise ValueError("Canonical validation does not contain exactly two experiments")

    summary_lookup = {
        (row["experiment"], row["model"]): row for row in summaries
    }
    folds_by_run: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in fold_rows:
        folds_by_run[(row["experiment"], row["model"])].append(row)

    metric_columns = {
        "balanced_accuracy": "balanced_accuracy",
        "recall": "recall",
        "precision": "precision",
        "macro_f1": "macro_f1",
    }
    for validation_row in validations:
        key = (validation_row["experiment"], validation_row["model"])
        children = sorted(folds_by_run[key], key=lambda row: int(row["fold"]))
        if [int(row["fold"]) for row in children] != [0, 1, 2, 3, 4]:
            raise ValueError(f"{key} does not contain child folds 0 through 4")
        if any(row["child_status"] != "FINISHED" for row in children):
            raise ValueError(f"{key} contains an unfinished child run")
        if validation_row["run_id"] not in TRAINING_PROVENANCE:
            raise ValueError(
                f"Missing sanitized provenance for {validation_row['run_id']}"
            )
        if (
            validation_row["dataset_sha256"]
            != DATASET_HASHES[validation_row["experiment"]]
        ):
            raise ValueError(f"Unexpected dataset hash for {key}")
        if int(validation_row["dataset_rows"]) != 3763:
            raise ValueError(f"Unexpected dataset row count for {key}")

        summary = summary_lookup[key]
        for source_name, summary_prefix in metric_columns.items():
            values = [as_number(row[source_name]) for row in children]
            mean = statistics.fmean(values)
            std = statistics.pstdev(values)
            if not math.isclose(
                mean,
                as_number(summary[f"{summary_prefix}_mean"]),
                rel_tol=0,
                abs_tol=1e-12,
            ):
                raise ValueError(f"Stored mean does not match children for {key}")
            if not math.isclose(
                std,
                as_number(summary[f"{summary_prefix}_std"]),
                rel_tol=0,
                abs_tol=1e-12,
            ):
                raise ValueError(f"Stored standard deviation does not match children for {key}")
        if not math.isclose(
            as_number(summary["balanced_accuracy_mean"]),
            as_number(summary["recall_mean"]),
            rel_tol=0,
            abs_tol=1e-12,
        ):
            raise ValueError(f"Balanced accuracy and macro recall diverge for {key}")


def build_fold_distribution(output_dir: Path) -> None:
    class_order = (
        "OSCC",
        "Leukoplakia with dysplasia",
        "Leukoplakia without dysplasia",
    )
    colors = ("#d95f02", "#087fbd", "#009b72")
    width, height = 1200, 600
    plot_top, plot_bottom = 100, 470
    plot_height = plot_bottom - plot_top
    panel_lefts = (90, 650)
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="600" y="38" text-anchor="middle" font-family="Arial, sans-serif" '
        'font-size="24" font-weight="700">Class distribution across the six folds by experiment</text>',
    ]
    for panel_left, (experiment, definition) in zip(panel_lefts, SPLITS.items()):
        table = pd.read_csv(definition["csv"])
        counts = (
            table.groupby(["fold", "diagnosis"])
            .size()
            .unstack(fill_value=0)
            .reindex(columns=class_order)
        )
        percentages = counts.div(counts.sum(axis=1), axis=0) * 100
        svg.extend(
            [
                f'<text x="{panel_left + 235}" y="72" text-anchor="middle" '
                f'font-family="Arial, sans-serif" font-size="16" font-weight="700">'
                f"{experiment}: {definition['name']}</text>",
                f'<line x1="{panel_left}" y1="{plot_top}" x2="{panel_left}" '
                f'y2="{plot_bottom}" stroke="#4b5563"/>',
                f'<line x1="{panel_left}" y1="{plot_bottom}" x2="{panel_left + 470}" '
                f'y2="{plot_bottom}" stroke="#4b5563"/>',
            ]
        )
        for tick in range(0, 101, 20):
            y = plot_bottom - tick / 100 * plot_height
            svg.append(
                f'<line x1="{panel_left}" y1="{y:.1f}" x2="{panel_left + 470}" '
                f'y2="{y:.1f}" stroke="#d1d5db" stroke-width="0.7"/>'
            )
            if panel_left == panel_lefts[0]:
                svg.append(
                    f'<text x="{panel_left - 10}" y="{y + 4:.1f}" text-anchor="end" '
                    f'font-family="Arial, sans-serif" font-size="11">{tick}</text>'
                )
        for fold in range(6):
            x = panel_left + 30 + fold * 72
            cumulative = 0.0
            for diagnosis, color in zip(class_order, colors):
                value = float(percentages.loc[fold, diagnosis])
                rect_height = value / 100 * plot_height
                y = plot_bottom - (cumulative + value) / 100 * plot_height
                svg.append(
                    f'<rect x="{x}" y="{y:.2f}" width="50" height="{rect_height:.2f}" '
                    f'fill="{color}"/>'
                )
                if value >= 9:
                    svg.append(
                        f'<text x="{x + 25}" y="{y + rect_height / 2 + 4:.2f}" '
                        f'text-anchor="middle" font-family="Arial, sans-serif" '
                        f'font-size="10" fill="white">{value:.1f}%</text>'
                    )
                cumulative += value
            svg.append(
                f'<text x="{x + 25}" y="{plot_bottom + 22}" text-anchor="middle" '
                f'font-family="Arial, sans-serif" font-size="11">Fold {fold}</text>'
            )
    svg.append(
        '<text x="28" y="285" transform="rotate(-90 28 285)" text-anchor="middle" '
        'font-family="Arial, sans-serif" font-size="13">Class distribution (%)</text>'
    )
    legend_x = 210
    for diagnosis, color in zip(class_order, colors):
        svg.append(
            f'<rect x="{legend_x}" y="535" width="16" height="16" fill="{color}"/>'
        )
        svg.append(
            f'<text x="{legend_x + 23}" y="548" font-family="Arial, sans-serif" '
            f'font-size="12">{diagnosis}</text>'
        )
        legend_x += 330
    svg.append("</svg>")
    (output_dir / "fold_class_distribution.svg").write_text(
        "\n".join(svg) + "\n",
        encoding="utf-8",
    )


def build_manifest(
    validations: list[dict[str, str]],
    fold_rows: list[dict[str, str]],
    summaries: list[dict[str, str]],
) -> dict[str, object]:
    fold_lookup: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in fold_rows:
        fold_lookup[(row["experiment"], row["model"])].append(row)
    summary_lookup = {
        (row["experiment"], row["model"]): row for row in summaries
    }
    validation_lookup = {
        (row["experiment"], row["model"]): row for row in validations
    }
    execution_lookup = {
        (row["experiment"], row["model"]): row
        for row in read_csv(SOURCE / "execution_times.csv")
    }

    experiments = []
    for experiment, definition in SPLITS.items():
        models = []
        for model in CANONICAL_MODELS:
            validation_row = validation_lookup[(experiment, model)]
            summary = summary_lookup[(experiment, model)]
            execution = execution_lookup[(experiment, model)]
            children = sorted(
                fold_lookup[(experiment, model)],
                key=lambda row: int(row["fold"]),
            )
            models.append(
                {
                    "model": model,
                    "parent_run_id": validation_row["run_id"],
                    "parent_run_name": validation_row["run_name"],
                    "status": validation_row["parent_status"],
                    "git_provenance": TRAINING_PROVENANCE[
                        validation_row["run_id"]
                    ],
                    "aggregate_metrics": {
                        key: float(value)
                        for key, value in summary.items()
                        if key not in {"experiment", "model", "folds"}
                    },
                    "parent_duration_seconds": float(execution["parent_total_seconds"]),
                    "children": [
                        {
                            "fold": int(row["fold"]),
                            "run_id": row["child_run_id"],
                            "status": row["child_status"],
                            "duration_seconds": float(row["duration_seconds"]),
                            "heldout_metrics": {
                                "balanced_accuracy": float(row["balanced_accuracy"]),
                                "macro_recall": float(row["recall"]),
                                "macro_precision": float(row["precision"]),
                                "macro_f1": float(row["macro_f1"]),
                            },
                        }
                        for row in children
                    ],
                }
            )
        experiments.append(
            {
                "id": experiment,
                "batch": definition["batch"],
                "split": definition["name"],
                "dataset_rows": 3763,
                "dataset_sha256": DATASET_HASHES[experiment],
                "cv_folds": [0, 1, 2, 3, 4],
                "heldout_test_fold": 5,
                "models": models,
            }
        )

    return {
        "schema_version": 1,
        "release": "v1.0.0",
        "privacy_mode": "public_sanitized",
        "generation_mode": "verified_from_stored_records_without_retraining",
        "experiment_contract": {
            "canonical_experiments": ["Experiment 1", "Experiment 2"],
            "canonical_models": list(CANONICAL_MODELS),
            "exploratory_archive": "Batch 3 (Virchow-pruned)",
            "metric_note": (
                "Balanced accuracy equals macro recall for this multiclass "
                "definition; five checkpoints are evaluated on held-out fold 5."
            ),
        },
        "hyperparameters": {
            "seed": 42,
            "initialization": "ImageNet pretrained",
            "training_mode": "full fine-tuning",
            "loss": "weighted cross-entropy",
            "optimizer": "SGD",
            "learning_rate": 0.001,
            "momentum": 0.9,
            "batch_size": 30,
            "epoch_ceiling": 150,
            "scheduler": "ReduceLROnPlateau on validation loss",
            "scheduler_factor": 0.1,
            "scheduler_patience": 10,
            "scheduler_min_lr": 0.000001,
            "early_stopping_patience": 15,
            "early_stopping_min_delta": 0.001,
        },
        "provenance_limitation": (
            "The completed historical runs were frozen without retraining. "
            "Four parents recorded base commit 648b708 with a dirty worktree; "
            "two parents recorded Git provenance as unavailable. The six "
            "parents therefore cannot all be attributed to one clean commit."
        ),
        "experiments": experiments,
        "statistics": {
            "scope": (
                "Exploratory only: five training subsets overlap and each "
                "experiment reuses one held-out test fold."
            ),
            "within_experiment": read_csv(
                SOURCE / "statistics_within_experiment.csv"
            ),
            "between_experiments": read_csv(
                SOURCE / "statistics_between_experiments.csv"
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    validations = read_csv(SOURCE / "canonical_run_validation.csv")
    fold_rows = read_csv(SOURCE / "fold_test_metrics.csv")
    summaries = read_csv(SOURCE / "results_summary.csv")
    verify_metrics(validations, fold_rows, summaries)

    manifest = build_manifest(validations, fold_rows, summaries)
    (output_dir / "canonical_run_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    for filename in PUBLIC_TABLES:
        shutil.copy2(SOURCE / filename, output_dir / filename)
    for filename in PUBLIC_FIGURES:
        shutil.copy2(SOURCE / filename, output_dir / filename)
    build_fold_distribution(output_dir)
    print("Verified six parents and 30 stored child-fold records.")
    print(f"Wrote public experiment assets to {output_dir}")


if __name__ == "__main__":
    main()
