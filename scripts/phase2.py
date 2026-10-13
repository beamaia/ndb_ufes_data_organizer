from __future__ import annotations

import argparse
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.phase2_report.atlas import (
    render_aligned_atlas_arg_parser, render_patient_atlas_arg_parser, run_render_aligned_atlas, run_render_patient_atlas,
)
from src.phase2_report.figures import figures_arg_parser, run_figures
from src.phase2_report.pages import pages_arg_parser, run_pages
from src.phase2_report.stats import run_stats, stats_arg_parser


COMMANDS = {
    "patient-atlas": ("PDF of case groups: pictures, patch boxes, each patch beside its crop", render_patient_atlas_arg_parser, run_render_patient_atlas),
    "aligned-atlas": ("PDF of related pictures rotated into one frame", render_aligned_atlas_arg_parser, run_render_aligned_atlas),
    "stats": ("Every table and statistic as a CSV file", stats_arg_parser, run_stats),
    "figures": ("The SVG charts of the wiki", figures_arg_parser, run_figures),
    "pages": ("The generated wiki pages", pages_arg_parser, run_pages),
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
