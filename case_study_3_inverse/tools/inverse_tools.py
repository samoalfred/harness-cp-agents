# -*- coding: utf-8 -*-
"""
inverse_tools.py -- tool schemas and dispatcher for the Case Study 3
inverse-texture agent. The LLM selects a search strategy from the repository,
runs it, and interprets the recovered initial texture. The optimizer performs
the entire search; the agent does not propose textures itself.
"""
import os
import sys

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.dirname(_TOOLS_DIR)
sys.path.insert(0, _BASE)
sys.path.insert(0, _TOOLS_DIR)

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "run_bayesian_texture_inverse",
            "description": (
                "Recover the initial crystallographic texture that reproduces the "
                "target Fig. 10 deformation texture, using Bayesian optimization "
                "(Gaussian process + expected improvement) over the initial-texture "
                "design variables: texture mode {random, fiber[100], fiber[110], "
                "fiber[111]} and fibre spread sigma. Most sample-efficient; the "
                "recommended choice for this expensive forward model. Each evaluation "
                "runs a full crystal plasticity simulation and scores the deformed "
                "texture against fig10_targets.json."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "n_evaluations": {
                        "type": "integer",
                        "description": "Simulation budget (number of forward evaluations). Default: 15.",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_random_texture_inverse",
            "description": (
                "Recover the initial texture using random search over the same "
                "design space as a baseline. Simpler but less sample-efficient than "
                "Bayesian optimization; use only if a naive baseline is requested."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "n_evaluations": {
                        "type": "integer",
                        "description": "Simulation budget. Default: 15.",
                    }
                },
                "required": [],
            },
        },
    },
]

_METHOD = {
    "run_bayesian_texture_inverse": "bayesian",
    "run_random_texture_inverse":   "random",
}


def execute_tool(tool_name, args):
    if tool_name not in _METHOD:
        return "ERROR: Unknown tool '{}'. Available: {}.".format(
            tool_name, ", ".join(_METHOD.keys()))
    budget = int(args.get("n_evaluations", 15))
    try:
        from inverse_search import run_search
        res = run_search(_METHOD[tool_name], budget)
    except Exception as e:
        return "FAILED: {} error -- {}.".format(tool_name, str(e))

    b = res["best"]
    recovered_random = (b["mode"] == "random") or (b["mode"] != "random" and b["sigma"] >= 70.0)
    note = ("The recovered initial texture is effectively random (a diffuse/isotropic "
            "orientation distribution)." if recovered_random else
            "The recovered initial texture is a fibre component; inspect the log to "
            "judge whether this is physically meaningful.")
    return (
        "COMPLETE: {} finished after {} evaluations. "
        "Best initial texture -- mode={}, fiber={}, sigma={:.1f} deg, texture-match loss={:.3f}. "
        "{} Log: {}. "
        "Please provide a physical interpretation of the recovered initial texture "
        "in relation to the target Fig. 10 compression texture."
    ).format(tool_name, res["n_evals"], b["mode"], b["fiber"], b["sigma"], b["loss"],
             note, res["log"])
