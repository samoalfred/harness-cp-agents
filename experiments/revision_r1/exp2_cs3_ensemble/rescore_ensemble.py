#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-
"""
rescore_ensemble.py  --  Experiment 2 (Revision R1), Phase 2: re-scoring (zero sims).

Reads each realization's inverse_log.csv (ensemble/log_seed*.csv) and, per realization,
reports under the DIGITIZED target (fig2c_targets.json):
  - random-mode loss, best diffuse-[110] loss, and their gap,
and under a SELF-CONSISTENT target:
  - whether the random mode is the global optimum.

Why this needs no new simulations
---------------------------------
score_texture.py splits cleanly into a target-INDEPENDENT part (the six pole-figure
features peak/center for {100},{110},{111}, computed from the deformed orientations) and a
target-DEPENDENT part (a weighted sum of squared differences of those features from the
target's peak/central values). The six features are already logged every evaluation
(columns p100,c100,p110,c110,p111,c111), so re-scoring against any target is arithmetic.

The self-consistent target
--------------------------
T_sc = the model's own feature-space image of a RANDOM initial texture, i.e. the mean of
the random-mode evaluations' six features across the ensemble (same 8 deg kernel / 12 deg
cap the scorer uses). It removes the digitization footing of the published figure. Weights
are the same as the digitized target. (With a single seed, T_sc is that seed's own random
features; use >=2 seeds for a meaningful ensemble.)

Loss (identical to tools/score_texture.py):
  loss = sum_n  w_n * ( 0.5*(peak_n - tgt_peak_n)^2 + (center_n - tgt_center_n)^2 )
  over n in {100,110,111}, with w = {111:1, 100:1, 110:2}.

Outputs: console table, ensemble/ensemble_summary.csv, ensemble/ensemble_summary.json.
"""

import os
import sys
import csv
import json
import glob
import math

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
ENS = os.path.join(HERE, "ensemble")
TARGET_FILE = os.path.join(HERE, "fig2c_targets.json")
PFS = ["100", "110", "111"]


def resolve_features(seed, rows):
    """If this seed's per-eval orientation archive exists, recompute the six pole-figure
    features at FULL precision with the genuine scorer (tools/score_texture.compute_features),
    replacing the 2-decimal features stored in the log. Returns True if the archive was used.
    Matching is by evaluation index: ori_eval_<iter>.csv <-> log row 'iter'."""
    archdir = os.path.join(ENS, "seed%d" % seed, "orientations")
    if not os.path.isdir(archdir):
        return False
    import score_texture
    used = False
    for r in rows:
        p = os.path.join(archdir, "ori_eval_%02d.csv" % r["iter"])
        if os.path.isfile(p):
            r["feat"] = score_texture.compute_features(p)
            used = True
    return used


def load_target():
    doc = json.load(open(TARGET_FILE))
    tg = doc["pole_figures"]
    weights = {n: float(doc.get("weights", {}).get(n, 1.0)) for n in PFS}
    tgt = {n: {"peak": float(tg[n]["peak_MRD"]), "center": float(tg[n]["central_MRD"])} for n in PFS}
    return tgt, weights


def load_log(path):
    rows = []
    with open(path) as f:
        for d in csv.DictReader(f):
            rows.append({
                "iter": int(d["iter"]), "mode": d["mode"], "sigma": float(d["sigma"]),
                "loss_logged": float(d["loss"]),
                "feat": {n: {"peak": float(d["p" + n]), "center": float(d["c" + n])} for n in PFS},
            })
    return rows


def loss_vs(feat, tgt, weights):
    L = 0.0
    for n in PFS:
        dp = feat[n]["peak"] - tgt[n]["peak"]
        dc = feat[n]["center"] - tgt[n]["center"]
        L += weights[n] * (0.5 * dp * dp + dc * dc)
    return L


def mean_std(xs):
    n = len(xs)
    if n == 0:
        return float("nan"), float("nan")
    m = sum(xs) / n
    if n == 1:
        return m, 0.0
    v = sum((x - m) ** 2 for x in xs) / (n - 1)
    return m, math.sqrt(v)


def main():
    tgt_dig, weights = load_target()
    logs = sorted(glob.glob(os.path.join(ENS, "log_seed*.csv")))
    if not logs:
        print("No ensemble/log_seed*.csv found. Run Phase 1 (run_ensemble.py) first,")
        print("or drop the reference log in as ensemble/log_seed0.csv to test re-scoring.")
        return

    seeds = []
    n_archived = 0
    for p in logs:
        seed = int(os.path.basename(p).split("seed")[1].split(".")[0])
        rows = load_log(p)
        if resolve_features(seed, rows):
            n_archived += 1
        seeds.append((seed, rows))

    feature_source = ("full-precision archived orientations (%d/%d seeds)" % (n_archived, len(seeds))
                      if n_archived else "2-decimal logged features (no orientation archive found)")
    print("Feature source: %s" % feature_source)

    # --- self-check: recompute the digitized loss from the resolved features ---
    max_err = 0.0
    for _s, rows in seeds:
        for r in rows:
            max_err = max(max_err, abs(loss_vs(r["feat"], tgt_dig, weights) - r["loss_logged"]))
    print("Self-check: max |recomputed digitized loss - logged loss| = %.4g" % max_err)
    if n_archived == len(seeds) and max_err > 1e-3:
        print("  WARNING: full-precision re-score disagrees with the logged loss; investigate.")
    elif n_archived < len(seeds):
        print("  Note: with logged 2-decimal features a rounding error up to ~0.04 is expected;")
        print("        run Phase 1 so the archived orientations give an exact re-score.")

    # --- self-consistent target: mean random-mode features across the ensemble ---
    rnd_feats = []
    for _s, rows in seeds:
        for r in rows:
            if r["mode"] == "random":
                rnd_feats.append(r["feat"])
    if not rnd_feats:
        print("No random-mode evaluations found; cannot build the self-consistent target.")
        return
    tgt_sc = {n: {"peak": sum(f[n]["peak"] for f in rnd_feats) / len(rnd_feats),
                  "center": sum(f[n]["center"] for f in rnd_feats) / len(rnd_feats)} for n in PFS}

    # --- per-realization measurements ---
    rows_out = []
    gaps = []
    rnd_opt_count = 0
    for seed, rows in seeds:
        rnd = [r for r in rows if r["mode"] == "random"]
        f110 = [r for r in rows if r["mode"] == "f110"]
        if not rnd or not f110:
            print("  seed %d: missing random or f110 evaluations; skipped." % seed)
            continue
        rnd_dig = min(r["loss_logged"] for r in rnd)
        best110_dig = min(r["loss_logged"] for r in f110)
        gap = rnd_dig - best110_dig                      # >0 means [110] beats random (digitized)
        gaps.append(gap)

        # self-consistent target: which mode is the global optimum?
        for r in rows:
            r["loss_sc"] = loss_vs(r["feat"], tgt_sc, weights)
        argmin = min(rows, key=lambda r: r["loss_sc"])
        rnd_sc = min(r["loss_sc"] for r in rnd)
        best110_sc = min(r["loss_sc"] for r in f110)
        random_is_opt = (argmin["mode"] == "random")
        rnd_opt_count += int(random_is_opt)

        rows_out.append({
            "seed": seed,
            "random_loss_dig": round(rnd_dig, 4),
            "best110_loss_dig": round(best110_dig, 4),
            "gap_dig": round(gap, 4),
            "random_loss_sc": round(rnd_sc, 4),
            "best110_loss_sc": round(best110_sc, 4),
            "argmin_mode_sc": argmin["mode"],
            "random_is_optimum_sc": random_is_opt,
        })

    M = len(rows_out)
    gmean, gstd = mean_std(gaps)

    # --- console table ---
    print("\n" + "=" * 92)
    print("Experiment 2 - CS3 realization ensemble (M = %d realizations, budget %d)" % (M, 15))
    print("=" * 92)
    print("%-6s %12s %12s %10s | %12s %12s %8s" %
          ("seed", "rand(dig)", "best110(dig)", "gap(dig)",
           "rand(sc)", "best110(sc)", "argmin"))
    print("-" * 92)
    for r in rows_out:
        print("%-6d %12.4f %12.4f %10.4f | %12.4f %12.4f %8s%s" %
              (r["seed"], r["random_loss_dig"], r["best110_loss_dig"], r["gap_dig"],
               r["random_loss_sc"], r["best110_loss_sc"], r["argmin_mode_sc"],
               "  <-- random" if r["random_is_optimum_sc"] else ""))
    print("-" * 92)
    print("Digitized target: gap (random - best[110]) = %.4f +/- %.4f across %d realizations" %
          (gmean, gstd, M))
    print("Self-consistent target: random is the global optimum in %d/%d realizations" %
          (rnd_opt_count, M))
    print("=" * 92)

    # --- write artifacts ---
    with open(os.path.join(ENS, "ensemble_summary.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seed", "random_loss_dig", "best110_loss_dig", "gap_dig",
                    "random_loss_sc", "best110_loss_sc", "argmin_mode_sc", "random_is_optimum_sc"])
        for r in rows_out:
            w.writerow([r["seed"], r["random_loss_dig"], r["best110_loss_dig"], r["gap_dig"],
                        r["random_loss_sc"], r["best110_loss_sc"], r["argmin_mode_sc"],
                        r["random_is_optimum_sc"]])
    summary = {
        "n_realizations": M,
        "budget": 15,
        "digitized_gap_mean": gmean, "digitized_gap_std": gstd,
        "random_optimum_fraction_sc": "%d/%d" % (rnd_opt_count, M),
        "self_consistent_target": tgt_sc,
        "weights": weights,
        "per_realization": rows_out,
        "selfcheck_max_loss_err": max_err,
    }
    with open(os.path.join(ENS, "ensemble_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("Wrote ensemble/ensemble_summary.csv and ensemble/ensemble_summary.json")


if __name__ == "__main__":
    main()
