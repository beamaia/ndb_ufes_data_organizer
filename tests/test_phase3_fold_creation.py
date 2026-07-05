import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from src.phase3.phase3_fold_creation import (
    broadcast_to_patch_level,
    load_patch_metadata,
    stratum_round_robin_lpt_assignment,
    validate_folds,
)


class Phase3FoldCreationTests(unittest.TestCase):
    def test_load_patch_metadata_preserves_origin_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "patches.csv"
            pd.DataFrame({
                "origin": [0, 0, 1],
                "patch": ["0_a", "0_b", "1_a"],
                "diagnosis": ["A", "A", "B"],
            }).to_csv(path, index=False)

            loaded = load_patch_metadata(path, [0, 1])

        self.assertEqual(set(loaded["origin"]), {0, 1})
        self.assertEqual(len(loaded), 3)

    def test_load_patch_metadata_rejects_origin_set_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "patches.csv"
            pd.DataFrame({
                "origin": [0],
                "patch": ["0_a"],
                "diagnosis": ["A"],
            }).to_csv(path, index=False)

            with self.assertRaisesRegex(ValueError, "origin mismatch"):
                load_patch_metadata(path, [0, 1])

    def test_round_robin_lpt_is_deterministic_and_spreads_each_stratum(self):
        origins = pd.DataFrame({
            "origin_id": list(range(18)),
            "patch_count": [20, 8, 17, 9, 14, 11, 19, 7, 16, 10, 13, 12, 6, 5, 4, 3, 2, 1],
            "stratification_key": ["a"] * 11 + ["b"] * 7,
        })

        first = stratum_round_robin_lpt_assignment(origins)
        second = stratum_round_robin_lpt_assignment(origins.sample(frac=1, random_state=7))
        first_map = first.set_index("origin_id")["fold"].sort_index()
        second_map = second.set_index("origin_id")["fold"].sort_index()

        pd.testing.assert_series_equal(first_map, second_map)
        counts = pd.crosstab(first["fold"], first["stratification_key"])
        self.assertLessEqual(int((counts.max() - counts.min()).max()), 1)

    def test_validation_detects_origin_leakage(self):
        origins = pd.DataFrame({
            "origin_id": list(range(6)),
            "fold": list(range(6)),
            "stratification_key": ["a"] * 6,
        })
        patches = pd.DataFrame({
            "origin_id": list(range(6)) + [0],
            "fold": list(range(6)) + [1],
        })

        with self.assertRaisesRegex(ValueError, "spans multiple folds"):
            validate_folds(origins, patches, list(range(6)), max_patch_imbalance_ratio=2.0)

    def test_valid_assignment_has_no_leakage(self):
        origins = pd.DataFrame({
            "origin_id": list(range(12)),
            "patch_count": [2] * 12,
            "stratification_key": ["a"] * 6 + ["b"] * 6,
        })
        assigned = stratum_round_robin_lpt_assignment(origins)
        patch_source = pd.DataFrame({
            "origin": [origin for origin in range(12) for _ in range(2)],
            "patch": [f"{origin}_{index}" for origin in range(12) for index in range(2)],
            "diagnosis": ["A"] * 24,
        })
        patches = broadcast_to_patch_level(assigned, patch_source)

        report = validate_folds(assigned, patches, list(range(12)))

        self.assertEqual(report["max_folds_per_origin"], 1)
        self.assertEqual(report["max_stratum_fold_count_range"], 0)


if __name__ == "__main__":
    unittest.main()
