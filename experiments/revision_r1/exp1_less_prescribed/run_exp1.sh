#!/usr/bin/env bash
# Convenience wrapper for Experiment 1 (1a + 1b). Run from inside WSL.
# Reads OPENAI_API_KEY from the environment, or from a local exp.env file
# (put: OPENAI_API_KEY=sk-...  on one line).
set -e
cd "$(dirname "$0")"
if [ -z "$OPENAI_API_KEY" ] && [ -f exp.env ]; then
  set -a; . ./exp.env; set +a
fi
if [ -z "$OPENAI_API_KEY" ]; then
  echo "OPENAI_API_KEY not set. export it or put it in exp.env"; exit 1
fi
N="${1:-10}"
echo "########## 1a: CS1 optimizer selection (n=$N) ##########"
python3.7 run_exp1.py --case 1a --n "$N"
echo
echo "########## 1b: CS3 strategy + budget (n=$N) ##########"
python3.7 run_exp1.py --case 1b --n "$N"
