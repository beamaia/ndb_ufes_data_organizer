import argparse
import json
import math
from pathlib import Path

import cv2 as cv
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from src.phase0.patch_similarity import off_diagonal_values, similarity_stats
from src.phase0.recovery_validation import DEFAULT_ACCEPTED_METADATA, DEFAULT_RAW_PATCH_DIR, accepted_patch_table, patch_number


DEFAULT_OUTPUT_DIR = Path("results/phase0/patch_coherence_report")
DEFAULT_SIMILARITY_TABLE = Path("results/phase0/similarity/intra_origin_similarity.csv")


def patch_image_path(raw_patch_dir: Path, patch_id: str) -> Path:
    return Path(raw_patch_dir) / f"{patch_id}.png"


def read_patch_rgb(path: Path) -> np.ndarray:
    image = cv.imread(str(path), cv.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read patch image: {path}")
    return cv.cvtColor(image, cv.COLOR_BGR2RGB)


def patch_fingerprint(path: Path, thumbnail_size: int) -> np.ndarray:
    image = cv.imread(str(path), cv.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"Could not read patch image: {path}")
    resized = cv.resize(image, (thumbnail_size, thumbnail_size), interpolation=cv.INTER_AREA)
    vector = resized.astype(np.float64).reshape(-1)
    vector -= float(vector.mean())
    norm = float(np.linalg.norm(vector))
    if norm == 0:
        return np.zeros_like(vector)
    return vector / norm


def cosine_matrix(vectors: np.ndarray) -> np.ndarray:
    if vectors.shape[0] == 0:
        return np.empty((0, 0), dtype=float)
    matrix = np.einsum("ik,jk->ij", vectors, vectors, optimize=False)
    return np.clip(matrix, -1.0, 1.0)


def origin_pixel_similarity(origin_rows: pd.DataFrame, raw_patch_dir: Path, thumbnail_size: int) -> tuple[np.ndarray, list[str]]:
    ordered = origin_rows.copy()
    ordered["patch_number"] = ordered["patch"].map(patch_number)
    ordered = ordered.sort_values("patch_number")
    patch_ids = ordered["patch"].tolist()
    vectors = np.vstack([patch_fingerprint(patch_image_path(raw_patch_dir, patch), thumbnail_size) for patch in patch_ids])
    return cosine_matrix(vectors), patch_ids


def representative_pairs(matrix: np.ndarray, patch_ids: list[str]) -> dict:
    if matrix.shape[0] < 2:
        return {
            "most_similar_patch_a": "",
            "most_similar_patch_b": "",
            "most_similar_score": np.nan,
            "least_similar_patch_a": "",
            "least_similar_patch_b": "",
            "least_similar_score": np.nan,
        }
    upper_i, upper_j = np.triu_indices(matrix.shape[0], k=1)
    values = matrix[upper_i, upper_j]
    max_index = int(np.argmax(values))
    min_index = int(np.argmin(values))
    return {
        "most_similar_patch_a": patch_ids[int(upper_i[max_index])],
        "most_similar_patch_b": patch_ids[int(upper_j[max_index])],
        "most_similar_score": float(values[max_index]),
        "least_similar_patch_a": patch_ids[int(upper_i[min_index])],
        "least_similar_patch_b": patch_ids[int(upper_j[min_index])],
        "least_similar_score": float(values[min_index]),
    }


def build_origin_coherence_tables(
    metadata: pd.DataFrame,
    raw_patch_dir: Path,
    thumbnail_size: int,
) -> tuple[pd.DataFrame, dict[int, dict]]:
    rows = []
    matrices = {}
    for origin_id, group in metadata.groupby("origin"):
        matrix, patch_ids = origin_pixel_similarity(group, raw_patch_dir, thumbnail_size)
        values = off_diagonal_values(matrix)
        diagnosis_counts = group["diagnosis"].value_counts(dropna=False).to_dict()
        class_count = int(group["diagnosis"].nunique(dropna=False))
        row = {
            "origin_id": int(origin_id),
            "origin_id_padded": f"{int(origin_id):04d}",
            "n_patches": int(len(group)),
            "n_patch_classes": class_count,
            "diagnosis_counts": json.dumps(diagnosis_counts, sort_keys=True),
            "has_multiple_patch_classes": bool(class_count > 1),
            **similarity_stats(values),
            **representative_pairs(matrix, patch_ids),
        }
        rows.append(row)
        matrices[int(origin_id)] = {"matrix": matrix, "patch_ids": patch_ids}
    table = pd.DataFrame(rows).sort_values(["mean_cosine_similarity", "n_patches"], ascending=[True, False])
    return table, matrices


def load_embedding_similarity(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    table = pd.read_csv(path)
    if "origin_id" in table.columns:
        table["origin_id"] = table["origin_id"].astype(int)
    return table


def draw_header(fig, title: str, subtitle: str = "") -> None:
    fig.text(0.04, 0.965, title, fontsize=16, fontweight="bold", va="top")
    if subtitle:
        fig.text(0.04, 0.938, subtitle, fontsize=9, color="#444444", va="top")


def text_block(fig, lines: list[str], x: float = 0.04, y: float = 0.90, size: int = 9) -> None:
    for index, line in enumerate(lines):
        fig.text(x, y - index * 0.022, line, fontsize=size, va="top")


def add_summary_page(pdf: PdfPages, metadata: pd.DataFrame, coherence: pd.DataFrame, embedding: pd.DataFrame) -> None:
    fig = plt.figure(figsize=(11, 8.5))
    draw_header(fig, "Patch Coherence Validation Report", "Candidate evidence for origin-level patch consistency. Source data are not modified.")
    class_counts = metadata["diagnosis"].value_counts(dropna=False)
    origin_counts = metadata.groupby("origin").size()
    lines = [
        f"Accepted patches: {len(metadata)}",
        f"Origins with accepted patches: {metadata['origin'].nunique()}",
        f"Median patches per origin: {origin_counts.median():.1f}",
        f"Max patches in one origin: {origin_counts.max()}",
        f"Origins with more than one patch diagnosis: {int(coherence['has_multiple_patch_classes'].sum())}",
        f"Mean within-origin pixel similarity: {coherence['mean_cosine_similarity'].mean():.3f}",
        f"Median within-origin pixel similarity: {coherence['median_cosine_similarity'].median():.3f}",
    ]
    if not embedding.empty:
        lines.extend([
            f"Mean within-origin embedding similarity: {embedding['mean_cosine_similarity'].mean():.3f}",
            f"Median within-origin embedding similarity: {embedding['median_cosine_similarity'].median():.3f}",
        ])
    lines.append("")
    lines.append("Class counts:")
    lines.extend([f"- {label}: {count}" for label, count in class_counts.items()])
    lines.append("")
    lines.append("Interpretation note:")
    lines.append("High similarity suggests redundant/shared visual structure; low similarity suggests origin heterogeneity.")
    lines.append("This report is evidence for review, not an automatic inclusion/exclusion rule.")
    text_block(fig, lines)

    ax = fig.add_axes([0.08, 0.08, 0.84, 0.28])
    ax.hist(coherence["mean_cosine_similarity"].dropna(), bins=25, color="#4C78A8", edgecolor="white")
    ax.set_title("Distribution of mean within-origin pixel similarity")
    ax.set_xlabel("Mean cosine similarity from downsampled grayscale patch fingerprints")
    ax.set_ylabel("Origins")
    ax.grid(axis="y", alpha=0.25)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def origin_metadata_lines(group: pd.DataFrame, coherence_row: pd.Series, embedding_row: pd.Series | None) -> list[str]:
    diagnoses = group["diagnosis"].value_counts(dropna=False).to_dict()
    lines = [
        f"Origin: {int(coherence_row['origin_id']):04d}",
        f"Patches: {int(coherence_row['n_patches'])}",
        f"Patch diagnosis counts: {diagnoses}",
        f"Pixel similarity mean/median/min: {coherence_row['mean_cosine_similarity']:.3f} / {coherence_row['median_cosine_similarity']:.3f} / {coherence_row['min_cosine_similarity']:.3f}",
        f"Most similar pair: {coherence_row['most_similar_patch_a']} - {coherence_row['most_similar_patch_b']} ({coherence_row['most_similar_score']:.3f})",
        f"Least similar pair: {coherence_row['least_similar_patch_a']} - {coherence_row['least_similar_patch_b']} ({coherence_row['least_similar_score']:.3f})",
    ]
    if embedding_row is not None:
        lines.append(
            "Embedding similarity mean/median/min: "
            f"{embedding_row['mean_cosine_similarity']:.3f} / "
            f"{embedding_row['median_cosine_similarity']:.3f} / "
            f"{embedding_row['min_cosine_similarity']:.3f}"
        )
    for column in ["patient_id", "lesion_id", "localization", "gender", "age_group", "dysplasia_severity"]:
        if column in group.columns:
            values = sorted(set(str(value) for value in group[column].dropna().tolist()))
            if values:
                lines.append(f"{column}: {', '.join(values[:6])}")
    return lines


def add_origin_overview_page(
    pdf: PdfPages,
    origin_id: int,
    group: pd.DataFrame,
    coherence_row: pd.Series,
    matrix: np.ndarray,
    patch_ids: list[str],
    raw_patch_dir: Path,
    embedding_row: pd.Series | None,
) -> None:
    fig = plt.figure(figsize=(11, 8.5))
    draw_header(fig, f"Origin {origin_id:04d} - Coherence Overview", "Within-origin similarity and representative patch pairs")
    text_block(fig, origin_metadata_lines(group, coherence_row, embedding_row), y=0.90)

    ax = fig.add_axes([0.58, 0.48, 0.34, 0.36])
    if matrix.shape[0] > 1:
        shown = matrix if matrix.shape[0] <= 80 else matrix[:80, :80]
        image = ax.imshow(shown, vmin=-1, vmax=1, cmap="viridis")
        ax.set_title("Patch similarity matrix" + (" (first 80)" if matrix.shape[0] > 80 else ""))
        ax.set_xlabel("patch index")
        ax.set_ylabel("patch index")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    else:
        ax.text(0.5, 0.5, "single patch", ha="center", va="center")
        ax.axis("off")

    pairs = [
        ("most similar A", coherence_row["most_similar_patch_a"]),
        ("most similar B", coherence_row["most_similar_patch_b"]),
        ("least similar A", coherence_row["least_similar_patch_a"]),
        ("least similar B", coherence_row["least_similar_patch_b"]),
    ]
    for index, (label, patch_id) in enumerate(pairs):
        ax_patch = fig.add_axes([0.06 + index * 0.23, 0.08, 0.18, 0.24])
        if isinstance(patch_id, str) and patch_id:
            ax_patch.imshow(read_patch_rgb(patch_image_path(raw_patch_dir, patch_id)))
            ax_patch.set_title(f"{label}\n{patch_id}", fontsize=8)
        else:
            ax_patch.text(0.5, 0.5, "n/a", ha="center", va="center")
        ax_patch.axis("off")

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_patch_contact_pages(
    pdf: PdfPages,
    origin_id: int,
    group: pd.DataFrame,
    raw_patch_dir: Path,
    patches_per_page: int,
) -> int:
    ordered = group.copy()
    ordered["patch_number"] = ordered["patch"].map(patch_number)
    ordered = ordered.sort_values("patch_number").reset_index(drop=True)
    pages = 0
    for start in range(0, len(ordered), patches_per_page):
        pages += 1
        chunk = ordered.iloc[start:start + patches_per_page]
        columns = 5
        rows = math.ceil(len(chunk) / columns)
        fig = plt.figure(figsize=(11, 8.5))
        draw_header(fig, f"Origin {origin_id:04d} - Patch Contact Sheet", f"Patches {start + 1}-{start + len(chunk)} of {len(ordered)}")
        for offset, row in enumerate(chunk.itertuples(index=False)):
            grid_row = offset // columns
            grid_col = offset % columns
            ax = fig.add_axes([
                0.04 + grid_col * 0.19,
                0.74 - grid_row * 0.22,
                0.16,
                0.16,
            ])
            ax.imshow(read_patch_rgb(patch_image_path(raw_patch_dir, row.patch)))
            ax.set_title(f"{row.patch} | {getattr(row, 'diagnosis', '')}", fontsize=7)
            ax.axis("off")
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)
    return pages


def write_patch_coherence_pdf(
    metadata: pd.DataFrame,
    coherence: pd.DataFrame,
    matrices: dict[int, dict],
    embedding: pd.DataFrame,
    raw_patch_dir: Path,
    output_pdf: Path,
    patches_per_page: int,
    max_origins: int | None,
) -> dict:
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    origin_ids = coherence["origin_id"].astype(int).tolist()
    if max_origins:
        origin_ids = origin_ids[:max_origins]
    pages = 0
    with PdfPages(output_pdf) as pdf:
        add_summary_page(pdf, metadata, coherence, embedding)
        pages += 1
        for origin_id in origin_ids:
            group = metadata[metadata["origin"].astype(int) == origin_id]
            row = coherence[coherence["origin_id"].astype(int) == origin_id].iloc[0]
            embedding_row = None
            if not embedding.empty and origin_id in set(embedding["origin_id"].astype(int)):
                embedding_row = embedding[embedding["origin_id"].astype(int) == origin_id].iloc[0]
            add_origin_overview_page(
                pdf,
                origin_id,
                group,
                row,
                matrices[origin_id]["matrix"],
                matrices[origin_id]["patch_ids"],
                raw_patch_dir,
                embedding_row,
            )
            pages += 1
            pages += add_patch_contact_pages(pdf, origin_id, group, raw_patch_dir, patches_per_page)
    return {"pdf_pages": pages, "origins_in_pdf": len(origin_ids)}


def run_patch_coherence_report(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = accepted_patch_table(args.accepted_metadata)
    metadata["origin"] = metadata["origin"].astype(int)
    coherence, matrices = build_origin_coherence_tables(metadata, args.raw_patch_dir, args.thumbnail_size)
    embedding = load_embedding_similarity(args.embedding_similarity)

    coherence.to_csv(output_dir / "origin_patch_pixel_similarity.csv", index=False)
    pdf_summary = {"pdf_written": False}
    output_pdf = None
    if args.write_pdf:
        output_pdf = output_dir / args.output_pdf
        max_origins = args.max_origins if args.max_origins > 0 else 10
        pdf_summary = {
            "pdf_written": True,
            **write_patch_coherence_pdf(
                metadata,
                coherence,
                matrices,
                embedding,
                args.raw_patch_dir,
                output_pdf,
                args.patches_per_page,
                max_origins,
            ),
        }
    summary = {
        "accepted_patches": int(len(metadata)),
        "origins": int(metadata["origin"].nunique()),
        "thumbnail_size": int(args.thumbnail_size),
        "output_pdf": str(output_pdf) if output_pdf else None,
        "coherence_table": str(output_dir / "origin_patch_pixel_similarity.csv"),
        **pdf_summary,
    }
    (output_dir / "patch_coherence_report_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def patch_coherence_report_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate compact patch coherence tables and optional representative PDF pages.")
    parser.add_argument("--accepted-metadata", type=Path, default=DEFAULT_ACCEPTED_METADATA)
    parser.add_argument("--raw-patch-dir", type=Path, default=DEFAULT_RAW_PATCH_DIR)
    parser.add_argument("--embedding-similarity", type=Path, default=DEFAULT_SIMILARITY_TABLE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-pdf", default="patch_coherence_validation_report.pdf")
    parser.add_argument("--write-pdf", action="store_true", help="Write a small representative PDF. Disabled by default.")
    parser.add_argument("--thumbnail-size", type=int, default=48)
    parser.add_argument("--patches-per-page", type=int, default=20)
    parser.add_argument("--max-origins", type=int, default=10)
    return parser
