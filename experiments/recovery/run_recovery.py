# -*- coding: utf-8 -*-
"""
run_recovery.py  --  Reviewer point #5 induced error-recovery trace (B3).

Demonstrates the agent DIAGNOSING a tool failure and RECOVERING, using the
GENUINE CS2 harness (real system prompt + real full tool schemas imported from
CS2_Texture_Evolution). Execution is a stateful DRY RUN: no real simulation is
launched. One tool is made to fail in a controlled way; the failure observation
carries a diagnostic; the agent must read it, reason, and take corrective action.
The complete Thought / Action / Observation trace is logged for the Supplementary
Material. Nothing in the production CS2 folder is modified.

Scenarios (--scenario):
  transient      run_simulation FAILS once (transient I/O timeout), then SUCCEEDS
                 on retry. Recovery = re-run. Most reliable clean trace.
  needs_convert  run_simulation FAILS with a diagnostic (voxel-dim / input
                 mismatch) until convert_hdf5_to_prisms is called, then SUCCEEDS.
                 Recovery = diagnose -> call convert -> re-run. Richest trace
                 (diagnostic-driven corrective action, not a blind retry).
  missing_ref    compare_stress_strain FAILS once (reference CSV not found), then
                 SUCCEEDS on retry.

Usage:
    export OPENAI_API_KEY='sk-...'
    python3.7 run_recovery.py --scenario needs_convert --n 5
    python3.7 run_recovery.py --scenario transient
"""

import os
import sys
import json
import argparse
import datetime
import importlib

from openai import OpenAI

# Base directory holding the case-study folders. Override with the
# CP_AGENTS_FCC environment variable to point at your local checkout.
FCC = os.environ.get(
    "CP_AGENTS_FCC",
    "/home/samoalfred/candi/plasticity/applications/crystalPlasticity/fcc")
CS2 = os.path.join(FCC, "CS2_Texture_Evolution")
MAX_ITERATIONS = 25

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


class RecoveryExecutor(object):
    """Stateful dry-run executor that injects one controlled failure."""

    def __init__(self, scenario):
        self.scenario = scenario
        self.called = {}                 # tool -> count (before this call)
        self.failure_hit = False
        self.recovered = False

    def observe(self, tool):
        n_prev = self.called.get(tool, 0)
        self.called[tool] = n_prev + 1

        if self.scenario == "transient" and tool == "run_simulation":
            if n_prev == 0:
                self.failure_hit = True
                return ("FAILED: PRISMS solver terminated early (transient I/O "
                        "timeout while writing results/). No output files were "
                        "produced. This condition is typically transient; "
                        "re-running the simulation with the same configuration "
                        "usually succeeds."), True
            else:
                self.recovered = True
                return CANNED[tool], False

        if self.scenario == "needs_convert" and tool == "run_simulation":
            if self.called.get("convert_hdf5_to_prisms", 0) == 0:
                self.failure_hit = True
                return ("FAILED: PRISMS aborted. grainID.txt / orientations.txt "
                        "are missing or the voxel dimensions in prm.prm do not "
                        "match the microstructure. The microstructure must be "
                        "converted to PRISMS input (grainID.txt, orientations.txt, "
                        "prm.prm voxel dims) before the solver can run."), True
            else:
                if self.failure_hit:
                    self.recovered = True
                return CANNED[tool], False

        if self.scenario == "missing_ref" and tool == "compare_stress_strain":
            if n_prev == 0:
                self.failure_hit = True
                return ("FAILED: reference curve file 'Yaghoobi et al. (2022).csv' "
                        "could not be opened for reading. Verify the file is "
                        "present in the working directory, then retry the "
                        "comparison."), True
            else:
                self.recovered = True
                return CANNED[tool], False

        return CANNED.get(tool, "SUCCESS."), False


def load_cs2():
    for p in (CS2, os.path.join(CS2, "tools"), os.path.join(CS2, "agents")):
        if p not in sys.path:
            sys.path.insert(0, p)
    ra = importlib.import_module("agents.react_agent")
    rt = importlib.import_module("tools.react_tools")
    return ra.SYSTEM_PROMPT, rt.TOOL_SCHEMAS


def run_episode(client, model, system_prompt, schemas, scenario):
    execu = RecoveryExecutor(scenario)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": CS2_QUERY},
    ]
    trace = []
    terminated = False
    for it in range(1, MAX_ITERATIONS + 1):
        resp = client.chat.completions.create(
            model=model, messages=messages, tools=schemas,
            tool_choice="auto", temperature=0.1, max_tokens=1024)
        msg = resp.choices[0].message
        thought = msg.content or ""
        if resp.choices[0].finish_reason == "stop" or not msg.tool_calls:
            trace.append({"iter": it, "thought": thought, "action": None,
                          "observation": None, "failed": False})
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
            obs, failed = execu.observe(name)
            trace.append({"iter": it, "thought": thought, "action": name,
                          "observation": obs, "failed": failed})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": obs})
            thought = ""   # attribute the thought to the first call only
    return trace, execu.failure_hit, execu.recovered, terminated


def format_trace(trace, scenario, failure_hit, recovered, terminated):
    lines = []
    lines.append("=" * 74)
    lines.append("CS2 induced error-recovery trace  |  scenario = %s" % scenario)
    lines.append("failure injected: %s | recovered: %s | terminated: %s"
                 % (failure_hit, recovered, terminated))
    lines.append("=" * 74)
    for step in trace:
        if step["thought"]:
            lines.append("")
            lines.append("[Iteration %d] Thought: %s" % (step["iter"], step["thought"].strip()))
        if step["action"]:
            lines.append("    Action: %s" % step["action"])
            tag = "  <-- INDUCED FAILURE" if step["failed"] else ""
            lines.append("    Observation: %s%s" % (step["observation"], tag))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="CS2 induced error-recovery (B3).")
    ap.add_argument("--scenario", choices=["transient", "needs_convert", "missing_ref"],
                    default="transient")
    ap.add_argument("--n", type=int, default=5, help="episodes (for recovery rate)")
    ap.add_argument("--model", type=str, default=os.environ.get("RECOVERY_MODEL", "gpt-4o"))
    args = ap.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set.  export OPENAI_API_KEY='sk-...'")
        sys.exit(1)

    system_prompt, schemas = load_cs2()
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    here = os.path.dirname(os.path.abspath(__file__))
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 70)
    print("RECOVERY  scenario=%s  model=%s  n=%d" % (args.scenario, args.model, args.n))
    print("=" * 70)

    n_fail = n_recov = n_term = 0
    best_trace_text = None
    for i in range(1, args.n + 1):
        trace, failure_hit, recovered, terminated = run_episode(
            client, args.model, system_prompt, schemas, args.scenario)
        n_fail += int(failure_hit)
        n_recov += int(recovered)
        n_term += int(terminated)
        actions = [s["action"] for s in trace if s["action"]]
        print("episode %d: failure=%s recovered=%s terminated=%s | %s"
              % (i, failure_hit, recovered, terminated, " -> ".join(actions)))
        # keep the first clean recovery trace for the SI
        if recovered and terminated and best_trace_text is None:
            best_trace_text = format_trace(trace, args.scenario, failure_hit,
                                           recovered, terminated)

    if best_trace_text is None:  # fall back to the last trace
        best_trace_text = format_trace(trace, args.scenario, failure_hit,
                                       recovered, terminated)

    trace_path = os.path.join(here, "recovery_trace_%s_%s.txt" % (args.scenario, stamp))
    with open(trace_path, "w") as f:
        f.write(best_trace_text + "\n")

    print("-" * 70)
    print("failure injected %d/%d | recovered %d/%d | terminated %d/%d"
          % (n_fail, args.n, n_recov, args.n, n_term, args.n))
    print("SI trace saved: %s" % trace_path)
    print("\n----- SI TRACE PREVIEW -----")
    print(best_trace_text)


if __name__ == "__main__":
    main()
