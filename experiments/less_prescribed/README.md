# Less-prescribed autonomy tests

Tests of whether the agent makes a workflow decision on its own when the query no
longer states it. All runs are **dry runs**: no CP-FEM is launched, each tool returns a
fixed `SUCCESS` observation, and only the agent's decisions are recorded. GPT-4o,
temperature 0.1.

| Folder | Case | Decision under test | Result |
|---|---|---|---|
| [`cs1_cs3/`](cs1_cs3/) (1a) | CS1 calibration | which optimizer to call, with no optimizer named | Bayesian optimization in 10/10 runs |
| [`cs1_cs3/`](cs1_cs3/) (1b) | CS3 inverse texture | search strategy and evaluation budget, with neither given | Bayesian optimization, budget 15, in 10/10 runs |
| [`cs4/`](cs4/) (1c) | CS4 multi-pass | chaining the five passes, with the ordering instruction removed from the query and the `run_pass` description | passes 1→5 in order in 5/5 runs |

Each subfolder contains the driver script, the exact query used (`prompt_*.txt`), the
per-run log, a JSON summary of all runs, and a full Thought/Action trace of the first run.
The harness modifications made for each test (removal of default directives from the
system prompt or tool description) are disclosed in each subfolder's `README.md`.

The drivers import the deployed case-study harnesses from the author's local
checkout; set the paths at the top of each script to point at the corresponding
`case_study_*` folders in this repository.
