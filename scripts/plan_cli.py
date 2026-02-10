#!/usr/bin/env python3
"""
Interactive CLI for the interactive planning flow.

Uses the same LangGraph graph as plan_interactive but drives it from the
terminal with a configurable LLM backend (Ollama by default).

Usage:
    uv run python scripts/plan_cli.py "Build a URL shortener" /tmp/my-project

Environment variables:
    PLANNING_LLM      LLM backend: "ollama" (default), "anthropic", or "none" (manual paste)
    OLLAMA_MODEL      Ollama model name (default: llama3.2)
    ANTHROPIC_API_KEY Anthropic API key (required for "anthropic" backend)
    ANTHROPIC_MODEL   Anthropic model (default: claude-sonnet-4-20250514)
"""

import os
import sqlite3
import sys
import uuid
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from my_ai_tools.agents.plan_interactive import start_interactive_plan, resume_interactive_plan

PLANNING_LLM = os.environ.get("PLANNING_LLM", "ollama")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")


def _generate_with_ollama(context: str) -> str:
    """Send context to Ollama and return the response."""
    import ollama

    r = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": "You are a principal ML engineer. Follow the instructions in the context precisely. Output only the requested content, no preamble."},
            {"role": "user", "content": context},
        ],
    )
    return (r.get("message") or {}).get("content", "").strip()


def _generate_with_anthropic(context: str) -> str:
    """Send context to the Anthropic API and return the response."""
    from my_ai_tools.agents.plan_auto_anthropic import _chat

    system = (
        "You are a principal ML engineer. Follow the instructions in the context "
        "precisely. Output only the requested content, no preamble."
    )
    return _chat(system, context)


def _generate_with_manual(context: str) -> str:
    """Print context and let the user paste content manually."""
    print("\n--- Paste your content below (end with a line containing only 'END') ---")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def _generate(context: str) -> str:
    """Route to the configured LLM backend."""
    if PLANNING_LLM == "ollama":
        return _generate_with_ollama(context)
    elif PLANNING_LLM == "anthropic":
        return _generate_with_anthropic(context)
    elif PLANNING_LLM == "none":
        return _generate_with_manual(context)
    else:
        print(
            f"Unknown PLANNING_LLM={PLANNING_LLM!r}. "
            "Use 'ollama', 'anthropic', or 'none'.",
            file=sys.stderr,
        )
        sys.exit(1)


def _prompt_review(phase: str, project_root: str) -> str:
    """Ask the user to review the artifact and provide feedback."""
    files = {"plan": "plan.md", "interface": "interface.md", "code": "generated_module.py"}
    filename = files.get(phase, "")
    if filename:
        filepath = Path(project_root) / filename
        print(f"\n--- Review {filepath} ---")

    print("\nOptions:")
    print("  [enter]   Accept and continue")
    print("  [text]    Revision feedback (loops back to regenerate)")
    print("  [q]       Quit")
    response = input("\nFeedback: ").strip()
    if response.lower() == "q":
        print("Aborted.")
        sys.exit(0)
    return response


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <task_description> [project_root]", file=sys.stderr)
        sys.exit(1)

    task = sys.argv[1]
    project_root = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
    project_root = str(Path(project_root).resolve())

    # Set up checkpointer
    db_path = Path(project_root) / ".planning_state.db"
    Path(project_root).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    checkpointer.setup()
    thread_id = str(uuid.uuid4())

    print(f"Planning: {task}")
    print(f"Project:  {project_root}")
    llm_detail = ""
    if PLANNING_LLM == "ollama":
        llm_detail = f" ({OLLAMA_MODEL})"
    elif PLANNING_LLM == "anthropic":
        llm_detail = f" ({os.environ.get('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')})"
    print(f"LLM:      {PLANNING_LLM}{llm_detail}")
    print(f"Thread:   {thread_id}")

    try:
        # Start — assemble plan context
        result = start_interactive_plan(
            task_description=task,
            project_root=project_root,
            thread_id=thread_id,
            checkpointer=checkpointer,
        )

        while True:
            phase = result.get("phase", "done")
            context = result.get("context_bundle", "")

            if phase == "done":
                print(f"\nDone! Files written to {project_root}:")
                print("  - plan.md")
                print("  - interface.md")
                print("  - generated_module.py")
                print("  - test_baseline.py")
                break

            print(f"\n{'='*60}")
            print(f"Phase: {phase}")
            print(f"{'='*60}")

            # Generate content via LLM
            print(f"\nGenerating {phase} content via {PLANNING_LLM}...")
            content = _generate(context)
            print(f"\n--- Generated content ({len(content)} chars) ---")
            print(content[:500] + ("..." if len(content) > 500 else ""))

            # Save and advance
            result = resume_interactive_plan(
                thread_id=thread_id,
                content=content,
                checkpointer=checkpointer,
            )

            # Review
            phase = result.get("phase", "done")
            if phase == "done":
                continue

            feedback = _prompt_review(phase, project_root)
            if feedback:
                # Revision loop
                result = resume_interactive_plan(
                    thread_id=thread_id,
                    feedback=feedback,
                    checkpointer=checkpointer,
                )
                # Loop back — will regenerate with updated context
            # else: accepted, loop continues with next phase context already in result

    finally:
        conn.close()


if __name__ == "__main__":
    main()
