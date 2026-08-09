"""
Supervisor Agent for System 3 (Semi-Autonomous).

Responsibilities:
  1. Read the user's natural language query
  2. Identify which optimization algorithm was requested
  3. Call the corresponding pre-built tool
  4. Interpret and report the results
  5. Provide physical insights about the calibrated parameters

The LLM does NOT write any optimization code — it only selects
and calls the pre-built tools in optimizer_tools.py.
"""

import os
import sys
import json

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.dirname(_HERE)
sys.path.insert(0, _BASE)
sys.path.insert(0, os.path.join(_BASE, "tools"))

import config_semi
from llm_client import chat
from optimizer_tools import TOOL_REGISTRY, TOOL_DESCRIPTIONS
from prm_tools import restore_backup


class SupervisorAgent(object):

    SYSTEM_PROMPT = (
        "You are an expert materials science supervisor managing a crystal plasticity "
        "calibration workflow for SS316L austenitic stainless steel.\n\n"
        "You have access to 4 pre-built optimization tools:\n"
        "{tools}\n\n"
        "Your responsibilities:\n"
        "1. Identify which algorithm the user requested\n"
        "2. Return the algorithm key (one of: bayesian, differential_evolution, "
        "nelder_mead, random_bo)\n"
        "3. After optimization, interpret results and provide physical insights\n\n"
        "You do NOT write optimization code. You only select and call tools."
    )

    def __init__(self):
        tools_str = "\n".join(
            "  - {}: {}".format(k, v)
            for k, v in TOOL_DESCRIPTIONS.items()
        )
        self.system_prompt = self.SYSTEM_PROMPT.format(tools=tools_str)

    def _identify_algorithm(self, query):
        """Ask GPT-4o to identify the requested algorithm from the query."""
        print("[Supervisor] Identifying requested algorithm...")
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": (
                "From this query, identify which optimization algorithm was requested. "
                "Return ONLY the algorithm key — one of: "
                "bayesian, differential_evolution, nelder_mead, random_bo.\n\n"
                "Query: {}"
            ).format(query)}
        ]
        response = chat(messages, model=config_semi.OPENAI_MODEL,
                        temperature=0.0, max_tokens=50)
        # Extract algorithm key
        response = response.strip().lower().replace(" ", "_")
        for key in TOOL_REGISTRY:
            if key in response:
                return key
        # Fallback — ask more explicitly
        print("[Supervisor] Could not identify algorithm — asking again...")
        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user", "content":
                         "Please return only one of these exact strings: "
                         "bayesian, differential_evolution, nelder_mead, random_bo"})
        response = chat(messages, model=config_semi.OPENAI_MODEL,
                        temperature=0.0, max_tokens=20).strip().lower()
        for key in TOOL_REGISTRY:
            if key in response:
                return key
        print("[Supervisor] Defaulting to bayesian optimization.")
        return "bayesian"

    def _interpret_results(self, query, algorithm, result):
        """Ask GPT-4o to interpret the calibration results."""
        print("[Supervisor] Interpreting results...")
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": (
                "The {} optimization has completed for SS316L calibration.\n\n"
                "Results:\n"
                "  Initial Slip Resistance (s0) : {:.4f} MPa\n"
                "  Initial Hardening Modulus (h0): {:.4f} MPa\n"
                "  Saturation Stress (ss)        : {:.4f} MPa\n"
                "  Power Law Exponent (n)        : {:.4f}\n"
                "  RMSE                          : {:.4f} MPa\n\n"
                "Original query: {}\n\n"
                "Please:\n"
                "1. State whether the calibration was successful\n"
                "2. Provide brief physical interpretation of these parameters "
                "for SS316L austenitic stainless steel\n"
                "3. Suggest any improvements if RMSE > 5 MPa"
            ).format(
                algorithm,
                result.get("s0", 0), result.get("h0", 0),
                result.get("ss", 0), result.get("n", 0),
                result.get("rmse", 0), query
            )}
        ]
        return chat(messages, model=config_semi.OPENAI_MODEL,
                    temperature=0.1, max_tokens=400)

    def run(self, query):
        """Main workflow: identify algorithm → run tool → interpret results."""
        print("\n" + "=" * 65)
        print("[Supervisor] Received query:")
        print("  " + query)
        print("=" * 65)

        # Step 1: Identify algorithm
        algorithm = self._identify_algorithm(query)
        print("[Supervisor] Selected algorithm: {}".format(algorithm))
        print("[Supervisor] Description: {}".format(
              TOOL_DESCRIPTIONS[algorithm]))

        # Step 2: Run the pre-built tool
        print("\n[Supervisor] Running optimization tool...")
        tool = TOOL_REGISTRY[algorithm]
        result = {}
        try:
            result = tool()
        except Exception as e:
            print("[Supervisor] Tool error: {}".format(e))
            result = {"rmse": float("inf"), "algorithm": algorithm}

        # Step 3: Restore prm.prm
        restore_backup(os.path.join(_BASE, "prm.prm"))

        # Step 4: Interpret results
        interpretation = self._interpret_results(query, algorithm, result)

        # Step 5: Print final summary
        print("\n" + "=" * 65)
        print("[Supervisor] CALIBRATION COMPLETE")
        print("  Algorithm : {}".format(result.get("algorithm", algorithm)))
        print("  s0        : {:.4f} MPa".format(result.get("s0", 0)))
        print("  h0        : {:.4f} MPa".format(result.get("h0", 0)))
        print("  ss        : {:.4f} MPa".format(result.get("ss", 0)))
        print("  n         : {:.4f}".format(result.get("n", 0)))
        print("  RMSE      : {:.4f} MPa".format(result.get("rmse", 0)))
        print("\n[Supervisor] Interpretation:")
        print(interpretation)
        print("=" * 65)

        return result, interpretation
