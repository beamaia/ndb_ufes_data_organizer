# Atlas Index

This is the lightweight, public index for the root-level
`NDB_UFES_SAB_atlas_public.pdf`. It gives the wiki one searchable row per
validated WSI without loading the 587-page PDF into the Pages payload or
exposing raw SAB case prefixes, image names, or local filesystem paths.

## What is in the index

The index contains:

- a pseudonymous `validated_wsi_id`;
- whether the WSI has public NDB-UFES + SAB evidence or is SAB-only recovered;
- patch count and source-level labels;
- coordinate-derived patch-pair and coverage metrics;
- the distinction between theoretical coordinate pairs and available similarity rows;
- aggregate patch-label counts;
- evidence summaries and metadata-conflict counts.
- a small machine-readable release-facts file for the atlas, thesis relationship scope, and current batch validation totals.

It does not contain the LAB-only crosswalk. The excluded private fields are recorded in the [atlas manifest](assets/atlas/atlas_manifest.json).

The field names, types, nullability, source-role values, and CSV encodings are recorded in the [public atlas schema](assets/atlas/atlas_schema.json). This is the schema for the public atlas index only; it does not settle which competing metadata label should be used in a thesis experiment.

## Current atlas counts

| Measure | Count |
| --- | ---: |
| Patch rows in atlas linkage | 3,763 |
| Patches with recovered coordinates | 3,763 |
| Patches with a validated WSI ID | 3,763 |
| Validated WSI groups | 251 |
| Public NDB-UFES + SAB WSI groups | 203 |
| SAB-only recovered WSI groups | 48 |
| WSI rows with coordinate-derived area metrics | 251 |
| Patch-label agreement rows | 3,763 |
| All coordinate-derived same-WSI patch pairs | 30,531 |
| Same-WSI similarity rows available | 29,350 |

The current relationship table has a different field of view: 3,086 rows have recovered public metadata linkage and 677 rows are retained with missing metadata linkage. That does not reduce the atlas WSI count; it describes the metadata status used by the thesis batch grouping. See [Atlas Guide](atlas-guide.md#two-linkage-layers) for the distinction.

The coverage fields in each WSI row are calculated from the recovered coordinate boxes and displayed WSI dimensions. `patch_pair_count` is the theoretical `n × (n - 1) / 2` coordinate-pair count; `similarity_pair_count` records how many rows are present in the validated similarity artifact. See [Atlas Methods](atlas-methods.md#atlas-panel-area-measures) for the denominators and [Metadata Conflict Review](metadata-conflict-review.md) for the separate label-status problem.

## Downloads

- [Validated WSI index (CSV)](assets/atlas/validated_wsi_index.csv)
- [Atlas manifest (JSON)](assets/atlas/atlas_manifest.json)
- [Public atlas schema (JSON)](assets/atlas/atlas_schema.json)
- [Metadata-conflict summary (JSON)](assets/atlas/metadata_conflict_summary.json)
- [Atlas methods contract (JSON)](assets/atlas/atlas_methods.json)
- [Public release facts (JSON)](assets/atlas/release_facts.json)

The index is generated from `results/phase0/validated_linkage/validated_wsi_inventory.csv` with:

```bash
uv run python scripts/src/release/build_atlas_public_index.py
```

The committed public export can be checked without private data or the local phase-0 result tree:

```bash
uv run python scripts/src/release/validate_atlas_public_index.py
```

The manifest records the source artifacts, privacy mode, scope counts, and excluded private fields; the schema records the public field contract. Together, these files let the web summary be checked against the atlas generation inputs without loading the LAB crosswalk.

!!! warning "Interpretation"
    A validated WSI ID means the patch was assigned to a WSI through the atlas linkage evidence, including recovered coordinates. It does not mean that every thesis metadata field is available or that all source-level labels agree. The index keeps those distinctions visible.
