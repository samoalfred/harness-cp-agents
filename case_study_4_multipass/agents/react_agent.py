# -*- coding: utf-8 -*-
"""
react_agent.py — Pure goal-driven ReAct agent for CS4 (multi-pass HCP Mg texture
evolution). SAME harness core as CS2 (system prompt shape, tool loop, iteration
cap); only the tool list and banner differ. The LLM is given a goal and the tool
list only; it reasons about which tools to call and in what order.
"""
import json, os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.dirname(_HERE)
sys.path.insert(0, _BASE); sys.path.insert(0, os.path.join(_BASE, "tools"))

import config
from react_tools import TOOL_SCHEMAS, execute_tool
from openai import OpenAI

MAX_ITERATIONS = 40   # multi-pass: 5 passes + validation steps

SYSTEM_PROMPT = """\
You are an autonomous agent for crystal plasticity simulation using PRISMS-Plasticity. Your goal: fulfill the user's request using the tools available to you.

You have the following tools:
  - run_pass
  - compare_stress_strain
  - analyze_texture_evolution
  - compare_final_texture

Read each tool's description carefully. The descriptions tell you what each tool does, what it requires as input, and what it produces as output. Use that information to reason about which tools to call, in what order, and with what arguments.

Before each tool call, write one to two sentences explaining what you are about to do and why; do not call a tool silently. If a tool returns FAILED or ERROR, reason about the cause and decide whether to retry, take a different action, or stop.

When you have completed the task, stop calling tools and deliver your final response.
"""


class ReactAgent(object):
    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY environment variable not set.")
        self._client = OpenAI(api_key=api_key, base_url=os.environ.get("OPENAI_BASE_URL") or None)

    def run(self, query):
        print("\n" + "=" * 65)
        print("[ReAct] CS4 (%s) MULTI-PASS PIPELINE STARTED" % config.ALLOY)
        print("[ReAct] Query: {}".format(query))
        print("=" * 65)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]
        iteration = 0
        while iteration < MAX_ITERATIONS:
            iteration += 1
            print("\n[ReAct] --- Iteration {} ---".format(iteration))
            response = self._client.chat.completions.create(
                model=config.OPENAI_MODEL, messages=messages,
                tools=TOOL_SCHEMAS, tool_choice="auto",
                temperature=0.1, max_tokens=1024)
            message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason
            if message.content:
                print("\n[ReAct] Thought: {}".format(message.content))
            if finish_reason == "stop" or not message.tool_calls:
                final = message.content or "(No final response from LLM)"
                print("\n" + "=" * 65)
                print("[ReAct] PIPELINE COMPLETE\n\n[ReAct] Final Answer:\n" + final)
                print("=" * 65)
                return final
            messages.append({"role": "assistant", "content": message.content,
                "tool_calls": [{"id": tc.id, "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in message.tool_calls]})
            for tool_call in message.tool_calls:
                name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments)
                except ValueError:
                    args = {}
                print("\n[ReAct] Action: {}".format(name))
                if args:
                    print("[ReAct] Args:   {}".format(json.dumps(args)))
                obs = execute_tool(name, args)
                print("[ReAct] Observation: {}".format(obs))
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": obs})
        print("[ReAct] WARNING: Maximum iterations ({}) reached.".format(MAX_ITERATIONS))
        return "Pipeline stopped: maximum iterations reached."
