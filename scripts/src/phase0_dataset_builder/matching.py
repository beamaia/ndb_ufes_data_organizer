from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum

import cv2 as cv
import numpy as np

from src.phase0_dataset_builder.sources import HistopathImage


class UnionFind:
    def __init__(self) -> None:
        self._parent: dict[str, str] = {}

    def add(self, item: str) -> None:
        self._parent.setdefault(item, item)

    def find(self, item: str) -> str:
        self.add(item)
        while self._parent[item] != item:
            self._parent[item] = self._parent[self._parent[item]]
            item = self._parent[item]
        return item

    def union(self, a: str, b: str) -> None:
        self._parent[self.find(a)] = self.find(b)


def group_pictures(picture_ids: list[str], strong_pairs: list[tuple[str, str]]) -> dict[str, str]:
    """Connected components over the strong relations: picture id -> group id."""
    union_find = UnionFind()
    for picture_id in picture_ids:
        union_find.add(picture_id)
    for a, b in strong_pairs:
        union_find.union(a, b)
    return {picture_id: union_find.find(picture_id) for picture_id in picture_ids}


# Patch against picture: exact pixels
class MatchStatus(str, Enum):
    EXACT = "exact"
    NEAR = "near"
    NONE = "none"


@dataclass(frozen=True)
class PixelMatch:
    status: MatchStatus
    x: int | None
    y: int | None
    width: int
    height: int
    mean_abs_diff: float | None
    max_abs_diff: int | None

    def as_row(self) -> dict:
        return {
            "status": self.status.value,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "mean_abs_diff": self.mean_abs_diff,
            "max_abs_diff": self.max_abs_diff,
        }


def classify(mean_abs_diff: float, max_abs_diff: int, near_mean: float, near_max: int) -> MatchStatus:
    if max_abs_diff == 0:
        return MatchStatus.EXACT
    if mean_abs_diff <= near_mean and max_abs_diff <= near_max:
        return MatchStatus.NEAR
    return MatchStatus.NONE


def match_patch(
    patch_bgr: np.ndarray,
    image_bgr: np.ndarray,
    image_gray: np.ndarray | None = None,
    near_mean: float = 1.0,
    near_max: int = 5,
) -> PixelMatch:
    patch_height, patch_width = patch_bgr.shape[:2]
    image_height, image_width = image_bgr.shape[:2]
    if image_height < patch_height or image_width < patch_width:
        return PixelMatch(MatchStatus.NONE, None, None, patch_width, patch_height, None, None)

    response = cv.matchTemplate(
        image_gray if image_gray is not None else cv.cvtColor(image_bgr, cv.COLOR_BGR2GRAY),
        cv.cvtColor(patch_bgr, cv.COLOR_BGR2GRAY),
        cv.TM_SQDIFF_NORMED,
    )
    _, _, (x, y), _ = cv.minMaxLoc(response)
    difference = cv.absdiff(patch_bgr, image_bgr[y : y + patch_height, x : x + patch_width])
    mean_abs_diff, max_abs_diff = float(np.mean(difference)), int(np.max(difference))
    status = classify(mean_abs_diff, max_abs_diff, near_mean, near_max)
    return PixelMatch(status, x, y, patch_width, patch_height, mean_abs_diff, max_abs_diff)


def read_bgr(path) -> np.ndarray:
    image = cv.imread(str(path), cv.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image: {path}")
    return image


class PictureCache:
    """Decoded pictures (colour and grey) kept in memory; the least recently used is dropped first."""

    def __init__(self, size: int):
        self._cache: OrderedDict[str, tuple[np.ndarray, np.ndarray]] = OrderedDict()
        self._size = size

    def get(self, picture: HistopathImage) -> tuple[np.ndarray, np.ndarray]:
        if picture.histopath_id in self._cache:
            self._cache.move_to_end(picture.histopath_id)
        else:
            bgr = read_bgr(picture.files[0].path)
            self._cache[picture.histopath_id] = (bgr, cv.cvtColor(bgr, cv.COLOR_BGR2GRAY))
            if len(self._cache) > self._size:
                self._cache.popitem(last=False)
        return self._cache[picture.histopath_id]


# Picture against picture: SIFT features, RANSAC homography
FEATURE_SCALE = 0.5
MAX_FEATURES = 5000
RATIO_TEST = 0.70
MIN_GOOD_MATCHES = 15
RANSAC_REPROJECTION_PX = 5.0
STRONG_MIN_INLIERS = 30
STRONG_MIN_INLIER_FRACTION = 0.50
STRONG_MAX_MEDIAN_ERROR_PX = 5.0


@dataclass(frozen=True)
class PictureFeatures:
    """SIFT keypoints (full-resolution coordinates) and descriptors of one picture."""

    points: np.ndarray
    descriptors: np.ndarray


@dataclass(frozen=True)
class PictureRelation:
    """Homography mapping picture A coordinates onto picture B coordinates."""

    good_matches: int
    inliers: int
    inlier_fraction: float
    median_error_px: float
    scale_x: float
    scale_y: float
    homography: tuple[float, ...]

    @property
    def is_strong(self) -> bool:
        return (
            self.inliers >= STRONG_MIN_INLIERS
            and self.inlier_fraction >= STRONG_MIN_INLIER_FRACTION
            and self.median_error_px <= STRONG_MAX_MEDIAN_ERROR_PX
        )


def extract_features(image_bgr: np.ndarray) -> PictureFeatures:
    gray = cv.cvtColor(image_bgr, cv.COLOR_BGR2GRAY)
    small = cv.resize(gray, None, fx=FEATURE_SCALE, fy=FEATURE_SCALE, interpolation=cv.INTER_AREA)
    keypoints, descriptors = cv.SIFT_create(nfeatures=MAX_FEATURES).detectAndCompute(small, None)
    if descriptors is None:
        return PictureFeatures(np.empty((0, 2), np.float32), np.empty((0, 128), np.float32))
    points = np.float32([keypoint.pt for keypoint in keypoints]) / FEATURE_SCALE
    return PictureFeatures(points, descriptors)


def extract_features_from_file(path) -> PictureFeatures:
    return extract_features(read_bgr(path))


# Exact search on purpose: FLANN's randomised trees give different matches from run to run.
_MATCHER = cv.BFMatcher(cv.NORM_L2)


def find_relation(a: PictureFeatures, b: PictureFeatures) -> PictureRelation | None:
    """Relation mapping A onto B, or None when the pictures share no consistent geometry."""
    if len(a.points) < 4 or len(b.points) < 4:
        return None
    pairs = _MATCHER.knnMatch(a.descriptors, b.descriptors, k=2)
    good = [pair[0] for pair in pairs if len(pair) == 2 and pair[0].distance < RATIO_TEST * pair[1].distance]
    if len(good) < MIN_GOOD_MATCHES:
        return None

    source = a.points[[m.queryIdx for m in good]].reshape(-1, 1, 2)
    target = b.points[[m.trainIdx for m in good]].reshape(-1, 1, 2)
    homography, mask = cv.findHomography(source, target, cv.RANSAC, RANSAC_REPROJECTION_PX)
    if homography is None or mask is None:
        return None

    inlier = mask.ravel() == 1
    inliers = int(inlier.sum())
    projected = cv.perspectiveTransform(source[inlier], homography)
    errors = np.linalg.norm(projected - target[inlier], axis=2).ravel()
    linear = homography[:2, :2]
    return PictureRelation(
        good_matches=len(good),
        inliers=inliers,
        inlier_fraction=inliers / len(good),
        median_error_px=float(np.median(errors)) if len(errors) else float("inf"),
        scale_x=float(np.linalg.norm(linear[:, 0])),
        scale_y=float(np.linalg.norm(linear[:, 1])),
        homography=tuple(float(v) for v in homography.ravel()),
    )


def parse_homography(text: str) -> np.ndarray:
    return np.array([float(v) for v in text.split()]).reshape(3, 3)


def overlap_fractions(homography: np.ndarray, size_a: tuple[int, int], size_b: tuple[int, int]) -> tuple[float, float]:
    """Share of picture A's area seen inside B, and share of B's area seen inside A.

    ``homography`` maps A onto B; sizes are (width, height). A pure shift of the same field of view
    gives two similar shares; a zoomed-in A inside a wide B gives a high share for A and a low one for B.
    """

    def share(matrix: np.ndarray, from_size: tuple[int, int], to_size: tuple[int, int]) -> float:
        width, height = from_size
        corners = np.float32([[0, 0], [width, 0], [width, height], [0, height]]).reshape(-1, 1, 2)
        projected = cv.perspectiveTransform(corners, matrix).reshape(-1, 2).astype(np.float32)
        projected_area = cv.contourArea(projected)
        if projected_area <= 0:
            return 0.0
        target = np.float32([[0, 0], [to_size[0], 0], [to_size[0], to_size[1]], [0, to_size[1]]])
        shared_area, _ = cv.intersectConvexConvex(projected, target)
        return float(shared_area / projected_area)

    return share(homography, size_a, size_b), share(np.linalg.inv(homography), size_b, size_a)


# Patch through a picture relation into another picture
GRID_POINTS = 16
COMPARE_SIZE = 128
CONFIRMED_MIN_INSIDE = 0.9
CONFIRMED_MIN_AGREEMENT = 0.8


@dataclass(frozen=True)
class Placement:
    """A patch's footprint in another picture."""

    scale: float
    inside_fraction: float
    agreement: float | None


def patch_to_picture(homography: np.ndarray, x: int, y: int) -> np.ndarray:
    """Matrix taking patch pixel coordinates to coordinates of the related picture."""
    shift = np.array([[1.0, 0.0, x], [0.0, 1.0, y], [0.0, 0.0, 1.0]])
    return homography @ shift


def _footprint(matrix: np.ndarray, width: int, height: int) -> np.ndarray:
    xs, ys = np.meshgrid(np.linspace(0, width, GRID_POINTS), np.linspace(0, height, GRID_POINTS))
    points = np.float32(np.stack([xs.ravel(), ys.ravel()], axis=1)).reshape(-1, 1, 2)
    return cv.perspectiveTransform(points, matrix).reshape(-1, 2)


def content_agreement(patch_gray: np.ndarray, picture_gray: np.ndarray, matrix: np.ndarray) -> float | None:
    """Normalised correlation between the patch and the related picture warped into the patch frame."""
    height, width = patch_gray.shape
    warped = cv.warpPerspective(picture_gray, matrix, (width, height), flags=cv.INTER_LINEAR | cv.WARP_INVERSE_MAP)
    size = (COMPARE_SIZE, COMPARE_SIZE)
    a = cv.resize(patch_gray, size, interpolation=cv.INTER_AREA)
    b = cv.resize(warped, size, interpolation=cv.INTER_AREA)
    if a.std() == 0 or b.std() == 0:
        return None
    return float(cv.matchTemplate(a, b, cv.TM_CCOEFF_NORMED)[0, 0])


def place_patch(
    patch_gray: np.ndarray,
    x: int,
    y: int,
    homography: np.ndarray,
    picture_gray: np.ndarray,
    min_inside_for_agreement: float = CONFIRMED_MIN_INSIDE,
) -> Placement:
    height, width = patch_gray.shape
    matrix = patch_to_picture(homography, x, y)
    points = _footprint(matrix, width, height)
    picture_height, picture_width = picture_gray.shape
    inside = (
        (points[:, 0] >= 0) & (points[:, 0] <= picture_width) & (points[:, 1] >= 0) & (points[:, 1] <= picture_height)
    )
    corners = points[[0, GRID_POINTS - 1, -1, -GRID_POINTS]]
    area = 0.5 * abs(np.dot(corners[:, 0], np.roll(corners[:, 1], -1)) - np.dot(corners[:, 1], np.roll(corners[:, 0], -1)))
    inside_fraction = float(inside.mean())
    agreement = (
        content_agreement(patch_gray, picture_gray, matrix) if inside_fraction >= min_inside_for_agreement else None
    )
    return Placement(
        scale=float(np.sqrt(area / (width * height))),
        inside_fraction=inside_fraction,
        agreement=agreement,
    )
