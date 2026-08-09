# -*- coding: utf-8 -*-
"""
texture_compare.py
Creates a publication-quality side-by-side comparison of pre- and
post-deformation pole figures.

Layout : 3 rows ({100}, {110}, {111}) x 2 columns (Pre | Post)
Output : matlab/figures/texture_comparison.png  (300 DPI)
"""

import os

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg
    from matplotlib import rcParams
except ImportError:
    raise ImportError("matplotlib is required: pip install matplotlib")

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG_DIR     = os.path.join(BASE_DIR, "matlab", "figures")
POST_DIR    = os.path.join(FIG_DIR, "post_deformation")
OUTPUT_FILE = os.path.join(FIG_DIR, "texture_comparison.png")

PRE_FIGS  = ["pre_pf100.png",  "pre_pf110.png",  "pre_pf111.png"]
POST_FIGS = ["post_pf100.png", "post_pf110.png", "post_pf111.png"]
HKL_LABELS = ["(100)", "(110)", "(111)"]

# Publication-quality font settings
rcParams.update({
    "font.family":      "serif",
    "font.size":        11,
    "axes.titlesize":   12,
    "axes.titleweight": "bold",
    "axes.labelsize":   11,
    "figure.dpi":       150,
})


def create_comparison():
    """
    Load pre/post pole figure PNGs and arrange them side by side.
    Returns (success, message, output_path).
    """
    for fname in PRE_FIGS:
        p = os.path.join(FIG_DIR, fname)
        if not os.path.isfile(p):
            return False, "Pre-deformation figure missing: {}".format(fname), None

    for fname in POST_FIGS:
        p = os.path.join(POST_DIR, fname)
        if not os.path.isfile(p):
            return False, "Post-deformation figure missing: {}".format(fname), None

    print("[Compare] Creating publication-quality texture comparison...")

    fig = plt.figure(figsize=(12, 16), facecolor="white")

    # Column headers
    col_header_y = 0.975
    fig.text(0.28, col_header_y, "Pre-Deformation",
             ha="center", va="top", fontsize=14, fontweight="bold",
             color="#1a1a2e")
    fig.text(0.72, col_header_y, "Post-Deformation",
             ha="center", va="top", fontsize=14, fontweight="bold",
             color="#1a1a2e")

    # Dividing line between columns
    fig.add_artist(plt.Line2D([0.50, 0.50], [0.04, 0.96],
                               transform=fig.transFigure,
                               color="#cccccc", linewidth=1.0))

    axes = []
    for row in range(3):
        for col in range(2):
            ax = fig.add_subplot(3, 2, row * 2 + col + 1)
            axes.append(ax)

    for row, (pre_f, post_f, label) in enumerate(zip(PRE_FIGS, POST_FIGS, HKL_LABELS)):
        ax_pre  = axes[row * 2]
        ax_post = axes[row * 2 + 1]

        pre_img  = mpimg.imread(os.path.join(FIG_DIR,    pre_f))
        post_img = mpimg.imread(os.path.join(POST_DIR, post_f))

        ax_pre.imshow(pre_img,  interpolation="lanczos")
        ax_pre.axis("off")
        ax_pre.set_title("{} Pole Figure".format(label),
                         fontsize=11, pad=4, color="#1a1a2e")

        ax_post.imshow(post_img, interpolation="lanczos")
        ax_post.axis("off")
        ax_post.set_title("{} Pole Figure".format(label),
                          fontsize=11, pad=4, color="#1a1a2e")

    plt.tight_layout(rect=[0, 0.01, 1, 0.955])
    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)

    print("[Compare] Saved (300 DPI): {}".format(OUTPUT_FILE))
    return True, "Publication-quality comparison figure saved.", OUTPUT_FILE


if __name__ == "__main__":
    ok, msg, path = create_comparison()
    print(msg)
    if path:
        print("Output: {}".format(path))
