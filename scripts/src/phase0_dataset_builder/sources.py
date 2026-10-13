from __future__ import annotations

import argparse
import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from src.utils.logger import logger


# Where the data lives
DEFAULT_NDB_ORIGIN_DIR = Path("data/ndb_ufes/origin_level/images")
DEFAULT_SAB_ROOT = Path("data/SAB")
DEFAULT_PATCH_IMAGE_DIR = Path("data/ndb_ufes/patch_level/images")
DEFAULT_SAB_PARSED_CSVS = [
    Path("data/ndb_ufes/patch_level/csvs/sabpatch_parsed_folders.csv"),
    Path("data/ndb_ufes/patch_level/csvs/sabpatch_parsed_test.csv"),
]
SAB_PATCHES_DIR = Path("data/patches_data")  # <split>/<class>/<sab patch name>.png
DEFAULT_SAB_NAMES_CSV = Path("data/ndb_ufes/patch_level/csvs/sab_patch_names.csv")  # patch id, SAB file name (private)
NDB_METADATA = Path("data/ndb_ufes/origin_level/csvs/ndb-ufes.csv")

# Where each stage writes what a later stage reads
PHASE0_RESULTS = Path("results/phase0")
POOL_MATCHES = PHASE0_RESULTS / "patch_pool_search" / "patch_pool_matches.csv"
PICTURE_FEATURES = PHASE0_RESULTS / "picture_feature_cache" / "picture_features.pkl"
PICTURE_RELATIONS = PHASE0_RESULTS / "picture_relations" / "picture_relations.csv"
PATCH_PLACEMENTS = PHASE0_RESULTS / "patch_placements" / "patch_placements.csv"
PATCH_TABLE_LAB = PHASE0_RESULTS / "dataset_tables" / "private_lab" / "patch_table_lab.csv"
PICTURE_TABLE_LAB = PHASE0_RESULTS / "dataset_tables" / "private_lab" / "picture_table_lab.csv"

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


# Source images: NDB-UFES origins and SAB origins, one pool
class Dataset(str, Enum):
    NDB = "ndb"
    SAB = "sab"


@dataclass(frozen=True)
class SourceImage:
    image_id: str
    dataset: Dataset
    path: Path
    width: int
    height: int
    case_prefix: str | None = None


def pixel_sha256(path: Path) -> str:
    """Hash of the decoded RGB pixels, independent of PNG encoding."""
    with Image.open(path) as image:
        return hashlib.sha256(np.asarray(image.convert("RGB")).tobytes()).hexdigest()


def _image_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)


def _read_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def discover_ndb(ndb_origin_dir: Path) -> list[SourceImage]:
    """NDB-UFES origins are named by their numeric id (``0011.png``); anything else is reported and skipped."""
    images = []
    for path in _image_files(ndb_origin_dir):
        if not path.stem.isdigit():
            logger.warning(f"Skipping non-origin file in NDB origin folder: {path.name}")
            continue
        width, height = _read_size(path)
        images.append(SourceImage(f"{Dataset.NDB.value}:{path.stem}", Dataset.NDB, path, width, height))
    return images


def discover_sab(sab_root: Path) -> list[SourceImage]:
    """SAB origins live in one sub-folder per diagnosis; the case prefix is the file-name prefix."""
    images = []
    for folder in sorted(p for p in sab_root.iterdir() if p.is_dir()):
        for path in _image_files(folder):
            width, height = _read_size(path)
            case_prefix = path.stem.split("_", 1)[0]
            images.append(
                SourceImage(f"{Dataset.SAB.value}:{path.stem}", Dataset.SAB, path, width, height, case_prefix)
            )
    return images


def discover_pool(ndb_origin_dir: Path, sab_root: Path) -> list[SourceImage]:
    pool = discover_ndb(ndb_origin_dir) + discover_sab(sab_root)
    ids = [image.image_id for image in pool]
    if len(ids) != len(set(ids)):
        raise ValueError("Source image ids must be unique across the combined pool")
    return pool


# Pictures: pool files with identical pixels are one picture
@dataclass(frozen=True)
class HistopathImage:
    histopath_id: str
    files: tuple[SourceImage, ...]

    @property
    def datasets(self) -> frozenset[Dataset]:
        return frozenset(file.dataset for file in self.files)

    @property
    def case_prefixes(self) -> frozenset[str]:
        return frozenset(file.case_prefix for file in self.files if file.case_prefix)

    @property
    def dataset_names(self) -> str:
        return "+".join(sorted(dataset.value for dataset in self.datasets))

    @property
    def sab_files(self) -> tuple[SourceImage, ...]:
        return tuple(file for file in self.files if file.dataset is Dataset.SAB)

    @property
    def sab_folders(self) -> frozenset[str]:
        return frozenset(file.path.parent.name for file in self.sab_files)

    @property
    def ndb_origin_id(self) -> str | None:
        stems = sorted(file.path.stem for file in self.files if file.dataset is Dataset.NDB)
        return stems[0] if stems else None


def histopath_id_from_hash(digest: str) -> str:
    """Deterministic id: the same picture gets the same id on every run."""
    return f"hp_{digest[:12]}"


def merge_exact_duplicates(pool: list[SourceImage]) -> list[HistopathImage]:
    by_hash: dict[str, list[SourceImage]] = defaultdict(list)
    for image in pool:
        by_hash[pixel_sha256(image.path)].append(image)
    return [
        HistopathImage(histopath_id_from_hash(digest), tuple(sorted(files, key=lambda f: f.image_id)))
        for digest, files in sorted(by_hash.items())
    ]


# Patches: labels from the SAB-parsed tables, names parsed from the SAB file names
class Diagnosis(str, Enum):
    OSCC = "OSCC"
    WITH_DYSPLASIA = "Leukoplakia with dysplasia"
    WITHOUT_DYSPLASIA = "Leukoplakia without dysplasia"


DIAGNOSIS_COLOR = {Diagnosis.OSCC.value: "#d62728", Diagnosis.WITH_DYSPLASIA.value: "#ff7f0e", Diagnosis.WITHOUT_DYSPLASIA.value: "#1f77b4"}
AGE_GROUP_YEARS = {"0": "< 40 years", "1": "40-60 years", "2": "> 60 years"}  # the age group codes of the NDB-UFES metadata
SHORT_LABEL = {Diagnosis.OSCC.value: "OSCC", Diagnosis.WITH_DYSPLASIA.value: "Dys+", Diagnosis.WITHOUT_DYSPLASIA.value: "Dys-"}

SEVERITY = {
    Diagnosis.WITHOUT_DYSPLASIA: 0,
    Diagnosis.WITH_DYSPLASIA: 1,
    Diagnosis.OSCC: 2,
}

SAB_LESION_TO_DIAGNOSIS = {
    "OSCC": Diagnosis.OSCC,
    "With dysplasia": Diagnosis.WITH_DYSPLASIA,
    "Without dysplasia": Diagnosis.WITHOUT_DYSPLASIA,
}

SAB_PATCH_NAME = re.compile(
    r"^(?P<case_prefix>\d{3}\.\d{3}\.\d{3}-\d{2})"
    r"_(?P<photo_uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    r"_(?P<patch_number>\d+)"
    r"(?:\((?P<copy_number>\d+)\))?\.png$"
)


@dataclass(frozen=True)
class SabPatchName:
    """A SAB patch file name, ``<case_prefix>_<photo_uuid>_<patch_number>[(copy)].png``.

    The prefix identifies the patient, the uuid the photo, and prefix + uuid together the SAB
    origin image the patch was cut from. ``copy_number`` is set for names such as ``_10(1).png``.
    These are claims to verify against the images, never ground truth.
    """

    filename: str
    case_prefix: str
    photo_uuid: str
    patch_number: int
    copy_number: int | None = None

    @property
    def origin_image_id(self) -> str:
        return f"{self.case_prefix}_{self.photo_uuid}"


def parse_sab_patch_name(filename: str) -> SabPatchName:
    match = SAB_PATCH_NAME.match(filename)
    if match is None:
        raise ValueError(f"Not a SAB patch name: {filename!r}")
    copy_number = match["copy_number"]
    return SabPatchName(
        filename=filename,
        case_prefix=match["case_prefix"],
        photo_uuid=match["photo_uuid"],
        patch_number=int(match["patch_number"]),
        copy_number=None if copy_number is None else int(copy_number),
    )


@dataclass(frozen=True)
class Patch:
    patch_id: str
    path: Path
    diagnosis: Diagnosis
    sab_name: SabPatchName | None  # None when the names were not loaded, which only the patch search can do without


def load_sab_names(names_csv: Path) -> dict[str, SabPatchName]:
    """Parse each patch's SAB file name from the saved record (patch id, SAB file name).

    The names were recorded by matching the patch images to the SAB patch crops by pixels, which the patch table checks again.
    """
    table = pd.read_csv(names_csv, dtype=str)
    return {row.ndb_patch: parse_sab_patch_name(row.sab_patch_filename) for row in table.itertuples()}


def load_patches(sab_parsed_csvs: list[Path], patch_image_dir: Path, sab_names: dict[str, SabPatchName] | None) -> list[Patch]:
    table = pd.concat([pd.read_csv(path, dtype=str) for path in sab_parsed_csvs], ignore_index=True)
    table["patch_id"] = table["path"].str.removesuffix(".png")
    if table["patch_id"].duplicated().any():
        raise ValueError("A patch appears in more than one SAB-parsed row")
    unknown = set(table["lesion"]) - set(SAB_LESION_TO_DIAGNOSIS)
    if unknown:
        raise ValueError(f"Unknown SAB lesion labels: {sorted(unknown)}")
    missing_names = [] if sab_names is None else sorted(set(table["patch_id"]) - set(sab_names))
    if missing_names:
        raise ValueError(f"{len(missing_names)} patches have no recorded SAB file name, e.g. {missing_names[:3]}")

    patches = []
    for row in table.sort_values("patch_id").itertuples():
        image_path = patch_image_dir / f"{row.patch_id}.png"
        if not image_path.exists():
            raise FileNotFoundError(f"Patch image missing: {image_path}")
        patches.append(
            Patch(
                patch_id=row.patch_id,
                path=image_path,
                diagnosis=SAB_LESION_TO_DIAGNOSIS[row.lesion],
                sab_name=None if sab_names is None else sab_names[row.patch_id],
            )
        )
    return patches


# Loading, shared by every stage
def add_source_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ndb-origin-dir", type=Path, default=DEFAULT_NDB_ORIGIN_DIR)
    parser.add_argument("--sab-root", type=Path, default=DEFAULT_SAB_ROOT)
    parser.add_argument("--patch-image-dir", type=Path, default=DEFAULT_PATCH_IMAGE_DIR)
    parser.add_argument("--sab-parsed-csv", type=Path, nargs="+", default=DEFAULT_SAB_PARSED_CSVS)
    parser.add_argument("--sab-names-csv", type=Path, default=DEFAULT_SAB_NAMES_CSV)


def load_pictures(args: argparse.Namespace) -> list[HistopathImage]:
    return merge_exact_duplicates(discover_pool(args.ndb_origin_dir, args.sab_root))


def load_patch_table(args: argparse.Namespace, with_names: bool = True) -> list[Patch]:
    """The patches with their labels; with ``with_names`` also the SAB file name of each, which is private and which the patch search does not need."""
    return load_patches(args.sab_parsed_csv, args.patch_image_dir, load_sab_names(args.sab_names_csv) if with_names else None)


def format_counts(counts: pd.Series) -> str:
    return "; ".join(f"{name}: {count}" for name, count in counts.items())
