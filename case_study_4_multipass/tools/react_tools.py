# -*- coding: utf-8 -*-
"""
react_tools.py  (CS4 — multi-pass HCP Mg texture evolution)

Tool schemas (OpenAI function-calling format) exposed to the ReAct agent, and an
executor. The workflow is a CHAINED multi-pass simulation: the agent runs five
successive plane-strain-compression passes, where each pass's deformed grain
orientations become the next pass's initial texture. After pass 1 it validates
the mechanical response; after pass 5 it analyses the texture evolution and
compares the final texture to the reference simulation (and experiment).

The rate-DEPENDENT PRISMS-Plasticity model (../../main_ratedep) is required for
these HCP magnesium alloys; the rate-independent ../../main gives physically
wrong twinning and stress and must not be used.
"""
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.dirname(_HERE)
sys.path.insert(0, _BASE); sys.path.insert(0, _HERE)

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "run_pass",
        "description": (
            "Run ONE plane-strain-compression Gleeble pass (20% true strain along the "
            "normal direction) with the RATE-DEPENDENT PRISMS-Plasticity Taylor model "
            "(../../main_ratedep). This is a chained, multi-pass workflow: PASS 1 starts "
            "from the random as-cast texture already in this folder; each later pass "
            "AUTOMATICALLY starts from the deformed orientations produced by the previous "
            "pass (the tool saves that pass's texture and prepares the next pass's input). "
            "You must therefore call this tool once per pass, IN ORDER, from pass 1 to "
            "pass 5 (config N_PASSES). It returns the plane-strain flow stress "
            "(sigma_yy - sigma_zz) and the reoriented twin fraction (TwinMade) for the pass. "
            "Do NOT use the rate-independent ../../main binary; it is physically wrong for "
            "these twinning-active HCP alloys."),
        "parameters": {"type": "object", "properties": {
            "pass_number": {"type": "integer",
                "description": "Which pass to run (1..5). Pass N>1 requires pass N-1 to have completed first."}},
            "required": ["pass_number"]}}},

    {"type": "function", "function": {
        "name": "compare_stress_strain",
        "description": (
            "After PASS 1 has completed, compare the simulated single-pass mechanical "
            "response against the reference simulation from the paper. Uses the plane-strain "
            "flow stress sigma_yy - sigma_zz versus TRUE strain (the correct measure for a "
            "velocity-gradient/Taylor BC) and reports RMSE and MAPE over the 0-20% range. "
            "Requires pass 1 to have been run."),
        "parameters": {"type": "object", "properties": {}, "required": []}}},

    {"type": "function", "function": {
        "name": "analyze_texture_evolution",
        "description": (
            "Compute the (0001) basal pole-figure MAXIMUM INTENSITY for every pass completed "
            "so far, and report how the texture strengthens with pass number. Call this after "
            "the passes of interest have been run (typically after all 5). Uses MATLAB/MTEX."),
        "parameters": {"type": "object", "properties": {}, "required": []}}},

    {"type": "function", "function": {
        "name": "compare_final_texture",
        "description": (
            "After all 5 passes, compare the FINAL (pass-5) (0001) texture against the "
            "reference 5-pass SIMULATION and, where available, the EXPERIMENT, and assemble a "
            "side-by-side comparison figure. Reports the max intensities and notes that a "
            "deformation-only model is expected to exceed the experimental intensity because "
            "recrystallization (which weakens texture) is neglected."),
        "parameters": {"type": "object", "properties": {}, "required": []}}},
]


def execute_tool(tool_name, tool_args):
    try:
        if tool_name == "run_pass":
            from sim_tools import run_pass
            ok, msg = run_pass(tool_args.get("pass_number"))
            return ("SUCCESS: " if ok else "FAILED: ") + msg
        elif tool_name == "compare_stress_strain":
            from stress_tools import compare_stress_strain
            ok, msg, _ = compare_stress_strain()
            return ("SUCCESS: " if ok else "FAILED: ") + msg
        elif tool_name == "analyze_texture_evolution":
            from texture_tools import analyze_texture_evolution
            ok, msg, _ = analyze_texture_evolution()
            return ("SUCCESS: " if ok else "FAILED: ") + msg
        elif tool_name == "compare_final_texture":
            from texture_tools import compare_final_texture
            ok, msg, _ = compare_final_texture()
            return ("SUCCESS: " if ok else "FAILED: ") + msg
        else:
            return "ERROR: Unknown tool '%s'." % tool_name
    except Exception as e:
        return "ERROR: Tool '%s' raised an exception: %s" % (tool_name, str(e))
