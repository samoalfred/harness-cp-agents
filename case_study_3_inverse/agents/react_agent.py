# -*- coding: utf-8 -*-
"""
react_agent.py — Pure goal-driven ReAct Agent for SS316L Texture Comparison.

The LLM is given a goal and a tool list only — no prescribed workflow.
It reasons from first principles about what to call, in what order,
observes results, and decides what to do next until the task is complete.
"""

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.dirname(_HERE)
sys.path.insert(0, _BASE)
sys.path.insert(0, os.path.join(_BASE, "tools"))

import config_semi
from react_tools import TOOL_SCHEMAS, execute_tool
from openai import OpenAI

MAX_ITERATIONS = 20


SYSTEM_PROMPT = """\
You are an autonomous agent for crystal plasticity simulation of Cu (copper).

Your goal: fulfil the user's request using the tools available to you. The task \
involves generating a Cu polycrystal with a random initial texture, deforming it \
under uniaxial compression to 40%, and then producing two comparisons: the \
crystallographic texture before versus after deformation, and the simulated \
stress-strain response versus an experimental tension-converted dataset.

You have the following tools:
  - inject_simulation_parameters
  - generate_microstructure
  - convert_hdf5_to_prisms
  - run_simulation
  - extract_post_orientations
  - generate_pole_figures
  - create_comparison_figure
  - compare_stress_strain

Read each tool's description carefully. The descriptions tell you what each \
tool does, what it requires as input, and what it produces as output. Use \
that information to reason about which tools to call, in what order, and \
with what arguments.

You are not told what order to call tools. Figure it out from the task and \
from what each tool's description says about prerequisites. Note that the two \
comparison outputs depend on different upstream steps: the texture comparison \
needs the post-deformation orientations and pole figures, while the \
stress-strain comparison needs the completed simulation. Both require the \
simulation to have run.

The material is copper, a face-centred cubic metal. Use the stated Cu defaults \
for the slip parameters unless the user explicitly overrides them, and do not \
invent parameter values of your own.

Before every tool call, write 1-2 sentences explaining what you are about \
to do and why. This reasoning must appear as text in your response before \
the tool call — do not call a tool silently.

When a tool returns FAILED or ERROR, reason about the cause and decide \
whether to stop or take a different action.

When you have completed the task, stop calling tools and deliver your \
final response.
"""


class ReactAgent(object):

    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY environment variable not set.")
        self._client = OpenAI(api_key=api_key, base_url=os.environ.get("OPENAI_BASE_URL") or None)

    def run(self, query):
        print("\n" + "=" * 65)
        print("[ReAct] SS316L PURE REACT PIPELINE STARTED")
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
                final_answer = message.content or "(No final response from LLM)"
                print("\n" + "=" * 65)
                print("[ReAct] PIPELINE COMPLETE")
                print("\n[ReAct] Final Answer:")
                print(final_answer)
                print("=" * 65)
                return final_answer

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
                        }
                    }
                    for tc in message.tool_calls
                ]
            })

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    tool_args = json.loads(tool_call.function.arguments)
                except ValueError:
                    tool_args = {}

                print("\n[ReAct] Action: {}".format(tool_name))
                if tool_args:
                    print("[ReAct] Args:   {}".format(json.dumps(tool_args)))

                observation = execute_tool(tool_name, tool_args)
                print("[ReAct] Observation: {}".format(observation))

                messages.append({
                    "role":         "tool",
                    "tool_call_id": tool_call.id,
                    "content":      observation,
                })

        print("[ReAct] WARNING: Maximum iterations ({}) reached.".format(MAX_ITERATIONS))
        return "Pipeline stopped: maximum iterations reached."
