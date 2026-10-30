#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-
"""
run_ensemble.py  --  Experiment 2 (Revision R1): CS3 realization ensemble.

Answers Reviewer R8: the diffuse-[110]-vs-random separation under the DIGITIZED target
lies within realization noise, and under a SELF-CONSISTENT (same-kernel) target the
random mode is recovered.

PHASE 1 (this script, SIM-HEAVY, no API needed):
  For each RNG seed in SEEDS, regenerate the 400-grain copper RVE with that seed and run
  the GENUINE CS3 Bayesian inverse search (budget 15) under the digitized target. The
  forward pipeline (generate -> convert -> compress -> extract -> score) is the deployed
  one in inverse_search.py; this driver only (a) sets the seed in microstructure_gen.m,
  (b) keeps each seed's inverse_log.csv, and (c) archives every evaluation's deformed
  orientations as insurance for re-scoring. Cost = len(SEEDS) * 15 forward runs.

PHASE 2 (rescore_ensemble.py, CHEAP, zero sims):
  Re-score every evaluation against a self-consistent target built from the ensemble's own
  random-mode forward features. Called automatically at the end, or run on its own later.

This runs entirely inside the copied folder R1_Exp2_CS3_Ensemble; the original
CS3_Inverse_Problem is never touched.

Usage (inside WSL, MATLAB + PRISMS available; NO OpenAI key needed):
    python3.7 run_ensemble.py                 # seeds 0..4, budget 15
    python3.7 run_ensemble.py --seeds 0 1 2   # subset
    python3.7 run_ensemble.py --rescore-only  # skip sims, just (re)build the tables
"""

import os
import re
import sys
import json
import shutil
import argparse
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

ENS = os.path.join(HERE, "ensemble")
GEN = os.path.join(HERE, "matlab", "microstructure_gen.m")
DEFAULT_SEEDS = [0, 1, 2, 3, 4]
BUDGET = 15

# archive counter shared with the patched evaluate()
_counter = {"it": 0}


def set_seed(seed):
    """Set rng_seed = <seed> in microstructure_gen.m (the injector never touches this line)."""
    with open(GEN) as f:
        c = f.read()
    # assert the PATTERN matched (count==1), not that the text changed -- when the file
    # already holds the target seed (e.g. seed 0), re.sub returns identical text, which is
    # still a correct, successful match.
    c2, n = re.subn(r"(rng_seed\s*=\s*)\d+", r"\g<1>%d" % seed, c, count=1)
    assert n == 1, "set_seed: 'rng_seed = <int>' line not found in microstructure_gen.m"
    with open(GEN, "w") as f:
        f.write(c2)


def _install_archiver(INV):
    """Wrap inverse_search.evaluate so each eval's deformed orientations are archived.
    Keeps inverse_search.py itself byte-identical to the deployed version."""
    orig = INV.evaluate

    def patched(c):
        loss, parts = orig(c)
        _counter["it"] += 1
        arch = os.environ.get("R1_ARCHIVE_DIR")
        if arch and os.path.isfile(INV.POST_SEARCH):
            if not os.path.isdir(arch):
                os.makedirs(arch)
            shutil.copyfile(INV.POST_SEARCH,
                            os.path.join(arch, "ori_eval_%02d.csv" % _counter["it"]))
        return loss, parts

    INV.evaluate = patched


def run_seed(INV, seed):
    print("\n" + "#" * 70)
    print("# REALIZATION seed=%d  (budget %d, Bayesian, digitized target)" % (seed, BUDGET))
    print("#" * 70)
    set_seed(seed)
    if os.path.isfile(INV.LOG):
        os.remove(INV.LOG)                      # fresh per-seed log
    os.environ["R1_ARCHIVE_DIR"] = os.path.join(ENS, "seed%d" % seed, "orientations")
    _counter["it"] = 0
    res = INV.run_search(method="bayesian", budget=BUDGET, final_rerun=False)
    shutil.copyfile(INV.LOG, os.path.join(ENS, "log_seed%d.csv" % seed))
    if os.path.isfile(INV.BEST):
        shutil.copyfile(INV.BEST, os.path.join(ENS, "best_seed%d.json" % seed))
    print("[seed %d] saved ensemble/log_seed%d.csv" % (seed, seed))
    return res


def main():
    ap = argparse.ArgumentParser(description="Experiment 2: CS3 realization ensemble.")
    ap.add_argument("--seeds", type=int, nargs="+", default=DEFAULT_SEEDS)
    ap.add_argument("--rescore-only", action="store_true",
                    help="skip the simulations; only (re)build the re-scored tables")
    args = ap.parse_args()

    if not os.path.isdir(ENS):
        os.makedirs(ENS)

    if not args.rescore_only:
        import inverse_search as INV
        _install_archiver(INV)
        # restore seed line to 0 on exit regardless of outcome
        try:
            for s in args.seeds:
                run_seed(INV, s)
        finally:
            try:
                set_seed(0)
            except Exception:
                pass

    # Phase 2: re-score (cheap)
    import rescore_ensemble
    rescore_ensemble.main()


if __name__ == "__main__":
    main()
