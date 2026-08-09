# -*- coding: utf-8 -*-
"""
react_agent.py — ReAct Calibration Agent for SS316L.

The LLM reads the query, selects the correct optimizer tool from the
repository, runs it, observes the result, and provides a physical
interpretation. No parameter guessing — the optimizer handles search.

Loop:
  Thought     — LLM reasons about which tool to use and why
  Action      — calls the selected optimizer tool
  Observation — tool returns best params + RMSE/MAPE
  Final       — LLM interprets the calibrated parameters physically
"""

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.dirname(_HERE)
sys.path.insert(0, _BASE)
sys.path.insert(0, os.path.join(_BASE, "tools"))

import config_semi
from llm_client import chat
from react_tools import TOOL_SCHEMAS, execute_tool

from openai import OpenAI

MAX_ITERATIONS = 12   # generate microstructure, convert, run one optimizer, interpret

SYSTEM_PROMPT = """\
You are an autonomous crystal plasticity calibration agent for SS316L austenitic \
stainless steel. Your job is to generate the microstructure, then calibrate slip \
parameters by selecting the correct optimization tool from the repository and running it.

Before any calibration, you MUST prepare the microstructure with these two tools, in order:

  1. generate_microstructure
     Runs MATLAB to build the synthetic 32x32x32 SS316L polycrystal used by the
     simulations. Produces the HDF5 microstructure file. Always call this first.

  2. convert_hdf5_to_prisms
     Converts the generated HDF5 into PRISMS-Plasticity input (grainID.txt,
     orientations.txt) and updates prm.prm. Call this after generate_microstructure
     and before any optimizer.

Only after the microstructure is generated and converted should you run an optimizer.

You have 4 optimizer tools available:

  1. run_bayesian_optimization
     LHS exploration + Gaussian Process + Expected Improvement.
     Most sample-efficient. Best for limited simulation budgets.
     Use when the query asks for Bayesian Optimization or does not specify.

  2. run_differential_evolution
     Population-based global search using mutation and crossover.
     Best for broad exploration and avoiding local minima.
     Use when the query asks for Differential Evolution or global search.

  3. run_nelder_mead
     Nelder-Mead Simplex local optimizer.
     Fast but may get trapped in local minima.
     Use when the query asks for Nelder-Mead or local refinement.

  4. run_random_bo
     Random Search followed by Bayesian Optimization.
     Simple baseline with BO exploitation phase.
     Use when the query asks for Random Search or Random+BO.

Parameters being calibrated (all bounds enforced by the tools):
  Initial Slip Resistance  (s0)  : 100–150 MPa  — controls yield stress
  Initial Hardening Modulus (h0) : 800–2500 MPa — controls hardening rate
  Saturation Stress (ss)         : 350–600 MPa  — controls flow stress plateau
  Power Law Exponent (n)         : 1–3          — controls transition sharpness

Stopping criteria (enforced automatically inside the tools):
  RMSE < 5 MPa  OR  MAPE < 2%  OR  60 simulations reached.

Rules:
- You MUST always write a brief Thought (1–2 sentences) before calling a tool, \
explaining what you are about to do and why.
- Call generate_microstructure once, then convert_hdf5_to_prisms once, before any optimizer.
- Call exactly ONE optimizer tool per calibration run.
- After the optimizer returns its result, provide a concise physical interpretation \
of the calibrated parameters for SS316L austenitic stainless steel.
- Do NOT guess parameter values — the optimizer tools handle all parameter search.
"""


class ReactCalibrationAgent(object):

    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY not set.")
        self._client = OpenAI(api_key=api_key)

    def run(self, query):
        print("\n" + "=" * 65)
        print("[ReAct] SS316L REACT CALIBRATION AGENT")
        print("[ReAct] Query: {}".format(query))
        print("=" * 65)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": query},
        ]

        iteration = 0

        while iteration < MAX_ITERATIONS:
            iteration += 1
            print("\n[ReAct] --- Iteration {} ---".format(iteration))

            response = self._client.chat.completions.create(
                model=config_semi.OPENAI_MODEL,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                temperature=0.1,
                max_tokens=1024,
            )

            message       = response.choices[0].message
            finish_reason = response.choices[0].finish_reason

            # Print Thought
            if message.content:
                print("\n[ReAct] Thought: {}".format(message.content))

            # No tool call → LLM is done (final interpretation)
            if finish_reason == "stop" or not message.tool_calls:
                final = message.content or "(No final response)"
                print("\n" + "=" * 65)
                print("[ReAct] CALIBRATION COMPLETE")
                print("\n[ReAct] Final Interpretation:")
                print(final)
                print("=" * 65)
                return final

            # Append assistant message
            messages.append({
                "role":       "assistant",
                "content":    message.content,
                "tool_calls": [
                    {
                        "id":       tc.id,
                        "type":     "function",
                        "function": {
                            "name":      tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            })

            # Execute tool calls
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    tool_args = json.loads(tool_call.function.arguments)
                except ValueError:
                    tool_args = {}

                print("[ReAct] Action: {}({})".format(tool_name, tool_args))

                observation = execute_tool(tool_name, tool_args)
                print("[ReAct] Observation: {}".format(observation))

                messages.append({
                    "role":         "tool",
                    "tool_call_id": tool_call.id,
                    "content":      observation,
                })

        print("[ReAct] WARNING: Max iterations reached.")
        return "Stopped: max iterations reached."
