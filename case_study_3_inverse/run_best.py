#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-
"""
run_best.py -- re-run the recovered optimum at FULL Taylor substeps.

The inverse search runs at reduced Taylor substeps (30) for speed. After the
search, this re-runs the best candidate in workdir/best_texture.json at 100
substeps (fully converged, matching CS2) to regenerate its deformed
orientations and final pole figures.
"""
import os, sys, json, re, time

_BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BASE)
from inverse_search import evaluate

BEST = os.path.join(_BASE, "workdir", "best_texture.json")
PRM  = os.path.join(_BASE, "prm.prm")
SUBSTEPS_FINAL = 100


def set_substeps(n):
    with open(PRM) as f:
        c = f.read()
    c = re.sub(r"(set Number of Taylor Substeps\s*=\s*)\d+", r"\g<1>{}".format(n), c)
    with open(PRM, "w") as f:
        f.write(c)


def main():
    b = json.load(open(BEST))
    print("RUN_BEST", b, flush=True)
    set_substeps(SUBSTEPS_FINAL)
    print("Taylor substeps set to %d for the final run." % SUBSTEPS_FINAL, flush=True)
    c = {"mode": b["mode"], "fiber": b["fiber"], "sigma": float(b["sigma"])}
    t0 = time.time()
    loss, parts = evaluate(c)
    print("RUN_BEST DONE loss=%.4f (%.1f min)" % (loss, (time.time() - t0) / 60.0), flush=True)
    print("parts:", parts, flush=True)


if __name__ == "__main__":
    main()
