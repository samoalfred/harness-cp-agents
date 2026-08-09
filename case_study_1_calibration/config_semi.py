"""
Configuration for SS316L System 3 (Semi-Autonomous LLM Agent).
"""

import os

BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
PRM_FILE         = os.path.join(BASE_DIR, "prm.prm")
EXP_DATA_FILE    = os.path.join(BASE_DIR, "SS316L_experiment.txt")
SIM_RESULTS_FILE = os.path.join(BASE_DIR, "results", "stressstrain.txt")
WORKDIR          = os.path.join(BASE_DIR, "workdir")
LOG_FILE         = os.path.join(WORKDIR, "optimization_results.csv")
BEST_FILE        = os.path.join(WORKDIR, "best_params.json")
CURVES_DIR       = os.path.join(WORKDIR, "curves")

SIM_COMMAND      = "../../main prm.prm"
N_SLIP_SYSTEMS   = 12
REFINE_FACTOR    = 2
SIM_TIMEOUT_SEC  = 7200

# OpenAI settings
OPENAI_MODEL     = "gpt-4o"
TEMPERATURE      = 0.0
MAX_TOKENS       = 1024

# Wider bounds for SS316L
PARAMETERS = [
    ("Initial Slip Resistance",   "Initial Slip Resistance",   100.0, 150.0,  "MPa"),
    ("Initial Hardening Modulus", "Initial Hardening Modulus", 800.0, 2500.0, "MPa"),
    ("Saturation Stress",         "Saturation Stress",         350.0, 600.0,  "MPa"),
    ("Power Law Exponent",        "Power Law Exponent",        1.0,   3.0,    "dimensionless"),
]

# Hard stopping criteria
MAX_EVALUATIONS = 60
RMSE_THRESHOLD  = 5.0   # MPa
MAPE_THRESHOLD  = 2.0   # %

# Available optimization algorithms
AVAILABLE_ALGORITHMS = [
    "bayesian",             # LHS + Gaussian Process + Expected Improvement
    "differential_evolution",  # Differential Evolution (scipy)
    "nelder_mead",          # Nelder-Mead Simplex
    "random_bo",            # Random Search then Bayesian Optimization
]
