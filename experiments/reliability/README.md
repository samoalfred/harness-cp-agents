# Agent reliability (paper Section 3.5.1)

Measures run-to-run reliability of the agent for all three case studies using
each case's **genuine** deployed harness (its real system prompt and tool
schemas) and its real user query. Execution is a **dry run**: tools are not
actually run; each returns a canned `SUCCESS` observation so a full episode
completes in seconds. Each run records whether the agent (a) produced the correct
tool sequence and (b) terminated cleanly.

Because the three case-study folders reuse module names (`react_tools`,
`config_semi`), each case is imported in its **own process** — run one case per
invocation.

## Configure

Set `CP_AGENTS_FCC` to the directory that holds the three case-study folders
(`SS316L_Semi_LLM_React_MicroGen3`, `CS2_Texture_Evolution`,
`CS3_Inverse_Problem`); it defaults to the author's local path.

```bash
export OPENAI_API_KEY='sk-...'
export CP_AGENTS_FCC=/path/to/case/study/folders
python3.7 run_reliability.py --case CS1 --n 20
python3.7 run_reliability.py --case CS2 --n 20
python3.7 run_reliability.py --case CS3 --n 20
# or:  ./run_all.sh 20
```

## Result reported in the paper

20 runs per case, GPT-4o, temperature 0.1: **CS1 20/20, CS2 20/20, CS3 20/20**
correct tool sequence and clean termination.
