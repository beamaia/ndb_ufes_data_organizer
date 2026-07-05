import pandas as pd

ORIGIN_MAPPING_PATH = "data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv"
FOLD_ASSIGNMENTS_PATH = "data/ndb_ufes/patch_level/csvs/fold_assignments_patch_level_detailed.csv"
OUTPUT_PATH = "data/ndb_ufes/patch_level/csvs/fold_assignments_patch_level_with_images.csv"
OUTPUT_COLUMNS = [
    "patch_id",
    "origin_id",
    "image_name",
    "image_path",
    "class",
    "morph_cluster",
    "fold",
]


def build_patch_mapping(origin_mapping):
    mapping = {}
    for _, row in origin_mapping.iterrows():
        origin_id = int(row["origin_id"])
        patch_names = [patch.strip() for patch in str(row["patch_ids"]).split(",")]
        image_paths = [path.strip() for path in str(row["image_paths"]).split("|")]
        mapping[origin_id] = list(zip(patch_names, image_paths))
    return mapping


def lookup_patch_image(row, patch_mapping):
    origin_id = int(row["origin_id"])
    patch_idx = int(row["patch_id"].split("_")[1])
    if origin_id not in patch_mapping or patch_idx >= len(patch_mapping[origin_id]):
        return "MISSING", "MISSING"
    return patch_mapping[origin_id][patch_idx]


def main():
    origin_mapping = pd.read_csv(ORIGIN_MAPPING_PATH)
    fold_assignments = pd.read_csv(FOLD_ASSIGNMENTS_PATH)
    patch_mapping = build_patch_mapping(origin_mapping)
    image_records = [
        lookup_patch_image(row, patch_mapping)
        for _, row in fold_assignments.iterrows()
    ]

    fold_assignments["image_name"] = [record[0] for record in image_records]
    fold_assignments["image_path"] = [record[1] for record in image_records]
    fold_assignments = fold_assignments[OUTPUT_COLUMNS]
    fold_assignments.to_csv(OUTPUT_PATH, index=False)

    missing_count = (fold_assignments["image_name"] == "MISSING").sum()
    print(f"Enhanced fold assignments created: {len(fold_assignments)} patches")
    print(f"Columns: {list(fold_assignments.columns)}")
    print("\nSample rows:")
    print(fold_assignments.head(3).to_string())
    print(f"\nMissing mappings: {missing_count}")


if __name__ == "__main__":
    main()
