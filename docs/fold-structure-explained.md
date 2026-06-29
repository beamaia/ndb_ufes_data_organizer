# Understanding Fold Structure

## Origins and Patches

The matched subset contains 203 origins and 3,086 image patches. An origin is the parent specimen image; each origin contributes multiple patches. Origin `0` is a valid parent with 20 patches.

The core invariant is:

```text
one origin_id -> one fold
```

All patches inherit the fold of their parent origin. Randomly splitting patch rows would leak specimen-specific information between training and evaluation.

## Why Six Folds

Six folds retain enough origins per evaluation split while allowing each supported diagnosis, morphology cluster, gender, and age group to be spread throughout the cross-validation structure. Six is a project design choice, not a claim that it is universally optimal.

## Morphology Signal

Phase 2 selected frozen Virchow embeddings with PCA=2 and K=3. The morphology clusters contain 101, 67, and 35 origins. Configurations are not accepted unless every cluster has at least 11 origins and the largest/smallest ratio is at most 5.

This feature use does not by itself prevent the same backbone from being trained later. The leakage boundary is procedural: do not fine-tune it on the full labeled dataset before fold construction, and do not choose folds based on downstream validation/test results.

## Combined Strata

Phase 3 combines:

- origin diagnosis;
- morphology cluster;
- gender;
- age group.

All four passed missingness and six-fold support checks in the current run. Other clinical fields remain descriptive.

## Round-Robin LPT

Within each combined stratum, origins are sorted by patch count, largest first. Successive blocks of six are assigned to six distinct folds. At each step, Phase 3 chooses the least-loaded unused fold, then breaks ties by origin count and fold ID.

This differs from global greedy LPT: a complete six-origin block cannot place two origins into the same fold. Consequently, the count of any combined stratum differs by no more than one across folds.

## Validated Result

| Fold | Origins | Patches |
| ---: | ---: | ---: |
| 0 | 31 | 520 |
| 1 | 36 | 510 |
| 2 | 31 | 511 |
| 3 | 34 | 511 |
| 4 | 37 | 524 |
| 5 | 34 | 510 |

The maximum/minimum patch ratio is 1.02745. No origin spans folds, no row is unassigned, and every combined stratum has a fold-count range at most one.

Use `fold_assignments_patch_level.csv` for patch training rows and `fold_assignments_origin.csv` for origin-level analysis. Fold rotation should be declared before comparing downstream models.
