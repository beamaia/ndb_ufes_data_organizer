import sys
import unittest
from pathlib import Path

import pandas as pd


sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from src.phase2.phase2_save_params import select_optimal_params


class Phase2SelectionTests(unittest.TestCase):
    def test_rejects_degenerate_high_silhouette_clustering(self):
        results = pd.DataFrame([
            {
                "pca_components": 2,
                "kmeans_clusters": 2,
                "silhouette_mean": 0.97,
                "silhouette_std": 0.0,
                "pca_explained_var": 0.80,
                "inertia_mean": 10.0,
                "inertia_std": 0.0,
                "runs": 5,
                "min_cluster_size_min": 1,
                "min_cluster_size_mean": 1.0,
                "max_cluster_size_max": 202,
                "max_cluster_size_mean": 202.0,
                "cluster_size_ratio_max": 202.0,
                "cluster_size_ratio_mean": 202.0,
            },
            {
                "pca_components": 2,
                "kmeans_clusters": 3,
                "silhouette_mean": 0.66,
                "silhouette_std": 0.01,
                "pca_explained_var": 0.75,
                "inertia_mean": 20.0,
                "inertia_std": 1.0,
                "runs": 5,
                "min_cluster_size_min": 35,
                "min_cluster_size_mean": 35.0,
                "max_cluster_size_max": 101,
                "max_cluster_size_mean": 101.0,
                "cluster_size_ratio_max": 101 / 35,
                "cluster_size_ratio_mean": 101 / 35,
            },
        ])

        selected = select_optimal_params(results, 42, 11, 5.0)

        self.assertEqual(selected["kmeans_clusters"], 3)
        self.assertEqual(selected["min_cluster_size"], 35)
        self.assertLessEqual(selected["max_cluster_size_ratio"], 5.0)

    def test_raises_when_no_configuration_is_eligible(self):
        results = pd.DataFrame([{
            "pca_components": 2,
            "kmeans_clusters": 2,
            "silhouette_mean": 0.97,
            "silhouette_std": 0.0,
            "pca_explained_var": 0.80,
            "inertia_mean": 10.0,
            "inertia_std": 0.0,
            "runs": 5,
            "min_cluster_size_min": 1,
            "min_cluster_size_mean": 1.0,
            "max_cluster_size_max": 202,
            "max_cluster_size_mean": 202.0,
            "cluster_size_ratio_max": 202.0,
            "cluster_size_ratio_mean": 202.0,
        }])

        with self.assertRaisesRegex(ValueError, "No clustering configuration"):
            select_optimal_params(results, 42, 11, 5.0)


if __name__ == "__main__":
    unittest.main()
