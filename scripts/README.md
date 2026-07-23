# Scripts

Top-level scripts are phase entrypoints only.

- `phase0.py`: audit, SAB consistency, coordinate recovery, validated linkage, and release-table helpers.
- `phase1.py`: feature extraction.
- `phase2.py`: tuning/model selection.
- `phase3.py`: fold creation.
- `phase4.py`: later analysis/interpretability helpers.
- `src/`: implementation modules.

To search for scaled or cropped relationships only among distinct WSI/origin
images with the same explicitly linked patient ID:

```bash
uv run python scripts/phase0.py same-patient-wsi
```

The audit writes `results/phase0/validated_linkage/same_patient_wsi_image_relationships.csv`.
Use `--patient-id VALUE` to restrict the search while testing, and inspect rows
with `candidate=True` before doing any larger visual review.

Research-facing copied tables live in `../research_ready_tables/`.
