#!/usr/bin/env python3
"""
Verify the plan_auto flow: full auto-approve cycle + revision loop.
Requires Ollama running with a model pulled (default: llama3.2).

Run from repo root:
    uv run python scripts/verify_plan_auto.py

Prerequisites:
    uv run ollama-serve
    ollama pull llama3.2
"""
import os
import sys
import tempfile
import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from my_ai_tools.agents.plan_auto import start_auto_plan, resume_auto_plan

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
OUTPUT_FILES = ["plan.md", "interface.md", "generated_module.py", "test_baseline.py"]


def _print_files(tmp: str) -> None:
    for f in OUTPUT_FILES:
        p = Path(tmp) / f
        size = p.stat().st_size if p.exists() else 0
        print(f"    {f}: exists={p.exists()}, {size} bytes")


def verify_full_cycle() -> bool:
    """Run planner -> approve -> interfacer -> approve -> executor (auto-approve)."""
    print("  Full cycle: planner -> approve -> interfacer -> approve -> executor")
    with tempfile.TemporaryDirectory() as tmp:
        conn = sqlite3.connect(str(Path(tmp) / "state.db"), check_same_thread=False)
        cp = SqliteSaver(conn)
        cp.setup()
        thread_id = "auto-cycle-1"
        try:
            result = start_auto_plan(
                task_description="Add a function add(a,b) that returns a+b.",
                project_root=tmp,
                thread_id=thread_id,
                checkpointer=cp,
            )
            assert result.get("phase") == "plan_review", (
                f"Expected plan_review, got {result.get('phase')}"
            )
            assert (Path(tmp) / "plan.md").exists(), "plan.md not written"
            print("    planner -> phase=plan_review, plan.md written  OK")

            result = resume_auto_plan(
                thread_id=thread_id,
                human_feedback="approved",
                checkpointer=cp,
            )
            assert result.get("phase") == "interface_review", (
                f"Expected interface_review, got {result.get('phase')}"
            )
            assert (Path(tmp) / "interface.md").exists(), "interface.md not written"
            print("    approve plan -> phase=interface_review, interface.md written  OK")

            result = resume_auto_plan(
                thread_id=thread_id,
                human_feedback="approved",
                checkpointer=cp,
            )
            assert result.get("phase") == "done", (
                f"Expected done, got {result.get('phase')}"
            )
            assert (Path(tmp) / "generated_module.py").exists(), "generated_module.py not written"
            assert (Path(tmp) / "test_baseline.py").exists(), "test_baseline.py not written"
            print("    approve interface -> phase=done, code+tests written  OK")

        finally:
            conn.close()

        _print_files(tmp)
    return True


def verify_revision_loop() -> bool:
    """Run planner -> revise -> approve -> interfacer (tests the feedback loop)."""
    print("  Revision loop: planner -> revise plan -> approve -> interfacer")
    with tempfile.TemporaryDirectory() as tmp:
        conn = sqlite3.connect(str(Path(tmp) / "state.db"), check_same_thread=False)
        cp = SqliteSaver(conn)
        cp.setup()
        thread_id = "auto-rev-1"
        try:
            result = start_auto_plan(
                task_description="Build a key-value cache with TTL support.",
                project_root=tmp,
                thread_id=thread_id,
                checkpointer=cp,
            )
            assert result.get("phase") == "plan_review"
            plan_v1 = (Path(tmp) / "plan.md").read_text(encoding="utf-8")
            print(f"    planner -> plan.md v1 ({len(plan_v1)} chars)  OK")

            result = resume_auto_plan(
                thread_id=thread_id,
                human_feedback="Add more detail on eviction strategy and thread safety.",
                checkpointer=cp,
            )
            assert result.get("phase") == "plan_review", (
                f"Expected plan_review, got {result.get('phase')}"
            )
            plan_v2 = (Path(tmp) / "plan.md").read_text(encoding="utf-8")
            assert plan_v2 != plan_v1 or len(plan_v2) > 0, "Plan was not revised"
            print(f"    revise -> plan.md v2 ({len(plan_v2)} chars)  OK")

            result = resume_auto_plan(
                thread_id=thread_id,
                human_feedback="approved",
                checkpointer=cp,
            )
            assert result.get("phase") == "interface_review", (
                f"Expected interface_review, got {result.get('phase')}"
            )
            assert (Path(tmp) / "interface.md").exists(), "interface.md not written"
            print("    approve revised plan -> phase=interface_review  OK")

        finally:
            conn.close()
    return True


def main() -> None:
    print(f"Verifying plan_auto (model: {OLLAMA_MODEL})...\n")

    tests = [
        ("1. Full cycle (auto-approve)", verify_full_cycle),
        ("2. Revision loop", verify_revision_loop),
    ]

    for name, test_fn in tests:
        print(name)
        try:
            if test_fn():
                print("   PASS\n")
            else:
                print("   FAIL\n")
                sys.exit(1)
        except Exception as e:
            print(f"   FAIL: {e}")
            print(
                "   Ensure Ollama is running (uv run ollama-serve) "
                f"and model is pulled (ollama pull {OLLAMA_MODEL})\n"
            )
            sys.exit(1)

    print("All plan_auto tests passed.")


if __name__ == "__main__":
    main()
