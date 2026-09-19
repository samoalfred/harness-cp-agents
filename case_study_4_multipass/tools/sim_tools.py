# -*- coding: utf-8 -*-
"""
sim_tools.py  (CS4 — multi-pass HCP Mg texture evolution)

run_pass(pass_number): runs ONE plane-strain-compression Gleeble pass with the
RATE-DEPENDENT PRISMS-Plasticity binary (../../main_ratedep). This is the
stateful workhorse of the multi-pass chain:
  - pass 1 uses the random as-cast initial orientations (orientations_initial.txt)
  - pass N>1 uses the deformed orientations produced by pass N-1
After each pass it saves that pass's QuadratureOutputs and, if not the last pass,
reformats the deformed Rodrigues orientations (columns 8-10, near-180 deg values
capped) into the next pass's orientation-input file. This output->input hand-off
is exactly the state carried across the chain.
"""
import os, subprocess, time, math, shutil
import config

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RATEDEP = os.path.join(BASE, config.SIM_COMMAND)


def _prm_for_pass(p):
    """Write pass p's prm from the template, cubic mesh + substeps + 12 constants."""
    src = os.path.join(BASE, "prm.prm")
    with open(src) as f:
        txt = f.read()
    n = config.SUBDIV
    reps = {
        r"set Subdivisions X": "set Subdivisions X = %d" % n,
        r"set Subdivisions Y": "set Subdivisions Y = %d" % n,
        r"set Subdivisions Z": "set Subdivisions Z = %d" % n,
        r"set Voxels in X direction": "set Voxels in X direction = %d" % n,
        r"set Voxels in Y direction": "set Voxels in Y direction = %d" % n,
        r"set Voxels in Z direction": "set Voxels in Z direction = %d" % n,
        r"set Number of Taylor Substeps": "set Number of Taylor Substeps = %d" % config.SUBSTEPS,
        r"set Number of User Material Constants 1": "set Number of User Material Constants 1 = 12",
        r"set Output Directory": "set Output Directory = out",
    }
    out = []
    for line in txt.splitlines():
        for key, new in reps.items():
            if line.strip().startswith(key):
                line = new
                break
        out.append(line)
    return "\n".join(out) + "\n"


def _write_next_input(quad_csv, next_txt):
    """Deformed Rodrigues (cols 8-10) -> next pass orientation input, |r| capped 1e4."""
    rows = []
    with open(quad_csv) as f:
        for line in f:
            c = [x for x in line.strip().split(",") if x != ""]
            if len(c) < 10:
                continue
            gid = int(float(c[0]))
            r = [float(c[7]), float(c[8]), float(c[9])]
            rows.append((gid, r))
    rows.sort(key=lambda t: t[0])
    with open(next_txt, "w") as f:
        f.write("************\n")
        for i, (gid, r) in enumerate(rows, start=1):
            m = math.sqrt(r[0]**2 + r[1]**2 + r[2]**2)
            if m > 1e4:
                s = 1e4 / m
                r = [r[0]*s, r[1]*s, r[2]*s]
            f.write("%d %f %f %f\n" % (i, r[0], r[1], r[2]))


def run_pass(pass_number, timeout=7200):
    p = int(pass_number)
    run = os.path.join(BASE, "pass%d" % p)
    if os.path.isdir(run):
        shutil.rmtree(run)
    os.makedirs(os.path.join(run, "out"))
    # static inputs
    for fn in ["slipDirectionsNoPyrA.txt", "slipNormalsNoPyrA.txt",
               "twinDirections.txt", "twinNormals.txt",
               "LatentHardeningRatioTwin.txt", "grainID.txt"]:
        shutil.copy(os.path.join(BASE, fn), run)
    # orientation input for this pass
    if p == 1:
        ori_src = os.path.join(BASE, "orientations_initial.txt")
    else:
        ori_src = os.path.join(BASE, "ori_pass%d.txt" % p)
        if not os.path.isfile(ori_src):
            return False, "Pass %d input not found (%s); run pass %d first." % (p, ori_src, p-1)
    shutil.copy(ori_src, os.path.join(run, "orientations_HCP_4096grains.txt"))
    # prm
    with open(os.path.join(run, "prm.prm"), "w") as f:
        f.write(_prm_for_pass(p))
    # run
    t0 = time.time()
    try:
        proc = subprocess.Popen([RATEDEP, "prm.prm"], cwd=run,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                universal_newlines=True)  # py3.6+ compatible (text= is 3.7+)
        for line in iter(proc.stdout.readline, ""):
            pass  # (increments stream to the log; suppressed here)
        proc.stdout.close(); proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill(); return False, "Pass %d timed out." % p
    except FileNotFoundError:
        return False, "Rate-dependent binary not found: %s" % RATEDEP
    quad = os.path.join(run, "out", "QuadratureOutputs79.csv")
    ss = os.path.join(run, "out", "stressstrain.txt")
    if not os.path.isfile(quad):
        return False, "Pass %d produced no QuadratureOutputs (check substeps/mesh)." % p
    # save this pass's texture; report flow stress + twinning
    shutil.copy(quad, os.path.join(BASE, "QuadOut_pass%d.csv" % p))
    flow = twin = float("nan")
    with open(ss) as f:
        last = f.readlines()[-1].split()
    flow = float(last[7]) - float(last[8])   # sigma_yy - sigma_zz
    twin = float(last[13])                   # TwinMade
    # hand off to next pass
    if p < config.N_PASSES:
        _write_next_input(quad, os.path.join(BASE, "ori_pass%d.txt" % (p + 1)))
    return True, ("Pass %d complete: plane-strain flow stress sigma_yy-sigma_zz = %.1f MPa, "
                  "reoriented twin fraction (TwinMade) = %.3f. Deformed orientations saved; "
                  "%s") % (p, flow, twin,
                           ("next-pass input prepared." if p < config.N_PASSES
                            else "this was the final pass."))
