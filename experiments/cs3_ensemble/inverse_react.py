#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-
"""
inverse_react.py -- entry point for the Case Study 3 inverse-texture agent.

The LLM selects a search strategy from the optimizer repository and launches it;
the optimizer recovers the initial texture that reproduces the target Fig. 2c
compression texture. Mirrors the Case Study 1 calibration entry point.

Usage:
  python3.7 inverse_react.py
  python3.7 inverse_react.py "Recover the initial texture using random search"
"""
import os
import sys

_BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BASE)
sys.path.insert(0, os.path.join(_BASE, "agents"))
sys.path.insert(0, os.path.join(_BASE, "tools"))

if not os.environ.get("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY not set.")
    print("  Run: export OPENAI_API_KEY='sk-...'")
    sys.exit(1)

from agents.inverse_agent import InverseTextureAgent

DEFAULT_QUERY = (
    "Recover the initial crystallographic texture of the copper polycrystal that, "
    "after uniaxial compression along Z to true strain ~1.0, reproduces the target "
    "deformation texture in fig2c_targets.json (the {111}, {100}, {110} pole figures "
    "with a central {110} compression fibre). Select the most sample-efficient search "
    "strategy and use a budget of 15 simulations. Then interpret the recovered "
    "initial texture."
)


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUERY

    print("\n" + "=" * 65)
    print("  Cu Inverse-Texture Agent (Case Study 3)")
    print("  Model     : GPT-4o")
    print("  Role      : LLM selects the search strategy; optimizer searches")
    print("  Target    : Fig. 2c compression texture (fig2c_targets.json)")
    print("  Budget    : 15 simulations | rate-dependent Taylor (m=77)")
    print("=" * 65)

    agent = InverseTextureAgent()
    return agent.run(query)


if __name__ == "__main__":
    main()
