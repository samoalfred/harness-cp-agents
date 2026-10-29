# -*- coding: utf-8 -*-
"""
stress_strain_compare.py

Compares the simulated compression stress-strain response against the
experimental Cu dataset of Anand & Kothari (1996).

The simulation is uniaxial compression along Z (BCinfo face 6, DoF 3), so the
compression axis coincides with the pole-figure centre (Fig. 10 convention).
PRISMS writes results/stressstrain.txt with the axial stress in column Tzz
(index 8), negative in compression. For compression the magnitudes are taken so
the response is plotted as a positive (tensile-equivalent) curve.

Conversions (both confirmed with the user):

  STRAIN. The x-axis is the NOMINAL APPLIED true strain, i.e. the strain
  commanded by the boundary condition, not the simulation's volume-averaged
  Green strain (which undershoots the nominal under clamped BCs). The BC ramps
  a displacement |d| over N increments on a domain of length L along the
  loaded axis, so at row i (1..N):
        engineering strain  = (i / N) * |d| / L
        true (log) strain   = |ln(1 - (i / N) * |d| / L)|.
  |d|/L is read from BCinfo.txt and prm.prm by _applied_eng_strain().

  STRESS. The axial Cauchy component Tzz is used directly (true stress):
        sig = |Tzz|.
  NOTE: |Tzz| equals the uniaxial flow stress only when the stress state is
  genuinely uniaxial (Txx = Tyy ~ 0). The roller/symmetry BCs used here give
  that uniaxial state, so |Tzz| is the flow stress with no confinement pressure.

The experiment runs to a true strain of 1.0; the simulation runs to a lower
strain. The two curves are compared over their overlapping strain range and
error metrics (RMSE, MAPE) are reported there.

Output: matlab/figures/stress_strain_comparison.png
"""

import os

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIM_FILE    = os.path.join(BASE_DIR, "results", "stressstrain.txt")
EXP_FILE    = os.path.join(BASE_DIR, "Cu_AnandKothari1996.csv")
BCINFO_FILE = os.path.join(BASE_DIR, "BCinfo.txt")
PRM_FILE    = os.path.join(BASE_DIR, "prm.prm")
FIG_DIR     = os.path.join(BASE_DIR, "matlab", "figures")
FIG_PATH    = os.path.join(FIG_DIR, "stress_strain_comparison.png")

# Column indices in results/stressstrain.txt (tab-separated, 1 header row)
# Order: Exx Eyy Ezz Eyz Exz Exy  Txx Tyy Tzz Tyz Txz Txy  ...
# Loading is along Z (BCinfo face 6, DoF 3), so the axial stress is Tzz (index 8).
IDX_AXIAL = 8   # Tzz, axial Cauchy stress along the loaded (Z) direction


def _applied_eng_strain():
    """
    Total applied engineering strain magnitude along the loaded axis,
    = |displacement| / L, read from BCinfo.txt (the row with the largest
    |FinalDisplacement|, i.e. the loading BC) and prm.prm (Domain size along
    the loaded DoF). This defines the NOMINAL applied strain used on the x-axis.
    """
    dof, disp = 1, None
    with open(BCINFO_FILE) as fh:
        for line in fh:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            parts = s.split()
            if len(parts) >= 3:
                try:
                    d = float(parts[2])
                except ValueError:
                    continue
                if disp is None or abs(d) > abs(disp):
                    disp, dof = d, int(parts[1])
    if disp is None:
        raise ValueError("No loading displacement found in BCinfo.txt")
    axis = {1: "X", 2: "Y", 3: "Z"}.get(dof, "X")
    L = 1.0
    with open(PRM_FILE) as fh:
        for line in fh:
            if line.strip().startswith("set Domain size " + axis):
                L = float(line.split("=")[1].strip())
                break
    return abs(disp) / L


def compare_stress_strain():
    """
    Build the simulated-vs-experimental stress-strain comparison figure.
    Returns (success, message, info_dict).
    """
    import numpy as np

    if not os.path.isfile(SIM_FILE):
        return False, "Simulated stressstrain.txt not found: {}".format(SIM_FILE), {}
    if not os.path.isfile(EXP_FILE):
        return False, "Experimental file not found: {}".format(EXP_FILE), {}

    # ── Simulated curve ──
    sim = np.loadtxt(SIM_FILE, skiprows=1)
    if sim.ndim == 1:
        sim = sim.reshape(1, -1)

    txx = sim[:, IDX_AXIAL]          # axial Cauchy (true) stress, Tzz (loaded Z)

    # STRAIN: nominal APPLIED true strain from the boundary condition.
    n       = sim.shape[0]                         # one row per increment
    max_eng = _applied_eng_strain()               # |d| / L along the loaded axis
    idx     = np.arange(1, n + 1, dtype=float)     # increment index, 1..N
    eng     = (idx / n) * max_eng                  # applied engineering strain
    eng     = np.clip(eng, 0.0, 0.999999)          # guard for compression log
    sim_strain = np.abs(np.log(1.0 - eng))         # applied true (log) strain
    # STRESS: axial Cauchy component, true stress = |Txx|
    sim_stress = np.abs(txx)
    sim_max    = float(sim_strain.max())

    # ── Experimental curve (already tension-converted) ──
    exp = np.loadtxt(EXP_FILE, delimiter=",", skiprows=1)
    exp_strain = exp[:, 0]
    exp_stress = exp[:, 1]

    # ── Overlap region for quantitative comparison (up to ~40%) ──
    lo = max(sim_strain.min(), exp_strain.min())
    hi = min(sim_max, exp_strain.max())
    grid = np.linspace(lo, hi, 100)
    sim_i = np.interp(grid, sim_strain, sim_stress)
    exp_i = np.interp(grid, exp_strain, exp_stress)

    rmse = float(np.sqrt(np.mean((sim_i - exp_i) ** 2)))
    nz   = exp_i > 1e-9
    mape = float(np.mean(np.abs((sim_i[nz] - exp_i[nz]) / exp_i[nz])) * 100.0)

    # ── Plot ──
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not os.path.isdir(FIG_DIR):
        os.makedirs(FIG_DIR)

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    ax.plot(exp_strain, exp_stress, "ko-", ms=4, lw=1.5,
            label="Experiment (Anand & Kothari 1996)")
    ax.plot(sim_strain, sim_stress, "r-", lw=2.0,
            label="Simulation (|axial Txx|)")
    ax.axvline(sim_max, color="0.6", ls="--", lw=1.0,
               label="Simulation limit ({:.2f})".format(sim_max))
    ax.set_xlabel("Nominal applied true strain")
    ax.set_ylabel("True stress (MPa)")
    ax.set_title("Cu stress-strain: simulation vs experiment\n"
                 "Overlap 0 to {:.2f}:  RMSE = {:.2f} MPa,  MAPE = {:.2f}%"
                 .format(hi, rmse, mape))
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    fig.savefig(FIG_PATH, dpi=200)
    plt.close(fig)

    info = {"rmse": rmse, "mape": mape, "sim_max_strain": sim_max,
            "overlap_hi": hi, "n_sim": int(sim.shape[0])}
    msg = ("Stress-strain comparison written. Simulation reaches strain {:.3f}; "
           "over the overlap 0 to {:.2f}, RMSE = {:.2f} MPa, MAPE = {:.2f}%."
           ).format(sim_max, hi, rmse, mape)
    return True, msg, info


if __name__ == "__main__":
    ok, msg, info = compare_stress_strain()
    print(("SUCCESS: " if ok else "FAILED: ") + msg)
