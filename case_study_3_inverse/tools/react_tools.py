# -*- coding: utf-8 -*-
"""
react_tools.py

Defines the tool schemas (OpenAI function-calling format) exposed to the
ReAct agent, and an executor that runs whichever tool the LLM selects.

The LLM sees each tool's name, description, and parameter schema.
It decides which tool to call, in what order, and with what arguments.
The executor runs the tool and returns an observation string that is fed
back into the conversation so the LLM can reason about what to do next.
"""

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.dirname(_HERE)
sys.path.insert(0, _BASE)
sys.path.insert(0, _HERE)

# ── Tool schemas (OpenAI function-calling format) ──────────────────────────

TOOL_SCHEMAS = [

    {
        "type": "function",
        "function": {
            "name": "inject_simulation_parameters",
            "description": (
                "Configure the simulation by writing parameters directly into "
                "microstructure_gen.m (texture type, fiber direction, spread) and "
                "prm.prm (slip parameters for all 12 FCC slip systems). "
                "Always call this first so the simulation reflects the user's request. "
                "IMPORTANT: only set a parameter to a non-default value if the user "
                "explicitly specified it. Use the stated defaults for everything else."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "orientation_type": {
                        "type": "string",
                        "enum": ["textured", "random"],
                        "description": "Grain orientation distribution type. Default: 'random' (this investigation targets the Fig. 10 deformation texture, which develops from a random initial texture). Only use 'textured' if the user explicitly requests a fiber texture."
                    },
                    "fiber_direction": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Miller indices of fiber axis, used only when orientation_type is 'textured'. Ignored for random texture. Default: [1,0,1]."
                    },
                    "sigma_spread": {
                        "type": "number",
                        "description": "Angular scatter around fiber axis in degrees, used only when orientation_type is 'textured'. Ignored for random texture. Default: 15.0. Only change if the user explicitly requests a different value."
                    },
                    "s0": {
                        "type": "number",
                        "description": "Initial Slip Resistance in MPa. Default: 16.0 (Cu). Only change if the user explicitly specifies it."
                    },
                    "h0": {
                        "type": "number",
                        "description": "Initial Hardening Modulus in MPa. Default: 180.0 (Cu). Only change if the user explicitly specifies it."
                    },
                    "ss": {
                        "type": "number",
                        "description": "Saturation Stress in MPa (slip resistance at hardening saturation). Default: 148.0 (Cu). Only change if the user explicitly specifies it."
                    },
                    "n": {
                        "type": "number",
                        "description": "Power Law Exponent (hardening exponent a, dimensionless). Default: 2.25 (Cu). Only change if the user explicitly specifies it."
                    }
                },
                "required": ["orientation_type", "fiber_direction", "sigma_spread",
                             "s0", "h0", "ss", "n"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "generate_microstructure",
            "description": (
                "Run MATLAB to generate a synthetic 3D Cu polycrystal microstructure "
                "(64x64x64 voxels, ~400 equiaxed grains, random texture). Produces "
                "input_structure_poly.h5, pre-deformation pole figures, and "
                "output_summary.txt. Call inject_simulation_parameters before this."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "convert_hdf5_to_prisms",
            "description": (
                "Convert the HDF5 microstructure file to PRISMS-Plasticity input format. "
                "Writes grainID.txt and orientations.txt, and updates prm.prm with the "
                "correct voxel dimensions. Call after generate_microstructure."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "run_simulation",
            "description": (
                "Run a single PRISMS-Plasticity crystal plasticity FEM simulation "
                "under uniaxial COMPRESSION to 40% true strain along Z (engineering "
                "displacement -0.3297, set in BCinfo.txt) using the current prm.prm "
                "settings. Produces QuadratureOutputsXXX.csv files and "
                "results/stressstrain.txt. Call after convert_hdf5_to_prisms."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "extract_post_orientations",
            "description": (
                "Find the last QuadratureOutputsXXX.csv in results/, extract columns 8-10 "
                "(post-deformation Rodrigues vectors rx, ry, rz), and save to "
                "matlab/orientations_post_deformation.csv. Call after run_simulation."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "generate_pole_figures",
            "description": (
                "Run MATLAB oriplot_big.m to compute pre- and post-deformation ODFs "
                "and generate {100}, {110}, {111} pole figures with matched color scales. "
                "Saves 6 PNG files. Call after extract_post_orientations."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "create_comparison_figure",
            "description": (
                "Assemble a publication-quality 3x2 side-by-side comparison figure "
                "(Pre | Post for each of {100}, {110}, {111}) saved as "
                "matlab/figures/texture_comparison.png at 300 DPI. This compares the "
                "initial random texture with the texture after 40% compression. "
                "Call after generate_pole_figures."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "compare_stress_strain",
            "description": (
                "Compare the simulated stress-strain response against the experimental "
                "tension-converted Cu dataset (Cu_AnandKothari1996.csv). Reads the axial "
                "components from results/stressstrain.txt, converts the compressive "
                "response to its tensile equivalent by taking magnitudes, overlays it on "
                "the experiment, and computes RMSE and MAPE over the overlapping strain "
                "range (0 to ~0.4). Saves matlab/figures/stress_strain_comparison.png. "
                "Call after run_simulation."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
]


# ── Tool executor ──────────────────────────────────────────────────────────

def execute_tool(tool_name, tool_args):
    """
    Execute a tool by name with the given arguments dict.
    Returns an observation string that is fed back to the LLM.
    """

    try:
        if tool_name == "inject_simulation_parameters":
            return _inject_params(tool_args)

        elif tool_name == "generate_microstructure":
            from matlab_runner import run_microstructure_gen
            ok, msg = run_microstructure_gen()
            return "SUCCESS: {}".format(msg) if ok else "FAILED: {}".format(msg)

        elif tool_name == "convert_hdf5_to_prisms":
            from h5_converter import convert_h5_to_prisms
            ok, msg, info = convert_h5_to_prisms()
            if ok:
                return ("SUCCESS: {} | Grid: {}x{}x{}, {} grains.").format(
                    msg, info.get("Nx"), info.get("Ny"),
                    info.get("Nz"), info.get("N_grains"))
            return "FAILED: {}".format(msg)

        elif tool_name == "run_simulation":
            from single_sim import run_single_simulation
            ok, msg = run_single_simulation()
            return "SUCCESS: {}".format(msg) if ok else "FAILED: {}".format(msg)

        elif tool_name == "extract_post_orientations":
            from texture_analysis import find_last_quadrature_csv, extract_orientations
            result = find_last_quadrature_csv()
            if result is None:
                return "FAILED: No QuadratureOutputs CSV found in results/."
            csv_path, csv_name = result
            ok, msg, _ = extract_orientations(csv_path)
            if ok:
                return "SUCCESS: {} (source: {})".format(msg, csv_name)
            return "FAILED: {}".format(msg)

        elif tool_name == "generate_pole_figures":
            from texture_analysis import run_oriplot
            ok, msg = run_oriplot()
            return "SUCCESS: {}".format(msg) if ok else "FAILED: {}".format(msg)

        elif tool_name == "create_comparison_figure":
            from texture_compare import create_comparison
            ok, msg, path = create_comparison()
            if ok:
                return "SUCCESS: {}. Saved to: {}".format(msg, path)
            return "FAILED: {}".format(msg)

        elif tool_name == "compare_stress_strain":
            from stress_strain_compare import compare_stress_strain
            ok, msg, info = compare_stress_strain()
            return "SUCCESS: {}".format(msg) if ok else "FAILED: {}".format(msg)

        else:
            return "ERROR: Unknown tool '{}'.".format(tool_name)

    except Exception as e:
        return "ERROR: Tool '{}' raised an exception: {}".format(tool_name, str(e))


def _inject_params(args):
    from param_injector import inject_all
    params = {
        "orientation_type": args.get("orientation_type", "random"),
        "fiber_direction":  args.get("fiber_direction", [1, 0, 1]),
        "sigma_spread":     float(args.get("sigma_spread", 15.0)),
        "s0":               float(args.get("s0", 16.0)),
        "h0":               float(args.get("h0", 180.0)),
        "ss":               float(args.get("ss", 148.0)),
        "n":                float(args.get("n", 2.25)),
    }
    ok, msg = inject_all(params)
    if ok:
        fd = params["fiber_direction"]
        return (
            "SUCCESS: Config files updated. "
            "orientation_type={}, fiber_direction=[{} {} {}], sigma_spread={}°, "
            "s0={} MPa, h0={} MPa, ss={} MPa, n={}"
        ).format(params["orientation_type"], fd[0], fd[1], fd[2],
                 params["sigma_spread"], params["s0"], params["h0"],
                 params["ss"], params["n"])
    return "FAILED: {}".format(msg)
