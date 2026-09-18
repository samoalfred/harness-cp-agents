# -*- coding: utf-8 -*-
"""
inverse_agent.py -- ReAct agent for the Case Study 3 inverse-texture problem.

The LLM reads the goal, selects the appropriate search strategy from the
optimizer repository, launches it, observes the recovered initial texture, and
provides a physical interpretation. The optimizer performs all of the search;
the agent does not propose textures itself (mirrors the Case Study 1 pattern).
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.dirname(_HERE)
sys.path.insert(0, _BASE)
sys.path.insert(0, os.path.join(_BASE, "tools"))

import config_semi
from inverse_tools import TOOL_SCHEMAS, execute_tool
from openai import OpenAI

MAX_ITERATIONS = 6   # select one optimizer, run it, interpret

SYSTEM_PROMPT = """\
You are an autonomous crystal plasticity agent solving an INVERSE problem for \
copper. A target deformation texture is given (the {111}, {100}, {110} pole \
figures of OFHC copper after uniaxial compression to true strain ~1.0, digitized \
from Fig. 2c of Yaghoobi et al. (2022) in fig2c_targets.json). Your job is to \
recover the INITIAL crystallographic texture that, after the same compression with \
the rate-dependent Taylor model, reproduces that target.

You do this by selecting a search strategy from the repository and launching it. \
The optimizer searches the initial-texture design variables (texture mode -- \
random or a fibre about [100], [110], or [111] -- and the fibre spread) by \
running a full crystal plasticity simulation for each candidate and scoring the \
resulting deformed texture against the target. You do NOT propose textures \
yourself; the optimizer handles the entire search.

Available search strategies:

  1. run_bayesian_texture_inverse
     Bayesian optimization (Gaussian process + expected improvement). Most \
sample-efficient. Recommended for this expensive forward model. Use this unless \
the user explicitly asks for a naive baseline.

  2. run_random_texture_inverse
     Random search baseline. Less efficient; use only if explicitly requested.

Rules:
- Write a brief Thought (1-2 sentences) before calling a tool, explaining which \
strategy you choose and why.
- Call exactly ONE search strategy.
- After it returns, provide a concise physical interpretation of the recovered \
initial texture and what it implies about the origin of the copper compression \
texture.
- Do NOT guess texture parameters; the optimizer performs the search.
"""


class InverseTextureAgent(object):

    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY not set.")
        self._client = OpenAI(api_key=api_key, base_url=os.environ.get("OPENAI_BASE_URL") or None)

    def run(self, query):
        print("\n" + "=" * 65)
        print("[ReAct] CU INVERSE-TEXTURE AGENT")
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
            message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason

            if message.content:
                print("\n[ReAct] Thought: {}".format(message.content))

            if finish_reason == "stop" or not message.tool_calls:
                final = message.content or "(No final response)"
                print("\n" + "=" * 65)
                print("[ReAct] INVERSE SEARCH COMPLETE")
                print("\n[ReAct] Final Interpretation:\n" + final)
                print("=" * 65)
                return final

            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in message.tool_calls
                ],
            })

            for tool_call in message.tool_calls:
                name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments)
                except ValueError:
                    args = {}
                print("[ReAct] Action: {}({})".format(name, args))
                observation = execute_tool(name, args)
                print("[ReAct] Observation: {}".format(observation))
                messages.append({"role": "tool", "tool_call_id": tool_call.id,
                                 "content": observation})

        print("[ReAct] WARNING: max iterations reached.")
        return "Stopped: max iterations reached."
