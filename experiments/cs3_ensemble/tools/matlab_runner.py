# -*- coding: utf-8 -*-
"""
matlab_runner.py
Calls microstructure_gen.m via MATLAB batch mode from WSL Python.
MATLAB runs on the Windows side; outputs land in the matlab/ subfolder.
"""

import os
import subprocess
import time

# Paths — Windows-style for matlab.exe, WSL-style for Python I/O
MATLAB_EXE   = r"/mnt/c/Program Files/MATLAB/R2025b/bin/matlab.exe"
BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATLAB_DIR    = os.path.join(BASE_DIR, "matlab")
SCRIPT_NAME   = "microstructure_gen"   # no .m extension
H5_OUTPUT     = os.path.join(MATLAB_DIR, "input_structure_poly.h5")
SUMMARY_FILE  = os.path.join(MATLAB_DIR, "output_summary.txt")
TIMEOUT_SEC   = 7200   # 2 hours — generation can be slow


def _win_path(wsl_path):
    """Convert /home/user/... or /mnt/c/... to Windows path for matlab.exe."""
    if wsl_path.startswith("/mnt/"):
        # /mnt/c/foo/bar -> C:\foo\bar
        parts = wsl_path[5:].split("/", 1)
        drive = parts[0].upper() + ":"
        rest  = parts[1].replace("/", "\\") if len(parts) > 1 else ""
        return drive + "\\" + rest
    else:
        # WSL path like /home/... -> \\wsl.localhost\ubuntu-18.04\...
        return r"\\wsl.localhost\ubuntu-18.04" + wsl_path.replace("/", "\\")


def run_microstructure_gen(timeout=TIMEOUT_SEC):
    """
    Run microstructure_gen.m in MATLAB batch mode.
    Returns (success, message).
    """
    if not os.path.isfile(MATLAB_EXE):
        return False, "MATLAB not found at: {}".format(MATLAB_EXE)

    matlab_dir_win = _win_path(MATLAB_DIR)

    # MATLAB batch command: cd to script folder, then run
    batch_cmd = "cd('{}'); run('{}');".format(
        matlab_dir_win.replace("'", "''"),
        SCRIPT_NAME
    )

    cmd = [
        MATLAB_EXE,
        "-batch", batch_cmd,
        "-nosplash",
        "-nodesktop",
    ]

    print("[MATLAB] Running microstructure_gen.m ...")
    print("[MATLAB] Working dir: {}".format(matlab_dir_win))
    print("[MATLAB] This may take several minutes for a 300x300x300 grid.")

    t0 = time.time()
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        return False, "Could not launch MATLAB. Check MATLAB_EXE path in matlab_runner.py."

    # Stream stdout in real-time
    stderr_lines = []
    try:
        for line in iter(proc.stdout.readline, ""):
            line = line.rstrip()
            if line:
                print("[MATLAB] {}".format(line))
        proc.stdout.close()

        # Capture stderr after stdout closes
        stderr_output = proc.stderr.read()
        proc.stderr.close()

        # Wait with timeout
        proc.wait(timeout=timeout)

    except subprocess.TimeoutExpired:
        proc.kill()
        return False, "MATLAB timed out after {} seconds.".format(timeout)

    elapsed = time.time() - t0
    print("[MATLAB] Finished in {:.1f} seconds.".format(elapsed))

    if stderr_output and proc.returncode != 0:
        print("[MATLAB stderr]\n{}".format(stderr_output[-2000:]))

    if proc.returncode != 0:
        return False, "MATLAB exited with code {}.".format(proc.returncode)

    if not os.path.isfile(H5_OUTPUT):
        return False, "HDF5 output not found after MATLAB run: {}".format(H5_OUTPUT)

    # Read and print summary
    if os.path.isfile(SUMMARY_FILE):
        with open(SUMMARY_FILE) as f:
            summary = f.read()
        print("[MATLAB] Output summary:\n{}".format(summary))

    return True, "Microstructure generated successfully ({:.1f}s).".format(elapsed)


if __name__ == "__main__":
    ok, msg = run_microstructure_gen()
    print(msg)
