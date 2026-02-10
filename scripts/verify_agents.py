#!/usr/bin/env python3
"""
Verify all agents: hello_world, plan_interactive, and plan_auto.
Run from repo root: uv run python scripts/verify_agents.py

- hello_world: no external dependencies
- plan_interactive: no external dependencies (no LLM needed)
- plan_auto: requires Ollama running with a model pulled
"""
import os
import subprocess
import sys

from my_ai_tools.agents.hello_world import run_hello


def verify_hello_world() -> bool:
    """Run hello_world agent and check output."""
    out = run_hello("verify")
    expected = "Global Agent Response: verify"
    ok = out == expected
    print(f"  hello_world: {out}")
    print(f"  expected:    {expected}")
    return ok


def _run_script(name: str, script: str) -> bool:
    """Run a verification script as a subprocess. Returns True if it passes."""
    root = os.getcwd()
    path = os.path.join(root, "scripts", script)
    return subprocess.call([sys.executable, path], cwd=root) == 0


def main() -> None:
    print("Verifying agents (run from repo root)...\n")

    print("1. hello_world")
    if verify_hello_world():
        print("   PASS\n")
    else:
        print("   FAIL\n")
        sys.exit(1)

    print("2. plan_interactive (no LLM needed)")
    if _run_script("plan_interactive", "verify_plan_interactive.py"):
        print("   PASS\n")
    else:
        print("   FAIL\n")
        sys.exit(1)

    print("3. plan_auto (requires Ollama running; uses OLLAMA_MODEL, default llama3.2)")
    if _run_script("plan_auto", "verify_plan_auto.py"):
        print("   PASS\n")
    else:
        print("   FAIL")
        print("   Ensure Ollama is running (uv run ollama-serve) and a model is pulled (ollama pull llama3.2)\n")
        sys.exit(1)

    print("All agents verified.")


if __name__ == "__main__":
    main()
