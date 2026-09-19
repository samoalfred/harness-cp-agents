# -*- coding: utf-8 -*-
"""
matlab_runner.py  (CS4)
Runs a MATLAB (+MTEX) script in batch mode from WSL Python. MATLAB runs on the
Windows side and accesses the WSL folder through a \\wsl.localhost path, exactly
as in CS2. Used to compute (0001) pole figures and their maximum intensity.
"""
import os, subprocess

MATLAB_EXE = r"/mnt/c/Program Files/MATLAB/R2025b/bin/matlab.exe"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATLAB_DIR = os.path.join(BASE, "matlab")


def _win(wsl_path):
    if wsl_path.startswith("/mnt/"):
        parts = wsl_path[5:].split("/", 1)
        return parts[0].upper() + ":\\" + (parts[1].replace("/", "\\") if len(parts) > 1 else "")
    return r"\\wsl.localhost\ubuntu-18.04" + wsl_path.replace("/", "\\")


def run_pole_figure(timeout=3600):
    """Run matlab/pole_figure.m; it processes every QuadOut_pass*.csv in BASE plus
    the reference and writes matlab/texture_results.txt. Returns (ok, message)."""
    if not os.path.isfile(MATLAB_EXE):
        return False, "MATLAB not found at %s" % MATLAB_EXE
    base_win = _win(BASE); mdir_win = _win(MATLAB_DIR)
    cmd_str = "cd('%s'); pole_figure('%s'); exit;" % (
        mdir_win.replace("'", "''"), base_win.replace("'", "''"))
    cmd = [MATLAB_EXE, "-batch", cmd_str, "-nosplash", "-nodesktop"]
    try:
        subprocess.run(cmd, timeout=timeout, check=True)
    except subprocess.TimeoutExpired:
        return False, "MATLAB pole-figure step timed out."
    except subprocess.CalledProcessError as e:
        return False, "MATLAB returned an error (%s)." % e
    return True, "Pole figures + max intensities computed."
