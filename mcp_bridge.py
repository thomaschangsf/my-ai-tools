"""
MCP bridge for Global Stateful AI Agent Orchestrator.
Cursor entry point: run this file so Cursor can invoke the planning tools.
"""
import os
import sqlite3
import uuid
from pathlib import Path

from fastmcp import FastMCP
from langgraph.checkpoint.sqlite import SqliteSaver

from my_ai_tools.agents.hello_world import run_hello as _run_hello
from my_ai_tools.agents.plan_auto import (
    start_auto_plan as _start_auto_plan,
    resume_auto_plan as _resume_auto_plan,
)
from my_ai_tools.agents.plan_interactive import (
    start_interactive_plan as _start_interactive_plan,
    resume_interactive_plan as _resume_interactive_plan,
)
from my_ai_tools.agents.pr_review import (
    start_pr_review as _start_pr_review,
    resume_pr_review as _resume_pr_review,
)

# SQLite checkpointer in global directory (same dir as this file; not the target project)
_REPO_ROOT = Path(__file__).resolve().parent
_AGENTS_DB = _REPO_ROOT / "agents_state.db"
_conn = sqlite3.connect(str(_AGENTS_DB), check_same_thread=False)
_checkpointer = SqliteSaver(_conn)
_checkpointer.setup()

mcp = FastMCP("GlobalAgents")


# ---------------------------------------------------------------------------
# Hello world
# ---------------------------------------------------------------------------

@mcp.tool()
def run_hello(input_text: str) -> str:
    """Invoke the hello_world agent. Returns a string with 'Global Agent Response:' prepended to the input."""
    return _run_hello(input_text or "")


# ---------------------------------------------------------------------------
# Auto planning — LLM generates content internally (today: Ollama)
# ---------------------------------------------------------------------------

@mcp.tool()
def plan_auto_start(
    task_description: str, project_root: str = "", backend: str = "ollama"
) -> str:
    """
    Start the auto planning flow (LLM generates content internally).

    Planner -> [Review] -> Interfacer -> [Review] -> Executor.
    The flow pauses after the planner writes plan.md so you can review it.
    Call plan_auto_resume with the returned thread_id and either 'approved'
    to proceed or revision feedback.

    Args:
        backend: LLM backend — "ollama" (default) or "anthropic".
    """
    project_path = (project_root or os.getcwd()).strip()
    thread_id = str(uuid.uuid4())
    try:
        _start_auto_plan(
            task_description=task_description,
            project_root=project_path,
            thread_id=thread_id,
            checkpointer=_checkpointer,
            backend=backend,
        )
        return (
            f"Plan written to {project_path}/plan.md\n"
            f"Thread ID: {thread_id}\n"
            f"Backend: {backend}\n\n"
            f"Review plan.md, then call plan_auto_resume with this thread_id "
            f"and feedback ('approved' to proceed, or revision notes)."
        )
    except Exception as e:
        return f"Auto plan error: {e}"


@mcp.tool()
def plan_auto_resume(
    thread_id: str, feedback: str, backend: str = "ollama"
) -> str:
    """
    Resume the auto planning flow after human review.

    - feedback='approved': proceed to the next phase (LLM generates next artifact).
    - feedback='<revision notes>': LLM regenerates the current artifact with feedback.

    Args:
        backend: LLM backend — "ollama" (default) or "anthropic". Must match the
                 backend used in plan_auto_start for the same thread.
    """
    try:
        result = _resume_auto_plan(
            thread_id=thread_id,
            human_feedback=feedback,
            checkpointer=_checkpointer,
            backend=backend,
        )
        phase = result.get("phase", "unknown")
        project_root = result.get("project_root", "")

        if phase == "plan_review":
            return (
                f"Plan revised and written to {project_root}/plan.md\n"
                f"Thread ID: {thread_id}\n\n"
                f"Review the updated plan.md, then call plan_auto_resume again."
            )
        elif phase == "interface_review":
            return (
                f"Interface written to {project_root}/interface.md\n"
                f"Thread ID: {thread_id}\n\n"
                f"Review interface.md, then call plan_auto_resume with feedback."
            )
        elif phase == "done":
            return (
                f"Auto plan completed. Outputs written to {project_root}:\n"
                f"  - plan.md\n"
                f"  - interface.md\n"
                f"  - generated_module.py\n"
                f"  - test_baseline.py"
            )
        else:
            return f"Flow in phase '{phase}'. Thread ID: {thread_id}"
    except Exception as e:
        return f"Resume auto plan error: {e}"


# ---------------------------------------------------------------------------
# Interactive planning — caller provides content, graph manages state
# ---------------------------------------------------------------------------

@mcp.tool()
def plan_interactive_start(task_description: str, project_root: str = "") -> str:
    """
    Start an interactive planning session (LLM-agnostic).

    Returns a thread_id and a context bundle. Use the context to generate a plan,
    then call plan_interactive_resume with the thread_id and your generated content.
    """
    project_path = (project_root or os.getcwd()).strip()
    thread_id = str(uuid.uuid4())
    try:
        result = _start_interactive_plan(
            task_description=task_description,
            project_root=project_path,
            thread_id=thread_id,
            checkpointer=_checkpointer,
        )
        context = result.get("context_bundle", "")
        return (
            f"Thread ID: {thread_id}\n"
            f"Phase: plan\n\n"
            f"## Context\n\n{context}\n\n"
            f"---\n"
            f"Generate a plan based on the context above, then call plan_interactive_resume "
            f"with the thread_id and your generated content."
        )
    except Exception as e:
        return f"Start plan error: {e}"


@mcp.tool()
def plan_interactive_resume(thread_id: str, content: str = "", feedback: str = "") -> str:
    """
    Resume an interactive planning session.

    Provide exactly one of:
    - content: the generated artifact to save (advances to next phase)
    - feedback: revision notes (re-assembles context for the same phase)

    Returns the next phase's context bundle, or a completion message.
    """
    try:
        result = _resume_interactive_plan(
            thread_id=thread_id,
            content=content,
            feedback=feedback,
            checkpointer=_checkpointer,
        )
        phase = result.get("phase", "unknown")
        context = result.get("context_bundle", "")
        project_root = result.get("project_root", "")

        if phase == "done":
            return (
                f"Planning complete! Files written to {project_root}:\n"
                f"  - plan.md\n"
                f"  - interface.md\n"
                f"  - generated_module.py\n"
                f"  - test_baseline.py"
            )
        else:
            return (
                f"Thread ID: {thread_id}\n"
                f"Phase: {phase}\n\n"
                f"## Context\n\n{context}\n\n"
                f"---\n"
                f"Generate content for the '{phase}' phase based on the context above, "
                f"then call plan_interactive_resume with the thread_id and your generated content."
            )
    except Exception as e:
        return f"Resume plan error: {e}"


# ---------------------------------------------------------------------------
# PR review — one recommendation at a time, approve before next
# ---------------------------------------------------------------------------

@mcp.tool()
def pr_review_start(pr_url: str) -> str:
    """
    Start a PR review flow (pull PR locally, run review, show recommendations one at a time).

    Runs scripts/git-utils.sh pr_review_v2 to clone/fetch the PR, then runs the Principal ML
    Engineer review prompt. Returns the first recommendation and a thread_id.
    Call pr_review_resume with that thread_id and feedback 'approved' to get the next
    recommendation, or 'abort' to stop.
    """
    thread_id = str(uuid.uuid4())
    try:
        result = _start_pr_review(
            pr_url=pr_url,
            thread_id=thread_id,
            checkpointer=_checkpointer,
        )
        phase = result.get("phase", "")
        recommendations = result.get("recommendations") or []
        current_index = result.get("current_index", 0)
        repo_path = result.get("repo_path", "")
        if phase == "error":
            return (
                f"PR review error: {result.get('full_review_text', 'Unknown error')}\n"
                f"Thread ID: {thread_id}"
            )
        if not recommendations:
            return (
                f"No recommendations produced. Thread ID: {thread_id}\n"
                f"Repo path: {repo_path}"
            )
        first = recommendations[current_index] if current_index < len(recommendations) else recommendations[0]
        return (
            f"Thread ID: {thread_id}\n"
            f"Repo path: {repo_path}\n\n"
            f"## Recommendation 1 of {len(recommendations)}\n\n{first}\n\n"
            f"---\n"
            f"To get the next recommendation, call pr_review_resume with thread_id={thread_id!r} and feedback='approved'. "
            f"Say feedback='abort' to stop."
        )
    except Exception as e:
        return f"PR review start error: {e}"


@mcp.tool()
def pr_review_resume(thread_id: str, feedback: str) -> str:
    """
    Resume PR review after reviewing one recommendation.

    - feedback='approved' (or 'next', 'continue'): show the next recommendation.
    - feedback='abort': end the review.
    - Other feedback: stay on the same recommendation (e.g. ask more questions in chat).
    """
    try:
        result = _resume_pr_review(
            thread_id=thread_id,
            human_feedback=feedback or "",
            checkpointer=_checkpointer,
        )
        phase = result.get("phase", "")
        recommendations = result.get("recommendations") or []
        current_index = result.get("current_index", 0)
        if phase == "aborted":
            return f"Review aborted. Thread ID: {thread_id}"
        if phase == "done":
            return (
                f"All recommendations shown ({len(recommendations)} total).\n"
                f"Thread ID: {thread_id}"
            )
        if current_index < len(recommendations):
            rec = recommendations[current_index]
            n = current_index + 1
            fb_lower = (feedback or "").strip().lower()
            is_approve = fb_lower in ("approved", "next", "continue", "yes", "ok")
            ask_more_note = (
                "\n(Staying on this recommendation. You can ask questions in chat; "
                "say 'approved' for next or 'abort' to stop.)\n\n"
                if feedback and not is_approve and fb_lower != "abort"
                else ""
            )
            return (
                f"Thread ID: {thread_id}\n"
                f"## Recommendation {n} of {len(recommendations)}\n\n{rec}\n\n"
                f"{ask_more_note}"
                f"---\n"
                f"Call pr_review_resume with feedback='approved' for next, or 'abort' to stop."
            )
        return f"Thread ID: {thread_id}\nNo more recommendations."
    except Exception as e:
        return f"PR review resume error: {e}"


if __name__ == "__main__":
    mcp.run()
