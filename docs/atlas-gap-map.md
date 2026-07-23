# Atlas Gap Map

This map separates the atlas evidence layer from the final Experiment 1/2
release. The public identifiers, release facts, canonical experiment manifest,
and public export are reconciled for v1.0.0; the remaining gaps concern future
metadata interpretation and byte-for-byte regeneration of the public atlas
PDF.

## Highest-priority gaps

| Priority | Gap | Evidence | What I need to do next | Status |
| --- | --- | --- | --- | --- |
| P1 | **Keep the two matching layers explicit.** The atlas reports 3,763/3,763 SAB-linked patches assigned to validated WSI IDs; the relationship table reports 3,086 rows matched to public NDB-UFES origin images plus 677 rows without a public NDB-UFES match. | `results/phase0/validated_linkage/validated_linkage_summary.json`; `results/phase3/current_thesis_batches/relationship_update_summary.json` | Use “SAB/atlas validated WSI linkage” for all 3,763 patches and “public NDB-UFES origin matching” for the 3,086/677 split. Do not collapse them into one count. | **Documented — no longer an unexplained contradiction** |
| P1 | **Set the public/private boundary.** The LAB atlas keeps raw SAB image names and case prefixes. | Comparison of the LAB PDF with the sanitized public PDF | Publish `NDB_UFES_SAB_atlas_public.pdf` at repository root; keep the LAB PDF and editable DOCX ignored; keep the large PDF outside the MkDocs payload. | **Implemented and validated for v1.0.0** |
| P1 | **Keep atlas provenance machine-readable.** | The phase-0 summary, thesis relationship summary, batch artifact manifest, generator script, public manifest, public schema, methods contract, conflict report, and release facts now exist as separate artifacts. | Regenerate the public assets after each validated phase-0 release and keep the source artifact paths/version recorded. | **Implemented — release maintenance remains** |
| P1 | **Keep metadata-conflict limits explicit.** The atlas summary flags 1,489 patch rows with metadata conflicts, even though complete NDB-UFES/SAB patch labels agree. | `results/phase0/validated_linkage/validated_linkage_summary.json`; [Metadata Conflict Review](metadata-conflict-review.md); [Atlas Index](atlas-index.md) | Preserve source labels side by side for future derived uses. Do not reinterpret the frozen Experiment 1/2 labels in v1.0.0. | **Release policy frozen; future interpretation remains open** |

## Content gaps

| Area | Already covered | Still missing or partial | Planned update |
| --- | --- | --- | --- |
| Definitions | The wiki explains origin, patch, fold, leakage, patient/case, and validated-WSI concepts. The [Data Dictionary](data-dictionary.md) now maps each question to its authoritative source, and the public atlas index has a versioned field contract. | A thesis-wide canonical schema and final label contract are still missing. | Keep the public atlas schema synchronized; add the broader schema after the metadata-conflict decision is frozen. |
| WSI linkage | The wiki documents current relationship files and matched-subset counts. The public PDF, index, manifest, schema, methods, and coordinate-derived area metrics now form a versioned atlas release contract. | These files still need to stay synchronized with the phase-0 inventory and the original panel renderer. | Use [Atlas Index](atlas-index.md), regenerate `docs/assets/atlas/` after a validated phase-0 run, and run both public atlas validators. |
| Evidence measures | The [Atlas Methods](atlas-methods.md) page and JSON contract now document coordinate recovery, IoU, fingerprints, LAB delta, pair-relation rules, current thresholds, and the three area denominators. | The original atlas panel renderer/configuration is not yet connected to the reusable helper. | Add the renderer/configuration version and a fixture comparison against an exported atlas panel before calling the full methods contract frozen. |
| Renderer provenance | The ignored editable source has `python-docx`/Word package metadata but no embedded generator reference; the repository builder path is known. The [Atlas Methods](atlas-methods.md) page now states the reproducibility boundary I can defend. | The exact script/configuration that produced the 587-page public atlas is not recoverable from the current package or repository search. | Recover the original renderer, or formally replace it with the tested builder and record the change before claiming reproducible PDF regeneration. |
| Source roles | Factsheet, data dictionary, public WSI index, and schema describe the public NDB-UFES + SAB versus SAB-only distinction. | No v1.0.0 field-level gap is known. | Keep the schema synchronized when the atlas inventory changes. |
| Labels | Wiki pages document three thesis classes and matched-subset counts. | The atlas mixes WSI labels, patch labels, and source labels in each WSI panel. | Document which label is used for training, which is retained as provenance, and how mixed-label WSIs are represented. |
| Navigation | The site has a clear pipeline/reference structure, and the thesis-batch, atlas guide, index, and gap map are now in navigation. | No current navigation gap is known. | Recheck navigation whenever a new release page is added. |

## Deployment and loading gaps

| Gap | Why it matters | Smallest safe fix |
| --- | --- | --- |
| The root public PDF is not a good default Pages payload. | A 587-page, 84.5 MB document would break the site's 55 MB gate and is harder to search. | Keep the public PDF at repository root; publish the guide, lightweight CSV index, and manifest through MkDocs. |
| Some legacy review assets are still heavy. | The largest files include a local-only 29 MB contamination PNG and a linked review PDF. They are not part of the atlas index. | The unused PNG is excluded from the public build; keep the linked review PDF only while it remains necessary evidence. Verify the complete site stays below the 55 MB release gate. |
| The console-script wrapper can be brittle across environments. | In this environment the `mkdocs` module was available even when the `mkdocs` executable wrapper was not discoverable. | Use `uv run --extra docs python -m mkdocs build --strict` for the reproducible build check; the current site passes it. |
| Generated artifacts have moved between historical and current result paths. | Stale links can make a polished page point at the wrong run. | Keep the current paths in one manifest and have the gap map or validation guide call out superseded paths. |
| Atlas provenance must stay machine-readable. | Reviewers need to verify that the web summary and public PDF describe the same 251-WSI scope. | Keep `atlas_manifest.json` and `atlas_schema.json` beside the public index, regenerate them with the release script, and run the root-PDF validator. |

## Suggested update order

1. Keep the two linkage layers named consistently across the factsheet and data dictionary.
2. Preserve the frozen v1.0.0 experiment labels while documenting metadata conflicts for future derived analyses.
3. Keep the root public PDF pseudonymous and rerun its privacy validator after every export.
4. Regenerate the public index, manifest, and schema after each validated phase-0 release.
5. Expand the data dictionary and factsheet from the reconciled fields.
6. Add richer WSI browsing only if the index proves useful; keep the main site text-first and fast.

## What I am deliberately not doing yet

- I am not copying the 84.5 MB public PDF into the MkDocs payload.
- I am not publishing the LAB PDF or editable DOCX source.
- I am not calling the atlas's 3,763/3,763 SAB linkage the public NDB-UFES
  origin-match count; it is canonical for the atlas WSI-evidence layer.
- I am not generating 251 standalone WSI pages when one lightweight index is enough for lookup.
- I am not treating visual fingerprint similarity or overlap as evidence of diagnostic equivalence.

That restraint is part of the update plan: close the identity and provenance questions first, then expand the public surface area.
