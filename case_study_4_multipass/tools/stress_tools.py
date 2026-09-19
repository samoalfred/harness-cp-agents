# -*- coding: utf-8 -*-
"""
stress_tools.py  (CS4)

compare_stress_strain(): after pass 1, compare the simulated single-pass
mechanical response against the reference simulation of the paper.

For a Taylor / velocity-gradient BC the state is multiaxial, so the reported
flow stress is the plane-strain flow stress  sigma_yy - sigma_zz  (extension
minus compression Cauchy component), plotted against TRUE (log) strain,
eps = -0.5*ln(1 + 2*E_zz)  (E_zz is the Green-Lagrange component in
stressstrain.txt). RMSE and MAPE are computed over the 0-20% range on a common
strain grid. The reference stress-strain file may extend past 20% (a longer
continuous run); only the overlapping 0-20% window is used.
"""
import os, math
import config

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(path, cap=0.166):
    hdr = None; E = []; S = []
    with open(path) as f:
        for line in f:
            t = line.split()
            if hdr is None:
                hdr = t; idx = {n: i for i, n in enumerate(hdr)}
                continue
            if len(t) < 9:
                continue
            Ezz = float(t[idx["Ezz"]])
            eps = -0.5 * math.log(1 + 2 * Ezz)
            flow = float(t[idx["Tyy"]]) - float(t[idx["Tzz"]])
            if eps <= cap:
                E.append(eps); S.append(flow)
    return E, S


def _interp(x, xp, fp):
    if x <= xp[0]:
        return fp[0]
    if x >= xp[-1]:
        return fp[-1]
    for i in range(1, len(xp)):
        if x <= xp[i]:
            t = (x - xp[i-1]) / (xp[i] - xp[i-1])
            return fp[i-1] + t * (fp[i] - fp[i-1])
    return fp[-1]


def compare_stress_strain():
    sim = os.path.join(BASE, "pass1", "out", "stressstrain.txt")
    ref = config.REF_1PASS_STRESS
    if not os.path.isfile(sim):
        return False, "Pass-1 stressstrain.txt not found; run pass 1 first.", {}
    if not os.path.isfile(ref):
        return False, "Reference 1-pass stress file not found: %s" % ref, {}
    Es, Ss = _load(sim); Er, Sr = _load(ref)
    # common grid over overlap
    lo = max(min(Es), min(Er)); hi = min(max(Es), max(Er))
    n = 40; grid = [lo + (hi - lo) * k / (n - 1) for k in range(n)]
    ss = [_interp(g, Es, Ss) for g in grid]
    sr = [_interp(g, Er, Sr) for g in grid]
    rmse = math.sqrt(sum((a - b) ** 2 for a, b in zip(ss, sr)) / n)
    mape = 100.0 * sum(abs(a - b) / abs(b) for a, b in zip(ss, sr) if b != 0) / n
    endmine = Ss[-1]; endref = Sr[-1]
    info = {"rmse": rmse, "mape": mape, "end_mine": endmine, "end_ref": endref}
    return True, ("Single-pass stress-strain vs reference simulation (%s): "
                  "RMSE = %.2f MPa, MAPE = %.2f%% over 0-20%% true strain. "
                  "End flow stress sigma_yy-sigma_zz: mine %.1f MPa vs reference %.1f MPa "
                  "(%+.1f%%)." % (config.ALLOY, rmse, mape, endmine, endref,
                                  100.0 * (endmine - endref) / endref)), info
