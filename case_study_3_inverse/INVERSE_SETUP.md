# CS3_Inverse_Problem — Case Study 3 (inverse texture, rate-dependent Taylor)

Created 2026-09-02. Copy of `Cu_REACT_Inverse2` with the forward model swapped
to the **rate-dependent Taylor** setup of CS2 (Yaghoobi et al. 2022, Application 1).

## Goal

Given a TARGET deformation texture (Fig. 2c of Yaghoobi et al. 2022, digitized in
`fig2c_targets.json`), search the INITIAL microstructure texture that, after
uniaxial compression along Z to true strain ~1.0, reproduces it. The agent is not
told the initial texture; the ground truth is a near-random initial texture (the
paper's Application 1 uses a random initial texture).

## What changed vs the original CS3 (Cu_REACT_Inverse2)

| Aspect | Old CS3 (rate-indep) | This CS3 (rate-dep Taylor) |
|---|---|---|
| Forward binary | `../../main` | `../../main_ratedep` |
| Model | rate-independent FEM | rate-dependent Taylor, m=77 |
| Loading | 40% compression, roller BCs (`BCinfo.txt`) | velocity-gradient BC to true strain ~1.0 |
| RVE | 65^3 voxels, refine 3 | 5x8x10 = 400 grains, one grain/voxel, refine 0 |
| Slip params | s0=16 h0=180 ss=135 a=2.25 | s0=16 h0=200 ss=129.5 a=2, q=1.4 |
| Target | Fig. 10 (2019), 0-2.5 MRD, `fig10_targets.json` | Fig. 2c (2022), 0-3.5 MRD, `fig2c_targets.json` |
| Substeps | n/a | 30 during search, 100 for the final re-run |

## Design (unchanged from CS3)

- Search: Bayesian optimization (GP + expected improvement, sklearn) over a pool.
- Budget: 15 evaluations.
- Design variables:
  - texture mode, categorical: {random, fiber[100], fiber[110], fiber[111]}.
    'random' is an explicit reachable state.
  - sigma_spread, continuous [3, 85] deg (initial fibre spread; ignored for random).
- Fixed: rate-dependent Taylor Cu params, compression to true strain ~1.0,
  400-grain equal-size RVE.

## Forward pipeline (each evaluation)

`param_injector.inject_microstructure_params` (writes orientation_type / fiber_dir
/ sigma_spread into `matlab/microstructure_gen.m`) -> `matlab_runner`
(MATLAB microstructure_gen -> `input_structure_poly.h5`) -> `h5_converter`
(`grainID.txt` + `orientations.txt`, updates Voxels in prm.prm) ->
`single_sim` (`../../main_ratedep prm.prm`) -> `texture_analysis.extract_orientations`
(cols 8-10 of the last `QuadratureOutputs` -> `matlab/orientations_post_deformation.csv`)
-> `score_texture.score` (vs `fig2c_targets.json`).

## Objective (`tools/score_texture.py`)

Pure-Python pole-figure scorer (no MATLAB). For each of {111},{100},{110}:
peak MRD and central MRD (mean within a 12 deg cap around Z), 8 deg kernel.
Loss = sum over pole figures of w*(0.5*dpeak^2 + dctr^2), with the {110} term
weighted x2 (the <110> compression fibre). Targets (digitized Fig. 2c, 0-3.5 MRD):

| {hkl} | peak target | central target |
|---|---|---|
| {111} | 2.5  | 0.3 (minimum) |
| {100} | 2.35 | 0.3 (minimum) |
| {110} | 3.5  | 3.3 (MAXIMUM = compression fibre) |

Validation: the CS2 random-start deformed texture scores loss 0.57 against this
target (a good match), confirming the random initial texture reproduces Fig. 2c.

Note (cross-footing caveat, same as CS2/old CS3): the target is digitized off the
MTEX-rendered Fig. 2c, while simulated features come from the Python scorer. The
scorer reads the random-start {110} central at ~2.9 vs the 3.3 target, so a mild
[110] pre-bias can lower the loss further — a measurement artefact, not evidence
of a physical [110] initial texture. This is discussed in the writeup.

## Agent wrapper (CS1 parity)

The LLM selects a search strategy from a repository and launches it (it does not
propose textures itself):
```
inverse_react.py            entry point (requires OPENAI_API_KEY)
agents/inverse_agent.py     ReAct agent (GPT-4o), selects the optimizer, interprets
tools/inverse_tools.py      run_bayesian_texture_inverse / run_random_texture_inverse
inverse_search.py           run_search(method, budget) -- the actual search
tools/score_texture.py      objective (deformed texture vs fig2c_targets.json)
```

## Run

Agent-driven (narrative parity with CS1):
```
cd ~/candi/plasticity/applications/crystalPlasticity/fcc/CS3_Inverse_Problem
export OPENAI_API_KEY='sk-...'
export LD_LIBRARY_PATH=$HOME/dealii-candi/symengine-0.8.1/lib:$LD_LIBRARY_PATH
python3.7 -u inverse_react.py 2>&1 | tee inverse_run.log
```

Optimizer only (no LLM):
```
python3.7 -u inverse_search.py bayesian 2>&1 | tee inverse_run.log   # or: random
```

Each forward run is a rate-dependent Taylor simulation (~9 min at 30 substeps, so
~2.3 h for 15). Watch `workdir/inverse_log.csv` and `workdir/best_texture.json`.

The recovered optimum is re-run AUTOMATICALLY at full 100 substeps at the end of
`run_search` (pass `final_rerun=False` to disable). The converged re-run writes
DEDICATED files and overwrites nothing the search produced -- not the per-eval
orientations, not the log, not best_texture.json -- and restores prm.prm to 30
substeps afterward:
  matlab/orientations_post_deformation_best100.csv   (authoritative optimum)
  workdir/best_texture_final100.json                 (its loss + features)
  matlab/figures/initial_texture_best.png, RVE_3D_best.png

`run_best.py` remains as a standalone way to re-run the optimum manually if needed.

Expected outcome: the search recovers mode=random (or a very diffuse fibre),
confirming a near-random initial texture reproduces Fig. 2c, with sharp and
mis-aligned initial textures decisively rejected.
