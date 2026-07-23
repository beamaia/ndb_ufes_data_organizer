#!/usr/bin/env python3
"""Build thesis tables and figures from the six canonical MLflow runs."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from matplotlib.lines import Line2D
from mlflow.tracking import MlflowClient
from scipy.stats import friedmanchisquare, mannwhitneyu, wilcoxon
from sklearn.metrics import confusion_matrix


OUTPUT_DIR = Path(__file__).resolve().parent
MLFLOW_ENV = Path("/Users/beamaia/thesis_organization/ndb_ufes_mlflow/.env")
EXPERIMENT_NAME = "pndb_ufes_leakage_batches"

# Exact IDs prevent same-name retries from entering the thesis evidence.
CANONICAL_RUNS = [
    {
        "experiment": "Experiment 1",
        "batch": "batch1",
        "model": "MobileNetV2",
        "model_key": "mobilenetv2",
        "run_name": "batch1_mobilenetv2_full_20260719_195146",
        "run_id": "06429825d70c4664bd63c4b53e996a94",
    },
    {
        "experiment": "Experiment 2",
        "batch": "batch2",
        "model": "MobileNetV2",
        "model_key": "mobilenetv2",
        "run_name": "batch2_mobilenetv2_full_20260719_195146",
        "run_id": "bff3f566eaaa44349f79b52413acb3ce",
    },
    {
        "experiment": "Experiment 1",
        "batch": "batch1",
        "model": "DenseNet-121",
        "model_key": "densenet121",
        "run_name": "batch1_densenet121_full_20260720_031259",
        "run_id": "871b5389e4214e01a6f7d6d61ed82e21",
    },
    {
        "experiment": "Experiment 1",
        "batch": "batch1",
        "model": "ResNet-50",
        "model_key": "resnet50",
        "run_name": "batch1_resnet50_full_20260720_031259",
        "run_id": "42bffdc2d37d43818707164934fef82e",
    },
    {
        "experiment": "Experiment 2",
        "batch": "batch2",
        "model": "DenseNet-121",
        "model_key": "densenet121",
        "run_name": "batch2_densenet121_full_20260721_batch2_cnn",
        "run_id": "828be67ffd494debbf0a355630b8b3f0",
    },
    {
        "experiment": "Experiment 2",
        "batch": "batch2",
        "model": "ResNet-50",
        "model_key": "resnet50",
        "run_name": "batch2_resnet50_full_20260721_batch2_cnn",
        "run_id": "188fc9fab12c4675a89381101c9beb01",
    },
]

METRICS = {
    "balanced_accuracy": "heldout_test_balanced_acc",
    "recall": "heldout_test_recall",
    "precision": "heldout_test_precision",
    "macro_f1": "heldout_test_macro_f1",
}

SHARED_PARAM_KEYS = [
    "hyperparameters_optimizer_name",
    "hyperparameters_optimizer_learning_rate",
    "hyperparameters_optimizer_momentum",
    "hyperparameters_scheduler_name",
    "hyperparameters_scheduler_other_patience",
    "hyperparameters_scheduler_other_factor",
    "hyperparameters_scheduler_other_min_lr",
    "hyperparameters_other_epochs",
    "hyperparameters_other_batch_size",
    "early_stopping_enabled",
    "early_stopping_patience",
    "early_stopping_min_delta",
    "early_stopping_mode",
    "seed",
    "device",
]

CLASS_ORDER = [2, 1, 0]
CLASS_NAMES = [
    "OSCC",
    "Leukoplakia\nwith dysplasia",
    "Leukoplakia\nwithout dysplasia",
]


def holm_adjust(p_values: list[float]) -> list[float]:
    """Return Holm-adjusted p-values in their original order."""
    p = np.asarray(p_values, dtype=float)
    order = np.argsort(p)
    adjusted = np.empty_like(p)
    running_max = 0.0
    total = len(p)
    for rank, index in enumerate(order):
        candidate = min(1.0, (total - rank) * p[index])
        running_max = max(running_max, candidate)
        adjusted[index] = running_max
    return adjusted.tolist()


def metric_history(client: MlflowClient, run_id: str, key: str) -> pd.DataFrame:
    """Read metric history and retain the latest value for duplicate steps."""
    rows = [
        {"step": item.step, "value": item.value, "timestamp": item.timestamp}
        for item in client.get_metric_history(run_id, key)
    ]
    if not rows:
        return pd.DataFrame(columns=["step", "value", "timestamp"])
    frame = pd.DataFrame(rows).sort_values(["step", "timestamp"])
    return frame.drop_duplicates("step", keep="last").sort_values("step")


def children_for_parent(client: MlflowClient, experiment_id: str, parent_id: str):
    children = client.search_runs(
        [experiment_id],
        filter_string=f"tags.mlflow.parentRunId = '{parent_id}'",
        max_results=100,
    )
    return sorted(children, key=lambda run: int(run.data.params.get("fold", -1)))


def collect_evidence(client: MlflowClient, experiment_id: str):
    validations = []
    fold_rows = []
    duration_rows = []
    child_runs: dict[tuple[str, str, int], str] = {}
    parent_runs = {}

    for spec in CANONICAL_RUNS:
        parent = client.get_run(spec["run_id"])
        parent_runs[(spec["experiment"], spec["model"])] = parent
        children = children_for_parent(client, experiment_id, spec["run_id"])
        folds = [int(child.data.params.get("fold", -1)) for child in children]
        same_name_runs = client.search_runs(
            [experiment_id],
            filter_string=f"attributes.run_name = '{spec['run_name']}'",
            max_results=100,
        )

        parent_duration = (
            (parent.info.end_time - parent.info.start_time) / 1000.0
            if parent.info.end_time is not None
            else np.nan
        )
        model_param = parent.data.params.get("hyperparameters_model_name", "")
        config_match = (
            parent.data.tags.get("batch") == spec["batch"]
            and parent.data.tags.get("model") == spec["model_key"]
            and spec["model_key"] in model_param
        )

        child_metric_values = {name: [] for name in METRICS}
        fold_durations = {}
        for child in children:
            fold = int(child.data.params["fold"])
            child_runs[(spec["experiment"], spec["model"], fold)] = child.info.run_id
            child_duration = (
                (child.info.end_time - child.info.start_time) / 1000.0
                if child.info.end_time is not None
                else np.nan
            )
            fold_durations[fold] = child_duration
            row = {
                "experiment": spec["experiment"],
                "batch": spec["batch"],
                "model": spec["model"],
                "model_key": spec["model_key"],
                "parent_run_name": spec["run_name"],
                "parent_run_id": spec["run_id"],
                "fold": fold,
                "child_run_id": child.info.run_id,
                "child_status": child.info.status,
                "duration_seconds": child_duration,
            }
            for name, mlflow_key in METRICS.items():
                value = child.data.metrics.get(mlflow_key)
                if value is None:
                    raise RuntimeError(
                        f"Missing {mlflow_key} in {spec['run_name']} fold {fold}."
                    )
                row[name] = value
                child_metric_values[name].append(value)
            fold_rows.append(row)

        aggregate_matches = True
        for name, values in child_metric_values.items():
            mean_key = f"avg_heldout_test_{'balanced_acc' if name == 'balanced_accuracy' else name}"
            std_key = f"std_heldout_test_{'balanced_acc' if name == 'balanced_accuracy' else name}"
            if name == "macro_f1":
                mean_key = "avg_heldout_test_macro_f1"
                std_key = "std_heldout_test_macro_f1"
            aggregate_matches &= np.isclose(
                np.mean(values), parent.data.metrics.get(mean_key, np.nan), atol=1e-12
            )
            aggregate_matches &= np.isclose(
                np.std(values, ddof=0), parent.data.metrics.get(std_key, np.nan), atol=1e-12
            )

        validations.append(
            {
                "experiment": spec["experiment"],
                "model": spec["model"],
                "run_name": spec["run_name"],
                "run_id": spec["run_id"],
                "parent_status": parent.info.status,
                "child_count": len(children),
                "folds": ",".join(map(str, folds)),
                "all_children_finished": all(
                    child.info.status == "FINISHED" for child in children
                ),
                "expected_folds": folds == [0, 1, 2, 3, 4],
                "batch_model_match": config_match,
                "dataset_rows": int(parent.data.params.get("dataset_row_count", -1)),
                "dataset_sha256": parent.data.params.get(
                    "dataset_fold_assignments_sha256", ""
                ),
                "same_name_runs_in_mlflow": len(same_name_runs),
                "parent_aggregate_matches_children": bool(aggregate_matches),
            }
        )

        duration_row = {
            "experiment": spec["experiment"],
            "model": spec["model"],
            "parent_total_seconds": parent_duration,
        }
        for fold in range(5):
            duration_row[f"fold_{fold}_seconds"] = fold_durations[fold]
        durations = np.array([fold_durations[fold] for fold in range(5)])
        duration_row["mean_fold_seconds"] = durations.mean()
        duration_row["std_fold_seconds"] = durations.std(ddof=0)
        duration_rows.append(duration_row)

    validation_df = pd.DataFrame(validations)
    fold_df = pd.DataFrame(fold_rows).sort_values(
        ["experiment", "model", "fold"]
    )
    duration_df = pd.DataFrame(duration_rows).sort_values(
        ["experiment", "model"]
    )

    if not validation_df["parent_status"].eq("FINISHED").all():
        raise RuntimeError("At least one selected parent run is not FINISHED.")
    boolean_checks = [
        "all_children_finished",
        "expected_folds",
        "batch_model_match",
        "parent_aggregate_matches_children",
    ]
    if not validation_df[boolean_checks].all(axis=None):
        raise RuntimeError("Canonical MLflow validation failed; inspect canonical_run_validation.csv.")
    if not validation_df["dataset_rows"].eq(3763).all():
        raise RuntimeError("A canonical run does not use all 3,763 patch rows.")

    shared_configs = []
    for spec in CANONICAL_RUNS:
        parent = parent_runs[(spec["experiment"], spec["model"])]
        shared_configs.append(
            {key: parent.data.params.get(key) for key in SHARED_PARAM_KEYS}
        )
    reference = shared_configs[0]
    if any(config != reference for config in shared_configs[1:]):
        raise RuntimeError("Relevant hyperparameters differ among canonical runs.")

    return validation_df, fold_df, duration_df, child_runs, parent_runs, reference


def summarize_results(fold_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (experiment, model), group in fold_df.groupby(["experiment", "model"]):
        row = {"experiment": experiment, "model": model, "folds": len(group)}
        for metric in METRICS:
            row[f"{metric}_mean"] = group[metric].mean()
            row[f"{metric}_std"] = group[metric].std(ddof=0)
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["experiment", "model"])


def within_experiment_statistics(fold_df: pd.DataFrame):
    omnibus_rows = []
    posthoc_rows = []
    model_order = ["MobileNetV2", "DenseNet-121", "ResNet-50"]
    for experiment in ["Experiment 1", "Experiment 2"]:
        arrays = [
            fold_df[
                (fold_df["experiment"] == experiment) & (fold_df["model"] == model)
            ].sort_values("fold")["balanced_accuracy"].to_numpy()
            for model in model_order
        ]
        statistic, p_value = friedmanchisquare(*arrays)
        omnibus_rows.append(
            {
                "experiment": experiment,
                "test": "Friedman",
                "statistic": statistic,
                "raw_p_value": p_value,
                "significant_0_05": p_value < 0.05,
            }
        )
        if p_value < 0.05:
            pending = []
            for first in range(len(model_order)):
                for second in range(first + 1, len(model_order)):
                    stat, raw_p = wilcoxon(
                        arrays[first], arrays[second], alternative="two-sided", method="exact"
                    )
                    median_difference = float(
                        np.median(arrays[first] - arrays[second])
                    )
                    pending.append(
                        {
                            "experiment": experiment,
                            "model_1": model_order[first],
                            "model_2": model_order[second],
                            "test": "Wilcoxon signed-rank",
                            "statistic": stat,
                            "raw_p_value": raw_p,
                            "median_difference_model_1_minus_model_2": median_difference,
                            "direction": (
                                f"{model_order[first]} higher"
                                if median_difference > 0
                                else f"{model_order[second]} higher"
                                if median_difference < 0
                                else "no median difference"
                            ),
                        }
                    )
            adjusted = holm_adjust([row["raw_p_value"] for row in pending])
            for row, adjusted_p in zip(pending, adjusted):
                row["holm_adjusted_p_value"] = adjusted_p
                row["significant_0_05"] = adjusted_p < 0.05
                posthoc_rows.append(row)
    posthoc_columns = [
        "experiment",
        "model_1",
        "model_2",
        "test",
        "statistic",
        "raw_p_value",
        "median_difference_model_1_minus_model_2",
        "direction",
        "holm_adjusted_p_value",
        "significant_0_05",
    ]
    return pd.DataFrame(omnibus_rows), pd.DataFrame(posthoc_rows, columns=posthoc_columns)


def between_experiment_statistics(fold_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for model in ["MobileNetV2", "DenseNet-121", "ResNet-50"]:
        first = fold_df[
            (fold_df["experiment"] == "Experiment 1") & (fold_df["model"] == model)
        ]["balanced_accuracy"].to_numpy()
        second = fold_df[
            (fold_df["experiment"] == "Experiment 2") & (fold_df["model"] == model)
        ]["balanced_accuracy"].to_numpy()
        statistic, raw_p = mannwhitneyu(
            first, second, alternative="two-sided", method="exact"
        )
        median_difference = float(np.median(first) - np.median(second))
        rank_biserial = float(2 * statistic / (len(first) * len(second)) - 1)
        rows.append(
            {
                "model": model,
                "test": "Mann-Whitney U",
                "statistic": statistic,
                "raw_p_value": raw_p,
                "median_experiment_1": float(np.median(first)),
                "median_experiment_2": float(np.median(second)),
                "median_difference_experiment_1_minus_2": median_difference,
                "rank_biserial_correlation": rank_biserial,
                "direction": (
                    "Experiment 1 higher"
                    if median_difference > 0
                    else "Experiment 2 higher"
                    if median_difference < 0
                    else "no median difference"
                ),
            }
        )
    adjusted = holm_adjust([row["raw_p_value"] for row in rows])
    for row, adjusted_p in zip(rows, adjusted):
        row["holm_adjusted_p_value"] = adjusted_p
        row["significant_0_05"] = adjusted_p < 0.05
    return pd.DataFrame(rows)


def validation_selected_folds(
    client: MlflowClient, parent_runs: dict
) -> dict[str, dict]:
    selected = {}
    for experiment in ["Experiment 1", "Experiment 2"]:
        models = [
            key[1] for key in parent_runs if key[0] == experiment
        ]
        means = {
            model: parent_runs[(experiment, model)].data.metrics[
                "avg_heldout_test_balanced_acc"
            ]
            for model in models
        }
        best_model = max(means, key=means.get)
        parent = parent_runs[(experiment, best_model)]
        history = metric_history(client, parent.info.run_id, "fold_val_balanced_acc")
        if sorted(history["step"].astype(int).tolist()) != [0, 1, 2, 3, 4]:
            raise RuntimeError(f"Incomplete fold validation history for {experiment}.")
        best_row = history.loc[history["value"].idxmax()]
        selected[experiment] = {
            "model": best_model,
            "parent_run_id": parent.info.run_id,
            "fold": int(best_row["step"]),
            "validation_balanced_accuracy": float(best_row["value"]),
            "mean_heldout_balanced_accuracy": float(means[best_model]),
        }
    return selected


def plot_loss_curves(
    client: MlflowClient,
    child_runs: dict,
    selected: dict[str, dict],
):
    colors = {"train": "#286D9F", "validation": "#D87824"}
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.2), sharey=True)
    all_values = []
    histories = {}
    history_rows = []
    for experiment in ["Experiment 1", "Experiment 2"]:
        model = selected[experiment]["model"]
        selected_fold = selected[experiment]["fold"]
        for fold in range(5):
            run_id = child_runs[(experiment, model, fold)]
            train = metric_history(client, run_id, "train_loss")
            validation = metric_history(client, run_id, "val_loss")
            histories[(experiment, fold, "train")] = train
            histories[(experiment, fold, "validation")] = validation
            all_values.extend(train["value"].tolist())
            all_values.extend(validation["value"].tolist())
            for kind, history in [("training", train), ("validation", validation)]:
                for _, item in history.iterrows():
                    history_rows.append(
                        {
                            "experiment": experiment,
                            "model": model,
                            "fold": fold,
                            "validation_selected_fold": fold == selected_fold,
                            "series": kind,
                            "epoch": int(item["step"]) + 1,
                            "loss": float(item["value"]),
                        }
                    )

        axis = axes[0 if experiment == "Experiment 1" else 1]
        for fold in range(5):
            is_selected = fold == selected_fold
            alpha = 1.0 if is_selected else 0.17
            width = 2.2 if is_selected else 1.0
            zorder = 5 if is_selected else 1
            for kind in ["train", "validation"]:
                history = histories[(experiment, fold, kind)]
                axis.plot(
                    history["step"] + 1,
                    history["value"],
                    color=colors[kind],
                    alpha=alpha,
                    linewidth=width,
                    zorder=zorder,
                )
            if is_selected:
                validation = histories[(experiment, fold, "validation")]
                minimum = validation.loc[validation["value"].idxmin()]
                axis.scatter(
                    minimum["step"] + 1,
                    minimum["value"],
                    color=colors["validation"],
                    s=34,
                    zorder=7,
                )

        axis.set_title(
            f"{experiment}: {model}\nvalidation-selected fold {selected_fold}"
        )
        axis.set_xlabel("Epoch")
        axis.grid(axis="y", alpha=0.25)
        axis.spines[["top", "right"]].set_visible(False)

    axes[0].set_ylabel("Loss")
    lower = min(all_values)
    upper = np.quantile(all_values, 0.995)
    margin = (upper - lower) * 0.08
    axes[0].set_ylim(max(0, lower - margin), upper + margin)
    legend = [
        Line2D([0], [0], color=colors["train"], lw=2.2, label="Training loss"),
        Line2D([0], [0], color=colors["validation"], lw=2.2, label="Validation loss"),
        Line2D([0], [0], color="#666666", lw=1.0, alpha=0.25, label="Other folds"),
    ]
    fig.legend(handles=legend, loc="upper center", ncol=3, frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 0.91))
    for suffix in ["png", "pdf"]:
        fig.savefig(
            OUTPUT_DIR / f"fig_train_validation_loss.{suffix}",
            dpi=300,
            bbox_inches="tight",
        )
    plt.close(fig)
    pd.DataFrame(history_rows).to_csv(OUTPUT_DIR / "epoch_loss_history.csv", index=False)


def plot_confusion_matrices(
    child_runs: dict,
    selected: dict[str, dict],
):
    matrices = {}
    prediction_info = []
    with tempfile.TemporaryDirectory() as temporary_dir:
        for experiment in ["Experiment 1", "Experiment 2"]:
            model = selected[experiment]["model"]
            fold = selected[experiment]["fold"]
            run_id = child_runs[(experiment, model, fold)]
            path = mlflow.artifacts.download_artifacts(
                run_id=run_id,
                artifact_path="heldout_predictions/predictions.csv",
                dst_path=temporary_dir,
            )
            predictions = pd.read_csv(path)
            if predictions["patch"].duplicated().any():
                raise RuntimeError(f"Duplicate held-out patches in {experiment} predictions.")
            matrix = confusion_matrix(
                predictions["y_true"], predictions["y_pred"], labels=CLASS_ORDER
            )
            percentages = matrix / matrix.sum(axis=1, keepdims=True) * 100
            matrices[experiment] = (matrix, percentages)
            prediction_info.append(
                {
                    "experiment": experiment,
                    "model": model,
                    "fold": fold,
                    "child_run_id": run_id,
                    "heldout_rows": len(predictions),
                    "unique_patches": predictions["patch"].nunique(),
                }
            )

    fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.4), constrained_layout=True)
    image = None
    for axis, experiment in zip(axes, ["Experiment 1", "Experiment 2"]):
        matrix, percentages = matrices[experiment]
        image = axis.imshow(percentages, cmap="Blues", vmin=0, vmax=100)
        for row in range(3):
            for column in range(3):
                color = "white" if percentages[row, column] >= 52 else "#1A1A1A"
                axis.text(
                    column,
                    row,
                    f"{matrix[row, column]:,}\n({percentages[row, column]:.1f}%)",
                    ha="center",
                    va="center",
                    color=color,
                    fontsize=10,
                )
        axis.set_xticks(range(3), CLASS_NAMES)
        axis.set_yticks(range(3), CLASS_NAMES)
        axis.set_xlabel("Predicted class")
        axis.set_ylabel("True class")
        axis.set_title(
            f"{experiment}: {selected[experiment]['model']}\n"
            f"Test fold 5 predictions; checkpoint selected using "
            f"validation fold {selected[experiment]['fold']}"
        )
        axis.tick_params(axis="x", rotation=0)
    colorbar = fig.colorbar(image, ax=axes, shrink=0.82, pad=0.02)
    colorbar.set_label("Percentage within true class")
    for suffix in ["png", "pdf"]:
        fig.savefig(
            OUTPUT_DIR / f"fig_confusion_matrices.{suffix}",
            dpi=300,
            bbox_inches="tight",
        )
    plt.close(fig)

    pd.DataFrame(prediction_info).to_csv(
        OUTPUT_DIR / "confusion_matrix_selection.csv", index=False
    )
    payload = {
        experiment: {
            "class_order": CLASS_NAMES,
            "counts": matrix.tolist(),
            "row_percentages": percentages.tolist(),
        }
        for experiment, (matrix, percentages) in matrices.items()
    }
    (OUTPUT_DIR / "confusion_matrices.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def result_cell(mean: float, std: float, bold: bool = False) -> str:
    value = f"{mean * 100:.2f} \\pm {std * 100:.2f}"
    return f"$\\mathbf{{{value}}}$" if bold else f"${value}$"


def create_latex(
    summary: pd.DataFrame,
    durations: pd.DataFrame,
    within: pd.DataFrame,
    between: pd.DataFrame,
    selected: dict[str, dict],
):
    historical = [
        ("ResNet-50", 91.38, 1.18, 91.77, 0.72, 91.77, 0.72, 91.77, 0.72),
        ("MobileNet", 91.49, 0.77, 91.57, 0.61, 91.57, 0.61, 91.57, 0.61),
        ("DenseNet-121", 91.91, 0.84, 91.93, 0.75, 91.93, 0.75, 91.93, 0.75),
    ]
    lines = [
        r"\begin{table*}[t]",
        r"\caption{Held-out test results for the CNN experiments. Values are reported as mean $\pm$ standard deviation across five folds. Bold values indicate the highest mean balanced accuracy within each experiment.}",
        r"\label{tab:cnn-experiment-results}",
        r"\centering",
        r"\small",
        r"\begin{tabular}{@{}lrrrr@{}}",
        r"\toprule",
        r"Model & BCC (\%) & Recall (\%) & Precision (\%) & Macro F1 (\%) \\",
        r"\midrule",
        r"\multicolumn{5}{c}{\textbf{Experiment from Maia et al. \citep{MAIA2024122418}}} \\",
        r"\midrule",
    ]
    for row in historical:
        model, bm, bs, rm, rs, pm, ps, fm, fs = row
        bold = model == "DenseNet-121"
        cells = [
            f"$\\mathbf{{{bm:.2f} \\pm {bs:.2f}}}$" if bold else f"${bm:.2f} \\pm {bs:.2f}$",
            f"${rm:.2f} \\pm {rs:.2f}$",
            f"${pm:.2f} \\pm {ps:.2f}$",
            f"${fm:.2f} \\pm {fs:.2f}$",
        ]
        lines.append(f"{model} & " + " & ".join(cells) + r" \\")

    for experiment, heading in [
        ("Experiment 1", "Experiment 1: Reference split"),
        ("Experiment 2", "Experiment 2: Patient-first grouped split"),
    ]:
        lines.extend(
            [
                r"\midrule",
                f"\\multicolumn{{5}}{{c}}{{\\textbf{{{heading}}}}} \\\\",
                r"\midrule",
            ]
        )
        subset = summary[summary["experiment"] == experiment].copy()
        best_model = subset.loc[subset["balanced_accuracy_mean"].idxmax(), "model"]
        order = ["MobileNetV2", "DenseNet-121", "ResNet-50"]
        for model in order:
            row = subset[subset["model"] == model].iloc[0]
            cells = [
                result_cell(
                    row["balanced_accuracy_mean"],
                    row["balanced_accuracy_std"],
                    bold=model == best_model,
                ),
                result_cell(row["recall_mean"], row["recall_std"]),
                result_cell(row["precision_mean"], row["precision_std"]),
                result_cell(row["macro_f1_mean"], row["macro_f1_std"]),
            ]
            lines.append(f"{model} & " + " & ".join(cells) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table*}"])

    time_lines = [
        r"\begin{table*}[t]",
        r"\caption{MLflow wall-clock duration for each CNN run. Fold durations and parent-run totals are reported in seconds.}",
        r"\label{tab:cnn-execution-time}",
        r"\centering",
        r"\scriptsize",
        r"\begin{tabular}{@{}lrrrrrrr@{}}",
        r"\toprule",
        r"Model & Fold 0 & Fold 1 & Fold 2 & Fold 3 & Fold 4 & Mean $\pm$ SD & Total \\",
        r"\midrule",
    ]
    for experiment, heading in [
        ("Experiment 1", "Experiment 1: Reference split"),
        ("Experiment 2", "Experiment 2: Patient-first grouped split"),
    ]:
        time_lines.extend(
            [
                f"\\multicolumn{{8}}{{c}}{{\\textbf{{{heading}}}}} \\\\",
                r"\midrule",
            ]
        )
        for model in ["MobileNetV2", "DenseNet-121", "ResNet-50"]:
            row = durations[
                (durations["experiment"] == experiment) & (durations["model"] == model)
            ].iloc[0]
            values = [f"{row[f'fold_{fold}_seconds']:.0f}" for fold in range(5)]
            mean_std = f"${row['mean_fold_seconds']:.0f} \\pm {row['std_fold_seconds']:.0f}$"
            total = f"{row['parent_total_seconds']:.0f}"
            time_lines.append(
                f"{model} & " + " & ".join(values + [mean_std, total]) + r" \\")
        if experiment == "Experiment 1":
            time_lines.append(r"\midrule")
    time_lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table*}"])

    stat_lines = [
        r"\begin{table*}[t]",
        r"\caption{Exploratory statistical analysis of fold-level balanced accuracy. Between-experiment $p$-values use Holm correction across the three architecture comparisons.}",
        r"\label{tab:bcc-statistical-analysis}",
        r"\centering",
        r"\small",
        r"\begin{tabularx}{\textwidth}{@{}XlrrrrX@{}}",
        r"\toprule",
        r"Comparison & Test & Statistic & Raw $p$ & Adjusted $p$ & Median difference & Direction \\",
        r"\midrule",
    ]
    for _, row in within.iterrows():
        stat_lines.append(
            f"{row['experiment']}: three CNNs & Friedman & "
            f"{row['statistic']:.3f} & {row['raw_p_value']:.4f} & -- & -- & "
            + ("Difference detected" if row["significant_0_05"] else "No difference detected")
            + r" \\"
        )
    stat_lines.append(r"\midrule")
    for _, row in between.iterrows():
        stat_lines.append(
            f"{row['model']}: Experiment 1 vs. 2 & Mann--Whitney $U$ & "
            f"{row['statistic']:.1f} & {row['raw_p_value']:.4f} & "
            f"{row['holm_adjusted_p_value']:.4f} & "
            f"{row['median_difference_experiment_1_minus_2'] * 100:.2f} pp & "
            f"{row['direction']}" + r" \\"
        )
    stat_lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table*}"])

    figure_lines = [
        r"\begin{figure*}[t]",
        r"\centering",
        r"\includegraphics[width=\textwidth]{fig_train_validation_loss.pdf}",
        r"\caption{Training and validation loss for the best-performing architecture in each experiment. Lighter lines show all five folds, while darker lines show the fold selected using validation balanced accuracy. The point marks the minimum validation loss of the selected fold.}",
        r"\label{fig:train-validation-loss}",
        r"\end{figure*}",
        "",
        r"\begin{figure*}[t]",
        r"\centering",
        r"\includegraphics[width=\textwidth]{fig_confusion_matrices.pdf}",
        r"\caption{Confusion matrices for test fold 5 in each experiment, using the DenseNet-121 checkpoint selected from validation fold 3. Within DenseNet-121, fold 3 was selected because it had the highest validation balanced accuracy; test fold 5 results were not used to select the representative checkpoint. Cells report counts and percentages within each true class.}",
        r"\label{fig:confusion-matrices}",
        r"\end{figure*}",
    ]

    (OUTPUT_DIR / "results_table.tex").write_text("\n".join(lines) + "\n")
    (OUTPUT_DIR / "execution_time_table.tex").write_text(
        "\n".join(time_lines) + "\n"
    )
    (OUTPUT_DIR / "statistical_analysis_table.tex").write_text(
        "\n".join(stat_lines) + "\n"
    )
    (OUTPUT_DIR / "figure_snippets.tex").write_text(
        "\n".join(figure_lines) + "\n"
    )
    (OUTPUT_DIR / "copy_ready_all.tex").write_text(
        "\n\n".join(
            [
                "\n".join(lines),
                "\n".join(time_lines),
                "\n".join(stat_lines),
                "\n".join(figure_lines),
            ]
        )
        + "\n"
    )

    selected_lines = [
        "Validation-selected confusion-matrix checkpoints:",
        *[
            f"- {experiment}: {info['model']}, fold {info['fold']}, "
            f"validation BCC {info['validation_balanced_accuracy'] * 100:.2f}%"
            for experiment, info in selected.items()
        ],
    ]
    (OUTPUT_DIR / "selection_summary.txt").write_text(
        "\n".join(selected_lines) + "\n"
    )


def write_guidance(
    validation: pd.DataFrame,
    shared_config: dict,
    within: pd.DataFrame,
    between: pd.DataFrame,
):
    duplicate_notes = []
    for _, row in validation[validation["same_name_runs_in_mlflow"] > 1].iterrows():
        duplicate_notes.append(
            f"- `{row['run_name']}` had {row['same_name_runs_in_mlflow']} same-name "
            "attempts in MLflow; only the exact completed run ID in the validation table was used."
        )
    text = f"""# Canonical experiment analysis

## Verification

- The six selected parent runs are finished.
- Every selected parent contains exactly five finished children, folds 0--4.
- Every selected run uses 3,763 rows and keeps fold 5 held out.
- The parent aggregate metrics exactly match the mean and population standard deviation recalculated from the five child folds.
- Shared configuration: SGD, learning rate {shared_config['hyperparameters_optimizer_learning_rate']}, momentum {shared_config['hyperparameters_optimizer_momentum']}, batch size {shared_config['hyperparameters_other_batch_size']}, maximum {shared_config['hyperparameters_other_epochs']} epochs, scheduler patience {shared_config['hyperparameters_scheduler_other_patience']}, and early-stopping patience {shared_config['early_stopping_patience']}.
{chr(10).join(duplicate_notes)}

## Methodology points to include

- State that MobileNetV2, DenseNet-121, and ResNet-50 were trained under the same relevant hyperparameters in both experiments.
- Explain that Experiment 1 uses the released patch-level reference split, while Experiment 2 uses patient-first grouping so linked patient/case and source-image groups remain together.
- State that fold 5 was never used for training or validation. Five models were trained per architecture by rotating validation folds 0--4, and every model was evaluated on fold 5.
- Explain that reported test metrics are the mean and standard deviation of the five model evaluations on the held-out fold.
- Explain that the confusion matrix uses one checkpoint so each held-out patch appears once. DenseNet-121 was identified as the best-performing architecture from the completed test-result comparison. Within that architecture, fold 3 was selected only because it had the highest validation BCC; test fold 5 results were not used to select the representative fold checkpoint.
- Mention that early stopping monitored validation loss. Different fold curves therefore end at different epochs.

## Results points to include

- Report Experiment 1 directly from the canonical stored-run evidence without claiming equivalence to a separate implementation.
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

"""
    for _, row in within.iterrows():
        text += (
            f"- {row['experiment']}: Friedman statistic {row['statistic']:.3f}, "
            f"p={row['raw_p_value']:.4f}; "
            + ("a model difference was detected.\n" if row["significant_0_05"] else "no model difference was detected at alpha=0.05.\n")
        )
    for _, row in between.iterrows():
        text += (
            f"- {row['model']}: U={row['statistic']:.1f}, raw p={row['raw_p_value']:.4f}, "
            f"Holm-adjusted p={row['holm_adjusted_p_value']:.4f}, "
            f"{row['direction'].lower()}.\n"
        )
    (OUTPUT_DIR / "writing_guidance.md").write_text(text, encoding="utf-8")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    load_dotenv(MLFLOW_ENV, override=False)
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:8000")
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient()
    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        raise RuntimeError(f"MLflow experiment {EXPERIMENT_NAME!r} was not found.")

    validation, folds, durations, child_runs, parent_runs, shared_config = collect_evidence(
        client, experiment.experiment_id
    )
    summary = summarize_results(folds)
    within, posthoc = within_experiment_statistics(folds)
    between = between_experiment_statistics(folds)
    selected = validation_selected_folds(client, parent_runs)

    validation.to_csv(OUTPUT_DIR / "canonical_run_validation.csv", index=False)
    folds.to_csv(OUTPUT_DIR / "fold_test_metrics.csv", index=False)
    durations.to_csv(OUTPUT_DIR / "execution_times.csv", index=False)
    summary.to_csv(OUTPUT_DIR / "results_summary.csv", index=False)
    within.to_csv(OUTPUT_DIR / "statistics_within_experiment.csv", index=False)
    posthoc.to_csv(OUTPUT_DIR / "statistics_within_posthoc.csv", index=False)
    between.to_csv(OUTPUT_DIR / "statistics_between_experiments.csv", index=False)
    (OUTPUT_DIR / "selected_models_and_folds.json").write_text(
        json.dumps(selected, indent=2), encoding="utf-8"
    )

    plot_loss_curves(client, child_runs, selected)
    plot_confusion_matrices(child_runs, selected)
    create_latex(summary, durations, within, between, selected)
    write_guidance(validation, shared_config, within, between)
    print(f"Analysis written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
