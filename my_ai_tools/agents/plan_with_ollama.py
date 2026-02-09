"""
Ollama-backed planning flow: Planner -> Interfacer -> Executor with human-in-the-loop review.

The graph pauses after the planner and interfacer for human review.  The human
can approve (proceed to the next stage) or provide revision feedback (loop back
to the same stage).  This is implemented with LangGraph's ``interrupt_before``
on the two review nodes.
"""

import os
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver

from .planning_common import (
    PlanningState,
    ensure_project_path,
    PLAN_FILE,
    INTERFACE_FILE,
    CODE_FILE,
    TEST_FILE,
)
from .plan_with_ollama_llm import (
    generate_plan,
    generate_plan_revision,
    generate_interface,
    generate_interface_revision,
    generate_code_and_tests,
)

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

def _planner(state: PlanningState) -> dict[str, Any]:
    """Generate (or revise) plan.md in the project directory."""
    try:
        root = ensure_project_path(state["project_root"])
        root.mkdir(parents=True, exist_ok=True)
        feedback = state.get("human_feedback", "")
        plan_path = root / PLAN_FILE

        if feedback and feedback.lower().strip() != "approved" and plan_path.exists():
            existing_plan = plan_path.read_text(encoding="utf-8")
            plan_content = generate_plan_revision(
                state["task_description"], str(root), existing_plan, feedback, OLLAMA_MODEL,
            )
        else:
            plan_content = generate_plan(state["task_description"], str(root), OLLAMA_MODEL)

        plan_path.write_text(plan_content, encoding="utf-8")
        return {"phase": "plan_review", "human_feedback": ""}
    except Exception as e:
        return {"phase": "error", "human_feedback": f"Planner error: {e}"}


def _plan_review(state: PlanningState) -> dict[str, Any]:
    """Pass-through node executed after interrupt; feedback is already in state."""
    return {"phase": "plan_review"}


def _route_plan_review(state: PlanningState) -> str:
    """Route after plan review: 'approved' -> interfacer, anything else -> revise."""
    feedback = state.get("human_feedback", "").strip().lower()
    if feedback == "approved":
        return "interfacer"
    return "planner"


def _interfacer(state: PlanningState) -> dict[str, Any]:
    """Generate (or revise) interface.md in the project directory."""
    try:
        root = ensure_project_path(state["project_root"])
        plan_path = root / PLAN_FILE
        if not plan_path.exists():
            return {"phase": "error", "human_feedback": "plan.md not found; run planner first."}
        plan_content = plan_path.read_text(encoding="utf-8")

        feedback = state.get("human_feedback", "")
        interface_path = root / INTERFACE_FILE

        if feedback and feedback.lower().strip() != "approved" and interface_path.exists():
            existing_interface = interface_path.read_text(encoding="utf-8")
            interface_content = generate_interface_revision(
                plan_content, str(root), existing_interface, feedback, OLLAMA_MODEL,
            )
        else:
            interface_content = generate_interface(plan_content, str(root), OLLAMA_MODEL)

        interface_path.write_text(interface_content, encoding="utf-8")
        return {"phase": "interface_review", "human_feedback": ""}
    except Exception as e:
        return {"phase": "error", "human_feedback": f"Interfacer error: {e}"}


def _interface_review(state: PlanningState) -> dict[str, Any]:
    """Pass-through node executed after interrupt; feedback is already in state."""
    return {"phase": "interface_review"}


def _route_interface_review(state: PlanningState) -> str:
    """Route after interface review: 'approved' -> executor, anything else -> revise."""
    feedback = state.get("human_feedback", "").strip().lower()
    if feedback == "approved":
        return "executor"
    return "interfacer"


def _executor(state: PlanningState) -> dict[str, Any]:
    """Read interface.md; write generated_module.py and test_baseline.py."""
    try:
        root = ensure_project_path(state["project_root"])
        interface_path = root / INTERFACE_FILE
        if not interface_path.exists():
            return {"phase": "error", "human_feedback": "interface.md not found."}
        interface_content = interface_path.read_text(encoding="utf-8")
        code_content, test_content = generate_code_and_tests(
            interface_content, str(root), OLLAMA_MODEL,
        )
        (root / CODE_FILE).write_text(code_content, encoding="utf-8")
        (root / TEST_FILE).write_text(test_content, encoding="utf-8")
        return {"phase": "done", "human_feedback": ""}
    except Exception as e:
        return {"phase": "error", "human_feedback": f"Executor error: {e}"}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph(checkpointer: SqliteSaver):
    """Build and compile the plan_with_ollama graph with human-in-the-loop review."""
    workflow = StateGraph(PlanningState)

    workflow.add_node("planner", _planner)
    workflow.add_node("plan_review", _plan_review)
    workflow.add_node("interfacer", _interfacer)
    workflow.add_node("interface_review", _interface_review)
    workflow.add_node("executor", _executor)

    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "plan_review")
    workflow.add_conditional_edges(
        "plan_review",
        _route_plan_review,
        {"interfacer": "interfacer", "planner": "planner"},
    )
    workflow.add_edge("interfacer", "interface_review")
    workflow.add_conditional_edges(
        "interface_review",
        _route_interface_review,
        {"executor": "executor", "interfacer": "interfacer"},
    )
    workflow.add_edge("executor", END)

    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["plan_review", "interface_review"],
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def plan_with_ollama(
    task_description: str,
    project_root: str,
    *,
    thread_id: str,
    checkpointer: SqliteSaver,
) -> dict[str, Any]:
    """Start the planning flow. Runs the planner, then pauses for human review."""
    graph = build_graph(checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    initial = {
        "task_description": task_description,
        "project_root": project_root or os.getcwd(),
        "human_feedback": "",
        "phase": "planning",
    }
    result = graph.invoke(initial, config=config)
    return result


def resume_plan_with_ollama(
    *,
    thread_id: str,
    human_feedback: str,
    checkpointer: SqliteSaver,
) -> dict[str, Any]:
    """Resume the flow after human review.

    Pass ``human_feedback='approved'`` to proceed to the next phase, or
    provide revision notes to loop back and regenerate the current artifact.
    """
    graph = build_graph(checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    graph.update_state(config, {"human_feedback": human_feedback})
    result = graph.invoke(None, config=config)
    return result
