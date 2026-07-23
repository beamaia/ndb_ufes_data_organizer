#!/usr/bin/env python3
"""Generate final-only wiki and thesis figures from the public experiment CSVs."""

from __future__ import annotations

import csv
import hashlib
import html
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TABLE_DIR = ROOT / "release/v1.0.0/public/tables"
OUTPUT_DIR = ROOT / "docs/assets/factsheet"
THESIS_OUTPUT_DIR = ROOT / "results/phase4/thesis_figures"

EXPERIMENTS = {
    "Experiment 1": {
        "subtitle": "Released patch-level reference split",
        "path": TABLE_DIR / "experiment1_patch_assignments.csv",
    },
    "Experiment 2": {
        "subtitle": "Patient-first grouped split",
        "path": TABLE_DIR / "experiment2_patch_assignments.csv",
    },
}
SOURCE_INDEX = TABLE_DIR / "validated_wsi_index.csv"

EXPECTED_PATCHES = 3_763
EXPECTED_SOURCE_IMAGES = 251
EXPECTED_DIAGNOSES = {
    "OSCC": 1_126,
    "Leukoplakia with dysplasia": 1_930,
    "Leukoplakia without dysplasia": 707,
}
EXPECTED_SOURCE_SUMMARY = {
    "both": {"groups": 203, "patches": 3_111},
    "SAB-only recovered WSI": {"groups": 48, "patches": 652},
}
DISTRIBUTION_FIELDS = {
    "age_group",
    "alcohol_consumption",
    "dysplasia_severity",
    "gender",
    "lesion_size",
    "localization",
    "skin_color",
    "sun_exposure",
    "tobacco_use",
}

CLASS_ORDER = (
    "OSCC",
    "Leukoplakia with dysplasia",
    "Leukoplakia without dysplasia",
)
CLASS_COLORS = {
    "OSCC": "#d95f02",
    "Leukoplakia with dysplasia": "#087fbd",
    "Leukoplakia without dysplasia": "#009b72",
}
SOURCE_COLORS = {
    "both": "#365cc1",
    "SAB-only recovered WSI": "#60aa26",
}
DISTRIBUTION_COLORS = ("#365cc1", "#60aa26", "#f5b700")
NOT_INFORMED_COLOR = "#aab3c2"
FIGURE_TITLES = {
    "clinical_distributions.svg": "Public-linked clinical distributions",
    "demographic_distributions.svg": "Public-linked demographic distributions",
    "diagnosis_distribution.svg": "Final three-class patch distribution",
    "exposure_distributions.svg": "Public-linked exposure distributions",
    "fold_class_distribution.svg": "Class distribution across the six folds",
    "source_image_linkage.svg": "Final source-image linkage",
}
STATIC_THESIS_FIGURES = (
    {
        "stem": "phase2_model_selection",
        "title": "Phase 2 model selection",
        "scope": "model-selection analysis",
        "source": "results/phase2/tuning/phase2_model_selection.csv",
    },
    {
        "stem": "origin_0011_overlap_bbox",
        "title": "Source-image 0011 overlap bounding boxes",
        "scope": "contamination-review example",
        "source": (
            "data/ndb_ufes/patch_level/images/p0020.png; "
            "data/ndb_ufes/patch_level/images/p0021.png"
        ),
    },
)


def read_csv(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = required_columns.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} is missing columns: {sorted(missing)}")
        return list(reader)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_inputs() -> tuple[
    dict[str, list[dict[str, str]]],
    list[dict[str, str]],
]:
    experiment_rows: dict[str, list[dict[str, str]]] = {}
    reference_diagnoses: dict[str, str] | None = None
    reference_attributes: dict[str, tuple[str, ...]] | None = None

    for experiment, definition in EXPERIMENTS.items():
        path = definition["path"]
        rows = read_csv(
            path,
            {
                "patch_id",
                "diagnosis",
                "fold",
                "role",
                "public_wsi_id",
                *DISTRIBUTION_FIELDS,
            },
        )
        require(
            len(rows) == EXPECTED_PATCHES,
            f"{path} contains {len(rows):,} rows, expected {EXPECTED_PATCHES:,}",
        )
        patch_ids = [row["patch_id"] for row in rows]
        require(
            len(set(patch_ids)) == len(patch_ids) and all(patch_ids),
            f"{path} contains blank or duplicate patch IDs",
        )
        diagnoses = {row["patch_id"]: row["diagnosis"] for row in rows}
        require(
            Counter(diagnoses.values()) == Counter(EXPECTED_DIAGNOSES),
            f"{path} does not contain the final diagnosis totals",
        )
        if reference_diagnoses is None:
            reference_diagnoses = diagnoses
        else:
            require(
                diagnoses == reference_diagnoses,
                "The experiment CSVs do not contain identical patch IDs and diagnoses",
            )
        attributes = {
            row["patch_id"]: tuple(row[field] for field in sorted(DISTRIBUTION_FIELDS))
            for row in rows
        }
        if reference_attributes is None:
            reference_attributes = attributes
        else:
            require(
                attributes == reference_attributes,
                "The experiment CSVs do not contain identical public distribution fields",
            )

        folds = {int(row["fold"]) for row in rows}
        require(folds == set(range(6)), f"{path} must contain folds 0 through 5")
        for row in rows:
            expected_role = (
                "held_out_test" if int(row["fold"]) == 5 else "cross_validation"
            )
            require(
                row["role"] == expected_role,
                f"{path} has an invalid fold/role pair for {row['patch_id']}",
            )
        experiment_rows[experiment] = rows

    source_rows = read_csv(
        SOURCE_INDEX,
        {
            "validated_wsi_id",
            "source",
            "patch_count",
            "patches_oscc",
            "patches_with_dysplasia",
            "patches_without_dysplasia",
            "patch_labels_unavailable",
        },
    )
    require(
        len(source_rows) == EXPECTED_SOURCE_IMAGES,
        f"{SOURCE_INDEX} contains {len(source_rows):,} rows, expected "
        f"{EXPECTED_SOURCE_IMAGES:,}",
    )
    source_ids = [row["validated_wsi_id"] for row in source_rows]
    require(
        len(set(source_ids)) == len(source_ids) and all(source_ids),
        f"{SOURCE_INDEX} contains blank or duplicate source-image IDs",
    )
    require(
        sum(int(row["patch_count"]) for row in source_rows) == EXPECTED_PATCHES,
        f"{SOURCE_INDEX} does not account for all final patches",
    )

    for source, expected in EXPECTED_SOURCE_SUMMARY.items():
        selected = [row for row in source_rows if row["source"] == source]
        require(
            len(selected) == expected["groups"],
            f"{SOURCE_INDEX} has an unexpected number of {source!r} groups",
        )
        require(
            sum(int(row["patch_count"]) for row in selected) == expected["patches"],
            f"{SOURCE_INDEX} has an unexpected {source!r} patch total",
        )
    require(
        {row["source"] for row in source_rows} == set(EXPECTED_SOURCE_SUMMARY),
        f"{SOURCE_INDEX} contains an unexpected source-image role",
    )

    index_patch_counts = {
        row["validated_wsi_id"]: int(row["patch_count"]) for row in source_rows
    }
    assignment_patch_counts = Counter(
        row["public_wsi_id"] for row in experiment_rows["Experiment 2"]
    )
    require(
        assignment_patch_counts == Counter(index_patch_counts),
        "The source-image index does not match the experiment assignments",
    )

    index_diagnoses = {
        "OSCC": sum(int(row["patches_oscc"]) for row in source_rows),
        "Leukoplakia with dysplasia": sum(
            int(row["patches_with_dysplasia"]) for row in source_rows
        ),
        "Leukoplakia without dysplasia": sum(
            int(row["patches_without_dysplasia"]) for row in source_rows
        ),
    }
    require(
        index_diagnoses == EXPECTED_DIAGNOSES,
        "The source-image index and experiment diagnosis totals differ",
    )
    require(
        sum(int(row["patch_labels_unavailable"]) for row in source_rows) == 0,
        "The final source-image index contains unavailable patch labels",
    )
    return experiment_rows, source_rows


def svg_document(
    title: str,
    description: str,
    width: int,
    height: int,
    body: list[str],
) -> str:
    title_id = "figure-title"
    description_id = "figure-description"
    return "\n".join(
        [
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
                f'height="{height}" viewBox="0 0 {width} {height}" role="img" '
                f'aria-labelledby="{title_id} {description_id}" fill="#17315f">'
            ),
            f'<title id="{title_id}">{html.escape(title)}</title>',
            f'<desc id="{description_id}">{html.escape(description)}</desc>',
            '<rect width="100%" height="100%" rx="14" fill="#ffffff"/>',
            (
                '<style>text { font-family: Inter, Arial, sans-serif; }</style>'
            ),
            *body,
            "</svg>",
            "",
        ]
    )


def write_svg(name: str, content: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    THESIS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / name).write_text(content, encoding="utf-8")
    (THESIS_OUTPUT_DIR / name).write_text(content, encoding="utf-8")


def generate_diagnosis_distribution(
    rows: list[dict[str, str]],
) -> None:
    counts = Counter(row["diagnosis"] for row in rows)
    width, height = 960, 500
    chart_left, chart_right = 325, 900
    chart_width = chart_right - chart_left
    axis_max = 2_000
    body = [
        (
            '<text x="480" y="44" text-anchor="middle" font-size="25" '
            'font-weight="700">Final three-class patch distribution</text>'
        ),
        (
            f'<text x="480" y="72" text-anchor="middle" font-size="14" '
            f'fill="#51617e">{EXPECTED_PATCHES:,} patches in each experiment</text>'
        ),
    ]
    for tick in range(0, axis_max + 1, 500):
        x = chart_left + chart_width * tick / axis_max
        body.extend(
            [
                (
                    f'<line x1="{x:.1f}" y1="105" x2="{x:.1f}" y2="410" '
                    'stroke="#e7ecf5" stroke-width="1"/>'
                ),
                (
                    f'<text x="{x:.1f}" y="434" text-anchor="middle" '
                    f'font-size="12" fill="#51617e">{tick:,}</text>'
                ),
            ]
        )
    for index, diagnosis in enumerate(CLASS_ORDER):
        y = 135 + index * 95
        value = counts[diagnosis]
        bar_width = chart_width * value / axis_max
        body.extend(
            [
                (
                    f'<text x="{chart_left - 18}" y="{y + 25}" text-anchor="end" '
                    f'font-size="14">{html.escape(diagnosis)}</text>'
                ),
                (
                    f'<rect x="{chart_left}" y="{y}" width="{bar_width:.1f}" '
                    f'height="40" rx="5" fill="{CLASS_COLORS[diagnosis]}"/>'
                ),
                (
                    f'<text x="{chart_left + bar_width + 12:.1f}" y="{y + 26}" '
                    f'font-size="14" font-weight="700">{value:,}</text>'
                ),
            ]
        )
    body.append(
        '<text x="612" y="472" text-anchor="middle" font-size="13" '
        'fill="#51617e">Patch count</text>'
    )
    write_svg(
        "diagnosis_distribution.svg",
        svg_document(
            "Final three-class patch distribution",
            "Bar chart showing 1,126 OSCC patches, 1,930 leukoplakia with "
            "dysplasia patches, and 707 leukoplakia without dysplasia patches.",
            width,
            height,
            body,
        ),
    )


def ordered_counts(
    rows: list[dict[str, str]],
    field: str,
    order: tuple[str, ...],
    labels: dict[str, str] | None = None,
) -> list[tuple[str, int]]:
    counts = Counter((row[field].strip() or "Not informed") for row in rows)
    ordered_values = [value for value in order if value in counts]
    ordered_values.extend(sorted(set(counts).difference(ordered_values)))
    display_labels = labels or {}
    return [
        (display_labels.get(value, value), counts[value])
        for value in ordered_values
    ]


def grouped_lesion_size_counts(
    rows: list[dict[str, str]],
) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    for row in rows:
        value = row["lesion_size"].strip()
        if not value or value == "Not informed":
            counts["Not informed"] += 1
            continue
        numeric_value = float(value)
        if numeric_value == 0:
            counts["0"] += 1
        elif numeric_value <= 1:
            counts[">0–1"] += 1
        elif numeric_value <= 2:
            counts[">1–2"] += 1
        elif numeric_value <= 3:
            counts[">2–3"] += 1
        else:
            counts[">3"] += 1
    order = ("0", ">0–1", ">1–2", ">2–3", ">3", "Not informed")
    return [(value, counts[value]) for value in order if counts[value]]


def generate_distribution_grid(
    filename: str,
    title: str,
    description: str,
    panels: list[tuple[str, list[tuple[str, int]], str]],
    total_rows: int,
) -> None:
    width = 1_200
    panel_width = 390
    panel_lefts = (10, 405, 800)
    plot_offset = 155
    plot_width = 205
    chart_top = 150
    row_step, bar_height = 48, 27
    maximum_rows = max(len(values) for _, values, _ in panels)
    chart_bottom = chart_top + (maximum_rows - 1) * row_step + bar_height + 10
    height = chart_bottom + 115
    body = [
        (
            f'<text x="600" y="43" text-anchor="middle" font-size="25" '
            f'font-weight="700">{html.escape(title)}</text>'
        ),
        (
            f'<text x="600" y="72" text-anchor="middle" font-size="14" '
            f'fill="#51617e">{total_rows:,} public NDB-UFES-linked patch rows; '
            '“Not informed” is retained</text>'
        ),
    ]

    for panel_index, (panel_title, values, color) in enumerate(panels):
        panel_left = panel_lefts[panel_index]
        plot_left = panel_left + plot_offset
        body.append(
            f'<text x="{panel_left + panel_width / 2}" y="112" '
            'text-anchor="middle" font-size="17" font-weight="700">'
            f"{html.escape(panel_title)}</text>"
        )
        for tick in (0, 25, 50, 75, 100):
            x = plot_left + plot_width * tick / 100
            body.extend(
                [
                    (
                        f'<line x1="{x:.1f}" y1="{chart_top - 10}" '
                        f'x2="{x:.1f}" y2="{chart_bottom}" stroke="#e7ecf5" '
                        'stroke-width="1"/>'
                    ),
                    (
                        f'<text x="{x:.1f}" y="{chart_bottom + 27}" '
                        'text-anchor="middle" '
                        f'font-size="11" fill="#51617e">{tick}%</text>'
                    ),
                ]
            )
        for row_index, (label, count) in enumerate(values):
            y = chart_top + row_index * row_step
            percent = 100 * count / total_rows
            bar_width = plot_width * percent / 100
            fill = NOT_INFORMED_COLOR if label == "Not informed" else color
            if percent >= 70:
                count_x = plot_left + bar_width - 7
                count_anchor = "end"
                count_fill = "#17315f" if label == "Not informed" else "#ffffff"
            else:
                count_x = plot_left + bar_width + 7
                count_anchor = "start"
                count_fill = "#17315f"
            body.extend(
                [
                    (
                        f'<text x="{plot_left - 10}" y="{y + 19}" '
                        f'text-anchor="end" font-size="12">'
                        f"{html.escape(label)}</text>"
                    ),
                    (
                        f'<rect x="{plot_left}" y="{y}" width="{bar_width:.1f}" '
                        f'height="{bar_height}" rx="4" fill="{fill}"/>'
                    ),
                    (
                        f'<text x="{count_x:.1f}" y="{y + 19}" '
                        f'text-anchor="{count_anchor}" font-size="11" '
                        f'font-weight="700" fill="{count_fill}">'
                        f"{count:,} ({percent:.1f}%)</text>"
                    ),
                ]
            )

    body.append(
        f'<text x="600" y="{height - 28}" text-anchor="middle" font-size="12" '
        'fill="#51617e">Percentages describe assignment rows, not unique '
        'patients or source images.</text>'
    )
    write_svg(
        filename,
        svg_document(title, description, width, height, body),
    )


def generate_patch_row_distributions(
    rows: list[dict[str, str]],
) -> None:
    total_rows = EXPECTED_SOURCE_SUMMARY["both"]["patches"]
    require(
        len(rows) == total_rows,
        f"Distribution scope contains {len(rows):,} rows, expected {total_rows:,}",
    )
    generate_distribution_grid(
        "demographic_distributions.svg",
        "Public-linked demographic distributions",
        "Patch-row distributions for released gender, age-group, and skin-color "
        "fields in the 3,111 public NDB-UFES-linked rows, with not-informed "
        "values retained.",
        [
            (
                "Gender",
                ordered_counts(
                    rows,
                    "gender",
                    ("F", "M", "Not informed"),
                    {"F": "Female (F)", "M": "Male (M)"},
                ),
                DISTRIBUTION_COLORS[0],
            ),
            (
                "Age group",
                ordered_counts(
                    rows,
                    "age_group",
                    ("0", "1", "2", "Not informed"),
                    {
                        "0": "Age group 0",
                        "1": "Age group 1",
                        "2": "Age group 2",
                    },
                ),
                DISTRIBUTION_COLORS[1],
            ),
            (
                "Skin color",
                ordered_counts(
                    rows,
                    "skin_color",
                    ("White", "Brown", "Black", "Not informed"),
                ),
                DISTRIBUTION_COLORS[2],
            ),
        ],
        total_rows,
    )
    generate_distribution_grid(
        "exposure_distributions.svg",
        "Public-linked exposure distributions",
        "Patch-row distributions for released tobacco-use, alcohol-consumption, "
        "and sun-exposure fields in the 3,111 public NDB-UFES-linked rows, with "
        "not-informed values retained.",
        [
            (
                "Tobacco use",
                ordered_counts(
                    rows,
                    "tobacco_use",
                    ("Yes", "Former", "No", "Not informed"),
                ),
                DISTRIBUTION_COLORS[0],
            ),
            (
                "Alcohol consumption",
                ordered_counts(
                    rows,
                    "alcohol_consumption",
                    ("Yes", "Former", "No", "Not informed"),
                ),
                DISTRIBUTION_COLORS[1],
            ),
            (
                "Sun exposure",
                ordered_counts(
                    rows,
                    "sun_exposure",
                    ("Yes", "No", "Not informed"),
                ),
                DISTRIBUTION_COLORS[2],
            ),
        ],
        total_rows,
    )
    generate_distribution_grid(
        "clinical_distributions.svg",
        "Public-linked clinical distributions",
        "Patch-row distributions for released lesion localization, dysplasia "
        "severity, and grouped recorded lesion-size values in the 3,111 public "
        "NDB-UFES-linked rows, with not-informed values retained.",
        [
            (
                "Lesion localization",
                ordered_counts(
                    rows,
                    "localization",
                    (
                        "Tongue",
                        "Gingiva",
                        "Floor of mouth",
                        "Buccal mucosa",
                        "Lip",
                        "Palate",
                        "Not informed",
                    ),
                ),
                DISTRIBUTION_COLORS[0],
            ),
            (
                "Dysplasia severity",
                ordered_counts(
                    rows,
                    "dysplasia_severity",
                    ("Mild", "Moderate", "Severe", "Not informed"),
                ),
                DISTRIBUTION_COLORS[1],
            ),
            (
                "Recorded lesion size",
                grouped_lesion_size_counts(rows),
                DISTRIBUTION_COLORS[2],
            ),
        ],
        total_rows,
    )


def generate_source_image_linkage(
    source_rows: list[dict[str, str]],
) -> None:
    group_counts = Counter(row["source"] for row in source_rows)
    patch_counts = Counter()
    for row in source_rows:
        patch_counts[row["source"]] += int(row["patch_count"])

    width, height = 960, 475
    chart_left, chart_width = 230, 650
    roles = ("both", "SAB-only recovered WSI")
    body = [
        (
            '<text x="480" y="44" text-anchor="middle" font-size="25" '
            'font-weight="700">Final source-image linkage</text>'
        ),
        (
            '<text x="480" y="72" text-anchor="middle" font-size="14" '
            'fill="#51617e">Every patch is assigned to one validated '
            'source-image group</text>'
        ),
    ]
    bars = (
        ("Source-image groups", group_counts, EXPECTED_SOURCE_IMAGES, 150),
        ("Patches", patch_counts, EXPECTED_PATCHES, 270),
    )
    for label, values, total, y in bars:
        body.extend(
            [
                (
                    f'<text x="{chart_left - 18}" y="{y + 29}" text-anchor="end" '
                    f'font-size="15" font-weight="700">{label}</text>'
                ),
                (
                    f'<text x="{chart_left + chart_width}" y="{y - 12}" '
                    f'text-anchor="end" font-size="13" fill="#51617e">'
                    f'Total: {total:,}</text>'
                ),
            ]
        )
        x = chart_left
        for role in roles:
            value = values[role]
            segment_width = chart_width * value / total
            percent = 100 * value / total
            body.extend(
                [
                    (
                        f'<rect x="{x:.1f}" y="{y}" width="{segment_width:.1f}" '
                        f'height="50" fill="{SOURCE_COLORS[role]}"/>'
                    ),
                    (
                        f'<text x="{x + segment_width / 2:.1f}" y="{y + 31}" '
                        'text-anchor="middle" font-size="14" font-weight="700" '
                        f'fill="#ffffff">{value:,} ({percent:.1f}%)</text>'
                    ),
                ]
            )
            x += segment_width

    legend = (
        ("both", "Public NDB-UFES + SAB evidence"),
        ("SAB-only recovered WSI", "SAB-only evidence"),
    )
    legend_x = 175
    for role, label in legend:
        body.extend(
            [
                (
                    f'<rect x="{legend_x}" y="390" width="18" height="18" '
                    f'rx="3" fill="{SOURCE_COLORS[role]}"/>'
                ),
                (
                    f'<text x="{legend_x + 27}" y="404" font-size="13">'
                    f"{html.escape(label)}</text>"
                ),
            ]
        )
        legend_x += 405
    write_svg(
        "source_image_linkage.svg",
        svg_document(
            "Final source-image linkage",
            "Stacked bars showing 203 source-image groups and 3,111 patches "
            "supported by public NDB-UFES and SAB evidence, plus 48 groups and "
            "652 patches supported by SAB-only evidence.",
            width,
            height,
            body,
        ),
    )


def generate_fold_class_distribution(
    experiment_rows: dict[str, list[dict[str, str]]],
) -> None:
    width, height = 1_200, 660
    plot_top, plot_bottom = 145, 515
    plot_height = plot_bottom - plot_top
    panel_lefts = (80, 650)
    panel_width = 480
    body = [
        (
            '<text x="600" y="42" text-anchor="middle" font-size="25" '
            'font-weight="700">Class distribution across the six folds</text>'
        ),
        (
            '<text x="600" y="70" text-anchor="middle" font-size="14" '
            'fill="#51617e">Both final experiments retain all 3,763 patches</text>'
        ),
    ]

    for panel_left, (experiment, definition) in zip(
        panel_lefts,
        EXPERIMENTS.items(),
    ):
        counts = Counter(
            (int(row["fold"]), row["diagnosis"])
            for row in experiment_rows[experiment]
        )
        fold_totals = Counter(
            int(row["fold"]) for row in experiment_rows[experiment]
        )
        body.extend(
            [
                (
                    f'<text x="{panel_left + panel_width / 2}" y="103" '
                    f'text-anchor="middle" font-size="17" font-weight="700">'
                    f"{experiment}</text>"
                ),
                (
                    f'<text x="{panel_left + panel_width / 2}" y="125" '
                    f'text-anchor="middle" font-size="12" fill="#51617e">'
                    f"{html.escape(definition['subtitle'])}</text>"
                ),
            ]
        )
        for tick in range(0, 101, 20):
            y = plot_bottom - tick / 100 * plot_height
            body.append(
                f'<line x1="{panel_left}" y1="{y:.1f}" '
                f'x2="{panel_left + panel_width}" y2="{y:.1f}" '
                'stroke="#e7ecf5" stroke-width="1"/>'
            )
            if panel_left == panel_lefts[0]:
                body.append(
                    f'<text x="{panel_left - 12}" y="{y + 4:.1f}" '
                    f'text-anchor="end" font-size="11" fill="#51617e">{tick}</text>'
                )

        for fold in range(6):
            x = panel_left + 22 + fold * 76
            cumulative = 0.0
            total = fold_totals[fold]
            for diagnosis in CLASS_ORDER:
                value = 100 * counts[(fold, diagnosis)] / total
                rectangle_height = value / 100 * plot_height
                y = plot_bottom - (cumulative + value) / 100 * plot_height
                body.append(
                    f'<rect x="{x}" y="{y:.2f}" width="52" '
                    f'height="{rectangle_height:.2f}" '
                    f'fill="{CLASS_COLORS[diagnosis]}"/>'
                )
                if value >= 12:
                    body.append(
                        f'<text x="{x + 26}" '
                        f'y="{y + rectangle_height / 2 + 4:.2f}" '
                        'text-anchor="middle" font-size="10" '
                        f'fill="#ffffff">{value:.1f}%</text>'
                    )
                cumulative += value
            fold_label = "Test" if fold == 5 else f"Fold {fold}"
            body.extend(
                [
                    (
                        f'<text x="{x + 26}" y="{plot_bottom + 21}" '
                        f'text-anchor="middle" font-size="11">{fold_label}</text>'
                    ),
                    (
                        f'<text x="{x + 26}" y="{plot_bottom + 39}" '
                        'text-anchor="middle" font-size="10" fill="#51617e">'
                        f"n={total:,}</text>"
                    ),
                ]
            )

    body.append(
        '<text x="23" y="330" transform="rotate(-90 23 330)" '
        'text-anchor="middle" font-size="13" fill="#51617e">'
        'Class distribution (%)</text>'
    )
    legend_x = 120
    for diagnosis in CLASS_ORDER:
        body.extend(
            [
                (
                    f'<rect x="{legend_x}" y="602" width="17" height="17" '
                    f'rx="3" fill="{CLASS_COLORS[diagnosis]}"/>'
                ),
                (
                    f'<text x="{legend_x + 25}" y="615" font-size="12">'
                    f"{html.escape(diagnosis)}</text>"
                ),
            ]
        )
        legend_x += 350
    write_svg(
        "fold_class_distribution.svg",
        svg_document(
            "Class distribution across the six folds",
            "Two stacked bar charts compare diagnosis percentages in folds zero "
            "through five for the released patch-level experiment and the "
            "patient-first grouped experiment.",
            width,
            height,
            body,
        ),
    )


def write_manifest(
    experiment_rows: dict[str, list[dict[str, str]]],
    source_rows: list[dict[str, str]],
) -> None:
    sources = {
        definition["path"].relative_to(ROOT).as_posix(): {
            "rows": len(experiment_rows[experiment]),
            "sha256": sha256(definition["path"]),
        }
        for experiment, definition in EXPERIMENTS.items()
    }
    sources[SOURCE_INDEX.relative_to(ROOT).as_posix()] = {
        "rows": len(source_rows),
        "sha256": sha256(SOURCE_INDEX),
    }
    manifest = {
        "format_version": 1,
        "scope": {
            "distribution_patch_rows": EXPECTED_SOURCE_SUMMARY["both"]["patches"],
            "patches": EXPECTED_PATCHES,
            "source_image_groups": EXPECTED_SOURCE_IMAGES,
        },
        "sources": sources,
        "outputs": list(FIGURE_TITLES),
    }
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    distribution_files = {
        "clinical_distributions.svg",
        "demographic_distributions.svg",
        "exposure_distributions.svg",
    }
    source_paths = "; ".join(sources)
    with (THESIS_OUTPUT_DIR / "figure_manifest.csv").open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("title", "kind", "path", "scope", "source"),
            lineterminator="\n",
        )
        writer.writeheader()
        for filename, title in FIGURE_TITLES.items():
            if filename in distribution_files:
                scope = "3,111 public NDB-UFES-linked patch rows"
            elif filename == "source_image_linkage.svg":
                scope = "3,763 patches; 251 source-image groups"
            else:
                scope = "3,763 final experiment patch rows"
            writer.writerow(
                {
                    "title": title,
                    "kind": "thesis_svg",
                    "path": (
                        THESIS_OUTPUT_DIR / filename
                    ).relative_to(ROOT).as_posix(),
                    "scope": scope,
                    "source": source_paths,
                }
            )
        for figure in STATIC_THESIS_FIGURES:
            for suffix in ("pdf", "png", "svg"):
                path = THESIS_OUTPUT_DIR / f"{figure['stem']}.{suffix}"
                require(path.is_file(), f"Missing retained thesis figure: {path}")
                writer.writerow(
                    {
                        "title": figure["title"],
                        "kind": f"thesis_{suffix}",
                        "path": path.relative_to(ROOT).as_posix(),
                        "scope": figure["scope"],
                        "source": figure["source"],
                    }
                )


def main() -> None:
    experiment_rows, source_rows = validate_inputs()
    both_source_ids = {
        row["validated_wsi_id"]
        for row in source_rows
        if row["source"] == "both"
    }
    public_linked_rows = [
        row
        for row in experiment_rows["Experiment 2"]
        if row["public_wsi_id"] in both_source_ids
    ]
    generate_diagnosis_distribution(experiment_rows["Experiment 2"])
    generate_patch_row_distributions(public_linked_rows)
    generate_source_image_linkage(source_rows)
    generate_fold_class_distribution(experiment_rows)
    write_manifest(experiment_rows, source_rows)
    print(
        "Generated 6 final factsheet figures from "
        f"{EXPECTED_PATCHES:,} patches and {EXPECTED_SOURCE_IMAGES:,} "
        f"source-image groups; distribution figures use the "
        f"{EXPECTED_SOURCE_SUMMARY['both']['patches']:,} public "
        f"NDB-UFES-linked patches in {OUTPUT_DIR.relative_to(ROOT)} and "
        f"{THESIS_OUTPUT_DIR.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
