# -*- coding: utf-8 -*-
"""
single_sim.py
Runs ONE PRISMS-Plasticity simulation with the current prm.prm settings.
No calibration loop — just a straight single FEM run.
"""

import os
import subprocess
import time

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIM_COMMAND = "../../main_ratedep"   # rate-dependent binary (paper Application 1); shared ../../main stays rate-independent
PRM_FILE    = "prm.prm"
TIMEOUT_SEC = 7200


def run_single_simulation(timeout=TIMEOUT_SEC):
    """
    Run PRISMS-Plasticity once with the current prm.prm.
    Streams output live. Returns (success, message).
    """
    exe = os.path.join(BASE_DIR, SIM_COMMAND)

    print("\n[PRISMS] Running single simulation...")
    print("[PRISMS] Working dir: {}".format(BASE_DIR))
    print("[PRISMS] Command: {} {}".format(SIM_COMMAND, PRM_FILE))

    t0 = time.time()
    try:
        proc = subprocess.Popen(
            [exe, PRM_FILE],
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except FileNotFoundError:
        return False, "PRISMS binary not found at: {}".format(exe)

    try:
        for line in iter(proc.stdout.readline, ""):
            line = line.rstrip()
            if line:
                print("[PRISMS] {}".format(line))
        proc.stdout.close()
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        return False, "PRISMS timed out after {} seconds.".format(timeout)

    elapsed = time.time() - t0
    print("[PRISMS] Finished in {:.1f} seconds.".format(elapsed))

    if proc.returncode != 0:
        return False, "PRISMS exited with code {}.".format(proc.returncode)

    return True, "Simulation completed successfully ({:.1f}s).".format(elapsed)


if __name__ == "__main__":
    ok, msg = run_single_simulation()
    print(msg)
