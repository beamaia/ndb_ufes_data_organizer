"""Stage pages: write the generated wiki pages from the published tables, so the numbers in them come from the data and cannot drift."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.phase0_dataset_builder.sources import AGE_GROUP_YEARS, SHORT_LABEL
from src.phase2_report.figures import CHOSEN_CLUSTERS, CHOSEN_PCA
from src.phase2_report.stats import NDB_LISTED_VALUES, RANDOM_DRAWS, original_folds
from src.utils.logger import logger


TABLES = Path("results/phase0/dataset_tables")
FOLDS = Path("results/phase1/folds")
CLUSTERS = Path("results/phase1/clusters/patch_clusters.csv")
STATS = Path("results/phase2/tables")
DOCS = Path("docs")
NDB_COLUMNS = {  # the meaning of each column of the NDB-UFES metadata, from the dictionary that comes with the dataset
    "public_id": "A unique ID for each sample, which is one image.",
    "lesion_id": "The lesion the image shows. One lesion can have several images.",
    "patient_id": "The patient. One patient can have several lesions and images.",
    "path": "Histopathologic image filename.",
    "localization": "Lesion's localization in the body.",
    "larger_size": "Larger size of the lesion, in centimeters. The dictionary does not say what the value 0 means.",
    "tobacco_use": "Patient's tobacco use.",
    "alcohol_consumption": "Patient's alcohol consumption.",
    "sun_exposure": "Patient's sun exposure. The original dictionary describes it in hours, with -1 when not informed, but the metadata file holds the values listed here.",
    "gender": "Patient's gender: male or female.",
    "skin_color": "Patient's skin color.",
    "age_group": "Patient's age group: group 0 is under 40 years, group 1 is 41 to 60 years, included, and group 2 is over 60 years.",
    "diagnosis": "Lesion diagnosis.",
    "dysplasia_severity": "Severity of the dysplasia in the lesion. Empty when the image has no dysplasia diagnosis.",
    "TaskII": "Label for task II: OSCC or leukoplakia.",
    "TaskIII": "Label for task III: presence or absence of dysplasia.",
    "TaskIV": "Label for task IV: OSCC, leukoplakia with dysplasia or leukoplakia without dysplasia.",
}
ATLASES = {"patient": Path("atlases/patient_atlas.pdf"), "aligned": Path("atlases/aligned_atlas.pdf")}
RAW_URL = "https://github.com/beamaia/ndb_ufes_data_organizer/raw/main/"
EXAMPLE_PAIR = ("p0020", "p0021")  # two overlapping patches of one picture, shown in Old Folds and Contamination
PATCH_SIDE = 512
LABELS = ["Leukoplakia without dysplasia", "Leukoplakia with dysplasia", "OSCC"]  # from least to most severe


def read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def markdown_table(header: list[str], rows: list[list], align_left: int = 1) -> str:
    """A GitHub table; the first ``align_left`` columns are text, the others are right-aligned numbers."""
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" if i < align_left else "---:" for i in range(len(header))) + " |"]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)


def figure(name: str, alt: str) -> str:
    return f"![{alt}](assets/figures/{name}.svg)"


def count_table(counts: pd.Series, total: int, name: str, order: list[str] | None = None) -> str:
    keys = order or list(counts.index)
    return markdown_table([name, "Patches", "Percentage"], [[key, f"{counts.get(key, 0):,}", f"{counts.get(key, 0) / total:.1%}"] for key in keys])


def fold_table(summary: pd.DataFrame, columns: dict[str, str], percent: bool = True) -> str:
    """One table of the fold summary: a row per fold and one for all folds, and a column per value of one variable.
    With ``percent`` each count is followed by its percentage of the patches of that row, and a last row gives the spread:
    the percentage of the fold with the highest share minus that of the fold with the lowest, in percentage points."""
    rows = summary[summary["fold"].isin([*map(str, range(6)), "total"])]
    patches = rows["patches"].astype(float).to_numpy()
    table = []
    for index, (_, row) in enumerate(rows.iterrows()):
        cells = [f"{float(row[column]):,.0f} ({float(row[column]) / patches[index]:.0%})" if percent else f"{float(row[column]):,.0f}" for column in columns.values()]
        table.append(["all folds" if row["fold"] == "total" else f"fold {row['fold']}", *cells])
    if percent:
        shares = rows[list(columns.values())].astype(float).div(patches, axis=0)[:6]
        table.append(["spread", *[f"{(shares[column].max() - shares[column].min()) * 100:.1f} points" for column in columns.values()]])
    return markdown_table(["Fold", *columns], table)


@dataclass
class Data:
    patch: pd.DataFrame
    picture: pd.DataFrame
    case: pd.DataFrame
    assignments: pd.DataFrame
    summary: pd.DataFrame
    cluster: pd.DataFrame
    stats: dict[str, pd.DataFrame]


def load(tables: Path, folds: Path, clusters: Path, stats: Path) -> Data:
    return Data(
        read(tables / "patch_table_public.csv"), read(tables / "picture_table_public.csv"), read(tables / "case_table_public.csv"),
        read(folds / "fold_assignments.csv"), read(folds / "fold_summary.csv"), read(clusters),
        {path.stem: pd.read_csv(path, keep_default_na=False) for path in [*stats.glob("*.csv"), clusters.parent / "cluster_choices.csv"]},
    )


def p_ndb_ufes_factsheet(d: Data) -> str:
    patch, picture, assignments = d.patch, d.picture, d.assignments
    total = len(patch)
    n_patches_of = picture["n_patches"].astype(int)
    by_dataset = picture["datasets"].value_counts()
    patches_by_dataset = patch["picture_datasets"].value_counts()
    ndb = patch["ndb_diagnosis"].replace("", "not in NDB-UFES")
    in_both = picture[picture["datasets"] == "ndb+sab"]
    folder_vs_ndb = pd.crosstab(in_both["sab_folders"], in_both["ndb_diagnosis"]).reindex(columns=LABELS, fill_value=0)
    folder_rows = [[folder, f"{row.sum():,}"] + [f"{row[label]:,}" for label in LABELS] for folder, row in folder_vs_ndb.iterrows()]
    benign = picture[picture["sab_folders"] == "benigno"]
    benign_labels = patch[patch["sab_folder"] == "benigno"]["patch_diagnosis"].value_counts()
    patches_per_picture = patch.groupby("histopath_id").size()
    less = int((patch["patch_vs_picture_diagnosis"] == "patch_less_severe").sum())
    more = patch[patch["patch_vs_picture_diagnosis"] == "patch_more_severe"]
    related = d.stats["related_pictures"]
    correlations = d.stats["patch_correlations"].set_index("variable")
    groups = picture["picture_group"].value_counts()
    with_diagnosis = patch[patch["ndb_diagnosis"] != ""]
    difference = with_diagnosis["patch_vs_picture_diagnosis"].value_counts()
    crossed = pd.crosstab(with_diagnosis["ndb_diagnosis"], with_diagnosis["patch_diagnosis"]).reindex(index=LABELS, columns=LABELS, fill_value=0)
    in_group = int(groups[groups > 1].sum())

    def of_picture(picture_label: str, patch_label: str) -> str:
        """How many patches of the pictures with this diagnosis carry this label, and their percentage."""
        return f"{crossed.loc[picture_label, patch_label]:,} ({crossed.loc[picture_label, patch_label] / crossed.loc[picture_label].sum():.1%})"

    return f"""# Factsheet: P-NDB-UFES

The patch dataset and how its patches were tied to their parent pictures. Every number on this page comes from the published tables. How the four datasets differ is in [About the Data](about-the-data.md), the folds are in [New Folds](folds.md), and every column is in the [data dictionary](data-dictionary.md).

## At a glance

{markdown_table(["Item", "Count"], [
    ["Patches (512 × 512 pixels)", f"{total:,}"],
    ["Pictures", f"{len(picture):,}"],
    ["Pictures with patches", f"{int((n_patches_of > 0).sum()):,}"],
    ["Pictures without patches", f"{int((n_patches_of == 0).sum()):,}"],
    ["Patches per picture, median", f"{int(patches_per_picture.median())} ({patches_per_picture.min()} to {patches_per_picture.max()})"],
    ["Diagnostic classes", "3"],
    ["Exact duplicate patches", f"{int((assignments['dropped_duplicate_of'] != '').sum())} (one of each pair of twins)"],
])}

## Where the patches come from

The patches are the P-NDB-UFES patches. Their parent pictures come from two datasets: the public NDB-UFES origin images and the SAB images, which are not published. A picture can exist in one dataset or in both, and two files with identical pixels count as one picture.

{markdown_table(["Found in", "Pictures", "Patches"], [
    ["NDB-UFES and SAB", f"{by_dataset.get('ndb+sab', 0):,}", f"{patches_by_dataset.get('ndb+sab', 0):,}"],
    ["SAB only", f"{by_dataset.get('sab', 0):,}", f"{patches_by_dataset.get('sab', 0):,}"],
    ["NDB-UFES only", f"{by_dataset.get('ndb', 0):,}", "0"],
])}

## SAB folders against the NDB-UFES diagnosis

SAB files its images in three folders, `carcinoma`, `leucoplasia` and `benigno`. These are not the three NDB-UFES classes. For the {len(in_both):,} pictures that exist in both datasets:

{markdown_table(["SAB folder", "Pictures", *LABELS], folder_rows, align_left=1)}

`carcinoma` holds mostly OSCC but also pictures NDB-UFES diagnoses with dysplasia, and `leucoplasia` is a broad folder that holds all three diagnoses. None of the `benigno` pictures is in NDB-UFES, so they have no NDB-UFES diagnosis, but their patches are in P-NDB-UFES: its {len(benign):,} pictures hold {int(benign["n_patches"].astype(int).sum()):,} patches ({benign["n_patches"].astype(int).sum() / total:.1%} of all patches) labelled {", ".join(f"{label} ({count:,})" for label, count in benign_labels.items())}. The SAB folders come from the SAB database and were not re-validated one by one, which is why they are never used as classes.

{figure("sab_folders", "SAB folders against the NDB-UFES diagnosis")}

## Classes

{count_table(patch["patch_diagnosis"].value_counts(), total, "Patch label", LABELS)}

The patch label is the label models train on. The NDB-UFES diagnosis belongs to the whole picture:

{count_table(ndb.value_counts(), total, "NDB-UFES diagnosis of the parent picture", [*LABELS, "not in NDB-UFES"])}

A picture has many regions, so a patch can differ from its picture's label. No label was changed. The disagreement is recorded in `patch_vs_picture_diagnosis`. The first percentage is of all {total:,} patches; the second leaves out the {int((patch["patch_vs_picture_diagnosis"] == "not_in_ndb").sum()):,} patches whose picture is not in NDB-UFES, which have no diagnosis to compare with.

{markdown_table(["Patch against its picture", "Patches", "Percentage of all patches", "Percentage of patches whose picture is in NDB-UFES"], [[key, f"{n:,}", f"{n / total:.1%}", "" if key == "not_in_ndb" else f"{n / len(with_diagnosis):.1%}"] for key, n in ((key, int((patch["patch_vs_picture_diagnosis"] == key).sum())) for key in ["match", "patch_less_severe", "patch_more_severe", "not_in_ndb"])])}

## Where the labels differ

Counting only the {len(with_diagnosis):,} patches whose picture is in NDB-UFES (the last column of the table above), the patch label equals the picture's diagnosis for {difference["match"] / len(with_diagnosis):.1%} of them, is less severe for {difference["patch_less_severe"] / len(with_diagnosis):.1%} and is more severe for {difference["patch_more_severe"] / len(with_diagnosis):.1%}. The first chart shows these shares for the pictures of each diagnosis and for all of them together.

{figure("patch_vs_picture", "How the patch label compares with the diagnosis of its picture, for the pictures of each diagnosis and for all of them")}

The second chart shows which labels the patches have, for the pictures of each diagnosis; the hatched parts are patches more severe than their picture.

{figure("patch_labels", "For the pictures of each NDB-UFES diagnosis, the share of their patches by patch label")}

- **Less severe patches** ({difference["patch_less_severe"]:,}) are expected, because a picture has many regions. A picture labeled OSCC can still hold patches of leukoplakia: {of_picture("OSCC", "Leukoplakia with dysplasia")} with dysplasia and {of_picture("OSCC", "Leukoplakia without dysplasia")} without. Pictures labeled with dysplasia can still hold patches without dysplasia: {of_picture("Leukoplakia with dysplasia", "Leukoplakia without dysplasia")}.
- **More severe patches** ({difference["patch_more_severe"]:,}, {difference["patch_more_severe"] / total:.1%} of all patches) mean the picture's label is milder than part of its content.
    - Pictures labeled without dysplasia hold no OSCC patch. They do hold patches with dysplasia, {of_picture("Leukoplakia without dysplasia", "Leukoplakia with dysplasia")}: signs of dysplasia in pictures that were not labeled as having it.
    - Pictures labeled with dysplasia hold {of_picture("Leukoplakia with dysplasia", "OSCC")} OSCC patches. OSCC is the serious case, so these pictures need to be revalidated.

!!! note "The hardest classes"
    Leukoplakia with dysplasia and leukoplakia without dysplasia are the hardest classes to learn. The data shows why: {crossed.loc["Leukoplakia without dysplasia", "Leukoplakia with dysplasia"] / crossed.loc["Leukoplakia without dysplasia"].sum():.0%} of the patches of the pictures judged as without dysplasia are labeled with dysplasia.

**Why they may differ.** The patches were labeled in a later step, not necessarily by the team that labeled NDB-UFES. The NDB-UFES diagnosis of the picture was accessible, but it was not used to label the patches, and the labeling was not blind. That may explain some of the patches with a more severe label.

## Patches per picture

{markdown_table(["Pictures", "Count", "Mean", "Median", "First quartile", "Third quartile", "Smallest", "Largest"], [[row.pictures, row.count, f"{row.mean:.1f}", f"{row.median:.0f}", f"{row.q1:.0f}", f"{row.q3:.0f}", row.smallest, row.largest] for row in d.stats["patches_per_picture"].itertuples()])}

{figure("patches_per_picture", "How many patches were cut from each picture")}

The patch extractor kept at most 20 patches from an image file. {int((patches_per_picture > 20).sum())} pictures have more, up to {patches_per_picture.max()}, because SAB holds two similar images of them, with identical pixels, and each gave its own patches.

## Related pictures

Some pictures show the same tissue: a wide view and a close-up, or two shots of one region. {len(related):,} pairs of pictures are tied by matching SIFT features, in {int((groups > 1).sum()):,} groups of related pictures that hold {in_group:,} of the {len(picture):,} pictures ({in_group / len(picture):.0%}). In {int(related["zoomed"].sum()):,} of the {len(related):,} pairs ({related["zoomed"].mean():.0%}) the zoom differs, usually by about four times, so one picture is a close-up of a part of the other. This fits how the images were taken, with the 10x and 40x objectives: the two differ by a factor of four. [Matching and Atlases](matching-and-atlases.md) shows how they were found and has the atlas.

{figure("related_zoom", "Zoom between related pictures")}

## How the patch variables relate

Each patch has its label, the diagnosis, gender and age group of its picture's patient, a morphology cluster (how the patch looks) and the SAB folder of its picture. The heatmap shows how strongly every two of them are tied, from 0 (not tied) to 1 (one decides the other); [how to read the heatmaps](factsheet-ndb-ufes.md#how-to-read-the-heatmaps). Pictures outside NDB-UFES have the value `unknown` for diagnosis, gender and age group, which ties those three together by construction.

{figure("patch_correlations", "How strongly the patch variables are tied together")}

The patch label and the morphology cluster are tied with V = {correlations.loc["patch label", "morphology cluster"]:.2f}: related, but a cluster is not a class. [New Folds](folds.md) shows the clusters by label.

## How each patch was tied to its picture

Every patch has a parent picture, checked in three independent ways:

{markdown_table(["Check", "Result"], [
    ["Exact pixel match inside the parent picture", f"{int((patch['match_status'] == 'exact').sum()):,} of {total:,} exact"],
    ["Template search over all {n} pictures names the picture in the SAB file name".format(n=len(picture)), f"{int((patch['parent_image_check'] == 'agrees').sum()):,} of {total:,} agree"],
    ["SAB patch crop with the same pixels, file name and class", f"{int(patch['sab_crop_check'].isin(['verified', 'verified_among_identical_crops']).sum()):,} of {total:,} verified"],
])}

{int((patch['other_confirmed_pictures'].astype(int) > 0).sum()):,} patches ({(patch['other_confirmed_pictures'].astype(int) > 0).mean():.0%}) also appear, confirmed by projection, in a related picture (a zoomed or shifted view of the same tissue). {int((patch['identical_patch_ids'] != '').sum())} patches have an exact twin, three pairs saved twice.

## Things to know

- **The `benigno` folder.** {len(benign):,} pictures and {int(benign['n_patches'].astype(int).sum()):,} patches ({benign['n_patches'].astype(int).sum() / total:.1%}) come from the SAB `benigno` folder. None of those pictures is in NDB-UFES, so they have no NDB-UFES diagnosis, but their patches are in P-NDB-UFES, with OSCC and dysplasia labels. They stay with their patch labels; `benigno` is never a class.
- **The patch label and the picture's diagnosis differ.** See [Where the labels differ](#where-the-labels-differ).
- **The SAB images are not published.** Publishing them would first need each image to be relabeled and verified, the way NDB-UFES was. Parts of them are shown in the atlases only because their patches are already published with labels, and the class shown for a SAB picture is not verified. Case prefixes and file paths are private as well; the published tables use pseudonyms.
"""


def fold_distance_text(d: Data) -> str:
    """The reading of the chart of the distances between the folds, shared by the two fold pages."""
    distances = d.stats["fold_distances"]
    mean = distances.groupby("fold_set")["distance"].mean()
    farthest = distances[distances["fold_set"] == "new folds"].sort_values("distance").iloc[-1]
    return f"""The chart gives, for every two folds, how far apart they are in the plane of the first two PCA components of the patch embeddings (the picture under [Morphology clusters](folds.md#morphology-clusters)). The distance is 0 when two folds cover the space in exactly the same way and grows the more differently they cover it. The panels are the original folds, the new folds, and a random division of the patches into six folds of the same sizes as the new folds (the average of {RANDOM_DRAWS} divisions), which is the distance that chance alone gives. The number in each title is the mean distance. In each panel both axes are the folds: the square where a row and a column meet is the distance between those two folds, and the diagonal is empty because a fold has no distance to itself.

{figure("fold_distances", "Distance between every two folds, for the original folds, the new folds and a random division")}

The original folds are about as close as a random division (mean {mean["original folds"]:.2f} against {mean["random division"]:.2f}), because they deal the patches out one by one. The new folds are about {mean["new folds"] / mean["random division"]:.1f} times as far apart (mean {mean["new folds"]:.2f}), and the farthest are folds {farthest.fold_a} and {farthest.fold_b} ({farthest.distance:.2f}). Patches of one case group look alike and sit close together, so keeping case groups in one fold makes each fold cover the space a little differently."""


def ndb_ufes_factsheet(d: Data) -> str:
    glance = d.stats["ndb_at_a_glance"].set_index("item")["value"]
    distributions = d.stats["ndb_distributions"]
    with_patches = d.stats["ndb_images_with_patches"].set_index("diagnosis")
    correlations = d.stats["ndb_correlations"].set_index("variable")
    columns = d.stats["ndb_columns"].set_index("column")
    picture = d.picture
    ndb_only = int((picture["datasets"] == "ndb").sum())
    in_sab_only_without_patches = int(((picture["datasets"] == "ndb+sab") & (picture["n_patches"].astype(int) == 0)).sum())
    diagnosis = distributions[distributions["variable"] == "diagnosis"].set_index("value")
    pairs = correlations.where(np.tril(np.ones(correlations.shape, dtype=bool), k=-1)).stack().sort_values(ascending=False)
    strongest, weakest = pairs.index[0], pairs.index[-1]
    diagnosis_ties = correlations["diagnosis"].drop("diagnosis").sort_values(ascending=False)
    age_groups = ", ".join(f"{code} ({years})" for code, years in AGE_GROUP_YEARS.items())

    return f"""# Factsheet: NDB-UFES

NDB-UFES, the public dataset of whole histopathology images with patient data and a diagnosis for each image, counted from its metadata file. How it was built is in [About the Data](about-the-data.md). The patches cut from these images are described in the [P-NDB-UFES factsheet](factsheet-p-ndb-ufes.md). Every number on this page comes from the published tables.

## At a glance

{markdown_table(["Item", "Count"], [
    ["Images", f"{int(glance['images']):,}"],
    ["Patients", f"{int(glance['patients']):,}"],
    ["Lesions", f"{int(glance['lesions']):,}"],
    ["Images with patches in P-NDB-UFES", f"{int(glance['images with patches in P-NDB-UFES']):,}"],
    ["Images without patches", f"{int(glance['images without patches']):,}"],
])}

Of the {int(glance['images without patches'])} images without patches, {in_sab_only_without_patches} are also in SAB but were never cut into usable patches, and {ndb_only} exist only in NDB-UFES. See [About the Data](about-the-data.md).

## Columns of the metadata

The metadata file has one row per image. The meanings are those of the dictionary that comes with the dataset. The values are listed when a column has {NDB_LISTED_VALUES} or fewer, and `Filled` is how many of the {int(glance['images'])} images have a value.

{markdown_table(["Column", "Meaning", "Values", "Filled"], [[f"`{name}`", meaning, columns.loc[name, "values"], columns.loc[name, "filled"]] for name, meaning in NDB_COLUMNS.items()], align_left=3)}

## Diagnosis

The diagnosis belongs to the whole image: {", ".join(f"{diagnosis.loc[label, 'images']} {label} ({diagnosis.loc[label, 'share']:.1%})" for label in LABELS[::-1])}.

{markdown_table(["Diagnosis", "Images with patches", "Images without patches"], [[label, with_patches.loc[label, "with patches"], with_patches.loc[label, "without patches"]] for label in LABELS])}

{figure("ndb_images_with_patches", "NDB-UFES images with and without patches, by diagnosis")}

## Patients and lesions

Each variable counts images. `Not informed` is a value of its own in the metadata: it is not a missing row. Age group is coded in the metadata as {age_groups}; group 0 is the smallest.

{figure("ndb_distributions", "Distribution of the NDB-UFES variables")}

## How the variables relate

The heatmap shows how strongly every two variables are tied, from 0 (not tied) to 1 (one decides the other). The strongest pair is {strongest[0].replace("_", " ")} and {strongest[1].replace("_", " ")} (V = {pairs.iloc[0]:.2f}) and the weakest is {weakest[0].replace("_", " ")} and {weakest[1].replace("_", " ")} (V = {pairs.iloc[-1]:.2f}). The diagnosis is tied most to {diagnosis_ties.index[0].replace("_", " ")} (V = {diagnosis_ties.iloc[0]:.2f}) and least to {diagnosis_ties.index[-1].replace("_", " ")} (V = {diagnosis_ties.iloc[-1]:.2f}).

{figure("ndb_correlations", "How strongly the NDB-UFES variables are tied together")}

`Not informed` and empty values count as values of their own, so a variable that is often not informed can be tied to another one only through that.

## How to read the heatmaps

Each square is Cramér's V between two variables. It is worked out from the table of counts of the two (for example the diagnosis in the rows and the gender in the columns) by comparing it with the counts the table would hold if the two variables had nothing to do with each other.

- **0** means the variables are not tied: knowing one tells nothing about the other.
- **1** means each value of one goes with exactly one value of the other.
- It does not depend on how many images there are, so squares can be compared. As a rough guide, under 0.1 is very weak, 0.1 to 0.3 weak to moderate and above 0.3 strong.
- A tie is not a cause: it only says the two vary together in this data.

"""


def old_folds_page(d: Data) -> str:
    patch, assignments = d.patch, d.assignments
    spread, overlap, balance = d.stats["fold_spread"], d.stats["overlapping_patches"], d.stats["fold_balance"]
    sets = ["original folds", "new folds"]
    units = list(dict.fromkeys(spread["unit"]))

    def split_units(name: str, unit: str) -> tuple[int, int]:
        """How many units of this kind there are in the fold set, and how many have patches in more than one fold."""
        part = spread[(spread["fold_set"] == name) & (spread["unit"] == unit)]
        return int(part["units"].sum()), int(part.loc[part["folds"] > 1, "units"].sum())

    contamination_rows = [[unit, f"{split_units('original folds', unit)[0]:,}", *[f"{split_units(name, unit)[1]:,} ({split_units(name, unit)[1] / split_units(name, unit)[0]:.0%})" for name in sets]] for unit in units]
    pairs = overlap.set_index(["fold_set", "shared_area_at_least"])
    overlap_rows = [[f"at least {share}", f"{pairs.loc[('original folds', share), 'pairs']:,}", *[f"{pairs.loc[(name, share), 'pairs_in_different_folds']:,} ({pairs.loc[(name, share), 'share_in_different_folds']:.0%})" for name in sets]] for share in dict.fromkeys(overlap["shared_area_at_least"])]
    affected_rows = [[f"at least {share}", f"{pairs.loc[('original folds', share), 'patches_with_neighbour']:,} ({pairs.loc[('original folds', share), 'patches_with_neighbour'] / pairs.loc[('original folds', share), 'patches']:.0%})", *[f"{pairs.loc[(name, share), 'patches_in_different_folds']:,} ({pairs.loc[(name, share), 'patches_in_different_folds'] / pairs.loc[(name, share), 'patches']:.0%})" for name in sets]] for share in dict.fromkeys(overlap["shared_area_at_least"])]
    quarter = pairs.loc[("original folds", "25%")]
    names = [f"age group {AGE_GROUP_YEARS[value]}" if variable == "age group" and value in AGE_GROUP_YEARS else f"{variable} {value}" if variable == "age group" else f"{variable}: {value}" for variable, value in zip(balance["variable"], balance["value"])]
    table = balance.assign(name=names).pivot_table(index=["variable", "value", "name"], columns="fold_set", values="spread_points", sort=False).reset_index()
    balance_rows = [[row["name"], f"{row['original folds']:.1f}", f"{row['new folds']:.1f}"] for _, row in table.iterrows()]
    widest = {name: balance[balance["fold_set"] == name]["spread_points"].max() for name in sets}

    first, second = EXAMPLE_PAIR
    a, b = (patch[patch["patch_id"] == name].iloc[0] for name in EXAMPLE_PAIR)
    shared = max(PATCH_SIDE - abs(int(a.x) - int(b.x)), 0) * max(PATCH_SIDE - abs(int(a.y) - int(b.y)), 0) / PATCH_SIDE**2
    folder = original_folds()
    new_fold = assignments.set_index("patch_id")["fold"]
    in_folders = patch.assign(folder=patch["patch_id"].map(folder)).groupby("case_pseudonym")["folder"].transform("nunique")
    patches_in_split_cases = int((in_folders > 1).sum())
    largest = d.stats["fold_largest_groups"]
    by_cluster = pd.crosstab(patch["patch_id"].map(folder), patch["patch_id"].map(d.cluster.set_index("patch_id")["cluster_k3"]))
    cluster_rows = [[f"fold {name}", *[f"{row[c]:,} ({row[c] / row.sum():.0%})" for c in by_cluster.columns]] for name, row in by_cluster.iterrows()]
    cluster_rows.append(["all folds", *[f"{by_cluster[c].sum():,} ({by_cluster[c].sum() / by_cluster.to_numpy().sum():.0%})" for c in by_cluster.columns]])

    return f"""# Old Folds and Contamination

The folds published with P-NDB-UFES on Mendeley Data, measured against the links rebuilt here and set beside the [new folds](folds.md). They are six folds of about 627 patches each, numbered 0 to 5 here, like the new folds, although the published files count them from 1. Every number on this page comes from the published tables.

## Contamination

Folds are contaminated when the same patient, picture or case has patches in more than one of them: whichever fold is held out, part of that unit is in the training folds. The links between patches, pictures and cases were not available when the original folds were made, so this is measured against the links rebuilt here. The table counts the units that have patches in more than one fold.

{markdown_table(["Unit", "Units", "Split in the original folds", "Split in the new folds"], contamination_rows)}

{patches_in_split_cases:,} of the {len(patch):,} patches ({patches_in_split_cases / len(patch):.2%}) belong to a case that the original folds split. The chart takes the {len(largest.case_group.unique())} largest case groups and shows, for each, how many of its patches are in each fold. In the original folds (left) every bar is split over all six folds, so each of these patients has patches on both sides of any evaluation. In the new folds (right) every bar is a single colour.

{figure("fold_largest_groups", "How the patches of the largest case groups are divided between the folds, original and new folds")}

## Neighbouring patches

Patches of one picture can overlap, because they were cut next to each other. Two overlapping patches in different folds share tissue between a training fold and a test fold. The first table counts the pairs of patches of one picture that share at least the given part of their area, and how many of them are in different folds.

{markdown_table(["Shared area", "Pairs", "In different folds, original folds", "In different folds, new folds"], overlap_rows)}

The second table counts patches instead of pairs: the patches that have a neighbour sharing at least that part of their area, and, among all patches, those whose neighbour is in a different fold. In the original folds, {int(quarter.patches_in_different_folds):,} of the {int(quarter.patches):,} patches ({quarter.patches_in_different_folds / quarter.patches:.0%}) have a neighbour sharing at least a quarter of their area in another fold, and in the new folds none do.

{markdown_table(["Shared area", "Patches with such a neighbour", "With that neighbour in a different fold, original folds", "With that neighbour in a different fold, new folds"], affected_rows)}

An example from the data: `{first}` and `{second}` are cut from one picture, at ({a.x}, {a.y}) and ({b.x}, {b.y}), and share about {shared:.0%} of their area. In the original folds they are in folds {folder[first]} and {folder[second]}, so a model trained on one is tested on a neighbour that holds part of the same tissue. In the new folds they are in folds {new_fold[first]} and {new_fold[second]}.

## Balance

Contamination is one side. The other is whether the folds look alike. In short, the new folds are less alike than the original ones: they give up some evenness to avoid the contamination. For each value, the table gives the spread: the percentage of the fold with the highest share of that value minus the percentage of the fold with the lowest, in percentage points. For example, if 30% of the patches of one fold are OSCC and 25% of another fold's, the spread is 5 points. Small numbers mean the folds look alike.

{markdown_table(["Value", "Spread, original folds", "Spread, new folds"], balance_rows)}

{figure("fold_balance", "Spread between the folds for each value, original and new folds")}

The original folds are the more even: their widest spread is {widest["original folds"]:.1f} points, against {widest["new folds"]:.1f} for the new folds. The new folds give up a little evenness to keep every case, picture and group of related pictures in one fold. The widest spreads in the new folds are for the smallest groups of patients, for example age group 0, which is only 199 patches in a few case groups.

## The original folds and the morphology clusters

The original folds deal patches out one by one, so patches of one picture end up in different folds. How the folds divide the three morphology clusters (see [New Folds](folds.md#morphology-clusters) for what they are):

{markdown_table(["Fold", *[f"Cluster {c}" for c in by_cluster.columns]], cluster_rows)}

## Distance between the folds

{fold_distance_text(d)}

## What this means

Results on the original folds are not directly comparable with results on the new folds, and scores on the original folds can be higher than they would be on new patients, because their test folds hold neighbours of their training patches. Retraining on the new folds is what will show how much the contamination mattered.
"""


def matching_page(d: Data) -> str:
    related = d.stats["related_pictures"]
    patch, picture = d.patch, d.picture
    groups = picture["picture_group"].value_counts()
    sizes = {name: path.stat().st_size / 2**20 for name, path in ATLASES.items()}
    projected = int((patch["other_confirmed_pictures"].astype(int) > 0).sum())
    in_group = int(groups[groups > 1].sum())

    return f"""# Matching and Atlases

How patches and pictures were tied together, and the two PDF atlases that show it.

## Two kinds of matching

The datasets hold the same material in several forms, so two questions had to be answered: which picture was each patch cut from, and which pictures show the same tissue.

- **Template matching, patch to picture.** A patch is a straight crop of its picture, so its size and colors do not change. The patch is slid over the picture and the position where the pixels are identical is the answer. All {len(patch):,} patches were found this way, exactly, in a picture of NDB-UFES or SAB.
- **SIFT, picture to picture.** Pictures of the same tissue vary in zoom, color and rotation, so exact pixels cannot be used. SIFT finds distinctive points in both pictures, the matching points are checked for one consistent geometry, and a pair counts as related when enough points agree.

## What it found

- {len(related):,} pairs of pictures are tied strongly, in {int((groups > 1).sum()):,} groups of related pictures that hold {in_group:,} of the {len(picture):,} pictures ({in_group / len(picture):.0%}).
- In {int(related["zoomed"].sum()):,} of the {len(related):,} pairs ({related["zoomed"].mean():.0%}) one picture is a zoomed close-up of part of the other, usually about four times. This fits the 10x and 40x objectives the images were taken with, which differ by a factor of four.
- {projected:,} patches ({projected / len(patch):.0%}) also appear in a second picture. Their position there was found by carrying the patch through the geometry between the two pictures.
- The file names of SAB point to the same pictures: all {int((patch["parent_image_check"] == "agrees").sum()):,} agree ({(patch["parent_image_check"] == "agrees").mean():.0%}). See [About the Data](about-the-data.md).

{figure("related_zoom", "Zoom between related pictures")}

## The atlases

Both are PDFs, made so that the links can be checked by eye.

- [Patient atlas]({RAW_URL}{ATLASES["patient"]}) ({sizes["patient"]:.0f} MB). One page for each case group: its pictures with a box around each patch, and below them each patch next to the region cut from the picture at those coordinates. The two sides are the same pixels, one the original patch file and the other the crop, so a mismatch would be visible at once.
- [Aligned atlas]({RAW_URL}{ATLASES["aligned"]}) ({sizes["aligned"]:.0f} MB). One row for each pair of related pictures. At the same zoom the two pictures are shown as one picture plus another picture equals the joined picture. When one is a close-up, the wide picture is shown with the rotated close-up outlined in it and the share of the close-up that lies inside the wide picture.

!!! warning "About the SAB pictures in the atlases"
    The SAB images are not published and are not available to download. Publishing them would first need each image to be relabeled and verified, the way NDB-UFES was. They appear in the atlases because their patches are already published with labels, and because part of the same tissue is already public in the dataset. The class shown for a SAB-only picture is the one the SAB database gave it, and it has not been verified. The atlases are for checking the links, not a copy of the images.
"""


def new_folds_page(d: Data) -> str:
    patch, case, assignments, summary, cluster = d.patch, d.case, d.assignments, d.summary, d.cluster
    kept = assignments[assignments["fold"] != ""]
    fold_sizes = kept.groupby("fold").size()
    group_sizes = patch.groupby("case_group").size().sort_values(ascending=False)
    cases_per_group = case.groupby("case_group").size()
    by_cluster = pd.crosstab(cluster["cluster_k3"], patch.set_index("patch_id").loc[cluster["patch_id"], "patch_diagnosis"].to_numpy()).reindex(columns=LABELS, fill_value=0)

    choices = d.stats["cluster_choices"]
    choice = choices[(choices["pca_components"] == CHOSEN_PCA) & (choices["clusters"] == CHOSEN_CLUSTERS)].iloc[0]
    cluster_rows = [[f"cluster {name}", f"{row.sum():,}"] + [f"{row[label]:,} ({row[label] / row.sum():.0%})" for label in LABELS] for name, row in by_cluster.iterrows()]

    return f"""# New Folds

The folds of the rebuilt dataset. Every number on this page comes from the published tables.

## What they guarantee

- Every case group is in exactly one fold, so patches of the same patient are never on both sides of an evaluation. Neither is any parent picture, nor any group of related pictures.
- Every fold holds all three classes.
- The largest fold holds {fold_sizes.max() / fold_sizes.min():.3f} times the patches of the smallest (the limit is 1.10).
- The same input always gives the same folds.

There is no separate test split: each of the six folds is held out in turn.

## Cases and case groups

The SAB file name carries a patient prefix, shown here as a masked case. Cases are tied into a case group when the same picture, related pictures, or one NDB-UFES patient appear under more than one prefix. {int((cases_per_group > 1).sum())} case group holds more than one case; every other group is one case. There are {len(case):,} cases in {case['case_group'].nunique():,} case groups.

{markdown_table(["Largest case groups", "Patches"], [[name, f"{size:,}"] for name, size in group_sizes.head(5).items()])}

## How they were made

The unit of assignment is the case group, so everything from one patient stays together. That alone does not make good folds, because case groups differ a lot in size and in what they hold: some are one picture, one is {int(group_sizes.max())} patches. So each fold was also balanced on other information about the patches, all with equal weight:

- the patch label,
- the NDB-UFES diagnosis of the picture (`unknown` for pictures outside NDB-UFES),
- the gender and the age group of the NDB-UFES patient (`unknown` for pictures outside NDB-UFES),
- the morphology cluster of the patch, which is how the patch looks (see below).

A greedy algorithm does the dividing. The case groups are dealt out largest first, and each goes to the fold where it keeps all those counts closest to an equal share. A greedy choice is the best one at that step, and it is never revisited, so the result is then improved: single groups are moved, and pairs of groups exchanged between two folds, for as long as that lowers the total deviation from an equal share. The whole search is repeated from 201 starting points (one greedy, 200 shuffled with a fixed seed) and the best result is kept. The {len(kept):,} patches counted are those left after the three duplicate pairs are counted once.

## The folds in numbers

Each table is one variable. Counts are patches, followed by their percentage of the fold. The last row, `spread`, is the percentage of the fold with the highest share minus that of the fold with the lowest, in percentage points: for the OSCC column, the fold with the most OSCC patches has that many points more of them than the fold with the fewest. Small numbers mean the folds look alike.

### Size

{fold_table(summary, {"Case groups": "groups", "Patches": "patches"}, percent=False)}

Only the patches are balanced, not the number of case groups: groups differ a lot in size, so a fold can hold fewer groups and still be as large.

### Patch label

{fold_table(summary, {"OSCC": "OSCC", "Leukoplakia with dysplasia": "Dys+", "Leukoplakia without dysplasia": "Dys-"})}

### NDB-UFES diagnosis of the picture

{fold_table(summary, {"OSCC": "NDB OSCC", "Leukoplakia with dysplasia": "NDB Dys+", "Leukoplakia without dysplasia": "NDB Dys-", "Not in NDB-UFES": "no NDB"})}

### Gender of the NDB-UFES patient

`Unknown` is a picture that is not in NDB-UFES.

{fold_table(summary, {"Female": "gender F", "Male": "gender M", "Unknown": "gender unknown"})}

### Age group of the NDB-UFES patient

{fold_table(summary, {f"Group {code}, {years}": f"age group {code}" for code, years in AGE_GROUP_YEARS.items()} | {"Unknown": "age group unknown"})}

Age group 0 is only 199 patches in a few case groups, so two folds hold none of it.

### Morphology cluster

{fold_table(summary, {"Cluster 0": "cluster 0", "Cluster 1": "cluster 1", "Cluster 2": "cluster 2"})}

### SAB `benigno` folder

This count is reported but not balanced.

{fold_table(summary, {"Patches from the benigno folder": "benigno"})}

## Morphology clusters

Patches of different pictures can look alike, and a fold made mostly of one kind of appearance would test something different from the other folds. So the folds are balanced on how the patches look as well. Each patch is turned into a list of numbers (an embedding) by the Virchow pathology model. Reduced to the two directions that vary most (the first two PCA components), the patches form the picture below, where each dot is a patch. The same patches are coloured by patch label on the left and by cluster on the right. The clusters describe appearance, not diagnosis: every class spreads over several of them.

{figure("embedding_view", "The patches in the plane of the first two PCA components, by patch label and by morphology cluster")}

The patches are grouped into {CHOSEN_CLUSTERS} clusters with K-Means (seed 42). The number of PCA components and of clusters was chosen by how well separated the clusters are (the silhouette, higher is better), among the choices whose clusters were not too small or too uneven. The chart shows every choice tried; the red square is the one used (silhouette {choice.silhouette:.2f}), and numbers in grey italics are choices that were set aside for their cluster sizes.

{figure("cluster_choices", "How well separated the clusters are, for each number of PCA components and of clusters")}

{markdown_table(["Cluster", "Patches", *LABELS], cluster_rows, align_left=1)}

## Distance between the folds

{fold_distance_text(d)}

## Using the folds

Use `results/phase1/folds/fold_assignments.csv` and its `fold` column instead of a random patch-level split. Skip the three patches with an empty `fold`: they are exact duplicates of a patch that stays in the folds. The label to predict is `patch_diagnosis`. To rebuild everything, see [Reproducibility](reproducibility.md).
"""


def run_pages(args: argparse.Namespace) -> dict:
    data = load(args.tables, args.folds, args.clusters, args.stats)
    pages = {
        "factsheet-ndb-ufes.md": ndb_ufes_factsheet(data), "factsheet-p-ndb-ufes.md": p_ndb_ufes_factsheet(data), "matching-and-atlases.md": matching_page(data),
        "old-folds.md": old_folds_page(data), "folds.md": new_folds_page(data),
    }
    for name, text in pages.items():
        (args.docs / name).write_text(text, encoding="utf-8")
        logger.info(f"Wrote {args.docs / name}")
    return {"pages": sorted(pages)}


def pages_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write the generated wiki pages from the published tables.")
    parser.add_argument("--tables", type=Path, default=TABLES)
    parser.add_argument("--folds", type=Path, default=FOLDS)
    parser.add_argument("--clusters", type=Path, default=CLUSTERS)
    parser.add_argument("--stats", type=Path, default=STATS)
    parser.add_argument("--docs", type=Path, default=DOCS)
    return parser
