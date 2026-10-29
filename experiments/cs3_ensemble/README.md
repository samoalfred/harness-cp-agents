# Experiment 2 - CS3 realization ensemble

Supplementary experiment repeating the CS3 inverse search over five random microstructure
realizations. This folder is a **full copy** of the CS3 harness (the original is not
modified); all experiment-specific code and outputs live here.

Claim: under the DIGITIZED Fig. 2c target the diffuse-[110]-vs-random separation lies
within realization noise, and under a SELF-CONSISTENT (same-kernel) target the random mode
is recovered - i.e. the separation is a measurement-footing artifact, not physics.

## New files (everything else is the untouched CS3 copy)
- `run_ensemble.py`   - Phase 1 orchestrator (sim-heavy). Sets the RNG seed, runs the genuine
                        Bayesian inverse search (budget 15) per seed, keeps each seed's log,
                        and archives every evaluation's deformed orientations.
- `rescore_ensemble.py` - Phase 2 (cheap, zero sims). Re-scores against a self-consistent target.
- `run_exp2.sh`       - wrapper.
- `ensemble/`         - outputs land here. `REFERENCE_seed0_digitized_log.csv` is the pre-existing
                        Sep-2 seed-0 run, kept for reference only.

## How it works (and why the second target is free)
`score_texture.py` computes six pole-figure features (peak + central MRD for {100},{110},{111})
from the deformed orientations - these are **target-independent**. The loss is a weighted sum of
squared differences of those features from a target's peak/central values. So re-scoring against a
different target is pure arithmetic. The six features are also logged each evaluation
(`p100,c100,...`), and Phase 1 additionally archives the full-precision orientations, so the
re-score is exact.

- **Digitized target**: `fig2c_targets.json` (values read off the published figure, +/- ~0.2 MRD).
- **Self-consistent target** `T_sc`: the mean of the ensemble's random-mode forward features
  (the model's own image of a random initial texture, same 8 deg kernel / 12 deg cap). Built
  automatically from the runs; needs >= 2 seeds to be a real ensemble mean.

## The only modification to the deployed pipeline
`run_ensemble.py` sets `rng_seed` in `matlab/microstructure_gen.m` to each seed in turn (the
parameter injector never touches that line), and monkeypatches `inverse_search.evaluate` at
runtime to copy each evaluation's orientations into `ensemble/seed<seed>/orientations/`.
`inverse_search.py` itself is left byte-identical to the deployed version. `final_rerun` is off
(the converged full-substep re-run of the optimum is not needed here).

## To run (inside WSL; MATLAB + PRISMS available; NO OpenAI key)
```bash
cd /home/samoalfred/candi/plasticity/applications/crystalPlasticity/fcc/R1_Exp2_CS3_Ensemble
python3.7 run_ensemble.py                 # seeds 0..4, budget 15  (= 75 forward runs)
# subset / resume:
python3.7 run_ensemble.py --seeds 2 3 4
# rebuild tables without simulating (after Phase 1, or to retune T_sc):
python3.7 run_ensemble.py --rescore-only
```
Cost: 75 forward runs for the full ensemble (CS3 uses 30 Taylor substeps, so each is cheap);
parallelizable by running seed subsets. The second target adds zero simulations.

Tip: to save 15 runs you may reuse the existing seed-0 data - copy
`ensemble/REFERENCE_seed0_digitized_log.csv` to `ensemble/log_seed0.csv` and run with
`--seeds 1 2 3 4`. (The reference run has no archived per-eval orientations, so seed 0 would then
re-score from 2-decimal logged features - fine for the digitized gap, slightly less precise for
the self-consistent argmin. For a uniformly exact ensemble, run all five fresh.)

## Outputs
- `ensemble/log_seed<seed>.csv`              - each realization's full evaluation log.
- `ensemble/seed<seed>/orientations/ori_eval_NN.csv` - archived per-eval orientations.
- `ensemble/ensemble_summary.csv` / `.json`  - per-realization gap + self-consistent optimum.
- Console: the paper-ready table (seed x {random, best[110], gap; self-consistent argmin}) and the
  two aggregates: digitized gap mean +/- std, and the k/M fraction where random is optimal under T_sc.

## Verified so far (no sims yet)
- Re-score reproduces the logged digitized loss from features (exact with archived orientations;
  ~0.04 rounding with 2-decimal logged features only).
- `compute_features` runs in this env; the seed and archiver plumbing are wired.
- On the reference seed-0 log: digitized gap (random - best[110]) = 0.306; random is the
  self-consistent optimum. Real conclusions require the full 5-seed run.
