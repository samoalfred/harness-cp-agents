# Harness reliability and robustness experiments

Supporting experiments for **Section 3.6** of the paper. They characterize the
agent's run-to-run reliability and the robustness of its autonomous sequencing,
and demonstrate diagnostic error recovery. All three run in a **dry-run** mode
(tool calls return canned observations) so they complete in seconds and record
only the agent's *decisions* — no CP-FEM simulation is launched, and none of the
production case-study folders are modified.

These reliability runs cover the three repeated-run case studies (CS1–CS3), as in
the paper. CS4 (five chained rate-dependent passes) is excluded from the 20x
repeated-run study because a single execution is far more expensive; its end-to-end
result is reported as a single validated run in `case_study_4_multipass/`, and its
autonomous chaining is tested separately over five dry runs in
[`less_prescribed/cs4/`](less_prescribed/cs4/).

| Folder | Paper section | What it shows | Result |
|---|---|---|---|
| [`ablation/`](ablation/) | 3.6.2 Sequencing ablation | 2x2 over tool-name informativeness (descriptive vs opaque) x tool-description content (full vs prerequisites removed), minimal prompt and query held fixed | valid order in **20/20** runs in all four cells |
| [`reliability/`](reliability/) | 3.6.1 Reliability | correct sequence + clean termination over repeated runs, per case study, using each case's genuine prompt and schemas | **CS1 20/20, CS2 20/20, CS3 20/20** |
| [`robustness/`](robustness/) | 3.6.3 Error recovery | three CS2 fault scenarios (missing conversion, missing microstructure input, conflicting intensity-scale constraint) run on a hard-coded script and on the agent | script fails in all three; agent recovers in **5/5** repeats of each; one example trace per scenario |
| [`less_prescribed/`](less_prescribed/) | 3.5.3, 4.2 | the agent makes a decision the query no longer states: optimizer (CS1), strategy and budget (CS3), five-pass chaining (CS4) | Bayesian optimization **10/10** (CS1) and **10/10** with budget 15 (CS3); passes chained in order **5/5** (CS4) |
| [`cs3_ensemble/`](cs3_ensemble/) | 3.4.5 | CS3 inverse search repeated over five random microstructure realizations, scored against the digitized and a self-consistent target | random texture is the self-consistent optimum in **2/5** realizations |
| [`recovery/`](recovery/) | earlier version | original single-fault recovery test (superseded by `robustness/`) | failure injected **5/5**, recovered **5/5**; trace in `recovery/example_recovery_trace.txt` |

## Common setup

```bash
export OPENAI_API_KEY='sk-...'
# reliability/ and recovery/ import the real case-study harnesses; point them at
# your checkout (defaults to the author's local path):
export CP_AGENTS_FCC=/path/to/case/study/folders
```

The `ablation/` scripts are self-contained (they carry their own tool schemas)
and need no `CP_AGENTS_FCC`. Each folder has its own README with exact commands.

All experiments use GPT-4o at temperature 0.1, matching the paper.
