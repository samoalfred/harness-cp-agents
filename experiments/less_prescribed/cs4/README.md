# Experiment 1c - CS4 autonomous chaining

The multi-pass case of the less-prescribed test. Given only the goal (and the fact that the
reference applies five passes), does the agent infer the chained workflow on its own:
call `run_pass` sequentially 1..5, carry deformed orientations forward (the tool does this
automatically), place the pass-1 mechanical comparison after pass 1, and the texture
analysis / final-texture comparison after pass 5?

This is the CS4 (HCP) sub-test of Experiment 1; 1a/1b live in `fcc/R1_Exp1_LessPrescribed/`.

**Option A (dry-run only).** No CP-FEM is launched; each tool returns a canned SUCCESS and
we log the pass sequence and where the comparisons land. The claim is about planning/
chaining inference, not texture resolution, so the dry run is sufficient. (If you later want
one real end-to-end confirmation, run the genuine `run_pipeline.py` in CS4 at 512 grains with
this same query - that is the optional Option B, not required for the table.)

## Disclosed harness modification (neutralized directive)
The deployed `run_pass` tool description contains a directive prescribing exactly the
behaviour under test:
> "You must therefore call this tool once per pass, IN ORDER, from pass 1 to pass 5 (config N_PASSES)."

The driver removes ONLY that one sentence from an in-memory COPY of the tool schema and keeps
the honest affordance the agent can reason from:
> "...each later pass AUTOMATICALLY starts from the deformed orientations produced by the previous pass..."

The removal is asserted in `run_exp1c.py` (`NEUTRALIZE_RUN_PASS`); if the deployed description
changes, the run aborts loudly. Nothing is written back to `CS4_ZX31_1728grains` (read-only import).

## To run (inside WSL)
```bash
cd /home/samoalfred/candi/plasticity/applications/crystalPlasticity/hcp/R1_Exp1c_CS4_Chaining
export OPENAI_API_KEY='sk-...'
python3.7 run_exp1c.py --n 5
# or: ./run_exp1c.sh 5
```

## Outputs (timestamped)
- `exp1c_<stamp>.log`          - per-run pass sequence + placement flags.
- `exp1c_<stamp>_trace.txt`    - full Thought/Action trace of the first run (for the SI).
- `exp1c_<stamp>_summary.json` - machine-readable results (all runs).
- Console: chained 1..5 in order k/n; compared after pass 1 k/n; analysed after pass 5 k/n.

## Expected result (smoke-tested, n=1)
passes=[1,2,3,4,5], ordered=True, compared after pass 1=True, analysed after pass 5=True.
Model defaults to `gpt-4o` (temp 0.1).
