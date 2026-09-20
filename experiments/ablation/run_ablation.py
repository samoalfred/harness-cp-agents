# -*- coding: utf-8 -*-
"""
run_ablation.py  --  Reviewer point #1 ablation (B1).

Question: does the agent recover the correct CS2 execution order from the
PREREQUISITE information in the tool descriptions, or from elsewhere?

Design (isolates the tool descriptions as the only variable):
  * The SYSTEM PROMPT is MINIMAL and goal-only (paper Section 2.3): it lists the
    tools but states NO workflow, NO "call after", NO "not needed" scoping. It is
    byte-identical across both conditions.
  * The USER QUERY is identical across both conditions. It carries scientific
    intent (which case, do-not-regenerate) but does NOT spell out the
    run -> extract -> pole -> comparison ordering.
  * FULL condition   : tool_schemas_full.py    (descriptions keep prerequisites)
  * ABLATED condition: tool_schemas_ablated.py (prerequisite/ordering clauses removed)

Execution is a DRY RUN: tools are not actually executed. Each tool returns a
canned SUCCESS observation so the agent proceeds through the whole pipeline in
seconds, and we log ONLY the ORDER in which the agent chooses to call tools.
Observations are always SUCCESS (never FAILED), so the environment never
"teaches" the agent the correct order through a failure -- the recovered order
reflects the agent's a priori reasoning from the descriptions alone.

Runs N repetitions per condition and reports the correct-sequence rate.

Usage:
    export OPENAI_API_KEY='sk-...'
    python3.7 run_ablation.py --n 20                 # both conditions, 20 reps
    python3.7 run_ablation.py --n 20 --condition ablated
    python3.7 run_ablation.py --n 20 --model gpt-4o
"""

import os
import sys
import json
import argparse
import datetime

from openai import OpenAI

# ---------------------------------------------------------------------------
# Minimal, goal-only system prompt (paper Section 2.3). NO workflow, NO
# ordering, NO "not needed" scoping. Identical across both conditions.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are an autonomous agent for crystal plasticity simulation. Your goal: "
    "fulfill the user's request using the tools available to you.\n"
    "You have the following tools: inject_simulation_parameters, "
    "generate_microstructure, convert_hdf5_to_prisms, run_simulation, "
    "extract_post_orientations, generate_pole_figures, create_comparison_figure, "
    "compare_stress_strain.\n"
    "Read each tool's description carefully. The descriptions tell you what each "
    "tool does, what it requires, and what it produces. Use that information to "
    "reason about which tools to call, in what order, and with what arguments. "
    "Before each tool call, write one sentence of reasoning. When you have "
    "completed the task, stop calling tools and deliver your final response."
)

# ---------------------------------------------------------------------------
# User query -- identical across conditions. Carries scientific intent but does
# NOT dictate the run/extract/pole/comparison ordering.
# ---------------------------------------------------------------------------
USER_QUERY = (
    "Perform a forward validation of the pre-configured OFHC copper compression "
    "case (Yaghoobi et al. 2022, PRISMS-Plasticity TM). The ~400-grain "
    "microstructure and the prm.prm input (fixed rate-dependent Cu slip "
    "parameters, Taylor model, velocity-gradient BC, compression along Z to true "
    "strain about 1.0) are already in place, so do not regenerate the "
    "microstructure, convert it, or change any parameters. Produce two "
    "comparisons: (a) the {111}, {100}, and {110} pole figures on the 0-3.5 MRD "
    "scale, both a pre-versus-post evolution figure and an aligned comparison "
    "against the reference paper Fig. 2c; and (b) a comparison of the simulated "
    "von Mises equivalent stress versus equivalent strain against the digitized "
    "reference curve, reporting RMSE and MAPE. Finish with a brief physical "
    "interpretation of the texture evolution and the stress-strain agreement."
)

# ---------------------------------------------------------------------------
# Canned dry-run observations. Always SUCCESS.
# ---------------------------------------------------------------------------
CANNED = {
    "inject_simulation_parameters": "SUCCESS: Parameters written to prm.prm.",
    "generate_microstructure": "SUCCESS: New microstructure generated (input_structure_poly.h5).",
    "convert_hdf5_to_prisms": "SUCCESS: Converted to grainID.txt/orientations.txt; grid 5x8x10, 400 grains.",
    "run_simulation": "SUCCESS: Simulation complete. Wrote results/stressstrain.txt and QuadratureOutputs099.csv.",
    "extract_post_orientations": "SUCCESS: Extracted post-deformation Rodrigues vectors. Saved matlab/orientations_post_deformation.csv.",
    "generate_pole_figures": "SUCCESS: Pre/post ODFs computed; {100},{110},{111} pole figures and tiles saved.",
    "create_comparison_figure": "SUCCESS: texture_comparison.png and texture_vs_paper.png saved.",
    "compare_stress_strain": "SUCCESS: RMSE 4.8 MPa, MAPE 1.8%. stress_strain_comparison.png saved.",
}

MAX_ITERATIONS = 20
UNNECESSARY = {"inject_simulation_parameters", "generate_microstructure", "convert_hdf5_to_prisms"}


def run_once(client, model, schemas):
    """Run one agent episode (dry run). Returns (sequence, terminated)."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_QUERY},
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
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })
        for tc in msg.tool_calls:
            name = tc.function.name
            sequence.append(name)
            messages.append({
                "role": "tool", "tool_call_id": tc.id,
                "content": CANNED.get(name, "SUCCESS."),
            })
    return sequence, terminated


def first_index(seq, name):
    return seq.index(name) if name in seq else None


def score(seq):
    """Return (ordering_ok, no_unnecessary, fully_correct, reason)."""
    r = first_index(seq, "run_simulation")
    e = first_index(seq, "extract_post_orientations")
    g = first_index(seq, "generate_pole_figures")
    c = first_index(seq, "create_comparison_figure")
    s = first_index(seq, "compare_stress_strain")

    reasons = []
    ok = True
    # all five productive tools present
    for nm, idx in [("run_simulation", r), ("extract_post_orientations", e),
                    ("generate_pole_figures", g), ("create_comparison_figure", c),
                    ("compare_stress_strain", s)]:
        if idx is None:
            ok = False
            reasons.append("missing %s" % nm)
    if ok:
        if not (r < e):
            ok = False; reasons.append("run not before extract")
        if not (e < g):
            ok = False; reasons.append("extract not before pole_figures")
        if not (g < c):
            ok = False; reasons.append("pole_figures not before comparison_figure")
        if not (r < s):
            ok = False; reasons.append("run not before stress_strain")
    unnecessary = [t for t in seq if t in UNNECESSARY]
    no_unnec = (len(unnecessary) == 0)
    if unnecessary:
        reasons.append("unnecessary calls: %s" % ",".join(sorted(set(unnecessary))))
    fully = ok and no_unnec
    return ok, no_unnec, fully, ("; ".join(reasons) if reasons else "correct")


def run_condition(client, model, schemas, label, n, logf):
    print("\n" + "=" * 70)
    print("CONDITION: %s   (model=%s, n=%d)" % (label, model, n))
    print("=" * 70)
    logf.write("\n=== CONDITION: %s (model=%s, n=%d) ===\n" % (label, model, n))
    n_order = n_unnec_free = n_full = n_term = 0
    for i in range(1, n + 1):
        seq, terminated = run_once(client, model, schemas)
        ordering_ok, no_unnec, fully, reason = score(seq)
        n_order += int(ordering_ok)
        n_unnec_free += int(no_unnec)
        n_full += int(fully)
        n_term += int(terminated)
        line = "[%s] run %2d: %-7s | seq=%s | %s" % (
            label, i, "FULL-OK" if fully else "x", " -> ".join(seq), reason)
        print(line)
        logf.write(line + "\n")
    print("-" * 70)
    summ = ("[%s] ordering-correct %d/%d (%.0f%%) | no-unnecessary %d/%d | "
            "fully-correct %d/%d (%.0f%%) | terminated %d/%d" % (
                label, n_order, n, 100.0 * n_order / n, n_unnec_free, n,
                n_full, n, 100.0 * n_full / n, n_term, n))
    print(summ)
    logf.write(summ + "\n")
    return {"label": label, "n": n, "ordering": n_order,
            "no_unnecessary": n_unnec_free, "fully": n_full, "terminated": n_term}


def main():
    ap = argparse.ArgumentParser(description="CS2 tool-description ablation (B1).")
    ap.add_argument("--n", type=int, default=20, help="repetitions per condition")
    ap.add_argument("--condition", choices=["full", "ablated", "both"], default="both")
    ap.add_argument("--model", type=str, default=os.environ.get("ABLATION_MODEL", "gpt-4o"))
    args = ap.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set.  export OPENAI_API_KEY='sk-...'")
        sys.exit(1)

    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    from tool_schemas_full import TOOL_SCHEMAS as FULL
    from tool_schemas_ablated import TOOL_SCHEMAS as ABLATED

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(here, "ablation_log_%s.txt" % stamp)
    results = []
    with open(log_path, "w") as logf:
        logf.write("CS2 tool-description ablation (B1)\nmodel=%s  n=%d  time=%s\n"
                   % (args.model, args.n, stamp))
        if args.condition in ("full", "both"):
            results.append(run_condition(client, args.model, FULL, "FULL", args.n, logf))
        if args.condition in ("ablated", "both"):
            results.append(run_condition(client, args.model, ABLATED, "ABLATED", args.n, logf))

        logf.write("\n=== SUMMARY ===\n")
        for r in results:
            logf.write(json.dumps(r) + "\n")

    print("\n=== SUMMARY (paper-ready) ===")
    # Primary metric (as reported in the paper): the sequence respects every data
    # dependency. The stricter fully-correct count (also excludes the held-out
    # inject/generate/convert calls) is shown in parentheses for completeness.
    for r in results:
        print("%-8s: valid order (data dependencies) in %d/%d runs (%.0f%%)"
              "  [fully-correct %d/%d]"
              % (r["label"], r["ordering"], r["n"], 100.0 * r["ordering"] / r["n"],
                 r["fully"], r["n"]))
    print("\nFull log: %s" % log_path)


if __name__ == "__main__":
    main()
