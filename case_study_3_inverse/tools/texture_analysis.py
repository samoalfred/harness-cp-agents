# -*- coding: utf-8 -*-
"""
texture_analysis.py
Extracts post-deformation orientations from the last QuadratureOutputsXXX.csv,
then calls MATLAB to run oriplot_big.m to generate post-deformation pole figures.
"""

import os
import re
import subprocess
import time

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
MATLAB_DIR  = os.path.join(BASE_DIR, "matlab")
MATLAB_EXE  = r"/mnt/c/Program Files/MATLAB/R2025b/bin/matlab.exe"
TIMEOUT_SEC = 3600


def _win_path(wsl_path):
    if wsl_path.startswith("/mnt/"):
        parts = wsl_path[5:].split("/", 1)
        drive = parts[0].upper() + ":"
        rest  = parts[1].replace("/", "\\") if len(parts) > 1 else ""
        return drive + "\\" + rest
    else:
        return r"\\wsl.localhost\ubuntu-18.04" + wsl_path.replace("/", "\\")


def find_last_quadrature_csv():
    """Find the QuadratureOutputsXXX.csv with the highest step number."""
    pattern = re.compile(r"QuadratureOutputs(\d+)\.csv$")
    files = []
    for f in os.listdir(RESULTS_DIR):
        m = pattern.match(f)
        if m:
            files.append((int(m.group(1)), f))
    if not files:
        return None
    files.sort(key=lambda x: x[0])
    return os.path.join(RESULTS_DIR, files[-1][1]), files[-1][1]


def extract_orientations(csv_path):
    """
    Extract columns 8, 9, 10 (1-indexed) from QuadratureOutputs CSV.
    Saves as matlab/orientations_post_deformation.csv (3 columns: rx, ry, rz).
    Returns (success, message, output_path).
    """
    print("[Texture] Reading: {}".format(csv_path))
    out_path = os.path.join(MATLAB_DIR, "orientations_post_deformation.csv")

    rows_written = 0
    with open(csv_path, "r") as fin, open(out_path, "w") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            cols = line.split(",")
            if len(cols) < 10:
                continue
            # columns 8, 9, 10 are index 7, 8, 9 (0-based)
            rx = cols[7].strip()
            ry = cols[8].strip()
            rz = cols[9].strip()
            fout.write("{},{},{}\n".format(rx, ry, rz))
            rows_written += 1

    print("[Texture] Extracted {} orientation rows -> {}".format(rows_written, out_path))
    return True, "Orientations extracted ({} points).".format(rows_written), out_path


def run_oriplot(timeout=TIMEOUT_SEC):
    """Run oriplot_big.m in MATLAB batch mode to generate post-deformation pole figures."""
    if not os.path.isfile(MATLAB_EXE):
        return False, "MATLAB not found at: {}".format(MATLAB_EXE)

    matlab_dir_win = _win_path(MATLAB_DIR)
    batch_cmd = "cd('{}'); run('oriplot_big');".format(
        matlab_dir_win.replace("'", "''")
    )

    cmd = [MATLAB_EXE, "-batch", batch_cmd, "-nosplash", "-nodesktop"]

    print("[Texture] Running oriplot_big.m in MATLAB...")
    t0 = time.time()
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
    except FileNotFoundError:
        return False, "Could not launch MATLAB."

    try:
        for line in iter(proc.stdout.readline, ""):
            line = line.rstrip()
            if line:
                print("[MATLAB] {}".format(line))
        proc.stdout.close()
        stderr_out = proc.stderr.read()
        proc.stderr.close()
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        return False, "MATLAB oriplot_big timed out."

    elapsed = time.time() - t0
    print("[Texture] oriplot_big.m finished in {:.1f}s.".format(elapsed))

    if proc.returncode != 0:
        print("[Texture] MATLAB stderr:\n{}".format(stderr_out[-1000:]))
        return False, "MATLAB exited with code {}.".format(proc.returncode)

    return True, "Post-deformation pole figures generated ({:.1f}s).".format(elapsed)


def run_texture_analysis():
    """
    Full post-processing pipeline:
    1. Find last QuadratureOutputs CSV
    2. Extract columns 8,9,10
    3. Run oriplot_big.m
    Returns (success, message).
    """
    # Step 1: Find last CSV
    result = find_last_quadrature_csv()
    if result is None:
        return False, "No QuadratureOutputs CSV found in results/."
    csv_path, csv_name = result
    print("[Texture] Last quadrature output: {}".format(csv_name))

    # Step 2: Extract orientations
    ok, msg, _ = extract_orientations(csv_path)
    if not ok:
        return False, msg

    # Step 3: Run MATLAB
    ok, msg = run_oriplot()
    return ok, msg


if __name__ == "__main__":
    ok, msg = run_texture_analysis()
    print(msg)
