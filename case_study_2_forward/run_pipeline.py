# -*- coding: utf-8 -*-
"""
run_pipeline.py — Entry point for CS2_Texture_Evolution.

Pure goal-driven ReAct agent: the LLM receives the goal and the tool list
only — no prescribed workflow. It reads tool descriptions, reasons about
what to call and in what order, observes results, and adapts until done.

Reproduces the OFHC-copper compression benchmark of Yaghoobi et al. (2022)
with PRISMS-Plasticity TM (rate-independent, Taylor model, velocity-gradient
BC). The microstructure and prm.prm are already configured in this folder.

Usage:
    python3.7 run_pipeline.py                         # full run
    python3.7 run_pipeline.py --query "custom query"  # custom query
"""

import os
import sys
import argparse

if not os.environ.get("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY is not set.")
    print("  Run: export OPENAI_API_KEY='sk-...'")
    sys.exit(1)

from agents.react_agent import ReactAgent

DEFAULT_QUERY = (
    "Reproduce Application 1 (polycrystalline OFHC copper, uniaxial compression) of "
    "Yaghoobi et al. (2022), PRISMS-Plasticity TM, as a forward validation of the copper "
    "already configured in this folder. The model is a RATE-DEPENDENT crystal plasticity "
    "formulation with isotropic hardening (gamma_dot0 = 1e-3, rate sensitivity m = 77, no "
    "twinning, no back stress), homogenized with the Taylor model. Loading is uniaxial "
    "COMPRESSION along Z through an imposed velocity gradient L = diag(0.0005, 0.0005, "
    "-0.001), with true strain accumulating linearly to 1.0 (the paper's 99% compression); "
    "the texture snapshot at t = 990 is the -99% state. The microstructure (about 400 "
    "grains) and the prm.prm input (including the fixed slip parameters) are already in "
    "place, so do not regenerate the microstructure, convert it, or change any parameters; "
    "run the simulation exactly as configured. "
    "Then perform two comparisons. First, the crystallographic texture: plot {111}, {100}, "
    "and {110} pole figures (Z at centre) on the fixed 0-3.5 MRD scale, producing both the "
    "pre-vs-post evolution figure and an aligned comparison of this simulation's "
    "post-deformation pole figures against the reference paper Fig. 2c "
    "(Reference_Plot_figures.png); the deformed texture should reproduce the <110> "
    "compression fibre. "
    "Second, compare the simulated EQUIVALENT (von Mises) stress versus EQUIVALENT strain "
    "against the digitized PRISMS-Plasticity TM reference curve of Yaghoobi et al. (2022) in "
    "'Yaghoobi et al. (2022).csv', reporting RMSE and MAPE over the overlapping strain range. "
    "Provide a brief physical interpretation of the texture evolution (the development of the "
    "<110> compression fibre) and of the stress-strain agreement for copper."
)


def main():
    parser = argparse.ArgumentParser(
        description="SS316L Crystal Plasticity — Pure ReAct Pipeline"
    )
    parser.add_argument(
        "--query", type=str, default=None,
        help="Custom natural language query (default: [101] fiber texture, standard params)"
    )
    args = parser.parse_args()

    query = args.query if args.query else DEFAULT_QUERY

    agent = ReactAgent()
    agent.run(query)
    return 0


if __name__ == "__main__":
    sys.exit(main())
