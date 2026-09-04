# -*- coding: utf-8 -*-
"""Render post-deformation pole figures on the paper's fixed 0-3.5 scale."""
import os, sys, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
from texture_analysis import _win_path, MATLAB_DIR, MATLAB_EXE

win = _win_path(MATLAB_DIR).replace("'", "''")
batch = "cd('{}'); run('post_pf_fixed');".format(win)
cmd = [MATLAB_EXE, "-batch", batch, "-nosplash", "-nodesktop"]
p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                   text=True, timeout=600)
print(p.stdout[-1800:])
print("RC", p.returncode)
