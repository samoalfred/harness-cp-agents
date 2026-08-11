# INSTALL — quick start

Condensed setup. See `README.md` for full detail and background.

> The Python agent only orchestrates. The simulations need external software, so
> **all six items below are required.** Recommended platform: **WSL (Ubuntu)** or
> native Linux (PRISMS-Plasticity is a Linux/deal.II code and will not run on native
> Windows).

## 1. Get the code
```bash
git clone https://github.com/samoalfred/harness-cp-agents.git
cd harness-cp-agents
```

## 2. External tools (install once)
| Tool | How |
|---|---|
| **PRISMS-Plasticity** (`main` binary) | Build from <https://github.com/prisms-center/plasticity> (needs deal.II + SymEngine). |
| **MATLAB** (R2025b) | Commercial — **needs a valid license.** |
| **MTEX 6.0.0** | Free MATLAB toolbox: <https://mtex-toolbox.github.io/>. |
| **OpenAI API key** | GPT-4o access (billed). |

Then edit machine-specific paths:
- `SIM_COMMAND` (PRISMS `main`) in each `case_study_*/config_semi.py` if not `../../main`.
- `MATLAB_EXE` in each `case_study_*/tools/matlab_runner.py`.
- The `run('.../startup_mtex.m')` line in each `case_study_*/matlab/*.m`.

## 3. Python environment
```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 4. Environment variables
```bash
export OPENAI_API_KEY="sk-..."
export LD_LIBRARY_PATH=/path/to/dealii-candi/symengine-0.8.1/lib:$LD_LIBRARY_PATH
```

## 5. Verify everything is in place
```bash
python3 check_environment.py
```
Fix any `[FAIL]` before running.

## 6. Run a case study
```bash
# CS1 - SS316L Voce calibration
cd case_study_1_calibration && python3 calibrate_react.py

# CS2 - Cu forward compression validation
cd case_study_2_forward && python3 run_pipeline.py

# CS3 - Cu inverse texture recovery
cd case_study_3_inverse && python3 inverse_react.py "Recover the initial texture that reproduces fig10_targets.json after 40% compression; budget 15 simulations."
```

Each forward evaluation is a full CP-FEM run, so expect minutes-to-hours depending on
mesh refinement and the number of evaluations.
