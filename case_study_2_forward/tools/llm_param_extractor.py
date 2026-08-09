# -*- coding: utf-8 -*-
"""
llm_param_extractor.py

Sends the user query to the LLM and asks it to return a structured JSON of
simulation parameters. The pipeline then applies those parameters to the
config files before running — so the LLM truly controls execution.

Parameters extracted:
  orientation_type  : "textured" | "random"
  fiber_direction   : [h, k, l]  (only used when orientation_type = "textured")
  sigma_spread      : float  (texture sharpness in degrees)
  s0                : float  (Initial Slip Resistance, MPa)
  h0                : float  (Initial Hardening Modulus, MPa)
  ss                : float  (Saturation Stress, MPa)
  n                 : float  (Power Law Exponent)
"""

import json
import re
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.dirname(_HERE)
sys.path.insert(0, _BASE)

import config_semi
from llm_client import chat

SYSTEM_PROMPT = """\
You are a materials science parameter extraction assistant for a crystal plasticity pipeline.

The user will provide a natural language query describing a simulation they want to run.
Your job is to extract the simulation parameters from the query and return ONLY a valid
JSON object — no explanation, no markdown fences, just the raw JSON.

Always return all fields. Use these defaults if a parameter is not specified:
  orientation_type : "textured"
  fiber_direction  : [1, 0, 1]
  sigma_spread     : 15
  s0               : 110
  h0               : 1300
  ss               : 420
  n                : 2.5

Rules:
- orientation_type must be exactly "textured" or "random"
- fiber_direction is a list of 3 integers (Miller indices), e.g. [1,0,1] or [1,1,1]
- sigma_spread is a positive float (degrees); lower = sharper texture
- s0, h0, ss, n are positive floats (MPa for s0/h0/ss)
- Return ONLY valid JSON, nothing else

Example output:
{"orientation_type":"textured","fiber_direction":[1,0,1],"sigma_spread":15,"s0":110,"h0":1300,"ss":420,"n":2.5}
"""

DEFAULTS = {
    "orientation_type": "textured",
    "fiber_direction":  [1, 0, 1],
    "sigma_spread":     15.0,
    "s0":               110.0,
    "h0":               1300.0,
    "ss":               420.0,
    "n":                2.5,
}


def extract_parameters(query):
    """
    Send query to LLM, parse JSON response into a parameter dict.
    Returns (params_dict, raw_llm_response).
    Falls back to defaults on any parse error.
    """
    print("[ParamExtractor] Sending query to LLM for parameter extraction...")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": query},
    ]

    raw = chat(messages, model=config_semi.OPENAI_MODEL,
               temperature=0.0, max_tokens=200)

    print("[ParamExtractor] LLM raw response: {}".format(raw))

    # Strip any accidental markdown fences
    cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()

    try:
        params = json.loads(cleaned)
    except (ValueError, KeyError) as e:
        print("[ParamExtractor] WARNING: Could not parse JSON ({}). Using defaults.".format(e))
        params = {}

    # Merge with defaults so missing keys are always filled
    result = dict(DEFAULTS)
    for key in DEFAULTS:
        if key in params:
            result[key] = params[key]

    # Validate orientation_type
    if result["orientation_type"] not in ("textured", "random"):
        print("[ParamExtractor] WARNING: Unknown orientation_type '{}'. Defaulting to 'textured'.".format(
            result["orientation_type"]))
        result["orientation_type"] = "textured"

    # Validate fiber_direction is a 3-element list
    fd = result["fiber_direction"]
    if not (isinstance(fd, list) and len(fd) == 3):
        print("[ParamExtractor] WARNING: Invalid fiber_direction. Defaulting to [1,0,1].")
        result["fiber_direction"] = [1, 0, 1]

    print("[ParamExtractor] Extracted parameters:")
    for k, v in result.items():
        print("  {:20s} = {}".format(k, v))

    return result, raw
