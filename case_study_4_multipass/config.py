# -*- coding: utf-8 -*-
"""
config.py  (CS4 — ZX31, Mg-3Zn-0.3Ca)
Alloy-specific configuration. Tool code is identical across CS4 folders; only this
file and the reference data change. Fixed slip/twin parameters live in prm.prm
(Table 1, 350 C).
"""
ALLOY        = "ZX31"
SIM_COMMAND  = "../../main_ratedep"   # RATE-DEPENDENT binary (required for HCP Mg)
SUBDIV       = 12                      # cubic mesh N x N x N -> N^3 grains (8=512; 12=1728; 16=4096)
N_GRAINS     = SUBDIV ** 3
SUBSTEPS     = 100                    # ZX31 stable at 100 Taylor substeps
N_PASSES     = 5

REF_1PASS_STRESS   = "reference/authors_1pass_stressstrain.txt"
REF_5PASS_TEXTURE  = "reference/authors_5pass_QuadratureOutputs79.csv"
REF_EXPERIMENT     = "reference/experiment_5pass.png"   # Fig 7(h), ZX31 after 5 passes
EXPERIMENT_MAX     = 4.6

OPENAI_MODEL = "gpt-4o"

DEFAULT_QUERY = (
    "Reproduce the multi-pass deformation-texture evolution of ZX31 (Mg-3Zn-0.3Ca) from "
    "Yaghoobi, Berman & Allison (2025) with PRISMS-Plasticity TM. This is a chained, "
    "five-pass workflow simulating hot rolling: each plane-strain-compression pass deforms "
    "the material to 20% true strain along the normal direction, and the deformed grain "
    "orientations from one pass become the initial texture of the next pass. The alloy is HCP "
    "with the calibrated Table-1 (350 C) slip/twin parameters already set in prm.prm, and it "
    "requires the RATE-DEPENDENT constitutive model (the rate-independent binary is physically "
    "wrong). "
    "Run the five passes in order. After the FIRST pass, compare the single-pass mechanical "
    "response (plane-strain flow stress sigma_yy - sigma_zz vs true strain) against the "
    "reference simulation, reporting RMSE and MAPE. After the FIFTH pass, analyse the (0001) "
    "basal texture evolution (peak intensity vs pass number) and compare the final texture "
    "against the reference 5-pass simulation and against the experiment. "
    "Finally, interpret the result: ZX31 has high basal-to-pyramidal and twin-to-pyramidal "
    "CRSS ratios, which suppress basal slip and extension twinning in favour of pyramidal "
    "<c+a> slip, so it should develop a WEAK basal texture that SPLITS toward the rolling "
    "direction and stays weak with increasing passes. Note that the deformation-only "
    "simulation is expected to exceed the experimental intensity because recrystallization "
    "(which weakens texture) is neglected."
)
