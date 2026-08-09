# -*- coding: utf-8 -*-
"""
param_injector.py

Applies LLM-extracted parameters to the actual config files before the
pipeline runs. This is the bridge that makes the LLM truly control execution.

Files modified:
  matlab/microstructure_gen.m  — orientation_type, sigma_spread, fiber_direction
  prm.prm                      — s0, h0, ss, n (all 12 FCC slip systems)
"""

import os
import re

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATLAB_FILE = os.path.join(BASE_DIR, "matlab", "microstructure_gen.m")
PRM_FILE    = os.path.join(BASE_DIR, "prm.prm")


def _replace_matlab_param(content, param, new_value):
    """Replace  param = <value>;  in MATLAB script (handles strings and numbers)."""
    if isinstance(new_value, str):
        pattern     = r"({}[\s]*=[\s]*')[^']*('[\s]*;)".format(re.escape(param))
        replacement = r"\g<1>{}\2".format(new_value)
    else:
        pattern     = r"({}[\s]*=[\s]*)[\d.]+([;\s])".format(re.escape(param))
        replacement = r"\g<1>{}\2".format(new_value)
    return re.sub(pattern, replacement, content)


def _replace_prm_param(content, param, value):
    """Replace  set param = v,v,...,v  with 12 copies of the new value."""
    vals_str = ", ".join([str(float(value))] * 12)
    pattern  = r"(set {}\s*=\s*)[^\n]+".format(re.escape(param))
    return re.sub(pattern, r"\g<1>{}".format(vals_str), content)


def inject_microstructure_params(params):
    """
    Write orientation_type, sigma_spread, and fiber_direction into
    microstructure_gen.m.
    Returns (success, message).
    """
    if not os.path.isfile(MATLAB_FILE):
        return False, "microstructure_gen.m not found: {}".format(MATLAB_FILE)

    with open(MATLAB_FILE, "r") as f:
        content = f.read()

    # orientation_type
    content = _replace_matlab_param(content, "orientation_type", params["orientation_type"])

    # sigma_spread
    content = re.sub(
        r"(sigma_spread\s*=\s*)[\d.]+(\s*;)",
        r"\g<1>{}\2".format(float(params["sigma_spread"])),
        content
    )

    # fiber_direction — replace the c_dir line
    h, k, l = params["fiber_direction"]
    norm_str = "norm([{} {} {}])".format(h, k, l)
    new_cdir = "    c_dir = [{} {} {}] / {};".format(h, k, l, norm_str)
    content  = re.sub(
        r"    c_dir\s*=\s*\[.*?\]\s*/\s*norm\(\[.*?\]\)\s*;",
        new_cdir,
        content
    )

    # Also update the fprintf label so it reflects the actual direction
    content = re.sub(
        r"(fprintf\('Generating \[)[^\]]+(\] Fiber Texture\\n'\);)",
        r"\g<1>{} {} {}\2".format(h, k, l),
        content
    )

    with open(MATLAB_FILE, "w") as f:
        f.write(content)

    msg = ("microstructure_gen.m updated: orientation_type='{}', "
           "sigma_spread={}, fiber_direction=[{} {} {}]").format(
        params["orientation_type"], params["sigma_spread"], h, k, l)
    print("[Injector] {}".format(msg))
    return True, msg


def inject_prm_params(params):
    """
    Write s0, h0, ss, n into prm.prm for all 12 FCC slip systems.
    Returns (success, message).
    """
    if not os.path.isfile(PRM_FILE):
        return False, "prm.prm not found: {}".format(PRM_FILE)

    with open(PRM_FILE, "r") as f:
        content = f.read()

    content = _replace_prm_param(content, "Initial Slip Resistance",   params["s0"])
    content = _replace_prm_param(content, "Initial Hardening Modulus", params["h0"])
    content = _replace_prm_param(content, "Saturation Stress",         params["ss"])
    content = _replace_prm_param(content, "Power Law Exponent",        params["n"])

    with open(PRM_FILE, "w") as f:
        f.write(content)

    msg = ("prm.prm updated: s0={}, h0={}, ss={}, n={}").format(
        params["s0"], params["h0"], params["ss"], params["n"])
    print("[Injector] {}".format(msg))
    return True, msg


def inject_all(params):
    """
    Apply all LLM-extracted parameters to config files.
    Returns (success, summary_message).
    """
    print("\n[Injector] Applying LLM parameters to config files...")

    ok1, msg1 = inject_microstructure_params(params)
    if not ok1:
        return False, msg1

    ok2, msg2 = inject_prm_params(params)
    if not ok2:
        return False, msg2

    return True, "{} | {}".format(msg1, msg2)


if __name__ == "__main__":
    # Quick test with defaults
    test_params = {
        "orientation_type": "textured",
        "fiber_direction":  [1, 1, 1],
        "sigma_spread":     10.0,
        "s0":               120.0,
        "h0":               1500.0,
        "ss":               450.0,
        "n":                3.0,
    }
    ok, msg = inject_all(test_params)
    print(msg)
