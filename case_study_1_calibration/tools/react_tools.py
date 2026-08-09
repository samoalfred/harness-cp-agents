# -*- coding: utf-8 -*-
"""
react_tools.py — Tool schemas and dispatcher for the SS316L ReAct calibration agent.

The LLM reads the query, selects the appropriate optimizer tool, runs it,
and observes the result at each iteration. No parameter guessing.

Available tools (specified in the input query):
  1. run_bayesian_optimization       — LHS + GP + Expected Improvement
  2. run_differential_evolution      — population-based global search
  3. run_nelder_mead                 — fast local simplex optimizer
  4. run_random_bo                   — random search then Bayesian Optimization
"""

import os
import sys
import json

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _TOOLS_DIR)

from sim_tools import CalibrationConverged, BEST_FILE
from optimizer_tools import (
    run_bayesian_optimization,
    run_differential_evolution,
    run_nelder_mead,
    run_random_bo,
    TOOL_DESCRIPTIONS,
)

# ── Tool schemas exposed to the LLM ───────────────────────────────

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "generate_microstructure",
            "description": (
                "Run MATLAB to generate the synthetic 3D SS316L polycrystal microstructure "
                "used for the calibration simulations (32x32x32 voxel grid, ~350 grains). "
                "Produces matlab/input_structure_poly.h5. "
                "This must be done before any calibration so the simulations use the "
                "generated microstructure rather than stale input files. "
                "Call this first, then convert_hdf5_to_prisms, then the optimizer."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "convert_hdf5_to_prisms",
            "description": (
                "Convert the generated HDF5 microstructure into PRISMS-Plasticity input "
                "format. Writes grainID.txt and orientations.txt and updates prm.prm with "
                "the correct voxel dimensions. Call after generate_microstructure and "
                "before running any optimizer."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_bayesian_optimization",
            "description": (
                "Run Bayesian Optimization (Latin Hypercube Sampling + Gaussian Process "
                "+ Expected Improvement) to calibrate SS316L slip parameters. "
                "Best choice for expensive simulations with a limited budget. "
                "Most sample-efficient algorithm. Recommended for calibration problems."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "n_initial": {
                        "type": "integer",
                        "description": "Number of initial LHS exploration points before GP+EI kicks in. Default: 10.",
                    },
                    "seed": {
                        "type": "integer",
                        "description": "Random seed for reproducibility. Default: 42.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_differential_evolution",
            "description": (
                "Run Differential Evolution to calibrate SS316L slip parameters. "
                "Population-based global search. Good for avoiding local minima. "
                "Needs more evaluations than Bayesian but explores the space broadly."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "popsize": {
                        "type": "integer",
                        "description": "Population size multiplier. Default: 3.",
                    },
                    "seed": {
                        "type": "integer",
                        "description": "Random seed for reproducibility. Default: 42.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_nelder_mead",
            "description": (
                "Run Nelder-Mead Simplex to calibrate SS316L slip parameters. "
                "Fast local optimizer. Best when starting near a good region. "
                "May get stuck in local minima — not ideal for broad exploration."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "seed": {
                        "type": "integer",
                        "description": "Random seed for reproducibility. Default: 42.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_random_bo",
            "description": (
                "Run Random Search followed by Bayesian Optimization to calibrate "
                "SS316L slip parameters. Phase 1: random exploration. "
                "Phase 2: GP+EI exploitation. Simple baseline with BO refinement."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "n_random": {
                        "type": "integer",
                        "description": "Number of random evaluations before switching to BO. Default: 15.",
                    },
                    "seed": {
                        "type": "integer",
                        "description": "Random seed for reproducibility. Default: 42.",
                    },
                },
                "required": [],
            },
        },
    },
]

# ── Tool registry ──────────────────────────────────────────────────

_REGISTRY = {
    "run_bayesian_optimization":  run_bayesian_optimization,
    "run_differential_evolution": run_differential_evolution,
    "run_nelder_mead":            run_nelder_mead,
    "run_random_bo":              run_random_bo,
}


def _load_best():
    if os.path.exists(BEST_FILE):
        with open(BEST_FILE) as f:
            return json.load(f)
    return None


def execute_tool(tool_name, args):
    """
    Dispatch a tool call from the ReAct agent and return an observation string.
    """
    # ── Microstructure generation tools (run once, before calibration) ──
    if tool_name == "generate_microstructure":
        try:
            from matlab_runner import run_microstructure_gen
            ok, msg = run_microstructure_gen()
        except Exception as e:
            return "FAILED: generate_microstructure error — {}.".format(str(e))
        return "SUCCESS: {}".format(msg) if ok else "FAILED: {}".format(msg)

    if tool_name == "convert_hdf5_to_prisms":
        try:
            from h5_converter import convert_h5_to_prisms
            ok, msg, info = convert_h5_to_prisms()
        except Exception as e:
            return "FAILED: convert_hdf5_to_prisms error — {}.".format(str(e))
        if ok:
            return ("SUCCESS: {} | Grid: {}x{}x{}, {} grains. "
                    "grainID.txt and orientations.txt written; prm.prm updated.").format(
                msg, info.get("Nx"), info.get("Ny"),
                info.get("Nz"), info.get("N_grains"))
        return "FAILED: {}".format(msg)

    if tool_name not in _REGISTRY:
        return "ERROR: Unknown tool '{}'. Available: {}.".format(
            tool_name, ", ".join(_REGISTRY.keys()))

    fn = _REGISTRY[tool_name]

    # Filter args to only those accepted by the function
    import inspect
    valid_keys = set(inspect.signature(fn).parameters.keys())
    filtered = {k: v for k, v in args.items() if k in valid_keys}

    print("\n[Tool] Calling {}({})".format(tool_name, filtered))

    try:
        result = fn(**filtered)
    except CalibrationConverged as e:
        result = {}
        print("[Tool] CalibrationConverged: {}".format(e))
    except Exception as e:
        return "FAILED: {} error — {}.".format(tool_name, str(e))

    best = _load_best()
    if best:
        return (
            "COMPLETE: {} finished. "
            "Best parameters — s0={:.4f} MPa, h0={:.4f} MPa, ss={:.4f} MPa, n={:.4f}. "
            "RMSE={:.4f} MPa, MAPE={:.3f}%. "
            "Algorithm: {}. "
            "Please provide your physical interpretation of these results."
        ).format(
            tool_name,
            best.get("s0", 0), best.get("h0", 0),
            best.get("ss", 0), best.get("n", 0),
            best.get("rmse", 0), best.get("mape") or 0.0,
            result.get("algorithm", tool_name),
        )

    return "COMPLETE: {} finished. Result: {}.".format(tool_name, result)
