# Experiment 1 (1a + 1b) - less-prescribed autonomy (Revision R1)

Answers Reviewer R4 ("tasks are too prescribed"): given ONLY the goal, the agent chooses
the decision the query previously stated for it. **Dry-run: no CP-FEM is launched** (each
tool returns a canned SUCCESS; we log only the decision and the agent's rationale).

1c (CS4 chaining) lives separately, in `hcp/R1_Exp1c_CS4_Chaining/`, because CS4 is HCP.

## Sub-tests
- **1a - optimizer selection (CS1).** The query no longer names an optimizer. Measures which
  of the four optimizer tools the agent calls, and its stated rationale.
- **1b - strategy + budget (CS3).** The query gives neither the search strategy nor a budget.
  Measures which strategy the agent calls and what `n_evaluations` (budget) it sets itself.

## Disclosed harness modification (neutralized default directive)
The deployed system prompts contain an explicit *default* directive that tells the agent which
optimizer/strategy to use when the query is silent:
- CS1: `"Use when the query asks for Bayesian Optimization or does not specify."`
- CS3: `"...Recommended for this expensive forward model. Use this unless the user explicitly asks for a naive baseline."`

Leaving these in would make the selection a rule-follow, not an inference. The driver removes
**only** those directive clauses (`-> "Use when the query asks for Bayesian Optimization."` and
`-> "...Recommended for this expensive forward model."`) and keeps every honest tool tradeoff
description (e.g. "most sample-efficient", "best for limited budgets"). The removals are
asserted in `run_exp1.py` (`NEUTRALIZE`), so if the deployed prompt ever changes the run aborts
loudly rather than testing the wrong thing. The edit is in memory only; nothing is written back
to the case folders (they are imported read-only).

## To run (inside WSL)
```bash
cd /home/samoalfred/candi/plasticity/applications/crystalPlasticity/fcc/R1_Exp1_LessPrescribed
export OPENAI_API_KEY='sk-...'
python3.7 run_exp1.py --case 1a --n 10
python3.7 run_exp1.py --case 1b --n 10
# or both at once:
./run_exp1.sh 10
```

## Outputs (per case, timestamped)
- `exp1_<case>_<stamp>.log`           - per-run decision + rationale.
- `exp1_<case>_<stamp>_trace.txt`     - full Thought/Action trace of the first run (for the SI).
- `exp1_<case>_<stamp>_summary.json`  - machine-readable results (all runs).
- Console: selection frequency (1a), and strategy + budget min/median/max (1b).

## Expected result (smoke-tested, n=1 each)
- 1a: selects `run_bayesian_optimization`, rationale "most sample-efficient ... for this calibration".
- 1b: selects `run_bayesian_texture_inverse`, sets `n_evaluations` ~= 15, rationale "most sample-efficient for this expensive forward model".

Model defaults to `gpt-4o` (temp 0.1); override with `--model` or `EXP1_MODEL`.
