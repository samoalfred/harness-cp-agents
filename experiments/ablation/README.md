# CS2 Tool-Description Ablation (Reviewer point B1)

Tests whether the agent recovers the correct CS2 execution order from the
**prerequisite information in the tool descriptions**, by removing that
information and measuring how sequencing degrades.

## What is held constant vs varied

| Element | Setting |
|---|---|
| System prompt | **Minimal, goal-only** (paper §2.3) — lists tools, states no workflow. Identical in both conditions. |
| User query | Identical in both conditions. Carries scientific intent (which case, do-not-regenerate) but **not** the step order. |
| Tool descriptions | **The only variable.** FULL keeps prerequisites; ABLATED strips them. |

FULL = `tool_schemas_full.py` (verbatim from `CS2_Texture_Evolution/tools/react_tools.py`).
ABLATED = `tool_schemas_ablated.py` (same names + parameter schemas; prerequisite/
ordering/output-chaining clauses removed).

## Dry run

Tools are **not executed**. Each returns a canned `SUCCESS` observation so the
agent walks the whole pipeline in seconds. Observations are **always SUCCESS**
(never FAILED), so the environment never teaches the order through a failure —
the recovered order reflects the agent's reasoning from descriptions alone.
Nothing in the real `CS2_Texture_Evolution` folder is touched or run.

## Correct-sequence rubric

A run is **fully correct** iff all five productive tools are present with
`run_simulation` → `extract_post_orientations` → `generate_pole_figures` →
`create_comparison_figure`, `compare_stress_strain` after `run_simulation`, and
**no** unnecessary `inject`/`generate_microstructure`/`convert` calls (the query
forbids them). Ordering-only and unnecessary-call counts are reported separately.

## Run

```bash
export OPENAI_API_KEY='sk-...'
python3.7 run_ablation.py --n 20            # both conditions, 20 reps each
```

Prints a per-run trace and a paper-ready summary; writes `ablation_log_<stamp>.txt`.

## Expected reporting (fill in with measured numbers)

> With full descriptions, the agent produced the correct execution order in
> X/20 runs; with prerequisites removed, Y/20, instead exhibiting
> [out-of-order conversion / premature pole-figure calls / …]. This confirms the
> ordering knowledge resides in the tool descriptions rather than in the LLM's
> prior or the system prompt.
