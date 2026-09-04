#!/usr/bin/env python3.7
"""
calibrate_react.py — Entry point for the SS316L ReAct Calibration Agent.

The LLM reads the query, selects the correct optimizer from the tool
repository, runs it, and interprets the results. The optimizer handles
all parameter search — no guessing by the LLM.

Available optimizers (specify in your query):
  - Bayesian Optimization       (default)
  - Differential Evolution
  - Nelder-Mead
  - Random Search + Bayesian Optimization

Usage:
  python3.7 calibrate_react.py
  python3.7 calibrate_react.py "Calibrate SS316L using Differential Evolution"
  python3.7 calibrate_react.py "Use Nelder-Mead to calibrate slip parameters"
  python3.7 calibrate_react.py "Apply Random Search then Bayesian Optimization"
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

from agents.react_agent import ReactCalibrationAgent
from tools.sim_tools import reset_counter
import shutil

DEFAULT_QUERY = (
    # "First generate the SS316L microstructure and convert it to PRISMS input, then "
    # "calibrate the crystal plasticity slip parameters for SS316L austenitic stainless steel "
    # "to match the experimental tensile stress-strain data in SS316L_experiment.txt. "
    # "Use Bayesian Optimization. "
    # "Tune: Initial Slip Resistance [100-150 MPa], Initial Hardening Modulus [800-2500 MPa], "
    # "Saturation Stress [350-600 MPa], Power Law Exponent [1-3]. "
    # "Stop when RMSE < 5 MPa or MAPE < 2% or after 60 simulations."
    
    "Generate a random SS316L microstructure for crystal plasticity simulations using PRISMS plasticity. "
    "Then calibrate the crystal plasticity slip parameters for SS316L to match the experimental tensile stress-strain data (SS316L_experiment.txt). "
    "Use Bayesian Optimization. Tune: Initial Slip Resistance [100-150 MPa], Initial Hardening Modulus [800-2500 MPa], Saturation Stress [350-600 MPa], Power Law Exponent [1-3]. "
    "Stop when RMSE < 5 MPa or MAPE < 2% or after 60 simulations."
)


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUERY

    # Clear previous run data so results are always from the current run only
    workdir = os.path.join(_BASE, "workdir")
    if os.path.exists(workdir):
        shutil.rmtree(workdir)
    os.makedirs(workdir)
    os.makedirs(os.path.join(workdir, "curves"))
    os.makedirs(os.path.join(_BASE, "results"), exist_ok=True)

    print("\n" + "=" * 65)
    print("  SS316L ReAct Calibration Agent")
    print("  Model     : GPT-4o")
    print("  Role      : LLM selects optimizer from repository")
    print("  Optimizers: Bayesian | DE | Nelder-Mead | Random+BO")
    print("  Budget    : 60 simulations | RMSE<5 MPa | MAPE<2%")
    print("=" * 65)

    reset_counter()
    agent = ReactCalibrationAgent()
    result = agent.run(query)

    # Auto-generate plots after calibration completes
    plot_script = os.path.join(_BASE, "plot_results.py")
    if os.path.exists(plot_script):
        import subprocess
        print("\n[ReAct] Generating plots...")
        subprocess.run([sys.executable, plot_script], cwd=_BASE)

    return result


if __name__ == "__main__":
    main()
