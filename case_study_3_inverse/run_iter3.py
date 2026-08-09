#!/usr/bin/env python3.7
# Re-run the recovered optimum (iter 3: f110, [110], sigma 46.4) to regenerate
# its initial + deformed orientations for the CS3 pole figures and features.
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inverse_search import evaluate

c = {"mode": "f110", "fiber": [1, 1, 0], "sigma": 46.41176470588235}
t0 = time.time()
print("RUN_ITER3 START", c, flush=True)
loss, parts = evaluate(c)
print("RUN_ITER3 DONE loss=%.4f  (%.1f min)" % (loss, (time.time() - t0) / 60.0), flush=True)
print("parts:", parts, flush=True)
