# -*- coding: utf-8 -*-
"""
run_reliability.py  --  Reviewer point #2 reliability study (B2).

Measures run-to-run reliability of the agent's autonomous behavior for each of
the three case studies, using each case's GENUINE deployed harness:
its real system prompt (imported from that case's agents module) and its real
tool schemas (imported from that case's tools module). The real user query for
each case is used verbatim.

Execution is a DRY RUN (no simulations, no optimizers): each tool returns a
canned SUCCESS observation, so a full episode finishes in seconds and we can
repeat it N times cheaply. We record, per run, (a) whether the agent produced
the correct tool sequence and (b) whether it terminated cleanly. This isolates
AGENT reliability (sequencing + termination) from numerical/optimizer
stochasticity, which is characterized separately (see README, B2b).

Because the three case folders reuse module names (react_tools, config_semi),
each case must be imported in its OWN process. Run one case per invocation:

    export OPENAI_API_KEY='sk-...'
    python3.7 run_reliability.py --case CS1 --n 20
    python3.7 run_reliability.py --case CS2 --n 20
    python3.7 run_reliability.py --case CS3 --n 20

or use ./run_all.sh 20 to run all three sequentially.
"""

import os
import sys
import json
import argparse
import datetime
import importlib

from openai import OpenAI

# Base directory holding the three case-study folders. Override with the
# CP_AGENTS_FCC environment variable to point at your local checkout.
FCC = os.environ.get(
    "CP_AGENTS_FCC",
    os.path.expanduser("~/candi/plasticity/applications/crystalPlasticity/fcc"))
MAX_ITERATIONS = 25

# ---------------------------------------------------------------------------
# Case definitions. Each imports the REAL prompt + REAL schemas from its folder.
# ---------------------------------------------------------------------------
CS1_QUERY = (
    "Generate a random SS316L microstructure for crystal plasticity simulations using PRISMS plasticity. "
    "Then calibrate the crystal plasticity slip parameters for SS316L to match the experimental tensile stress-strain data (SS316L_experiment.txt). "
    "Use Bayesian Optimization. Tune: Initial Slip Resistance [100-150 MPa], Initial Hardening Modulus [800-2500 MPa], Saturation Stress [350-600 MPa], Power Law Exponent [1-3]. "
    "Stop when RMSE < 5 MPa or MAPE < 2% or after 60 simulations."
)

CS2_QUERY = (
    "Reproduce Application 1 (polycrystalline OFHC copper, uniaxial compression) of "
    "Yaghoobi et al. (2022), PRISMS-Plasticity TM, as a forward validation of the copper "
    "already configured in this folder. The model is a RATE-DEPENDENT crystal plasticity "
    "formulation with isotropic hardening (gamma_dot0 = 1e-3, rate sensitivity m = 77, no "
    "twinning, no back stress), homogenized with the Taylor model. Loading is uniaxial "
    "COMPRESSION along Z through an imposed velocity gradient L = diag(0.0005, 0.0005, "
    "-0.001), with true strain accumulating linearly to 1.0 (the paper's 99% compression); "
    "the texture snapshot at t = 990 is the -99% state. The microstructure (about 400 "
    "grains) and the prm.prm input (including the fixed slip parameters) are already in "
    "place, so do not regenerate the microstructure, convert it, or change any parameters; "
    "run the simulation exactly as configured. "
    "Then perform two comparisons. First, the crystallographic texture: plot {111}, {100}, "
    "and {110} pole figures (Z at centre) on the fixed 0-3.5 MRD scale, producing both the "
    "pre-vs-post evolution figure and an aligned comparison of this simulation's "
    "post-deformation pole figures against the reference paper Fig. 2c "
    "(Reference_Plot_figures.png); the deformed texture should reproduce the <110> "
    "compression fibre. "
    "Second, compare the simulated EQUIVALENT (von Mises) stress versus EQUIVALENT strain "
    "against the digitized PRISMS-Plasticity TM reference curve of Yaghoobi et al. (2022) in "
    "'Yaghoobi et al. (2022).csv', reporting RMSE and MAPE over the overlapping strain range. "
    "Provide a brief physical interpretation of the texture evolution (the development of the "
    "<110> compression fibre) and of the stress-strain agreement for copper."
)

CS3_QUERY = (
    "Recover the initial crystallographic texture of the copper polycrystal that, "
    "after uniaxial compression along Z to true strain ~1.0, reproduces the target "
    "deformation texture in fig2c_targets.json (the {111}, {100}, {110} pole figures "
    "with a central {110} compression fibre). Select the most sample-efficient search "
    "strategy and use a budget of 15 simulations. Then interpret the recovered "
    "initial texture."
)

CASES = {
    "CS1": {
        "base": os.path.join(FCC, "SS316L_Semi_LLM_React_MicroGen3"),
        "prompt_module": "agents.react_agent",
        "schema_module": "tools.react_tools",
        "query": CS1_QUERY,
        "canned": {
            "generate_microstructure": "SUCCESS: Random SS316L microstructure generated. Wrote matlab/input_structure_poly.h5.",
            "convert_hdf5_to_prisms": "SUCCESS: Converted HDF5 to PRISMS input (grainID.txt, orientations.txt); prm.prm voxel dims updated.",
            "run_bayesian_optimization": "SUCCESS: Bayesian optimization complete. Best: s0=121 MPa, h0=2399 MPa, ss=542 MPa, n=2.94. RMSE=4.95 MPa, MAPE=2.85%. Terminated at evaluation 26 of 60.",
            "run_differential_evolution": "SUCCESS: Differential evolution complete.",
            "run_nelder_mead": "SUCCESS: Nelder-Mead complete.",
            "run_random_bo": "SUCCESS: Random+BO complete.",
        },
        "rubric": {
            "required": ["generate_microstructure", "convert_hdf5_to_prisms"],
            "order": ["generate_microstructure", "convert_hdf5_to_prisms", "run_bayesian_optimization"],
            "after": [],
            "single_choice": (
                ["run_bayesian_optimization", "run_differential_evolution",
                 "run_nelder_mead", "run_random_bo"],
                "run_bayesian_optimization",
            ),
            "forbidden": [],
        },
    },
    "CS2": {
        "base": os.path.join(FCC, "CS2_Texture_Evolution"),
        "prompt_module": "agents.react_agent",
        "schema_module": "tools.react_tools",
        "query": CS2_QUERY,
        "canned": {
            "run_simulation": "SUCCESS: Simulation complete. Wrote results/stressstrain.txt and QuadratureOutputs099.csv.",
            "extract_post_orientations": "SUCCESS: Extracted post-deformation Rodrigues vectors. Saved matlab/orientations_post_deformation.csv.",
            "generate_pole_figures": "SUCCESS: Pre/post ODFs computed; {100},{110},{111} pole figures and tiles saved.",
            "create_comparison_figure": "SUCCESS: texture_comparison.png and texture_vs_paper.png saved.",
            "compare_stress_strain": "SUCCESS: RMSE 4.8 MPa, MAPE 1.8%. stress_strain_comparison.png saved.",
            "inject_simulation_parameters": "SUCCESS: Parameters written to prm.prm.",
            "generate_microstructure": "SUCCESS: New microstructure generated.",
            "convert_hdf5_to_prisms": "SUCCESS: Converted to grainID.txt/orientations.txt.",
        },
        "rubric": {
            "required": ["run_simulation", "extract_post_orientations",
                         "generate_pole_figures", "create_comparison_figure",
                         "compare_stress_strain"],
            "order": ["run_simulation", "extract_post_orientations",
                      "generate_pole_figures", "create_comparison_figure"],
            "after": [("compare_stress_strain", "run_simulation")],
            "single_choice": None,
            "forbidden": ["inject_simulation_parameters", "generate_microstructure",
                          "convert_hdf5_to_prisms"],
        },
    },
    "CS3": {
        "base": os.path.join(FCC, "CS3_Inverse_Problem"),
        "prompt_module": "agents.inverse_agent",
        "schema_module": "tools.inverse_tools",
        "query": CS3_QUERY,
        "canned": {
            "run_bayesian_texture_inverse": "SUCCESS: Bayesian texture inverse complete. Recovered diffuse [110] fibre, spread 27 deg, loss 0.262 (15 evaluations).",
            "run_random_texture_inverse": "SUCCESS: Random-search texture inverse complete.",
        },
        "rubric": {
            "required": ["run_bayesian_texture_inverse"],
            "order": ["run_bayesian_texture_inverse"],
            "after": [],
            "single_choice": (
                ["run_bayesian_texture_inverse", "run_random_texture_inverse"],
                "run_bayesian_texture_inverse",
            ),
            "forbidden": [],
        },
    },
}


def load_case(case):
    """Insert the case folder on sys.path and import its real prompt + schemas."""
    cfg = CASES[case]
    base = cfg["base"]
    for p in (base, os.path.join(base, "tools"), os.path.join(base, "agents")):
        if p not in sys.path:
            sys.path.insert(0, p)
    prompt_mod = importlib.import_module(cfg["prompt_module"])
    schema_mod = importlib.import_module(cfg["schema_module"])
    return prompt_mod.SYSTEM_PROMPT, schema_mod.TOOL_SCHEMAS, cfg


def first_index(seq, name):
    return seq.index(name) if name in seq else None


def score(seq, terminated, rubric):
    reasons = []
    ok = True
    for nm in rubric["required"]:
        if nm not in seq:
            ok = False; reasons.append("missing %s" % nm)
    order = rubric["order"]
    for a, b in zip(order, order[1:]):
        ia, ib = first_index(seq, a), first_index(seq, b)
        if ia is None or ib is None or not (ia < ib):
            ok = False; reasons.append("%s not before %s" % (a, b))
    for later, earlier in rubric["after"]:
        il, ie = first_index(seq, later), first_index(seq, earlier)
        if il is None or ie is None or not (ie < il):
            ok = False; reasons.append("%s not after %s" % (later, earlier))
    sc = rubric["single_choice"]
    if sc is not None:
        alts, expected = sc
        calls = [t for t in seq if t in alts]
        if len(calls) != 1 or calls[0] != expected:
            ok = False; reasons.append("optimizer choice=%s (want single %s)" % (calls, expected))
    forbidden = [t for t in seq if t in rubric["forbidden"]]
    if forbidden:
        ok = False; reasons.append("forbidden calls: %s" % ",".join(sorted(set(forbidden))))
    if not terminated:
        ok = False; reasons.append("did not terminate")
    return ok, ("; ".join(reasons) if reasons else "correct")


def run_once(client, model, system_prompt, query, schemas, canned):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]
    sequence = []
    terminated = False
    for _ in range(MAX_ITERATIONS):
        resp = client.chat.completions.create(
            model=model, messages=messages, tools=schemas,
            tool_choice="auto", temperature=0.1, max_tokens=1024,
        )
        msg = resp.choices[0].message
        if resp.choices[0].finish_reason == "stop" or not msg.tool_calls:
            terminated = True
            break
        messages.append({
            "role": "assistant", "content": msg.content,
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })
        for tc in msg.tool_calls:
            name = tc.function.name
            sequence.append(name)
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": canned.get(name, "SUCCESS.")})
    return sequence, terminated


def main():
    ap = argparse.ArgumentParser(description="Agent reliability over repeated runs (B2).")
    ap.add_argument("--case", choices=list(CASES.keys()), required=True)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--model", type=str, default=os.environ.get("RELIABILITY_MODEL", "gpt-4o"))
    args = ap.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set.  export OPENAI_API_KEY='sk-...'")
        sys.exit(1)

    system_prompt, schemas, cfg = load_case(args.case)
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    here = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(here, "reliability_%s_%s.txt" % (args.case, stamp))

    print("\n" + "=" * 70)
    print("RELIABILITY  case=%s  model=%s  n=%d" % (args.case, args.model, args.n))
    print("prompt: %s.SYSTEM_PROMPT   schemas: %s.TOOL_SCHEMAS"
          % (cfg["prompt_module"], cfg["schema_module"]))
    print("=" * 70)

    n_seq = n_term = 0
    with open(log_path, "w") as logf:
        logf.write("Reliability case=%s model=%s n=%d time=%s\n"
                   % (args.case, args.model, args.n, stamp))
        for i in range(1, args.n + 1):
            seq, terminated = run_once(client, args.model, system_prompt,
                                       cfg["query"], schemas, cfg["canned"])
            ok, reason = score(seq, terminated, cfg["rubric"])
            n_seq += int(ok)
            n_term += int(terminated)
            line = "[%s] run %2d: %-4s | seq=%s | %s" % (
                args.case, i, "OK" if ok else "x", " -> ".join(seq), reason)
            print(line)
            logf.write(line + "\n")
        summ = ("[%s] correct-sequence %d/%d (%.0f%%) | terminated %d/%d (%.0f%%)"
                % (args.case, n_seq, args.n, 100.0 * n_seq / args.n,
                   n_term, args.n, 100.0 * n_term / args.n))
        print("-" * 70); print(summ)
        logf.write(summ + "\n")
    print("Log: %s" % log_path)


if __name__ == "__main__":
    main()
