"""Pure-Python atlas geometry helpers used by the public methods contract.

The helpers use half-open rectangles ``(x1, y1, x2, y2)``. Coverage is measured
in the displayed WSI coordinate space, with boxes clipped to the image bounds.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping


Box = tuple[float, float, float, float]


def _clipped_boxes(boxes: Iterable[Box], image_width: float, image_height: float) -> list[Box]:
    clipped = []
    for x1, y1, x2, y2 in boxes:
        box = (
            max(0.0, min(float(image_width), float(x1))),
            max(0.0, min(float(image_height), float(y1))),
            max(0.0, min(float(image_width), float(x2))),
            max(0.0, min(float(image_height), float(y2))),
        )
        if box[2] > box[0] and box[3] > box[1]:
            clipped.append(box)
    return clipped


def _coverage_areas(boxes: list[Box]) -> tuple[float, float]:
    """Return union area and area covered by at least two boxes."""

    if not boxes:
        return 0.0, 0.0
    x_edges = sorted({edge for box in boxes for edge in (box[0], box[2])})
    union = 0.0
    repeated = 0.0
    for left, right in zip(x_edges, x_edges[1:]):
        if right <= left:
            continue
        midpoint = (left + right) / 2.0
        active = [box for box in boxes if box[0] <= midpoint < box[2]]
        y_edges = sorted({edge for box in active for edge in (box[1], box[3])})
        for bottom, top in zip(y_edges, y_edges[1:]):
            if top <= bottom:
                continue
            y_midpoint = (bottom + top) / 2.0
            coverage = sum(box[1] <= y_midpoint < box[3] for box in active)
            area = (right - left) * (top - bottom)
            if coverage >= 1:
                union += area
            if coverage >= 2:
                repeated += area
    return union, repeated


def coverage_metrics(
    boxes: Iterable[Box], image_width: float, image_height: float
) -> dict[str, float]:
    """Calculate the three atlas-panel coverage percentages.

    ``repeated_sampled_area_percent`` uses the mapped union as its denominator,
    matching the atlas panel's definition of the sampled patch area. The full
    WSI metric uses the displayed image area as its denominator.
    """

    image_area = float(image_width) * float(image_height)
    if image_area <= 0:
        raise ValueError("image dimensions must be positive")
    union, repeated = _coverage_areas(_clipped_boxes(boxes, image_width, image_height))
    return {
        "mapped_image_area_percent": union / image_area * 100.0,
        "repeated_sampled_area_percent": repeated / union * 100.0 if union else 0.0,
        "repeated_full_wsi_image_area_percent": repeated / image_area * 100.0,
        "mapped_area": union,
        "repeated_area": repeated,
        "image_area": image_area,
    }


def bbox_iou(a: Mapping[str, float], b: Mapping[str, float], prefix: str = "") -> float:
    """Calculate intersection-over-union for two coordinate-box mappings."""

    required = [f"{prefix}x", f"{prefix}y", f"{prefix}x2", f"{prefix}y2"]
    try:
        values = [float(a[column]) for column in required] + [float(b[column]) for column in required]
    except (KeyError, TypeError, ValueError):
        return math.nan
    if any(math.isnan(value) for value in values):
        return math.nan
    ax1, ay1, ax2, ay2, bx1, by1, bx2, by2 = values
    inter_area = max(0.0, min(ax2, bx2) - max(ax1, bx1)) * max(0.0, min(ay2, by2) - max(ay1, by1))
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter_area
    return math.nan if union <= 0 else inter_area / union


def pair_relation(coordinate_relation: str, feature_relation: str, iou: float | None) -> str:
    """Apply the atlas pair-relation decision order."""

    iou_positive = iou is not None and not math.isnan(float(iou)) and float(iou) > 0
    feature_similar = feature_relation == "feature_similar"
    if coordinate_relation == "coordinate_unavailable_or_requires_review":
        return "feature_similar_coordinate_requires_review" if feature_similar else coordinate_relation
    if coordinate_relation == "spatially_overlapping" and feature_similar:
        return "feature_similar_and_spatially_overlapping"
    if coordinate_relation == "spatially_distinct" and feature_similar:
        return "feature_similar_without_spatial_overlap"
    return "spatially_overlapping" if iou_positive else "spatially_distinct"
