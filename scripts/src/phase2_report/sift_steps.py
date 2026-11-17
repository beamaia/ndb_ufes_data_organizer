"""Figures that explain the steps of SIFT on one real pair of pictures (a wide picture and its close-up), for the private slides.

The scale space, the keypoints and the fingerprint are a short SIFT written for teaching, the one of the SIFT Lab page (cv_ml_concepts/concepts/sift): the picture
blurred at growing widths, the difference between blur levels, the extremes of that difference, the main direction from the gradients, and the 4 x 4 x 8 numbers of the
window turned to that direction. The matches and the rule (zoom, turn, shift) come from the OpenCV SIFT with the settings of the matching code.
"""

from __future__ import annotations

from pathlib import Path

import cv2 as cv
import matplotlib
import numpy as np
from scipy import ndimage

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402

from src.phase0_dataset_builder.matching import FEATURE_SCALE, MAX_FEATURES, RANSAC_REPROJECTION_PX, RATIO_TEST  # noqa: E402
from src.utils.logger import logger  # noqa: E402

WIDTH = 520  # the teaching SIFT runs on a copy of the close-up this wide, in pixels; the wide picture shows the tissue about 4 times smaller, so its copy is twice as wide
LEVELS, SIGMA0 = 12, 1.6  # blur levels, and the blur of the first; every 3 levels the blur doubles
CONTRAST, EDGE_RATIO = 0.004, 10  # a keypoint needs |difference| >= CONTRAST on gray values 0..1 (low: the pictures have little contrast, and only the strongest are kept), and Tr^2/Det below (EDGE_RATIO + 1)^2 / EDGE_RATIO
DARK_SPOT, LIGHT_SPOT = "#f2b705", "#2a9df4"
DARK = "#3a3a3a"  # titles in dark gray, as on the other slide figures
RULE, OFF_RULE = (25, 190, 120), (235, 70, 70)  # the colors of the matches that follow the rule and of those that do not


def opencv_matches(images: list[np.ndarray]):
    """The two steps of the matching code on a pair of RGB pictures: SIFT key points on half-size gray copies, and the matches that pass the ratio test.
    Returns the copies, their key points, the matches, and the positions of the matches in the full-size pictures."""
    small = [cv.resize(cv.cvtColor(image, cv.COLOR_RGB2GRAY), None, fx=FEATURE_SCALE, fy=FEATURE_SCALE, interpolation=cv.INTER_AREA) for image in images]
    sift = cv.SIFT_create(nfeatures=MAX_FEATURES)
    (keys_a, desc_a), (keys_b, desc_b) = [sift.detectAndCompute(image, None) for image in small]
    pairs = cv.BFMatcher(cv.NORM_L2).knnMatch(desc_a, desc_b, k=2)
    good = [pair[0] for pair in pairs if len(pair) == 2 and pair[0].distance < RATIO_TEST * pair[1].distance]
    source = np.float32([keys_a[m.queryIdx].pt for m in good]) / FEATURE_SCALE
    target = np.float32([keys_b[m.trainIdx].pt for m in good]) / FEATURE_SCALE
    return small, keys_a, keys_b, good, source, target


def resized(image: np.ndarray, width: int) -> np.ndarray:
    return cv.resize(image, (width, round(image.shape[0] * width / image.shape[1])), interpolation=cv.INTER_AREA)


def scale_space(gray: np.ndarray):
    """The blurred pictures (each blurred from the one before, so the widths add up) and the difference between neighbouring levels: blurrier minus sharper."""
    sigmas = [SIGMA0 * 2 ** (k / 3) for k in range(LEVELS)]
    levels = [cv.GaussianBlur(gray, (0, 0), float(np.sqrt(SIGMA0**2 - 0.25)))]
    for k in range(1, LEVELS):
        levels.append(cv.GaussianBlur(levels[-1], (0, 0), float(np.sqrt(sigmas[k] ** 2 - sigmas[k - 1] ** 2))))
    return sigmas, levels, np.stack([levels[k + 1] - levels[k] for k in range(LEVELS - 1)])


def detect(dog: np.ndarray, sigmas: list[float], limit: int = 400, margin: int = 8) -> list[dict]:
    """The pixels that are the largest or the smallest of their 26 neighbours (position and blur level), strong enough, and not on a straight edge."""
    extreme = (dog == ndimage.maximum_filter(dog, size=3)) | (dog == ndimage.minimum_filter(dog, size=3))
    d = dog
    dxx, dyy, dxy = np.zeros_like(d), np.zeros_like(d), np.zeros_like(d)
    dxx[:, :, 1:-1] = d[:, :, 2:] + d[:, :, :-2] - 2 * d[:, :, 1:-1]
    dyy[:, 1:-1, :] = d[:, 2:, :] + d[:, :-2, :] - 2 * d[:, 1:-1, :]
    dxy[:, 1:-1, 1:-1] = (d[:, 2:, 2:] - d[:, 2:, :-2] - d[:, :-2, 2:] + d[:, :-2, :-2]) / 4
    trace, det = dxx + dyy, dxx * dyy - dxy**2
    blob = (det > 0) & (trace**2 < (EDGE_RATIO + 1) ** 2 / EDGE_RATIO * np.where(det > 0, det, 1))
    keep = extreme & blob & (np.abs(d) >= CONTRAST)
    keep[0] = keep[-1] = False  # the first and last difference have a neighbour level on one side only
    keep[:, :margin] = keep[:, -margin:] = False
    keep[:, :, :margin] = keep[:, :, -margin:] = False
    k, y, x = np.nonzero(keep)
    order = np.argsort(-np.abs(d[k, y, x]))[:limit]
    return [{"x": float(x[i]), "y": float(y[i]), "k": int(k[i]), "sigma": sigmas[k[i]], "dark": bool(d[k[i], y[i], x[i]] > 0)} for i in order]


def gradients(level: np.ndarray):
    gy, gx = np.gradient(level)
    return gx, gy


def _window(gx, gy, x, y, reach):
    """Pixel offsets around (x, y) within ``reach`` pixels, the gradients there, and which of them lie inside the picture."""
    x0, y0 = int(round(x)), int(round(y))
    dy, dx = np.mgrid[-reach:reach + 1, -reach:reach + 1]
    xs, ys = x0 + dx, y0 + dy
    inside = (xs >= 1) & (ys >= 1) & (xs <= gx.shape[1] - 2) & (ys <= gx.shape[0] - 2)
    xs, ys = np.clip(xs, 0, gx.shape[1] - 1), np.clip(ys, 0, gx.shape[0] - 1)
    return dx, dy, gx[ys, xs], gy[ys, xs], inside


def main_direction(gx: np.ndarray, gy: np.ndarray, x: float, y: float, sigma: float) -> float:
    """The direction in which the picture changes most around the keypoint: gradients vote in 36 bins of 10 degrees, near ones and strong ones count more."""
    dx, dy, ax, ay, inside = _window(gx, gy, x, y, int(np.ceil(4.5 * sigma)))
    weight = np.exp(-(dx**2 + dy**2) / (2 * (1.5 * sigma) ** 2)) * np.hypot(ax, ay) * inside
    angle = np.arctan2(ay, ax) % (2 * np.pi)
    hist = np.bincount(np.minimum(35, (angle / (2 * np.pi) * 36).astype(int)).ravel(), weights=weight.ravel(), minlength=36)
    smooth = (np.roll(hist, 1) + 2 * hist + np.roll(hist, -1)) / 4
    return (int(np.argmax(smooth)) + 0.5) * 2 * np.pi / 36


def fingerprint(gx: np.ndarray, gy: np.ndarray, x: float, y: float, sigma: float, theta: float) -> np.ndarray:
    """A window of 4 x 4 cells (3 sigma wide each) turned to ``theta``, and in each cell the strength of 8 gradient directions: 4 x 4 x 8 numbers, as an array of
    shape (rows, columns, 8), made to have length 1 after cutting the largest at 0.2."""
    cell = 3 * sigma
    dx, dy, ax, ay, inside = _window(gx, gy, x, y, int(np.ceil(2.83 * cell)))
    c, s = np.cos(theta), np.sin(theta)
    rx, ry = (c * dx + s * dy) / cell, (-s * dx + c * dy) / cell
    u, v = rx + 2, ry + 2
    use = inside & (u > 0) & (u < 4) & (v > 0) & (v < 4)
    turned = (np.arctan2(ay, ax) - theta) % (2 * np.pi) / (2 * np.pi) * 8
    b0, fb = np.floor(turned).astype(int), turned - np.floor(turned)
    weight = np.hypot(ax, ay) * np.exp(-(rx**2 + ry**2) / 8)
    cu, cv_ = u - 0.5, v - 0.5
    i0, j0 = np.floor(cu).astype(int), np.floor(cv_).astype(int)
    fi, fj = cu - i0, cv_ - j0
    hist = np.zeros((4, 4, 8))
    for di in (0, 1):
        for dj in (0, 1):
            ii, jj = i0 + di, j0 + dj
            ok = use & (ii >= 0) & (ii <= 3) & (jj >= 0) & (jj <= 3)
            share = (fi if di else 1 - fi) * (fj if dj else 1 - fj)
            for db in (0, 1):
                np.add.at(hist, (jj[ok], ii[ok], (b0[ok] + db) % 8), (weight * share * (fb if db else 1 - fb))[ok])
    vector = hist.ravel() / (np.linalg.norm(hist) or 1)
    vector = np.minimum(vector, 0.2)
    return (vector / (np.linalg.norm(vector) or 1)).reshape(4, 4, 8)


def turned_window(rgb: np.ndarray, x: float, y: float, sigma: float, theta: float, size: int = 260) -> np.ndarray:
    """The picture around a keypoint, turned so that its main direction points right and sized so that a cell is 3 sigma wide: the window of the fingerprint."""
    cell = 3 * sigma
    e = (np.arange(size) + 0.5) / size * 4 - 2
    ex, ey = np.meshgrid(e, e)
    c, s = np.cos(theta), np.sin(theta)
    return cv.remap(rgb, (x + (c * ex - s * ey) * cell).astype(np.float32), (y + (s * ex + c * ey) * cell).astype(np.float32), cv.INTER_LINEAR,
                    borderMode=cv.BORDER_CONSTANT, borderValue=(255, 255, 255))


def draw_window(axis, window: np.ndarray, finger: np.ndarray) -> None:
    axis.imshow(window, extent=(0, 4, 4, 0))
    for g in (1, 2, 3):
        axis.axvline(g, color="white", lw=1, alpha=0.8)
        axis.axhline(g, color="white", lw=1, alpha=0.8)
    top = finger.max() or 1
    for row in range(4):
        for col in range(4):
            for b in range(8):
                a, length = (b + 0.5) * 2 * np.pi / 8, finger[row, col, b] / top * 0.46
                axis.plot([col + 0.5, col + 0.5 + length * np.cos(a)], [row + 0.5, row + 0.5 + length * np.sin(a)], color="#f2b705", lw=2.4, solid_capstyle="round")
    axis.plot([2, 3.9], [2, 2], color="white", lw=2.4)  # the main direction
    axis.set_xlim(0, 4)
    axis.set_ylim(4, 0)
    axis.axis("off")


def _ring(axis, kp: dict, color: str, lw: float = 1.4, theta: float | None = None, minimum: float = 3.0) -> None:
    r = max(minimum, 2 * kp["sigma"])
    axis.add_patch(Circle((kp["x"], kp["y"]), r, fill=False, ec=color, lw=lw))
    if theta is not None:
        axis.plot([kp["x"], kp["x"] + r * np.cos(theta)], [kp["y"], kp["y"] + r * np.sin(theta)], color=color, lw=lw)


def scales_figure(rgb: np.ndarray, width: int, path: Path) -> None:
    """Three panels on one picture: a blur level, the difference between that level and the next, and the keypoints found at all levels (the strongest of every
    level, so that every size of circle is drawn). The level shown is the one with the most keypoints among those that are not the finest detail."""
    work = resized(rgb, width)
    gray = cv.cvtColor(work, cv.COLOR_RGB2GRAY).astype(np.float32) / 255
    sigmas, levels, dog = scale_space(gray)
    found = detect(dog, sigmas, limit=2000)
    counts = np.bincount([kp["k"] for kp in found], minlength=LEVELS - 1)
    k = 2 + int(np.argmax(counts[2:LEVELS - 3]))
    keypoints = [kp for level in range(LEVELS - 1) for kp in [q for q in found if q["k"] == level][:12]]
    peak = float(np.percentile(np.abs(dog[k]), 99.5))
    figure, axes = plt.subplots(1, 3, figsize=(15.5, 4.2))
    axes[0].imshow(levels[k], cmap="gray", vmin=0, vmax=1)
    axes[0].set_title(f"Blurred,\nwidth σ = {sigmas[k]:.1f} px", fontsize=14, color=DARK)
    axes[1].imshow(dog[k], cmap="gray", vmin=-peak, vmax=peak)
    axes[1].set_title(f"Blurrier minus sharper\n(σ {sigmas[k + 1]:.1f} − {sigmas[k]:.1f})", fontsize=14, color=DARK)
    axes[2].imshow(work)
    axes[2].set_title("Keypoints: the strongest\nof each blur level", fontsize=14, color=DARK)
    for kp in keypoints:
        grads = gradients(levels[kp["k"]])
        _ring(axes[2], kp, DARK_SPOT if kp["dark"] else LIGHT_SPOT, lw=1.8, theta=main_direction(*grads, kp["x"], kp["y"], kp["sigma"]))
    for kp in [q for q in found if q["k"] == k][:40]:
        for axis in axes[:2]:
            axis.add_patch(Circle((kp["x"], kp["y"]), 7, fill=False, ec=DARK_SPOT, lw=1.6))
    for axis in axes:
        axis.axis("off")
    figure.subplots_adjust(wspace=0.03)
    figure.savefig(path, dpi=120, bbox_inches="tight", pad_inches=0.05)
    plt.close(figure)
    logger.info(f"scales: {len(found)} keypoints in all, {int(counts[k])} at the shown blur level {k}, written to {path}")


def _prepared(rgb: np.ndarray, width: int):
    """The copy of a picture the teaching SIFT works on, its size against the full picture, its blurred levels and its keypoints."""
    work = resized(rgb, width)
    gray = cv.cvtColor(work, cv.COLOR_RGB2GRAY).astype(np.float32) / 255
    sigmas, levels, dog = scale_space(gray)
    return work, work.shape[1] / rgb.shape[1], levels, detect(dog, sigmas, limit=2000)


def descriptor_figure(wide: np.ndarray, close: np.ndarray, similarity: np.ndarray, widths: tuple[int, int], path: Path) -> bool:
    """One keypoint of the wide picture and the keypoint of the close-up at the place where the rule says it lands: the two pictures, and under them the two
    windows turned to the main direction, with the 8 directions of each cell. Among the pairs, the one whose fingerprints are closest is drawn."""
    (work_a, f_a, levels_a, kps_a), (work_b, f_b, levels_b, kps_b) = _prepared(wide, widths[0]), _prepared(close, widths[1])
    zoom = float(np.hypot(similarity[0, 0], similarity[1, 0]))
    grads_a, grads_b = {}, {}
    best = None
    for kp in kps_a:
        if kp["sigma"] < 2.2:
            continue
        fx, fy = np.array([kp["x"] / f_a, kp["y"] / f_a, 1.0]) @ similarity.T
        px, py = fx * f_b, fy * f_b
        expected = kp["sigma"] * zoom * f_b / f_a
        near = [q for q in kps_b if np.hypot(q["x"] - px, q["y"] - py) <= 6 and 0.6 < q["sigma"] / expected < 1.6]
        if not near:
            continue
        partner = min(near, key=lambda q: np.hypot(q["x"] - px, q["y"] - py))
        if min(kp["x"], kp["y"]) < 7 * kp["sigma"] or min(partner["x"], partner["y"]) < 7 * partner["sigma"]:
            continue
        if kp["x"] + 7 * kp["sigma"] > work_a.shape[1] or kp["y"] + 7 * kp["sigma"] > work_a.shape[0]:
            continue
        if partner["x"] + 7 * partner["sigma"] > work_b.shape[1] or partner["y"] + 7 * partner["sigma"] > work_b.shape[0]:
            continue
        grads_a.setdefault(kp["k"], gradients(levels_a[kp["k"]]))
        grads_b.setdefault(partner["k"], gradients(levels_b[partner["k"]]))
        theta_a, theta_b = main_direction(*grads_a[kp["k"]], kp["x"], kp["y"], kp["sigma"]), main_direction(*grads_b[partner["k"]], partner["x"], partner["y"], partner["sigma"])
        finger_a = fingerprint(*grads_a[kp["k"]], kp["x"], kp["y"], kp["sigma"], theta_a)
        finger_b = fingerprint(*grads_b[partner["k"]], partner["x"], partner["y"], partner["sigma"], theta_b)
        distance = float(np.linalg.norm(finger_a - finger_b))
        if best is None or distance < best[0]:
            best = (distance, kp, partner, theta_a, theta_b, finger_a, finger_b)
    if best is None:
        logger.warning("descriptor figure: no keypoint of the wide picture has a partner in the close-up")
        return False
    distance, kp, partner, theta_a, theta_b, finger_a, finger_b = best
    figure = plt.figure(figsize=(9.2, 9.0))
    grid = figure.add_gridspec(2, 2, height_ratios=[1, 1.04], hspace=0.12, wspace=0.05)
    top_a, top_b, bottom_a, bottom_b = (figure.add_subplot(grid[i, j]) for i in range(2) for j in range(2))
    for axis, work, point, theta, title in ((top_a, work_a, kp, theta_a, "Wide picture: a keypoint"), (top_b, work_b, partner, theta_b, "Close-up: where the rule puts it")):
        axis.imshow(work)
        _ring(axis, point, DARK_SPOT, lw=2.6, theta=theta, minimum=16)
        axis.set_title(title, fontsize=13, color=DARK)
        axis.axis("off")
    draw_window(bottom_a, turned_window(work_a, kp["x"], kp["y"], kp["sigma"], theta_a), finger_a)
    draw_window(bottom_b, turned_window(work_b, partner["x"], partner["y"], partner["sigma"], theta_b), finger_b)
    bottom_a.set_title("Its window, turned\nto its direction", fontsize=13, color=DARK)
    bottom_b.set_title(f"The same in the close-up\n(fingerprint distance {distance:.2f})", fontsize=13, color=DARK)
    figure.savefig(path, dpi=120, bbox_inches="tight", pad_inches=0.05)
    plt.close(figure)
    logger.info(f"descriptor: keypoint at scale {kp['sigma']:.1f} (wide) and {partner['sigma']:.1f} (close-up), fingerprint distance {distance:.2f}, written to {path}")
    return True


def rule_figure(wide: np.ndarray, close: np.ndarray, path: Path, shown: int = 18, seed: int = 0) -> np.ndarray:
    """The matches between the two pictures, some of those that follow one rule (green) and of those that do not (red), and the rule: zoom, turn and where the
    close-up sits in the wide picture, fitted with RANSAC on the matched positions. Returns the 2 x 3 matrix of the rule (full-size pixels, wide to close-up)."""
    small, keys_a, keys_b, good, source, target = opencv_matches([wide, close])
    similarity, mask = cv.estimateAffinePartial2D(source, target, method=cv.RANSAC, ransacReprojThreshold=RANSAC_REPROJECTION_PX)
    inlier = mask.ravel().astype(bool)
    rng = np.random.default_rng(seed)
    follow = rng.permutation(np.flatnonzero(inlier))[:shown]
    off = rng.permutation(np.flatnonzero(~inlier))[: max(4, shown // 4)]
    pictures = [cv.resize(image, None, fx=FEATURE_SCALE, fy=FEATURE_SCALE, interpolation=cv.INTER_AREA) for image in (wide, close)]
    gap = 24
    canvas = np.full((max(p.shape[0] for p in pictures), pictures[0].shape[1] + gap + pictures[1].shape[1], 3), 255, np.uint8)
    canvas[: pictures[0].shape[0], : pictures[0].shape[1]] = pictures[0]
    canvas[: pictures[1].shape[0], pictures[0].shape[1] + gap:] = pictures[1]
    shift = pictures[0].shape[1] + gap
    figure, axis = plt.subplots(figsize=(13.5, 5.2))
    axis.imshow(canvas)
    for indices, color, width in ((off, OFF_RULE, 1.8), (follow, RULE, 2.0)):
        for i in indices:
            (xa, ya), (xb, yb) = keys_a[good[i].queryIdx].pt, keys_b[good[i].trainIdx].pt
            axis.plot([xa, xb + shift], [ya, yb], color=np.array(color) / 255, lw=width, marker="o", ms=4, alpha=0.9)
    zoom, turn = float(np.hypot(similarity[0, 0], similarity[1, 0])), float(np.degrees(np.arctan2(similarity[1, 0], similarity[0, 0])))
    turn = 0.0 if abs(turn) < 0.05 else turn
    center = np.linalg.inv(np.vstack([similarity, [0, 0, 1]])) @ [close.shape[1] / 2, close.shape[0] / 2, 1]  # where the middle of the close-up is, in the wide picture
    axis.set_title(f"The rule: zoom {zoom:.2f}×, turn {turn:.1f}°, the close-up is centered at ({center[0]:.0f}, {center[1]:.0f}) of the wide picture", fontsize=14, color=DARK)
    axis.text(0.5, -0.01, f"{int(inlier.sum()):,} of {len(good):,} matches follow it (green); the others do not (red)", transform=axis.transAxes, ha="center", va="top", fontsize=13, color=DARK)
    axis.axis("off")
    figure.savefig(path, dpi=120, bbox_inches="tight", pad_inches=0.05)
    plt.close(figure)
    logger.info(f"rule: zoom {zoom:.2f}, turn {turn:.1f} degrees, {int(inlier.sum())} of {len(good)} matches follow it, written to {path}")
    return similarity


def sift_steps(wide: np.ndarray, close: np.ndarray, out: Path) -> None:
    """The three figures of the slides that explain SIFT, written to ``out``: sift_scales.png, sift_descriptor.png and sift_rule.png."""
    widths = (2 * WIDTH, WIDTH)  # the wide picture shows the tissue about 4 times smaller than the close-up: twice as many pixels keeps its detail
    scales_figure(wide, widths[0], out / "sift_scales.png")
    similarity = rule_figure(wide, close, out / "sift_rule.png")
    descriptor_figure(wide, close, similarity, widths, out / "sift_descriptor.png")
