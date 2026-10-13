from __future__ import annotations

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.phase0_dataset_builder.matching import (
    CONFIRMED_MIN_AGREEMENT, CONFIRMED_MIN_INSIDE, UnionFind, group_pictures, overlap_fractions, parse_homography,
)
from src.phase0_dataset_builder.sources import (
    NDB_METADATA, PATCH_PLACEMENTS, PATCH_TABLE_LAB, PICTURE_RELATIONS, PICTURE_TABLE_LAB, POOL_MATCHES,
    SAB_PATCHES_DIR, SEVERITY, Diagnosis, HistopathImage, Patch, add_source_arguments, format_counts, load_patch_table,
    load_pictures, pixel_sha256,
)
from src.utils.logger import logger


LAB_DIR_NAME = "private_lab"  # git-ignored: case prefixes and file paths live only here

# patch-table
MATCH = "match"
LESS_SEVERE = "patch_less_severe"
MORE_SEVERE = "patch_more_severe"
NOT_IN_NDB = "not_in_ndb"

LAB_COLUMNS = [
    "patch_id", "patch_path", "patch_diagnosis",
    "case_pseudonym", "case_prefix", "photo_uuid", "patch_number", "copy_number", "sab_patch_filename",
    "histopath_id", "picture_datasets", "ndb_origin_id", "sab_folder", "sab_picture_path", "picture_group", "case_group",
    "x", "y", "x2", "y2", "match_status",
    "ndb_diagnosis", "patch_vs_picture_diagnosis",
    "other_confirmed_pictures", "other_confirmed_picture_ids", "sab_crop_check", "identical_patch_ids", "parent_image_check",
]
PUBLIC_COLUMNS = [
    "patch_id", "patch_path", "patch_diagnosis", "case_pseudonym",
    "histopath_id", "picture_datasets", "ndb_origin_id", "sab_folder", "picture_group", "case_group",
    "x", "y", "x2", "y2", "match_status",
    "ndb_diagnosis", "patch_vs_picture_diagnosis",
    "other_confirmed_pictures", "other_confirmed_picture_ids", "sab_crop_check", "identical_patch_ids", "parent_image_check",
]
PICTURE_LAB_COLUMNS = [
    "histopath_id", "datasets", "ndb_origin_id", "ndb_diagnosis", "sab_folders", "case_pseudonym", "case_prefix",
    "sab_files", "picture_group", "case_group", "n_patches", "patch_diagnoses", "group_conflicts", "overlap_with_group",
]
PICTURE_PUBLIC_COLUMNS = [
    "histopath_id", "datasets", "ndb_origin_id", "ndb_diagnosis", "sab_folders", "case_pseudonym",
    "picture_group", "case_group", "n_patches", "patch_diagnoses", "group_conflicts", "overlap_with_group",
]

LEAK_PATTERNS = {
    "case prefix": re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}"),
    "SAB file uuid": re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"),
    "SAB path": re.compile(r"data/SAB/"),
    "absolute path": re.compile(r"/(?:Users|Volumes)/"),
}

# How the SAB crop with the recorded file name compares to the P-NDB-UFES patch image, by pixels
CROP_VERIFIED = "verified"
CROP_VERIFIED_AMONG_COPIES = "verified_among_identical_crops"
CROP_NAME_DIFFERS = "name_differs"
CROP_CLASS_DIFFERS = "class_differs"
CROP_MISSING = "no_crop_with_these_pixels"
CROP_NOT_CHECKED = "not_checked"
CLASS_FOLDER_DIAGNOSIS = {
    "carcinoma": Diagnosis.OSCC,
    "with_dysplasia": Diagnosis.WITH_DYSPLASIA,
    "no_dysplasia": Diagnosis.WITHOUT_DYSPLASIA,
}

# The picture found by searching the whole pool by template matching, against the parent photo named in the SAB file name
PARENT_AGREES = "agrees"
PARENT_AGREES_AND_ELSEWHERE = "agrees_and_also_found_in_another_picture"
PARENT_ONLY_ELSEWHERE = "found_only_in_another_picture"
PARENT_NOT_FOUND = "not_found"

TABLES_DIR = PATCH_TABLE_LAB.parent.parent
PICTURE_ADDED_LATER = {"case_group", "group_conflicts", "overlap_with_group"}  # need the groups of related pictures and of cases
PATCH_TABLE_PUBLIC_NAME = "patch_table_public.csv"
PICTURE_TABLE_PUBLIC_NAME = "picture_table_public.csv"
CASE_TABLE_PUBLIC_NAME = "case_table_public.csv"
CASE_TABLE_LAB_NAME = "case_table_lab.csv"
CASE_FLAGS_LAB_NAME = "case_flags_lab.csv"
CASE_PUBLIC_COLUMNS = ["case_pseudonym", "case_group", "n_pictures", "n_patches"]


def relation_to_picture_diagnosis(patch_diagnosis: Diagnosis, ndb_diagnosis: str | None) -> str:
    """How a patch label relates to the NDB-UFES diagnosis of its picture (the reference)."""
    if ndb_diagnosis is None:
        return NOT_IN_NDB
    reference = Diagnosis(ndb_diagnosis)
    if patch_diagnosis == reference:
        return MATCH
    return MORE_SEVERE if SEVERITY[patch_diagnosis] > SEVERITY[reference] else LESS_SEVERE


def case_pseudonyms(prefixes: Iterable[str]) -> dict[str, str]:
    return {prefix: f"case_{rank:03d}" for rank, prefix in enumerate(sorted(set(prefixes)), start=1)}


def patch_pixel_hashes(patches: list[Patch]) -> dict[str, str]:
    hashes = {}
    for number, patch in enumerate(patches, start=1):
        hashes[patch.patch_id] = pixel_sha256(patch.path)
        if number % 1000 == 0:
            logger.info(f"Hashed {number}/{len(patches)} patch images")
    return hashes


def identical_patch_groups(hashes: dict[str, str]) -> list[list[str]]:
    """Groups of two or more patches whose images have exactly the same pixels."""
    by_hash: dict[str, list[str]] = defaultdict(list)
    for patch_id, digest in hashes.items():
        by_hash[digest].append(patch_id)
    return sorted(sorted(ids) for ids in by_hash.values() if len(ids) > 1)


def verify_sab_crops(patches: list[Patch], hashes: dict[str, str], sab_patches_dir: Path) -> dict[str, str]:
    """Patch id -> how the SAB crop carrying its recorded file name compares to the patch image, by pixels.

    The crops sit in <old split folder>/<class folder>/<name>.png; only the file name and the class folder are used.
    """
    crop_paths = sorted(Path(sab_patches_dir).glob("*/*/*.png")) if Path(sab_patches_dir).is_dir() else []
    if not crop_paths:
        logger.warning(f"No SAB crops found under {sab_patches_dir}; the crop check is skipped")
        return {patch.patch_id: CROP_NOT_CHECKED for patch in patches}

    crops_with_pixels: dict[str, list[Path]] = defaultdict(list)
    for number, path in enumerate(crop_paths, start=1):
        crops_with_pixels[pixel_sha256(path)].append(path)
        if number % 1000 == 0:
            logger.info(f"Hashed {number}/{len(crop_paths)} SAB crops")

    result = {}
    for number, patch in enumerate(patches, start=1):
        crops = crops_with_pixels.get(hashes[patch.patch_id], [])
        named = [crop for crop in crops if crop.name == patch.sab_name.filename]
        if not crops:
            result[patch.patch_id] = CROP_MISSING
        elif not named:
            result[patch.patch_id] = CROP_NAME_DIFFERS
        elif all(CLASS_FOLDER_DIAGNOSIS.get(crop.parent.name) != patch.diagnosis for crop in named):
            result[patch.patch_id] = CROP_CLASS_DIFFERS
        else:
            result[patch.patch_id] = CROP_VERIFIED if len(crops) == 1 else CROP_VERIFIED_AMONG_COPIES
        if number % 1000 == 0:
            logger.info(f"Checked {number}/{len(patches)} patches against the SAB crops")
    return result


def check_parent_images(patches: list[Patch], claimed_picture: dict[str, str], pool: pd.DataFrame) -> dict[str, str]:
    """Patch id -> whether the pool search found the picture its SAB file name (prefix and photo) names."""
    found = pool.groupby("patch_id")["histopath_id"].apply(set).to_dict()
    result = {}
    for patch in patches:
        pictures = found.get(patch.patch_id, set())
        if not pictures:
            result[patch.patch_id] = PARENT_NOT_FOUND
        elif claimed_picture[patch.patch_id] not in pictures:
            result[patch.patch_id] = PARENT_ONLY_ELSEWHERE
        else:
            result[patch.patch_id] = PARENT_AGREES if len(pictures) == 1 else PARENT_AGREES_AND_ELSEWHERE
    return result


def build_lab_table(
    patches: list[Patch],
    pictures: dict[str, HistopathImage],
    claimed_picture: dict[str, str],
    pool_matches: dict[tuple[str, str], object],
    group_of: dict[str, str],
    ndb_diagnosis_of: dict[str, str],
    confirmed_pictures: dict[str, list[str]],
    pseudonym_of: dict[str, str],
    crop_check: dict[str, str],
    identical: dict[str, list[str]],
    parent_check: dict[str, str],
) -> pd.DataFrame:

    rows = []
    for patch in patches:
        name = patch.sab_name
        picture = pictures[claimed_picture[patch.patch_id]]
        match = pool_matches.get((patch.patch_id, picture.histopath_id))
        sab_file = next((f for f in picture.sab_files if f.path.stem == name.origin_image_id), None)
        ndb_origin_id = picture.ndb_origin_id
        ndb_diagnosis = ndb_diagnosis_of.get(ndb_origin_id) if ndb_origin_id else None
        others = confirmed_pictures.get(patch.patch_id, [])
        rows.append({
            "patch_id": patch.patch_id,
            "patch_path": str(patch.path),
            "patch_diagnosis": patch.diagnosis.value,
            "case_pseudonym": pseudonym_of[name.case_prefix],
            "case_prefix": name.case_prefix,
            "photo_uuid": name.photo_uuid,
            "patch_number": name.patch_number,
            "copy_number": name.copy_number,
            "sab_patch_filename": name.filename,
            "histopath_id": picture.histopath_id,
            "picture_datasets": picture.dataset_names,
            "ndb_origin_id": ndb_origin_id or "",
            "sab_folder": sab_file.path.parent.name if sab_file else "",
            "sab_picture_path": str(sab_file.path) if sab_file else "",
            "picture_group": group_of[picture.histopath_id],
            "x": match.x if match else "",
            "y": match.y if match else "",
            "x2": match.x + match.width if match else "",
            "y2": match.y + match.height if match else "",
            "match_status": match.status if match else "none",
            "ndb_diagnosis": ndb_diagnosis or "",
            "patch_vs_picture_diagnosis": relation_to_picture_diagnosis(patch.diagnosis, ndb_diagnosis),
            "other_confirmed_pictures": len(others),
            "other_confirmed_picture_ids": " ".join(others),
            "sab_crop_check": crop_check[patch.patch_id],
            "identical_patch_ids": " ".join(identical.get(patch.patch_id, [])),
            "parent_image_check": parent_check[patch.patch_id],
        })
    return pd.DataFrame(rows, columns=[c for c in LAB_COLUMNS if c != "case_group"]).sort_values("patch_id").reset_index(drop=True)


def find_leaks(public: pd.DataFrame) -> list[str]:
    """Cells of the public table that carry something identifying; empty when clean."""
    leaks = []
    for column in public.columns:
        values = public[column].astype(str)
        for label, pattern in LEAK_PATTERNS.items():
            hits = int(values.str.contains(pattern).sum())
            if hits:
                leaks.append(f"{column}: {hits} cells match {label}")
    return leaks


# Pictures of one group show the same tissue, so their SAB folders and patch labels are expected to agree; where not, flag it for review
FOLDER_DIFFERS = "sab_folder_differs_in_group"
LABELS_DIFFER = "patch_labels_differ_in_group"


def _overlaps(picture_id: str, relations: pd.DataFrame, sizes: dict) -> str:
    """For each related picture: how much of this one is seen in it, and how much of it is seen in this one."""
    parts = []
    for relation in relations.itertuples():
        if picture_id not in (relation.a, relation.b):
            continue
        a_in_b, b_in_a = overlap_fractions(parse_homography(relation.homography), sizes[relation.a], sizes[relation.b])
        other, mine, theirs = (relation.b, a_in_b, b_in_a) if picture_id == relation.a else (relation.a, b_in_a, a_in_b)
        parts.append(f"{other}: this_seen_in_other={mine:.2f} other_seen_in_this={theirs:.2f} scale={relation.scale_x:.2f}")
    return " | ".join(parts)


def picture_group_conflicts(
    pictures: dict[str, HistopathImage], lab: pd.DataFrame, group_of: dict[str, str], strong: pd.DataFrame,
) -> tuple[dict[str, str], dict[str, str]]:
    """Per picture: the conflicts inside its group of related pictures, and its overlap with the group."""
    main_diagnosis = lab.groupby("histopath_id")["patch_diagnosis"].agg(lambda labels: labels.value_counts().index[0]).to_dict()
    sizes = {picture_id: (picture.files[0].width, picture.files[0].height) for picture_id, picture in pictures.items()}
    members_of: dict[str, list[str]] = defaultdict(list)
    for picture_id in sorted(pictures):
        members_of[group_of[picture_id]].append(picture_id)

    conflicts, overlaps = {}, {}
    for ids in members_of.values():
        folders = set().union(*(pictures[i].sab_folders for i in ids))
        labels = {main_diagnosis[i] for i in ids if i in main_diagnosis}
        in_group = strong[strong["a"].isin(ids) & strong["b"].isin(ids)]
        for picture_id in ids:
            reasons = []
            if len(ids) > 1 and len(folders) > 1:
                reasons.append(FOLDER_DIFFERS)
            if len(ids) > 1 and len(labels) > 1:
                reasons.append(LABELS_DIFFER)
            conflicts[picture_id] = " ".join(reasons)
            overlaps[picture_id] = _overlaps(picture_id, in_group, sizes) if len(ids) > 1 else ""
    return conflicts, overlaps


def build_picture_table(
    pictures: dict[str, HistopathImage],
    lab: pd.DataFrame,
    group_of: dict[str, str],
    ndb_diagnosis_of: dict[str, str],
    pseudonym_of: dict[str, str],
) -> pd.DataFrame:
    """One row per picture, including pictures with no patches."""
    counts_of = {
        picture_id: group["patch_diagnosis"].value_counts()
        for picture_id, group in lab.groupby("histopath_id")
    }
    rows = []
    for picture_id, picture in pictures.items():
        ndb_origin_id = picture.ndb_origin_id
        prefixes = sorted(picture.case_prefixes)
        counts = counts_of.get(picture_id)
        rows.append({
            "histopath_id": picture_id,
            "datasets": picture.dataset_names,
            "ndb_origin_id": ndb_origin_id or "",
            "ndb_diagnosis": ndb_diagnosis_of.get(ndb_origin_id, "") if ndb_origin_id else "",
            "sab_folders": " ".join(sorted(picture.sab_folders)),
            "case_pseudonym": " ".join(pseudonym_of[prefix] for prefix in prefixes),
            "case_prefix": " ".join(prefixes),
            "sab_files": " | ".join(str(f.path) for f in picture.sab_files),
            "picture_group": group_of[picture_id],
            "n_patches": int(counts.sum()) if counts is not None else 0,
            "patch_diagnoses": format_counts(counts) if counts is not None else "",
        })
    return pd.DataFrame(rows, columns=[c for c in PICTURE_LAB_COLUMNS if c not in PICTURE_ADDED_LATER]).sort_values(["case_prefix", "histopath_id"]).reset_index(drop=True)


# Case groups: case prefixes tied together by shared evidence form one group, so a group never crosses folds
FLAG_PICTURE = "picture_filed_under_several_case_prefixes"
FLAG_SIFT_GROUP = "related_pictures_under_several_case_prefixes"
FLAG_NDB_PATIENT = "ndb_patient_under_several_case_prefixes"

FLAG_NOTES = {
    FLAG_PICTURE: "The same picture is filed under more than one SAB case prefix. The cases are kept in one group so they cannot fall in different folds. Ask which filing is right.",
    FLAG_SIFT_GROUP: "Pictures that show the same tissue are filed under more than one SAB case prefix. The cases are kept in one group. Ask which filing is right.",
    FLAG_NDB_PATIENT: "One NDB-UFES patient id appears under more than one SAB case prefix. The cases are kept in one group. Ask which is right.",
}
FLAG_COLUMNS = ["flag", "evidence", "case_prefixes", "case_group", "patches_in_evidence", "review_status", "note"]


@dataclass(frozen=True)
class CaseGroups:
    group_of_prefix: dict[str, str]
    flags: pd.DataFrame


def _prefixes(cell: str) -> list[str]:
    return [prefix for prefix in str(cell).split() if prefix]


def build_case_groups(pictures: pd.DataFrame, ndb_patient_of_origin: dict[str, str]) -> CaseGroups:
    """``pictures`` needs: histopath_id, case_prefix (space separated), picture_group, ndb_origin_id, n_patches."""
    uf = UnionFind()
    tied: list[tuple[str, str, list[str], int]] = []  # flag, evidence, prefixes, patches in the evidence

    for row in pictures.itertuples():
        prefixes = _prefixes(row.case_prefix)
        for prefix in prefixes:
            uf.add(prefix)
        for prefix in prefixes[1:]:
            uf.union(prefixes[0], prefix)
        if len(prefixes) > 1:
            tied.append((FLAG_PICTURE, row.histopath_id, prefixes, int(row.n_patches)))

    for group_id, members in pictures.groupby("picture_group"):
        prefixes = sorted({p for cell in members["case_prefix"] for p in _prefixes(cell)})
        for prefix in prefixes[1:]:
            uf.union(prefixes[0], prefix)
        if len(prefixes) > 1 and len(members) > 1:  # a single picture is already reported by its own flag
            tied.append((FLAG_SIFT_GROUP, group_id, prefixes, int(members["n_patches"].sum())))

    by_patient: dict[str, dict] = {}
    for row in pictures.itertuples():
        patient = ndb_patient_of_origin.get(row.ndb_origin_id) if row.ndb_origin_id else None
        if patient is None:
            continue
        entry = by_patient.setdefault(patient, {"prefixes": set(), "patches": 0})
        entry["prefixes"].update(_prefixes(row.case_prefix))
        entry["patches"] += int(row.n_patches)
    for patient, entry in by_patient.items():
        prefixes = sorted(entry["prefixes"])
        for prefix in prefixes[1:]:
            uf.union(prefixes[0], prefix)
        if len(prefixes) > 1:
            tied.append((FLAG_NDB_PATIENT, f"ndb_patient_{patient}", prefixes, entry["patches"]))

    members_of: dict[str, list[str]] = {}
    for prefix in sorted({p for cell in pictures["case_prefix"] for p in _prefixes(cell)}):
        members_of.setdefault(uf.find(prefix), []).append(prefix)
    ordered = sorted(members_of.values(), key=lambda prefixes: prefixes[0])
    group_of_prefix = {prefix: f"group_{rank:03d}" for rank, prefixes in enumerate(ordered, start=1) for prefix in prefixes}

    flags = pd.DataFrame(
        [
            {
                "flag": flag,
                "evidence": evidence,
                "case_prefixes": " ".join(prefixes),
                "case_group": group_of_prefix[prefixes[0]],
                "patches_in_evidence": patches,
                "review_status": "pending",
                "note": FLAG_NOTES[flag],
            }
            for flag, evidence, prefixes, patches in tied
        ],
        columns=FLAG_COLUMNS,
    )
    return CaseGroups(group_of_prefix, flags)


def picture_case_groups(lab_pictures: pd.DataFrame, group_of_prefix: dict[str, str]) -> list[str]:
    """Case group of each picture; a picture with no prefix (NDB-UFES only) takes the one of its related views, if unique."""
    own = {row.histopath_id: group_of_prefix[row.case_prefix.split()[0]] if row.case_prefix else "" for row in lab_pictures.itertuples()}
    related = lab_pictures.groupby("picture_group")["histopath_id"].apply(list).to_dict()
    result = []
    for row in lab_pictures.itertuples():
        if own[row.histopath_id]:
            result.append(own[row.histopath_id])
            continue
        among_related = {own[other] for other in related[row.picture_group] if own[other]}
        result.append(next(iter(among_related)) if len(among_related) == 1 else "")
    return result


def build_case_table(lab: pd.DataFrame, lab_pictures: pd.DataFrame, pseudonym_of: dict[str, str], group_of_prefix: dict[str, str]) -> pd.DataFrame:
    cases = pd.DataFrame({"case_prefix": sorted(group_of_prefix)})
    cases["case_pseudonym"] = cases["case_prefix"].map(pseudonym_of)
    cases["case_group"] = cases["case_prefix"].map(group_of_prefix)
    cases["n_patches"] = cases["case_prefix"].map(lab.groupby("case_prefix").size()).fillna(0).astype(int)
    cases["n_pictures"] = cases["case_prefix"].map(
        lambda prefix: int(lab_pictures["case_prefix"].map(lambda cell: prefix in cell.split()).sum())
    )
    return cases


def run_build_patch_table(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    lab_dir = output_dir / LAB_DIR_NAME
    lab_dir.mkdir(parents=True, exist_ok=True)

    patches = load_patch_table(args)
    pictures = {picture.histopath_id: picture for picture in load_pictures(args)}
    relations = pd.read_csv(args.relations)
    strong = relations[relations["strong"].astype(bool)]
    metadata = pd.read_csv(args.ndb_metadata, dtype=str)
    placements = pd.read_csv(args.placements)
    pool = pd.read_csv(args.pool_matches)
    picture_of = {file.image_id: picture.histopath_id for picture in pictures.values() for file in picture.files}
    claimed_picture = {patch.patch_id: picture_of[f"sab:{patch.sab_name.origin_image_id}"] for patch in patches}
    pool_matches = {(row.patch_id, row.histopath_id): row for row in pool.itertuples()}

    confirmed = placements[(placements["inside_fraction"] >= CONFIRMED_MIN_INSIDE) & (placements["agreement"] >= CONFIRMED_MIN_AGREEMENT)]
    confirmed_pictures: dict[str, list[str]] = defaultdict(list)
    for patch_id, picture_id in zip(confirmed["patch_id"], confirmed["to_picture"]):
        confirmed_pictures[patch_id].append(picture_id)

    group_of = group_pictures(sorted(pictures), list(zip(strong["a"], strong["b"])))
    ndb_diagnosis_of = {Path(path).stem: diagnosis for path, diagnosis in zip(metadata["path"], metadata["diagnosis"])}
    ndb_patient_of_origin = {Path(path).stem: patient for path, patient in zip(metadata["path"], metadata["patient_id"])}
    prefixes = {patch.sab_name.case_prefix for patch in patches} | set().union(*(p.case_prefixes for p in pictures.values()))
    pseudonym_of = case_pseudonyms(prefixes)

    hashes = patch_pixel_hashes(patches)
    identical_groups = identical_patch_groups(hashes)
    identical = {patch_id: [other for other in ids if other != patch_id] for ids in identical_groups for patch_id in ids}

    lab = build_lab_table(
        patches,
        pictures,
        claimed_picture,
        pool_matches,
        group_of,
        ndb_diagnosis_of,
        {patch_id: sorted(ids) for patch_id, ids in confirmed_pictures.items()},
        pseudonym_of,
        verify_sab_crops(patches, hashes, args.sab_patches_dir),
        identical,
        check_parent_images(patches, claimed_picture, pool),
    )
    lab_pictures = build_picture_table(pictures, lab, group_of, ndb_diagnosis_of, pseudonym_of)
    if len(lab) != len(patches) or lab["patch_id"].duplicated().any():
        raise ValueError("The patch table must have exactly one row per patch")

    groups = build_case_groups(lab_pictures, ndb_patient_of_origin)
    lab["case_group"] = lab["case_prefix"].map(groups.group_of_prefix)
    lab_pictures["case_group"] = picture_case_groups(lab_pictures, groups.group_of_prefix)
    conflicts, overlaps = picture_group_conflicts(pictures, lab, group_of, strong)
    lab_pictures["group_conflicts"] = lab_pictures["histopath_id"].map(conflicts)
    lab_pictures["overlap_with_group"] = lab_pictures["histopath_id"].map(overlaps)
    if lab["case_group"].isna().any():
        raise ValueError("Every patch must belong to a case group")
    spread = lab.groupby("histopath_id")["case_group"].nunique()
    if (spread > 1).any():
        raise ValueError(f"Patches of one picture fell in different case groups: {list(spread[spread > 1].index)}")
    lab, lab_pictures = lab[LAB_COLUMNS], lab_pictures[PICTURE_LAB_COLUMNS]
    cases = build_case_table(lab, lab_pictures, pseudonym_of, groups.group_of_prefix)

    public, public_pictures, public_cases = lab[PUBLIC_COLUMNS], lab_pictures[PICTURE_PUBLIC_COLUMNS], cases[CASE_PUBLIC_COLUMNS]
    leaks = find_leaks(public) + find_leaks(public_pictures) + find_leaks(public_cases)
    if leaks:
        raise ValueError("A public table carries identifying content: " + "; ".join(leaks))

    lab.to_csv(lab_dir / PATCH_TABLE_LAB.name, index=False)
    lab_pictures.to_csv(lab_dir / PICTURE_TABLE_LAB.name, index=False)
    cases.to_csv(lab_dir / CASE_TABLE_LAB_NAME, index=False)
    groups.flags.to_csv(lab_dir / CASE_FLAGS_LAB_NAME, index=False)
    public.to_csv(output_dir / PATCH_TABLE_PUBLIC_NAME, index=False)
    public_pictures.to_csv(output_dir / PICTURE_TABLE_PUBLIC_NAME, index=False)
    public_cases.to_csv(output_dir / CASE_TABLE_PUBLIC_NAME, index=False)

    relation_counts = lab["patch_vs_picture_diagnosis"].value_counts().to_dict()
    crop_counts = lab["sab_crop_check"].value_counts().to_dict()
    parent_counts = lab["parent_image_check"].value_counts().to_dict()
    in_ndb = lab_pictures[(lab_pictures["ndb_diagnosis"] != "") & (lab_pictures["sab_folders"] != "")]
    folder_vs_ndb = {f"{folder} / {diagnosis}": int(count) for (folder, diagnosis), count in in_ndb.groupby(["sab_folders", "ndb_diagnosis"]).size().items()}
    folder_vs_patches = {
        f"{folder} / {diagnosis}": int(count)
        for (folder, diagnosis), count in lab[lab["sab_folder"] != ""].groupby(["sab_folder", "patch_diagnosis"]).size().items()
    }
    by_conflict = {reason: int(lab_pictures["group_conflicts"].str.contains(reason).sum()) for reason in (FOLDER_DIFFERS, LABELS_DIFFER)}
    by_patch = lab.set_index("patch_id")
    twin_summary = {
        "identical_patch_groups": len(identical_groups),
        "patches_with_an_identical_twin": len(identical),
        "group_sizes": pd.Series([len(ids) for ids in identical_groups], dtype=int).value_counts().sort_index().to_dict(),
        "groups_across_several_pictures": int(sum(by_patch.loc[ids, "histopath_id"].nunique() > 1 for ids in identical_groups)),
        "groups_across_several_cases": int(sum(by_patch.loc[ids, "case_pseudonym"].nunique() > 1 for ids in identical_groups)),
        "groups_with_different_labels": int(sum(by_patch.loc[ids, "patch_diagnosis"].nunique() > 1 for ids in identical_groups)),
    }
    case_sizes = cases.groupby("case_group").size()
    flag_counts = groups.flags["flag"].value_counts().to_dict()
    logger.info(f"SAB crop check: {crop_counts}")
    logger.info(f"Parent image check (template search against the SAB file name): {parent_counts}")
    logger.info(f"Patches with exactly the same pixels: {twin_summary}")
    logger.info(f"SAB folder against NDB-UFES diagnosis, pictures in both: {folder_vs_ndb}")
    logger.info(f"SAB folder against patch label, patches: {folder_vs_patches}")
    logger.info(f"Pictures whose group disagrees: {by_conflict}")
    logger.info(f"{len(cases)} cases form {case_sizes.size} groups; {int((case_sizes > 1).sum())} groups hold more than one case; flags {flag_counts}")
    logger.info(f"{len(lab)} patches in {lab['histopath_id'].nunique()} pictures; relation to the NDB-UFES diagnosis: {relation_counts}")
    logger.info(f"Public tables checked for identifying content: clean. Lab tables saved under {lab_dir}; public under {output_dir}")
    return {
        "patches": int(len(lab)),
        "pictures_with_patches": int(lab["histopath_id"].nunique()),
        "pictures_in_table": int(len(lab_pictures)),
        "pictures_without_patches": int((lab_pictures["n_patches"] == 0).sum()),
        "case_pseudonyms": int(lab["case_pseudonym"].nunique()),
        "patch_vs_picture_diagnosis": relation_counts,
        "pictures_with_a_more_severe_patch": int(lab.loc[lab["patch_vs_picture_diagnosis"] == MORE_SEVERE, "histopath_id"].nunique()),
        "sab_folder_vs_ndb_diagnosis": folder_vs_ndb,
        "sab_folder_vs_patch_diagnosis": folder_vs_patches,
        "pictures_whose_group_disagrees": by_conflict,
        "sab_crop_check": crop_counts,
        "parent_image_check": parent_counts,
        "identical_patches": twin_summary,
        "pictures_with_several_case_prefixes": int((lab.groupby("histopath_id")["case_prefix"].nunique() > 1).sum()),
        "patches_with_another_confirmed_picture": int((lab["other_confirmed_pictures"] > 0).sum()),
        "case_groups": int(case_sizes.size),
        "groups_with_more_than_one_case": int((case_sizes > 1).sum()),
        "case_group_flags": flag_counts,
    }


def build_patch_table_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the patch, picture and case tables, lab and public versions, with the checks and case groups.")
    add_source_arguments(parser)
    parser.add_argument("--ndb-metadata", type=Path, default=NDB_METADATA)
    parser.add_argument("--relations", type=Path, default=PICTURE_RELATIONS)
    parser.add_argument("--placements", type=Path, default=PATCH_PLACEMENTS)
    parser.add_argument("--pool-matches", type=Path, default=POOL_MATCHES)
    parser.add_argument("--sab-patches-dir", type=Path, default=SAB_PATCHES_DIR)
    parser.add_argument("--output-dir", type=Path, default=TABLES_DIR)
    return parser
