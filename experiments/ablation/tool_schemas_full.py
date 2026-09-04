# -*- coding: utf-8 -*-
"""
tool_schemas_full.py  --  FULL condition.

Tool descriptions copied VERBATIM from the CS2_Texture_Evolution harness
(tools/react_tools.py). Each description embeds the tool's prerequisites and
outputs ("first tool to call", "Call after ...", the input file it reads),
which is the information the paper claims drives autonomous sequencing.

This file is the control. tool_schemas_ablated.py is identical except the
prerequisite/ordering clauses are removed.
"""

TOOL_SCHEMAS = [

    {
        "type": "function",
        "function": {
            "name": "inject_simulation_parameters",
            "description": (
                "OPTIONAL / NOT REQUIRED FOR THIS STUDY. Overwrites the slip "
                "parameters in prm.prm and the texture settings in "
                "microstructure_gen.m. The prm.prm and microstructure in this "
                "folder are ALREADY configured to reproduce Yaghoobi et al. "
                "(2022) (rate-independent Taylor model, velocity-gradient BC, "
                "Cu slip parameters), so you normally should NOT call this. "
                "Only call it if the user explicitly asks to change a slip "
                "parameter; otherwise leave prm.prm untouched. Defaults below "
                "match the values already in prm.prm."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "orientation_type": {
                        "type": "string",
                        "enum": ["textured", "random"],
                        "description": "Grain orientation distribution type. Default: 'random'. Only relevant if regenerating the microstructure (not required here)."
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
                    "s0": {"type": "number", "description": "Initial Slip Resistance in MPa. Default: 16.0 (Cu, already in prm.prm)."},
                    "h0": {"type": "number", "description": "Initial Hardening Modulus in MPa. Default: 200.0 (already in prm.prm)."},
                    "ss": {"type": "number", "description": "Saturation Stress in MPa. Default: 129.5 (already in prm.prm)."},
                    "n":  {"type": "number", "description": "Power Law Exponent (dimensionless). Default: 2.0 (already in prm.prm)."}
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
                "OPTIONAL / NOT REQUIRED FOR THIS STUDY. Runs MATLAB to generate "
                "a NEW synthetic Cu polycrystal microstructure. This folder "
                "already contains a pre-generated ~400-grain microstructure "
                "(GrainId.txt + orientations_FCC_400grains.txt), so you should "
                "NOT call this unless the user explicitly asks to generate a new "
                "microstructure. Using the existing microstructure is the "
                "intended path for this study."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },

    {
        "type": "function",
        "function": {
            "name": "convert_hdf5_to_prisms",
            "description": (
                "OPTIONAL / NOT REQUIRED FOR THIS STUDY. Converts a freshly "
                "generated HDF5 microstructure to PRISMS input (grainID.txt, "
                "orientations.txt) and updates prm.prm voxel dimensions. Only "
                "needed after generate_microstructure. The PRISMS input files "
                "are already present, so skip this unless a new microstructure "
                "was just generated."
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
                "with the current prm.prm (via the rate-dependent binary "
                "../../main_ratedep). The model is RATE-DEPENDENT with isotropic "
                "hardening (gamma_dot0 = 1e-3, m = 77) and uses the TAYLOR "
                "homogenization scheme (Flag To Use Taylor Model = true). Loading "
                "is uniaxial COMPRESSION along Z through a VELOCITY GRADIENT "
                "boundary condition (L = diag(0.0005, 0.0005, -0.001), Total time "
                "1000), true strain reaching 1.0 (texture snapshot at t = 990 = "
                "-99%). Produces QuadratureOutputsXXX.csv and "
                "results/stressstrain.txt. This is the first tool to call for this "
                "study (microstructure and prm.prm are already configured). "
                "Runtime is ~15 min single-core."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },

    {
        "type": "function",
        "function": {
            "name": "extract_post_orientations",
            "description": (
                "Find the last QuadratureOutputsXXX.csv in results/, extract "
                "columns 8-10 (post-deformation Rodrigues vectors rx, ry, rz), "
                "and save to matlab/orientations_post_deformation.csv. Call after "
                "run_simulation."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },

    {
        "type": "function",
        "function": {
            "name": "generate_pole_figures",
            "description": (
                "Run MATLAB oriplot_big.m to compute pre- and post-deformation "
                "ODFs and generate {100}, {110}, {111} pole figures on the fixed "
                "0-3.5 MRD scale (matching the paper). The pre-deformation texture "
                "is read from the existing orientations.txt (the initial "
                "~400-grain texture); the post-deformation texture is read from "
                "orientations_post_deformation.csv. Saves the 6 pre/post PNGs plus "
                "the three post-deformation tiles (tile_mine_111/100/110.png) used "
                "for the paper comparison. Call after extract_post_orientations."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },

    {
        "type": "function",
        "function": {
            "name": "create_comparison_figure",
            "description": (
                "Assemble the texture comparison figures, all on the fixed "
                "0-3.5 MRD scale (matching the paper). Produces TWO outputs: "
                "(1) matlab/figures/texture_comparison.png -- the pre vs post "
                "pole figures ({100},{110},{111}), showing the texture evolution; "
                "and (2) matlab/figures/texture_vs_paper.png -- the aligned "
                "comparison of THIS simulation's post-deformation pole figures "
                "(top row) against the reference paper Fig. 2c "
                "(Reference_Plot_figures.png, bottom row), {111}/{100}/{110} "
                "columns aligned on a shared colorbar. Call after "
                "generate_pole_figures."
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
                "reference curve of Yaghoobi et al. (2022) in 'Yaghoobi et al. "
                "(2022).csv'. Reads the homogenized stress and strain tensors from "
                "results/stressstrain.txt, forms the von Mises equivalent stress "
                "and equivalent strain, overlays them on the reference, and "
                "computes RMSE and MAPE over the overlapping strain range. With "
                "the rate-dependent model the run stays nearly pressure-free, so "
                "the equivalent stress is the correct measure. Saves "
                "matlab/figures/stress_strain_comparison.png. Call after "
                "run_simulation."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
]
