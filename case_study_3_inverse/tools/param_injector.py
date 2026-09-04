# -*- coding: utf-8 -*-
"""
param_injector.py -- Case Study 3 (inverse texture, rate-dependent Taylor).

Writes the candidate INITIAL texture proposed by the inverse search into the
equal-grain microstructure generator (matlab/microstructure_gen.m) before each
forward evaluation. Only the initial-texture design variables are injected; the
constitutive parameters (rate-dependent Taylor, m=77, s0/h0/ss/a, ...) are fixed
in prm.prm at the Yaghoobi et al. (2022) Application 1 values.

Variables set in microstructure_gen.m:
  orientation_type   'random' | 'textured'
  fiber_dir          [h k l]        (used only when 'textured')
  sigma_spread       scatter (deg)  (used only when 'textured')
"""

import os
import re

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATLAB_FILE = os.path.join(BASE_DIR, "matlab", "microstructure_gen.m")


def inject_microstructure_params(params):
    """
    Write orientation_type, fiber_dir and sigma_spread into microstructure_gen.m.
    params = {"orientation_type": str, "fiber_direction": [h,k,l], "sigma_spread": float}
    Returns (success, message).
    """
    if not os.path.isfile(MATLAB_FILE):
        return False, "microstructure_gen.m not found: {}".format(MATLAB_FILE)

    with open(MATLAB_FILE, "r") as f:
        content = f.read()

    otype = params["orientation_type"]
    h, k, l = params["fiber_direction"]
    sigma = float(params["sigma_spread"])

    # orientation_type = '...';
    content = re.sub(r"(orientation_type\s*=\s*')[^']*(')",
                     r"\g<1>{}\2".format(otype), content, count=1)

    # fiber_dir = [h k l];
    content = re.sub(r"(fiber_dir\s*=\s*\[)[^\]]*(\])",
                     r"\g<1>{} {} {}\2".format(h, k, l), content, count=1)

    # sigma_spread = <value>;
    content = re.sub(r"(sigma_spread\s*=\s*)[\d.eE+\-]+",
                     r"\g<1>{}".format(sigma), content, count=1)

    with open(MATLAB_FILE, "w") as f:
        f.write(content)

    msg = ("microstructure_gen.m updated: orientation_type='{}', "
           "fiber_dir=[{} {} {}], sigma_spread={}").format(otype, h, k, l, sigma)
    print("[Injector] {}".format(msg))
    return True, msg


if __name__ == "__main__":
    ok, msg = inject_microstructure_params(
        {"orientation_type": "textured", "fiber_direction": [1, 1, 0], "sigma_spread": 46.0})
    print(msg)
