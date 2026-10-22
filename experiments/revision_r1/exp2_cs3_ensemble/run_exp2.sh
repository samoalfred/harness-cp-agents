#!/usr/bin/env bash
# Convenience wrapper for Experiment 2 (CS3 realization ensemble). Run inside WSL.
# NO OpenAI key needed - this drives MATLAB + PRISMS, not the LLM.
# Phase 1 is sim-heavy (len(seeds) x 15 forward runs); Phase 2 (re-score) is instant.
set -e
cd "$(dirname "$0")"
# Pass through any args (e.g. --seeds 0 1 2, or --rescore-only)
python3.7 run_ensemble.py "$@"
