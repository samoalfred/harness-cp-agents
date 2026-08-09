# Harness-Engineered LLM Agents for Crystal Plasticity Simulation

Code accompanying the paper:

> **[PAPER TITLE]**
> [Author names], *[Journal / preprint]*, [year]. [DOI / arXiv link]

A single **harness-engineered, ReAct-style LLM agent** that drives full crystal
plasticity finite element (CP-FEM) workflows from a one-sentence natural-language
goal. The *same* harness (system prompt + tool schemas + dispatcher + iteration
loop) is applied unchanged to three structurally different problems:

| | Case study | Material | Task |
|---|---|---|---|
| **CS1** | Parameter calibration | SS316L | Recover four Voce hardening parameters that fit an experimental tensile curve. The agent selects a numerical optimizer and delegates the search. |
| **CS2** | Forward validation | OFHC copper | With fixed parameters, run one compression simulation and validate the flow response and deformation texture against a published benchmark. |
| **CS3** | Inverse texture recovery | OFHC copper | Given a target deformation texture, search over the initial microstructural texture to reproduce it. |

Only the **tool set** and the **user query** change between case studies; the agent
architecture does not. See `docs/CS1_Map.png`, `CS2_Map.png`, `CS3_Map.png` for the
per-case pipeline structure.

---

## Repository structure

```
.
├── README.md
├── INSTALL.md                    # condensed quick-start
├── LICENSE
├── requirements.txt
├── CITATION.cff
├── check_environment.py          # environment smoke test (run this first)
├── case_study_1_calibration/     # CS1: SS316L Voce calibration
│   ├── calibrate_react.py        #   entry point
│   ├── config_semi.py            #   bounds, stopping criteria, paths, model
│   ├── agents/                   #   react_agent.py (ReAct loop)
│   ├── tools/                    #   optimizer_tools, sim_tools, prm_tools, matlab_runner, h5_converter, llm_client
│   ├── prm.prm                   #   PRISMS-Plasticity input template
│   ├── grainID.txt, orientations.txt, BCinfo.txt, ...   # example microstructure
│   └── SS316L_experiment.txt     #   reference tensile curve
├── case_study_2_forward/         # CS2: Cu forward validation
│   ├── run_pipeline.py           #   entry point
│   ├── config_semi.py, agents/, tools/
│   └── Cu_AnandKothari1996.csv   #   reference stress-strain data
├── case_study_3_inverse/         # CS3: Cu inverse texture recovery
│   ├── inverse_react.py          #   entry point (agent selects the strategy)
│   ├── inverse_search.py         #   Bayesian optimization over the initial texture
│   ├── config_semi.py, agents/, tools/
│   └── fig10_targets.json        #   digitized target pole-figure features
└── docs/                         # structure maps, pipeline diagram
```

Each `case_study_*` folder also contains a `matlab/` subfolder (MTEX scripts for
microstructure generation and pole figures) and a `workdir/` with small example
output logs (`optimization_results.csv`, `inverse_log.csv`, `best_*.json`).

> **Note.** These folders were assembled from the working directories
> `SS316L_Semi_LLM_React_MicroGen/`, `Cu_REACT_Investigation2/`, and
> `Cu_REACT_Inverse2/`, with the heavy run artifacts (`results/`, `*.vtu`,
> `QuadratureOutputs*.csv`, HDF5, generated figures) excluded per `.gitignore`;
> paths in each `config_semi.py` are relative, so the folders are self-contained.

---

## Requirements at a glance

The Python agent is only the **orchestrator**. The simulations it drives depend on
external software that must be installed separately. **All of the items below are
required; the agents cannot run end to end without every one of them.**

| # | Requirement | Cost | Needed for |
|---|---|---|---|
| 1 | **Linux or WSL** (developed on WSL Ubuntu 18.04) | free | running PRISMS-Plasticity, a Linux / deal.II code. **Native Windows without WSL will not work.** |
| 2 | **PRISMS-Plasticity**, built from source (needs **deal.II** + **SymEngine**) | free / open-source | the CP-FEM simulations (the `main` executable) |
| 3 | **MATLAB** (developed with R2025b) | **commercial — a valid MATLAB license is required** | synthetic microstructure generation and pole figures |
| 4 | **MTEX 6.0.0** MATLAB toolbox | free / open-source | crystallographic texture analysis inside MATLAB |
| 5 | **OpenAI API key** with **GPT-4o** access | paid (API usage is billed) | the LLM agent |
| 6 | **Python 3.7+** and the packages in `requirements.txt` | free | the agent and its Python tooling |

The detailed setup for each is below.

---

## Prerequisites (external tools)

These are **not** Python packages and must be installed separately.

1. **PRISMS-Plasticity** (the CP-FEM solver) — a **Linux / deal.II** code, so build
   and run it under **WSL (Ubuntu) or native Linux**, not on native Windows.
   Build the `main` executable from the crystal-plasticity application:
   <https://github.com/prisms-center/plasticity>. It depends on **deal.II** and
   **SymEngine**. Each case study invokes it as `../../main prm.prm`
   (`SIM_COMMAND` in `config_semi.py`); place the built binary accordingly or edit
   the path. At run time the shared libraries must be on the loader path, e.g.:
   ```bash
   export LD_LIBRARY_PATH=/path/to/dealii-candi/symengine-0.8.1/lib:$LD_LIBRARY_PATH
   ```

2. **MATLAB** (developed with R2025b). **MATLAB is commercial software and requires a
   valid, activated license** — it is not free and is not bundled here. It is used to
   generate the synthetic polycrystals and plot pole figures. On top of MATLAB you also
   need the **MTEX 6.0.0** toolbox (item 3). The MATLAB executable path and the MTEX
   `startup_mtex.m` path are set in `tools/matlab_runner.py` and the MTEX `.m` scripts,
   so **edit these to match your machine.**

3. **MTEX 6.0.0** toolbox (<https://mtex-toolbox.github.io/>) installed inside MATLAB.
   Free and open-source, but it runs on top of a licensed MATLAB.

4. **OpenAI API access** to **GPT-4o** (billed API usage). Provide your key as an
   environment variable:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

5. **Python 3.7+** and the packages in `requirements.txt` (see the Installation
   section below).

> **Platform note.** The pipeline was developed under **WSL (Ubuntu 18.04)** driving
> a **Windows MATLAB** install; `tools/matlab_runner.py` performs WSL↔Windows path
> conversion. On a native-Linux or macOS setup you will need to adapt
> `matlab_runner.py` to call your local `matlab` binary directly.

---

## Installation (Python)

Python **3.7+** is required.

```bash
git clone [REPO URL]
cd [repo]

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt`:
```
openai>=1.0
numpy>=1.24
scipy>=1.10
matplotlib>=3.7
scikit-learn>=1.2
scikit-optimize>=0.9
h5py>=3.8
```

---

## Configuration

Each case study has a `config_semi.py`. Review before running:

- `SIM_COMMAND` — path to the PRISMS-Plasticity `main` binary (default `../../main prm.prm`).
- `SIM_TIMEOUT_SEC` — per-simulation wall-clock cap (default 7200 s).
- `OPENAI_MODEL`, `TEMPERATURE`, `MAX_TOKENS` — LLM settings (default `gpt-4o`, 0.0–0.1, 1024).
- `REFINE_FACTOR` — FE mesh refinement (2^n elements per dimension).
- CS1: `PARAMETERS` (search bounds), `MAX_EVALUATIONS`, `RMSE_THRESHOLD`, `MAPE_THRESHOLD`.
- CS3: fibre-spread bounds and the 15-evaluation budget (in `inverse_search.py`).

Also edit the MATLAB / MTEX paths in `tools/matlab_runner.py` and the `matlab/*.m` scripts.

---

## Verify your environment (smoke test)

Before launching a run (each is an expensive CP-FEM job), confirm that all six
requirements are in place. From the repository root:

```bash
python3 check_environment.py
```

It reports `[ OK ]` / `[WARN]` / `[FAIL]` for: Python 3.7+, the Python packages,
`OPENAI_API_KEY`, the PRISMS-Plasticity `main` binary, `LD_LIBRARY_PATH`, the MATLAB
executable, and MTEX (`startup_mtex.m`). It runs **no** simulation and makes **no** API
call, and exits non-zero if a hard requirement fails. Example:

```
[ OK ]  Python 3.7+                      found 3.7.16
[ OK ]  python pkg: openai               1.30.0
[FAIL]  OPENAI_API_KEY                   not set  (export OPENAI_API_KEY=...)
[FAIL]  PRISMS main binary               not found (expected near .../main); build PRISMS-Plasticity
[ OK ]  MATLAB executable                /mnt/c/Program Files/MATLAB/R2025b/bin/matlab.exe
...
```

Resolve any `[FAIL]` items before running.

---

## Usage

Activate the environment, set `OPENAI_API_KEY` and `LD_LIBRARY_PATH`, then run the
entry point for the case study.

### CS1 — parameter calibration (SS316L)
```bash
cd case_study_1_calibration
python3 calibrate_react.py
```
The agent generates the microstructure, selects Bayesian optimization, and runs the
calibration. Output: `workdir/optimization_results.csv` (evaluation history),
`workdir/best_params.json` (calibrated Voce parameters), and figures via
`plot_results.py`.

### CS2 — forward validation (Cu compression)
```bash
cd case_study_2_forward
python3 run_pipeline.py
# optional custom goal:
python3 run_pipeline.py --query "Generate a random-texture Cu polycrystal, compress 40% along Z, and compare texture and stress-strain to the reference."
```
The agent recovers the eight-step workflow, runs the compression, and produces the
stress-strain comparison (`results/stressstrain.txt`) and pre/post pole figures
(`matlab/figures/`).

### CS3 — inverse texture recovery (Cu)
```bash
cd case_study_3_inverse
python3 inverse_react.py "Recover the initial texture that reproduces fig10_targets.json after 40% compression; use a budget of 15 simulations."
```
The agent selects Bayesian optimization and searches over the initial texture.
Output: `workdir/inverse_log.csv` (15-evaluation history),
`workdir/best_texture.json` (recovered optimum). To regenerate the recovered
optimum's deformed texture and pole figures:
```bash
python3 run_iter3.py
```

Each case study is expensive (each forward evaluation is a full CP-FEM run). CS1
completes in tens of evaluations; CS2 is a single run; CS3 uses 15 evaluations.

---

## Reproducing the paper figures

The MTEX pole figures are produced by the scripts in `matlab/` (e.g.
`prepost25.m`, `compare_pf.m`, `features25.m`), which render on the reference
0–2.5 MRD scale. The plotting utilities `plot_results.py` regenerate the
stress-strain and convergence figures from the logged output.

---

## Citing

If you use this code, please cite the paper (see `CITATION.cff`):

```bibtex
@article{[KEY],
  title   = {[PAPER TITLE]},
  author  = {[Authors]},
  journal = {[Journal]},
  year    = {[year]},
  doi     = {[DOI]}
}
```

Please also cite **PRISMS-Plasticity** (Yaghoobi et al., *Comput. Mater. Sci.* 169,
2019), **MTEX** (Bachmann et al., 2010), and **Anand & Kothari** (1996) as
appropriate.

---

## License

Released under the **MIT License** (see `LICENSE`). Change if your institution
requires a different one.

---

## Contact

[Your name] — [email] — [institution].
Issues and questions: please use the GitHub issue tracker.
