#!/bin/bash
# Run the reliability study for all three case studies, one process each
# (the case folders reuse module names, so they cannot share a process).
# Usage: ./run_all.sh [N]     (default N=20 reps per case)
set -e
N="${1:-20}"
for c in CS1 CS2 CS3; do
    echo ""
    echo "########################## $c ##########################"
    python3.7 run_reliability.py --case "$c" --n "$N"
done
