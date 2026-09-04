# -*- coding: utf-8 -*-
"""
tool_schemas_ablated.py  --  ABLATED condition.

Identical tool NAMES and PARAMETER SCHEMAS to tool_schemas_full.py, but every
prerequisite / ordering / output-chaining clause is removed from the
descriptions. Specifically stripped:
  - explicit ordering directives ("This is the first tool to call",
    "Call after run_simulation", "Call after extract_post_orientations",
    "Call after generate_pole_figures", "Only needed after
    generate_microstructure");
  - input-file dependency phrases that reveal order (which file each tool
    READS, e.g. "the post-deformation texture is read from
    orientations_post_deformation.csv");
  - the "NOT REQUIRED / already configured / should NOT call" scoping that
    tells the agent which tools to skip.
Each description is reduced to a self-contained statement of WHAT the tool
does, plus the (unchanged) parameter schema. The physics wording is kept so
that only the sequencing information is removed.
"""

TOOL_SCHEMAS = [

    {
        "type": "function",
        "function": {
            "name": "inject_simulation_parameters",
            "description": (
                "Overwrites the crystal-plasticity slip parameters (s0, h0, ss, "
                "n) in the PRISMS input file and the texture settings in the "
                "microstructure generation script."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "orientation_type": {
                        "type": "string",
                        "enum": ["textured", "random"],
                        "description": "Grain orientation distribution type. Default: 'random'."
                    },
                    "fiber_direction": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Miller indices of fiber axis, used only when orientation_type is 'textured'. Default: [1,0,1]."
                    },
                    "sigma_spread": {
                        "type": "number",
                        "description": "Angular scatter around fiber axis in degrees (textured only). Default: 15.0."
                    },
                    "s0": {"type": "number", "description": "Initial Slip Resistance in MPa. Default: 16.0."},
                    "h0": {"type": "number", "description": "Initial Hardening Modulus in MPa. Default: 200.0."},
                    "ss": {"type": "number", "description": "Saturation Stress in MPa. Default: 129.5."},
                    "n":  {"type": "number", "description": "Power Law Exponent (dimensionless). Default: 2.0."}
                },
                "required": ["orientation_type", "fiber_direction", "sigma_spread", "s0", "h0", "ss", "n"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "generate_microstructure",
            "description": (
                "Runs MATLAB to generate a synthetic Cu polycrystal "
                "microstructure (grain ID map and per-grain Rodrigues "
                "orientations)."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },

    {
        "type": "function",
        "function": {
            "name": "convert_hdf5_to_prisms",
            "description": (
                "Converts an HDF5 microstructure to PRISMS input files "
                "(grainID.txt, orientations.txt) and sets the voxel grid "
                "dimensions."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },

    {
        "type": "function",
        "function": {
            "name": "run_simulation",
            "description": (
                "Run a single PRISMS-Plasticity TM crystal-plasticity simulation "
                "(via the rate-dependent binary ../../main_ratedep). The model is "
                "RATE-DEPENDENT with isotropic hardening (gamma_dot0 = 1e-3, "
                "m = 77) and uses the TAYLOR homogenization scheme. Loading is "
                "uniaxial COMPRESSION along Z through a VELOCITY GRADIENT boundary "
                "condition (L = diag(0.0005, 0.0005, -0.001)), true strain "
                "reaching 1.0. Runtime is ~15 min single-core."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },

    {
        "type": "function",
        "function": {
            "name": "extract_post_orientations",
            "description": (
                "Extract the post-deformation Rodrigues vector components "
                "(rx, ry, rz) of the deformed lattice orientations from the "
                "PRISMS quadrature output."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },

    {
        "type": "function",
        "function": {
            "name": "generate_pole_figures",
            "description": (
                "Run MATLAB oriplot_big.m to compute orientation distribution "
                "functions and generate {100}, {110}, {111} pole figures on the "
                "fixed 0-3.5 MRD scale."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },

    {
        "type": "function",
        "function": {
            "name": "create_comparison_figure",
            "description": (
                "Assemble the texture comparison figures on the fixed 0-3.5 MRD "
                "scale: a pre-versus-post pole-figure evolution figure, and an "
                "aligned comparison of this simulation's post-deformation pole "
                "figures against the reference paper Fig. 2c."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },

    {
        "type": "function",
        "function": {
            "name": "compare_stress_strain",
            "description": (
                "Compare the simulated EQUIVALENT (von Mises) stress versus "
                "EQUIVALENT strain against the digitized PRISMS-Plasticity TM "
                "reference curve of Yaghoobi et al. (2022), and compute RMSE and "
                "MAPE over the overlapping strain range."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
]
