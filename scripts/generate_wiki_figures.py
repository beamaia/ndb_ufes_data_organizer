#!/usr/bin/env python3
"""Generate documentation and thesis figures from current pipeline outputs."""

from __future__ import annotations

import argparse
import html as html_lib
import sys
import textwrap
from pathlib import Path

import cv2 as cv
import matplotlib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


matplotlib.use("Agg")
import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT))

from src.docs.figure_style import (  # noqa: E402
    LABCIN_BLUE,
    LABCIN_CORAL,
    LABCIN_DARK,
    LABCIN_GOLD,
    LABCIN_GREEN,
    LABCIN_LIGHT_GREEN,
    LABCIN_SEQUENCE,
    configure_matplotlib,
    configure_plotly,
    ensure_dir,
)


DOCS_FIGURE_DIR = PROJECT_ROOT / "docs/assets/generated"
DOCS_PLOTLY_PREVIEW_DIR = DOCS_FIGURE_DIR / "plotly_previews"
DOCS_CONTAMINATION_DIR = PROJECT_ROOT / "docs/assets/contamination"
DOCS_PLOTLY_DIR = PROJECT_ROOT / "docs/visualizations/generated"
DOCS_DATASET_GALLERY_PAGE = PROJECT_ROOT / "docs/dataset-figure-gallery.md"
DOCS_EXPLORATORY_PAGE = PROJECT_ROOT / "docs/exploratory-analysis.md"
DOCS_PHASE2_TUNING_PAGE = PROJECT_ROOT / "docs/phase2-tuning-diagnostics.md"
THESIS_FIGURE_DIR = PROJECT_ROOT / "results/thesis_figures"
THESIS_PLOTLY_DIR = THESIS_FIGURE_DIR / "plotly"
PLOTLY_SCRIPT = "../plotly-3.5.0.min.js"
EXPORT_PLOTLY_PREVIEWS = True
EXPORT_PLOTLY_THESIS = False
PHASE2_MIN_CLUSTER_SIZE = 11
PHASE2_MAX_CLUSTER_RATIO = 5.0

DATASET_FIELDS = [
    "age_group",
    "alcohol_consumption",
    "dysplasia_severity",
    "gender",
    "localization",
    "skin_color",
    "sun_exposure",
    "tobacco_use",
]

FIELD_LABELS = {
    "age_group": "Age Group",
    "alcohol_consumption": "Alcohol Consumption",
    "diagnosis": "Diagnosis",
    "dysplasia_severity": "Dysplasia Severity",
    "gender": "Gender",
    "localization": "Localization",
    "morph_cluster": "Morphology Cluster",
    "origin_diagnosis": "Origin Diagnosis",
    "skin_color": "Skin Color",
    "sun_exposure": "Sun Exposure",
    "TaskII": "Task II",
    "TaskIII": "Task III",
    "TaskIV": "Task IV",
    "tobacco_use": "Tobacco Use",
}

AGE_LABELS = {
    0: "Younger than 40",
    1: "40-60",
    2: "Older than 60",
    "0": "Younger than 40",
    "1": "40-60",
    "2": "Older than 60",
}


def save_matplotlib_figure(
    fig: plt.Figure,
    stem: str,
    title: str,
    source: str,
    docs_dir: Path = DOCS_FIGURE_DIR,
    thesis_dir: Path = THESIS_FIGURE_DIR,
) -> list[dict]:
    docs_dir = ensure_dir(docs_dir)
    thesis_dir = ensure_dir(thesis_dir)
    docs_png = docs_dir / f"{stem}.png"
    thesis_png = thesis_dir / f"{stem}.png"
    thesis_svg = thesis_dir / f"{stem}.svg"
    thesis_pdf = thesis_dir / f"{stem}.pdf"

    fig.savefig(docs_png)
    fig.savefig(thesis_png)
    fig.savefig(thesis_svg)
    fig.savefig(thesis_pdf)
    plt.close(fig)
    strip_trailing_whitespace(thesis_svg)

    return [
        {"title": title, "kind": "docs_png", "path": str(docs_png), "source": source},
        {"title": title, "kind": "thesis_png", "path": str(thesis_png), "source": source},
        {"title": title, "kind": "thesis_svg", "path": str(thesis_svg), "source": source},
        {"title": title, "kind": "thesis_pdf", "path": str(thesis_pdf), "source": source},
    ]


def strip_trailing_whitespace(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    cleaned = "\n".join(line.rstrip() for line in text.splitlines())
    if text.endswith("\n"):
        cleaned += "\n"
    path.write_text(cleaned, encoding="utf-8")


def save_plotly_html(fig, stem: str, title: str, source: str) -> dict:
    ensure_dir(DOCS_PLOTLY_DIR)
    output_path = DOCS_PLOTLY_DIR / f"{stem}.html"
    fig.update_layout(template="labcin")
    current_margin = fig.layout.margin.to_plotly_json() if fig.layout.margin else {}
    fig.update_layout(
        margin={
            "l": current_margin.get("l", 72),
            "r": current_margin.get("r", 32),
            "t": current_margin.get("t", 72),
            "b": current_margin.get("b", 72),
        }
    )
    html = fig.to_html(
        include_plotlyjs=False,
        full_html=True,
        div_id=f"plotly-{stem}",
        config={"responsive": True, "displaylogo": False},
    )
    html = html.replace("<head>", f'<head>\n<script src="{PLOTLY_SCRIPT}"></script>')
    output_path.write_text(html, encoding="utf-8")
    return {
        "title": title,
        "kind": "plotly_html",
        "path": str(output_path),
        "source": source,
    }


def save_plotly_static_exports(fig, stem: str, title: str, source: str) -> list[dict]:
    rows = []
    height = int(fig.layout.height) if fig.layout.height else 650

    if EXPORT_PLOTLY_PREVIEWS:
        ensure_dir(DOCS_PLOTLY_PREVIEW_DIR)
        docs_png = DOCS_PLOTLY_PREVIEW_DIR / f"{stem}.png"
        fig.write_image(docs_png, width=1200, height=height, scale=1)
        rows.append({
            "title": title,
            "kind": "plotly_preview_png",
            "path": str(docs_png),
            "source": source,
        })

    if not EXPORT_PLOTLY_THESIS:
        return rows

    ensure_dir(THESIS_PLOTLY_DIR)
    thesis_png = THESIS_PLOTLY_DIR / f"{stem}.png"
    thesis_svg = THESIS_PLOTLY_DIR / f"{stem}.svg"
    thesis_pdf = THESIS_PLOTLY_DIR / f"{stem}.pdf"
    fig.write_image(thesis_png, width=1600, height=height, scale=2)
    fig.write_image(thesis_svg, width=1600, height=height, scale=1)
    fig.write_image(thesis_pdf, width=1600, height=height, scale=1)
    strip_trailing_whitespace(thesis_svg)

    rows.extend([
        {"title": title, "kind": "plotly_thesis_png", "path": str(thesis_png), "source": source},
        {"title": title, "kind": "plotly_thesis_svg", "path": str(thesis_svg), "source": source},
        {"title": title, "kind": "plotly_thesis_pdf", "path": str(thesis_pdf), "source": source},
    ])
    return rows


def save_plotly_figure(fig, stem: str, title: str, source: str) -> list[dict]:
    return [
        save_plotly_html(fig, stem, title, source),
        *save_plotly_static_exports(fig, stem, title, source),
    ]


def wrap_label(value: object, width: int = 28) -> str:
    text = str(value)
    return "<br>".join(textwrap.wrap(text, width=width, break_long_words=False)) or text


def clean_category(series: pd.Series, column: str) -> pd.Series:
    cleaned = series.copy()
    if column == "age_group":
        cleaned = cleaned.map(lambda value: AGE_LABELS.get(value, value))
    cleaned = cleaned.astype("object")
    missing = cleaned.isna() | cleaned.astype(str).str.strip().isin(["", "nan", "None"])
    cleaned.loc[missing] = "Missing"
    return cleaned.astype(str)


def dataset_gallery_record(section: str, stem: str, title: str, caption: str) -> dict:
    preview = (
        f"../assets/generated/plotly_previews/{stem}.png"
        if EXPORT_PLOTLY_PREVIEWS
        else f"../assets/dataset_statistics/{stem}.png"
    )
    return {
        "section": section,
        "stem": stem,
        "title": title,
        "caption": caption,
        "preview": preview,
    }


def add_dataset_plotly_figure(
    rows: list[dict],
    section: str,
    stem: str,
    title: str,
    caption: str,
    fig,
    source: str,
) -> list[dict]:
    manifest = save_plotly_figure(fig, stem, title, source)
    rows.append(dataset_gallery_record(section, stem, title, caption))
    return manifest


def plotly_lazy_lines(row: dict) -> list[str]:
    title = html_lib.escape(row["title"])
    caption = html_lib.escape(row["caption"])
    stem = html_lib.escape(row["stem"])
    preview = html_lib.escape(row["preview"])
    return [
        f"### {row['title']}",
        "",
        (
            f'<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/{stem}.html" '
            f'data-plotly-title="{title}">'
        ),
        f'  <img class="plotly-preview-image" src="{preview}" alt="{title}" loading="lazy">',
        '  <button type="button" class="plotly-load-button">Load Interactive Figure</button>',
        '  <div class="plotly-lazy-target"></div>',
        "</div>",
        "",
        f'<p class="figure-caption">{caption}</p>',
        "",
    ]


def display_column_name(column: str) -> str:
    return FIELD_LABELS.get(column, column.replace("_", " ").title())


def display_model_name(model_name: str) -> str:
    replacements = {
        "ctranspath": "CTransPath",
        "deit": "DeiT",
        "efficientnet": "EfficientNet",
        "mocov3": "MoCo v3",
        "swin": "Swin",
        "uni": "UNI",
        "virchow": "Virchow",
        "vit": "ViT",
    }
    words = []
    for part in model_name.split("_"):
        words.append(replacements.get(part, part.upper() if part in {"b0", "b1"} else part.title()))
    return " ".join(words).replace("Patch16", "Patch 16").replace("Patch32", "Patch 32")


def representative_values(values: list[int], preferred: list[int]) -> set[int]:
    available = sorted({int(value) for value in values})
    selected = {value for value in preferred if value in available}
    if available:
        selected.add(available[0])
        selected.add(available[-1])
    return selected


def count_percent_frame(df: pd.DataFrame, column: str) -> pd.DataFrame:
    values = clean_category(df[column], column)
    counts = values.value_counts(dropna=False).rename_axis("category").reset_index(name="count")
    counts["percent"] = counts["count"] / counts["count"].sum() * 100
    counts["label"] = counts["count"].astype(str) + " (" + counts["percent"].round(1).astype(str) + "%)"
    return counts


def count_percent_plot(df: pd.DataFrame, column: str, title: str):
    counts = count_percent_frame(df, column).sort_values("count", ascending=True)
    counts["category_wrapped"] = counts["category"].map(wrap_label)
    fig = px.bar(
        counts,
        x="count",
        y="category_wrapped",
        color="category",
        orientation="h",
        text="label",
        title=title,
        labels={"category_wrapped": FIELD_LABELS.get(column, column), "count": "Rows"},
        color_discrete_sequence=LABCIN_SEQUENCE,
    )
    fig.update_layout(
        showlegend=False,
        height=max(420, 90 * len(counts) + 160),
        margin=dict(l=220, r=48, t=72, b=72),
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    return fig


def task_count_plot(df: pd.DataFrame, column: str, title: str):
    counts = count_percent_frame(df, column).sort_values("count", ascending=True)
    counts["category_wrapped"] = counts["category"].map(wrap_label)
    fig = px.bar(
        counts,
        x="count",
        y="category_wrapped",
        color="category",
        orientation="h",
        text="label",
        title=title,
        labels={"category_wrapped": FIELD_LABELS.get(column, column), "count": "Rows"},
        color_discrete_sequence=LABCIN_SEQUENCE,
    )
    fig.update_layout(
        showlegend=False,
        height=max(420, 90 * len(counts) + 160),
        margin=dict(l=220, r=48, t=72, b=72),
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    return fig


def row_percent_plot(df: pd.DataFrame, variable: str, title: str):
    data = pd.DataFrame({
        variable: clean_category(df[variable], variable),
        "diagnosis": clean_category(df["diagnosis"], "diagnosis"),
    })
    counts = pd.crosstab(data[variable], data["diagnosis"])
    percents = counts.div(counts.sum(axis=1), axis=0) * 100
    long_df = percents.reset_index().melt(
        id_vars=variable,
        var_name="diagnosis",
        value_name="percent",
    )
    long_df[f"{variable}_wrapped"] = long_df[variable].map(lambda value: wrap_label(value, 28))
    fig = px.bar(
        long_df,
        x="percent",
        y=f"{variable}_wrapped",
        color="diagnosis",
        orientation="h",
        title=title,
        labels={
            f"{variable}_wrapped": FIELD_LABELS.get(variable, variable),
            "percent": "Diagnosis share within category (%)",
        },
        color_discrete_sequence=LABCIN_SEQUENCE,
    )
    category_count = long_df[f"{variable}_wrapped"].nunique()
    fig.update_layout(
        height=max(460, 95 * category_count + 180),
        margin=dict(l=260, r=48, t=72, b=72),
    )
    return fig


def column_percent_plot(df: pd.DataFrame, variable: str, title: str):
    data = pd.DataFrame({
        variable: clean_category(df[variable], variable),
        "diagnosis": clean_category(df["diagnosis"], "diagnosis"),
    })
    counts = pd.crosstab(data["diagnosis"], data[variable])
    percents = counts.div(counts.sum(axis=1), axis=0) * 100
    long_df = percents.reset_index().melt(
        id_vars="diagnosis",
        var_name=variable,
        value_name="percent",
    )
    long_df["diagnosis_wrapped"] = long_df["diagnosis"].map(lambda value: wrap_label(value, 30))
    fig = px.bar(
        long_df,
        x="percent",
        y="diagnosis_wrapped",
        color=variable,
        orientation="h",
        title=title,
        labels={
            "diagnosis_wrapped": "Diagnosis",
            "percent": "Share within diagnosis (%)",
            variable: FIELD_LABELS.get(variable, variable),
        },
        color_discrete_sequence=LABCIN_SEQUENCE,
    )
    fig.update_layout(
        height=500,
        margin=dict(l=280, r=48, t=72, b=72),
    )
    return fig


def missingness_plot(df: pd.DataFrame, title: str):
    rows = []
    for column in DATASET_FIELDS:
        series = df[column]
        as_text = series.astype(str).str.strip().str.lower()
        missing = series.isna() | as_text.isin(["", "nan", "none"])
        not_informed = as_text.eq("not informed")
        rows.append({
            "field": FIELD_LABELS[column],
            "metric": "Missing",
            "percent": missing.mean() * 100,
        })
        rows.append({
            "field": FIELD_LABELS[column],
            "metric": "Not informed",
            "percent": not_informed.mean() * 100,
        })
    missing_df = pd.DataFrame(rows)
    missing_df["field_wrapped"] = missing_df["field"].map(lambda value: wrap_label(value, 26))
    fig = px.bar(
        missing_df,
        x="percent",
        y="field_wrapped",
        color="metric",
        orientation="h",
        barmode="group",
        title=title,
        labels={"field_wrapped": "Field", "percent": "Rows (%)", "metric": "Metric"},
        color_discrete_sequence=[LABCIN_CORAL, LABCIN_GOLD],
    )
    fig.update_layout(height=720, margin=dict(l=260, r=48, t=72, b=72))
    return fig


def write_dataset_figure_gallery(rows: list[dict]) -> None:
    lines = [
        "# Dataset Figure Gallery",
        "",
        "This page lists Plotly counterparts for the dataset-statistics figures that were previously only available as static notebook images. The figures are descriptive. They document counts, percentages, missingness, and associations used for dataset understanding, not downstream model performance.",
        "",
        "Each figure starts as a fast static preview. Use **Load Interactive Figure** to open the Plotly version in place. This keeps the page usable while still keeping every converted graph available in the wiki.",
        "",
        "Interactive Plotly files are saved under `docs/visualizations/generated/`. Fast Plotly PNG previews are saved under `docs/assets/generated/plotly_previews/`. Curated thesis exports are saved under `results/thesis_figures/`. Full Plotly PNG/SVG/PDF thesis copies can be generated with `--export-plotly-thesis` when needed.",
        "",
        "Regenerate this page with:",
        "",
        "```bash",
        "uv run python scripts/generate_wiki_figures.py",
        "```",
        "",
    ]
    current_section = None
    for row in rows:
        if row["section"] != current_section:
            current_section = row["section"]
            lines.extend([f"## {current_section}", ""])
        lines.extend(plotly_lazy_lines(row))
    lines.extend([
        "<div class=\"ndb-next\" markdown>",
        "<strong>Related read:</strong> [Exploratory Analysis](exploratory-analysis.md)",
        "</div>",
        "",
    ])
    DOCS_DATASET_GALLERY_PAGE.write_text("\n".join(lines), encoding="utf-8")


def write_exploratory_analysis(rows: list[dict]) -> None:
    lines = [
        "# Exploratory Analysis",
        "",
        "This page collects the full converted Plotly set for the dataset organization work. These plots are descriptive. They document the available metadata, matched subset, missingness, and variable relationships used to decide what belongs in the public factsheet and what should not silently drive fold construction.",
        "",
        "The page uses static previews first and loads the interactive Plotly version only when **Load Interactive Figure** is pressed. This prevents the browser from initializing dozens of Plotly charts at once.",
        "",
        "## Main Insights",
        "",
        "- The matched fold-design subset contains 203 origins from the 237 origin-level metadata rows currently present in the source metadata copy.",
        "- Origin-level and patch-level class counts should be read separately because origins contribute different numbers of patches.",
        "- The current patch-level matched subset is largest for OSCC, followed by leukoplakia with dysplasia and leukoplakia without dysplasia.",
        "- Skin color, tobacco use, alcohol consumption, and sun exposure have high `Not informed` rates. They are useful for descriptive context, but they should not be treated as complete clinical covariates.",
        "- Dysplasia severity is missing for many rows because it is not meaningful or available for every diagnostic category.",
        "- Association charts are screening views. They describe relationships in the metadata and do not prove causality or downstream model quality.",
        "",
        "## How To Read These Figures",
        "",
        "- Count bars show how many origin or patch rows belong to each category.",
        "- Percent labels are calculated within the plotted level.",
        "- Row-percentage plots sum to 100 percent within each category on the x-axis.",
        "- Column-percentage plots sum to 100 percent within each diagnosis.",
        "- The colors use the Labcin blue/green palette with bright complementary colors for contrast.",
        "",
    ]
    current_section = None
    for row in rows:
        if row["section"] != current_section:
            current_section = row["section"]
            lines.extend([f"## {current_section}", ""])
        lines.extend(plotly_lazy_lines(row))
    lines.extend([
        "<div class=\"ndb-next\" markdown>",
        "<strong>Next read:</strong> [Dataset Factsheet](factsheet.md)",
        "</div>",
        "",
    ])
    DOCS_EXPLORATORY_PAGE.write_text("\n".join(lines), encoding="utf-8")


def generate_phase2_selection() -> list[dict]:
    source = PROJECT_ROOT / "results/phase2_tuning/phase2_model_selection.csv"
    selection = pd.read_csv(source)
    selection["plot_score"] = selection["silhouette_score"].fillna(0.0)
    selection["display_score"] = np.where(
        selection["eligibility_status"].eq("eligible"),
        selection["plot_score"],
        0.015,
    )
    selection = selection.sort_values("silhouette_score", ascending=True)
    labels = selection["model_name"].str.replace("_", " ", regex=False)
    colors = np.where(
        selection["eligibility_status"].eq("eligible"),
        LABCIN_GREEN,
        LABCIN_CORAL,
    )

    fig, ax = plt.subplots(figsize=(9, 5.6))
    ax.barh(labels, selection["display_score"], color=colors)
    ax.set_title("Phase 2 Model Selection")
    ax.set_xlabel("Mean silhouette score for eligible configurations")
    ax.set_ylabel("")
    ax.axvline(0, color="#d7deea", linewidth=1)
    for y_position, row in enumerate(selection.itertuples()):
        if row.eligibility_status != "eligible":
            ax.text(0.025, y_position, "rejected", va="center", color=LABCIN_CORAL)
    ax.legend(
        handles=[
            plt.Rectangle((0, 0), 1, 1, color=LABCIN_GREEN, label="Eligible"),
            plt.Rectangle((0, 0), 1, 1, color=LABCIN_CORAL, label="Rejected"),
        ],
        loc="lower right",
    )
    manifest = save_matplotlib_figure(
        fig,
        "phase2_model_selection",
        "Phase 2 model selection",
        str(source),
    )

    plotly_fig = px.bar(
        selection.sort_values("silhouette_score", ascending=False),
        x="display_score",
        y="model_name",
        color="eligibility_status",
        orientation="h",
        title="Phase 2 Model Selection",
        labels={
            "display_score": "Mean silhouette score for eligible configurations",
            "model_name": "Model",
            "eligibility_status": "Eligibility",
        },
        color_discrete_map={"eligible": LABCIN_GREEN, "rejected": LABCIN_CORAL},
    )
    plotly_fig.update_yaxes(autorange="reversed")
    manifest.extend(
        save_plotly_figure(
            plotly_fig,
            "phase2_model_selection",
            "Phase 2 model selection",
            str(source),
        )
    )
    return manifest


def phase2_metric_frame(model_name: str) -> pd.DataFrame:
    source = PROJECT_ROOT / "results/phase2_tuning" / f"phase2_all_results_{model_name}_averaged.csv"
    if not source.exists():
        raise FileNotFoundError(f"Missing averaged Phase 2 results for {model_name}: {source}")

    df = pd.read_csv(source).copy()
    df["model_name"] = model_name
    df["model_display"] = display_model_name(model_name)
    df["source_file"] = str(source)
    df["pca_components"] = df["pca_components"].astype(int)
    df["kmeans_clusters"] = df["kmeans_clusters"].astype(int)
    df["inertia_value"] = df["inertia_mean"] if "inertia_mean" in df else df["inertia"]
    df["silhouette_value"] = (
        df["silhouette_mean"] if "silhouette_mean" in df else df["silhouette"]
    )

    if "min_cluster_size_min" in df and "cluster_size_ratio_max" in df:
        df["min_cluster_size"] = df["min_cluster_size_min"]
        df["cluster_size_ratio"] = df["cluster_size_ratio_max"]
        df["fold_eligible"] = (
            (df["min_cluster_size"] >= PHASE2_MIN_CLUSTER_SIZE)
            & (df["cluster_size_ratio"] <= PHASE2_MAX_CLUSTER_RATIO)
        )
    else:
        df["min_cluster_size"] = np.nan
        df["cluster_size_ratio"] = np.nan
        df["fold_eligible"] = True
    return df


def accepted_phase2_row(selection: pd.DataFrame, model_name: str) -> pd.Series | None:
    rows = selection[
        selection["model_name"].eq(model_name)
        & selection["eligibility_status"].eq("eligible")
    ]
    if rows.empty:
        return None
    return rows.iloc[0]


def add_selected_marker(fig: go.Figure, selected: pd.Series | None, x_value: float, y_value: float) -> None:
    if selected is None:
        return
    fig.add_trace(
        go.Scatter(
            x=[x_value],
            y=[y_value],
            mode="markers",
            marker={
                "symbol": "star",
                "size": 16,
                "color": LABCIN_CORAL,
                "line": {"color": "#17315f", "width": 1.5},
            },
            name="Accepted selection",
            hovertemplate="Accepted selection<extra></extra>",
        )
    )


def phase2_elbow_figure(df: pd.DataFrame, selected: pd.Series | None):
    model_display = df["model_display"].iloc[0]
    visible_pca = representative_values(df["pca_components"].tolist(), [2, 3, 5, 8, 10, 15])
    fig = go.Figure()
    for index, pca_value in enumerate(sorted(df["pca_components"].unique())):
        subset = df[df["pca_components"].eq(pca_value)].sort_values("kmeans_clusters")
        fig.add_trace(
            go.Scatter(
                x=subset["kmeans_clusters"],
                y=subset["inertia_value"],
                mode="lines+markers",
                name=f"PCA {pca_value}",
                visible=True if pca_value in visible_pca else "legendonly",
                line={"color": LABCIN_SEQUENCE[index % len(LABCIN_SEQUENCE)]},
                hovertemplate=(
                    "PCA components=%{customdata[0]}<br>"
                    "K clusters=%{x}<br>"
                    "Inertia=%{y:.2f}<extra></extra>"
                ),
                customdata=np.stack([subset["pca_components"]], axis=-1),
            )
        )
    if selected is not None:
        selected_point = df[
            df["pca_components"].eq(int(selected["pca_components"]))
            & df["kmeans_clusters"].eq(int(selected["kmeans_clusters"]))
        ]
        if not selected_point.empty:
            add_selected_marker(
                fig,
                selected,
                int(selected["kmeans_clusters"]),
                float(selected_point["inertia_value"].iloc[0]),
            )
    fig.update_layout(
        title=f"{model_display}: Elbow Curve",
        xaxis_title="K-Means clusters",
        yaxis_title="Inertia. Lower means tighter clusters.",
        height=620,
        margin=dict(l=92, r=48, t=76, b=72),
        legend_title="PCA components",
    )
    return fig


def phase2_inertia_by_pca_figure(df: pd.DataFrame, selected: pd.Series | None):
    model_display = df["model_display"].iloc[0]
    visible_k = representative_values(df["kmeans_clusters"].tolist(), [2, 3, 4, 5, 6, 8])
    fig = go.Figure()
    for index, k_value in enumerate(sorted(df["kmeans_clusters"].unique())):
        subset = df[df["kmeans_clusters"].eq(k_value)].sort_values("pca_components")
        fig.add_trace(
            go.Scatter(
                x=subset["pca_components"],
                y=subset["inertia_value"],
                mode="lines+markers",
                name=f"K {k_value}",
                visible=True if k_value in visible_k else "legendonly",
                line={"color": LABCIN_SEQUENCE[index % len(LABCIN_SEQUENCE)]},
                hovertemplate=(
                    "PCA components=%{x}<br>"
                    "K clusters=%{customdata[0]}<br>"
                    "Inertia=%{y:.2f}<extra></extra>"
                ),
                customdata=np.stack([subset["kmeans_clusters"]], axis=-1),
            )
        )
    if selected is not None:
        selected_point = df[
            df["pca_components"].eq(int(selected["pca_components"]))
            & df["kmeans_clusters"].eq(int(selected["kmeans_clusters"]))
        ]
        if not selected_point.empty:
            add_selected_marker(
                fig,
                selected,
                int(selected["pca_components"]),
                float(selected_point["inertia_value"].iloc[0]),
            )
    fig.update_layout(
        title=f"{model_display}: Inertia By PCA Components",
        xaxis_title="PCA components",
        yaxis_title="Inertia. Lower means tighter clusters.",
        height=620,
        margin=dict(l=92, r=48, t=76, b=72),
        legend_title="K clusters",
    )
    return fig


def phase2_silhouette_by_k_figure(df: pd.DataFrame, selected: pd.Series | None):
    model_display = df["model_display"].iloc[0]
    visible_pca = representative_values(df["pca_components"].tolist(), [2, 3, 5, 8, 10, 15])
    fig = go.Figure()
    for index, pca_value in enumerate(sorted(df["pca_components"].unique())):
        subset = df[df["pca_components"].eq(pca_value)].sort_values("kmeans_clusters")
        fig.add_trace(
            go.Scatter(
                x=subset["kmeans_clusters"],
                y=subset["silhouette_value"],
                mode="lines+markers",
                name=f"PCA {pca_value}",
                visible=True if pca_value in visible_pca else "legendonly",
                line={"color": LABCIN_SEQUENCE[index % len(LABCIN_SEQUENCE)]},
                hovertemplate=(
                    "PCA components=%{customdata[0]}<br>"
                    "K clusters=%{x}<br>"
                    "Mean silhouette=%{y:.3f}<extra></extra>"
                ),
                customdata=np.stack([subset["pca_components"]], axis=-1),
            )
        )
    if selected is not None:
        selected_point = df[
            df["pca_components"].eq(int(selected["pca_components"]))
            & df["kmeans_clusters"].eq(int(selected["kmeans_clusters"]))
        ]
        if not selected_point.empty:
            add_selected_marker(
                fig,
                selected,
                int(selected["kmeans_clusters"]),
                float(selected_point["silhouette_value"].iloc[0]),
            )
    fig.update_layout(
        title=f"{model_display}: Silhouette By K",
        xaxis_title="K-Means clusters",
        yaxis_title="Mean silhouette. Higher means cleaner separation.",
        height=620,
        margin=dict(l=92, r=48, t=76, b=72),
        legend_title="PCA components",
    )
    return fig


def phase2_silhouette_heatmap_figure(df: pd.DataFrame, selected: pd.Series | None):
    model_display = df["model_display"].iloc[0]
    pivot = (
        df.pivot_table(
            index="pca_components",
            columns="kmeans_clusters",
            values="silhouette_value",
        )
        .sort_index()
        .sort_index(axis=1)
    )
    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns.astype(int),
            y=pivot.index.astype(int),
            colorscale=[
                [0.0, "#f7fbff"],
                [0.35, "#bde5b4"],
                [0.7, LABCIN_GREEN],
                [1.0, LABCIN_BLUE],
            ],
            colorbar={"title": "Mean silhouette"},
            hovertemplate=(
                "PCA components=%{y}<br>"
                "K clusters=%{x}<br>"
                "Mean silhouette=%{z:.3f}<extra></extra>"
            ),
        )
    )
    values = pivot.to_numpy(dtype=float)
    finite_values = values[np.isfinite(values)]
    label_threshold = (
        float(finite_values.min() + 0.65 * (finite_values.max() - finite_values.min()))
        if finite_values.size
        else 0.0
    )
    for pca_value in pivot.index.astype(int):
        for k_value in pivot.columns.astype(int):
            value = pivot.loc[pca_value, k_value]
            if not np.isfinite(value):
                continue
            fig.add_annotation(
                x=int(k_value),
                y=int(pca_value),
                text=f"{value:.3f}",
                showarrow=False,
                font={
                    "size": 10,
                    "color": "#ffffff" if value >= label_threshold else LABCIN_DARK,
                },
            )
    if selected is not None:
        fig.add_trace(
            go.Scatter(
                x=[int(selected["kmeans_clusters"])],
                y=[int(selected["pca_components"])],
                mode="markers",
                marker={
                    "symbol": "circle-open",
                    "size": 18,
                    "color": LABCIN_CORAL,
                    "line": {"width": 3},
                },
                name="Accepted selection",
                hovertemplate="Accepted selection<extra></extra>",
            )
        )
    fig.update_layout(
        title=f"{model_display}: Silhouette Heatmap",
        xaxis_title="K-Means clusters",
        yaxis_title="PCA components",
        height=680,
        margin=dict(l=92, r=48, t=76, b=72),
    )
    return fig


def phase2_top10_figure(df: pd.DataFrame):
    model_display = df["model_display"].iloc[0]
    top = df.sort_values("silhouette_value", ascending=False).head(10).copy()
    top["configuration"] = (
        "PCA "
        + top["pca_components"].astype(str)
        + ". K "
        + top["kmeans_clusters"].astype(str)
    )
    top["configuration_wrapped"] = top["configuration"].map(lambda value: wrap_label(value, 20))
    top["eligibility"] = np.where(top["fold_eligible"], "Fold-ready", "Rejected")
    top["label"] = top["silhouette_value"].round(3).astype(str)
    fig = px.bar(
        top.sort_values("silhouette_value", ascending=True),
        x="silhouette_value",
        y="configuration_wrapped",
        color="eligibility",
        orientation="h",
        text="label",
        title=f"{model_display}: Top 10 Configurations By Silhouette",
        labels={
            "silhouette_value": "Mean silhouette",
            "configuration_wrapped": "Configuration",
            "eligibility": "Fold readiness",
        },
        color_discrete_map={"Fold-ready": LABCIN_GREEN, "Rejected": LABCIN_CORAL},
        hover_data={
            "pca_components": True,
            "kmeans_clusters": True,
            "min_cluster_size": ":.0f",
            "cluster_size_ratio": ":.2f",
            "configuration_wrapped": False,
            "label": False,
        },
        height=620,
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(margin=dict(l=170, r=72, t=76, b=72))
    return fig


def phase2_tuning_record(section: str, stem: str, title: str, caption: str) -> dict:
    preview = (
        f"../assets/generated/plotly_previews/{stem}.png"
        if EXPORT_PLOTLY_PREVIEWS
        else f"../assets/generated/phase2_model_selection.png"
    )
    return {
        "section": section,
        "stem": stem,
        "title": title,
        "caption": caption,
        "preview": preview,
    }


def save_phase2_tuning_figure(
    rows: list[dict],
    section: str,
    stem: str,
    title: str,
    caption: str,
    fig,
    source: str,
) -> list[dict]:
    rows.append(phase2_tuning_record(section, stem, title, caption))
    return save_plotly_figure(fig, stem, title, source)


def write_phase2_tuning_page(rows: list[dict], selection: pd.DataFrame) -> None:
    accepted = selection[selection["eligibility_status"].eq("eligible")].iloc[0]
    lines = [
        "# Phase 2 Tuning Diagnostics",
        "",
        "This page documents the diagnostic plots used to choose the Phase 2 morphology signal. The figures are generated from the averaged Phase 2 result files when repeated runs are available. The final accepted selection is still derived by rule: a configuration must be fold-ready first, and only eligible configurations are ranked by silhouette.",
        "",
        "## Selected Result",
        "",
        "| Field | Value |",
        "| --- | ---: |",
        f"| Model | {display_model_name(str(accepted['model_name']))} |",
        f"| PCA components | {int(accepted['pca_components'])} |",
        f"| K-Means clusters | {int(accepted['kmeans_clusters'])} |",
        f"| Mean silhouette | {accepted['silhouette_score']:.6f} |",
        f"| Minimum cluster size | {int(accepted['min_cluster_size'])} origins |",
        f"| Largest/smallest cluster ratio | {accepted['max_cluster_size_ratio']:.2f} |",
        "",
        "## How To Read The Diagnostics",
        "",
        "- **PCA components** means how many compressed embedding dimensions are kept before clustering. Lower values are simpler. Higher values keep more detail but can add noise.",
        "- **K** is the number of clusters requested from K-Means. In this project, clusters are not labels. They are morphology groups used as one stratification signal for fold construction.",
        "- **Inertia** measures how tightly points sit around their cluster centers. Lower is tighter. Inertia usually drops when K increases, so it is read by looking for an elbow where the drop starts slowing down.",
        "- **Silhouette** measures how separated the clusters are. Higher is usually better, but it can be misleading if one cluster is tiny.",
        f"- **Fold-ready** means every cluster has at least {PHASE2_MIN_CLUSTER_SIZE} origins and the largest cluster is no more than {PHASE2_MAX_CLUSTER_RATIO:g} times the smallest cluster.",
        "- **Rejected** configurations are not allowed to drive Phase 3, even if their silhouette is high, because they would make unsafe or unstable folds.",
        "",
        "## Figure Guide",
        "",
        "- **Elbow curve**. Read from left to right. A sharp early drop means adding clusters helped. A flat line means extra clusters are doing less useful work.",
        "- **Inertia by PCA**. Read whether adding PCA components keeps reducing cluster spread. A lower curve is tighter, but this is not enough on its own.",
        "- **Silhouette by K**. Read peaks as cleaner separations for a given PCA setting.",
        "- **Silhouette heatmap**. Rows are PCA components and columns are K. Stronger color means higher silhouette. A red outlined marker shows the accepted configuration when the model has one.",
        "- **Top 10 configurations**. Green bars are fold-ready. Red bars fail fold-readiness and are shown only to explain why a high score was not selected.",
        "",
    ]

    current_section = None
    for row in rows:
        if row["section"] != current_section:
            current_section = row["section"]
            lines.extend([f"## {current_section}", ""])
        lines.extend(plotly_lazy_lines(row))

    lines.extend([
        "<div class=\"ndb-next\" markdown>",
        "<strong>Next result:</strong> [Phase 3 Results](phase3-results.md)",
        "</div>",
        "",
    ])
    DOCS_PHASE2_TUNING_PAGE.write_text("\n".join(lines), encoding="utf-8")


def generate_phase2_tuning_diagnostics() -> list[dict]:
    selection_source = PROJECT_ROOT / "results/phase2_tuning/phase2_model_selection.csv"
    selection = pd.read_csv(selection_source)
    model_names = selection["model_name"].tolist()
    manifest: list[dict] = []
    page_rows: list[dict] = []
    top10_rows = []
    combined_rows = []

    for model_name in model_names:
        df = phase2_metric_frame(model_name)
        selected = accepted_phase2_row(selection, model_name)
        display_name = display_model_name(model_name)
        source = df["source_file"].iloc[0]
        combined_rows.append(df)

        figure_specs = [
            (
                "elbow",
                "Elbow Curve",
                "Shows how much K-Means inertia drops as more clusters are added. Look for the bend where adding clusters stops helping as much.",
                phase2_elbow_figure(df, selected),
            ),
            (
                "inertia_by_pca",
                "Inertia By PCA Components",
                "Shows whether keeping more PCA dimensions makes clusters tighter. Lower inertia is tighter, but it is not the final selection rule.",
                phase2_inertia_by_pca_figure(df, selected),
            ),
            (
                "silhouette_by_k",
                "Silhouette By K",
                "Shows how cluster separation changes as K changes. Peaks are useful candidates, but only fold-ready candidates can be selected.",
                phase2_silhouette_by_k_figure(df, selected),
            ),
            (
                "silhouette_heatmap",
                "Silhouette Heatmap",
                "Shows the full PCA-by-K grid. Stronger color means higher silhouette. The red marker shows the accepted configuration when available.",
                phase2_silhouette_heatmap_figure(df, selected),
            ),
            (
                "top10_configurations",
                "Top 10 Configurations",
                "Ranks the ten highest-silhouette configurations for this model. Red bars failed fold-readiness and are not valid Phase 3 inputs.",
                phase2_top10_figure(df),
            ),
        ]

        top = df.sort_values("silhouette_value", ascending=False).head(10).copy()
        top10_rows.append(top)
        for suffix, title_suffix, caption, fig in figure_specs:
            stem = f"phase2_{suffix}_{model_name}"
            title = f"{display_name}: {title_suffix}"
            manifest.extend(save_phase2_tuning_figure(
                page_rows,
                display_name,
                stem,
                title,
                caption,
                fig,
                source,
            ))

    ensure_dir(DOCS_FIGURE_DIR)
    pd.concat(combined_rows, ignore_index=True).to_csv(
        DOCS_FIGURE_DIR / "phase2_tuning_diagnostics.csv",
        index=False,
    )
    pd.concat(top10_rows, ignore_index=True).to_csv(
        DOCS_FIGURE_DIR / "phase2_tuning_top10_configurations.csv",
        index=False,
    )
    write_phase2_tuning_page(page_rows, selection)
    return manifest


def generate_dataset_diagnosis_summary() -> list[dict]:
    origin_source = PROJECT_ROOT / "results/phase3_fold_creation/fold_assignments_origin.csv"
    patch_source = PROJECT_ROOT / "results/phase3_fold_creation/fold_assignments_patch_level.csv"
    origin_df = pd.read_csv(origin_source)
    patch_df = pd.read_csv(patch_source)

    origin_counts = origin_df["origin_diagnosis"].value_counts().rename("Origins")
    patch_counts = patch_df["diagnosis"].value_counts().rename("Patches")
    summary = pd.concat([origin_counts, patch_counts], axis=1).fillna(0).astype(int)
    summary = summary.loc[
        [
            "OSCC",
            "Leukoplakia with dysplasia",
            "Leukoplakia without dysplasia",
        ]
    ]
    summary.to_csv(ensure_dir(DOCS_FIGURE_DIR) / "dataset_diagnosis_summary.csv")

    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    x = np.arange(len(summary))
    width = 0.36
    ax.bar(x - width / 2, summary["Origins"], width, label="Origins", color=LABCIN_BLUE)
    ax.bar(x + width / 2, summary["Patches"], width, label="Patches", color=LABCIN_GREEN)
    ax.set_title("Matched Subset Diagnosis Counts")
    ax.set_ylabel("Rows")
    ax.set_xticks(x)
    ax.set_xticklabels(summary.index, rotation=15, ha="right")
    ax.legend()
    manifest = save_matplotlib_figure(
        fig,
        "dataset_diagnosis_summary",
        "Matched subset diagnosis summary",
        f"{origin_source}; {patch_source}",
    )

    long_df = summary.reset_index(names="diagnosis").melt(
        id_vars="diagnosis",
        var_name="level",
        value_name="count",
    )
    long_df["diagnosis_wrapped"] = long_df["diagnosis"].map(lambda value: wrap_label(value, 30))
    plotly_fig = px.bar(
        long_df,
        x="count",
        y="diagnosis_wrapped",
        color="level",
        orientation="h",
        barmode="group",
        title="Matched Subset Diagnosis Counts",
        labels={"diagnosis_wrapped": "Diagnosis", "count": "Rows", "level": "Level"},
        color_discrete_sequence=[LABCIN_BLUE, LABCIN_GREEN],
    )
    plotly_fig.update_layout(height=500, margin=dict(l=280, r=48, t=72, b=72))
    manifest.extend(
        save_plotly_figure(
            plotly_fig,
            "dataset_diagnosis_summary",
            "Matched subset diagnosis summary",
            f"{origin_source}; {patch_source}",
        )
    )
    return manifest


def generate_source_task_counts() -> list[dict]:
    source = "NDB-UFES source paper task counts"
    task_counts = pd.DataFrame([
        {"task": "Task II", "class": "Leukoplakia", "origin_count": 146},
        {"task": "Task II", "class": "OSCC", "origin_count": 91},
        {"task": "Task III", "class": "Presence", "origin_count": 180},
        {"task": "Task III", "class": "Absence", "origin_count": 57},
        {"task": "Task IV", "class": "OSCC", "origin_count": 91},
        {"task": "Task IV", "class": "Leukoplakia with dysplasia", "origin_count": 89},
        {"task": "Task IV", "class": "Leukoplakia without dysplasia", "origin_count": 57},
    ])
    task_counts.to_csv(ensure_dir(DOCS_FIGURE_DIR) / "source_task_counts.csv", index=False)

    fig, axes = plt.subplots(3, 1, figsize=(9, 7.5), sharex=True)
    for ax, (task, group) in zip(axes, task_counts.groupby("task", sort=False)):
        colors = LABCIN_SEQUENCE[:len(group)]
        group = group.sort_values("origin_count", ascending=True)
        ax.barh(group["class"], group["origin_count"], color=colors)
        ax.set_title(task)
        ax.set_ylabel("")
    axes[-1].set_xlabel("Origin count")
    fig.suptitle("Source-Paper NDB-UFES Task Counts", y=1.02)
    manifest = save_matplotlib_figure(
        fig,
        "source_task_counts",
        "Source-paper NDB-UFES task counts",
        source,
    )

    task_counts["task_class"] = task_counts["task"] + ". " + task_counts["class"]
    task_counts["task_class_wrapped"] = task_counts["task_class"].map(lambda value: wrap_label(value, 34))
    plotly_fig = px.bar(
        task_counts.sort_values(["task", "origin_count"], ascending=[False, True]),
        x="origin_count",
        y="task_class_wrapped",
        color="task",
        orientation="h",
        title="Source-Paper NDB-UFES Task Counts",
        labels={"task_class_wrapped": "Task and class", "origin_count": "Origin count", "task": "Task"},
        color_discrete_sequence=LABCIN_SEQUENCE,
        height=620,
    )
    plotly_fig.update_layout(margin=dict(l=300, r=48, t=80, b=72))
    manifest.extend(
        save_plotly_figure(
            plotly_fig,
            "source_task_counts",
            "Source-paper NDB-UFES task counts",
            source,
        )
    )
    return manifest


def generate_top_cramers_v() -> list[dict]:
    source = PROJECT_ROOT / "results/dataset_statistics/categorical_association_cramers_v.csv"
    associations = pd.read_csv(source).head(12)
    associations["pair"] = associations["var_a"] + " x " + associations["var_b"]
    associations["pair_label"] = (
        associations["var_a"].map(display_column_name)
        + " x "
        + associations["var_b"].map(display_column_name)
    )
    associations["pair_wrapped"] = associations["pair_label"].map(lambda value: wrap_label(value, 30))
    associations = associations.sort_values("cramers_v", ascending=True)
    associations.to_csv(ensure_dir(DOCS_FIGURE_DIR) / "top_cramers_v.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 6.3))
    ax.barh(associations["pair_label"], associations["cramers_v"], color=LABCIN_GOLD)
    ax.set_title("Top Categorical Associations")
    ax.set_xlabel("Cramer's V")
    ax.set_ylabel("")
    ax.set_xlim(0, 1)
    manifest = save_matplotlib_figure(
        fig,
        "top_cramers_v",
        "Top categorical associations",
        str(source),
    )

    plotly_fig = px.bar(
        associations.sort_values("cramers_v", ascending=False),
        x="cramers_v",
        y="pair_wrapped",
        orientation="h",
        title="Top Categorical Associations",
        labels={"cramers_v": "Cramer's V", "pair_wrapped": "Variable pair"},
        color_discrete_sequence=[LABCIN_GOLD],
        height=720,
    )
    plotly_fig.update_yaxes(autorange="reversed")
    plotly_fig.update_layout(margin=dict(l=320, r=48, t=72, b=72))
    manifest.extend(
        save_plotly_figure(
            plotly_fig,
            "top_cramers_v",
            "Top categorical associations",
            str(source),
        )
    )
    return manifest


def generate_dataset_statistics_gallery() -> list[dict]:
    origin_source = PROJECT_ROOT / "data/ndb_ufes/origin_level/csvs/ndb-ufes.csv"
    patch_source = PROJECT_ROOT / "data/ndb_ufes/patch/parcial_pndb_ufes.csv"
    matched_origin_source = PROJECT_ROOT / "results/phase3_fold_creation/fold_assignments_origin.csv"
    association_source = PROJECT_ROOT / "results/dataset_statistics/categorical_association_cramers_v.csv"

    source_origin_df = pd.read_csv(origin_source)
    patch_df = pd.read_csv(patch_source)
    matched_origin_df = pd.read_csv(matched_origin_source).rename(
        columns={"origin_diagnosis": "diagnosis"}
    )
    matched_origin_ids = set(matched_origin_df["origin_id"].astype(int))
    matched_source_origin_df = source_origin_df[
        source_origin_df["public_id"].astype(int).isin(matched_origin_ids)
    ].copy()
    origin_stats_df = matched_source_origin_df

    manifest: list[dict] = []
    gallery_rows: list[dict] = []

    source_counts = source_origin_df["diagnosis"].value_counts().rename("source_origin_count")
    matched_counts = origin_stats_df["diagnosis"].value_counts().rename("matched_origin_count")
    diagnosis_compare = (
        pd.concat([source_counts, matched_counts], axis=1)
        .fillna(0)
        .astype(int)
        .reset_index(names="diagnosis")
        .melt(id_vars="diagnosis", var_name="level", value_name="count")
    )
    diagnosis_compare["level"] = diagnosis_compare["level"].map({
        "source_origin_count": "Source metadata",
        "matched_origin_count": "Matched subset",
    })
    diagnosis_compare["diagnosis_wrapped"] = diagnosis_compare["diagnosis"].map(
        lambda value: wrap_label(value, 30)
    )
    fig = px.bar(
        diagnosis_compare,
        x="count",
        y="diagnosis_wrapped",
        color="level",
        orientation="h",
        barmode="group",
        title="Origin Diagnosis: Source Metadata vs Matched Subset",
        labels={"diagnosis_wrapped": "Diagnosis", "count": "Origins", "level": "Level"},
        color_discrete_sequence=[LABCIN_BLUE, LABCIN_GREEN],
        height=500,
    )
    fig.update_layout(margin=dict(l=280, r=48, t=72, b=72))
    manifest.extend(add_dataset_plotly_figure(
        gallery_rows,
        "Diagnosis And Source Tasks",
        "01a_origin_diagnosis_actual_vs_matched_stacked",
        "Origin Diagnosis: Source Metadata vs Matched Subset",
        "Compares all origin metadata rows with the currently matched origins used for fold design.",
        fig,
        f"{origin_source}; {matched_origin_source}",
    ))

    diagnosis_specs = [
        (origin_stats_df, "diagnosis", "01b_origin_diagnosis_matched_count_percent", "Origin Diagnosis In Matched Subset", "Origin-level parent-image counts in the matched fold-design subset."),
        (patch_df, "diagnosis", "01c_patch_diagnosis_matched_count_percent", "Patch Diagnosis In Matched Subset", "Patch-row counts in the matched fold-design subset."),
    ]
    for df, column, stem, title, caption in diagnosis_specs:
        manifest.extend(add_dataset_plotly_figure(
            gallery_rows,
            "Diagnosis And Source Tasks",
            stem,
            title,
            caption,
            count_percent_plot(df, column, title),
            str(patch_source if df is patch_df else origin_source),
        ))

    task_specs = [
        (patch_df, "TaskII", "02a_patch_taskii_count_percent", "Patch Task II Distribution"),
        (origin_stats_df, "TaskII", "02a_taskii_origin_count_percent", "Origin Task II Distribution"),
        (patch_df, "TaskII", "02a_taskii_patch_count_percent", "Patch Task II Distribution"),
        (patch_df, "TaskIII", "02b_patch_taskiii_count_percent", "Patch Task III Distribution"),
        (origin_stats_df, "TaskIII", "02b_taskiii_origin_count_percent", "Origin Task III Distribution"),
        (patch_df, "TaskIII", "02b_taskiii_patch_count_percent", "Patch Task III Distribution"),
        (patch_df, "TaskIV", "02c_patch_taskiv_count_percent", "Patch Task IV Distribution"),
        (origin_stats_df, "TaskIV", "02c_taskiv_origin_count_percent", "Origin Task IV Distribution"),
        (patch_df, "TaskIV", "02c_taskiv_patch_count_percent", "Patch Task IV Distribution"),
    ]
    for df, column, stem, title in task_specs:
        level = "patch rows" if df is patch_df else "matched origins"
        manifest.extend(add_dataset_plotly_figure(
            gallery_rows,
            "Diagnosis And Source Tasks",
            stem,
            title,
            f"Counts and percentages for {display_column_name(column)} across {level}.",
            task_count_plot(df, column, title),
            str(patch_source if df is patch_df else origin_source),
        ))

    for level_name, df, source in [
        ("Origin", origin_stats_df, origin_source),
        ("Patch", patch_df, patch_source),
    ]:
        prefix = "origin" if level_name == "Origin" else "patch"
        for column in DATASET_FIELDS:
            stem = f"03_{prefix}_{column}_count_percent"
            if column == "age_group":
                stem = f"03_{prefix}_age_group_label_count_percent"
            title = f"{level_name} {FIELD_LABELS[column]} Distribution"
            manifest.extend(add_dataset_plotly_figure(
                gallery_rows,
                "Demographic, Clinical, And Missingness Summaries",
                stem,
                title,
                f"Counts and percentages for {FIELD_LABELS[column].lower()} at {level_name.lower()} level.",
                count_percent_plot(df, column, title),
                str(source),
            ))

    manifest.extend(add_dataset_plotly_figure(
        gallery_rows,
        "Demographic, Clinical, And Missingness Summaries",
        "04a_origin_missing_not_informed_rates",
        "Origin Missing And Not-Informed Rates",
        "Shows missing and `Not informed` percentages for origin-level metadata fields.",
        missingness_plot(origin_stats_df, "Origin Missing And Not-Informed Rates"),
        str(origin_source),
    ))
    manifest.extend(add_dataset_plotly_figure(
        gallery_rows,
        "Demographic, Clinical, And Missingness Summaries",
        "04b_patch_missing_not_informed_rates",
        "Patch Missing And Not-Informed Rates",
        "Shows missing and `Not informed` percentages for patch-level metadata fields.",
        missingness_plot(patch_df, "Patch Missing And Not-Informed Rates"),
        str(patch_source),
    ))

    age_specs = [
        (origin_stats_df, "05a_origin_age_group_count_percent", "Origin Age Group Distribution"),
        (patch_df, "05a_patch_age_group_count_percent", "Patch Age Group Distribution"),
        (origin_stats_df, "05b_origin_age_group_count_percent", "Origin Age Group Distribution For Diagnosis Review"),
        (patch_df, "05b_patch_age_group_count_percent", "Patch Age Group Distribution For Diagnosis Review"),
    ]
    for df, stem, title in age_specs:
        manifest.extend(add_dataset_plotly_figure(
            gallery_rows,
            "Age, Diagnosis, And Variable Associations",
            stem,
            title,
            "Age-group counts and percentages used as context for diagnosis association views.",
            count_percent_plot(df, "age_group", title),
            str(patch_source if df is patch_df else origin_source),
        ))

    diagnosis_age_specs = [
        (origin_stats_df, "06_diagnosis_by_age_group_row_percent", "Origin Diagnosis By Age Group: Row Percentages"),
        (patch_df, "06a_diagnosis_by_age_group_row_percent", "Patch Diagnosis By Age Group: Row Percentages"),
    ]
    for df, stem, title in diagnosis_age_specs:
        manifest.extend(add_dataset_plotly_figure(
            gallery_rows,
            "Age, Diagnosis, And Variable Associations",
            stem,
            title,
            "Each bar sums to 100 percent within one age group.",
            row_percent_plot(df, "age_group", title),
            str(patch_source if df is patch_df else origin_source),
        ))

    manifest.extend(add_dataset_plotly_figure(
        gallery_rows,
        "Age, Diagnosis, And Variable Associations",
        "06b_diagnosis_by_age_group_column_percent",
        "Diagnosis By Age Group: Column Percentages",
        "Each bar sums to 100 percent within one diagnosis.",
        column_percent_plot(origin_stats_df, "age_group", "Diagnosis By Age Group: Column Percentages"),
        str(origin_source),
    ))

    association_variables = [
        "alcohol_consumption",
        "gender",
        "localization",
        "skin_color",
        "sun_exposure",
        "tobacco_use",
    ]
    for level_name, df, source in [
        ("Origin", origin_stats_df, origin_source),
        ("Patch", patch_df, patch_source),
    ]:
        prefix = "origin" if level_name == "Origin" else "patch"
        for variable in association_variables:
            title = f"{level_name} Diagnosis By {FIELD_LABELS[variable]}"
            manifest.extend(add_dataset_plotly_figure(
                gallery_rows,
                "Age, Diagnosis, And Variable Associations",
                f"07_{prefix}_diagnosis_by_{variable}_row_percent",
                title,
                f"Each bar sums to 100 percent within one {FIELD_LABELS[variable].lower()} category.",
                row_percent_plot(df, variable, title),
                str(source),
            ))

    associations = pd.read_csv(association_source)
    associations["pair"] = associations["var_a"] + " x " + associations["var_b"]
    associations["pair_label"] = (
        associations["var_a"].map(display_column_name)
        + " x "
        + associations["var_b"].map(display_column_name)
    )
    associations["pair_wrapped"] = associations["pair_label"].map(lambda value: wrap_label(value, 34))
    associations = associations.sort_values("cramers_v", ascending=False)
    fig = px.bar(
        associations,
        x="cramers_v",
        y="pair_wrapped",
        orientation="h",
        title="Categorical Variable Association By Cramer's V",
        labels={"cramers_v": "Cramer's V", "pair_wrapped": "Variable pair"},
        color_discrete_sequence=[LABCIN_GOLD],
        height=950,
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(margin=dict(l=320, r=48, t=72, b=72))
    manifest.extend(add_dataset_plotly_figure(
        gallery_rows,
        "Age, Diagnosis, And Variable Associations",
        "08_categorical_association_cramers_v",
        "Categorical Variable Association By Cramer's V",
        "Full descriptive association list. Higher values indicate stronger categorical association, not causality.",
        fig,
        str(association_source),
    ))

    lesion_df = patch_df.copy()
    lesion_df["diagnosis"] = clean_category(lesion_df["diagnosis"], "diagnosis")
    fig = px.histogram(
        lesion_df,
        x="larger_size",
        nbins=30,
        title="Lesion Size Distribution",
        labels={"larger_size": "Larger size", "count": "Patch rows"},
        color_discrete_sequence=[LABCIN_BLUE],
    )
    manifest.extend(add_dataset_plotly_figure(
        gallery_rows,
        "Lesion Size",
        "09_larger_size_histogram_count_percent",
        "Lesion Size Distribution",
        "Histogram of the larger-size metadata field across patch rows.",
        fig,
        str(patch_source),
    ))

    fig = px.box(
        lesion_df.assign(
            diagnosis_wrapped=lesion_df["diagnosis"].map(lambda value: wrap_label(value, 30))
        ),
        x="larger_size",
        y="diagnosis_wrapped",
        color="diagnosis",
        points="outliers",
        title="Lesion Size By Diagnosis",
        labels={"diagnosis_wrapped": "Diagnosis", "larger_size": "Larger size"},
        color_discrete_sequence=LABCIN_SEQUENCE,
    )
    fig.update_layout(showlegend=False, height=520, margin=dict(l=280, r=48, t=72, b=72))
    manifest.extend(add_dataset_plotly_figure(
        gallery_rows,
        "Lesion Size",
        "10_lesion_size_by_diagnosis",
        "Lesion Size By Diagnosis",
        "Descriptive lesion-size spread by diagnosis. This is not a fold-selection rule.",
        fig,
        str(patch_source),
    ))

    write_dataset_figure_gallery(gallery_rows)
    write_exploratory_analysis(gallery_rows)
    return manifest


def fold_balance_table() -> pd.DataFrame:
    origin_path = PROJECT_ROOT / "results/phase3_fold_creation/fold_assignments_origin.csv"
    patch_path = PROJECT_ROOT / "results/phase3_fold_creation/fold_assignments_patch_level.csv"
    origin_df = pd.read_csv(origin_path)
    patch_df = pd.read_csv(patch_path)

    fold_summary = pd.DataFrame({
        "fold": sorted(origin_df["fold"].unique()),
    })
    origin_counts = origin_df["fold"].value_counts().sort_index()
    patch_counts = patch_df["fold"].value_counts().sort_index()
    fold_summary["origins"] = fold_summary["fold"].map(origin_counts).astype(int)
    fold_summary["origin_percent"] = (
        fold_summary["origins"] / len(origin_df) * 100
    ).round(2)
    fold_summary["patches"] = fold_summary["fold"].map(patch_counts).astype(int)
    fold_summary["patch_percent"] = (
        fold_summary["patches"] / len(patch_df) * 100
    ).round(2)
    return fold_summary


def generate_fold_balance() -> list[dict]:
    source = PROJECT_ROOT / "results/phase3_fold_creation/fold_assignments_patch_level.csv"
    summary = fold_balance_table()
    ensure_dir(DOCS_FIGURE_DIR)
    summary.to_csv(DOCS_FIGURE_DIR / "fold_balance_summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(8.8, 4.9))
    x = np.arange(len(summary))
    width = 0.36
    ax.bar(x - width / 2, summary["origin_percent"], width, label="Origins", color=LABCIN_BLUE)
    ax.bar(x + width / 2, summary["patch_percent"], width, label="Patches", color=LABCIN_GREEN)
    ax.set_title("Fold Share Of Origins And Patches")
    ax.set_xlabel("Fold")
    ax.set_ylabel("Share of total (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(summary["fold"].astype(str))
    ax.legend()
    manifest = save_matplotlib_figure(
        fig,
        "fold_origin_patch_percent",
        "Fold origin and patch percentages",
        str(source),
    )

    long_summary = summary.melt(
        id_vars="fold",
        value_vars=["origin_percent", "patch_percent"],
        var_name="metric",
        value_name="percent",
    )
    plotly_fig = px.bar(
        long_summary,
        x="fold",
        y="percent",
        color="metric",
        barmode="group",
        title="Fold Share Of Origins And Patches",
        labels={"fold": "Fold", "percent": "Share of total (%)", "metric": "Metric"},
        color_discrete_sequence=[LABCIN_BLUE, LABCIN_GREEN],
    )
    manifest.extend(
        save_plotly_figure(
            plotly_fig,
            "fold_origin_patch_percent",
            "Fold origin and patch percentages",
            str(source),
        )
    )
    return manifest


def generate_fold_diagnosis_percent() -> list[dict]:
    source = PROJECT_ROOT / "results/phase3_fold_creation/fold_assignments_patch_level.csv"
    patch_df = pd.read_csv(source)
    counts = pd.crosstab(patch_df["fold"], patch_df["diagnosis"])
    percents = counts.div(counts.sum(axis=1), axis=0) * 100
    ensure_dir(DOCS_FIGURE_DIR)
    percents.round(2).to_csv(DOCS_FIGURE_DIR / "fold_diagnosis_percent.csv")

    fig, ax = plt.subplots(figsize=(9, 5.2))
    bottom = np.zeros(len(percents))
    for index, column in enumerate(percents.columns):
        values = percents[column].to_numpy()
        ax.bar(
            percents.index.astype(str),
            values,
            bottom=bottom,
            label=column,
            color=LABCIN_SEQUENCE[index],
        )
        bottom += values
    ax.set_title("Patch Diagnosis Share Within Each Fold")
    ax.set_xlabel("Fold")
    ax.set_ylabel("Patch share within fold (%)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    manifest = save_matplotlib_figure(
        fig,
        "fold_diagnosis_percent",
        "Fold diagnosis percentages",
        str(source),
    )

    long_df = percents.reset_index().melt(
        id_vars="fold",
        var_name="diagnosis",
        value_name="percent",
    )
    plotly_fig = px.bar(
        long_df,
        x="fold",
        y="percent",
        color="diagnosis",
        title="Patch Diagnosis Share Within Each Fold",
        labels={"fold": "Fold", "percent": "Patch share within fold (%)"},
        color_discrete_sequence=LABCIN_SEQUENCE,
    )
    manifest.extend(
        save_plotly_figure(
            plotly_fig,
            "fold_diagnosis_percent",
            "Fold diagnosis percentages",
            str(source),
        )
    )
    return manifest


def fold_variable_long_frame(df: pd.DataFrame, variable: str) -> pd.DataFrame:
    data = pd.DataFrame({
        "fold": df["fold"].astype(int),
        "category": clean_category(df[variable], variable),
    })
    counts = pd.crosstab(data["fold"], data["category"])
    percents = counts.div(counts.sum(axis=1), axis=0) * 100
    long_df = percents.reset_index().melt(
        id_vars="fold",
        var_name="category",
        value_name="percent",
    )
    count_long = counts.reset_index().melt(
        id_vars="fold",
        var_name="category",
        value_name="count",
    )
    long_df = long_df.merge(count_long, on=["fold", "category"], how="left")
    long_df["label"] = (
        long_df["count"].astype(int).astype(str)
        + " ("
        + long_df["percent"].round(1).astype(str)
        + "%)"
    )
    return long_df


def save_fold_variable_matplotlib(
    long_df: pd.DataFrame,
    stem: str,
    title: str,
    source: str,
) -> list[dict]:
    pivot = long_df.pivot(index="fold", columns="category", values="percent").fillna(0)
    fig, ax = plt.subplots(figsize=(9, 5.2))
    bottom = np.zeros(len(pivot))
    for index, column in enumerate(pivot.columns):
        values = pivot[column].to_numpy()
        ax.bar(
            pivot.index.astype(str),
            values,
            bottom=bottom,
            label=str(column),
            color=LABCIN_SEQUENCE[index % len(LABCIN_SEQUENCE)],
        )
        bottom += values
    ax.set_title(title)
    ax.set_xlabel("Fold")
    ax.set_ylabel("Origin share within fold (%)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    return save_matplotlib_figure(fig, stem, title, source)


def generate_fold_stratification_figures() -> list[dict]:
    source = PROJECT_ROOT / "results/phase3_fold_creation/fold_assignments_origin.csv"
    origin_df = pd.read_csv(source)
    manifest: list[dict] = []

    variable_specs = [
        ("origin_diagnosis", "fold_origin_diagnosis_percent", "Origin Diagnosis Share Within Each Fold"),
        ("morph_cluster", "fold_morph_cluster_percent", "Morphology Cluster Share Within Each Fold"),
        ("gender", "fold_gender_percent", "Gender Share Within Each Fold"),
        ("age_group", "fold_age_group_percent", "Age Group Share Within Each Fold"),
    ]
    for variable, stem, title in variable_specs:
        long_df = fold_variable_long_frame(origin_df, variable)
        long_df.to_csv(ensure_dir(DOCS_FIGURE_DIR) / f"{stem}.csv", index=False)
        manifest.extend(save_fold_variable_matplotlib(long_df, stem, title, str(source)))
        plotly_fig = px.bar(
            long_df,
            x="fold",
            y="percent",
            color="category",
            text="label",
            title=title,
            labels={
                "fold": "Fold",
                "percent": "Origin share within fold (%)",
                "category": FIELD_LABELS.get(variable, variable),
            },
            color_discrete_sequence=LABCIN_SEQUENCE,
        )
        plotly_fig.update_traces(textposition="inside", insidetextanchor="middle")
        manifest.extend(save_plotly_figure(plotly_fig, stem, title, str(source)))

    counts = pd.crosstab(origin_df["stratification_key"], origin_df["fold"])
    spread = counts.max(axis=1) - counts.min(axis=1)
    spread_summary = (
        spread.value_counts()
        .sort_index()
        .rename_axis("fold_count_range")
        .reset_index(name="strata")
    )
    spread_summary.to_csv(
        ensure_dir(DOCS_FIGURE_DIR) / "fold_combined_stratum_spread.csv",
        index=False,
    )

    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.bar(
        spread_summary["fold_count_range"].astype(str),
        spread_summary["strata"],
        color=LABCIN_GREEN,
    )
    ax.set_title("Combined Stratum Spread Across Folds")
    ax.set_xlabel("Maximum minus minimum origin count across folds")
    ax.set_ylabel("Number of combined strata")
    manifest.extend(save_matplotlib_figure(
        fig,
        "fold_combined_stratum_spread",
        "Combined stratum spread across folds",
        str(source),
    ))

    plotly_fig = px.bar(
        spread_summary,
        x="fold_count_range",
        y="strata",
        text="strata",
        title="Combined Stratum Spread Across Folds",
        labels={
            "fold_count_range": "Max-min origin count across folds",
            "strata": "Combined strata",
        },
        color_discrete_sequence=[LABCIN_GREEN],
    )
    plotly_fig.update_traces(textposition="outside", cliponaxis=False)
    manifest.extend(save_plotly_figure(
        plotly_fig,
        "fold_combined_stratum_spread",
        "Combined stratum spread across folds",
        str(source),
    ))
    return manifest


def overlap_for_shift(
    dx: int,
    dy: int,
    width: int,
    height: int,
) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]] | None:
    a_x0 = max(0, dx)
    a_x1 = min(width, width + dx)
    a_y0 = max(0, dy)
    a_y1 = min(height, height + dy)
    b_x0 = max(0, -dx)
    b_x1 = min(width, width - dx)
    b_y0 = max(0, -dy)
    b_y1 = min(height, height - dy)
    if a_x1 <= a_x0 or a_y1 <= a_y0:
        return None
    return (a_x0, a_y0, a_x1, a_y1), (b_x0, b_y0, b_x1, b_y1)


def normalized_overlap_score(
    image_a: np.ndarray,
    image_b: np.ndarray,
    dx: int,
    dy: int,
    minimum_side: int = 64,
) -> tuple[float, tuple[int, int, int, int], tuple[int, int, int, int]] | None:
    height, width = image_a.shape
    overlap = overlap_for_shift(dx, dy, width, height)
    if overlap is None:
        return None

    rect_a, rect_b = overlap
    ax0, ay0, ax1, ay1 = rect_a
    bx0, by0, bx1, by1 = rect_b
    if ax1 - ax0 < minimum_side or ay1 - ay0 < minimum_side:
        return None

    region_a = image_a[ay0:ay1, ax0:ax1]
    region_b = image_b[by0:by1, bx0:bx1]
    region_a = (region_a - region_a.mean()) / (region_a.std() + 1e-6)
    region_b = (region_b - region_b.mean()) / (region_b.std() + 1e-6)
    return float((region_a * region_b).mean()), rect_a, rect_b


def estimate_translation_overlap(
    image_a: np.ndarray,
    image_b: np.ndarray,
) -> tuple[int, int, float, tuple[int, int, int, int], tuple[int, int, int, int]]:
    shift, _ = cv.phaseCorrelate(image_a.astype(np.float32), image_b.astype(np.float32))
    seed_dx = int(round(-shift[0]))
    seed_dy = int(round(-shift[1]))

    best = (-np.inf, seed_dx, seed_dy, None, None)
    for dy in range(seed_dy - 16, seed_dy + 17):
        for dx in range(seed_dx - 16, seed_dx + 17):
            score = normalized_overlap_score(image_a, image_b, dx, dy)
            if score and score[0] > best[0]:
                best = (score[0], dx, dy, score[1], score[2])

    if best[3] is None:
        raise ValueError("Could not estimate a rectangular patch overlap")

    score, dx, dy, rect_a, rect_b = best
    return dx, dy, score, rect_a, rect_b


def highlighted_grayscale_patch(
    image: np.ndarray,
    rect: tuple[int, int, int, int],
    color_rgb: tuple[int, int, int],
) -> np.ndarray:
    gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
    rgb = cv.cvtColor(gray, cv.COLOR_GRAY2RGB)
    x0, y0, x1, y1 = rect
    overlay = rgb.copy()
    overlay[y0:y1, x0:x1] = (
        0.45 * overlay[y0:y1, x0:x1]
        + 0.55 * np.array(color_rgb, dtype=np.float32)
    ).astype(np.uint8)
    cv.rectangle(overlay, (x0, y0), (x1 - 1, y1 - 1), color_rgb, thickness=4)
    return overlay


def generate_contamination_overlap_bbox() -> list[dict]:
    source_a = PROJECT_ROOT / "data/ndb_ufes/patch_level/images/p0020.png"
    source_b = PROJECT_ROOT / "data/ndb_ufes/patch_level/images/p0021.png"
    image_a = cv.imread(str(source_a), cv.IMREAD_COLOR)
    image_b = cv.imread(str(source_b), cv.IMREAD_COLOR)
    if image_a is None or image_b is None:
        raise FileNotFoundError(f"Could not read {source_a} or {source_b}")

    gray_a = cv.cvtColor(image_a, cv.COLOR_BGR2GRAY).astype(np.float32)
    gray_b = cv.cvtColor(image_b, cv.COLOR_BGR2GRAY).astype(np.float32)
    dx, dy, score, rect_a, rect_b = estimate_translation_overlap(gray_a, gray_b)
    width = rect_a[2] - rect_a[0]
    height = rect_a[3] - rect_a[1]

    ensure_dir(DOCS_CONTAMINATION_DIR)
    ensure_dir(THESIS_FIGURE_DIR)

    highlight = tuple(int(LABCIN_LIGHT_GREEN.lstrip("#")[index:index + 2], 16) for index in (0, 2, 4))
    patch_a = highlighted_grayscale_patch(image_a, rect_a, highlight)
    patch_b = highlighted_grayscale_patch(image_b, rect_b, highlight)

    fig, axes = plt.subplots(1, 2, figsize=(10, 5.4))
    axes[0].imshow(patch_a)
    axes[0].set_title("p0020")
    axes[0].axis("off")
    axes[1].imshow(patch_b)
    axes[1].set_title("p0021")
    axes[1].axis("off")
    fig.suptitle(
        "Origin 0011 Shared Patch Region\n"
        f"{width} x {height} px rectangle. Translation ({dx}, {dy}). NCC {score:.3f}",
        y=0.98,
    )
    manifest = save_matplotlib_figure(
        fig,
        "origin_0011_overlap_bbox",
        "Origin 0011 overlap bounding boxes",
        f"{source_a}; {source_b}",
        docs_dir=DOCS_CONTAMINATION_DIR,
    )

    diagnostics = pd.DataFrame([{
        "origin_id": "0011",
        "patch_a": "p0020",
        "patch_b": "p0021",
        "algorithm": "translation-only image registration with normalized cross-correlation over the overlap",
        "translation_dx": dx,
        "translation_dy": dy,
        "patch_a_rect_x0": rect_a[0],
        "patch_a_rect_y0": rect_a[1],
        "patch_a_rect_x1": rect_a[2],
        "patch_a_rect_y1": rect_a[3],
        "patch_b_rect_x0": rect_b[0],
        "patch_b_rect_y0": rect_b[1],
        "patch_b_rect_x1": rect_b[2],
        "patch_b_rect_y1": rect_b[3],
        "overlap_width_px": width,
        "overlap_height_px": height,
        "normalized_cross_correlation": round(score, 6),
    }])
    diagnostics.to_csv(DOCS_CONTAMINATION_DIR / "origin_0011_overlap_bbox.csv", index=False)
    return manifest


def write_manifest(rows: list[dict]) -> None:
    manifest = pd.DataFrame(rows)
    ensure_dir(DOCS_FIGURE_DIR)
    ensure_dir(THESIS_FIGURE_DIR)
    manifest.to_csv(DOCS_FIGURE_DIR / "figure_manifest.csv", index=False)
    manifest.to_csv(THESIS_FIGURE_DIR / "figure_manifest.csv", index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate MkDocs and thesis figures from current pipeline outputs."
    )
    parser.add_argument(
        "--skip-plotly-previews",
        action="store_true",
        help="Use existing legacy preview PNGs instead of exporting Plotly PNG previews.",
    )
    parser.add_argument(
        "--export-plotly-thesis",
        action="store_true",
        help="Also export Plotly PNG, SVG, and PDF copies under results/thesis_figures/plotly/.",
    )
    return parser.parse_args()


def main() -> None:
    global EXPORT_PLOTLY_PREVIEWS, EXPORT_PLOTLY_THESIS
    args = parse_args()
    EXPORT_PLOTLY_PREVIEWS = not args.skip_plotly_previews
    EXPORT_PLOTLY_THESIS = args.export_plotly_thesis

    configure_matplotlib()
    configure_plotly()
    manifest_rows = []
    manifest_rows.extend(generate_dataset_diagnosis_summary())
    manifest_rows.extend(generate_source_task_counts())
    manifest_rows.extend(generate_top_cramers_v())
    manifest_rows.extend(generate_dataset_statistics_gallery())
    manifest_rows.extend(generate_phase2_selection())
    manifest_rows.extend(generate_phase2_tuning_diagnostics())
    manifest_rows.extend(generate_fold_balance())
    manifest_rows.extend(generate_fold_diagnosis_percent())
    manifest_rows.extend(generate_fold_stratification_figures())
    manifest_rows.extend(generate_contamination_overlap_bbox())
    write_manifest(manifest_rows)
    print(f"Generated {len(manifest_rows)} figure artifacts")


if __name__ == "__main__":
    main()
