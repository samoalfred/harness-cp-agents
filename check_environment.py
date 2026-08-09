#!/usr/bin/env python3
"""
check_environment.py -- environment smoke test.

Verifies that everything needed to run the crystal-plasticity agents is in place,
WITHOUT running a simulation or calling the OpenAI API. Run from the repository root
(ideally inside WSL / Linux):

    python3 check_environment.py

It reports [ OK ] / [WARN] / [FAIL] for each of the six requirements and exits with a
non-zero status if any hard requirement fails.
"""
import os, sys, re, shutil, importlib

ROOT = os.path.dirname(os.path.abspath(__file__))
OK, WARN, FAIL = "[ OK ]", "[WARN]", "[FAIL]"
results = []


def report(status, name, detail=""):
    results.append(status)
    print("%s  %-32s %s" % (status, name, detail))


print("Environment smoke test for the crystal-plasticity agents")
print("=" * 60)

# 1. Python version
v = sys.version_info
report(OK if v >= (3, 7) else FAIL, "Python 3.7+", "found %d.%d.%d" % (v[0], v[1], v[2]))

# 2. Python packages
pkgs = {"openai": "openai", "numpy": "numpy", "scipy": "scipy",
        "matplotlib": "matplotlib", "scikit-learn": "sklearn",
        "scikit-optimize": "skopt", "h5py": "h5py"}
for disp, mod in pkgs.items():
    try:
        m = importlib.import_module(mod)
        report(OK, "python pkg: %s" % disp, getattr(m, "__version__", "installed"))
    except Exception:
        report(FAIL, "python pkg: %s" % disp, "MISSING  (pip install %s)" % disp)

# 3. OPENAI_API_KEY
key = os.environ.get("OPENAI_API_KEY")
report(OK if key else FAIL, "OPENAI_API_KEY",
       "set (%d chars)" % len(key) if key else "not set  (export OPENAI_API_KEY=...)")

# 4. case-study folders
cases = [d for d in ("case_study_1_calibration", "case_study_2_forward", "case_study_3_inverse")
         if os.path.isdir(os.path.join(ROOT, d))]
report(OK if len(cases) == 3 else WARN, "case-study folders",
       "%d found: %s" % (len(cases), ", ".join(cases) or "none"))

# 5. PRISMS-Plasticity 'main' binary (resolve ../../main from a case study)
found_main = None
for c in cases:
    cand = os.path.normpath(os.path.join(ROOT, c, "..", "..", "main"))
    if os.path.isfile(cand):
        found_main = cand
        break
if found_main:
    ex = os.access(found_main, os.X_OK)
    report(OK if ex else WARN, "PRISMS main binary",
           found_main + ("" if ex else "  (not executable: chmod +x)"))
else:
    guess = os.path.normpath(os.path.join(ROOT, cases[0] if cases else ".", "..", "..", "main"))
    report(FAIL, "PRISMS main binary",
           "not found (expected near %s); build PRISMS-Plasticity" % guess)

# 6. LD_LIBRARY_PATH (SymEngine) -- needed at run time, warn only
ld = os.environ.get("LD_LIBRARY_PATH", "")
report(OK if "symengine" in ld.lower() else WARN, "LD_LIBRARY_PATH (SymEngine)",
       "set" if "symengine" in ld.lower() else "not set  (needed at run time for the solver)")

# 7. MATLAB executable (parse MATLAB_EXE from tools/matlab_runner.py)
matlab_exe = None
for c in cases:
    mr = os.path.join(ROOT, c, "tools", "matlab_runner.py")
    if os.path.isfile(mr):
        txt = open(mr, encoding="utf-8", errors="ignore").read()
        m = re.search(r'MATLAB_EXE\s*=\s*r?["\'](.+?)["\']', txt)
        if m:
            matlab_exe = m.group(1)
            break
if matlab_exe and os.path.isfile(matlab_exe):
    report(OK, "MATLAB executable", matlab_exe)
elif shutil.which("matlab"):
    report(OK, "MATLAB executable",
           "on PATH: %s  (set MATLAB_EXE in matlab_runner.py)" % shutil.which("matlab"))
else:
    report(FAIL, "MATLAB executable",
           ("configured path missing: %s" % matlab_exe) if matlab_exe
           else "not found; set MATLAB_EXE in tools/matlab_runner.py (MATLAB needs a license)")

# 8. MTEX startup_mtex.m (parse the run(...) path from a matlab/*.m script)
mtex_path = None
for c in cases:
    mdir = os.path.join(ROOT, c, "matlab")
    if os.path.isdir(mdir):
        for f in sorted(os.listdir(mdir)):
            if f.endswith(".m"):
                txt = open(os.path.join(mdir, f), encoding="utf-8", errors="ignore").read()
                m = re.search(r"run\(['\"](.+?startup_mtex\.m)['\"]\)", txt)
                if m:
                    mtex_path = m.group(1)
                    break
    if mtex_path:
        break
if mtex_path:
    exists = os.path.isfile(mtex_path)
    if not exists and len(mtex_path) > 2 and mtex_path[1:3] == ":\\":   # Windows path -> WSL mount
        exists = os.path.isfile("/mnt/" + mtex_path[0].lower() + mtex_path[2:].replace("\\", "/"))
    report(OK if exists else WARN, "MTEX (startup_mtex.m)",
           mtex_path + ("" if exists else "  (path not found; edit the run() line in matlab/*.m)"))
else:
    report(WARN, "MTEX (startup_mtex.m)",
           "path not found in matlab/*.m; ensure MTEX 6.0.0 is installed and referenced")

# summary
print("-" * 60)
nfail, nwarn = results.count(FAIL), results.count(WARN)
if nfail == 0 and nwarn == 0:
    print("All checks passed. You are ready to run the agents.")
elif nfail == 0:
    print("Core checks passed with %d warning(s). Review the WARN items above." % nwarn)
else:
    print("%d check(s) FAILED, %d warning(s). Resolve the FAIL items before running." % (nfail, nwarn))
    sys.exit(1)
