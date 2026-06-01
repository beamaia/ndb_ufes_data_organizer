# Contamination Checks

This page records image-level checks used to inspect possible contamination, duplicate-like patches, and origin-patch matching behavior. These checks are exploratory quality-control material and should be reviewed before final fold publication.

## Purpose

The contamination checks are intended to answer practical data-organization questions:

- whether visually similar patches are duplicates or near-duplicates;
- whether patches can be traced back to the expected origin image;
- whether suspicious examples require exclusion, relabeling, or documentation;
- whether fold construction needs extra safeguards beyond origin-level grouping.

## Example Patch Comparison

The comparison below illustrates a suspicious or informative patch-pair case used during manual review.

![Contaminated patches comparison](assets/contamination/contaminated_patches_comparison.png)

## Origin Patch Grid

Patch grids help inspect whether patch samples align with the expected origin image.

![Origin patch grid](assets/contamination/origin_0011_patch_grid.png)

## Similarity Matrix

Similarity matrices are used to spot unusually similar patch groups that may require manual inspection.

![Similarity matrix](assets/contamination/similarity_matrix_0011.png)

## Test Case

This test case is retained as an example of the contamination-check workflow.

![Patch test case](assets/contamination/p0020_p0021_test_case.png)

## WIP Notes

The current figures live under `results/phase0_contamination_analysis/`. They are not final exclusion criteria by themselves. Before finalizing folds, confirm which suspicious cases are accepted, excluded, or documented, and make sure any decisions are reflected in the data dictionary and reproducibility notes.
