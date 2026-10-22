# Revision R1 experiments

Driver scripts for the additional experiments added during the first revision
(R1) of the CP-Agent manuscript. Each experiment reuses the unmodified case-study
harnesses in `../../case_study_*`; only the drivers, prompts, and run scripts are
included here. The OpenAI API key is read from the `OPENAI_API_KEY` environment
variable (no keys are stored in this repository).

| Folder | Experiment | Reviewer point |
|---|---|---|
| `exp1_less_prescribed/` | Less-prescribed autonomy: optimizer selection (CS1) and search strategy + budget (CS3) with the default-naming directives removed from the harness | R4 |
| `exp1c_cs4_chaining/` | Multi-pass chaining (CS4) with the explicit "run the passes in order" directive removed | R4 |
| `exp2_cs3_ensemble/` | CS3 inverse-search ensemble over five independent random-realization RVEs, re-scored against a shared self-consistent target | R8 |
| `exp3_robustness/` | Scripted-vs-agent robustness on three perturbed CS2 scenarios (missing prerequisite, missing input, conflicting constraint) | R1, R5 |

Each subfolder has its own README with the exact commands and expected output.
