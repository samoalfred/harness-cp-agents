#!/usr/bin/env python3.7
"""
System 3 — Semi-Autonomous LLM Calibration Agent
==================================================
The optimization algorithm is provided as a pre-built tool.
The LLM selects the algorithm, runs it, and interprets results.

Available algorithms (specify in your query):
  - Bayesian Optimization
  - Differential Evolution
  - Nelder-Mead
  - Random Search + Bayesian Optimization

Usage
-----
  python3.7 calibrate_semi.py
  python3.7 calibrate_semi.py "Calibrate SS316L using Bayesian Optimization"
  python3.7 calibrate_semi.py "Use Differential Evolution to calibrate..."
  python3.7 calibrate_semi.py "Apply Nelder-Mead to find best parameters..."
  python3.7 calibrate_semi.py "Use Random Search then BO for calibration..."
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

from agents.supervisor import SupervisorAgent
from tools.sim_tools import reset_counter

DEFAULT_QUERY = (
    "Calibrate the crystal plasticity slip parameters for SS316L austenitic "
    "tensile stress-strain data in SS316L_experiment.txt. "
    "Tune: Initial Slip Resistance [100-150 MPa], "
    "Initial Hardening Modulus [800-2500 MPa], "
    "Saturation Stress [350-600 MPa], Power Law Exponent [1-3]. "
    "Stop when RMSE < 5 MPa or MAPE < 2% or after 60 simulations."
)


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUERY

    os.makedirs(os.path.join(_BASE, "workdir"), exist_ok=True)
    os.makedirs(os.path.join(_BASE, "results"), exist_ok=True)

    print("\n" + "=" * 65)
    print("  System 3 — Semi-Autonomous LLM Calibration Agent")
    print("  Model     : GPT-4o")
    print("  Role      : LLM selects algorithm | Python runs it")
    print("  Algorithms: Bayesian | DE | Nelder-Mead | Random+BO")
    print("=" * 65)

    reset_counter()
    supervisor = SupervisorAgent()
    result, interpretation = supervisor.run(query)

    # Auto-generate plots
    plot_script = os.path.join(_BASE, "plot_results.py")
    if os.path.exists(plot_script):
        import subprocess
        print("\n[System 3] Generating plots...")
        subprocess.run([sys.executable, plot_script], cwd=_BASE)

    return result


if __name__ == "__main__":
    main()
