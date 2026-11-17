"""Static figures and LaTeX tables for the thesis (the Overleaf project), from the same tables as the slides.

Written to ``--project`` (the folder of the Overleaf project):
- ``figuras/resultados/``: the result charts of the slides as PNG (balanced accuracy of both experiments, ROC curves, balanced accuracy by zoom).
- ``capitulos/rascunho-tabelas.tex``: the tables, ready to copy into a chapter (``\\label{tab:...}``, captions to edit).
- ``capitulos/rascunho-figuras.tex``: every figure of ``figuras/dados`` and ``figuras/slides`` as a ``figure`` block, with a draft caption and ``\\label{fig:...}``.

Occlusion, deletion and the other explainability analyzes are not included.
"""

from __future__ import annotations

import argparse
import re
from itertools import combinations
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from PIL import Image

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from src.utils.logger import logger  # noqa: E402

EXPERIMENTS = Path("results/experiments")
ARTICLE = Path("../presentation/web/data/article_table4.csv")
NAMES = {"coat_lite_small": "CoaT-Lite Small", "convnext_large": "ConvNeXt-L", "densenet121": "DenseNet-121", "efficientnet_b0": "EfficientNet-B0", "efficientnet_b3": "EfficientNet-B3",
         "mobilenetv2": "MobileNetV2", "pit_s_distilled_224": "PiT-S", "resnet50": "ResNet-50", "swin_base_patch4_window7_224": "Swin-B", "swin_tiny_patch4_window7_224": "Swin-T",
         "vgg16": "VGG16", "vit_small_patch16_384": "ViT-S"}
CLASSES = ["Without dysplasia", "With dysplasia", "OSCC"]  # from the least to the most severe
KEYS = ["leukoplakia_without_dysplasia", "leukoplakia_with_dysplasia", "oscc"]
EXPERIMENT_NAME = {1: "Experiment 1 (published folds)", 2: "Experiment 2 (leakage-safe folds)"}
COLOR = {1: "#e4572e", 2: "#2a6fdb"}


def name(model: str) -> str:
    return NAMES.get(model, model)


def tex(text) -> str:
    """A value as LaTeX text: the plus-minus sign and the characters LaTeX reserves."""
    return str(text).replace("\\%", "%").replace("\\&", "&").replace("±", "$\\pm$").replace("×", "$\\times$").replace("%", "\\%").replace("&", "\\&").replace("_", "\\_")


def bold_best(rows: list[list], first: int = 1) -> list[list]:
    """The largest value of each column in bold (ties too): a cell is "mean $\\pm$ sd", or a plain number; a cell with no number ("-") never wins."""
    value = lambda cell: float(str(cell).split()[0]) if str(cell).split()[:1] and str(cell).split()[0].replace(".", "", 1).isdigit() else None  # noqa: E731
    for column in range(first, len(rows[0])):
        values = [value(row[column]) for row in rows]
        best = max((v for v in values if v is not None), default=None)
        for row, v in zip(rows, values):
            if v is not None and v == best:
                row[column] = f"\\textbf{{{row[column]}}}"
    return rows


def table(label: str, caption: str, header: list[str], rows: list[list], spec: str, groups: list[tuple[str, int]] | None = None, fit: bool = False, wide: bool = False, size: str = "small") -> str:
    """A ``table`` environment: caption above (ABNT), three rules, an optional line of group headings. ``fit`` scales a wide table to the width of the text."""
    lines = ["\\begin{table}[htb]", "\\centering", f"\\{size}", f"\\caption{{{caption}}}", f"\\label{{tab:{label}}}"] + (["\\resizebox{\\textwidth}{!}{%"] if fit else [])
    lines += [(f"\\begin{{tabularx}}{{\\textwidth}}{{{spec}}}" if wide else f"\\begin{{tabular}}{{{spec}}}"), "\\toprule"]  # wide: the X columns take the width of the text
    if groups:
        lines.append(" & ".join(f"\\multicolumn{{{span}}}{{c}}{{{tex(title)}}}" for title, span in groups) + " \\\\")
        start = 1
        for title, span in groups:
            if title:
                lines.append(f"\\cmidrule(lr){{{start}-{start + span - 1}}}")
            start += span
    lines.append(" & ".join(f"\\textbf{{{tex(h)}}}" for h in header) + " \\\\")
    lines.append("\\midrule")
    lines += [" & ".join(tex(v) for v in row) + " \\\\" for row in rows]
    lines += ["\\bottomrule", ("\\end{tabularx}" if wide else "\\end{tabular}") + ("}" if fit else "")]
    lines.append("\\end{table}")
    return "\n".join(lines)


def tables(project: Path, results: Path, article: Path, organizer: Path) -> list[str]:
    summary = {e: pd.read_csv(results / f"experiment_{e}/summary.csv", dtype=str) for e in (1, 2)}
    out = []
    # the two datasets
    ndb = pd.read_csv(organizer / "data/ndb_ufes/origin_level/csvs/ndb-ufes.csv", dtype=str)
    labels_to_class = {"Leukoplakia without dysplasia": "Without dysplasia", "Leukoplakia with dysplasia": "With dysplasia"}
    pictures = ndb["diagnosis"].value_counts()
    parent = pd.read_csv(results / "experiment_2/parent_vs_label.csv")
    patches = parent.groupby("label")["patches"].sum()
    labels = {"Without dysplasia": "Leukoplakia without dysplasia", "With dysplasia": "Leukoplakia with dysplasia", "OSCC": "OSCC"}
    linked = pd.read_csv(organizer / "results/phase0/dataset_tables/picture_table_public.csv", dtype=str, keep_default_na=False)
    linked = linked[linked["datasets"].str.contains("ndb")]
    with_patches = (linked["n_patches"].astype(int) > 0).groupby(linked["ndb_diagnosis"]).sum()  # the NDB-UFES pictures that patches were cut from, by diagnosis
    rows = []
    for c in CLASSES:
        n, yes = pictures[labels[c]], int(with_patches[labels[c]])
        rows.append([c, n, f"{100 * n / pictures.sum():.1f}", f"{yes} ({100 * yes / n:.1f}%)", f"{n - yes} ({100 * (n - yes) / n:.1f}%)", f"{patches[c]:,}", f"{100 * patches[c] / patches.sum():.1f}"])
    yes = int(with_patches.sum())
    rows.append(["Total", pictures.sum(), "100", f"{yes} ({100 * yes / pictures.sum():.1f}%)", f"{pictures.sum() - yes} ({100 * (pictures.sum() - yes) / pictures.sum():.1f}%)", f"{patches.sum():,}", "100"])
    out.append(table("datasets", "Pictures of NDB-UFES, with how many patches were cut from, and patches of P-NDB-UFES by class.",
                     ["Class", "Pictures", "%", "With patches", "Without patches", "Patches", "%"], rows, "lrrrrrr", [("", 1), ("NDB-UFES", 4), ("P-NDB-UFES", 2)], fit=True))
    # the internal dataset (SAB) is divided in classes: its pictures by class, the patches of the internal patch dataset, and how the classes relate to NDB-UFES and to the patch labels
    sab_class = {"carcinoma": "Carcinoma", "leucoplasia": "Leukoplakia", "benigno": "Benign"}
    sab = pd.read_csv(organizer / "results/phase0/dataset_tables/picture_table_public.csv", dtype=str, keep_default_na=False)
    sab = sab[sab["datasets"].str.contains("sab")]
    counts = sab["sab_folders"].value_counts()
    rows = [[sab_class[k], f"{counts[k]:,}", f"{100 * counts[k] / counts.sum():.1f}"] for k in sab_class]
    rows.append(["Total", f"{counts.sum():,}", "100"])
    out.append(table("sab-folders", "Pictures of the internal dataset (SAB) by class.", ["Class", "Pictures", "%"], rows, "lrr", [("", 1), ("SAB", 2)]))
    folder_of = {"Without dysplasia": "no_dysplasia", "With dysplasia": "with_dysplasia", "OSCC": "carcinoma"}
    rows = [[folder_of[c], f"{patches[c]:,}", f"{100 * patches[c] / patches.sum():.1f}"] for c in CLASSES]
    rows.append(["Total", f"{patches.sum():,}", "100"])
    out.append(table("patches-data", "Patches of the internal patch dataset (patches\\_data) by class.", ["Class", "Patches", "%"], rows, "lrr", [("", 1), ("patches_data", 2)]))
    # the columns of the NDB-UFES metadata file: the meanings of the dictionary of the dataset (docs/factsheet-ndb-ufes.md), shortened to fit a page
    meaning = {"public_id": ("Unique ID of the picture", "237 distinct"), "lesion_id": ("Lesion in the picture; a lesion can have several pictures", "77 distinct"),
               "patient_id": ("Patient; a patient can have several lesions and pictures", "69 distinct"), "path": ("Image file name", "237 distinct"),
               "localization": ("Location of the lesion", "Buccal mucosa, floor of mouth, gingiva, lip, palate, tongue"), "larger_size": ("Larger size of the lesion, in cm", "20 distinct"),
               "tobacco_use": ("Patient's tobacco use", "Former, no, not informed, yes"), "alcohol_consumption": ("Patient's alcohol consumption", "Former, no, not informed, yes"),
               "sun_exposure": ("Patient's sun exposure", "No, not informed, yes"), "gender": ("Patient's gender", "F, M"), "skin_color": ("Patient's skin color", "Black, brown, not informed, white"),
               "age_group": ("Patient's age group: 0 is under 40 years, 1 is 41 to 60 years, 2 is over 60 years", "0, 1, 2"), "diagnosis": ("Diagnosis of the lesion", "Leukoplakia with dysplasia, leukoplakia without dysplasia, OSCC"),
               "dysplasia_severity": ("Severity of the dysplasia; only the 89 pictures with dysplasia have a value", "Mild, moderate, severe"),
               "TaskII": ("Label of task II: OSCC or leukoplakia", "Leukoplakia, OSCC"), "TaskIII": ("Label of task III: presence or absence of dysplasia", "Absence, presence"),
               "TaskIV": ("Label of task IV: the three classes", "As in diagnosis")}
    section = (organizer / "docs/factsheet-ndb-ufes.md").read_text().split("## Columns of the metadata")[1].split("\n## ")[0]
    columns = [cells[0].strip("`") for cells in ([c.strip() for c in line.strip().strip("|").split("|")] for line in section.splitlines()) if len(cells) == 4 and cells[0].startswith("`")]
    assert columns == list(meaning), "the columns of the factsheet are not those described here"
    out.append(table("ndb-metadata", "Columns of the metadata file of NDB-UFES, which has one row per picture (after the dictionary of the dataset).", ["Column", "Meaning", "Values"],
                     [[f"\\texttt{{{name}}}", *meaning[name]] for name in columns], "lXX", wide=True, size="footnotesize"))
    # do the groups agree with the patient of NDB-UFES? the case groups (original file names) and the SIFT groups, over the pictures of NDB-UFES
    metadata = ndb.assign(ndb_origin_id=ndb["path"].str.removesuffix(".png"))[["ndb_origin_id", "patient_id"]]
    in_ndb = pd.read_csv(organizer / "results/phase0/dataset_tables/picture_table_public.csv", dtype=str, keep_default_na=False).merge(metadata, on="ndb_origin_id")
    rows = []
    for title, column, part in [("File-name groups", "case_group", in_ndb[in_ndb["case_group"] != ""]), ("SIFT groups", "picture_group", in_ndb)]:
        rows.append([title, part[column].nunique(), len(part), part["patient_id"].nunique(), int((part.groupby(column)["patient_id"].nunique() > 1).sum()), int((part.groupby("patient_id")[column].nunique() > 1).sum())])
    labels = ["Groups", "Pictures", "Patients", "Groups with several patients", "Patients in several groups"]  # one row for each measure, one column for each grouping
    out.append(table("groups-vs-patients", "Groups of NDB-UFES pictures compared with their \\texttt{patient\\_id}: groups from the original file names (only pictures that have one) and groups from SIFT (all pictures).",
                     ["", *[row[0] for row in rows]], [[label, *[row[k] for row in rows]] for k, label in enumerate(labels, 1)], "lrr"))
    # where the patient of a picture comes from: the patient_id of the NDB-UFES metadata, the code in the original file name, or both
    every = pd.read_csv(organizer / "results/phase0/dataset_tables/picture_table_public.csv", dtype=str, keep_default_na=False).merge(metadata, on="ndb_origin_id", how="left").fillna({"patient_id": ""})
    named_in_ndb = set(every[every["patient_id"] != ""]["case_group"]) - {""}
    only_sab = every[every["datasets"] == "sab"]
    new_codes = only_sab[~only_sab["case_group"].isin(named_in_ndb)]["case_group"].nunique()  # the codes of SAB-only pictures that no NDB-UFES picture shares: patients that are only in SAB
    both, ndb_only = every[every["datasets"] == "ndb+sab"], every[every["datasets"] == "ndb"]
    rows = [["Both: in NDB-UFES and SAB", len(both), both["patient_id"].nunique(), both["patient_id"].nunique()],
            ["patient_id only: only in NDB-UFES", len(ndb_only), ndb_only["patient_id"].nunique(), ndb_only["patient_id"].nunique()],
            ["File name only: only in SAB", len(only_sab), f"{only_sab['case_group'].nunique()} codes", new_codes],
            ["Total", len(every), "", both["patient_id"].nunique() + ndb_only["patient_id"].nunique() + new_codes]]
    logger.info(f"{rows[-1][-1]} patients in all: those of NDB-UFES plus {new_codes} that exist only in SAB")
    out.append(table("patient-sources", "Where the patient of a picture comes from: the patient\\_id of the NDB-UFES metadata, the code in the original file name, or both.",
                     ["Source of the patient", "Pictures", "Patients or codes", "New patients"], rows, "lrrr", fit=True))
    # which pictures generated patches
    sab["with_patches"] = sab["n_patches"].astype(int) > 0
    all_pictures = pd.read_csv(organizer / "results/phase0/dataset_tables/picture_table_public.csv", dtype=str, keep_default_na=False)
    all_pictures["n"] = all_pictures["n_patches"].astype(int)
    groups = [("In NDB-UFES and SAB", "ndb+sab"), ("Only in NDB-UFES", "ndb"), ("Only in SAB", "sab")]
    rows = []
    for title, key in groups + [("Total", None)]:
        part = all_pictures if key is None else all_pictures[all_pictures["datasets"] == key]
        with_patches = int((part["n"] > 0).sum())
        rows.append([title, len(part), f"{with_patches} ({100 * with_patches / len(part):.1f}%)", f"{len(part) - with_patches} ({100 * (len(part) - with_patches) / len(part):.1f}%)", f"{int(part['n'].sum()):,}"])
    out.append(table("pictures-with-patches", "Pictures by the dataset they are in, and whether patches were cut from them. The share is of the row.",
                     ["Dataset", "Pictures", "With patches", "Without patches", "Patches"], rows, "lrrrr"))
    # the picture groups that SIFT made: how many pictures a group has
    size = all_pictures.groupby("picture_group").size()
    rows = [[f"{n} picture" + ("s" if n > 1 else "") if n < 5 else f"{n} pictures", int((size == n).sum()), int((size == n).sum() * n), f"{100 * (size == n).sum() * n / len(all_pictures):.1f}"] for n in sorted(size.unique())]
    rows.append(["Total", len(size), len(all_pictures), "100"])
    out.append(table("picture-groups", "Groups of related pictures found with SIFT, by the number of pictures in the group.", ["Pictures in the group", "Groups", "Pictures", "%"], rows, "lrrr"))
    # the pictures of the classes that are in NDB-UFES, by their diagnosis there (the benign class has no picture in NDB-UFES)
    diagnosis = sab["ndb_diagnosis"].replace({"": "not in NDB-UFES", **labels_to_class})
    cross = pd.crosstab(sab["sab_folders"], diagnosis).reindex(index=["carcinoma", "leucoplasia"], columns=[*CLASSES, "not in NDB-UFES"], fill_value=0)
    share = lambda n, total: f"{n} ({100 * n / total:.1f}%)" if n else "0"  # noqa: E731
    rows = [[sab_class[k], *[share(int(n), cross.loc[k].sum()) for n in cross.loc[k]], int(cross.loc[k].sum())] for k in cross.index]
    rows.append(["Total", *[share(int(n), cross.values.sum()) for n in cross.sum()], int(cross.values.sum())])
    out.append(table("sab-vs-ndb", "Pictures of the carcinoma and leukoplakia classes of the internal dataset (SAB) (rows) by their diagnosis in NDB-UFES (columns). The share is of the row.",
                     ["SAB class", *CLASSES, "Not in NDB-UFES", "Total"], rows, "lrrrrr", [("", 1), ("NDB-UFES", 4), ("", 1)], fit=True))
    # the patches by the SAB class of their picture and their own label; the benign class on its own
    patch_table = pd.read_csv(organizer / "results/phase0/dataset_tables/patch_table_public.csv", dtype=str, keep_default_na=False)
    cross = pd.crosstab(patch_table["sab_folder"], patch_table["patch_diagnosis"].replace(labels_to_class)).reindex(index=list(sab_class), columns=CLASSES, fill_value=0)
    benign = cross.loc["benigno"]
    rows = [[c, f"{int(benign[c]):,}", f"{100 * benign[c] / benign.sum():.1f}"] for c in CLASSES] + [["Total", f"{int(benign.sum()):,}", "100"]]
    out.append(table("sab-benign-patches", "Patches of the benign class of the internal dataset (SAB) by their own class.", ["Patch class", "Patches", "%"], rows, "lrr", [("", 1), ("Benign", 2)]))
    rows = [[sab_class[k], *[f"{int(n):,} ({100 * n / cross.loc[k].sum():.1f}%)" if n else "0" for n in cross.loc[k]], f"{int(cross.loc[k].sum()):,}"] for k in cross.index]
    rows.append(["Total", *[f"{int(n):,} ({100 * n / cross.values.sum():.1f}%)" for n in cross.sum()], f"{int(cross.values.sum()):,}"])
    out.append(table("sab-folder-patches", "Patches by the SAB class of their picture (rows) and their own class (columns). The share is of the row.", ["SAB class", *CLASSES, "Total"], rows, "lrrrr",
                     [("", 1), ("Patch class", 3), ("", 1)]))
    # the label of a patch against the diagnosis of its picture
    counts = parent.pivot(index="parent", columns="label", values="patches").reindex(index=[*CLASSES, "not in NDB-UFES"], columns=CLASSES).fillna(0).astype(int)
    cell = lambda n, total: f"{n:,} ({100 * n / total:.1f}%)" if n else "0"  # noqa: E731
    rows = [[idx.replace("not in NDB-UFES", "Not in NDB-UFES"), *[cell(int(v), counts.loc[idx].sum()) for v in counts.loc[idx]], f"{counts.loc[idx].sum():,}"] for idx in counts.index]
    rows.append(["Total", *[cell(int(v), counts.values.sum()) for v in counts.sum()], f"{counts.values.sum():,}"])
    out.append(table("patch-vs-picture", "Patches by the diagnosis of their picture in NDB-UFES (rows) and their own class (columns). The share is of the row.", ["NDB-UFES diagnosis", *CLASSES, "Total"], rows, "lrrrr",
                     [("", 1), ("Patch class", 3), ("", 1)]))
    # the leakage-safe folds
    folds = pd.read_csv(organizer / "results/phase1/folds/fold_summary.csv", dtype=str)
    folds = folds[folds["fold"].isin([*map(str, range(6)), "total"])]  # the last lines of the table are the ideal share and the largest gap
    n = folds.set_index("fold")[["groups", "patches", "Dys-", "Dys+", "OSCC"]].astype(float).astype(int)
    rows = [[{"5": "6 (test)", "total": "Total"}.get(fold) or str(int(fold) + 1),
             cell(r["groups"], n.loc["total", "groups"]), cell(r["patches"], n.loc["total", "patches"]),
             *[cell(r[c], r["patches"]) for c in ("Dys-", "Dys+", "OSCC")]] for fold, r in n.iterrows()]
    six = n.drop("total")  # the mean fold: the average count of a fold and its share (of the total, 100 / 6, for the first two columns; of the mean fold for the labels)
    mean = lambda n_mean, share: f"{n_mean:,.1f} ({share:.1f}%)"  # noqa: E731
    rows.append(["Mean", *[mean(six[c].mean(), (100 * six[c] / n.loc["total", c]).mean()) for c in ("groups", "patches")],
                 *[mean(six[c].mean(), 100 * six[c].mean() / six["patches"].mean()) for c in ("Dys-", "Dys+", "OSCC")]])  # the share of the mean fold, so it matches the total row
    out.append(table("folds", "The leakage-safe folds: case groups and patches (the share is of the total) and the label of the patches (the share is of the fold).",
                     ["Fold", "Case groups", "Patches", "Without dysplasia", "With dysplasia", "OSCC"], rows, "lrrrrr", size="footnotesize"))
    # the published folds: the same table (3 duplicate patches were dropped from both), with the case groups found in each fold
    old = pd.read_csv(organizer / "results/phase1/folds/fold_assignments_published.csv").dropna(subset=["fold"])
    old = old.assign(fold=old["fold"].astype(int)).merge(pd.read_csv(organizer / "results/phase1/folds/fold_assignments.csv")[["patch_id", "case_group"]], on="patch_id", suffixes=("_patch", ""))
    labels = ["Leukoplakia without dysplasia", "Leukoplakia with dysplasia", "OSCC"]
    per_fold = old.groupby("fold").agg(groups=("case_group", "nunique"), patches=("patch_id", "size"))
    per_fold = per_fold.join(old.groupby(["fold", "patch_diagnosis"]).size().unstack()[labels].set_axis(["Dys-", "Dys+", "OSCC"], axis=1))
    per_fold.loc["total"] = [old["case_group"].nunique(), len(old), *old["patch_diagnosis"].value_counts()[labels]]
    rows = [[{5: "6 (test)", "total": "Total"}.get(fold) or str(fold + 1),
             cell(r["groups"], per_fold.loc["total", "groups"]), cell(r["patches"], per_fold.loc["total", "patches"]),
             *[cell(r[c], r["patches"]) for c in ("Dys-", "Dys+", "OSCC")]] for fold, r in per_fold.iterrows()]
    out.append(table("folds-published", "The published folds: case groups with at least one patch in the fold and patches (the share is of the total) and the label of the patches (the share is of the fold).",
                     ["Fold", "Case groups", "Patches", "Without dysplasia", "With dysplasia", "OSCC"], rows, "lrrrrr", size="footnotesize"))
    # the folds by possible zoom and class (the zoom belongs to the picture, and is empty for pictures where it was not set)
    zoom_of = pd.read_csv(organizer / "results/phase0/dataset_tables/patch_table_public.csv", dtype=str, keep_default_na=False).set_index("patch_id")["possible_zoom"]
    zooms = [z for z in ("10x", "40x") if (zoom_of == z).any()] + (["not set"] if (zoom_of == "").any() else [])
    for e, file, first in ((1, "fold_assignments_published.csv", True), (2, "fold_assignments.csv", False)):
        assigned = pd.read_csv(organizer / "results/phase1/folds" / file, dtype=str).dropna(subset=["fold"])
        assigned = assigned.assign(fold=assigned["fold"].astype(float).astype(int), zoom=assigned["patch_id"].map(zoom_of).replace("", "not set"))
        counts = assigned.groupby(["fold", "zoom", "patch_diagnosis"]).size()
        count = lambda fold, z, label, counts=counts: int(counts.get((fold, z, label), 0))  # noqa: E731
        rows = []
        for fold in [*range(6), "Total"]:
            of_fold = assigned if fold == "Total" else assigned[assigned["fold"] == fold]
            rows.append([{5: "6 (test)", "Total": "Total"}.get(fold) or str(fold + 1),
                         *[cell((of_fold[(of_fold["zoom"] == z) & (of_fold["patch_diagnosis"] == label)]).shape[0], len(of_fold)) for z in zooms for label in labels]])
        out.append(table(f"folds-zoom-{e}", f"{EXPERIMENT_NAME[e]}: patches of each fold by possible zoom and class. The share is of the patches of the fold.",
                         ["Fold", *[c for _ in zooms for c in CLASSES]], rows, "l" + "r" * (3 * len(zooms)), [("", 1), *[(z, 3) for z in zooms]], fit=True))
    # the training protocol, read from the params file of the training repository (the same for both experiments)
    import yaml  # the only place the thesis export reads a YAML file

    params = yaml.safe_load((organizer.resolve().parent / "ndb_ufes_training_pipeline/params.yaml").read_text())
    hyper, scheduler, stopping = params["hyperparameters"], params["hyperparameters"]["scheduler"]["other"], params["early_stopping"]
    rows = [["Training", "fine-tuning of all the layers (end to end)"],
            ["Optimizer", f"SGD, learning rate {hyper['optimizer']['learning_rate']}, momentum {hyper['optimizer']['momentum']}"],
            ["Scheduler", f"ReduceLROnPlateau on the validation loss (factor {scheduler['factor']}, patience {scheduler['patience']}, minimum learning rate $10^{{{int(f"{scheduler['min_lr']:.0e}".split('e')[1])}}}$)"],
            ["Loss", "cross-entropy with a weight for each class" if hyper["other"]["loss_weights"] else "cross-entropy"],
            ["Epochs", f"up to {hyper['other']['epochs']}"],
            ["Early stopping", f"patience {stopping['patience']} epochs, minimum improvement {stopping['min_delta']}"],
            ["Batch size", hyper["other"]["batch_size"]],
            ["Folds", "5-fold cross-validation (folds 1 to 5) and one fold (6) only for testing"],
            ["Seed", params["seed"]]]
    out.append(table("training-parameters", "Training parameters, the same for both experiments and all models.", ["Parameter", "Value"], rows, "lp{0.7\\textwidth}"))
    # the models: both experiments and the article
    art = pd.read_csv(article)
    order = list(summary[2]["model"])
    rows = []
    for m in order:
        a = art[art["model"] == m]
        rows.append([name(m), f"{a['bcc'].item():.1f} $\\pm$ {a['bcc_sd'].item():.1f}" if len(a) else "-", *[summary[e].set_index("model").loc[m, "balanced acc patch"] for e in (1, 2)]])
    out.append(table("bcc-article", "Balanced accuracy (\\%, mean $\\pm$ standard deviation over the five fold runs) on the test fold: the original article, and this work on the published and the leakage-safe folds. The best of each column is in bold.",
                     ["Model", "Article", "Experiment 1", "Experiment 2"], bold_best(rows), "lrrr"))
    for e in (1, 2):
        # the caption says (%), so the recall cells have no sign, as in the other columns
        rows = [[name(r["model"]), r["balanced acc patch"], r["balanced acc picture"], r["balanced acc patient"], r["ROC AUC"], *[str(r[f"recall {k}"]).replace("%", "") for k in KEYS]] for _, r in summary[e].iterrows()]
        out.append(table(f"results-{e}", f"{EXPERIMENT_NAME[e]}: balanced accuracy of the patch, picture and patient calls, macro ROC AUC, and recall by class (\\%). The best of each column is in bold.",
                         ["Model", "Patch", "Picture", "Patient", "ROC AUC", *CLASSES], bold_best(rows), "lrrrrrrr", [("", 1), ("Balanced accuracy", 3), ("", 1), ("Recall", 3)], fit=True))
    # per class AUC
    rows = [[name(r["model"]), *[r[f"AUC {k}"] for k in KEYS]] for _, r in summary[2].iterrows()]
    out.append(table("auc-class", "Experiment 2: ROC AUC of each class against the other two (\\%, mean $\\pm$ standard deviation).", ["Model", *CLASSES], rows, "lrrr"))
    # the ranking of the models
    ranking = pd.read_csv(results / "experiment_2/model_ranking.csv")
    rows = [[name(r["model"]), r["family"], f"{r['mean_rank']:.1f}", f"{r['balanced_acc_mean']:.1f} $\\pm$ {r['balanced_acc_std']:.1f}"] for _, r in ranking.iterrows()]
    out.append(table("ranking", "Experiment 2: the architectures by mean rank over the fold runs.", ["Model", "Family", "Mean rank", "Balanced accuracy (\\%)"], rows, "llrr"))
    # patch label and picture diagnosis: what the models call (test fold, consensus of the 12 models)
    panel = pd.read_csv(results / "experiment_2/panel_patches.csv", keep_default_na=False)
    rows, seen = [], set()
    for label in CLASSES:
        for parent_name in ["OSCC", "With dysplasia", "Without dysplasia", "not in NDB-UFES"]:
            part = panel[(panel["label"] == label) & (panel["parent"] == parent_name)]
            if len(part):
                rows.append([label if label not in seen else "", parent_name, len(part), part["histopath_id"].nunique(),
                             *[f"{100 * (part['consensus'] == c).mean():.0f}\\%" for c in CLASSES]])
                seen.add(label)
    out.append(table("calls-by-parent", "Experiment 2, test fold: the share of the patches of each label and picture diagnosis that most of the 12 models assign to each class.",
                     ["Patch label", "Picture diagnosis", "Patches", "Pictures", *CLASSES], rows, "llrrrrr", [("", 4), ("Models say (\\% of the patches)", 3)], fit=True))
    # zoom
    for e in (1, 2):
        zoom = test_zoom(results, e)
        zoom = zoom[zoom["model"] == "all models"]
        total = {z: sum(zoom[(zoom["zoom"] == z) & (zoom["true"] == t) & (zoom["predicted"] == t)]["patches"].item() for t in CLASSES) for z in ("10x", "40x")}
        rows = []
        for t in CLASSES:
            for z in ("10x", "40x"):
                cells = {p: zoom[(zoom["zoom"] == z) & (zoom["true"] == t) & (zoom["predicted"] == p)].iloc[0] for p in CLASSES}
                n = cells[t]["patches"]
                rows.append([t if z == "10x" else "", z.replace("x", "×"), f"{n} ({100 * n / total[z]:.0f}\\%)", cells[t]["pictures"], *[f"{cells[p]['share of true class %']:.1f}\\%" for p in CLASSES]])
        out.append(table(f"zoom-{e}", f"{EXPERIMENT_NAME[e]}, test fold: recall by possible zoom (the 12 models added up). Patches: count and share of the patches at that zoom.",
                         ["True class", "Zoom", "Patches", "Pictures", *CLASSES], rows, "llrrrrr", [("", 4), ("Predicted (\\% of the true class)", 3)], fit=True))
    return out


def test_zoom(results: Path, experiment: int) -> pd.DataFrame:
    """The confusion cells by possible zoom on the test fold (Experiment 1 has no column for what the predictions are on)."""
    zoom = pd.read_csv(results / f"experiment_{experiment}/confusion_by_zoom.csv")
    return zoom[zoom["predictions on"] == "test fold"] if "predictions on" in zoom else zoom


PATCH = 512  # the side of a patch, in pixels of the picture
OVERLAP_BINS = [(0, 25), (25, 50), (50, 75), (75, 99.999)]  # the share of the area that two patches have in common, in per cent: over the lower limit, up to the upper
FULL = 99.999  # two patches with the same box have all their area in common


def overlap_label(low: float, high: float) -> str:
    return f"Over {low:g} to under 100%" if high == FULL else f"Over {low:g} to {high:g}%"


def overlapping_pairs(organizer: Path) -> tuple[pd.DataFrame, list[str]]:
    """Every pair of patches of one picture, with the share of a patch that they have in common (0 when the boxes do not intersect), over all 3,763 patches (the three patches
    that have exactly the same pixels as another one are counted, and overlap their twin completely); the second result is the list of the patches."""
    patches = pd.read_csv(organizer / "results/phase0/dataset_tables/patch_table_public.csv", dtype=str, keep_default_na=False)
    rows = []
    for picture, group in patches.groupby("histopath_id"):
        boxes, ids = group[["x", "y", "x2", "y2"]].astype(int).to_numpy(), group["patch_id"].to_numpy()
        for i, j in combinations(range(len(boxes)), 2):
            width, height = min(boxes[i, 2], boxes[j, 2]) - max(boxes[i, 0], boxes[j, 0]), min(boxes[i, 3], boxes[j, 3]) - max(boxes[i, 1], boxes[j, 1])
            rows.append({"picture": picture, "a": ids[i], "b": ids[j], "shared": 100 * max(width, 0) * max(height, 0) / PATCH**2})
    return pd.DataFrame(rows), list(patches["patch_id"])


def overlap_table(pairs: pd.DataFrame) -> str:
    """The pairs of patches of one picture by the share of area they have in common: none (the boxes do not intersect), bins of a quarter of a patch, and all of it (the same box)."""
    rows = [["No intersection (0%)", f"{int((pairs['shared'] == 0).sum()):,}", f"{100 * (pairs['shared'] == 0).mean():.1f}"]]
    for low, high in OVERLAP_BINS:
        n = int(((pairs["shared"] > low) & (pairs["shared"] <= high)).sum())
        rows.append([overlap_label(low, high), f"{n:,}", f"{100 * n / len(pairs):.1f}"])
    full = int((pairs["shared"] > FULL).sum())
    rows.append(["All the area (100%)", f"{full:,}", "<0.1" if 0 < 100 * full / len(pairs) < 0.05 else f"{100 * full / len(pairs):.1f}"])  # a few pairs: do not show 0.0
    rows.append(["Total", f"{len(pairs):,}", "100"])
    return table("overlapping-pairs", "Pairs of patches of one picture by the share of the area they have in common.", ["Area in common", "Pairs", "%"], rows, "lrr")


def overlap_patches_table(pairs: pd.DataFrame, patch_ids: list[str]) -> str:
    """The patches by the highest share of area they have in common with another patch (rows) and by how many other patches they intersect (columns)."""
    both = pd.concat([pairs[["a", "shared"]].rename(columns={"a": "patch"}), pairs[["b", "shared"]].rename(columns={"b": "patch"})])
    both = both[both["shared"] > 0]
    stats = pd.DataFrame(index=patch_ids).join(both.groupby("patch")["shared"].agg(highest="max", neighbours="size")).fillna(0)
    columns = [("None", 0, 0), ("1 to 4", 1, 4), ("5 to 9", 5, 9), ("10 or more", 10, 10**6)]  # how many other patches a patch intersects
    count = lambda part, low, high: int(((part["neighbours"] >= low) & (part["neighbours"] <= high)).sum())  # noqa: E731
    none = stats[stats["neighbours"] == 0]
    rows = [["No intersection (0%)", *[f"{count(none, a, b):,}" for _, a, b in columns], f"{len(none):,} ({100 * len(none) / len(stats):.1f}%)"]]
    parts = [(overlap_label(low, high), stats[(stats["highest"] > low) & (stats["highest"] <= high)]) for low, high in OVERLAP_BINS] + [("All the area (100%)", stats[stats["highest"] > FULL])]
    for title, part in parts:
        rows.append([title, *[f"{count(part, a, b):,}" for _, a, b in columns], f"{len(part):,} ({100 * len(part) / len(stats):.1f}%)"])
    rows.append(["Total", *[f"{count(stats, a, b):,}" for _, a, b in columns], f"{len(stats):,} (100%)"])
    return table("overlapping-patches", "Patches by the highest share of area they have in common with another patch of their picture (rows) and by the number of other patches they intersect (columns).",
                 ["Highest area in common", *[name for name, _, _ in columns], "Patches"], rows, "lrrrrr", [("", 1), ("Patches it intersects", 4), ("", 1)])


def overlap_histogram(pairs: pd.DataFrame, path: Path) -> None:
    """The share of area in common of the pairs that intersect."""
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "text.color": "#222222", "axes.labelcolor": "#222222", "xtick.color": "#222222",
                         "ytick.color": "#222222", "axes.edgecolor": "#222222", "figure.facecolor": "white", "axes.facecolor": "white", "savefig.transparent": False})
    fig, ax = plt.subplots(figsize=(7.5, 4))
    ax.hist(pairs.loc[pairs["shared"] > 0, "shared"], bins=np.arange(0, 105, 5), color=COLOR[2])  # the pairs with an intersection
    ax.set_xlabel("Area in common of two overlapping patches of one picture (% of a patch)")
    ax.set_ylabel("Pairs of patches")
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


def zoom_balanced(results: Path) -> pd.DataFrame:
    """Balanced accuracy (the mean of the three recalls) of each model and of all together, by possible zoom and experiment."""
    rows = []
    for e in (1, 2):
        zoom = test_zoom(results, e)
        zoom = zoom[zoom["true"] == zoom["predicted"]]
        for (model, z), part in zoom.groupby(["model", "zoom"]):
            rows.append({"experiment": e, "model": model, "zoom": z, "balanced accuracy": part["share of true class %"].mean()})
    return pd.DataFrame(rows)


def zoom_table(results: Path) -> str:
    data = zoom_balanced(results)
    order = list(pd.read_csv(results / "experiment_2/summary.csv", dtype=str)["model"]) + ["all models"]
    rows = []
    for m in order:
        cells = [f"{data[(data['experiment'] == e) & (data['model'] == m) & (data['zoom'] == z)]['balanced accuracy'].item():.1f}\\%" for e in (1, 2) for z in ("10x", "40x")]
        rows.append([name(m) if m != "all models" else "All", *cells])
    return table("bcc-zoom", "Balanced accuracy by possible zoom on the test fold of each experiment (the folds differ; the fold runs of a model and, in the last line, the 12 models are added up).",
                 ["Model", "10$\\times$", "40$\\times$", "10$\\times$", "40$\\times$"], rows, "lrrrr", [("", 1), (EXPERIMENT_NAME[1], 2), (EXPERIMENT_NAME[2], 2)])


def charts(project: Path, results: Path) -> list[Path]:
    out = project / "figuras/resultados"
    out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "text.color": "#222222", "axes.labelcolor": "#222222", "xtick.color": "#222222",
                         "ytick.color": "#222222", "axes.edgecolor": "#222222", "legend.labelcolor": "#222222", "figure.facecolor": "white", "axes.facecolor": "white", "savefig.transparent": False})
    summary = {e: pd.read_csv(results / f"experiment_{e}/summary.csv", dtype=str) for e in (1, 2)}
    parse = lambda text: tuple(float(x) for x in str(text).split("±"))  # noqa: E731
    order = sorted(summary[2]["model"], key=lambda m: parse(summary[2].set_index("model").loc[m, "balanced acc patch"])[0])
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for e in (1, 2):
        values = [parse(summary[e].set_index("model").loc[m, "balanced acc patch"]) for m in order]
        ax.errorbar([v[0] for v in values], range(len(order)), xerr=[v[1] for v in values], fmt="o", color=COLOR[e], label=EXPERIMENT_NAME[e], capsize=3)
    ax.axvline(100 / 3, color="gray", linestyle="--", linewidth=1)
    ax.text(100 / 3 + 0.5, len(order) - 0.6, "chance (3 classes)", color="gray", fontsize=8)
    ax.set_yticks(range(len(order)), [name(m) for m in order])
    ax.set_xlabel("Balanced accuracy per patch (%), mean ± sd over the five fold runs")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(out / "balanced_accuracy_both_experiments.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    fig, axes = plt.subplots(3, 2, figsize=(8, 11.5), sharex=True, sharey=True)  # a row for each class, a column for each experiment
    for col, e in enumerate((1, 2)):
        curves = pd.read_csv(results / f"experiment_{e}/roc_curves.csv")
        for row, c in enumerate(CLASSES):
            for k, (m, part) in enumerate(curves[curves["class"] == c].groupby("model")):
                axes[row, col].plot(part["fpr"], part["tpr"], linewidth=1, color=plt.cm.tab20(k), linestyle="-" if k < 10 else "--", label=name(m))
            axes[row, col].plot([0, 1], [0, 1], "--", color="gray", linewidth=1)
            axes[row, col].set_title((f"{EXPERIMENT_NAME[e]}\n" if row == 0 else "") + c, fontsize=10)
            axes[row, col].set_aspect("equal")
    for ax in axes[2]:
        ax.set_xlabel("False-positive rate")
    for ax in axes[:, 0]:
        ax.set_ylabel("True-positive rate")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=6, frameon=False, fontsize=8)  # one key for all panels, below them
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(out / "roc_curves_both_experiments.png", dpi=300)
    plt.close(fig)
    recall = pd.concat([test_zoom(results, e).assign(experiment=e) for e in (1, 2)])
    recall = recall[(recall["true"] == recall["predicted"]) & (recall["model"] != "all models")]  # the recall of a class: the share of its patches that the model calls right
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True)
    for ax, c in zip(axes, CLASSES):
        for k, (e, z) in enumerate([(e, z) for e in (1, 2) for z in ("10x", "40x")]):
            part = recall[(recall["experiment"] == e) & (recall["zoom"] == z) & (recall["true"] == c)]
            ax.bar(np.full(len(part), k) + np.linspace(-0.3, 0.3, len(part)), part["share of true class %"], width=0.045, color=COLOR[e], alpha=1 if z == "10x" else 0.45)
        ax.set_xticks(range(4), ["Exp. 1\n10×", "Exp. 1\n40×", "Exp. 2\n10×", "Exp. 2\n40×"], fontsize=8)
        ax.set_title(c, fontsize=10)
    axes[0].set_ylabel("Recall (%) of each model")
    fig.tight_layout()
    fig.savefig(out / "recall_by_zoom.png", dpi=300)
    plt.close(fig)
    data = zoom_balanced(results)
    data = data[data["model"] != "all models"]
    fig, ax = plt.subplots(figsize=(7.5, 4))
    for k, (e, z) in enumerate([(e, z) for e in (1, 2) for z in ("10x", "40x")]):
        part = data[(data["experiment"] == e) & (data["zoom"] == z)]
        ax.bar(np.full(len(part), k) + np.linspace(-0.3, 0.3, len(part)), part["balanced accuracy"], width=0.045, color=COLOR[e], alpha=1 if z == "10x" else 0.45)
    ax.set_xticks(range(4), ["Exp. 1\n10×", "Exp. 1\n40×", "Exp. 2\n10×", "Exp. 2\n40×"])
    ax.set_ylabel("Balanced accuracy (%) of each model")
    ax.axhline(100 / 3, color="gray", linestyle="--", linewidth=1)
    fig.tight_layout()
    fig.savefig(out / "balanced_accuracy_by_zoom.png", dpi=300)
    plt.close(fig)
    return sorted(out.glob("*.png"))


CAPTIONS = {  # file (without folder) -> label, draft caption
    "cluster_choices": ("fig:cluster-choices", "Choice of the number of PCA components and of morphology clusters."),
    "cluster_examples": ("fig:cluster-examples", "The most typical patches of each morphology cluster."),
    "embedding_view": ("fig:embedding-view", "Patches in the first two PCA components of their embedding, by label and by morphology cluster."),
    "fold_balance": ("fig:fold-balance", "Spread of each balanced characteristic across the folds, for the original and the new folds."),
    "fold_distances": ("fig:fold-distances", "Distances between the folds."),
    "fold_largest_groups": ("fig:fold-largest-groups", "The largest groups of related patches and the folds that hold them."),
    "ndb_correlations": ("fig:ndb-correlations", "Correlations between the metadata of NDB-UFES."),
    "ndb_distributions": ("fig:ndb-distributions", "Distributions of the metadata of NDB-UFES."),
    "ndb_images_with_patches": ("fig:ndb-images-with-patches", "Pictures of NDB-UFES with and without patches."),
    "patch_correlations": ("fig:patch-correlations", "Correlations between the characteristics of the patches."),
    "patch_labels": ("fig:patch-labels", "Labels of the patches of P-NDB-UFES."),
    "patch_vs_picture": ("fig:patch-vs-picture", "Label of each patch against the diagnosis of its picture: same, less severe or more severe."),
    "patches_per_picture": ("fig:patches-per-picture", "Number of patches cut from each picture."),
    "related_zoom": ("fig:related-zoom", "Zoom between related pictures found by SIFT."),
    "sab_folders": ("fig:sab-folders", "Pictures by the folder of the internal dataset and the diagnosis in NDB-UFES."),
    "class_examples_pictures": ("fig:class-examples-pictures", "One picture of NDB-UFES of each class."),
    "class_examples_patches": ("fig:class-examples-patches", "One patch of P-NDB-UFES of each class."),
    "template_scores": ("fig:template-scores", "Template matching: the patch and three windows of the picture with their scores."),
    "template_map": ("fig:template-map", "Template matching: the score at every position of the patch in the picture."),
    "template_pixels": ("fig:template-pixels", "Template matching: the pixel check of the best window in the patch's own picture and in another one."),
    "opencv_template_matching_mario": ("fig:opencv-mario", "Template matching of a coin in a game screenshot."),
    "picture_with_patches": ("fig:picture-with-patches", "A picture with the patches cut from it, colored by label."),
    "sift_scales": ("fig:sift-scales", "SIFT: the blurred picture, the difference between blur levels, and the keypoints found."),
    "sift_descriptor": ("fig:sift-descriptor", "SIFT: a keypoint, its main direction and its 128-number descriptor."),
    "sift_rule": ("fig:sift-rule", "SIFT: matches that follow one zoom, turn and shift, found with RANSAC."),
    "sift_example": ("fig:sift-example", "SIFT matches between two related pictures."),
    "parent_zoom": ("fig:parent-zoom", "A picture and its close-up."),
    "parent_shift": ("fig:parent-shift", "A shifted field of the same tissue."),
    "shift_intersection": ("fig:shift-intersection", "Two pictures of the same field, each cut down to the tissue that both show, with the patches inside it."),
    "shift_patch_pairs": ("fig:shift-patch-pairs", "The patches of the first picture put in the frame of the second: the pairs of patches that overlap, and the three with the largest area in common."),
    "parent_same_patient": ("fig:parent-same-patient", "Pictures of the same patient that show different tissue."),
    "more_severe_1": ("fig:more-severe-1", "A picture and its patches: patches labeled more severe than the picture (example 1)."),
    "more_severe_2": ("fig:more-severe-2", "A picture and its patches: patches labeled more severe than the picture (example 2)."),
    "more_severe_3": ("fig:more-severe-3", "A picture and its patches: patches labeled more severe than the picture (example 3)."),
    "more_severe_4": ("fig:more-severe-4", "A picture and its patches: patches labeled more severe than the picture (example 4)."),
    "more_severe_5": ("fig:more-severe-5", "A picture and its patches: patches labeled more severe than the picture (example 5)."),
    "contamination_picture": ("fig:contamination-picture", "One picture whose patches fall in several of the published folds."),
    "contamination_pair": ("fig:contamination-pair", "The same tissue in a test patch and a training patch of the published folds."),
    "contamination_patient": ("fig:contamination-patient", "One patient whose patches fall on both sides of the published folds: two pictures of the same field, with the patches in the test fold and in the training folds."),
    "contamination_patient_pair": ("fig:contamination-patient-pair", "The same tissue in a test patch and a training patch cut from two different pictures of one patient."),
    "balanced_accuracy_both_experiments": ("fig:bcc-both", "Balanced accuracy per patch of the 12 models on the published and the leakage-safe folds."),
    "roc_curves_both_experiments": ("fig:roc-both", "ROC curves of each class against the other two, for the 12 models, in both experiments."),
    "overlap_histogram": ("fig:overlap-histogram", "Area in common of the overlapping pairs of patches of one picture."),
    "balanced_accuracy_by_zoom": ("fig:bcc-zoom", "Balanced accuracy of the 12 models by possible zoom, in both experiments."),
    "recall_by_zoom": ("fig:recall-zoom", "Recall of each class of the 12 models by possible zoom, in both experiments."),
}


SECTIONS = [  # the sections of the thesis the items belong to (the outline of the thesis): title, figure files, table labels
    ("Datasets", ["class_examples_pictures", "class_examples_patches", "ndb_distributions", "ndb_correlations", "ndb_images_with_patches", "patch_labels", "patch_correlations",
                  "patches_per_picture", "sab_folders"], ["datasets", "ndb-metadata", "sab-folders", "patches-data", "pictures-with-patches", "patient-sources", "picture-groups", "groups-vs-patients", "sab-vs-ndb", "sab-benign-patches", "sab-folder-patches"]),
    ("Data leakage: linking the patches, template matching", ["opencv_template_matching_mario", "template_scores", "template_map", "template_pixels", "picture_with_patches"], []),
    ("Data leakage: linking the pictures, SIFT", ["sift_scales", "sift_descriptor", "sift_rule", "sift_example", "parent_zoom", "parent_shift", "shift_intersection", "shift_patch_pairs", "parent_same_patient", "related_zoom"], []),
    ("Data leakage: contamination, labels and folds", ["patch_vs_picture", "more_severe_1", "more_severe_2", "more_severe_3", "more_severe_4", "more_severe_5", "contamination_picture", "contamination_pair", "contamination_patient", "contamination_patient_pair",
                                                      "embedding_view", "cluster_examples", "cluster_choices", "fold_balance", "fold_distances", "fold_largest_groups", "overlap_histogram"], ["patch-vs-picture", "overlapping-pairs", "overlapping-patches", "folds", "folds-published", "folds-zoom-1", "folds-zoom-2"]),
    ("Experimental results", ["balanced_accuracy_both_experiments", "roc_curves_both_experiments"], ["bcc-article", "results-1", "results-2", "auc-class", "ranking"]),
    ("Discussion: dysplasia and the possible zoom", ["balanced_accuracy_by_zoom", "recall_by_zoom"], ["calls-by-parent", "zoom-1", "zoom-2", "bcc-zoom"]),
]


def figure_block(path: Path, folder: str, root: str = "figuras") -> list[str]:
    label, caption = CAPTIONS.get(path.stem, (f"fig:{path.stem.replace('_', '-')}", path.stem.replace("_", " ")))
    return ["\\begin{figure}[htb]", "\\centering", f"\\caption{{{caption}}}", f"\\label{{{label}}}", f"\\includegraphics[width=\\textwidth]{{{root}/{folder}/{path.name}}}",
            "\\par\\small " + ("Source: OpenCV documentation~\\cite{opencv_template_matching}." if path.stem == "opencv_template_matching_mario" else "Source: the author."), "\\end{figure}", ""]


def catalog(project: Path, root: str = "figuras", folders: tuple[str, ...] = ("dados", "slides", "resultados")) -> str:
    """The figures of the project (those in ``folders``) as figure blocks that read them from ``root``, under the sections of the thesis; the figures that no section names come last."""
    files = {path.stem: (folder, path) for folder in folders for path in sorted((project / "figuras" / folder).glob("*")) if path.suffix.lower() in (".png", ".jpg")}
    blocks = ["% Every figure of the project as a figure block, by section of the thesis: copy what you need into a chapter and edit the caption. Generated by scripts/phase2.py thesis.", ""]
    for title, stems, _ in SECTIONS:
        blocks += [f"\\section{{{title}}}", ""]
        for stem in stems:
            if stem in files:
                folder, path = files.pop(stem)
                blocks += figure_block(path, folder, root)
    if files:
        blocks += ["\\section{Other figures}", ""]
        for folder, path in files.values():
            blocks += figure_block(path, folder, root)
    return "\n".join(blocks)


def table_sections(body: list[str]) -> str:
    """The tables under the sections of the thesis, found by their labels; the tables that no section names come last."""
    found = {re.search(r"\\label\{tab:([^}]*)\}", text).group(1): text for text in body}
    parts = []
    for title, _, labels in SECTIONS:
        if any(label in found for label in labels):
            parts += [f"\\section{{{title}}}", ""] + [found.pop(label) + "\n" for label in labels if label in found]
    if found:
        parts += ["\\section{Other tables}", ""] + [text + "\n" for text in found.values()]
    return "\n".join(parts)


def copy_slide_figures(project: Path, figures: Path, opencv: Path, width: int = 2200) -> int:
    """The figures of the slides that the thesis may mention, copied to ``figuras/slides`` and reduced to at most ``width`` pixels (an Overleaf upload is limited in size)."""
    out = project / "figuras/slides"
    out.mkdir(parents=True, exist_ok=True)
    sources = [(figures / f"{stem}.png", out / f"{stem}.png") for stem in CAPTIONS if (figures / f"{stem}.png").exists()] + [(opencv, out / "opencv_template_matching_mario.jpg")]
    for source, target in sources:
        with Image.open(source) as image:
            if image.width > width:
                image = image.resize((width, round(image.height * width / image.width)), Image.Resampling.LANCZOS)
            image.save(target, optimize=True)
    return len(sources)


def run_thesis(args: argparse.Namespace) -> dict:
    project, results = Path(args.project), Path(args.results)
    if args.catalog_file:  # only the figure blocks of the slide figures, for a project whose images are in another folder
        args.catalog_file.write_text(catalog(project, args.image_root, ("slides",)) + "\n")
        return {"catalog": str(args.catalog_file)}
    logger.info(f"{copy_slide_figures(project, Path(args.figures), Path(args.opencv_image))} figures of the slides copied")
    charts(project, results)
    body = tables(project, results, Path(args.article), Path("."))
    pairs, counted = overlapping_pairs(Path("."))
    body.append(overlap_table(pairs))
    body.append(overlap_patches_table(pairs, counted))
    overlap_histogram(pairs, project / "figuras/resultados/overlap_histogram.png")
    body.append(zoom_table(results))
    (project / "capitulos").mkdir(exist_ok=True)
    (project / "capitulos/rascunho-tabelas.tex").write_text(
        "\\chapter{Tables for drafting}\n\\label{ch-rascunho-tabelas}\n\\hl{Draft: copy the tables you need into the chapters and delete this chapter before submitting.}\n\n" + table_sections(body) + "\n")
    (project / "capitulos/rascunho-figuras.tex").write_text("\\chapter{Figures for drafting}\n\\label{ch-rascunho-figuras}\n\\hl{Draft: copy the figures you need into the chapters and delete this chapter before submitting.}\n\n" + catalog(project) + "\n")
    logger.info(f"{len(body)} tables and the figure catalog written under {project}")
    return {"tables": len(body), "project": str(project)}


def thesis_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True, help="The folder of the Overleaf project (it holds main.tex).")
    parser.add_argument("--results", type=Path, default=EXPERIMENTS)
    parser.add_argument("--image-root", default="figuras", help="The folder of the Overleaf project that holds the images (figuras/slides/...), for the figure blocks.")
    parser.add_argument("--catalog-file", type=Path, help="Write only the figure blocks of the slide figures to this file and stop.")
    parser.add_argument("--article", type=Path, default=ARTICLE, help="The table of the article with the original results.")
    parser.add_argument("--figures", type=Path, default=Path("../presentation/web/figures"), help="The figures of the slides (scripts/phase2.py slides).")
    parser.add_argument("--opencv-image", type=Path, default=Path("../presentation/web/img/template/res_mario.jpg"), help="The OpenCV tutorial image of the template matching slide.")
    return parser
