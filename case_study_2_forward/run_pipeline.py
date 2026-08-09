# -*- coding: utf-8 -*-
"""
run_pipeline.py — Entry point for SS316L_Pure_REACT.

Pure goal-driven ReAct agent: the LLM receives the goal and the tool list
only — no prescribed workflow. It reads tool descriptions, reasons about
what to call and in what order, observes results, and adapts until done.

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
    "Generate a synthetic Cu (copper) polycrystal microstructure with a random texture "
    "(approximately 400 equiaxed grains) and run a single crystal plasticity simulation "
    "under uniaxial COMPRESSION to 40% true strain along Z using PRISMS-Plasticity. Then "
    "perform two comparisons. First, compare the crystallographic texture before and after "
    "deformation by plotting {100}, {110}, and {111} pole figures side by side, that is the "
    "initial random texture against the texture at 40% true strain. Second, compare the simulated "
    "stress-strain response against the experimental tension-converted dataset in "
    "Cu_AnandKothari1996.csv; the simulation is in compression, so convert its response to "
    "the tensile equivalent (take magnitudes) and compare over the overlapping strain range "
    "up to the 40% mark. "
    "Use the Cu material defaults: Initial Slip Resistance=16 MPa, Initial Hardening "
    "Modulus=180 MPa, Saturation Stress=148 MPa, Power Law Exponent=2.25. "
    "Provide a brief physical interpretation of the texture evolution and of the "
    "stress-strain agreement for copper."
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
