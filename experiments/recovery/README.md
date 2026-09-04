# CS2 Induced Error-Recovery Trace (Reviewer point B3)

Demonstrates the agent **diagnosing a tool failure and recovering** — the
adaptive behavior claimed in §2.1 but not previously shown in a trace.

Uses the **genuine CS2 harness** (real system prompt + real full tool schemas
imported from `CS2_Texture_Evolution`). A stateful dry-run executor injects one
controlled failure; the failure observation carries a diagnostic; the agent must
read it, reason, and act. Nothing in the production CS2 folder is touched.

## Scenarios

| `--scenario` | Failure | Expected recovery |
|---|---|---|
| `transient` (default) | `run_simulation` fails once (transient I/O timeout), succeeds on retry | re-run |
| `needs_convert` | `run_simulation` fails (voxel-dim / input mismatch) until `convert_hdf5_to_prisms` is called | **diagnose → convert → re-run** (richest trace) |
| `missing_ref` | `compare_stress_strain` fails once (reference CSV not found), succeeds on retry | retry |

`needs_convert` is the strongest demonstration: the diagnostic points to a
corrective action the agent must infer, and it must override the prompt's
"do not convert" default in light of solver evidence — genuine diagnostic
reasoning, not a blind retry.

## Run

```bash
export OPENAI_API_KEY='sk-...'
python3.7 run_recovery.py --scenario needs_convert --n 5
python3.7 run_recovery.py --scenario transient          # reliable fallback
```

Runs `n` episodes, reports recovery rate, and saves the first clean recovery
trace (full Thought / Action / Observation, failure step marked) to
`recovery_trace_<scenario>_<stamp>.txt` for the Supplementary Material.

## Reporting (fill from the saved trace)

> To demonstrate autonomous error recovery, a controlled failure was injected:
> [describe]. The agent read the diagnostic observation, [reasoned about the
> cause], and [corrective action], after which the pipeline completed. Recovery
> occurred in k of n episodes. The full trace is given in Section S[x].
