# -*- coding: utf-8 -*-
"""
run_robustness.py  --  Experiment 3 (Revision R1): scripted-vs-agent robustness.

Head-to-head demonstration that a FIXED, hard-coded script fails (silently or by
halting) under perturbation, while the harness-engineered agent diagnoses and
recovers. Reuses the GENUINE CS2 harness (real system prompt + real tool schemas,
imported from CS2_Texture_Evolution) and the stateful DRY-RUN executor pattern of
run_recovery.py: no real simulation is launched; one controlled fault is injected
per scenario.

Three scenarios (--scenario):
  needs_convert          run_simulation FAILS until convert_hdf5_to_prisms is called
                         (missing prerequisite). Recovery = diagnose -> convert -> run.
  missing_input          run_simulation FAILS until BOTH generate_microstructure AND
                         convert_hdf5_to_prisms have run (microstructure + PRISMS input
                         absent). Recovery = infer the longer chain generate -> convert -> run.
  conflicting_constraint compare_stress_strain returns a CONFLICT warning (requested
                         0-3.5 MRD scale vs a reference on a 0-2.5 MRD scale). A fixed
                         script ignores it and emits a mismatched comparison; the agent
                         must detect the conflict and resolve it (re-plot on the matched
                         scale or explicitly flag the discrepancy).

For each scenario this runs BOTH:
  * the fixed SCRIPT baseline (deterministic; executes a hard-coded tool order and
    does not react to observations), and
  * the AGENT (n stochastic episodes),
then prints a comparison table and saves an example agent trace for the SI.

Usage (inside WSL):
    export OPENAI_API_KEY='sk-...'
    python3.7 run_robustness.py --scenario conflicting_constraint --n 5
    python3.7 run_robustness.py --scenario all --n 5
"""

import os
import sys
import argparse
import datetime
import importlib

from openai import OpenAI

FCC = os.environ.get(
    "CP_AGENTS_FCC",
    os.path.expanduser("~/candi/plasticity/applications/crystalPlasticity/fcc"))
CS2 = os.path.join(FCC, "CS2_Texture_Evolution")
MAX_ITERATIONS = 25

# The fixed "known-good" order a conventional script would hard-code for the
# pre-configured CS2 forward workflow. The script executes these blindly, in order,
# and does NOT branch on observations.
SCRIPT_ORDER = [
    "run_simulation",
    "extract_post_orientations",
    "generate_pole_figures",
    "create_comparison_figure",
    "compare_stress_strain",
]

CS2_QUERY = (
    "Perform the pre-configured CS2 forward validation of polycrystalline OFHC copper "
    "(rate-dependent Taylor model, uniaxial compression along Z to true strain ~1.0). "
    "Run the simulation, then compare the crystallographic texture ({111}, {100}, {110} "
    "pole figures on the fixed 0-3.5 MRD scale) against the reference figure, and compare "
    "the simulated von Mises equivalent stress against the reference curve, reporting RMSE "
    "and MAPE. Provide a brief physical interpretation."
)

CANNED = {
    "inject_simulation_parameters": "SUCCESS: Parameters written to prm.prm.",
    "generate_microstructure": "SUCCESS: New microstructure generated (input_structure_poly.h5).",
    "convert_hdf5_to_prisms": "SUCCESS: Converted to grainID.txt/orientations.txt; grid 5x8x10, 400 grains; prm.prm voxel dims updated.",
    "run_simulation": "SUCCESS: Simulation complete. Wrote results/stressstrain.txt and QuadratureOutputs099.csv.",
    "extract_post_orientations": "SUCCESS: Extracted post-deformation Rodrigues vectors. Saved matlab/orientations_post_deformation.csv.",
    "generate_pole_figures": "SUCCESS: Pre/post ODFs computed; {100},{110},{111} pole figures and tiles saved.",
    "create_comparison_figure": "SUCCESS: texture_comparison.png and texture_vs_paper.png saved.",
    "compare_stress_strain": "SUCCESS: RMSE 4.8 MPa, MAPE 1.8%. stress_strain_comparison.png saved.",
}

# status values returned by the executor
OK, FAILED, CONFLICT = "ok", "failed", "conflict"


class RobustnessExecutor(object):
    """Stateful dry-run executor that injects one controlled perturbation."""

    def __init__(self, scenario):
        self.scenario = scenario
        self.called = {}
        self.failure_hit = False
        self.recovered = False
        self.conflict_hit = False

    def observe(self, tool):
        n_prev = self.called.get(tool, 0)
        self.called[tool] = n_prev + 1

        if self.scenario == "needs_convert" and tool == "run_simulation":
            if self.called.get("convert_hdf5_to_prisms", 0) == 0:
                self.failure_hit = True
                return ("FAILED: PRISMS aborted. grainID.txt / orientations.txt are "
                        "missing or the voxel dimensions in prm.prm do not match the "
                        "microstructure. The microstructure must be converted to PRISMS "
                        "input before the solver can run."), FAILED
            if self.failure_hit:
                self.recovered = True
            return CANNED[tool], OK

        if self.scenario == "missing_input" and tool == "run_simulation":
            has_gen = self.called.get("generate_microstructure", 0) > 0
            has_conv = self.called.get("convert_hdf5_to_prisms", 0) > 0
            if not (has_gen and has_conv):
                self.failure_hit = True
                return ("FAILED: no microstructure found. input_structure_poly.h5 is "
                        "absent AND grainID.txt / orientations.txt are missing, so the "
                        "solver has no input. A microstructure must be generated and then "
                        "converted to PRISMS input before the simulation can run."), FAILED
            if self.failure_hit:
                self.recovered = True
            return CANNED[tool], OK

        if self.scenario == "conflicting_constraint" and tool == "compare_stress_strain":
            # soft conflict: not a hard failure, but a decision is required
            if n_prev == 0:
                self.conflict_hit = True
                return ("CONFLICT: the task requests the 0-3.5 MRD intensity scale, but the "
                        "provided reference figure 'Reference_Plot_figures.png' is on a 0-2.5 "
                        "MRD scale. Producing the comparison as-is would misalign the two on "
                        "different color scales. Resolve the scale before reporting, or state "
                        "the discrepancy explicitly."), CONFLICT
            return CANNED[tool], OK

        return CANNED.get(tool, "SUCCESS."), OK


# ----------------------------------------------------------------------------
# Fixed scripted baseline: executes SCRIPT_ORDER blindly, no branching.
# ----------------------------------------------------------------------------
def run_script_baseline(scenario, halt_on_fail=True):
    execu = RobustnessExecutor(scenario)
    steps = []
    outcome = "OK"
    for tool in SCRIPT_ORDER:
        obs, status = execu.observe(tool)
        steps.append((tool, status, obs))
        if status == FAILED:
            # A conventional hard-coded script crashes at the failed step.
            outcome = "HARD_FAIL (halted at %s)" % tool if halt_on_fail else "SILENT_WRONG"
            if halt_on_fail:
                break
        elif status == CONFLICT:
            # The script has no branch to resolve the conflict; it proceeds and emits
            # a mismatched comparison.
            outcome = "SILENT_MISMATCH (ignored scale conflict)"
    return outcome, steps


# ----------------------------------------------------------------------------
# Agent episode (same loop as run_recovery.py).
# ----------------------------------------------------------------------------
def load_cs2():
    for p in (CS2, os.path.join(CS2, "tools"), os.path.join(CS2, "agents")):
        if p not in sys.path:
            sys.path.insert(0, p)
    ra = importlib.import_module("agents.react_agent")
    rt = importlib.import_module("tools.react_tools")
    return ra.SYSTEM_PROMPT, rt.TOOL_SCHEMAS


def run_agent_episode(client, model, system_prompt, schemas, scenario):
    execu = RobustnessExecutor(scenario)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": CS2_QUERY},
    ]
    trace = []
    terminated = False
    conflict_addressed = False
    for it in range(1, MAX_ITERATIONS + 1):
        resp = client.chat.completions.create(
            model=model, messages=messages, tools=schemas,
            tool_choice="auto", temperature=0.1, max_tokens=1024)
        msg = resp.choices[0].message
        thought = msg.content or ""
        if resp.choices[0].finish_reason == "stop" or not msg.tool_calls:
            # heuristic: did the final answer acknowledge the scale conflict?
            if execu.conflict_hit and any(k in thought.lower()
                                          for k in ("scale", "mrd", "mismatch", "conflict")):
                conflict_addressed = True
            trace.append({"iter": it, "thought": thought, "action": None,
                          "observation": None, "status": None})
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
            obs, status = execu.observe(name)
            # heuristic: a corrective tool call AFTER a conflict counts as addressing it
            if execu.conflict_hit and name in ("generate_pole_figures", "create_comparison_figure"):
                conflict_addressed = True
            trace.append({"iter": it, "thought": thought, "action": name,
                          "observation": obs, "status": status})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": obs})
            thought = ""
    # define "resolved" per scenario
    if scenario == "conflicting_constraint":
        resolved = execu.conflict_hit and conflict_addressed
    else:
        resolved = execu.recovered
    return trace, execu, resolved, terminated


def format_trace(trace, scenario):
    lines = ["=" * 74, "CS2 robustness trace  |  scenario = %s" % scenario, "=" * 74]
    for s in trace:
        if s["thought"]:
            lines.append("")
            lines.append("[Iter %d] Thought: %s" % (s["iter"], s["thought"].strip()))
        if s["action"]:
            tag = {FAILED: "  <-- INDUCED FAILURE", CONFLICT: "  <-- INJECTED CONFLICT"}.get(s["status"], "")
            lines.append("    Action: %s" % s["action"])
            lines.append("    Observation: %s%s" % (s["observation"], tag))
    return "\n".join(lines)


SCENARIOS = ["needs_convert", "missing_input", "conflicting_constraint"]


def main():
    ap = argparse.ArgumentParser(description="Experiment 3: scripted-vs-agent robustness.")
    ap.add_argument("--scenario", choices=SCENARIOS + ["all"], default="all")
    ap.add_argument("--n", type=int, default=5, help="agent episodes per scenario")
    ap.add_argument("--model", type=str, default=os.environ.get("ROBUSTNESS_MODEL", "gpt-4o"))
    args = ap.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set.  export OPENAI_API_KEY='sk-...'")
        sys.exit(1)

    system_prompt, schemas = load_cs2()
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    here = os.path.dirname(os.path.abspath(__file__))
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    scenarios = SCENARIOS if args.scenario == "all" else [args.scenario]

    rows = []
    for sc in scenarios:
        script_outcome, _ = run_script_baseline(sc)
        n_resolved = n_term = 0
        example = None
        for i in range(1, args.n + 1):
            trace, execu, resolved, terminated = run_agent_episode(
                client, args.model, system_prompt, schemas, sc)
            n_resolved += int(resolved)
            n_term += int(terminated)
            if resolved and terminated and example is None:
                example = format_trace(trace, sc)
        if example is None:
            example = format_trace(trace, sc)
        trace_path = os.path.join(here, "robustness_trace_%s_%s.txt" % (sc, stamp))
        with open(trace_path, "w") as f:
            f.write(example + "\n")
        rows.append((sc, script_outcome, "%d/%d" % (n_resolved, args.n), trace_path))
        print("\n[%s] script: %s | agent resolved: %d/%d (trace: %s)"
              % (sc, script_outcome, n_resolved, args.n, os.path.basename(trace_path)))

    print("\n" + "=" * 78)
    print("SUMMARY (paper-ready)")
    print("=" * 78)
    print("%-24s %-34s %-12s" % ("Scenario", "Fixed script", "Agent (resolved)"))
    print("-" * 78)
    for sc, script_outcome, agent, _ in rows:
        print("%-24s %-34s %-12s" % (sc, script_outcome, agent))


if __name__ == "__main__":
    main()
