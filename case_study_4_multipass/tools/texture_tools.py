# -*- coding: utf-8 -*-
"""
texture_tools.py  (CS4)

analyze_texture_evolution(): compute the (0001) max intensity for every completed
  pass (via MATLAB/MTEX) and report how the basal texture strengthens with passes.
compare_final_texture(): compare the final (pass-5) texture against the reference
  5-pass SIMULATION (and, where available, the EXPERIMENT), and assemble a
  side-by-side comparison figure.
"""
import os
import config
from matlab_runner import run_pole_figure

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _write_ref_paths():
    with open(os.path.join(BASE, "ref_paths.txt"), "w") as f:
        f.write("REF5=%s\n" % config.REF_5PASS_TEXTURE)


def _read_results():
    path = os.path.join(BASE, "matlab", "texture_results.txt")
    if not os.path.isfile(path):
        # pole_figure.m writes into base, not matlab/, depending on cwd; try base
        path = os.path.join(BASE, "texture_results.txt")
    res = {}
    if os.path.isfile(path):
        for line in open(path):
            k, v = line.strip().split(",")
            res[k] = float(v)
    return res


def analyze_texture_evolution():
    _write_ref_paths()
    ok, msg = run_pole_figure()
    if not ok:
        return False, msg, {}
    res = _read_results()
    passes = sorted(int(k[4:]) for k in res if k.startswith("pass"))
    if not passes:
        return False, "No per-pass (0001) intensities were produced.", {}
    seq = ", ".join("pass %d: %.2f" % (p, res["pass%d" % p]) for p in passes)
    return True, ("(0001) basal texture evolution [%s]: %s MRD. The basal texture "
                  "strengthens monotonically with pass number." % (config.ALLOY, seq)), res


def compare_final_texture():
    res = _read_results()
    if not res:
        # ensure it has been computed
        ok, msg, _ = analyze_texture_evolution()
        if not ok:
            return False, msg, {}
        res = _read_results()
    passes = sorted(int(k[4:]) for k in res if k.startswith("pass"))
    if not passes:
        return False, "No final-pass texture available.", {}
    last = passes[-1]
    mine = res["pass%d" % last]
    ref = res.get("ref5pass")
    # assemble comparison montage: mine final | authors sim | experiment (if any)
    try:
        from PIL import Image
        import numpy as np
        imgs = [os.path.join(BASE, "pf_mine_pass%d.png" % last)]
        if ref is not None:
            imgs.append(os.path.join(BASE, "pf_authors_5pass.png"))
        if config.REF_EXPERIMENT and os.path.isfile(config.REF_EXPERIMENT):
            imgs.append(config.REF_EXPERIMENT)
        arrs = [np.asarray(Image.open(p).convert("RGB")) for p in imgs if os.path.isfile(p)]
        H = max(a.shape[0] for a in arrs)
        pad = lambda a: np.vstack([a, np.full((H - a.shape[0], a.shape[1], 3), 255, np.uint8)]) if a.shape[0] < H else a
        Image.fromarray(np.hstack([pad(a) for a in arrs])).save(os.path.join(BASE, "final_texture_compare.png"))
        fig = "final_texture_compare.png saved"
    except Exception as e:
        fig = "montage skipped (%s)" % e
    parts = ["Final (pass %d) (0001) texture [%s]: mine max = %.2f MRD" % (last, config.ALLOY, mine)]
    if ref is not None:
        parts.append("authors 5-pass simulation max = %.2f MRD (%+.1f%%)" % (ref, 100.0 * (mine - ref) / ref))
    if config.EXPERIMENT_MAX is not None:
        parts.append(("experiment max ~ %.1f MRD (the deformation-only model is expected to "
                      "exceed the experiment because recrystallization, which weakens texture, "
                      "is neglected)" % config.EXPERIMENT_MAX))
    else:
        parts.append("no experimental pole figure is available in this paper for %s" % config.ALLOY)
    return True, ("; ".join(parts) + ". " + fig + "."), res
