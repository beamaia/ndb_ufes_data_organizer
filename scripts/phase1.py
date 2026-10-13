from __future__ import annotations

import argparse
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.phase1_folds.clusters import (
    cluster_choices_arg_parser, cluster_view_arg_parser, patch_clusters_arg_parser, run_cluster_choices, run_cluster_view,
    run_patch_clusters,
)
from src.phase1_folds.embeddings import patch_embeddings_arg_parser, run_patch_embeddings
from src.phase1_folds.folds import folds_arg_parser, run_folds


COMMANDS = {
    "cluster-choices": ("How well separated the patch embeddings cluster, for each choice", cluster_choices_arg_parser, run_cluster_choices),
    "cluster-view": ("Picture of the clusters: by label, by cluster, by silhouette", cluster_view_arg_parser, run_cluster_view),
    "patch-clusters": ("Cluster the patches and show what each cluster is made of", patch_clusters_arg_parser, run_patch_clusters),
    "patch-embeddings": ("Virchow embedding of every patch", patch_embeddings_arg_parser, run_patch_embeddings),
    "folds": ("Folds over the case groups", folds_arg_parser, run_folds),
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
