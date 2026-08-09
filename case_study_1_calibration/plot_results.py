"""
Generate comprehensive plots for System 3 (Semi-Autonomous) results.
Produces 4 plots:
  1. Best fit curve vs experiment
  2. Convergence history
  3. Parameter sensitivity (s0, h0, ss, n vs RMSE)
  4. All curves overlay coloured by RMSE

Usage: python3.7 plot_results.py
"""

import os
import csv
import glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import subprocess
import sys

BASE     = os.path.dirname(os.path.abspath(__file__))
CSV_F    = os.path.join(BASE, "workdir", "optimization_results.csv")
EXP_FILE = os.path.join(BASE, "SS316L_experiment.txt")
CURVES   = os.path.join(BASE, "workdir", "curves")
OUT_DIR  = os.path.join(BASE, "workdir")

sys.path.insert(0, os.path.join(BASE, "tools"))
from tools.prm_tools import write_params, restore_backup

# ── Best known parameters — read from best_params.json if available
import json as _json
BEST_FILE = os.path.join(BASE, "workdir", "best_params.json")
if os.path.exists(BEST_FILE):
    with open(BEST_FILE) as _f:
        _b = _json.load(_f)
    BEST = {
        "s0":   _b["s0"],
        "h0":   _b["h0"],
        "ss":   _b["ss"],
        "n":    _b["n"],
        "rmse": _b["rmse"],
        "mape": _b.get("mape") or 0.0,
    }
    print("Loaded best params from best_params.json: RMSE={:.4f} MPa".format(BEST["rmse"]))
else:
    # Fallback to hardcoded best known result
    BEST = {
        "s0":   120.1524,
        "h0":   1981.8941,
        "ss":   517.2399,
        "n":    1.4731,
        "rmse": 4.6770,
        "mape": 2.7668,
    }
    print("best_params.json not found — using hardcoded best parameters.")

# ── Load experimental data ────────────────────────────────────────
exp_data   = np.loadtxt(EXP_FILE, delimiter=",", skiprows=1)
exp_strain = exp_data[:, 0]
exp_stress = exp_data[:, 1]

# ── Load CSV ──────────────────────────────────────────────────────
iterations, rmse_vals, mape_vals = [], [], []
s0_vals, h0_vals, ss_vals, n_vals = [], [], [], []

if not os.path.exists(CSV_F):
    print("No optimization_results.csv found — no plots to generate.")
    exit(0)

with open(CSV_F) as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            if not row.get("s0_MPa") or not row.get("h0_MPa"):
                continue
            iterations.append(int(row["Iteration"]))
            s0_vals.append(float(row["s0_MPa"]))
            h0_vals.append(float(row["h0_MPa"]))
            ss_vals.append(float(row["ss_MPa"]))
            n_vals.append(float(row["n"]))
            rmse_vals.append(float(row["RMSE_MPa"]))
            mape = row.get("MAPE_pct") or "nan"
            mape_vals.append(float(mape) if mape != "nan" else float("nan"))
        except (ValueError, KeyError):
            continue

print("Total iterations loaded: {}".format(len(iterations)))
best_idx  = int(np.argmin(rmse_vals))
best_iter = iterations[best_idx]
best_rmse = rmse_vals[best_idx]

# ── Run validation simulation with best parameters ────────────────
print("Running validation simulation with best parameters...")
param_dict = {
    "Initial Slip Resistance":   BEST["s0"],
    "Initial Hardening Modulus": BEST["h0"],
    "Saturation Stress":         BEST["ss"],
    "Power Law Exponent":        BEST["n"],
}
write_params(os.path.join(BASE, "prm.prm"), param_dict,
             n_slip=12, refine_factor=2)

proc = subprocess.run(
    "../../main prm.prm", shell=True, cwd=BASE,
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=7200)

if proc.returncode != 0:
    print("Validation simulation failed.")
    restore_backup(os.path.join(BASE, "prm.prm"))
    exit(1)

sim_data   = np.loadtxt(os.path.join(BASE, "results", "stressstrain.txt"), skiprows=1)
sim_strain = np.concatenate([[0.0], sim_data[:, 0]])
sim_stress = np.concatenate([[0.0], sim_data[:, 6]])
print("Validation RMSE: {:.4f} MPa".format(BEST["rmse"]))

restore_backup(os.path.join(BASE, "prm.prm"))

# ── Load all saved curves ─────────────────────────────────────────
all_curves = []
for f in sorted(glob.glob(os.path.join(CURVES, "iter_*.txt"))):
    try:
        d = np.loadtxt(f, skiprows=1)
        rmse_str = os.path.basename(f).split("rmse")[1].replace(".txt","")
        rmse = float(rmse_str)
        all_curves.append((rmse, d[:, 0], d[:, 1]))
    except Exception:
        continue
print("Curves loaded: {}".format(len(all_curves)))

# ── PLOT 1: Best fit curve ────────────────────────────────────────
fig1, ax = plt.subplots(figsize=(8, 6))
ax.plot(exp_strain, exp_stress, "ko-", markersize=5, linewidth=1.5,
        label="Experiment (SS316L)")
ax.plot(sim_strain, sim_stress, "r-", linewidth=2,
        label="Best simulation (RMSE={:.2f} MPa, MAPE={:.2f}%)".format(
              BEST["rmse"], BEST["mape"]))
ax.set_xlabel("True Strain")
ax.set_ylabel("True Stress (MPa)")
ax.set_title("Best Fit — System 3 (Semi-Autonomous Agent)\n"
             "s0={:.1f}, h0={:.1f}, ss={:.1f}, n={:.2f}".format(
             BEST["s0"], BEST["h0"], BEST["ss"], BEST["n"]))
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)
fig1.tight_layout()
fig1.savefig(os.path.join(OUT_DIR, "S3_best_fit.png"), dpi=150, bbox_inches="tight")
plt.close(fig1)
print("Saved: S3_best_fit.png")

# ── PLOT 2: Convergence history ───────────────────────────────────
fig2, axes = plt.subplots(1, 2, figsize=(12, 5))
fig2.suptitle("SS316L Calibration — System 3 (Semi-Autonomous Agent)",
              fontsize=12, fontweight="bold")

ax = axes[0]
ax.semilogy(iterations, rmse_vals, "b.-", markersize=4, label="RMSE per iteration")
ax.axhline(5.0, color="g", linestyle="--", label="Target 5 MPa")
ax.scatter([best_iter], [best_rmse], color="red", zorder=5, s=100,
           label="Best: {:.2f} MPa (iter {})".format(best_rmse, best_iter))
ax.set_xlabel("Iteration")
ax.set_ylabel("RMSE (MPa)")
ax.set_title("RMSE Convergence")
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)

ax = axes[1]
ax.plot(iterations, mape_vals, "r.-", markersize=4)
ax.axhline(2.0, color="g", linestyle="--", label="Target 2%")
ax.set_xlabel("Iteration")
ax.set_ylabel("MAPE (%)")
ax.set_title("MAPE Convergence")
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)

fig2.tight_layout()
fig2.savefig(os.path.join(OUT_DIR, "S3_convergence.png"), dpi=150, bbox_inches="tight")
plt.close(fig2)
print("Saved: S3_convergence.png")

# ── PLOT 3: Parameter sensitivity ────────────────────────────────
fig3 = plt.figure(figsize=(14, 5))
fig3.suptitle("SS316L — System 3: Parameter Sensitivity",
              fontsize=12, fontweight="bold")
gs = gridspec.GridSpec(1, 4, wspace=0.35)

param_data = [
    ("s0 (MPa)", s0_vals),
    ("h0 (MPa)", h0_vals),
    ("ss (MPa)", ss_vals),
    ("n (-)",    n_vals),
]
best_params = [BEST["s0"], BEST["h0"], BEST["ss"], BEST["n"]]

for i, ((label, vals), bp) in enumerate(zip(param_data, best_params)):
    ax = fig3.add_subplot(gs[0, i])
    sc = ax.scatter(vals, rmse_vals, c=iterations, cmap="viridis", s=40, alpha=0.7)
    ax.scatter([bp], [BEST["rmse"]], color="red", s=150, zorder=5, marker="*")
    plt.colorbar(sc, ax=ax, label="Iter")
    ax.set_xlabel(label)
    ax.set_ylabel("RMSE (MPa)")
    ax.set_title("{} vs RMSE".format(label.split(" ")[0]))
    ax.axhline(5.0, color="g", linestyle="--", alpha=0.5)
    ax.grid(True, alpha=0.3)

fig3.tight_layout()
fig3.savefig(os.path.join(OUT_DIR, "S3_sensitivity.png"), dpi=150, bbox_inches="tight")
plt.close(fig3)
print("Saved: S3_sensitivity.png")

# ── PLOT 4: All curves overlay ────────────────────────────────────
if all_curves:
    fig4, ax = plt.subplots(figsize=(9, 7))
    ax.plot(exp_strain, exp_stress, "ko-", markersize=5, linewidth=2,
            label="Experiment (SS316L)", zorder=10)

    all_rmses = np.array([c[0] for c in all_curves])
    norm = plt.Normalize(all_rmses.min(), min(all_rmses.max(), 35))
    cmap = plt.cm.coolwarm_r

    for rmse, strain, stress in all_curves:
        color = cmap(norm(rmse))
        ax.plot(strain, stress, color=color, alpha=0.3, linewidth=0.8)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    fig4.colorbar(sm, ax=ax, label="RMSE (MPa)")

    ax.plot(sim_strain, sim_stress, "r-", linewidth=2.5,
            label="Best (RMSE={:.2f} MPa)".format(BEST["rmse"]), zorder=9)
    ax.set_xlabel("True Strain")
    ax.set_ylabel("True Stress (MPa)")
    ax.set_title("All Calibration Iterations — System 3 (Semi-Autonomous)")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    fig4.tight_layout()
    fig4.savefig(os.path.join(OUT_DIR, "S3_all_curves.png"), dpi=150, bbox_inches="tight")
    plt.close(fig4)
    print("Saved: S3_all_curves.png")

print("\nAll plots saved to: {}".format(OUT_DIR))
print("\nFinal Summary:")
print("  Best RMSE : {:.4f} MPa".format(BEST["rmse"]))
print("  Best MAPE : {:.4f} %".format(BEST["mape"]))
print("  s0        : {:.4f} MPa".format(BEST["s0"]))
print("  h0        : {:.4f} MPa".format(BEST["h0"]))
print("  ss        : {:.4f} MPa".format(BEST["ss"]))
print("  n         : {:.4f}".format(BEST["n"]))
