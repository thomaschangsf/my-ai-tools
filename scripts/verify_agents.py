#!/usr/bin/env python3
"""
Verify hello_world and principal_flow agents.
Run from repo root: uv run python scripts/verify_agents.py
"""
import sys
import tempfile
import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from my_ai_tools.agents.hello_world import run_hello
from my_ai_tools.agents.principal_flow import run_principal_flow


def verify_hello_world() -> bool:
    """Run hello_world agent and check output."""
    out = run_hello("verify")
    expected = "Global Agent Response: verify"
    ok = out == expected
    print(f"  hello_world: {out}")
    print(f"  expected:    {expected}")
    return ok


def verify_principal_flow() -> bool:
    """Run principal_flow (Planner -> Interfacer -> Executor) in a temp dir."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "agents_state.db"
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        checkpointer = SqliteSaver(conn)
        try:
            run_principal_flow(
                task_description="Add a function add(a,b) that returns a+b.",
                project_root=tmp,
                thread_id="verify-1",
                checkpointer=checkpointer,
            )
        finally:
            conn.close()

        plan = Path(tmp) / "plan.md"
        interface = Path(tmp) / "interface.md"
        code = Path(tmp) / "generated_module.py"
        test = Path(tmp) / "test_baseline.py"

        ok = plan.exists() and interface.exists() and code.exists() and test.exists()
        print(f"  plan.md:             {plan.exists()} ({plan.stat().st_size if plan.exists() else 0} bytes)")
        print(f"  interface.md:        {interface.exists()} ({interface.stat().st_size if interface.exists() else 0} bytes)")
        print(f"  generated_module.py: {code.exists()} ({code.stat().st_size if code.exists() else 0} bytes)")
        print(f"  test_baseline.py:    {test.exists()} ({test.stat().st_size if test.exists() else 0} bytes)")
    return ok


def main() -> None:
    print("Verifying agents (run from repo root)...\n")

    print("1. hello_world")
    if verify_hello_world():
        print("   OK\n")
    else:
        print("   FAIL\n")
        sys.exit(1)

    print("2. principal_flow (requires Ollama running; uses OLLAMA_MODEL, default llama3.2)")
    try:
        if verify_principal_flow():
            print("   OK\n")
        else:
            print("   FAIL (missing output files)\n")
            sys.exit(1)
    except Exception as e:
        print(f"   FAIL: {e}")
        print("   Ensure Ollama is running (e.g. uv run ollama-serve) and a model is pulled (ollama pull llama3.2)\n")
        sys.exit(1)

    print("All agents verified.")


if __name__ == "__main__":
    main()
