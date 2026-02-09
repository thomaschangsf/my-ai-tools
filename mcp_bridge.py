"""
MCP bridge for Global Stateful AI Agent Orchestrator.
Cursor entry point: run this file so Cursor can invoke run_hello and plan_with_ollama.
"""
import os
import sqlite3
import uuid
from pathlib import Path

from fastmcp import FastMCP
from langgraph.checkpoint.sqlite import SqliteSaver

from my_ai_tools.agents.hello_world import run_hello as _run_hello
from my_ai_tools.agents.plan_with_ollama import (
    plan_with_ollama as _plan_with_ollama,
    resume_plan_with_ollama as _resume_plan_with_ollama,
)

# SQLite checkpointer in global directory (same dir as this file; not the target project)
_REPO_ROOT = Path(__file__).resolve().parent
_AGENTS_DB = _REPO_ROOT / "agents_state.db"
_conn = sqlite3.connect(str(_AGENTS_DB), check_same_thread=False)
_checkpointer = SqliteSaver(_conn)
_checkpointer.setup()

mcp = FastMCP("GlobalAgents")


@mcp.tool()
def run_hello(input_text: str) -> str:
    """Invoke the hello_world agent. Returns a string with 'Global Agent Response:' prepended to the input."""
    return _run_hello(input_text or "")


@mcp.tool()
def plan_with_ollama(task_description: str, project_root: str = "") -> str:
    """
    Start the Ollama-backed planning flow: Planner -> [Review] -> Interfacer -> [Review] -> Executor.

    The flow pauses after the planner writes plan.md so you can review it.
    Call resume_flow with the returned thread_id and either 'approved' to
    proceed or revision feedback to regenerate the plan.
    """
    project_path = (project_root or os.getcwd()).strip()
    thread_id = str(uuid.uuid4())
    try:
        _plan_with_ollama(
            task_description=task_description,
            project_root=project_path,
            thread_id=thread_id,
            checkpointer=_checkpointer,
        )
        return (
            f"Plan written to {project_path}/plan.md\n"
            f"Thread ID: {thread_id}\n\n"
            f"Review plan.md, then call resume_flow with this thread_id "
            f"and feedback ('approved' to proceed, or revision notes)."
        )
    except Exception as e:
        return f"Planning flow error: {e}"


@mcp.tool()
def resume_flow(thread_id: str, feedback: str) -> str:
    """
    Resume the planning flow after human review.

    - feedback='approved': proceed to the next phase.
    - feedback='<revision notes>': revise the current artifact with the given feedback.

    The flow pauses again after each phase for review, until execution completes.
    """
    try:
        result = _resume_plan_with_ollama(
            thread_id=thread_id,
            human_feedback=feedback,
            checkpointer=_checkpointer,
        )
        phase = result.get("phase", "unknown")
        project_root = result.get("project_root", "")

        if phase == "plan_review":
            return (
                f"Plan revised and written to {project_root}/plan.md\n"
                f"Thread ID: {thread_id}\n\n"
                f"Review the updated plan.md, then call resume_flow again."
            )
        elif phase == "interface_review":
            return (
                f"Interface written to {project_root}/interface.md\n"
                f"Thread ID: {thread_id}\n\n"
                f"Review interface.md, then call resume_flow with feedback."
            )
        elif phase == "done":
            return (
                f"Planning flow completed. Outputs written to {project_root}:\n"
                f"  - plan.md\n"
                f"  - interface.md\n"
                f"  - generated_module.py\n"
                f"  - test_baseline.py"
            )
        else:
            return f"Flow in phase '{phase}'. Thread ID: {thread_id}"
    except Exception as e:
        return f"Resume flow error: {e}"


if __name__ == "__main__":
    mcp.run()
