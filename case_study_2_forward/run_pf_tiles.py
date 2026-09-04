# -*- coding: utf-8 -*-
"""Render individual post-deformation pole-figure tiles (paper scale)."""
import os, sys, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
from texture_analysis import _win_path, MATLAB_DIR, MATLAB_EXE
win = _win_path(MATLAB_DIR).replace("'", "''")
cmd = [MATLAB_EXE, "-batch", "cd('{}'); run('post_pf_tiles');".format(win),
       "-nosplash", "-nodesktop"]
p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                   text=True, timeout=600)
print(p.stdout[-1200:]); print("RC", p.returncode)
