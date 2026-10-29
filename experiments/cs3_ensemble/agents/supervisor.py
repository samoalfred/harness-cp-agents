# -*- coding: utf-8 -*-
"""
Supervisor Agent for SS316L_Auto_Pipeline — Fully Autonomous Texture Comparison.

Pipeline stages:
  Stage 0 — LLM extracts parameters from query → injects into config files
  Stage 1 — Microstructure generation (MATLAB) with LLM-set texture/orientation
  Stage 2 — Single PRISMS-Plasticity FEM simulation with LLM-set slip parameters
  Stage 3 — Extract post-deformation orientations from last QuadratureOutputs CSV
  Stage 4 — Post-deformation pole figures with matched color scales (oriplot_big.m)
  Stage 5 — Side-by-side comparison figure (matplotlib, 300 DPI)
  Stage 6 — LLM physical interpretation of texture evolution

LLM role:
  - Parse query → structured parameters (truly controls execution)
  - Post-simulation physical interpretation + anomaly flagging
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.dirname(_HERE)
sys.path.insert(0, _BASE)
sys.path.insert(0, os.path.join(_BASE, "tools"))

import config_semi
from llm_client import chat
from llm_param_extractor import extract_parameters
from param_injector import inject_all
from matlab_runner import run_microstructure_gen
from h5_converter import convert_h5_to_prisms
from single_sim import run_single_simulation
from texture_analysis import run_texture_analysis
from texture_compare import create_comparison


class SupervisorAgent(object):

    SYSTEM_PROMPT = (
        "You are an expert materials science supervisor analysing crystallographic "
        "texture evolution in SS316L austenitic stainless steel under uniaxial tension.\n\n"
        "You have knowledge of:\n"
        "  - FCC crystal plasticity and slip systems\n"
        "  - Texture representation via pole figures ({100}, {110}, {111})\n"
        "  - Expected texture evolution under uniaxial tension in FCC metals\n"
        "  - Rodrigues vector representation of orientations\n\n"
        "Your role:\n"
        "  1. Interpret the observed texture change after simulation\n"
        "  2. Assess physical consistency with SS316L FCC deformation behaviour\n"
        "  3. Flag any anomalies if the texture change is unexpected\n\n"
        "Keep responses concise and physically grounded."
    )

    def __init__(self):
        pass

    def _interpret_texture(self, query, params, micro_info):
        print("\n[Supervisor] LLM: Post-simulation interpretation...")

        fd  = params.get("fiber_direction", [1, 0, 1])
        micro_context = ""
        if micro_info:
            micro_context = (
                "Microstructure: {}x{}x{} voxel grid, {} grains, "
                "[{} {} {}] fiber texture (sigma={} deg), mean grain size ~55 um.\n"
                "Slip parameters: s0={} MPa, h0={} MPa, ss={} MPa, n={}.\n"
            ).format(
                micro_info.get("Nx", "?"), micro_info.get("Ny", "?"),
                micro_info.get("Nz", "?"), micro_info.get("N_grains", "?"),
                fd[0], fd[1], fd[2], params.get("sigma_spread", "?"),
                params.get("s0", "?"), params.get("h0", "?"),
                params.get("ss", "?"), params.get("n", "?")
            )

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": (
                "The texture comparison pipeline has completed.\n\n"
                "{micro}"
                "Pre- and post-deformation {{100}}, {{110}}, and {{111}} pole figures "
                "have been generated and saved side by side.\n\n"
                "Please provide:\n"
                "1. A succinct interpretation (4-6 sentences) of the expected "
                "texture evolution — what changed and why\n"
                "2. Whether this is physically consistent with SS316L FCC "
                "deformation behaviour under uniaxial tension\n"
                "3. Any anomalies to watch for when reviewing the pole figures\n\n"
                "Query context: {query}"
            ).format(micro=micro_context, query=query)}
        ]
        return chat(messages, model=config_semi.OPENAI_MODEL,
                    temperature=0.1, max_tokens=350)

    def run(self, query, skip_microstructure=False, skip_simulation=False):
        print("\n" + "=" * 65)
        print("[Supervisor] SS316L AUTO PIPELINE STARTED")
        print("[Supervisor] Query: {}".format(query))
        print("=" * 65)

        # ── Stage 0: LLM parameter extraction + config injection ──
        print("\n[Supervisor] Stage 0: LLM Parameter Extraction")
        print("-" * 50)
        params, _ = extract_parameters(query)

        ok, msg = inject_all(params)
        if not ok:
            return None, "Pipeline failed at Stage 0: {}".format(msg)
        print("[Supervisor] Config files updated from LLM parameters.")

        micro_info = {}

        # ── Stage 1: Microstructure generation ────────────────────
        if not skip_microstructure:
            print("\n[Supervisor] Stage 1: Microstructure Generation")
            print("-" * 50)
            ok, msg = run_microstructure_gen()
            if not ok:
                print("[Supervisor] MATLAB failed: {}".format(msg))
                return None, "Pipeline failed at Stage 1: {}".format(msg)
            print("[Supervisor] {}".format(msg))

            ok, msg, micro_info = convert_h5_to_prisms()
            if not ok:
                print("[Supervisor] HDF5 conversion failed: {}".format(msg))
                return None, "Pipeline failed at Stage 1 (conversion): {}".format(msg)
            print("[Supervisor] {}".format(msg))
        else:
            print("\n[Supervisor] Skipping Stage 1 — using existing microstructure.")

        # ── Stage 2: Single PRISMS simulation ─────────────────────
        if not skip_simulation:
            print("\n[Supervisor] Stage 2: PRISMS-Plasticity Simulation")
            print("-" * 50)
            ok, msg = run_single_simulation()
            if not ok:
                print("[Supervisor] Simulation failed: {}".format(msg))
                return None, "Pipeline failed at Stage 2: {}".format(msg)
            print("[Supervisor] {}".format(msg))
        else:
            print("\n[Supervisor] Skipping Stage 2 — using existing simulation results.")

        # ── Stage 3 & 4: Extract orientations + pole figures ──────
        print("\n[Supervisor] Stage 3 & 4: Post-Deformation Texture Analysis")
        print("-" * 50)
        ok, msg = run_texture_analysis()
        if not ok:
            print("[Supervisor] Texture analysis failed: {}".format(msg))
            return None, "Pipeline failed at Stage 3/4: {}".format(msg)
        print("[Supervisor] {}".format(msg))

        # ── Stage 5: Comparison figure ────────────────────────────
        print("\n[Supervisor] Stage 5: Creating Comparison Figure")
        print("-" * 50)
        ok, msg, fig_path = create_comparison()
        if not ok:
            print("[Supervisor] Comparison figure failed: {}".format(msg))
            fig_path = None
        else:
            print("[Supervisor] {}".format(msg))

        # ── Stage 6: LLM interpretation ───────────────────────────
        interpretation = self._interpret_texture(query, params, micro_info)

        # Final summary
        fd = params.get("fiber_direction", [1, 0, 1])
        print("\n" + "=" * 65)
        print("[Supervisor] PIPELINE COMPLETE")
        print("  Texture      : {} fiber, sigma={}°".format(fd, params.get("sigma_spread")))
        print("  Slip params  : s0={}, h0={}, ss={}, n={}".format(
            params["s0"], params["h0"], params["ss"], params["n"]))
        if micro_info:
            print("  Microstructure: {}x{}x{} voxels, {} grains".format(
                micro_info.get("Nx"), micro_info.get("Ny"),
                micro_info.get("Nz"), micro_info.get("N_grains")))
        if fig_path:
            print("  Comparison   : matlab/figures/texture_comparison.png")
        print("\n[Supervisor] Physical Interpretation:")
        print(interpretation)
        print("=" * 65)

        return {"comparison_figure": fig_path, "params": params}, interpretation
