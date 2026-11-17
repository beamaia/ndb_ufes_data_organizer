"""Figures that explain the neuron, layers, gradient descent, convolution, pooling and attention, for the slides and the thesis. They are diagrams and made-up examples,
except for the input of the network diagram, which is a public P-NDB-UFES patch.

Eight figures, written to the folder given to the slides command:
- ``neuron_activations.png``: (a) a neuron with three inputs, its weights (width = size, color = sign), its bias, its sum and its activation; (b) the sigmoid with
  its largest slope; (c) ReLU with its two slopes.
- ``network_layers.png``: a network of three layers (input, hidden, output), (a) with each neuron connected to two neurons of the previous layer drawn at
  random and (b) fully connected, with the number of weights of each.
- ``gradient_descent.png``: gradient descent on the cross-entropy of a sigmoid neuron with two weights and no bias, over 8 made-up examples: (a) the loss
  as a surface over the two weights, (b-d) the same loss seen from above, with the steps of a learning rate that is too small, suitable and too large.
- ``cnn_architecture.png``: a convolutional network from a patch to the classes: convolution, pooling, more blocks, small and deep feature maps, fully
  connected layers and the softmax.
- ``convolution_kernel.png``: a 2 x 2 kernel sliding over a 4 x 4 input with stride 1, at steps 1, 2 and 9, filling the 3 x 3 feature map.
- ``pooling.png``: a 4 x 4 feature map split into four 2 x 2 windows (stride 2), and its max pooling and average pooling.
- ``attention_scores.png``: the scores Q K^T, the dot product of each query with each key, of "I need a hand building this", with made-up 3-number
  embeddings (about help, about the body, a grammar word) and W_Q and W_K the identity. The row of "hand" is outlined: it scores high with "need" and
  "building".
- ``attention_neuron.png``: the attention of "hand" drawn like a neuron: the scores of "hand" divided by sqrt(d_k), their softmax (the weights), and the
  values of the tokens going into a sum with lines as wide as their weights. W_V is the identity, so the values are the embeddings.

The examples of the gradient descent: 4 with inputs (1, 1), three of them of class 1, and 4 with inputs (2, -2), one of them of class 1. Examples with the
same inputs and different classes mean no weights get them all right, so the loss has a lowest point and does not keep falling forever. The lowest point
is where the neuron predicts the share of class 1 of each group: sigmoid(w1 + w2) = 3/4 and sigmoid(2 w1 - 2 w2) = 1/4, so w1 = ln(3) / 4 and
w2 = 3 ln(3) / 4. The two groups pull along different diagonals with different strength, so the valley is long, thin and tilted.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle  # noqa: E402
from PIL import Image  # noqa: E402

from src.phase0_dataset_builder.sources import DEFAULT_PATCH_IMAGE_DIR  # noqa: E402
from src.phase2_report.cluster_steps import ACCENT, DARK, POINT, STYLE  # noqa: E402
from src.utils.logger import logger  # noqa: E402

POSITIVE, NEGATIVE = "#2a78d6", "#e34948"  # the sign of a weight
NODE = "#f2f2f2"
WEIGHTS = [0.8, -0.5, 0.2]  # the made-up weights of the example neuron
LAYER_SIZES = (4, 5, 3)  # input values, hidden neurons, output classes
INPUTS_PER_NEURON, CONNECTION_SEED = 2, 1  # the network that is not fully connected: each neuron takes 2 neurons of the previous layer, drawn at random
INPUTS = np.array([[1.0, 1.0]] * 4 + [[2.0, -2.0]] * 4)  # the made-up examples of the gradient descent, see the module docstring
TARGETS = np.array([1, 1, 1, 0, 1, 0, 0, 0])
MINIMUM = np.log(3) * np.array([0.25, 0.75])  # the weights with the lowest loss, worked out in the module docstring
START, STEPS = np.array([-2.0, -1.0]), 25
LEARNING_RATES = {"too small": 0.05, "suitable": 1.0, "too large": 4.0}
LANDSCAPE = "viridis"  # low loss dark, high loss yellow
INPUT_PATCH = "p0407"  # the input of the network diagram: the OSCC example patch of the slides (public, P-NDB-UFES)
CONVOLUTION_INPUT = np.array([[1, 2, 0, 1], [0, 1, 3, 1], [2, 1, 0, 2], [1, 0, 1, 3]], dtype=float)  # made-up values
CONVOLUTION_KERNEL = np.array([[1, 0], [-1, 2]], dtype=float)
SHOWN_STEPS = (0, 1, 8)  # steps 1, 2 and 9 of the 9 positions of the kernel
POOLING_INPUT = np.array([[1, 3, 2, 0], [4, 2, 1, 1], [0, 1, 5, 2], [2, 1, 3, 6]], dtype=float)  # made-up values
WINDOW, KERNEL_CELL, DONE = "#f9d0cf", "#d6e6f7", "#eeeeee"  # the window of the current step, the kernel, the values already computed
BLOCKS = ["#d6e6f7", "#fde2c8", "#d5f0e3", "#eadcf5"]  # the four pooling windows
MAP_FILL, MAP_EDGE = "#bfe3e6", "#4a8c96"  # the feature maps of the network diagram
SENTENCE = ["I", "need", "a", "hand", "building", "this"]
EMBEDDINGS = {  # made up: (about help, about the body, a grammar word); the grammar words are short vectors so that they do not outshine "hand"
    "I": (0.2, 0.2, 1.0), "need": (2.0, 0.0, 0.4), "a": (0.0, 0.0, 1.0), "hand": (1.2, 1.2, 0.0), "building": (1.8, 0.2, 0.2), "this": (0.0, 0.0, 1.0)}


def _arrow(axis, start, end, color=DARK, lw=1.4) -> None:
    axis.annotate("", xy=end, xytext=start, arrowprops={"arrowstyle": "-|>", "color": color, "lw": lw, "shrinkA": 0, "shrinkB": 0})


def neuron_panel(axis) -> None:
    """Three inputs, each with a line to the sum whose width is the size of its weight and whose color is its sign, a bias from below, the activation and the output."""
    body, radius = np.array([2.6, 1.0]), 0.5
    for k, (w, y) in enumerate(zip(WEIGHTS, [2.0, 1.0, 0.0]), start=1):
        start = np.array([0.0, y])
        axis.add_patch(Circle(start, 0.3, fc=NODE, ec=DARK, lw=1.2, zorder=2))
        axis.text(*start, f"$x_{k}$", ha="center", va="center", fontsize=13, zorder=3)
        direction = (body - start) / np.linalg.norm(body - start)
        color = POSITIVE if w > 0 else NEGATIVE
        _arrow(axis, start + 0.3 * direction, body - radius * direction, color=color, lw=1 + 5 * abs(w))
        label = start + 0.45 * (body - start)  # on the line, with a white box behind it so it never overlaps the arrow
        axis.text(*label, f"$w_{k} = {w}$", color=color, fontsize=11, ha="center", va="center", zorder=4,
                  bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none"})
    axis.add_patch(Circle(body, radius, fc=NODE, ec=DARK, lw=1.4, zorder=2))
    axis.text(*body, "$\\Sigma$", ha="center", va="center", fontsize=18, zorder=3)
    _arrow(axis, body + np.array([0, -1.25]), body + np.array([0, -radius]))
    axis.text(body[0] + 0.12, body[1] - 1.05, "$b$", fontsize=13)
    box = np.array([4.0, 1.0])
    axis.add_patch(FancyBboxPatch(box - 0.32, 0.64, 0.64, boxstyle="round,pad=0.02", fc=NODE, ec=DARK, lw=1.4, zorder=2))
    axis.text(*box, "$f$", ha="center", va="center", fontsize=16, zorder=3)
    _arrow(axis, body + np.array([radius, 0]), box - np.array([0.34, 0]))
    axis.text((body[0] + radius + box[0] - 0.34) / 2, body[1] + 0.12, "$z$", ha="center", fontsize=12)
    _arrow(axis, box + np.array([0.34, 0]), box + np.array([0.95, 0]))
    axis.text(box[0] + 1.02, box[1], "$a = f(z)$", va="center", fontsize=13)
    axis.text(body[0], -0.7, "$z = \\sum_i w_i x_i + b$", ha="center", fontsize=13)
    axis.text(body[0], -1.35, "line width: size of the weight    blue: positive    red: negative", ha="center", fontsize=10, color=DARK)
    axis.set_xlim(-0.5, 6.0)
    axis.set_ylim(-1.6, 2.5)
    axis.set_aspect("equal")
    axis.axis("off")
    axis.set_title("(a) A neuron: weights, bias, sum and activation", fontsize=12)


def activation_panels(sigmoid_axis, relu_axis) -> None:
    z = np.linspace(-6, 6, 400)
    sigmoid = 1 / (1 + np.exp(-z))
    sigmoid_axis.plot(z, sigmoid, color=DARK, lw=2)
    near = np.linspace(-2, 2, 2)
    sigmoid_axis.plot(near, 0.5 + 0.25 * near, color=ACCENT, ls="--", lw=1.4)
    sigmoid_axis.scatter([0], [0.5], color=ACCENT, zorder=3)
    sigmoid_axis.text(0.4, 0.33, "largest slope:\n0.25 at $z = 0$", color=ACCENT, fontsize=11)
    sigmoid_axis.set_ylim(-0.05, 1.05)
    sigmoid_axis.set_ylabel("$\\sigma(z)$")
    sigmoid_axis.set_title("(b) Sigmoid: always between 0 and 1", fontsize=12)
    relu_axis.plot(z, np.maximum(0, z), color=DARK, lw=2)
    relu_axis.text(-5.5, 0.6, "slope 0", fontsize=11, color=ACCENT)
    relu_axis.text(1.0, 4.2, "slope 1", fontsize=11, color=ACCENT)
    relu_axis.set_ylabel("$\\max(0, z)$")
    relu_axis.set_title("(c) ReLU: 0 for negative $z$, $z$ for positive $z$", fontsize=12)
    for axis in (sigmoid_axis, relu_axis):
        axis.axhline(0, color=POINT, lw=0.8, zorder=0)
        axis.axvline(0, color=POINT, lw=0.8, zorder=0)
        axis.set_xlabel("$z$")
        axis.spines[["top", "right"]].set_visible(False)


def neuron_figure(path: Path) -> None:
    with plt.rc_context(STYLE):
        figure, axes = plt.subplots(1, 3, figsize=(18, 5.2), gridspec_kw={"width_ratios": [1.7, 1, 1]})
        neuron_panel(axes[0])
        activation_panels(axes[1], axes[2])
        figure.tight_layout()
        figure.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(figure)
    logger.info(f"neuron: weights {WEIGHTS}, written to {path}")


def layer_positions() -> list[list[tuple[float, float]]]:
    """The neurons of each layer, in columns 2 apart, centered on 0 vertically."""
    return [[(2.0 * column, (size - 1) / 2 - i) for i in range(size)] for column, size in enumerate(LAYER_SIZES)]


def network_panel(axis, connected, title: str) -> int:
    """The three layers with a line for every connection ``connected(start, end)`` allows; returns the number of weights (connections)."""
    positions = layer_positions()
    weights = 0
    for layer in range(len(LAYER_SIZES) - 1):
        for start in positions[layer]:
            for end in positions[layer + 1]:
                if connected(start, end):
                    axis.plot([start[0], end[0]], [start[1], end[1]], color=DARK, lw=1.0, alpha=0.7, zorder=1)
                    weights += 1
    names = [f"input layer\n({LAYER_SIZES[0]} values)", f"hidden layer\n({LAYER_SIZES[1]} neurons)", f"output layer\n({LAYER_SIZES[2]} classes)"]
    for layer, column in enumerate(positions):
        for x, y in column:
            axis.add_patch(Circle((x, y), 0.28, fc=NODE, ec=DARK, lw=1.2, zorder=2))
        axis.text(column[0][0], -max(LAYER_SIZES) / 2 - 0.35, names[layer], ha="center", va="top", fontsize=11)
    axis.set_xlim(-0.8, 2.0 * (len(LAYER_SIZES) - 1) + 0.8)
    axis.set_ylim(-max(LAYER_SIZES) / 2 - 1.5, max(LAYER_SIZES) / 2 + 0.2)
    axis.set_aspect("equal")
    axis.axis("off")
    axis.set_title(f"{title}\n{weights} weights", fontsize=12)
    return weights


def random_connections() -> set:
    """For every neuron after the input, ``INPUTS_PER_NEURON`` neurons of the previous layer drawn at random (fixed seed), as (start, end) position pairs. Draws
    are repeated until every neuron before the output feeds at least one neuron of the next layer: a neuron that leads nowhere would be computed for nothing."""
    rng = np.random.default_rng(CONNECTION_SEED)
    positions = layer_positions()
    while True:
        pairs = set()
        for layer in range(len(positions) - 1):
            for end in positions[layer + 1]:
                for i in rng.choice(len(positions[layer]), size=INPUTS_PER_NEURON, replace=False):
                    pairs.add((positions[layer][i], end))
        if {start for start, _ in pairs} == {position for column in positions[:-1] for position in column}:
            return pairs


def network_figure(path: Path) -> dict:
    pairs = random_connections()
    with plt.rc_context(STYLE):
        figure, axes = plt.subplots(1, 2, figsize=(12, 5.6))
        partial = network_panel(axes[0], lambda start, end: (start, end) in pairs,
                                f"(a) Not fully connected: each neuron connected\nto {INPUTS_PER_NEURON} neurons of the previous layer")
        full = network_panel(axes[1], lambda start, end: True, "(b) Fully connected: every neuron\nconnected to all of the previous layer")
        figure.tight_layout()
        figure.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(figure)
    logger.info(f"layers: {partial} weights when not fully connected, {full} when fully connected, written to {path}")
    return {"layers_weights": f"{partial} / {full}"}


def neuron_loss(w1, w2):
    """The mean cross-entropy of the sigmoid neuron with weights (w1, w2) over the made-up examples. w1 and w2 can be numbers or grids of the same shape.
    Written as -log sigmoid(z) = log(1 + e^-z) and -log(1 - sigmoid(z)) = log(1 + e^z), which stay finite when z is large."""
    z = np.multiply.outer(w1, INPUTS[:, 0]) + np.multiply.outer(w2, INPUTS[:, 1])
    return np.mean(np.where(TARGETS == 1, np.logaddexp(0, -z), np.logaddexp(0, z)), axis=-1)


def slopes(w: np.ndarray) -> np.ndarray:
    """The slope of the loss for each weight, from backpropagation through cross-entropy and sigmoid: the mean of (p - t) x_i, the prediction minus the
    class, times the input of that weight."""
    p = 1 / (1 + np.exp(-(INPUTS @ w)))
    return INPUTS.T @ (p - TARGETS) / len(TARGETS)


def descent(rate: float) -> np.ndarray:
    """The weights visited by gradient descent from the start, one row per step."""
    w = [START]
    for _ in range(STEPS):
        w.append(w[-1] - rate * slopes(w[-1]))
    return np.array(w)


def path_panel(axis, w1, w2, loss, levels, visited: np.ndarray) -> None:
    """The loss seen from above (one line per level) with the weights visited, the start and the lowest point."""
    axis.contourf(w1, w2, loss, levels=levels, cmap=LANDSCAPE, alpha=0.85, extend="both")
    axis.contour(w1, w2, loss, levels=levels, colors="white", linewidths=0.5)
    axis.plot(visited[:, 0], visited[:, 1], color=ACCENT, lw=1.4, marker="o", ms=4, zorder=3)
    axis.scatter(*START, s=90, color=ACCENT, edgecolor="white", lw=1.5, zorder=4)
    axis.text(START[0], START[1] - 0.25, "start", color="white", ha="center", va="top", fontsize=11, zorder=4)
    axis.scatter(*MINIMUM, marker="*", s=260, color="white", edgecolor=DARK, zorder=4)
    axis.set_xlabel("$w_1$")
    axis.set_ylabel("$w_2$")
    axis.set_aspect("equal")


def descent_figure(path: Path) -> dict:
    """(a) The loss as a surface over the two weights, with the steps of the suitable learning rate. (b-d) The loss seen from above, one panel per learning
    rate, with the weights visited."""
    paths = {name: descent(rate) for name, rate in LEARNING_RATES.items()}
    visited = np.vstack([*paths.values(), MINIMUM])
    low, high = visited.min(axis=0) - 0.6, visited.max(axis=0) + 0.6
    w1, w2 = np.meshgrid(np.linspace(low[0], high[0], 240), np.linspace(low[1], high[1], 240))
    loss = neuron_loss(w1, w2)
    lowest = float(neuron_loss(*MINIMUM))
    levels = lowest + np.geomspace(0.01, float(loss.max()) - lowest, 14)  # closer together near the bottom, where the loss changes slowly
    finals = {}
    with plt.rc_context(STYLE):
        figure = plt.figure(figsize=(13, 11.5))
        surface = figure.add_subplot(2, 2, 1, projection="3d", computed_zorder=False)  # draw in the order given, so the path is never hidden by the surface
        surface.plot_surface(w1, w2, loss, cmap=LANDSCAPE, alpha=0.75, lw=0, rstride=4, cstride=4, zorder=1)
        suitable = paths["suitable"]
        surface.plot(suitable[:, 0], suitable[:, 1], neuron_loss(suitable[:, 0], suitable[:, 1]), color=ACCENT, lw=1.6, marker="o", ms=3, zorder=2)
        surface.scatter(*START, neuron_loss(*START), s=70, color=ACCENT, edgecolor="white", lw=1.5, depthshade=False, zorder=3)
        surface.text(*START, neuron_loss(*START) + 0.12, "start", color=DARK, ha="center", fontsize=11, zorder=3)
        surface.scatter(*MINIMUM, lowest, marker="*", s=220, color="white", edgecolor=DARK, depthshade=False, zorder=3)
        surface.set_xlabel("$w_1$")
        surface.set_ylabel("$w_2$")
        surface.set_zlabel("cross-entropy loss")
        surface.view_init(elev=30, azim=-60)
        surface.set_title("(a) The loss over the two weights, with the\nsteps of the suitable learning rate", fontsize=12)
        for k, (name, rate) in enumerate(LEARNING_RATES.items()):
            axis = figure.add_subplot(2, 2, k + 2)
            path_panel(axis, w1, w2, loss, levels, paths[name])
            finals[name] = round(float(neuron_loss(*paths[name][-1])), 3)
            axis.set_title(f"({'bcd'[k]}) $\\eta = {rate}$: {name}\nloss after {STEPS} steps: {finals[name]:.2f} (lowest: {lowest:.2f})", fontsize=12)
        figure.tight_layout()
        figure.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(figure)
    logger.info(f"gradient descent: loss {float(neuron_loss(*START)):.3f} at the start, first slopes {np.round(slopes(START), 3)}, loss after {STEPS} steps "
                f"{finals}, lowest {lowest:.3f} at {np.round(MINIMUM, 3)}, written to {path}")
    return {"descent_final_loss": str(finals)}


def matrix(axis, values: np.ndarray, x: float, y: float, fill=None, size: float = 1.0, fontsize: float = 14) -> None:
    """``values`` as a grid of cells with its top-left corner at (x, y), rows going down; ``fill(i, j)`` gives a cell color (white when it is None). Cells
    with NaN are left empty."""
    for (i, j), value in np.ndenumerate(values):
        face = (fill(i, j) if fill else None) or "white"
        axis.add_patch(Rectangle((x + j * size, y - (i + 1) * size), size, size, fc=face, ec=DARK, lw=1))
        if not np.isnan(value):
            axis.text(x + (j + 0.5) * size, y - (i + 0.5) * size, format(value, "g").replace("-", "\u2212"), ha="center", va="center", fontsize=fontsize)


def feature_map(values: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """The feature map of ``kernel`` on ``values``, stride 1, no padding and no bias: at each position, the sum of the window times the kernel."""
    windows = np.lib.stride_tricks.sliding_window_view(values, kernel.shape)
    return np.einsum("ijkl,kl->ij", windows, kernel)


def convolution_figure(path: Path) -> dict:
    """One row per shown step: the input with the window of the step, the kernel, the feature map filled up to that step, and the sum of the products."""
    result = feature_map(CONVOLUTION_INPUT, CONVOLUTION_KERNEL)
    k, side = CONVOLUTION_KERNEL.shape[0], result.shape[0]
    with plt.rc_context(STYLE):
        figure, axis = plt.subplots(figsize=(13, 10.5))
        for row, step in enumerate(SHOWN_STEPS):
            top = -6.0 * row
            i, j = divmod(step, side)
            matrix(axis, CONVOLUTION_INPUT, 0, top, lambda a, b: WINDOW if i <= a < i + k and j <= b < j + k else None)
            axis.text(5.0, top - 2, "\u00d7", fontsize=26, ha="center", va="center")
            matrix(axis, CONVOLUTION_KERNEL, 6, top - 1, lambda a, b: KERNEL_CELL)
            axis.text(9.0, top - 2, "=", fontsize=26, ha="center", va="center")
            shown = np.where(np.arange(result.size).reshape(result.shape) <= step, result, np.nan)
            matrix(axis, shown, 10, top - 0.5, lambda a, b: WINDOW if (a, b) == (i, j) else (DONE if a * side + b < step else None))
            products = " + ".join(f"{v:g}\u00d7{w:g}" if w >= 0 else f"{v:g}\u00d7({w:g})" for v, w in zip(CONVOLUTION_INPUT[i:i + k, j:j + k].ravel(), CONVOLUTION_KERNEL.ravel()))
            axis.text(14.0, top - 2, f"{products}\n= {result[i, j]:g}".replace("-", "\u2212"), fontsize=13, va="center")
            note = " (the window moved 1 column: stride 1)" if step == 1 else (" (the last position)" if step == side * side - 1 else "")
            axis.text(0, top + 0.45, f"Step {step + 1} of {side * side}{note}", fontsize=13, fontweight="bold", color=DARK)
        for x, label in ((2.0, f"input, {CONVOLUTION_INPUT.shape[0]} x {CONVOLUTION_INPUT.shape[1]}"), (7.0, f"kernel, {k} x {k}"),
                         (11.5, f"feature map, {side} x {side}")):
            axis.text(x, -6.0 * len(SHOWN_STEPS) + 1.3, label, ha="center", fontsize=13, color=DARK)
        axis.set_xlim(-0.3, 21)
        axis.set_ylim(-6.0 * len(SHOWN_STEPS) + 0.9, 1.2)
        axis.set_aspect("equal")
        axis.axis("off")
        figure.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(figure)
    logger.info(f"convolution: {CONVOLUTION_INPUT.shape} input, {CONVOLUTION_KERNEL.shape} kernel, feature map {result.astype(int).tolist()}, written to {path}")
    return {"convolution_map": str(result.astype(int).tolist())}


def pooling_figure(path: Path) -> dict:
    """The input with its four 2 x 2 windows in four colors, and the max and the average of each window, in the same colors."""
    windows = POOLING_INPUT.reshape(2, 2, 2, 2).swapaxes(1, 2)  # windows[a, b] is the 2 x 2 window in row a, column b
    pooled = {"max pooling": windows.max(axis=(2, 3)), "average pooling": windows.mean(axis=(2, 3))}
    with plt.rc_context(STYLE):
        figure, axis = plt.subplots(figsize=(11, 6))
        matrix(axis, POOLING_INPUT, 0, 4, lambda a, b: BLOCKS[2 * (a // 2) + b // 2])
        axis.text(2, -0.5, "feature map, 4 x 4", ha="center", va="top", fontsize=13, color=DARK)
        for (name, values), top in zip(pooled.items(), (5.0, 1.0)):
            matrix(axis, values, 9, top, lambda a, b: BLOCKS[2 * a + b], size=1.2)
            axis.text(10.2, top - 2.55, f"{name}, 2 x 2", ha="center", va="top", fontsize=13, color=DARK)
            _arrow(axis, (4.3, 2.0), (8.7, top - 1.2))
        axis.text(6.3, 2.0, "windows of 2 x 2,\nstride 2", ha="center", va="center", fontsize=12, color=DARK,
                  bbox={"boxstyle": "round,pad=0.3", "fc": "white", "ec": "none"})
        axis.set_xlim(-0.3, 12)
        axis.set_ylim(-2.3, 5.4)
        axis.set_aspect("equal")
        axis.axis("off")
        figure.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(figure)
    logger.info(f"pooling: max {pooled['max pooling'].tolist()}, average {pooled['average pooling'].tolist()}, written to {path}")
    return {"pooling": f"max {pooled['max pooling'].astype(int).tolist()}, average {pooled['average pooling'].tolist()}"}


def map_stack(axis, x: float, y: float, side: float, count: int, step: float = 0.35) -> tuple:
    """``count`` square feature maps of side ``side``, the back one with its bottom-left corner at (x, y) and each next one shifted right and down by
    ``step``; returns the bottom-left corner of the front one."""
    for k in range(count):
        axis.add_patch(Rectangle((x + k * step, y - k * step), side, side, fc=MAP_FILL, ec=MAP_EDGE, lw=1))
    return x + (count - 1) * step, y - (count - 1) * step


def projection(axis, source: tuple, source_side: float, target: tuple, target_side: float) -> None:
    """A small square on one map, a smaller one on the next, and the lines from the corners of the first to the corners of the second."""
    for corner, side in ((source, source_side), (target, target_side)):
        axis.add_patch(Rectangle(corner, side, side, fc=MAP_EDGE, ec=MAP_EDGE, lw=1, alpha=0.6, zorder=3))
    for dx, dy in ((0, 1), (1, 1), (0, 0), (1, 0)):
        if (dx, dy) in ((0, 1), (1, 0)):  # two opposite corners are enough to show the cone
            axis.plot([source[0] + dx * source_side, target[0] + dx * target_side], [source[1] + dy * source_side, target[1] + dy * target_side],
                      color=MAP_EDGE, lw=0.8, zorder=3)


def architecture_figure(path: Path) -> None:
    """From the patch to the classes: a convolutional layer, a pooling layer, more blocks, the last feature maps, the fully connected layers and the softmax."""
    with Image.open(DEFAULT_PATCH_IMAGE_DIR / f"{INPUT_PATCH}.png") as patch:
        image = np.asarray(patch.convert("RGB"))
    with plt.rc_context(STYLE):
        figure, axis = plt.subplots(figsize=(17, 5.6))
        axis.imshow(image, extent=(0, 3.2, 1.6, 4.8), zorder=1)
        convolution = map_stack(axis, 4.6, 2.9, 2.9, 6)
        pooling = map_stack(axis, 10.2, 2.7, 1.9, 6)
        last = map_stack(axis, 15.4, 2.9, 1.0, 9, step=0.22)
        projection(axis, (1.9, 2.4), 0.45, (convolution[0] + 1.6, convolution[1] + 1.2), 0.18)
        projection(axis, (convolution[0] + 0.5, convolution[1] + 0.4), 0.5, (pooling[0] + 0.5, pooling[1] + 0.4), 0.25)
        axis.text(14.55, 2.6, "\u00b7 \u00b7 \u00b7", fontsize=22, ha="center", va="center")
        _arrow(axis, (18.2, 2.6), (19.0, 2.6))
        hidden = [(19.8, 4.2), (19.8, 3.2), (19.8, 1.2)]
        outputs = [(22.0, 3.7), (22.0, 2.6), (22.0, 1.5)]
        for start in hidden:
            for end in outputs:
                axis.plot(*zip(start, end), color=MAP_EDGE, lw=0.8, zorder=1)
        for position in hidden + outputs:
            axis.add_patch(Circle(position, 0.32, fc=NODE, ec=DARK, lw=1.2, zorder=2))
        axis.text(19.8, 2.25, "\u22ee", fontsize=20, ha="center", va="center")
        for (x, y), name in zip(outputs, ("without dysplasia", "with dysplasia", "OSCC")):
            axis.text(x + 0.5, y, name, fontsize=11, va="center")
        labels = [(1.6, "input patch"), (6.3, "convolution + ReLU\n(one feature map\nper kernel)"), (11.6, "pooling\n(smaller maps,\nsame depth)"),
                  (16.4, "last feature maps\n(small and deep)"), (20.9, "fully connected\n+ softmax")]
        for x, label in labels:
            axis.text(x, 0.3, label, ha="center", va="top", fontsize=12, color=DARK)
        axis.set_xlim(-0.2, 24.6)
        axis.set_ylim(-1.3, 6.1)
        axis.set_aspect("equal")
        axis.axis("off")
        figure.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(figure)
    logger.info(f"cnn architecture: input patch {INPUT_PATCH}, written to {path}")


def hand_attention() -> tuple:
    """Attention of "hand" in ``SENTENCE``, with W_Q, W_K and W_V the identity: the embeddings, the table of scores Q K^T, the scores of "hand" divided by
    sqrt(d_k), their softmax (the weights) and the new embedding of "hand", the weights times the values."""
    x = np.array([EMBEDDINGS[token] for token in SENTENCE])
    scores = x @ x.T
    scaled = scores[SENTENCE.index("hand")] / np.sqrt(x.shape[1])
    weights = np.exp(scaled) / np.exp(scaled).sum()
    return x, scores, scaled, weights, weights @ x


def attention_scores_figure(path: Path) -> dict:
    """The scores Q K^T of ``SENTENCE``: one row per query, one column per key, each cell colored by its score and the row of "hand" outlined."""
    _, scores, *_ = hand_attention()
    n, hand = len(SENTENCE), SENTENCE.index("hand")
    shade = plt.get_cmap("Blues")
    with plt.rc_context(STYLE):
        figure, axis = plt.subplots(figsize=(7.2, 7.0))
        matrix(axis, np.round(scores, 2), 0, n, lambda i, j: shade(0.05 + 0.6 * scores[i, j] / scores.max()), fontsize=12)
        axis.add_patch(Rectangle((0, n - hand - 1), n, 1, fill=False, ec=ACCENT, lw=2.5, zorder=3))
        for k, token in enumerate(SENTENCE):
            axis.text(-0.15, n - k - 0.5, token, ha="right", va="center", fontsize=12, color=DARK)
            axis.text(k + 0.5, n + 0.12, token, ha="left", va="bottom", rotation=45, fontsize=12, color=DARK)
        axis.text(-2.0, n / 2, "queries $Q$", rotation=90, ha="center", va="center", fontsize=12, color=DARK)
        axis.text(n / 2, n + 1.7, "keys $K$", ha="center", va="bottom", fontsize=12, color=DARK)
        axis.set_xlim(-2.4, n + 0.2)
        axis.set_ylim(-0.2, n + 2.5)
        axis.set_aspect("equal")
        axis.axis("off")
        figure.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(figure)
    logger.info(f"attention scores: row of hand {scores[hand].round(2).tolist()}, written to {path}")
    return {"attention_hand_scores": str(scores[hand].round(2).tolist())}


def attention_neuron_figure(path: Path) -> dict:
    """The attention of "hand" drawn like a neuron: each token's value goes into a sum with a line whose width is its weight, and the weights come from the
    scores of "hand" divided by sqrt(d_k) and passed through the softmax, shown in a table on the left."""
    x, _, scaled, weights, new = hand_attention()
    n = len(SENTENCE)
    body, radius = np.array([5.2, (n - 1) / 2]), 0.5
    with plt.rc_context(STYLE):
        figure, axis = plt.subplots(figsize=(13, 6.4))
        for column, header in ((-4.6, "score\n$q_{hand} \\cdot k_j / \\sqrt{d_k}$"), (-2.4, "weight $a_j$\n(softmax)"), (0.7, "value $v_j$")):
            axis.text(column, n - 0.2, header, ha="center", va="bottom", fontsize=12, color=DARK)
        for j, token in enumerate(SENTENCE):
            y = n - 1 - j
            color = ACCENT if token == "hand" else DARK
            axis.text(-4.6, y, f"{scaled[j]:.2f}", ha="center", va="center", fontsize=13, color=color)
            axis.text(-2.4, y, f"{weights[j]:.2f}", ha="center", va="center", fontsize=13, color=color)
            axis.add_patch(FancyBboxPatch((0.0, y - 0.3), 1.4, 0.6, boxstyle="round,pad=0.03", fc=NODE, ec=DARK, lw=1.2, zorder=2))
            axis.text(0.7, y, token, ha="center", va="center", fontsize=12, color=color, zorder=3)
            start = np.array([1.45, y])
            direction = (body - start) / np.linalg.norm(body - start)
            _arrow(axis, start, body - radius * direction, color=color, lw=0.5 + 14 * weights[j])
        axis.add_patch(Circle(body, radius, fc=NODE, ec=DARK, lw=1.4, zorder=2))
        axis.text(*body, "$\\Sigma$", ha="center", va="center", fontsize=18, zorder=3)
        _arrow(axis, body + np.array([radius, 0]), body + np.array([1.6, 0]))
        values = ", ".join(f"{v:.2f}" for v in new)
        axis.text(body[0] + 1.75, body[1], f"new embedding\nof hand\n({values})", va="center", fontsize=12, color=ACCENT)
        axis.text(body[0] - 0.3, -0.95, "$z_{hand} = \\sum_j a_j v_j$", ha="center", fontsize=14)
        axis.text(-3.5, -1.15, "the weights are computed from $q$ and $k$, not learned", ha="center", fontsize=11, color=DARK)
        axis.text(body[0] - 0.3, -1.55, "line width: weight $a_j$", ha="center", fontsize=11, color=DARK)
        axis.set_xlim(-5.6, 9.2)
        axis.set_ylim(-1.8, n + 0.6)
        axis.set_aspect("equal")
        axis.axis("off")
        figure.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(figure)
    logger.info(f"attention neuron: scaled scores {scaled.round(2).tolist()}, weights {weights.round(3).tolist()}, new hand {new.round(2).tolist()}, "
                f"written to {path}")
    return {"attention_hand_weights": str(weights.round(2).tolist()), "attention_new_hand": str(new.round(2).tolist())}


def network_steps(out: Path) -> dict:
    neuron_figure(out / "neuron_activations.png")
    architecture_figure(out / "cnn_architecture.png")
    return (network_figure(out / "network_layers.png") | descent_figure(out / "gradient_descent.png") | convolution_figure(out / "convolution_kernel.png")
            | pooling_figure(out / "pooling.png") | attention_scores_figure(out / "attention_scores.png")
            | attention_neuron_figure(out / "attention_neuron.png"))
