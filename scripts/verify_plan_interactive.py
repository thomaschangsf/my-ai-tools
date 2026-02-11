#!/usr/bin/env python3
"""
Verify the plan_interactive graph: full cycle + revision loop + cross-session.
No LLM needed — uses hardcoded content to exercise the state machine.

Run from repo root: uv run python scripts/verify_plan_interactive.py
"""
import sys
import tempfile
import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from my_ai_tools.agents.plan_interactive import start_interactive_plan, resume_interactive_plan
from my_ai_tools.agents.planning_common import load_skill


def verify_full_cycle() -> bool:
    """Run start -> 3x resume(content=...) through all phases."""
    print("  Full cycle: plan -> interface -> code -> done")
    with tempfile.TemporaryDirectory() as tmp:
        conn = sqlite3.connect(str(Path(tmp) / "state.db"), check_same_thread=False)
        cp = SqliteSaver(conn)
        cp.setup()
        try:
            result = start_interactive_plan(
                "Add a function add(a,b) that returns a+b.",
                tmp, thread_id="cycle-1", checkpointer=cp,
            )
            assert result["phase"] == "plan", f"Expected plan, got {result['phase']}"
            assert len(result.get("context_bundle", "")) > 0, "Empty context_bundle"
            skill = load_skill()
            if skill:
                assert (
                    "Planning Framework" in result.get("context_bundle", "")
                ), "Expected SKILL.md content in context_bundle"
                print("    start -> phase=plan, context includes SKILL.md  OK")
            else:
                print("    start -> phase=plan, SKILL.md not found (optional)  OK")

            result = resume_interactive_plan(
                thread_id="cycle-1",
                content="# Plan\nImplement add(a,b) returning a+b.",
                checkpointer=cp,
            )
            assert result["phase"] == "interface", f"Expected interface, got {result['phase']}"
            assert (Path(tmp) / "plan.md").exists(), "plan.md not written"
            print("    resume(content=plan) -> phase=interface, plan.md written  OK")

            result = resume_interactive_plan(
                thread_id="cycle-1",
                content="# Interface\ndef add(a: int, b: int) -> int: ...",
                checkpointer=cp,
            )
            assert result["phase"] == "code", f"Expected code, got {result['phase']}"
            assert (Path(tmp) / "interface.md").exists(), "interface.md not written"
            print("    resume(content=interface) -> phase=code, interface.md written  OK")

            result = resume_interactive_plan(
                thread_id="cycle-1",
                content=(
                    "## MODULE\n"
                    "def add(a, b):\n    return a + b\n"
                    "## TEST\n"
                    "def test_add():\n    assert add(1, 2) == 3\n"
                ),
                checkpointer=cp,
            )
            assert result["phase"] == "done", f"Expected done, got {result['phase']}"
            assert (Path(tmp) / "generated_module.py").exists(), "generated_module.py not written"
            assert (Path(tmp) / "test_baseline.py").exists(), "test_baseline.py not written"
            print("    resume(content=code) -> phase=done, code+tests written  OK")

        finally:
            conn.close()
    return True


def verify_revision_loop() -> bool:
    """Verify that feedback loops back to the same phase with updated context."""
    print("  Revision loop: plan -> feedback -> revised plan -> interface")
    with tempfile.TemporaryDirectory() as tmp:
        conn = sqlite3.connect(str(Path(tmp) / "state.db"), check_same_thread=False)
        cp = SqliteSaver(conn)
        cp.setup()
        try:
            result = start_interactive_plan(
                "Build a cache", tmp, thread_id="rev-1", checkpointer=cp,
            )
            assert result["phase"] == "plan"

            result = resume_interactive_plan(
                thread_id="rev-1",
                content="# Plan v1: simple cache",
                checkpointer=cp,
            )
            assert result["phase"] == "interface"
            print("    plan saved -> phase=interface  OK")

            result = resume_interactive_plan(
                thread_id="rev-1",
                feedback="Add TTL support to the interface",
                checkpointer=cp,
            )
            assert result["phase"] == "interface", f"Expected interface, got {result['phase']}"
            assert "TTL" in result.get("context_bundle", ""), "Feedback not in context"
            print("    feedback('Add TTL') -> phase=interface, feedback in context  OK")

            result = resume_interactive_plan(
                thread_id="rev-1",
                content="# Interface v2\ndef get(key): ...\ndef set(key, val, ttl=None): ...",
                checkpointer=cp,
            )
            assert result["phase"] == "code", f"Expected code, got {result['phase']}"
            iface = (Path(tmp) / "interface.md").read_text()
            assert "TTL" in iface or "ttl" in iface, "Revised interface not saved"
            print("    resume(content=revised interface) -> phase=code  OK")

        finally:
            conn.close()
    return True


def verify_cross_session() -> bool:
    """Verify that closing and reopening the checkpointer preserves state."""
    print("  Cross-session: start, close, reopen, resume")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "state.db")

        conn1 = sqlite3.connect(db_path, check_same_thread=False)
        cp1 = SqliteSaver(conn1)
        cp1.setup()
        result = start_interactive_plan(
            "Build an API", tmp, thread_id="xsess-1", checkpointer=cp1,
        )
        assert result["phase"] == "plan"
        conn1.close()
        print("    Session 1: started, phase=plan, closed  OK")

        conn2 = sqlite3.connect(db_path, check_same_thread=False)
        cp2 = SqliteSaver(conn2)
        cp2.setup()
        result = resume_interactive_plan(
            thread_id="xsess-1",
            content="# Plan: REST API with FastAPI",
            checkpointer=cp2,
        )
        assert result["phase"] == "interface", f"Expected interface, got {result['phase']}"
        assert (Path(tmp) / "plan.md").exists(), "plan.md not written after resume"
        conn2.close()
        print("    Session 2: resumed, phase=interface, plan.md written  OK")

    return True


def main() -> None:
    print("Verifying plan_interactive (no LLM needed)...\n")

    tests = [
        ("1. Full cycle", verify_full_cycle),
        ("2. Revision loop", verify_revision_loop),
        ("3. Cross-session persistence", verify_cross_session),
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
            print(f"   FAIL: {e}\n")
            sys.exit(1)

    print("All plan_interactive tests passed.")


if __name__ == "__main__":
    main()
