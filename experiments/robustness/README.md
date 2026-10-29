# Experiment 3 - scripted-vs-agent robustness (Revision R1)

Answers Reviewer R1 (distinction from scripted automation) and R5 (more demanding
robustness tests). **Dry-run: no CP-FEM is launched.** It imports the GENUINE CS2
harness (`SYSTEM_PROMPT`, `TOOL_SCHEMAS` from `../CS2_Texture_Evolution`) and injects
one controlled fault per scenario, running BOTH a fixed hard-coded script and the agent.

Nothing in `CS2_Texture_Evolution` is written to - the harness is only imported (read).

## To run (inside WSL)
```bash
cd /home/samoalfred/candi/plasticity/applications/crystalPlasticity/fcc/R1_Exp3_Robustness
export OPENAI_API_KEY='sk-...'
python3.7 run_robustness.py --scenario all --n 5
```
Or use the wrapper (reads the key from exp.env if present):
```bash
./run_exp3.sh
```

## Scenarios
- `needs_convert`   - missing prerequisite (run_simulation fails until convert_hdf5_to_prisms is called).
- `missing_input`   - microstructure + PRISMS input both absent; agent must infer generate -> convert -> run.
- `conflicting_constraint` - requested 0-3.5 MRD scale vs a reference on 0-2.5 MRD; the script emits a
  mismatched comparison, the agent must detect and resolve it.

## Expected result (script is deterministic; agent needs the API key)
| Scenario | Fixed script | Agent |
|---|---|---|
| needs_convert | HARD_FAIL (halts at run_simulation) | recovers |
| missing_input | HARD_FAIL (halts at run_simulation) | recovers via generate -> convert -> run |
| conflicting_constraint | SILENT_MISMATCH (ignores scale conflict) | detects + resolves |

## Outputs
- Console: the paper-ready summary table (script outcome vs agent resolved k/n).
- `robustness_trace_<scenario>_<stamp>.txt` - one example agent recovery trace per scenario (for the SI).

## Notes
- Model defaults to `gpt-4o` (override with `--model` or `ROBUSTNESS_MODEL`); temp 0.1.
- The `conflicting_constraint` "resolved" check is a heuristic (a corrective tool call after the
  conflict, or an explicit mention of scale/MRD/mismatch/conflict in the final answer). Spot-check
  the saved trace before quoting the rate.
