"""
Simulation tools for System 3 (Semi-Autonomous).
Hard stopping criteria enforced here — outside LLM control.
"""

import os
import sys
import subprocess
import numpy as np
import csv
import json
from datetime import datetime
from pathlib import Path

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = os.path.dirname(_TOOLS_DIR)

PRM_FILE         = os.path.join(BASE_DIR, "prm.prm")
RESULTS_FILE     = os.path.join(BASE_DIR, "results", "stressstrain.txt")
EXP_FILE         = os.path.join(BASE_DIR, "SS316L_experiment.txt")
LOG_FILE         = os.path.join(BASE_DIR, "workdir", "optimization_results.csv")
CURVES_DIR       = os.path.join(BASE_DIR, "workdir", "curves")
BEST_FILE        = os.path.join(BASE_DIR, "workdir", "best_params.json")
SIM_COMMAND      = "../../main prm.prm"
N_SLIP           = 12
SIM_TIMEOUT      = 7200
PENALTY          = 1e6

MAX_EVALUATIONS  = 60
RMSE_THRESHOLD   = 5.0
MAPE_THRESHOLD   = 2.0

_exp_strain = None
_exp_stress = None
_iteration_counter = [0]


class CalibrationConverged(Exception):
    """Raised when stopping criteria are met."""
    pass


def _load_experiment():
    global _exp_strain, _exp_stress
    if _exp_strain is None:
        data = np.loadtxt(EXP_FILE, delimiter=",", skiprows=1)
        idx = np.argsort(data[:, 0])
        _exp_strain = data[idx, 0]
        _exp_stress = data[idx, 1]


def _write_prm(s0, h0, ss, n):
    import re, shutil
    backup = Path(PRM_FILE).with_suffix(".prm.bak")
    if not backup.exists():
        shutil.copy(PRM_FILE, str(backup))
    param_map = {
        "Initial Slip Resistance":   s0,
        "Initial Hardening Modulus": h0,
        "Saturation Stress":         ss,
        "Power Law Exponent":        n,
    }
    with open(PRM_FILE) as f:
        lines = f.readlines()
    new_lines = []
    for line in lines:
        replaced = False
        for key, val in param_map.items():
            pat = re.compile(
                r"^(\s*set\s+" + re.escape(key) + r"\s*=\s*)(.+)$", re.IGNORECASE)
            m = pat.match(line)
            if m:
                new_lines.append("{}{}\n".format(
                    m.group(1), ", ".join(str(val) for _ in range(N_SLIP))))
                replaced = True
                break
        if not replaced:
            new_lines.append(line)
    with open(PRM_FILE, "w") as f:
        f.writelines(new_lines)


def _compute_rmse(sim_strain, sim_stress):
    from scipy.interpolate import interp1d
    _load_experiment()
    lo = max(sim_strain.min(), _exp_strain.min())
    hi = min(sim_strain.max(), _exp_strain.max())
    if hi <= lo:
        return PENALTY
    mask = (_exp_strain >= lo) & (_exp_strain <= hi)
    if mask.sum() < 2:
        return PENALTY
    interp = interp1d(sim_strain, sim_stress, kind="linear",
                      bounds_error=False, fill_value="extrapolate")
    return float(np.sqrt(np.mean((interp(_exp_strain[mask]) - _exp_stress[mask]) ** 2)))


def _compute_mape(sim_strain, sim_stress):
    from scipy.interpolate import interp1d
    _load_experiment()
    lo = max(sim_strain.min(), _exp_strain.min())
    hi = min(sim_strain.max(), _exp_strain.max())
    mask = (_exp_strain >= lo) & (_exp_strain <= hi)
    nonzero = mask & (_exp_stress > 1.0)
    if nonzero.sum() == 0:
        return float("nan")
    interp = interp1d(sim_strain, sim_stress, kind="linear",
                      bounds_error=False, fill_value="extrapolate")
    return float(np.mean(
        np.abs(interp(_exp_strain[nonzero]) - _exp_stress[nonzero])
        / _exp_stress[nonzero]) * 100.0)


def _log_result(s0, h0, ss, n, rmse, mape, sim_strain, sim_stress):
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    file_exists = os.path.exists(LOG_FILE)
    it = _iteration_counter[0]
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Iteration","Timestamp","s0_MPa","h0_MPa",
                             "ss_MPa","n","RMSE_MPa","MAPE_pct"])
        writer.writerow([it, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                         round(s0,4), round(h0,4), round(ss,4), round(n,4),
                         round(rmse,4),
                         round(mape,4) if not np.isnan(mape) else "nan"])
    # Save curve
    Path(CURVES_DIR).mkdir(parents=True, exist_ok=True)
    np.savetxt(os.path.join(CURVES_DIR, "iter_{:04d}_rmse{:.2f}.txt".format(it, rmse)),
               np.column_stack([sim_strain, sim_stress]),
               header="Exx  Txx_MPa", comments="")
    # Update best
    best = {"iteration": it, "s0": s0, "h0": h0, "ss": ss, "n": n,
            "rmse": rmse, "mape": float(mape) if not np.isnan(mape) else None}
    if not os.path.exists(BEST_FILE):
        with open(BEST_FILE, "w") as f:
            json.dump(best, f, indent=2)
    else:
        with open(BEST_FILE) as f:
            current = json.load(f)
        if rmse < current.get("rmse", float("inf")):
            with open(BEST_FILE, "w") as f:
                json.dump(best, f, indent=2)
            print("  [sim] New best saved: RMSE={:.4f} MPa".format(rmse))


def run_simulation(s0, h0, ss, n, timeout=SIM_TIMEOUT):
    """
    Run one PRISMS-Plasticity simulation.
    Returns (rmse, mape).
    Raises CalibrationConverged when stopping criteria are met.
    """
    _iteration_counter[0] += 1
    it = _iteration_counter[0]
    print("  [sim] Eval {}: s0={:.3g} h0={:.3g} ss={:.3g} n={:.3g}".format(
          it, s0, h0, ss, n))

    try:
        _write_prm(s0, h0, ss, n)
    except Exception as e:
        print("  [sim] PRM write failed: {}".format(e))
        return PENALTY, PENALTY

    try:
        proc = subprocess.run(SIM_COMMAND, shell=True, cwd=BASE_DIR,
                              timeout=timeout,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print("  [sim] Non-zero exit: {}".format(proc.returncode))
            return PENALTY, PENALTY
    except subprocess.TimeoutExpired:
        print("  [sim] Timeout.")
        return PENALTY, PENALTY
    except Exception as e:
        print("  [sim] Error: {}".format(e))
        return PENALTY, PENALTY

    try:
        data = np.loadtxt(RESULTS_FILE, skiprows=1)
        if data.ndim == 1:
            data = data.reshape(1, -1)
        sim_strain = np.concatenate([[0.0], data[:, 0]])
        sim_stress = np.concatenate([[0.0], data[:, 6]])
    except Exception as e:
        print("  [sim] Parse failed: {}".format(e))
        return PENALTY, PENALTY

    rmse = _compute_rmse(sim_strain, sim_stress)
    mape = _compute_mape(sim_strain, sim_stress)
    _log_result(s0, h0, ss, n, rmse, mape, sim_strain, sim_stress)
    print("  [sim] RMSE={:.3f} MPa  MAPE={:.2f}%".format(
          rmse, mape if not np.isnan(mape) else -1))

    # ── Hard stopping — guaranteed regardless of algorithm ────────
    if it >= MAX_EVALUATIONS:
        print("  [sim] Budget reached ({} evals). Stopping.".format(it))
        raise CalibrationConverged("Budget ({} evaluations)".format(it))
    if rmse < RMSE_THRESHOLD:
        print("  [sim] RMSE={:.3f} < {} MPa. Stopping.".format(rmse, RMSE_THRESHOLD))
        raise CalibrationConverged("RMSE={:.3f} MPa".format(rmse))
    if not np.isnan(mape) and mape < MAPE_THRESHOLD:
        print("  [sim] MAPE={:.3f}% < {}%. Stopping.".format(mape, MAPE_THRESHOLD))
        raise CalibrationConverged("MAPE={:.3f}%".format(mape))

    return rmse, mape


def get_experimental_data():
    _load_experiment()
    return _exp_strain.copy(), _exp_stress.copy()


def reset_counter():
    """Reset evaluation counter for a fresh run."""
    _iteration_counter[0] = 0
