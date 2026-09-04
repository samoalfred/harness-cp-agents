# -*- coding: utf-8 -*-
"""
run_ablation2.py  --  decisive 2x2 ablation.

run_ablation.py (v1) found that stripping the prerequisite clauses did NOT
degrade CS2 sequencing: the tool NAMES (run_simulation, extract_post_orientations,
generate_pole_figures, ...) already encode the order, so the descriptions were
redundant. To test whether the DESCRIPTIONS carry the ordering knowledge, this
script crosses two factors:

    names        : descriptive        vs  opaque (tool_a ... tool_h)
    descriptions : full (prereqs)     vs  ablated (prereqs removed)

Four conditions. The decisive contrast is OPAQUE-FULL vs OPAQUE-ABLATED: with
names hidden, only the description text can convey order, so if OPAQUE-FULL
stays high while OPAQUE-ABLATED drops, the prerequisite clauses in the
descriptions are shown to be load-bearing.

Everything else is identical to v1: minimal goal-only system prompt, identical
query, dry-run executor with always-SUCCESS canned observations, N reps.

Usage:
    export OPENAI_API_KEY='sk-...'
    python3.7 run_ablation2.py --n 20                    # all four conditions
    python3.7 run_ablation2.py --n 20 --model gpt-4o
"""

import os
import sys
import copy
import json
import argparse
import datetime

from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tool_schemas_full import TOOL_SCHEMAS as FULL
from tool_schemas_ablated import TOOL_SCHEMAS as ABLATED
from run_ablation import SYSTEM_PROMPT, USER_QUERY, score, MAX_ITERATIONS

# opaque alias for every real tool name (order preserved, semantics removed)
ALIAS = {
    "inject_simulation_parameters": "tool_a",
    "generate_microstructure":      "tool_b",
    "convert_hdf5_to_prisms":       "tool_c",
    "run_simulation":               "tool_d",
    "extract_post_orientations":    "tool_e",
    "generate_pole_figures":        "tool_f",
    "create_comparison_figure":     "tool_g",
    "compare_stress_strain":        "tool_h",
}
REV = {v: k for k, v in ALIAS.items()}

CANNED_REAL = {
    "inject_simulation_parameters": "SUCCESS: Parameters written to prm.prm.",
    "generate_microstructure": "SUCCESS: New microstructure generated (input_structure_poly.h5).",
    "convert_hdf5_to_prisms": "SUCCESS: Converted to grainID.txt/orientations.txt; grid 5x8x10, 400 grains.",
    "run_simulation": "SUCCESS: Simulation complete. Wrote results/stressstrain.txt and QuadratureOutputs099.csv.",
    "extract_post_orientations": "SUCCESS: Extracted post-deformation Rodrigues vectors. Saved matlab/orientations_post_deformation.csv.",
    "generate_pole_figures": "SUCCESS: Pre/post ODFs computed; {100},{110},{111} pole figures and tiles saved.",
    "create_comparison_figure": "SUCCESS: texture_comparison.png and texture_vs_paper.png saved.",
    "compare_stress_strain": "SUCCESS: RMSE 4.8 MPa, MAPE 1.8%. stress_strain_comparison.png saved.",
}

# opaque system prompt: same minimal prompt but the tool list uses aliases
_TOOL_LIST_REAL = ("inject_simulation_parameters, generate_microstructure, "
                   "convert_hdf5_to_prisms, run_simulation, extract_post_orientations, "
                   "generate_pole_figures, create_comparison_figure, compare_stress_strain")
_TOOL_LIST_OPAQUE = ", ".join(ALIAS[n] for n in
                              ["inject_simulation_parameters", "generate_microstructure",
                               "convert_hdf5_to_prisms", "run_simulation",
                               "extract_post_orientations", "generate_pole_figures",
                               "create_comparison_figure", "compare_stress_strain"])
SYSTEM_PROMPT_OPAQUE = SYSTEM_PROMPT.replace(_TOOL_LIST_REAL, _TOOL_LIST_OPAQUE)


def make_opaque(schemas):
    """Rename functions to aliases and substitute any real tool name inside the
    description text with its alias (longest name first to avoid partial hits)."""
    out = copy.deepcopy(schemas)
    names_by_len = sorted(ALIAS.keys(), key=len, reverse=True)
    for t in out:
        fn = t["function"]
        fn["name"] = ALIAS[fn["name"]]
        d = fn["description"]
        for real in names_by_len:
            d = d.replace(real, ALIAS[real])
        fn["description"] = d
    return out


def build_condition(kind):
    """Return (label, schemas, system_prompt, canned_by_presented_name, name_map)."""
    if kind == "descriptive_full":
        return ("DESCRIPTIVE-FULL", FULL, SYSTEM_PROMPT,
                dict(CANNED_REAL), {n: n for n in CANNED_REAL})
    if kind == "descriptive_ablated":
        return ("DESCRIPTIVE-ABLATED", ABLATED, SYSTEM_PROMPT,
                dict(CANNED_REAL), {n: n for n in CANNED_REAL})
    if kind == "opaque_full":
        canned = {ALIAS[k]: v for k, v in CANNED_REAL.items()}
        return ("OPAQUE-FULL", make_opaque(FULL), SYSTEM_PROMPT_OPAQUE, canned, dict(REV))
    if kind == "opaque_ablated":
        canned = {ALIAS[k]: v for k, v in CANNED_REAL.items()}
        return ("OPAQUE-ABLATED", make_opaque(ABLATED), SYSTEM_PROMPT_OPAQUE, canned, dict(REV))
    raise ValueError(kind)


def run_once(client, model, system_prompt, schemas, canned):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": USER_QUERY},
    ]
    seq = []
    terminated = False
    for _ in range(MAX_ITERATIONS):
        resp = client.chat.completions.create(
            model=model, messages=messages, tools=schemas,
            tool_choice="auto", temperature=0.1, max_tokens=1024)
        msg = resp.choices[0].message
        if resp.choices[0].finish_reason == "stop" or not msg.tool_calls:
            terminated = True
            break
        messages.append({
            "role": "assistant", "content": msg.content,
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls]})
        for tc in msg.tool_calls:
            name = tc.function.name
            seq.append(name)
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": canned.get(name, "SUCCESS.")})
    return seq, terminated


def run_condition(client, model, kind, n, logf):
    label, schemas, prompt, canned, name_map = build_condition(kind)
    print("\n" + "=" * 70)
    print("CONDITION: %s   (model=%s, n=%d)" % (label, model, n))
    print("=" * 70)
    logf.write("\n=== %s (model=%s, n=%d) ===\n" % (label, model, n))
    n_full = n_term = 0
    for i in range(1, n + 1):
        raw, terminated = run_once(client, model, prompt, schemas, canned)
        real = [name_map.get(x, x) for x in raw]      # translate to real identity
        ordering_ok, no_unnec, fully, reason = score(real)
        n_full += int(fully)
        n_term += int(terminated)
        line = "[%s] run %2d: %-7s | seq=%s | %s" % (
            label, i, "FULL-OK" if fully else "x", " -> ".join(real), reason)
        print(line)
        logf.write(line + "\n")
    summ = "[%s] fully-correct %d/%d (%.0f%%) | terminated %d/%d" % (
        label, n_full, n, 100.0 * n_full / n, n_term, n)
    print("-" * 70); print(summ)
    logf.write(summ + "\n")
    return {"condition": label, "n": n, "fully": n_full, "terminated": n_term}


def main():
    ap = argparse.ArgumentParser(description="CS2 2x2 ablation (names x descriptions).")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--model", type=str, default=os.environ.get("ABLATION_MODEL", "gpt-4o"))
    ap.add_argument("--conditions", type=str,
                    default="descriptive_full,descriptive_ablated,opaque_full,opaque_ablated")
    args = ap.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set.  export OPENAI_API_KEY='sk-...'")
        sys.exit(1)

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    here = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(here, "ablation2_log_%s.txt" % stamp)
    results = []
    with open(log_path, "w") as logf:
        logf.write("CS2 2x2 ablation  model=%s n=%d time=%s\n" % (args.model, args.n, stamp))
        for kind in args.conditions.split(","):
            results.append(run_condition(client, args.model, kind.strip(), args.n, logf))
        logf.write("\n=== SUMMARY ===\n")
        for r in results:
            logf.write(json.dumps(r) + "\n")

    print("\n=== SUMMARY (paper-ready) ===")
    for r in results:
        print("%-20s: correct sequence in %d/%d runs (%.0f%%)"
              % (r["condition"], r["fully"], r["n"], 100.0 * r["fully"] / r["n"]))
    print("\nDecisive contrast: OPAQUE-FULL vs OPAQUE-ABLATED.")
    print("Full log: %s" % log_path)


if __name__ == "__main__":
    main()
