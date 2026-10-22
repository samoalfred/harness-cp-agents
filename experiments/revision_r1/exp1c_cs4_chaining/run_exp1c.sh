#!/usr/bin/env bash
# Convenience wrapper for Experiment 1c (CS4 chaining). Run from inside WSL.
# Reads OPENAI_API_KEY from the environment, or from a local exp.env file.
set -e
cd "$(dirname "$0")"
if [ -z "$OPENAI_API_KEY" ] && [ -f exp.env ]; then
  set -a; . ./exp.env; set +a
fi
if [ -z "$OPENAI_API_KEY" ]; then
  echo "OPENAI_API_KEY not set. export it or put it in exp.env"; exit 1
fi
N="${1:-5}"
python3.7 run_exp1c.py --n "$N"
