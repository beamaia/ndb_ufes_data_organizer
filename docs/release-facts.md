# Current Release Facts

I use this page as the quick scope check for the current wiki release. It brings the atlas, thesis relationship layer, and experiment batches together without pretending that they are one dataset table.

The machine-readable source is the [public release facts JSON](assets/atlas/release_facts.json). The JSON is generated from the validated atlas summary, the current relationship summary, and the thesis batch artifact manifest, then checked by the public atlas validator.

## Scope at a glance

| Layer | Current value | What it answers | Authoritative source |
| --- | ---: | --- | --- |
| Full P-NDB-UFES thesis starting scope | 3,763 patch rows | Which rows the final experiments start from | [Thesis Experiment Design](thesis-experiment-batches.md) |
| SAB-linked relationship scope | 3,086 linked + 677 missing-linkage rows | Which rows have recovered metadata linkage for the thesis relationship layer | [Data Dictionary](data-dictionary.md#current-thesis-linkage-counts) |
| Atlas validated-WSI scope | 251 validated WSIs covering 3,763 patches | Where the atlas places patches using recovered WSI evidence | [Atlas Index](atlas-index.md) |
| Atlas source roles | 203 public NDB-UFES + SAB / 48 SAB-only | What kind of source evidence supports each validated WSI | [Atlas Guide](atlas-guide.md#atlas-snapshot) |
| Atlas metadata-conflict cohort | 1,489 patch rows | Which atlas rows require metadata caution | [Metadata Conflict Review](metadata-conflict-review.md) |

The practical rule is simple: **3,763** is the full thesis starting scope, **3,086/677** describes thesis metadata linkage, and **251** describes the atlas WSI layer. I do not use one of these numbers as a substitute for another.

## Current thesis batches

| Batch | Patch rows | Fold counts, 0–5 | Origin leaks | Patient/case leaks | Use |
| --- | ---: | --- | ---: | ---: | --- |
| Batch 1 / Experiment 1 | 3,763 | 628/627/627/627/627/627 | 201 | 61 | Final original-comparable split; retains known contamination risk. |
| Batch 2 / Experiment 2 | 3,763 | 627/631/627/626/626/626 | 0 | 0 | Final patient-first grouped, lower-contamination-risk split. |
| Batch 3 | 3,351 | 566/552/544/553/556/580 | 0 | 0 | Exploratory archive only; not part of the final thesis comparison. |

These are experiment-batch facts, not atlas facts. The final comparison uses
only Experiments 1 and 2. The full design, class totals, archived pruning rule,
and metadata caveats are on [Thesis Experiment Design](thesis-experiment-batches.md).

## Atlas evidence snapshot

- All 3,763 represented patches have recovered coordinates and a validated WSI ID.
- The atlas reports complete NDB-UFES/SAB patch-label agreement for all 3,763 rows.
- The public index contains 30,531 theoretical coordinate-derived same-WSI patch pairs and 29,350 available similarity rows.
- The public export keeps raw SAB case prefixes, image names, and local paths out of the web payload.

These are placement and provenance facts. They do not make visual similarity a diagnosis, and they do not resolve the separate reconstructed-metadata disagreements.

## Release boundary

The final Experiment 1/2 training labels, folds, parameters, and stored metrics
are frozen for v1.0.0. The metadata-conflict policy in
[Metadata Conflict Review](metadata-conflict-review.md) remains relevant to
future derived uses, but it does not reopen the recorded experiment results.
The original atlas DOCX renderer is still needed before claiming byte-for-byte
DOCX regeneration; that separate boundary is documented in
[Atlas Methods](atlas-methods.md#reproducibility-boundary-i-can-defend-today).

The full update order is maintained in the [Atlas Gap Map](atlas-gap-map.md).

## Refresh and verify

From a checkout with the validated phase-0 and thesis-batch artifacts:

```bash
uv run python scripts/src/release/build_atlas_public_index.py
uv run python scripts/src/release/validate_atlas_public_index.py
uv run python scripts/src/release/build_canonical_experiment_release.py
uv run python scripts/src/release/generate_research_ready_tables.py --profile public
uv run --extra docs python -m mkdocs build --strict
```

The public site only needs the committed files under `docs/assets/atlas/`; it
does not load the root-level public PDF. The LAB PDF, editable DOCX, and
private SAB crosswalk are not public release inputs.
