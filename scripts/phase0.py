#!/usr/bin/env python3
"""Run Phase 0 validation, linkage, and release-table commands."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.phase0.dataset_alignment_report import dataset_alignment_report_arg_parser, run_dataset_alignment_report
from src.phase0.missing_patch_similarity import missing_patch_similarity_arg_parser, run_missing_patch_similarity
from src.phase0.patch_coherence_report import patch_coherence_report_arg_parser, run_patch_coherence_report
from src.phase0.patch_origin_registration import registration_arg_parser, run_registration_validation
from src.phase0.patch_similarity import run_similarity_plan, similarity_arg_parser
from src.phase0.recovery_validation import balance_arg_parser, recovery_arg_parser, run_balance_validation, run_recovery_validation
from src.phase0.review_packets import review_packet_arg_parser, run_review_packet
from src.phase0.sab_consistency_validation import run_sab_consistency_validation, sab_consistency_arg_parser
from src.phase0.sab_patch_coordinate_recovery import run_sab_patch_coordinate_recovery, sab_patch_coordinate_recovery_arg_parser
from src.phase0.same_patient_wsi_image_relationships import parser as same_patient_wsi_arg_parser, run_same_patient_wsi_relationships
from src.phase0.validated_linkage import run_validated_linkage, validated_linkage_arg_parser


COMMANDS = {
    "recovery-validation": ("Patch-origin recovery validation", recovery_arg_parser, run_recovery_validation),
    "balance-validation": ("Origin patch balance validation", balance_arg_parser, run_balance_validation),
    "sab-consistency": ("SAB consistency validation", sab_consistency_arg_parser, run_sab_consistency_validation),
    "recover-coordinates": ("SAB patch coordinate recovery", sab_patch_coordinate_recovery_arg_parser, run_sab_patch_coordinate_recovery),
    "validated-linkage": ("Validated patch-to-WSI linkage", validated_linkage_arg_parser, run_validated_linkage),
    "alignment-report": ("Dataset alignment report", dataset_alignment_report_arg_parser, run_dataset_alignment_report),
    "missing-review": ("Missing patch review packet", review_packet_arg_parser, run_review_packet),
    "missing-similarity": ("Missing patch similarity groups", missing_patch_similarity_arg_parser, run_missing_patch_similarity),
    "registration-validation": ("Patch-origin registration validation", registration_arg_parser, run_registration_validation),
    "similarity-plan": ("Patch similarity plan", similarity_arg_parser, run_similarity_plan),
    "patch-coherence-report": ("Patch coherence report", patch_coherence_report_arg_parser, run_patch_coherence_report),
    "same-patient-wsi": ("Same-patient WSI image relationship validation", same_patient_wsi_arg_parser, run_same_patient_wsi_relationships),
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
