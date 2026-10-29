# -*- coding: utf-8 -*-
"""
run_exp1.py  --  Experiment 1 (Revision R1): less-prescribed autonomy, sub-tests 1a and 1b.

Answers Reviewer R4 ("tasks are too prescribed"): given ONLY the goal, the agent
chooses the decision the query previously stated for it.

  1a  CS1 calibration -- the optimizer is NOT named in the query.
      Measures which optimizer the agent selects and its stated rationale.
      (run_bayesian_optimization | run_differential_evolution | run_nelder_mead | run_random_bo)
  1b  CS3 inverse      -- neither the strategy NOR the budget is given in the query.
      Measures which search strategy the agent selects and what n_evaluations (budget)
      it sets for itself.
      (run_bayesian_texture_inverse | run_random_texture_inverse)

This uses the GENUINE case-study harness (real system prompt + real tool schemas,
imported live from the deployed case folders) in a stateful DRY RUN: every tool call
returns a canned SUCCESS so the agent walks the workflow in seconds; no CP-FEM is
launched. We log only the decision of interest and the agent's rationale.

NEUTRALIZED HINTS (Revision R1, disclosed):
  The deployed system prompts contain an explicit *default* directive that tells the
  agent which optimizer/strategy to use when the query is silent ("...or does not
  specify" in CS1; "Use this unless the user explicitly asks for a naive baseline" in
  CS3). Leaving those in would make the selection a rule-follow, not an inference, so
  this driver removes exactly those directive clauses (and nothing else -- the honest
  tool tradeoff descriptions such as "most sample-efficient / limited budget" are KEPT).
  The removals are asserted below, so if the deployed prompt ever changes the driver
  fails loudly instead of silently testing the wrong thing. Nothing is written back to
  the case folders; the harness is imported read-only and the prompt is edited in memory.

Usage (inside WSL):
    export OPENAI_API_KEY='sk-...'
    python3.7 run_exp1.py --case 1a --n 10
    python3.7 run_exp1.py --case 1b --n 10
"""

import os
import sys
import re
import json
import argparse
import datetime
import importlib
from collections import Counter

from openai import OpenAI

HERE = os.path.dirname(os.path.abspath(__file__))
FCC = os.environ.get("CP_AGENTS_FCC",
                     os.path.expanduser("~/candi/plasticity/applications/crystalPlasticity/fcc"))
MAX_ITERATIONS = 30

CASES = {
    "1a": {
        "dir": os.environ.get("EXP1_CS1_DIR", os.path.join(FCC, "SS316L_Semi_LLM_React_MicroGen3")),
        "prompt_module": "agents.react_agent", "schema_module": "tools.react_tools",
        "prompt_file": "prompt_1a_cs1_optimizer.txt",
        "optimizers": ["run_bayesian_optimization", "run_differential_evolution",
                       "run_nelder_mead", "run_random_bo"],
    },
    "1b": {
        "dir": os.environ.get("EXP1_CS3_DIR", os.path.join(FCC, "CS3_Inverse_Problem")),
        "prompt_module": "agents.inverse_agent", "schema_module": "tools.inverse_tools",
        "prompt_file": "prompt_1b_cs3_strategy_budget.txt",
        "strategies": ["run_bayesian_texture_inverse", "run_random_texture_inverse"],
    },
}

# Explicit default directives removed from the system prompt (see docstring).
# Each is (old, new); `old` MUST be present or the run aborts.
NEUTRALIZE = {
    "1a": [("Use when the query asks for Bayesian Optimization or does not specify.",
            "Use when the query asks for Bayesian Optimization.")],
    "1b": [("Recommended for this expensive forward model. Use this unless the user explicitly asks for a naive baseline.",
            "Recommended for this expensive forward model.")],
}


def neutralize(case, prompt):
    for old, new in NEUTRALIZE.get(case, []):
        assert old in prompt, \
            "NEUTRALIZE: expected directive not found in %s system prompt: %r" % (case, old)
        prompt = prompt.replace(old, new)
    return prompt


def canned(tool, args):
    """Generic SUCCESS, with converged/terminal messages so the agent stops."""
    if tool in ("run_bayesian_optimization", "run_differential_evolution",
                "run_nelder_mead", "run_random_bo"):
        return ("SUCCESS: optimization converged. Best RMSE 4.95 MPa, MAPE 2.85% in 26 "
                "evaluations. Calibrated parameters written to workdir/best_params.json.")
    if tool in ("run_bayesian_texture_inverse", "run_random_texture_inverse"):
        return ("SUCCESS: inverse search complete. Best candidate is a near-random initial "
                "texture (loss 0.26); log written to workdir/inverse_log.csv.")
    if tool == "generate_microstructure":
        return "SUCCESS: microstructure generated (matlab/input_structure_poly.h5)."
    if tool == "convert_hdf5_to_prisms":
        return "SUCCESS: converted to grainID.txt/orientations.txt; prm.prm voxel dims updated."
    return "SUCCESS."


def load_harness(case):
    cfg = CASES[case]
    d = cfg["dir"]
    for p in (d, os.path.join(d, "tools"), os.path.join(d, "agents")):
        if p not in sys.path:
            sys.path.insert(0, p)
    pm = importlib.import_module(cfg["prompt_module"])
    sm = importlib.import_module(cfg["schema_module"])
    system_prompt = neutralize(case, pm.SYSTEM_PROMPT)
    return system_prompt, sm.TOOL_SCHEMAS


def episode(client, model, system_prompt, schemas, query):
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": query}]
    actions = []          # list of (tool_name, arguments_str, thought)
    for _ in range(MAX_ITERATIONS):
        resp = client.chat.completions.create(
            model=model, messages=messages, tools=schemas,
            tool_choice="auto", temperature=0.1, max_tokens=1024)
        msg = resp.choices[0].message
        thought = msg.content or ""
        if resp.choices[0].finish_reason == "stop" or not msg.tool_calls:
            actions.append(("<final>", "", thought))
            break
        messages.append({"role": "assistant", "content": msg.content,
                         "tool_calls": [{"id": tc.id, "type": "function",
                                         "function": {"name": tc.function.name,
                                                      "arguments": tc.function.arguments}}
                                        for tc in msg.tool_calls]})
        for tc in msg.tool_calls:
            name = tc.function.name
            args = tc.function.arguments or ""
            actions.append((name, args, thought))
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": canned(name, args)})
            thought = ""
    return actions


def _arg_int(args, key):
    try:
        v = json.loads(args).get(key)
        return int(v) if v is not None else None
    except Exception:
        m = re.search(r"%s\D{0,8}(\d{1,4})" % key, (args or "").lower())
        return int(m.group(1)) if m else None


def extract_decision(case, actions):
    if case == "1a":
        opts = CASES["1a"]["optimizers"]
        for name, args, thought in actions:
            if name in opts:
                return {"optimizer": name, "rationale": (thought or "").strip()}
        return {"optimizer": None, "rationale": ""}
    if case == "1b":
        strats = CASES["1b"]["strategies"]
        for name, args, thought in actions:
            if name in strats:
                return {"strategy": name, "budget": _arg_int(args, "n_evaluations"),
                        "rationale": (thought or "").strip()}
        return {"strategy": None, "budget": None, "rationale": ""}
    return {}


def format_trace(case, query, actions):
    out = ["=" * 74, "Experiment 1 %s trace" % case, "=" * 74,
           "QUERY: " + query, "-" * 74]
    for name, args, thought in actions:
        if thought:
            out.append("")
            out.append("Thought: " + thought.strip())
        if name != "<final>":
            out.append("  Action: %s%s" % (name, ("  args=" + args) if args else ""))
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Experiment 1 (1a/1b): less-prescribed autonomy (dry run).")
    ap.add_argument("--case", choices=["1a", "1b"], required=True)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--model", type=str, default=os.environ.get("EXP1_MODEL", "gpt-4o"))
    args = ap.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set."); sys.exit(1)

    cfg = CASES[args.case]
    query = open(os.path.join(HERE, cfg["prompt_file"]), encoding="utf-8").read().strip()
    system_prompt, schemas = load_harness(args.case)
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 70)
    print("EXP1 %s  model=%s  n=%d  dir=%s" % (args.case, args.model, args.n, cfg["dir"]))
    print("=" * 70)

    results = []
    logf = open(os.path.join(HERE, "exp1_%s_%s.log" % (args.case, stamp)), "w", encoding="utf-8")
    logf.write("QUERY: %s\n%s\n" % (query, "=" * 70))
    first_trace = None
    for i in range(1, args.n + 1):
        actions = episode(client, args.model, system_prompt, schemas, query)
        dec = extract_decision(args.case, actions)
        results.append(dec)
        if first_trace is None:
            first_trace = format_trace(args.case, query, actions)
        seq = " -> ".join(a[0] for a in actions if a[0] != "<final>")
        line = "run %2d: %s | seq: %s" % (i, json.dumps({k: v for k, v in dec.items() if k != "rationale"}), seq)
        print(line)
        logf.write(line + "\n")
        if dec.get("rationale"):
            logf.write("        rationale: %s\n" % dec["rationale"].replace("\n", " "))
    logf.close()

    with open(os.path.join(HERE, "exp1_%s_%s_trace.txt" % (args.case, stamp)), "w", encoding="utf-8") as f:
        f.write(first_trace + "\n")

    print("-" * 70)
    if args.case == "1a":
        c = Counter(r["optimizer"] for r in results)
        print("Optimizer chosen (n=%d): %s" % (args.n, dict(c)))
    elif args.case == "1b":
        c = Counter(r["strategy"] for r in results)
        budgets = [r["budget"] for r in results if r["budget"] is not None]
        print("Strategy chosen (n=%d): %s" % (args.n, dict(c)))
        print("Budgets (n_evaluations) observed: %s" % budgets)
        if budgets:
            budgets_sorted = sorted(budgets)
            med = budgets_sorted[len(budgets_sorted) // 2]
            print("  budget min/median/max: %d / %d / %d" % (min(budgets), med, max(budgets)))

    # machine-readable summary
    summ = {"case": args.case, "n": args.n, "model": args.model, "results": results}
    with open(os.path.join(HERE, "exp1_%s_%s_summary.json" % (args.case, stamp)), "w", encoding="utf-8") as f:
        json.dump(summ, f, indent=2)


if __name__ == "__main__":
    main()
