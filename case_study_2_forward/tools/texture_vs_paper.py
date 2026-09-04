# -*- coding: utf-8 -*-
"""
texture_vs_paper.py

Builds the aligned "this study vs paper" pole-figure comparison:
  top row    = this simulation's post-deformation {111},{100},{110} pole figures
  bottom row = the reference paper Fig. 2c ({111},{100},{110})
both on the SAME fixed 0-3.5 MRD colour scale, columns aligned by {hkl}.

Inputs (already produced by generate_pole_figures / oriplot_big.m):
  matlab/figures/tile_mine_111.png , _100.png , _110.png   (this study, 0-3.5, upper hemisphere)
Reference:
  Reference_Plot_figures.png   (paper Fig. 2c: three circles {111},{100},{110} + colorbar)

Output:
  matlab/figures/texture_vs_paper.png
"""

import os

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG_DIR   = os.path.join(BASE_DIR, "matlab", "figures")
REF_IMG   = os.path.join(BASE_DIR, "Reference_Plot_figures.png")
OUT_PATH  = os.path.join(FIG_DIR, "texture_vs_paper.png")

# Column x-ranges of the three circles in Reference_Plot_figures.png (paper Fig. 2c),
# order {111},{100},{110}. Determined from the reference image content bands.
REF_COLS = {"111": (63, 392), "100": (416, 743), "110": (765, 1093)}
ORDER    = ["111", "100", "110"]


def _sat_disk(arr):
    """Crop an RGB array to the coloured pole-figure disk (saturation bbox) and
    resize to a fixed square, so every tile is the same size and centred."""
    import numpy as np
    from PIL import Image
    a = arr.astype(int)
    sat = a.max(2) - a.min(2)
    m = sat > 40
    xs = np.where(m.sum(0) > 3)[0]
    ys = np.where(m.sum(1) > 3)[0]
    crop = arr[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return np.array(Image.fromarray(crop).resize((420, 420), Image.LANCZOS))


def build_paper_comparison():
    """Compose the aligned this-study-vs-paper figure. Returns (ok, msg, path)."""
    import numpy as np
    from PIL import Image
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import cm, colors

    for h in ORDER:
        t = os.path.join(FIG_DIR, "tile_mine_{}.png".format(h))
        if not os.path.isfile(t):
            return False, "Missing simulation tile: tile_mine_{}.png (run generate_pole_figures first)".format(h), None
    if not os.path.isfile(REF_IMG):
        return False, "Reference image not found: {}".format(REF_IMG), None

    mine = {h: _sat_disk(np.array(Image.open(os.path.join(FIG_DIR, "tile_mine_{}.png".format(h))).convert("RGB")))
            for h in ORDER}
    R = np.array(Image.open(REF_IMG).convert("RGB"))
    ref = {h: _sat_disk(R[:, a:b]) for h, (a, b) in REF_COLS.items()}

    fig = plt.figure(figsize=(11, 7.6))
    gs = fig.add_gridspec(2, 4, width_ratios=[1, 1, 1, 0.07],
                          hspace=0.06, wspace=0.06,
                          left=0.09, right=0.9, top=0.9, bottom=0.03)
    for j, h in enumerate(ORDER):
        ax = fig.add_subplot(gs[0, j]); ax.imshow(mine[h])
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title("{" + h + "}", fontsize=15, fontweight="bold")
        for s in ax.spines.values():
            s.set_visible(False)
        ax2 = fig.add_subplot(gs[1, j]); ax2.imshow(ref[h])
        ax2.set_xticks([]); ax2.set_yticks([])
        for s in ax2.spines.values():
            s.set_visible(False)
    fig.text(0.02, 0.68, "This study", fontsize=13,
             fontweight="bold", rotation=90, va="center", ha="center")
    fig.text(0.02, 0.26, "Yaghoobi et al. (2022)", fontsize=13,
             fontweight="bold", rotation=90, va="center", ha="center")
    cax = fig.add_subplot(gs[:, 3])
    sm = cm.ScalarMappable(norm=colors.Normalize(0, 3.5), cmap="jet")
    cb = fig.colorbar(sm, cax=cax); cb.set_label("MRD", fontsize=12)

    if not os.path.isdir(FIG_DIR):
        os.makedirs(FIG_DIR)
    fig.savefig(OUT_PATH, dpi=200, facecolor="white")
    plt.close(fig)
    return True, "This-study-vs-paper pole-figure comparison saved.", OUT_PATH


if __name__ == "__main__":
    ok, msg, path = build_paper_comparison()
    print(("SUCCESS: " if ok else "FAILED: ") + msg)
    if path:
        print("Output:", path)
