#!/usr/bin/env bash
# Convenience wrapper for Experiment 3 (robustness). Run from inside WSL.
# Reads OPENAI_API_KEY from the environment, or from a local exp.env file
# (exp.env is git-ignored; put: OPENAI_API_KEY=sk-...  on one line).
set -e
cd "$(dirname "$0")"
if [ -z "$OPENAI_API_KEY" ] && [ -f exp.env ]; then
  set -a; . ./exp.env; set +a
fi
if [ -z "$OPENAI_API_KEY" ]; then
  echo "OPENAI_API_KEY not set. export it or put it in exp.env"; exit 1
fi
N="${1:-5}"
python3.7 run_robustness.py --scenario all --n "$N"
