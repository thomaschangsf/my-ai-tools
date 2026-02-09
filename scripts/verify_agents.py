#!/usr/bin/env python3
"""
Verify hello_world and plan_with_ollama agents.
Run from repo root: uv run python scripts/verify_agents.py
"""
import sys
import tempfile
import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from my_ai_tools.agents.hello_world import run_hello
from my_ai_tools.agents.plan_with_ollama import plan_with_ollama, resume_plan_with_ollama


def verify_hello_world() -> bool:
    """Run hello_world agent and check output."""
    out = run_hello("verify")
    expected = "Global Agent Response: verify"
    ok = out == expected
    print(f"  hello_world: {out}")
    print(f"  expected:    {expected}")
    return ok


def verify_plan_with_ollama() -> bool:
    """Run plan_with_ollama (Planner -> review -> Interfacer -> review -> Executor) in a temp dir.

    Automatically approves at each review checkpoint so the full pipeline runs.
    """
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "agents_state.db"
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        checkpointer = SqliteSaver(conn)
        checkpointer.setup()
        thread_id = "verify-1"
        try:
            # Start the flow — runs planner, then pauses before plan_review
            plan_with_ollama(
                task_description="Add a function add(a,b) that returns a+b.",
                project_root=tmp,
                thread_id=thread_id,
                checkpointer=checkpointer,
            )

            # Approve plan — runs plan_review + interfacer, pauses before interface_review
            resume_plan_with_ollama(
                thread_id=thread_id,
                human_feedback="approved",
                checkpointer=checkpointer,
            )

            # Approve interface — runs interface_review + executor, completes
            resume_plan_with_ollama(
                thread_id=thread_id,
                human_feedback="approved",
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

    print("2. plan_with_ollama (requires Ollama running; uses OLLAMA_MODEL, default llama3.2)")
    try:
        if verify_plan_with_ollama():
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
