# CP-Agent: A Harness-Engineered Agent for Crystal Plasticity Simulation Workflows

Code accompanying the paper:

> **CP-Agent: A Harness-Engineered Agent for Crystal Plasticity Simulation Workflows**
> Samuel Onimpa Alfred, Abhishek Kumar, and Veera Sundararaghavan.
> Department of Aerospace Engineering, University of Michigan, Ann Arbor.
> Manuscript, 2026 (DOI to be added upon publication).

A single **harness-engineered, ReAct-style LLM agent** that drives full crystal
plasticity finite element (CP-FEM) workflows from a one-sentence natural-language
goal. The *same* harness (system prompt + tool schemas + dispatcher + iteration
loop) is applied unchanged to four structurally different problems:

| | Case study | Material | Task |
|---|---|---|---|
| **CS1** | Parameter calibration | SS316L | Recover four hardening parameters that fit an experimental tensile curve. The agent selects a numerical optimizer and delegates the search. |
| **CS2** | Forward validation | OFHC copper | With fixed parameters, run one compression simulation and validate the flow response and deformation texture against a published benchmark. |
| **CS3** | Inverse texture recovery | OFHC copper | Given a target deformation texture, search over the initial microstructural texture to reproduce it. |
| **CS4** | Multi-pass evolution | ZX31 (Mg-3Zn-0.3Ca), HCP | Chain five rate-dependent plane-strain-compression passes of hot rolling, carrying the deformed texture forward pass to pass, and reproduce the experimentally observed weakened, split basal texture. |

Only the **tool set** and the **user query** change between case studies; the agent
architecture does not. See `docs/CS1_Map.png`, `CS2_Map.png`, `CS3_Map.png` for the
per-case pipeline structure; CS4 chains five passes of the CS2-style forward
pipeline, so it reuses that structure (see `case_study_4_multipass/README.md`).

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
├── case_study_1_calibration/     # CS1: SS316L calibration
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
│   └── Yaghoobi et al. (2022).csv #  digitized reference stress-strain curve
├── case_study_3_inverse/         # CS3: Cu inverse texture recovery
│   ├── inverse_react.py          #   entry point (agent selects the strategy)
│   ├── inverse_search.py         #   Bayesian optimization over the initial texture
│   ├── config_semi.py, agents/, tools/
│   └── fig2c_targets.json        #   digitized target pole-figure features
├── case_study_4_multipass/       # CS4: ZX31 Mg five-pass rolling texture evolution
│   ├── run_pipeline.py           #   entry point (goal-driven ReAct, chains 5 passes)
│   ├── config.py                 #   alloy params, reference paths, DEFAULT_QUERY
│   ├── prm.prm                   #   rate-dependent Table-1 350C deck (main_ratedep)
│   ├── orientations_initial.txt  #   random as-cast start (pass-1 input)
│   ├── agents/, tools/, matlab/  #   react_agent + run_pass/compare/analyze tools
│   └── reference/                #   authors' 1-pass stress, 5-pass texture, experiment PNG
├── experiments/                  # Section 3.5: reliability & robustness studies
│   ├── reliability/              #   correct-sequence + termination over repeated runs
│   ├── ablation/                 #   2x2 tool-name x tool-description ablation
│   └── recovery/                 #   induced-fault error-recovery trace (paper S3)
└── docs/                         # structure maps, pipeline diagram
```

Each `case_study_*` folder also contains a `matlab/` subfolder (MTEX scripts for
microstructure generation and pole figures) and a `workdir/` with small example
output logs (`optimization_results.csv`, `inverse_log.csv`, `best_*.json`).

> **Note.** These folders mirror the exact harnesses used for the paper
> (`SS316L_Semi_LLM_React_MicroGen3/`, `CS2_Texture_Evolution/`, and
> `CS3_Inverse_Problem/`), with the heavy run artifacts (`results/`, `*.vtu`,
> `QuadratureOutputs*.csv`, HDF5, `.mat`, generated figures) excluded per
> `.gitignore`; paths in each `config_semi.py` are relative, so the folders are
> self-contained.

---

## Requirements at a glance

The Python agent is only the **orchestrator**. The simulations it drives depend on
external software that must be installed separately. **All of the items below are
required; the agents cannot run end to end without every one of them.**

| # | Requirement | Cost | Needed for |
|---|---|---|---|
| 1 | **Linux or WSL** (developed on WSL Ubuntu 18.04) | free | running PRISMS-Plasticity, a Linux / deal.II code. **Native Windows without WSL will not work.** |
| 2 | **PRISMS-Plasticity**, built from source (needs **deal.II** + **SymEngine**) | free / open-source | the CP-FEM simulations (the `main` executable; CS4 also needs the rate-dependent build `main_ratedep`) |
| 3 | **MATLAB** (developed with R2025b) | **commercial — a valid MATLAB license is required** | synthetic microstructure generation and pole figures |
| 4 | **MTEX** MATLAB toolbox (6.0.0 for CS1–CS3; 6.2.beta.3 for CS4) | free / open-source | crystallographic texture analysis inside MATLAB |
| 5 | **OpenAI API key** with **GPT-4o** access (or an OpenAI-compatible endpoint / another provider, see below) | paid (API usage is billed) | the LLM agent |
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
   need the **MTEX 6.0.0** toolbox (item 3). The MATLAB executable path is set in
   `tools/matlab_runner.py`. The MTEX location is read from the **`MTEX_ROOT`**
   environment variable by every `matlab/*.m` script; set it to the folder that
   contains `startup_mtex.m`, for example:
   ```bash
   export MTEX_ROOT="/path/to/mtex-6.0.0"      # Linux/WSL
   # Windows (PowerShell):  setx MTEX_ROOT "C:\path\to\mtex-6.0.0"
   ```
   If `MTEX_ROOT` is unset, the scripts fall back to a default install location that
   you can edit at the top of each `matlab/*.m` file.

3. **MTEX 6.0.0** toolbox (<https://mtex-toolbox.github.io/>) installed inside MATLAB.
   Free and open-source, but it runs on top of a licensed MATLAB.

4. **OpenAI API access** to **GPT-4o** (billed API usage). Provide your key as an
   environment variable:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```
   Using a different provider (for example **Anthropic Claude**) is supported; see
   [Using a different LLM provider](#using-a-different-llm-provider-eg-anthropic-claude)
   under Configuration.

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
git clone https://github.com/samoalfred/harness-cp-agents.git
cd harness-cp-agents

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

Each case study has a config file (`config_semi.py` for CS1–CS3, `config.py` for
CS4). Review before running:

- `SIM_COMMAND` — path to the PRISMS-Plasticity binary (default `../../main prm.prm`;
  CS4 uses the rate-dependent `../../main_ratedep`).
- `SIM_TIMEOUT_SEC` — per-simulation wall-clock cap (default 7200 s).
- `OPENAI_MODEL`, `TEMPERATURE`, `MAX_TOKENS` — LLM settings (default `gpt-4o`, 0.0–0.1, 1024).
- `REFINE_FACTOR` — FE mesh refinement (2^n elements per dimension).
- CS1: `PARAMETERS` (search bounds), `MAX_EVALUATIONS`, `RMSE_THRESHOLD`, `MAPE_THRESHOLD`.
- CS3: fibre-spread bounds and the 15-evaluation budget (in `inverse_search.py`).
- CS4 (`config.py`): `ALLOY`, `SUBDIV` (grain count `SUBDIV^3`; 12 -> 1728),
  `SUBSTEPS`, `N_PASSES`, and the `REF_*` reference-data paths.

Also set the MATLAB executable in `tools/matlab_runner.py` and the `MTEX_ROOT`
environment variable for the `matlab/*.m` scripts (see the Prerequisites section).

### Using a different LLM provider (e.g., Anthropic Claude)

By default the agents call **OpenAI GPT-4o** through OpenAI's function-calling
interface (`tools=TOOL_SCHEMAS` in `agents/*.py`), and the tool schemas are written
in the OpenAI function-calling format. If you have a key from a different provider,
you have two options.

**Option A — an OpenAI-compatible endpoint (no code changes).** The agents build the
client with `base_url=os.environ.get("OPENAI_BASE_URL")`, so any endpoint that speaks
the OpenAI Chat Completions + function-calling protocol works by setting two
variables and the model name in `config_semi.py`:
```bash
export OPENAI_API_KEY="your-key-for-that-endpoint"
export OPENAI_BASE_URL="https://your-openai-compatible-endpoint/v1"
```
This covers Azure OpenAI, OpenRouter, local servers (vLLM, Ollama in OpenAI-compatible
mode), and gateways such as **LiteLLM**. To use **Anthropic Claude** this way, run a
proxy that exposes Claude behind an OpenAI-compatible API (for example, the LiteLLM
proxy), point `OPENAI_BASE_URL` at it, set `OPENAI_MODEL` in `config_semi.py` to the
Claude model id, and provide your `ANTHROPIC_API_KEY` to the proxy. No changes to the
agent code are needed.

**Option B — the native Anthropic SDK (requires code changes).** Anthropic's tool-use
API differs from OpenAI's (the system prompt is a separate argument, and tool calls
are returned as `tool_use` content blocks with matching `tool_result` blocks). To use
it natively you would `pip install anthropic`, set `ANTHROPIC_API_KEY`, and adapt the
loop in each `agents/*.py`: replace the `OpenAI(...)` client and
`client.chat.completions.create(..., tools=TOOL_SCHEMAS)` call with
`Anthropic(...).messages.create(...)`, convert `TOOL_SCHEMAS` to Anthropic's tool
schema, and parse `tool_use`/`tool_result` blocks instead of `message.tool_calls`.
See the Anthropic tool-use documentation for the exact message shapes.

For most users, **Option A is the simplest** and keeps the agent code unchanged.

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
`workdir/best_params.json` (calibrated parameters), and figures via
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
(`matlab/figures/`). The microstructure generator (`matlab/microstructure_gen.m`)
fixes its random seed (`rng(0,'twister')`), so the generated ~400-grain random
texture is reproducible and matches the frozen realization in
`orientations_FCC_400grains.txt`.

### CS3 — inverse texture recovery (Cu)
```bash
cd case_study_3_inverse
python3 inverse_react.py            # uses the default query (recover the initial texture)
```
The agent selects Bayesian optimization and searches over the initial texture to
reproduce the target deformation texture (`fig2c_targets.json`) after compression to
true strain ~1.0. Output: `workdir/inverse_log.csv` (15-evaluation history),
`workdir/best_texture.json` (recovered optimum). To re-run the recovered optimum at
full Taylor substeps:
```bash
python3 run_best.py
```

### CS4 — multi-pass texture evolution (ZX31 Mg)
```bash
cd case_study_4_multipass
export MTEX_ROOT="/path/to/mtex-6.2.beta.3"
python3 run_pipeline.py
```
The agent chains five rate-dependent plane-strain-compression passes, carrying each
pass's deformed texture forward as the next pass's input, then compares the pass-1
flow stress and the pass-5 (0001) texture against the reference simulation and the
experiment. This case requires the **rate-dependent** solver binary
(`../../main_ratedep`, set in `config.py`) and MTEX 6.2.beta.3; see
`case_study_4_multipass/README.md`.

Each case study is expensive (each forward evaluation is a full CP-FEM run). CS1
completes in tens of evaluations; CS2 is a single run; CS3 uses 15 evaluations; CS4
runs five chained passes (roughly one hour per pass at 1728 grains).

---

## Reproducing the paper figures

The MTEX pole figures are produced by the scripts in `matlab/` (e.g.
`prepost25.m`, `compare_pf.m`, `features25.m` for CS1–CS3, and `pole_figure.m` for
CS4), which render on the reference intensity scale. The plotting utilities
`plot_results.py` regenerate the stress-strain and convergence figures from the
logged output. For CS4, `matlab/pole_figure.m` computes the (0001) pole figures and
peak intensities per pass and writes `texture_results.txt`.

---

## Citing

If you use this code, please cite the paper (see `CITATION.cff`):

```bibtex
@article{alfred2026harness,
  title   = {CP-Agent: A Harness-Engineered Agent for Crystal Plasticity Simulation Workflows},
  author  = {Alfred, Samuel Onimpa and Kumar, Abhishek and Sundararaghavan, Veera},
  journal = {Manuscript (under review)},
  year    = {2026},
  note    = {DOI to be added upon publication}
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

Samuel Onimpa Alfred, Department of Aerospace Engineering, University of Michigan,
Ann Arbor (soalfred@umich.edu).
Issues and questions: please use the GitHub issue tracker.
