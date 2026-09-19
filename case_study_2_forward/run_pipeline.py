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
    "Perform a forward validation of polycrystalline OFHC copper using the rate-dependent "
    "Taylor crystal-plasticity model. First generate a synthetic copper polycrystal of "
    "approximately 400 equiaxed grains with a random initial texture, then run a single "
    "simulation of uniaxial compression along Z through an imposed velocity gradient to a "
    "true strain of about 1.0 (100% compression), using the fixed slip parameters in "
    "prm.prm. Then perform two comparisons. First, the crystallographic texture: plot the "
    "{111}, {100}, and {110} pole figures (Z at centre) on a fixed 0-3.5 MRD scale, "
    "producing both the pre- versus post-deformation figure and an aligned comparison of "
    "the post-deformation pole figures against the reference pole figures; the deformed "
    "texture should reproduce the <110> compression fiber. Second, compare the simulated "
    "von Mises equivalent stress against the reference stress-strain curve over the "
    "overlapping strain range, reporting RMSE and MAPE. Provide a brief physical "
    "interpretation of the texture evolution (the development of the <110> compression "
    "fiber) and of the stress-strain agreement for copper."
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
