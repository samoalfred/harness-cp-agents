# -*- coding: utf-8 -*-
"""
run_pipeline.py — Entry point for CS4 (multi-pass HCP Mg texture evolution).

Pure goal-driven ReAct agent: the LLM receives the goal (config.DEFAULT_QUERY) and
the tool list only. It reasons about which tools to call and in what order,
orchestrating the five-pass chain, then reports.

Usage:
    export OPENAI_API_KEY='sk-...'
    python3.7 run_pipeline.py                          # uses config.DEFAULT_QUERY
    python3.7 run_pipeline.py --query "custom query"
"""
import os, sys, argparse
if not os.environ.get("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY is not set.  export OPENAI_API_KEY='sk-...'")
    sys.exit(1)

import config
from agents.react_agent import ReactAgent


def main():
    ap = argparse.ArgumentParser(description="CS4 multi-pass Mg texture evolution — ReAct pipeline")
    ap.add_argument("--query", type=str, default=None)
    args = ap.parse_args()
    query = args.query if args.query else config.DEFAULT_QUERY
    ReactAgent().run(query)
    return 0


if __name__ == "__main__":
    sys.exit(main())
