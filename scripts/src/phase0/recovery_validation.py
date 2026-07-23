import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.errors import EmptyDataError


DEFAULT_RAW_PATCH_DIR = Path("data/ndb_ufes/patch_level/images")
DEFAULT_ORIGIN_IMAGE_DIR = Path("data/ndb_ufes/origin_level/images")
DEFAULT_ACCEPTED_METADATA = Path("data/ndb_ufes/patch/parcial_pndb_ufes.csv")
DEFAULT_ALL_MISSING = Path("data/all_missing_ids.csv")
DEFAULT_MISSING_IDS = Path("data/missing_ids.csv")
DEFAULT_WRONG_IDS = Path("data/wrong_ids.csv")
DEFAULT_FOLD_ASSIGNMENTS = Path("results/phase3/fold_creation/fold_assignments_patch_level.csv")
DEFAULT_ORIGIN_METADATA = Path("data/ndb_ufes/origin_level/csvs/ndb-ufes.csv")
DEFAULT_PARSED_FOLDERS = Path("data/ndb_ufes/patch_level/csvs/sabpatch_parsed_folders.csv")
DEFAULT_PARSED_TEST = Path("data/ndb_ufes/patch_level/csvs/sabpatch_parsed_test.csv")
DEFAULT_OUTPUT_DIR = Path("results/phase0/recovery_validation")


def patch_number(patch_id: str) -> int | None:
    text = str(patch_id)
    if len(text) < 2 or not text.startswith("p") or not text[1:].isdigit():
        return None
    return int(text[1:])


def origin_number(origin_id) -> int | None:
    text = str(origin_id).replace(".png", "").strip()
    if text.startswith("-"):
        return int(text) if text[1:].isdigit() else None
    return int(text) if text.isdigit() else None


def normalized_origin_id(origin_id) -> str:
    number = origin_number(origin_id)
    if number is None or number < 0:
        return ""
    return f"{number:04d}"


def numeric_png_stems(directory: Path) -> list[str]:
    return sorted(
        path.stem
        for path in Path(directory).glob("*.png")
        if path.stem.isdigit()
    )


def patch_png_stems(directory: Path) -> list[str]:
    return sorted(
        path.stem
        for path in Path(directory).glob("p*.png")
        if patch_number(path.stem) is not None
    )


def read_csv_if_exists(path: Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except EmptyDataError:
        return pd.DataFrame()


def load_folder_labels(parsed_folders_path: Path, parsed_test_path: Path) -> pd.DataFrame:
    frames = []
    for source_name, path in [("folders", parsed_folders_path), ("test", parsed_test_path)]:
        frame = read_csv_if_exists(path)
        if frame.empty or "path" not in frame.columns:
            continue
        frame = frame.copy()
        frame["source_split_hint"] = source_name
        frame["patch"] = frame["path"].astype(str).str.replace(".png", "", regex=False)
        frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=["patch"])
    return pd.concat(frames, ignore_index=True)


def accepted_patch_table(accepted_metadata_path: Path) -> pd.DataFrame:
    table = pd.read_csv(accepted_metadata_path).copy()
    required = {"patch", "origin", "diagnosis"}
    missing = required - set(table.columns)
    if missing:
        raise ValueError(f"Accepted metadata missing required columns: {sorted(missing)}")
    table["patch_number"] = table["patch"].map(patch_number)
    table["origin_id"] = table["origin"].map(normalized_origin_id)
    return table


def previous_next_accepted(missing_number: int, accepted_by_number: dict[int, dict]) -> dict:
    numbers = np.asarray(sorted(accepted_by_number), dtype=int)
    if numbers.size == 0:
        return {}
    insert_at = int(np.searchsorted(numbers, missing_number))
    previous_number = int(numbers[insert_at - 1]) if insert_at > 0 else None
    next_number = int(numbers[insert_at]) if insert_at < len(numbers) else None

    result = {}
    for prefix, number in [("previous", previous_number), ("next", next_number)]:
        if number is None:
            result[f"{prefix}_accepted_patch"] = ""
            result[f"{prefix}_accepted_origin_id"] = ""
            result[f"{prefix}_accepted_diagnosis"] = ""
            result[f"{prefix}_accepted_distance"] = ""
            continue
        row = accepted_by_number[number]
        result[f"{prefix}_accepted_patch"] = row["patch"]
        result[f"{prefix}_accepted_origin_id"] = row["origin_id"]
        result[f"{prefix}_accepted_diagnosis"] = row["diagnosis"]
        result[f"{prefix}_accepted_distance"] = abs(missing_number - number)
    return result


def build_raw_patch_inventory(
    raw_patch_dir: Path,
    accepted_metadata: pd.DataFrame,
    all_missing: pd.DataFrame,
    missing_ids: pd.DataFrame,
    wrong_ids: pd.DataFrame,
    folder_labels: pd.DataFrame,
) -> pd.DataFrame:
    raw_patches = patch_png_stems(raw_patch_dir)
    accepted = accepted_metadata.set_index("patch", drop=False)
    all_missing_set = set(all_missing["patch"]) if "patch" in all_missing.columns else set()
    missing_ids_set = {
        f"p{int(value):04d}"
        for value in missing_ids.get("missing_patch_id", pd.Series(dtype=int)).dropna()
    }
    wrong = wrong_ids.set_index("patch", drop=False) if "patch" in wrong_ids.columns else pd.DataFrame()
    labels = folder_labels.set_index("patch", drop=False) if "patch" in folder_labels.columns else pd.DataFrame()

    rows = []
    for patch_id in raw_patches:
        row = {
            "patch": patch_id,
            "patch_number": patch_number(patch_id),
            "raw_patch_path": str(Path(raw_patch_dir) / f"{patch_id}.png"),
            "accepted": patch_id in accepted.index,
            "raw_absent_from_accepted": patch_id not in accepted.index,
            "listed_all_missing": patch_id in all_missing_set,
            "listed_missing_ids": patch_id in missing_ids_set,
            "listed_wrong_ids": patch_id in wrong.index,
            "proposed_correct_origin_id": "",
            "has_proposed_correct_origin": False,
            "needs_manual_association": patch_id not in accepted.index,
            "accepted_origin_id": "",
            "accepted_diagnosis": "",
            "folder_label": "",
            "folder_label_number": "",
            "source_split_hint": "",
        }
        if patch_id in accepted.index:
            accepted_row = accepted.loc[patch_id]
            row["accepted_origin_id"] = accepted_row["origin_id"]
            row["accepted_diagnosis"] = accepted_row["diagnosis"]
        if patch_id in wrong.index:
            correct_origin = wrong.loc[patch_id]["correct_origin"]
            normalized = normalized_origin_id(correct_origin)
            row["proposed_correct_origin_id"] = normalized
            row["has_proposed_correct_origin"] = bool(normalized)
        if patch_id in labels.index:
            label_row = labels.loc[patch_id]
            row["folder_label"] = label_row.get("lesion", "")
            row["folder_label_number"] = label_row.get("label_number", "")
            row["source_split_hint"] = label_row.get("source_split_hint", "")
        rows.append(row)
    return pd.DataFrame(rows).sort_values("patch_number").reset_index(drop=True)


def build_origin_image_inventory(
    origin_image_dir: Path,
    accepted_metadata: pd.DataFrame,
    origin_metadata_path: Path,
) -> pd.DataFrame:
    origins = numeric_png_stems(origin_image_dir)
    accepted_counts = accepted_metadata.groupby("origin_id").size().rename("accepted_patch_count")
    origin_meta = read_csv_if_exists(origin_metadata_path)
    if not origin_meta.empty and "path" in origin_meta.columns:
        origin_meta = origin_meta.copy()
        origin_meta["origin_id"] = origin_meta["path"].map(normalized_origin_id)
        origin_meta = origin_meta.set_index("origin_id", drop=False)
    else:
        origin_meta = pd.DataFrame()

    rows = []
    for origin_id in origins:
        count = int(accepted_counts.get(origin_id, 0))
        row = {
            "origin_id": origin_id,
            "origin_number": int(origin_id),
            "origin_image_path": str(Path(origin_image_dir) / f"{origin_id}.png"),
            "has_accepted_patches": count > 0,
            "accepted_patch_count": count,
            "patchless_priority": 0 if count == 0 else 1,
        }
        if not origin_meta.empty and origin_id in origin_meta.index:
            meta_row = origin_meta.loc[origin_id]
            for column in ["diagnosis", "TaskII", "TaskIII", "TaskIV", "dysplasia_severity", "patient_id", "lesion_id"]:
                if column in meta_row.index:
                    row[column] = meta_row[column]
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["patchless_priority", "origin_number"]).reset_index(drop=True)


def build_missing_patch_candidates(raw_inventory: pd.DataFrame, accepted_metadata: pd.DataFrame) -> pd.DataFrame:
    accepted_by_number = {
        int(row.patch_number): row._asdict()
        for row in accepted_metadata[accepted_metadata["patch_number"].notna()].itertuples(index=False)
    }
    rows = []
    missing = raw_inventory[raw_inventory["raw_absent_from_accepted"]].copy()
    for row in missing.itertuples(index=False):
        candidate = row._asdict()
        candidate.update(previous_next_accepted(int(row.patch_number), accepted_by_number))
        candidate["candidate_status"] = (
            "proposed_correct_origin_needs_review"
            if row.has_proposed_correct_origin
            else "manual_origin_association_needed"
        )
        rows.append(candidate)
    return pd.DataFrame(rows)


def build_patchless_origin_candidates(origin_inventory: pd.DataFrame) -> pd.DataFrame:
    candidates = origin_inventory[~origin_inventory["has_accepted_patches"]].copy()
    if candidates.empty:
        return candidates
    sort_columns = ["patchless_priority", "origin_number"]
    if "diagnosis" in candidates.columns:
        class_counts = candidates["diagnosis"].value_counts(dropna=False).to_dict()
        candidates["patchless_origin_count_for_diagnosis"] = candidates["diagnosis"].map(class_counts)
        sort_columns = ["patchless_priority", "diagnosis", "origin_number"]
    return candidates.sort_values(sort_columns).reset_index(drop=True)


def class_ratio_table(patch_table: pd.DataFrame) -> pd.DataFrame:
    origin_col = "origin_id" if "origin_id" in patch_table.columns else "origin"
    table = patch_table.copy()
    if origin_col == "origin":
        table["origin_id"] = table["origin"].map(normalized_origin_id)
        origin_col = "origin_id"
    counts = pd.crosstab(table[origin_col], table["diagnosis"])
    counts["total_patches"] = counts.sum(axis=1)
    class_columns = [column for column in counts.columns if column != "total_patches"]
    for column in class_columns:
        counts[f"ratio_{column}"] = counts[column] / counts["total_patches"]
    counts["n_patch_classes"] = counts[class_columns].gt(0).sum(axis=1)
    counts["has_multiple_patch_classes"] = counts["n_patch_classes"] > 1
    counts["dominant_class"] = counts[class_columns].idxmax(axis=1)
    counts["dominant_class_ratio"] = counts[class_columns].max(axis=1) / counts["total_patches"]
    return counts.reset_index().sort_values(["total_patches", origin_col], ascending=[False, True])


def fold_origin_dominance(fold_assignments: pd.DataFrame) -> pd.DataFrame:
    required = {"fold", "origin_id", "diagnosis"}
    missing = required - set(fold_assignments.columns)
    if missing:
        raise ValueError(f"Fold assignments missing required columns: {sorted(missing)}")
    counts = (
        fold_assignments.groupby(["fold", "origin_id", "diagnosis"], dropna=False)
        .size()
        .reset_index(name="patch_count")
    )
    fold_totals = fold_assignments.groupby("fold").size().rename("fold_patch_count")
    counts["fold_patch_count"] = counts["fold"].map(fold_totals)
    counts["fold_patch_share"] = counts["patch_count"] / counts["fold_patch_count"]
    return counts.sort_values(["fold_patch_share", "patch_count"], ascending=[False, False])


def fold_class_balance(fold_assignments: pd.DataFrame) -> pd.DataFrame:
    counts = (
        fold_assignments.groupby(["fold", "diagnosis"], dropna=False)
        .size()
        .reset_index(name="patch_count")
    )
    fold_totals = fold_assignments.groupby("fold").size().rename("fold_patch_count")
    counts["fold_patch_count"] = counts["fold"].map(fold_totals)
    counts["fold_class_share"] = counts["patch_count"] / counts["fold_patch_count"]
    return counts.sort_values(["fold", "diagnosis"]).reset_index(drop=True)


def write_json(payload: dict, path: Path) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str))


def run_recovery_validation(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    accepted = accepted_patch_table(args.accepted_metadata)
    all_missing = read_csv_if_exists(args.all_missing)
    missing_ids = read_csv_if_exists(args.missing_ids)
    wrong_ids = read_csv_if_exists(args.wrong_ids)
    folder_labels = load_folder_labels(args.parsed_folders, args.parsed_test)

    raw_inventory = build_raw_patch_inventory(
        args.raw_patch_dir,
        accepted,
        all_missing,
        missing_ids,
        wrong_ids,
        folder_labels,
    )
    origin_inventory = build_origin_image_inventory(args.origin_image_dir, accepted, args.origin_metadata)
    missing_candidates = build_missing_patch_candidates(raw_inventory, accepted)
    patchless_candidates = build_patchless_origin_candidates(origin_inventory)

    raw_inventory.to_csv(output_dir / "raw_patch_inventory.csv", index=False)
    origin_inventory.to_csv(output_dir / "origin_image_inventory.csv", index=False)
    missing_candidates.to_csv(output_dir / "missing_patch_candidates.csv", index=False)
    patchless_candidates.to_csv(output_dir / "patchless_origin_candidates.csv", index=False)

    summary = {
        "raw_patch_images": int(len(raw_inventory)),
        "accepted_patch_rows": int(raw_inventory["accepted"].sum()),
        "raw_absent_from_accepted": int(raw_inventory["raw_absent_from_accepted"].sum()),
        "listed_all_missing": int(raw_inventory["listed_all_missing"].sum()),
        "listed_wrong_ids": int(raw_inventory["listed_wrong_ids"].sum()),
        "proposed_correct_origin_candidates": int(raw_inventory["has_proposed_correct_origin"].sum()),
        "numeric_origin_images": int(len(origin_inventory)),
        "origins_with_accepted_patches": int(origin_inventory["has_accepted_patches"].sum()),
        "patchless_origin_images": int((~origin_inventory["has_accepted_patches"]).sum()),
        "candidate_policy": "manual_verified_only",
    }
    write_json(summary, output_dir / "recovery_summary.json")
    return summary


def run_balance_validation(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    accepted = accepted_patch_table(args.accepted_metadata)
    origin_inventory = build_origin_image_inventory(args.origin_image_dir, accepted, args.origin_metadata)
    ratios = class_ratio_table(accepted)
    ratios.to_csv(output_dir / "origin_patch_class_ratios.csv", index=False)
    top_origins = ratios.sort_values("total_patches", ascending=False).head(args.top_n)
    top_origins.to_csv(output_dir / "top_patch_heavy_origins.csv", index=False)

    summary = {
        "accepted_origins": int(accepted["origin_id"].nunique()),
        "patchless_origin_images": int((~origin_inventory["has_accepted_patches"]).sum()),
        "accepted_origins_with_multiple_patch_classes": int(ratios["has_multiple_patch_classes"].sum()),
    }

    fold_path = Path(args.fold_assignments)
    if fold_path.exists():
        fold_table = pd.read_csv(fold_path)
        dominance = fold_origin_dominance(fold_table)
        balance = fold_class_balance(fold_table)
        dominance.to_csv(output_dir / "fold_origin_dominance.csv", index=False)
        balance.to_csv(output_dir / "fold_class_balance.csv", index=False)
        if not dominance.empty:
            top = dominance.iloc[0]
            summary["top_fold_origin_id"] = int(top["origin_id"])
            summary["top_fold_origin_fold"] = int(top["fold"])
            summary["top_fold_origin_patch_share"] = float(top["fold_patch_share"])
    write_json(summary, output_dir / "balance_summary.json")
    return summary


def add_common_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--raw-patch-dir", type=Path, default=DEFAULT_RAW_PATCH_DIR)
    parser.add_argument("--origin-image-dir", type=Path, default=DEFAULT_ORIGIN_IMAGE_DIR)
    parser.add_argument("--accepted-metadata", type=Path, default=DEFAULT_ACCEPTED_METADATA)
    parser.add_argument("--all-missing", type=Path, default=DEFAULT_ALL_MISSING)
    parser.add_argument("--missing-ids", type=Path, default=DEFAULT_MISSING_IDS)
    parser.add_argument("--wrong-ids", type=Path, default=DEFAULT_WRONG_IDS)
    parser.add_argument("--origin-metadata", type=Path, default=DEFAULT_ORIGIN_METADATA)
    parser.add_argument("--parsed-folders", type=Path, default=DEFAULT_PARSED_FOLDERS)
    parser.add_argument("--parsed-test", type=Path, default=DEFAULT_PARSED_TEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)


def recovery_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validation raw patch images that are absent from accepted metadata.")
    add_common_paths(parser)
    return parser


def balance_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report origin patch counts, class ratios, and fold dominance.")
    add_common_paths(parser)
    parser.add_argument("--fold-assignments", type=Path, default=DEFAULT_FOLD_ASSIGNMENTS)
    parser.add_argument("--top-n", type=int, default=30)
    return parser
