# -*- coding: utf-8 -*-
"""
run_exp1c.py  --  Experiment 1c: less-prescribed autonomy, CS4 chaining.

Tests whether the tasks are over-prescribed, for the multi-pass case: given only
the goal (and the fact that the reference applies five passes), does the agent infer
the chained workflow on its own -- call run_pass sequentially 1..5, carry the deformed
orientations forward (the tool does this automatically), place the pass-1 mechanical
comparison after pass 1, and the texture analysis / final-texture comparison after
pass 5?

DRY RUN: no CP-FEM is launched. Each tool returns a canned SUCCESS so the agent walks
the workflow in seconds; we log the pass sequence and where the comparisons land.

DISCLOSED HARNESS MODIFICATION (neutralized directive):
  The deployed run_pass tool DESCRIPTION contains an explicit directive that prescribes
  exactly the behaviour under test:
     "You must therefore call this tool once per pass, IN ORDER, from pass 1 to pass 5
      (config N_PASSES)."
  Leaving it in would make the chaining a rule-follow, not an inference. This driver
  removes ONLY that one sentence from a COPY of the tool schema, and keeps the honest
  affordance that lets the agent reason the chain out for itself:
     "...each later pass AUTOMATICALLY starts from the deformed orientations produced by
      the previous pass (the tool saves that pass's texture and prepares the next pass's
      input)."
  The removal is asserted (NEUTRALIZE_RUN_PASS), so if the deployed description ever
  changes the run aborts loudly. The edit is on an in-memory copy; nothing is written
  back to the case folder (it is imported read-only).

Usage (inside WSL):
    export OPENAI_API_KEY='sk-...'
    python3.7 run_exp1c.py --n 5
"""

import os
import sys
import re
import json
import copy
import argparse
import datetime
import importlib

from openai import OpenAI

HERE = os.path.dirname(os.path.abspath(__file__))
HCP = os.environ.get("CP_AGENTS_HCP",
                     os.path.expanduser("~/candi/plasticity/applications/crystalPlasticity/hcp"))
CS4 = os.environ.get("EXP1_CS4_DIR", os.path.join(HCP, "CS4_ZX31_1728grains"))
MAX_ITERATIONS = 40
N_PASSES = 5

# Directive sentence removed from the run_pass description (kept honest affordance).
NEUTRALIZE_RUN_PASS = (
    " You must therefore call this tool once per pass, IN ORDER, from pass 1 to pass 5 "
    "(config N_PASSES).")


def canned(tool, args):
    if tool == "run_pass":
        p = None
        try:
            p = int(json.loads(args).get("pass_number"))
        except Exception:
            m = re.search(r"\d+", args or "")
            p = int(m.group(0)) if m else None
        tail = "next-pass input prepared." if (p is None or p < N_PASSES) else "final pass complete."
        return ("SUCCESS: pass %s complete. plane-strain flow stress (sigma_yy - sigma_zz) "
                "recorded and the deformed texture saved; %s" % (p, tail))
    if tool == "compare_stress_strain":
        return "SUCCESS: pass-1 flow stress vs reference RMSE 0.26 MPa, MAPE 0.16% over 0-20% strain."
    if tool == "analyze_texture_evolution":
        return "SUCCESS: (0001) basal peak intensity 2.10 -> 5.66 MRD over passes 1-5."
    if tool == "compare_final_texture":
        return "SUCCESS: final (pass-5) texture compared to reference 5-pass sim and experiment; figure saved."
    return "SUCCESS."


def load_harness():
    for p in (CS4, os.path.join(CS4, "tools"), os.path.join(CS4, "agents")):
        if p not in sys.path:
            sys.path.insert(0, p)
    ra = importlib.import_module("agents.react_agent")
    rt = importlib.import_module("tools.react_tools")
    schemas = copy.deepcopy(rt.TOOL_SCHEMAS)
    hit = False
    for t in schemas:
        f = t["function"]
        if f["name"] == "run_pass":
            assert NEUTRALIZE_RUN_PASS in f["description"], \
                "NEUTRALIZE: run_pass directive sentence not found; description changed?"
            f["description"] = f["description"].replace(NEUTRALIZE_RUN_PASS, "")
            hit = True
    assert hit, "NEUTRALIZE: run_pass tool not found in CS4 schemas."
    return ra.SYSTEM_PROMPT, schemas


def episode(client, model, system_prompt, schemas, query):
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": query}]
    actions = []
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


def extract_decision(actions):
    calls = [(n, a) for (n, a, _t) in actions if n != "<final>"]
    names = [n for n, _a in calls]
    passes = []
    for n, a in calls:
        if n == "run_pass":
            m = re.search(r"\d+", a or "")
            passes.append(int(m.group(0)) if m else None)

    def first_idx(name):
        return names.index(name) if name in names else None

    idx_p1 = None
    for i, (n, a) in enumerate(calls):
        if n == "run_pass":
            m = re.search(r"\d+", a or "")
            if m and int(m.group(0)) == 1:
                idx_p1 = i
                break
    idx_p5_last = None
    for i, (n, a) in enumerate(calls):
        if n == "run_pass":
            m = re.search(r"\d+", a or "")
            if m and int(m.group(0)) == N_PASSES:
                idx_p5_last = i
    idx_cmp = first_idx("compare_stress_strain")
    idx_ana = first_idx("analyze_texture_evolution")
    idx_fin = first_idx("compare_final_texture")

    ordered = passes == list(range(1, N_PASSES + 1))
    compared_after_pass1 = (idx_cmp is not None and idx_p1 is not None and idx_cmp > idx_p1)
    analysed_after_pass5 = (idx_p5_last is not None and
                            ((idx_ana is not None and idx_ana > idx_p5_last) or
                             (idx_fin is not None and idx_fin > idx_p5_last)))
    return {"pass_sequence": passes, "ordered_1to5": ordered,
            "n_passes": len([p for p in passes if p is not None]),
            "compared_after_pass1": compared_after_pass1,
            "analysed_after_pass5": analysed_after_pass5,
            "did_compare_stress_strain": idx_cmp is not None,
            "did_analyze_texture": idx_ana is not None,
            "did_compare_final": idx_fin is not None}


def format_trace(query, actions):
    out = ["=" * 74, "Experiment 1c (CS4 chaining) trace", "=" * 74,
           "QUERY: " + query, "-" * 74]
    for name, args, thought in actions:
        if thought:
            out.append("")
            out.append("Thought: " + thought.strip())
        if name != "<final>":
            out.append("  Action: %s%s" % (name, ("  args=" + args) if args else ""))
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Experiment 1c: CS4 autonomous chaining (dry run).")
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--model", type=str, default=os.environ.get("EXP1_MODEL", "gpt-4o"))
    args = ap.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set."); sys.exit(1)

    query = open(os.path.join(HERE, "prompt_1c_cs4_chaining.txt"), encoding="utf-8").read().strip()
    system_prompt, schemas = load_harness()
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 70)
    print("EXP1c  model=%s  n=%d  dir=%s" % (args.model, args.n, CS4))
    print("=" * 70)

    results = []
    logf = open(os.path.join(HERE, "exp1c_%s.log" % stamp), "w", encoding="utf-8")
    logf.write("QUERY: %s\n%s\n" % (query, "=" * 70))
    first_trace = None
    for i in range(1, args.n + 1):
        actions = episode(client, args.model, system_prompt, schemas, query)
        dec = extract_decision(actions)
        results.append(dec)
        if first_trace is None:
            first_trace = format_trace(query, actions)
        line = "run %2d: passes=%s ordered=%s cmp@1=%s ana@5=%s" % (
            i, dec["pass_sequence"], dec["ordered_1to5"],
            dec["compared_after_pass1"], dec["analysed_after_pass5"])
        print(line); logf.write(line + "\n")
    logf.close()

    with open(os.path.join(HERE, "exp1c_%s_trace.txt" % stamp), "w", encoding="utf-8") as f:
        f.write(first_trace + "\n")
    with open(os.path.join(HERE, "exp1c_%s_summary.json" % stamp), "w", encoding="utf-8") as f:
        json.dump({"n": args.n, "model": args.model, "results": results}, f, indent=2)

    ok = sum(1 for r in results if r["ordered_1to5"])
    cmp1 = sum(1 for r in results if r["compared_after_pass1"])
    ana5 = sum(1 for r in results if r["analysed_after_pass5"])
    print("-" * 70)
    print("Chained passes 1..%d in order:   %d/%d" % (N_PASSES, ok, args.n))
    print("Compared after pass 1:          %d/%d" % (cmp1, args.n))
    print("Analysed/compared after pass 5: %d/%d" % (ana5, args.n))


if __name__ == "__main__":
    main()
