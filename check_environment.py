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

# 8. MTEX (resolved from the MTEX_ROOT environment variable; the matlab/*.m
#    scripts fall back to a local default when MTEX_ROOT is unset)
mtex_root = os.environ.get("MTEX_ROOT")
if mtex_root:
    mtex_start = os.path.join(mtex_root, "startup_mtex.m")
    exists = os.path.isfile(mtex_start)
    report(OK if exists else WARN, "MTEX (startup_mtex.m)",
           mtex_start + ("" if exists else "  (MTEX_ROOT set, but startup_mtex.m not found there)"))
else:
    report(WARN, "MTEX (startup_mtex.m)",
           "MTEX_ROOT not set; the matlab/*.m scripts will use their fallback path. "
           "Set MTEX_ROOT to your MTEX installation directory for portability.")

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
