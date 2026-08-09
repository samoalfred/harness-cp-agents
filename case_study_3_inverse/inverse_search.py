#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-
"""
inverse_search.py -- Case Study 3 inverse problem.

Bayesian optimization over the INITIAL TEXTURE to reproduce the Fig. 10
deformation texture. Each evaluation runs the full forward pipeline
(generate -> convert -> compress -> extract orientations) and scores the
deformed texture against fig10_targets.json with tools/score_texture.py.

Design variables (what the agent recovers):
  - texture mode : {random, fiber[100], fiber[110], fiber[111]}   (categorical,
                    'random' is an explicit reachable state)
  - sigma_spread : initial fibre spread in degrees, [3, 85]        (continuous,
                    ignored when mode == random)

Everything else is fixed (Cu slip parameters, 40% Z-compression, roller BCs,
~400 grains, refine factor set in prm.prm). Budget: 15 evaluations.

Expected result: the search selects the random mode (or a very diffuse fibre),
recovering that a near-random initial texture reproduces Fig. 10.
"""
import os, sys, csv, json, time
import numpy as np

_BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BASE)
sys.path.insert(0, os.path.join(_BASE, "tools"))

from param_injector import inject_microstructure_params
from matlab_runner import run_microstructure_gen
from h5_converter import convert_h5_to_prisms
from single_sim import run_single_simulation
from texture_analysis import find_last_quadrature_csv, extract_orientations
from score_texture import score

from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel as C
from scipy.stats import norm

N_BUDGET   = 15
BIG_LOSS   = 100.0
SIGMA_LO, SIGMA_HI = 3.0, 85.0
FIBERS = {"f100": [1, 0, 0], "f110": [1, 1, 0], "f111": [1, 1, 1]}

WORKDIR = os.path.join(_BASE, "workdir")
LOG     = os.path.join(WORKDIR, "inverse_log.csv")
BEST    = os.path.join(WORKDIR, "best_texture.json")


# ── candidate pool + encoding ──────────────────────────────────────
def build_pool():
    pool = [{"mode": "random", "fiber": [1, 0, 1], "sigma": 45.0}]
    for fk, fv in FIBERS.items():
        for s in np.linspace(SIGMA_LO, SIGMA_HI, 18):
            pool.append({"mode": fk, "fiber": fv, "sigma": float(s)})
    return pool


def encode(c):
    # one-hot(random,f100,f110,f111) + sigma_norm
    modes = ["random", "f100", "f110", "f111"]
    oh = [1.0 if c["mode"] == m else 0.0 for m in modes]
    sn = 0.5 if c["mode"] == "random" else (c["sigma"] - SIGMA_LO) / (SIGMA_HI - SIGMA_LO)
    return oh + [sn]


# ── one expensive evaluation: full forward pipeline + score ────────
def evaluate(c):
    params = {
        "orientation_type": "random" if c["mode"] == "random" else "textured",
        "sigma_spread":     float(c["sigma"]),
        "fiber_direction":  c["fiber"],
    }
    ok, msg = inject_microstructure_params(params)
    if not ok:
        print("  inject FAILED:", msg); return BIG_LOSS, {}
    ok, msg = run_microstructure_gen()
    if not ok:
        print("  generate FAILED:", msg); return BIG_LOSS, {}
    ok, msg, _ = convert_h5_to_prisms()
    if not ok:
        print("  convert FAILED:", msg); return BIG_LOSS, {}
    ok, msg = run_single_simulation()
    if not ok:
        print("  simulation FAILED:", msg); return BIG_LOSS, {}
    res = find_last_quadrature_csv()
    if res is None:
        print("  no quadrature output"); return BIG_LOSS, {}
    csv_path, _ = res
    ok, msg, _ = extract_orientations(csv_path)
    if not ok:
        print("  extract FAILED:", msg); return BIG_LOSS, {}
    loss, parts = score(verbose=False)
    return float(loss), parts


def expected_improvement(mu, sd, f_best):
    sd = np.maximum(sd, 1e-9)
    z = (f_best - mu) / sd
    return (f_best - mu) * norm.cdf(z) + sd * norm.pdf(z)   # minimisation


def log_row(it, c, loss, parts):
    new = not os.path.exists(LOG)
    with open(LOG, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["iter", "mode", "fiber", "sigma", "loss",
                        "p100", "c100", "p110", "c110", "p111", "c111"])
        g = lambda n, k: parts.get(n, {}).get(k, "")
        w.writerow([it, c["mode"], "".join(map(str, c["fiber"])), round(c["sigma"], 1),
                    round(loss, 4), g("100","peak"), g("100","center"),
                    g("110","peak"), g("110","center"), g("111","peak"), g("111","center")])


def run_search(method="bayesian", budget=N_BUDGET):
    """
    Run the inverse texture search. method: 'bayesian' (GP + expected
    improvement) or 'random' (random sampling baseline). Returns a result dict.
    """
    if not os.path.isdir(WORKDIR):
        os.makedirs(WORKDIR)
    pool = build_pool()
    Xp = np.array([encode(c) for c in pool])

    # initial design: random + each fibre at mid spread
    init_idx = [0]
    for fk in ["f100", "f110", "f111"]:
        cand = [i for i, c in enumerate(pool) if c["mode"] == fk]
        init_idx.append(cand[len(cand) // 2])

    evaluated, Xs, ys, history = [], [], [], []
    rng = np.random.RandomState(0)
    t0 = time.time()
    rf = "?"
    try:
        for _ln in open(os.path.join(_BASE, "prm.prm")):
            if _ln.strip().startswith("set Refine factor"):
                rf = _ln.split("=")[1].strip(); break
    except Exception:
        pass
    print("=" * 64)
    print("  Case Study 3: inverse texture search (%s)" % method)
    print("  Budget: %d evaluations | refine factor %s" % (budget, rf))
    print("=" * 64)

    for it in range(1, budget + 1):
        if method == "bayesian" and it <= len(init_idx):
            idx = init_idx[it - 1]
        elif method == "bayesian":
            gp = GaussianProcessRegressor(
                kernel=C(1.0) * Matern(length_scale=[1.0]*5, nu=2.5) + WhiteKernel(1e-2),
                normalize_y=True, n_restarts_optimizer=3, alpha=1e-6)
            gp.fit(np.array(Xs), np.array(ys))
            mu, sd = gp.predict(Xp, return_std=True)
            ei = expected_improvement(mu, sd, min(ys))
            for j in evaluated:
                ei[j] = -1.0                      # do not re-pick
            idx = int(np.argmax(ei))
        else:                                     # random baseline
            remaining = [i for i in range(len(pool)) if i not in evaluated]
            idx = int(rng.choice(remaining))

        c = pool[idx]
        print("\n[iter %d/%d] mode=%s fiber=%s sigma=%.1f" %
              (it, budget, c["mode"], c["fiber"], c["sigma"]))
        loss, parts = evaluate(c)
        print("  -> loss = %.4f  (elapsed %.1f min)" % (loss, (time.time()-t0)/60))
        evaluated.append(idx); Xs.append(encode(c)); ys.append(loss)
        history.append({"iter": it, "mode": c["mode"], "sigma": c["sigma"], "loss": loss})
        log_row(it, c, loss, parts)

        best_i = int(np.argmin(ys))
        bc = pool[evaluated[best_i]]
        json.dump({"iter": best_i + 1, "mode": bc["mode"], "fiber": bc["fiber"],
                   "sigma": bc["sigma"], "loss": ys[best_i]},
                  open(BEST, "w"), indent=2)

    print("\n" + "=" * 64)
    print("  BEST: mode=%s fiber=%s sigma=%.1f  loss=%.4f" %
          (bc["mode"], bc["fiber"], bc["sigma"], ys[best_i]))
    print("  Log: %s" % LOG)
    print("=" * 64)
    return {"method": method, "n_evals": budget, "log": LOG,
            "best": {"mode": bc["mode"], "fiber": bc["fiber"],
                     "sigma": bc["sigma"], "loss": ys[best_i]},
            "history": history}


def main():
    method = sys.argv[1] if len(sys.argv) > 1 else "bayesian"
    run_search(method, N_BUDGET)


if __name__ == "__main__":
    main()
