from __future__ import annotations

import argparse
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.phase0_dataset_builder.cases import build_patch_table_arg_parser, run_build_patch_table
from src.phase0_dataset_builder.patch_links import (
    place_patches_arg_parser, run_place_patches, run_search_patches_in_pictures, search_patches_in_pictures_arg_parser,
)
from src.phase0_dataset_builder.pictures import extract_picture_features_arg_parser, relate_pictures_arg_parser, run_extract_picture_features, run_relate_pictures


COMMANDS = {
    "picture-features": ("SIFT features per picture", extract_picture_features_arg_parser, run_extract_picture_features),
    "picture-relations": ("Geometric relations between pictures", relate_pictures_arg_parser, run_relate_pictures),
    "patch-pool-search": ("Search every patch in every picture by template matching", search_patches_in_pictures_arg_parser, run_search_patches_in_pictures),
    "patch-placements": ("Patch projection into related pictures", place_patches_arg_parser, run_place_patches),
    "patch-table": ("Patch, picture and case tables (lab and public) with all checks and the case groups", build_patch_table_arg_parser, run_build_patch_table),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=sorted(COMMANDS))
    args, remaining = parser.parse_known_args()
    label, arg_parser_factory, runner = COMMANDS[args.command]
    command_args = arg_parser_factory().parse_args(remaining)
    summary = runner(command_args)
    print(f"{label} complete")
    for key, value in summary.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
