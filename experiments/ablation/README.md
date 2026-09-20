# CS2 Tool-Description Ablation (Reviewer point B1)

Tests whether the agent recovers the correct CS2 execution order from the
**prerequisite information in the tool descriptions**, by removing that
information and measuring how sequencing degrades.

> **Scenario note.** To isolate *ordering recovery* as cleanly as possible, this
> ablation fixes the microstructure as pre-provided, so the productive chain under
> test is `run_simulation` → `extract_post_orientations` → `generate_pole_figures`
> → `create_comparison_figure` (with `compare_stress_strain` after the run). This
> is a deliberately narrower setup than the main CS2 case study (which begins by
> generating the microstructure); here the microstructure-generation tools are held
> out so the experiment measures only the analysis-chain sequencing.

## What is held constant vs varied

| Element | Setting |
|---|---|
| System prompt | **Minimal, goal-only** (paper §2.3) — lists tools, states no workflow. Identical in both conditions. |
| User query | Identical in both conditions. Carries scientific intent (which case; microstructure treated as pre-provided for this scenario) but **not** the step order. |
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

The primary metric (as reported in the paper) is whether the emitted sequence
**respects every data dependency**: all five productive tools present with
`run_simulation` → `extract_post_orientations` → `generate_pole_figures` →
`create_comparison_figure`, and `compare_stress_strain` after `run_simulation`.
For completeness the scripts also report a stricter *fully-correct* count that
additionally requires no `inject`/`generate_microstructure`/`convert` calls (held
out in this scenario); the two counts are logged separately.

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
