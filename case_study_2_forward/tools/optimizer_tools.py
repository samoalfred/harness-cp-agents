"""
Pre-built optimization algorithms for System 3 (Semi-Autonomous).
Pure numpy/scipy implementation — no scikit-optimize required.

Available tools:
    run_bayesian_optimization()
    run_differential_evolution()
    run_nelder_mead()
    run_random_bo()
"""

import os
import sys
import numpy as np
from scipy.stats import norm

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _TOOLS_DIR)

from sim_tools import run_simulation, CalibrationConverged, PENALTY

BOUNDS = [
    (100.0, 150.0),   # s0
    (800.0, 2500.0),  # h0
    (350.0, 600.0),   # ss
    (1.0,   3.0),     # n
]


def _objective(params):
    s0, h0, ss, n = params
    result = run_simulation(s0, h0, ss, n)
    rmse = result[0] if isinstance(result, tuple) else result
    return rmse


# ── GP helpers (pure numpy) ───────────────────────────────────────

def _normalize(X):
    arr = np.array(BOUNDS)
    return (np.array(X) - arr[:, 0]) / (arr[:, 1] - arr[:, 0])


def _rbf_kernel(X1, X2, ls=1.0, noise=1e-5):
    X1n = _normalize(np.atleast_2d(X1))
    X2n = _normalize(np.atleast_2d(X2))
    D = np.sum((X1n[:, None] - X2n[None, :]) ** 2, axis=-1)
    K = np.exp(-0.5 * D / ls ** 2)
    if X1n.shape == X2n.shape and np.allclose(X1n, X2n):
        K += noise * np.eye(len(K))
    return K


def _gp_predict(X_obs, y_obs, X_cand, ls=1.0):
    K    = _rbf_kernel(X_obs, X_obs, ls)
    Ks   = _rbf_kernel(X_obs, X_cand, ls)
    Kss  = np.diag(_rbf_kernel(X_cand, X_cand, ls))
    try:
        L    = np.linalg.cholesky(K)
        alpha = np.linalg.solve(L.T, np.linalg.solve(L, y_obs))
        mu   = Ks.T @ alpha
        v    = np.linalg.solve(L, Ks)
        var  = np.maximum(Kss - np.sum(v**2, axis=0), 0.0)
    except np.linalg.LinAlgError:
        mu  = np.full(len(X_cand), np.mean(y_obs))
        var = np.ones(len(X_cand))
    return mu, np.sqrt(var)


def _ei(mu, sigma, best):
    Z  = (best - mu) / (sigma + 1e-9)
    ei = (best - mu) * norm.cdf(Z) + sigma * norm.pdf(Z)
    ei[sigma < 1e-9] = 0.0
    return ei


def _next_ei(X_obs, y_obs, rng, n_cand=500):
    cands = np.array([[rng.uniform(lo, hi) for lo, hi in BOUNDS]
                      for _ in range(n_cand)])
    mu, sigma = _gp_predict(X_obs, y_obs, cands)
    return cands[np.argmax(_ei(mu, sigma, min(y_obs)))].tolist()


def _lhs(n, rng):
    pts = np.empty((n, len(BOUNDS)))
    for j, (lo, hi) in enumerate(BOUNDS):
        perm = rng.permutation(n)
        pts[:, j] = lo + (hi - lo) * (perm + rng.uniform(size=n)) / n
    return pts.tolist()


# ─────────────────────────────────────────────────────────────────
# Tool 1: Bayesian Optimization
# ─────────────────────────────────────────────────────────────────

def run_bayesian_optimization(n_initial=10, seed=42):
    """
    Tool 1: Bayesian Optimization — LHS exploration + GP+EI exploitation.
    Pure numpy/scipy — no external packages needed.
    Best for: expensive simulations, limited budget.
    """
    print("\n[Tool 1] Bayesian Optimization (LHS + GP+EI)")
    rng   = np.random.RandomState(seed)
    queue = _lhs(n_initial, rng)
    X_obs, y_obs = [], []
    best  = {"rmse": float("inf")}

    try:
        while True:
            if queue:
                params = queue.pop(0)
                phase  = "LHS"
            else:
                params = _next_ei(np.array(X_obs), np.array(y_obs), rng)
                phase  = "GP+EI"
            print("  [{}] s0={:.2f} h0={:.2f} ss={:.2f} n={:.3f}".format(
                  phase, *params))
            rmse = _objective(params)
            X_obs.append(params)
            y_obs.append(rmse)
            if rmse < best["rmse"]:
                best = {"s0": params[0], "h0": params[1],
                        "ss": params[2], "n": params[3], "rmse": rmse}
    except CalibrationConverged as e:
        print("\n[Tool 1] Stopped: {}".format(e))

    best["algorithm"] = "Bayesian Optimization (LHS + GP+EI)"
    return best


# ─────────────────────────────────────────────────────────────────
# Tool 2: Differential Evolution
# ─────────────────────────────────────────────────────────────────

def run_differential_evolution(popsize=3, seed=42):
    """
    Tool 2: Differential Evolution — population-based global search.
    Best for: broad global exploration, avoiding local minima.
    """
    from scipy.optimize import differential_evolution
    print("\n[Tool 2] Differential Evolution")

    # Track best in closure so we always have it even if CalibrationConverged is raised
    best = {"rmse": float("inf")}

    def tracked_objective(params):
        rmse = _objective(params)
        if rmse < best.get("rmse", float("inf")):
            best.update({"s0": params[0], "h0": params[1],
                         "ss": params[2], "n":  params[3], "rmse": rmse})
        return rmse

    try:
        result = differential_evolution(
            tracked_objective, BOUNDS,
            strategy="best1bin", maxiter=1000,
            popsize=popsize, tol=0.001,
            mutation=(0.5, 1.0), recombination=0.7,
            seed=seed, disp=True, polish=False,
        )
        best.update({"s0": result.x[0], "h0": result.x[1],
                     "ss": result.x[2], "n":  result.x[3], "rmse": result.fun})
    except CalibrationConverged as e:
        print("\n[Tool 2] Stopped: {}".format(e))

    best["algorithm"] = "Differential Evolution"
    return best


# ─────────────────────────────────────────────────────────────────
# Tool 3: Nelder-Mead Simplex
# ─────────────────────────────────────────────────────────────────

def run_nelder_mead(seed=42):
    """
    Tool 3: Nelder-Mead Simplex — fast local optimizer.
    Best for: local refinement near a known good region.
    """
    from scipy.optimize import minimize
    print("\n[Tool 3] Nelder-Mead Simplex")

    rng = np.random.RandomState(seed)
    x0  = np.array([(lo + hi) / 2.0 + rng.uniform(-0.05, 0.05) * (hi - lo)
                    for lo, hi in BOUNDS])

    def bounded_obj(params):
        clipped = [np.clip(p, lo, hi) for p, (lo, hi) in zip(params, BOUNDS)]
        return _objective(clipped)

    best = {"rmse": float("inf")}

    def tracked_bounded_obj(params):
        clipped = [np.clip(p, lo, hi) for p, (lo, hi) in zip(params, BOUNDS)]
        rmse = _objective(clipped)
        if rmse < best.get("rmse", float("inf")):
            best.update({"s0": clipped[0], "h0": clipped[1],
                         "ss": clipped[2], "n":  clipped[3], "rmse": rmse})
        return rmse

    try:
        result = minimize(tracked_bounded_obj, x0, method="Nelder-Mead",
                          options={"maxiter": 1000, "xatol": 0.01,
                                   "fatol": 0.1, "disp": True})
        params = [np.clip(p, lo, hi) for p, (lo, hi) in zip(result.x, BOUNDS)]
        best.update({"s0": params[0], "h0": params[1],
                     "ss": params[2], "n":  params[3], "rmse": result.fun})
    except CalibrationConverged as e:
        print("\n[Tool 3] Stopped: {}".format(e))

    best["algorithm"] = "Nelder-Mead Simplex"
    return best


# ─────────────────────────────────────────────────────────────────
# Tool 4: Random Search + Bayesian Optimization
# ─────────────────────────────────────────────────────────────────

def run_random_bo(n_random=15, seed=42):
    """
    Tool 4: Random Search then Bayesian Optimization.
    Phase 1: n_random purely random evaluations.
    Phase 2: GP+EI Bayesian Optimization.
    Best for: simple baseline with BO exploitation.
    """
    print("\n[Tool 4] Random Search + Bayesian Optimization")
    rng    = np.random.RandomState(seed)
    X_obs, y_obs = [], []
    best   = {"rmse": float("inf")}

    try:
        # Phase 1: random
        for _ in range(n_random):
            params = [rng.uniform(lo, hi) for lo, hi in BOUNDS]
            print("  [Random] s0={:.2f} h0={:.2f} ss={:.2f} n={:.3f}".format(*params))
            rmse = _objective(params)
            X_obs.append(params)
            y_obs.append(rmse)
            if rmse < best["rmse"]:
                best = {"s0": params[0], "h0": params[1],
                        "ss": params[2], "n": params[3], "rmse": rmse}

        # Phase 2: GP+EI
        while True:
            params = _next_ei(np.array(X_obs), np.array(y_obs), rng)
            print("  [BO] s0={:.2f} h0={:.2f} ss={:.2f} n={:.3f}".format(*params))
            rmse = _objective(params)
            X_obs.append(params)
            y_obs.append(rmse)
            if rmse < best["rmse"]:
                best = {"s0": params[0], "h0": params[1],
                        "ss": params[2], "n": params[3], "rmse": rmse}

    except CalibrationConverged as e:
        print("\n[Tool 4] Stopped: {}".format(e))

    best["algorithm"] = "Random Search + Bayesian Optimization"
    return best


# ── Tool registry ─────────────────────────────────────────────────

TOOL_REGISTRY = {
    "bayesian":               run_bayesian_optimization,
    "differential_evolution": run_differential_evolution,
    "nelder_mead":            run_nelder_mead,
    "random_bo":              run_random_bo,
}

TOOL_DESCRIPTIONS = {
    "bayesian": (
        "Bayesian Optimization (LHS + GP+EI). "
        "Best for expensive simulations. Most sample-efficient. "
        "Recommended for calibration problems."
    ),
    "differential_evolution": (
        "Differential Evolution. Population-based global search. "
        "Good for avoiding local minima. Needs more evaluations than Bayesian."
    ),
    "nelder_mead": (
        "Nelder-Mead Simplex. Fast local optimizer. "
        "Best when starting near a good region. May get stuck in local minima."
    ),
    "random_bo": (
        "Random Search then Bayesian Optimization. "
        "Simple baseline with BO exploitation phase."
    ),
}
