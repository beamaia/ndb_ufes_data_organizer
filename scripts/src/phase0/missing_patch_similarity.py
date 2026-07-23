import argparse
import json
from pathlib import Path

import cv2 as cv
import numpy as np
import pandas as pd

from src.phase0.review_packets import DEFAULT_REVIEW_OUTPUT_DIR, make_contact_sheet


DEFAULT_REVIEW_QUEUE = DEFAULT_REVIEW_OUTPUT_DIR / "missing_patch_review_queue.csv"
DEFAULT_OUTPUT_DIR = DEFAULT_REVIEW_OUTPUT_DIR / "similar_patch_groups"


def normalized_patch_fingerprint(image_path: Path, thumbnail_size: int = 64) -> np.ndarray:
    image = cv.imread(str(image_path), cv.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")
    resized = cv.resize(image, (thumbnail_size, thumbnail_size), interpolation=cv.INTER_AREA)
    vector = resized.astype(np.float32).reshape(-1)
    vector -= float(vector.mean())
    norm = float(np.linalg.norm(vector))
    if norm == 0:
        return np.zeros_like(vector)
    return vector / norm


def build_fingerprint_matrix(queue: pd.DataFrame, thumbnail_size: int = 64) -> np.ndarray:
    vectors = [
        normalized_patch_fingerprint(Path(row.raw_patch_path), thumbnail_size=thumbnail_size)
        for row in queue.itertuples(index=False)
    ]
    if not vectors:
        return np.empty((0, thumbnail_size * thumbnail_size), dtype=np.float32)
    return np.vstack(vectors).astype(np.float32)


def pairwise_similarity_matrix(fingerprints: np.ndarray) -> np.ndarray:
    if fingerprints.size == 0:
        return np.empty((0, 0), dtype=np.float32)
    stable = np.nan_to_num(fingerprints.astype(np.float64), nan=0.0, posinf=0.0, neginf=0.0)
    similarities = np.einsum("ik,jk->ij", stable, stable, optimize=False)
    return np.clip(similarities, -1.0, 1.0).astype(np.float32)


def top_similarity_pairs(queue: pd.DataFrame, similarities: np.ndarray, top_k: int = 5) -> pd.DataFrame:
    rows = []
    n_items = len(queue)
    patches = queue["patch"].tolist()
    patch_numbers = queue["patch_number"].tolist()
    folder_labels = queue.get("folder_label", pd.Series([""] * n_items)).tolist()
    for i in range(n_items):
        order = np.argsort(similarities[i])[::-1]
        emitted = 0
        for j in order:
            if i == j:
                continue
            rows.append({
                "patch": patches[i],
                "patch_number": int(patch_numbers[i]),
                "neighbor_patch": patches[j],
                "neighbor_patch_number": int(patch_numbers[j]),
                "similarity": float(similarities[i, j]),
                "same_folder_label": bool(folder_labels[i] == folder_labels[j]),
                "folder_label": folder_labels[i],
                "neighbor_folder_label": folder_labels[j],
            })
            emitted += 1
            if emitted >= top_k:
                break
    return pd.DataFrame(rows).sort_values(["patch_number", "similarity"], ascending=[True, False])


def connected_components_from_threshold(similarities: np.ndarray, threshold: float) -> list[list[int]]:
    n_items = similarities.shape[0]
    parent = list(range(n_items))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(a: int, b: int) -> None:
        root_a = find(a)
        root_b = find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    for i in range(n_items):
        for j in range(i + 1, n_items):
            if similarities[i, j] >= threshold:
                union(i, j)

    components = {}
    for index in range(n_items):
        root = find(index)
        components.setdefault(root, []).append(index)
    return list(components.values())


def assign_similarity_groups(
    queue: pd.DataFrame,
    similarities: np.ndarray,
    threshold: float = 0.92,
    min_group_size: int = 2,
) -> pd.DataFrame:
    grouped = queue.copy().reset_index(drop=True)
    grouped["similarity_group_id"] = ""
    grouped["similarity_group_size"] = 1
    grouped["similarity_group_representative_patch"] = ""
    grouped["max_similarity_to_group_representative"] = np.nan

    components = connected_components_from_threshold(similarities, threshold)
    eligible = [component for component in components if len(component) >= min_group_size]
    eligible.sort(key=lambda component: (-len(component), int(grouped.iloc[min(component)]["patch_number"])))

    for group_index, component in enumerate(eligible, start=1):
        component_table = grouped.iloc[component].sort_values("patch_number")
        representative_index = int(component_table.index[0])
        representative_patch = str(grouped.loc[representative_index, "patch"])
        group_id = f"G{group_index:04d}"
        for member_index in component:
            grouped.loc[member_index, "similarity_group_id"] = group_id
            grouped.loc[member_index, "similarity_group_size"] = len(component)
            grouped.loc[member_index, "similarity_group_representative_patch"] = representative_patch
            grouped.loc[member_index, "max_similarity_to_group_representative"] = float(
                similarities[member_index, representative_index]
            )

    return grouped.sort_values(["patch_number"]).reset_index(drop=True)


def high_similarity_edges(queue: pd.DataFrame, similarities: np.ndarray, threshold: float) -> pd.DataFrame:
    rows = []
    for i in range(len(queue)):
        for j in range(i + 1, len(queue)):
            if similarities[i, j] >= threshold:
                row_i = queue.iloc[i]
                row_j = queue.iloc[j]
                rows.append({
                    "patch_a": row_i["patch"],
                    "patch_a_number": int(row_i["patch_number"]),
                    "patch_b": row_j["patch"],
                    "patch_b_number": int(row_j["patch_number"]),
                    "similarity": float(similarities[i, j]),
                    "same_folder_label": bool(row_i.get("folder_label", "") == row_j.get("folder_label", "")),
                    "folder_label_a": row_i.get("folder_label", ""),
                    "folder_label_b": row_j.get("folder_label", ""),
                })
    return pd.DataFrame(rows).sort_values("similarity", ascending=False) if rows else pd.DataFrame(rows)


def group_summary(grouped_queue: pd.DataFrame) -> pd.DataFrame:
    rows = []
    groups = grouped_queue[grouped_queue["similarity_group_id"] != ""]
    for group_id, group in groups.groupby("similarity_group_id", sort=False):
        folder_counts = group["folder_label"].value_counts(dropna=False).to_dict() if "folder_label" in group else {}
        rows.append({
            "similarity_group_id": group_id,
            "group_size": int(len(group)),
            "representative_patch": group["similarity_group_representative_patch"].iloc[0],
            "start_patch_number": int(group["patch_number"].min()),
            "end_patch_number": int(group["patch_number"].max()),
            "n_folder_labels": int(group["folder_label"].nunique(dropna=False)) if "folder_label" in group else 0,
            "folder_label_counts": json.dumps(folder_counts, sort_keys=True),
            "candidate_origins_previous": "|".join(sorted(set(str(value) for value in group.get("previous_accepted_origin_id", []) if str(value) != "nan"))),
            "candidate_origins_next": "|".join(sorted(set(str(value) for value in group.get("next_accepted_origin_id", []) if str(value) != "nan"))),
        })
    return pd.DataFrame(rows)


def write_group_contact_sheets(
    grouped_queue: pd.DataFrame,
    output_dir: Path,
    max_group_sheets: int = 100,
) -> int:
    groups = grouped_queue[grouped_queue["similarity_group_id"] != ""]
    group_summaries = group_summary(grouped_queue)
    if group_summaries.empty:
        return 0
    written = 0
    for summary_row in group_summaries.head(max_group_sheets).itertuples(index=False):
        group = groups[groups["similarity_group_id"] == summary_row.similarity_group_id].sort_values("patch_number")
        items = []
        for row in group.itertuples(index=False):
            label = (
                f"{row.patch} | {getattr(row, 'folder_label', '')} | "
                f"{summary_row.similarity_group_id} n={summary_row.group_size}"
            )
            items.append({"image_path": row.raw_patch_path, "label": label})
        make_contact_sheet(
            items,
            output_dir / "group_contact_sheets" / f"{summary_row.similarity_group_id}_n{summary_row.group_size}.png",
            columns=6,
        )
        written += 1
    return written


def run_missing_patch_similarity(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    queue = pd.read_csv(args.review_queue).sort_values("patch_number").reset_index(drop=True)
    if args.limit:
        queue = queue.head(args.limit)

    fingerprints = build_fingerprint_matrix(queue, thumbnail_size=args.thumbnail_size)
    similarities = pairwise_similarity_matrix(fingerprints)
    grouped_queue = assign_similarity_groups(
        queue,
        similarities,
        threshold=args.threshold,
        min_group_size=args.min_group_size,
    )
    groups = group_summary(grouped_queue)
    pairs = top_similarity_pairs(queue, similarities, top_k=args.top_k)
    edges = high_similarity_edges(queue, similarities, threshold=args.threshold)

    grouped_queue.to_csv(output_dir / "missing_patch_review_queue_with_similarity_groups.csv", index=False)
    groups.to_csv(output_dir / "missing_patch_similarity_groups.csv", index=False)
    pairs.to_csv(output_dir / "missing_patch_similarity_pairs_topk.csv", index=False)
    edges.to_csv(output_dir / "missing_patch_high_similarity_edges.csv", index=False)
    written_sheets = write_group_contact_sheets(grouped_queue, output_dir, max_group_sheets=args.max_group_sheets)

    summary = {
        "candidate_policy": "candidate_only_manual_verified",
        "reviewed_missing_patches": int(len(queue)),
        "thumbnail_size": int(args.thumbnail_size),
        "threshold": float(args.threshold),
        "min_group_size": int(args.min_group_size),
        "similarity_groups": int(len(groups)),
        "grouped_patches": int((grouped_queue["similarity_group_id"] != "").sum()),
        "singleton_patches": int((grouped_queue["similarity_group_id"] == "").sum()),
        "high_similarity_edges": int(len(edges)),
        "group_contact_sheets": int(written_sheets),
    }
    (output_dir / "missing_patch_similarity_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def missing_patch_similarity_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Group visually similar missing patches for candidate-only review.")
    parser.add_argument("--review-queue", type=Path, default=DEFAULT_REVIEW_QUEUE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--threshold", type=float, default=0.92)
    parser.add_argument("--thumbnail-size", type=int, default=64)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-group-size", type=int, default=2)
    parser.add_argument("--max-group-sheets", type=int, default=100)
    parser.add_argument("--limit", type=int, default=0)
    return parser
