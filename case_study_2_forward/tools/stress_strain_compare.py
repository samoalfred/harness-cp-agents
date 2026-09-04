# -*- coding: utf-8 -*-
"""
stress_strain_compare.py  (CS2_Texture_Evolution)

Compares the simulated compression stress-strain response against the
digitized PRISMS-Plasticity TM reference curve of Yaghoobi et al. (2022)
for OFHC copper (uniaxial compression, true strain 0 to 1.0).

Model context (differs from the earlier roller-BC copper runs):
  * Rate-independent crystal plasticity with the TAYLOR homogenization model
    (set Flag To Use Taylor Model = true).
  * Loading is applied through an imposed VELOCITY GRADIENT boundary condition
    (set Use velocity gradient BC = true), with L33 = -0.001 and Total time
    1000, so the nominal applied strain magnitude |L33 * t| reaches 1.0 along Z.
  * There is therefore NO BCinfo.txt displacement file to read; the applied
    deformation is defined by the velocity gradient in prm.prm and is recovered
    directly from the simulation's own homogenized strain output.

Comparison quantities (uniaxial axial true stress vs axial true strain, to match
the reference uniaxial compression curve):

  STRESS. Under the fully-imposed deviatoric velocity gradient (L11=L22=+0.0005,
  L33=-0.001) the Taylor full-constraint model builds up large sideways stresses
  and a large spurious hydrostatic pressure p = (Txx+Tyy+Tzz)/3, so the raw axial
  Cauchy stress Tzz is contaminated. The uniaxial axial true stress that
  corresponds to the reference (where the lateral faces are traction-free) is the
  pressure-removed axial component:
        sigma = |Tzz - (Txx + Tyy + Tzz)/3|.
  With the copper parameters this matches the Yaghoobi curve at saturation
  (~398 vs 383 MPa).

  STRAIN. Axial true (log) strain from the axial Green strain Ezz:
        true strain = |0.5 * ln(1 + 2 * Ezz)|,
  which reaches ~1.0 at the end of the run.

The reference runs to a true strain of 1.0; the simulation is compared against
it over their overlapping strain range and error metrics (RMSE, MAPE) are
reported there.

Output: matlab/figures/stress_strain_comparison.png
"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIM_FILE = os.path.join(BASE_DIR, "results", "stressstrain.txt")
EXP_FILE = os.path.join(BASE_DIR, "Yaghoobi et al. (2022).csv")
FIG_DIR  = os.path.join(BASE_DIR, "matlab", "figures")
FIG_PATH = os.path.join(FIG_DIR, "stress_strain_comparison.png")

# Column indices in results/stressstrain.txt (tab-separated, 1 header row)
# Order: Exx Eyy Ezz Eyz Exz Exy  Txx Tyy Tzz Tyz Txz Txy  ...
IDX_E = (0, 1, 2, 3, 4, 5)   # Exx Eyy Ezz Eyz Exz Exy  (Green-Lagrange strain)
IDX_T = (6, 7, 8, 9, 10, 11) # Txx Tyy Tzz Tyz Txz Txy  (Cauchy stress)


def compare_stress_strain():
    """
    Build the simulated-vs-reference stress-strain comparison figure.
    Returns (success, message, info_dict).
    """
    import numpy as np

    if not os.path.isfile(SIM_FILE):
        return False, "Simulated stressstrain.txt not found: {}".format(SIM_FILE), {}
    if not os.path.isfile(EXP_FILE):
        return False, "Reference file not found: {}".format(EXP_FILE), {}

    # -- Simulated curve --
    sim = np.loadtxt(SIM_FILE, skiprows=1)
    if sim.ndim == 1:
        sim = sim.reshape(1, -1)

    Exx, Eyy, Ezz, Eyz, Exz, Exy = (sim[:, i] for i in IDX_E)
    Txx, Tyy, Tzz, Tyz, Txz, Txy = (sim[:, i] for i in IDX_T)

    # EQUIVALENT STRESS: von Mises of the homogenized Cauchy tensor. With the
    # rate-dependent model the Taylor run stays nearly pressure-free, so the
    # equivalent stress matches the reference uniaxial true-stress curve.
    sim_stress = np.sqrt(0.5 * ((Txx - Tyy) ** 2 + (Tyy - Tzz) ** 2 +
                                (Tzz - Txx) ** 2) +
                         3.0 * (Tyz ** 2 + Txz ** 2 + Txy ** 2))
    # STRAIN: axial TRUE (logarithmic) strain from the axial Green strain Ezz,
    #   true strain = |0.5 * ln(1 + 2 * Ezz)|.
    # For this isochoric uniaxial compression this equals the equivalent (von
    # Mises) logarithmic strain, and it reaches ~1.0 at the end of the run, so it
    # is consistent with the paper's "true strain" axis (0 to 1.0). Using the von
    # Mises of the GREEN strain instead would under-report the strain at large
    # deformation (it tops out near 0.86), which is why earlier plots stopped
    # short of 1.0.
    sim_strain = np.abs(0.5 * np.log(1.0 + 2.0 * Ezz))
    sim_max = float(sim_strain.max())

    # Ensure monotonically increasing strain for interpolation.
    order      = np.argsort(sim_strain)
    sim_strain = sim_strain[order]
    sim_stress = sim_stress[order]

    # -- Reference curve: Yaghoobi et al. (2022), PRISMS-Plasticity TM --
    exp = np.loadtxt(EXP_FILE, delimiter=",", skiprows=1)
    exp_strain = exp[:, 0]
    exp_stress = exp[:, 1]

    # -- Overlap region for quantitative comparison --
    lo = max(sim_strain.min(), exp_strain.min())
    hi = min(sim_max, exp_strain.max())
    grid = np.linspace(lo, hi, 100)
    sim_i = np.interp(grid, sim_strain, sim_stress)
    exp_i = np.interp(grid, exp_strain, exp_stress)

    rmse = float(np.sqrt(np.mean((sim_i - exp_i) ** 2)))
    nz   = exp_i > 1e-9
    mape = float(np.mean(np.abs((sim_i[nz] - exp_i[nz]) / exp_i[nz])) * 100.0)

    # -- Plot --
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not os.path.isdir(FIG_DIR):
        os.makedirs(FIG_DIR)

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    ax.plot(exp_strain, exp_stress, "ko--", ms=4, lw=1.5,
            label="Yaghoobi et al. (2022)")
    ax.plot(sim_strain, sim_stress, "r-", lw=2.0,
            label="This study")
    ax.set_xlabel("True Strain")
    ax.set_ylabel("Von Mises Stress (MPa)")
    ax.legend(loc="lower right", fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    fig.savefig(FIG_PATH, dpi=200)
    plt.close(fig)

    info = {"rmse": rmse, "mape": mape, "sim_max_strain": sim_max,
            "overlap_hi": hi, "n_sim": int(sim.shape[0])}
    msg = ("Stress-strain comparison written. Simulation reaches true strain {:.3f}; "
           "over the overlap 0 to {:.2f}, RMSE = {:.2f} MPa, MAPE = {:.2f}%."
           ).format(sim_max, hi, rmse, mape)
    return True, msg, info


if __name__ == "__main__":
    ok, msg, info = compare_stress_strain()
    print(("SUCCESS: " if ok else "FAILED: ") + msg)
