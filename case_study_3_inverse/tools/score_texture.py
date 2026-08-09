# -*- coding: utf-8 -*-
"""
score_texture.py -- objective function for the Case Study 3 inverse problem.

Reads the post-deformation orientations (Rodrigues vectors) produced by a run,
computes {100},{110},{111} pole-figure features in pure Python (no MATLAB, so it
is fast enough to call inside an optimization loop), and returns a scalar loss
measuring the distance to the Fig. 10 target (fig10_targets.json).

Key discriminating features of the Fig. 10 compression texture:
  {110} : central MAXIMUM  (the <110> compression fibre along the load axis Z)
  {100} : central minimum
  {111} : central minimum
plus the peak intensities. The loss rewards reproducing this pattern.
"""
import os, json
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.dirname(_HERE)
POST_FILE    = os.path.join(_BASE, "matlab", "orientations_post_deformation.csv")
TARGET_FILE  = os.path.join(_BASE, "fig10_targets.json")

HALFWIDTH_DEG = 8.0     # ODF kernel halfwidth (matches the pipeline)
CENTER_CAP_DEG = 12.0   # cap half-angle used for the "central" intensity


def _sym_dirs(hkl):
    """Cubic m-3m symmetric equivalents of {hkl}, as unit vectors (all signs)."""
    h, k, l = hkl
    base = set()
    from itertools import permutations, product
    for p in set(permutations([abs(h), abs(k), abs(l)])):
        for sx, sy, sz in product([1, -1], repeat=3):
            v = (p[0]*sx, p[1]*sy, p[2]*sz)
            if v == (0, 0, 0):
                continue
            base.add(v)
    V = np.array(sorted(base), float)
    return V / np.linalg.norm(V, axis=1, keepdims=True)


def _rod_to_R(r):
    """Rodrigues vectors (N,3) -> rotation matrices (N,3,3)."""
    mag = np.linalg.norm(r, axis=1)
    ang = 2.0 * np.arctan(mag)
    ax = np.where(mag[:, None] > 1e-12, r / np.maximum(mag[:, None], 1e-12),
                  np.array([0.0, 0.0, 1.0]))
    x, y, z = ax[:, 0], ax[:, 1], ax[:, 2]
    c = np.cos(ang); s = np.sin(ang); C = 1 - c
    R = np.empty((len(r), 3, 3))
    R[:, 0, 0] = c + x*x*C;   R[:, 0, 1] = x*y*C - z*s; R[:, 0, 2] = x*z*C + y*s
    R[:, 1, 0] = y*x*C + z*s;  R[:, 1, 1] = c + y*y*C;  R[:, 1, 2] = y*z*C - x*s
    R[:, 2, 0] = z*x*C - y*s;  R[:, 2, 1] = z*y*C + x*s; R[:, 2, 2] = c + z*z*C
    return R


def _hemi_grid(n=1500):
    """Roughly equal-area points on the upper hemisphere (Fibonacci)."""
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - i / n)          # 0..pi/2 (upper hemisphere)
    theta = np.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.sin(phi)*np.cos(theta),
                     np.sin(phi)*np.sin(theta),
                     np.cos(phi)], axis=1)


def pole_figure_mrd(poles, grid, hw_deg=HALFWIDTH_DEG):
    """Density (MRD) of sample-frame poles evaluated on grid, kernel-smoothed."""
    hw = np.radians(hw_deg)
    # antipodal: use |cos(angle)|
    cs = np.abs(poles @ grid.T)                 # (Npoles, Ngrid)
    ang = np.arccos(np.clip(cs, -1, 1))
    dens = np.exp(-(ang ** 2) / (2 * hw ** 2)).sum(0)
    return dens / dens.mean()                    # normalise so mean MRD = 1


def compute_features(post_file=POST_FILE):
    r = np.loadtxt(post_file, delimiter=",")[:, :3]
    R = _rod_to_R(r)
    grid = _hemi_grid()
    zc = np.argmax(grid[:, 2])                    # grid point nearest Z (centre)
    cap = np.radians(CENTER_CAP_DEG)
    feats = {}
    for name, hkl in [("100", (1, 0, 0)), ("110", (1, 1, 0)), ("111", (1, 1, 1))]:
        H = _sym_dirs(hkl)                        # (M,3)
        poles = np.einsum("nij,mj->nmi", R, H).reshape(-1, 3)   # sample-frame poles
        poles[poles[:, 2] < 0] *= -1             # fold to upper hemisphere
        mrd = pole_figure_mrd(poles, grid)
        # central intensity = mean MRD within the cap around Z
        ang_to_Z = np.arccos(np.clip(np.abs(grid[:, 2]), -1, 1))
        center = mrd[ang_to_Z < cap].mean()
        feats[name] = {"peak": float(mrd.max()), "center": float(center)}
    return feats


def score(post_file=POST_FILE, target_file=TARGET_FILE, verbose=True):
    feats = compute_features(post_file)
    tgt = json.load(open(target_file))["pole_figures"]
    # target central intensity: {110} is a maximum (~peak), {100}/{111} minima
    tgt_center = {"100": 0.4, "110": tgt["110"]["peak_MRD"], "111": 0.4}
    loss = 0.0
    parts = {}
    for n in ["100", "110", "111"]:
        dpeak = feats[n]["peak"] - tgt[n]["peak_MRD"]
        dctr = feats[n]["center"] - tgt_center[n]
        w = 2.0 if n == "110" else 1.0           # weight the fibre feature
        li = w * (0.5 * dpeak ** 2 + dctr ** 2)
        loss += li
        parts[n] = {"peak": round(feats[n]["peak"], 2), "center": round(feats[n]["center"], 2),
                    "tgt_peak": tgt[n]["peak_MRD"], "tgt_center": tgt_center[n],
                    "contrib": round(li, 3)}
    if verbose:
        print("feature            peak   center  tgt_peak tgt_center contrib")
        for n in ["100", "110", "111"]:
            p = parts[n]
            print("  {%s}%s %6.2f %7.2f %8.2f %9.2f %8.3f" %
                  (n, "" if len(n) == 3 else " ", p["peak"], p["center"],
                   p["tgt_peak"], p["tgt_center"], p["contrib"]))
        print("TOTAL LOSS = %.3f" % loss)
    return loss, parts


if __name__ == "__main__":
    import sys
    pf = sys.argv[1] if len(sys.argv) > 1 else POST_FILE
    score(pf)
