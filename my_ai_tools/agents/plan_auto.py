"""
Auto planning flow: the graph calls an LLM internally at each stage.

The human only reviews and approves/revises between stages.  The LLM backend
is pluggable — pass ``backend="ollama"`` (default) or ``backend="anthropic"``
to ``start_auto_plan`` / ``resume_auto_plan``.

Graph:
    START -> planner -> [interrupt] -> plan_review -> interfacer -> [interrupt]
                                          |
                                          +-- revise -> planner
          -> interface_review -> executor -> END
                  |
                  +-- revise -> interfacer

Control flow: auto (push) — the graph drives the LLM calls.
LLM backend: parameterized via ``backend`` argument (resolved at runtime).
"""

import importlib
import os
from types import ModuleType
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


# ---------------------------------------------------------------------------
# Backend registry
# ---------------------------------------------------------------------------

_BACKENDS: dict[str, str] = {
    "ollama": "my_ai_tools.agents.plan_auto_ollama",
    "anthropic": "my_ai_tools.agents.plan_auto_anthropic",
}


def _resolve_backend(name: str) -> ModuleType:
    """Import and return the backend module by short name."""
    module_path = _BACKENDS.get(name)
    if not module_path:
        raise ValueError(
            f"Unknown backend {name!r}. Available: {sorted(_BACKENDS.keys())}"
        )
    return importlib.import_module(module_path)


# ---------------------------------------------------------------------------
# Graph construction (nodes are closures that capture the backend module)
# ---------------------------------------------------------------------------

def build_graph(checkpointer: SqliteSaver, backend: ModuleType):
    """Build and compile the auto planning graph with human-in-the-loop review.

    ``backend`` is a module exposing generate_plan, generate_plan_revision,
    generate_interface, generate_interface_revision, generate_code_and_tests.
    """

    # -- Node functions (closures over ``backend``) -------------------------

    def _planner(state: PlanningState) -> dict[str, Any]:
        """Generate (or revise) plan.md in the project directory."""
        try:
            root = ensure_project_path(state["project_root"])
            root.mkdir(parents=True, exist_ok=True)
            feedback = state.get("human_feedback", "")
            plan_path = root / PLAN_FILE

            if feedback and feedback.lower().strip() != "approved" and plan_path.exists():
                existing_plan = plan_path.read_text(encoding="utf-8")
                plan_content = backend.generate_plan_revision(
                    state["task_description"], str(root), existing_plan, feedback,
                )
            else:
                plan_content = backend.generate_plan(state["task_description"], str(root))

            plan_path.write_text(plan_content, encoding="utf-8")
            return {"phase": "plan_review", "human_feedback": ""}
        except Exception as e:
            return {"phase": "error", "human_feedback": f"Planner error: {e}"}

    def _plan_review(state: PlanningState) -> dict[str, Any]:
        """Pass-through node executed after interrupt; feedback is already in state."""
        return {"phase": "plan_review"}

    def _route_plan_review(state: PlanningState) -> str:
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
                interface_content = backend.generate_interface_revision(
                    plan_content, str(root), existing_interface, feedback,
                )
            else:
                interface_content = backend.generate_interface(plan_content, str(root))

            interface_path.write_text(interface_content, encoding="utf-8")
            return {"phase": "interface_review", "human_feedback": ""}
        except Exception as e:
            return {"phase": "error", "human_feedback": f"Interfacer error: {e}"}

    def _interface_review(state: PlanningState) -> dict[str, Any]:
        """Pass-through node executed after interrupt; feedback is already in state."""
        return {"phase": "interface_review"}

    def _route_interface_review(state: PlanningState) -> str:
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
            code_content, test_content = backend.generate_code_and_tests(
                interface_content, str(root),
            )
            (root / CODE_FILE).write_text(code_content, encoding="utf-8")
            (root / TEST_FILE).write_text(test_content, encoding="utf-8")
            return {"phase": "done", "human_feedback": ""}
        except Exception as e:
            return {"phase": "error", "human_feedback": f"Executor error: {e}"}

    # -- Wire up the graph --------------------------------------------------

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

def start_auto_plan(
    task_description: str,
    project_root: str,
    *,
    thread_id: str,
    checkpointer: SqliteSaver,
    backend: str = "ollama",
) -> dict[str, Any]:
    """Start the auto planning flow.

    Runs the planner, then pauses for human review.

    Args:
        backend: LLM backend name — ``"ollama"`` (default) or ``"anthropic"``.
    """
    backend_module = _resolve_backend(backend)
    graph = build_graph(checkpointer, backend_module)
    config = {"configurable": {"thread_id": thread_id}}
    initial = {
        "task_description": task_description,
        "project_root": project_root or os.getcwd(),
        "human_feedback": "",
        "phase": "planning",
    }
    result = graph.invoke(initial, config=config)
    return result


def resume_auto_plan(
    *,
    thread_id: str,
    human_feedback: str,
    checkpointer: SqliteSaver,
    backend: str = "ollama",
) -> dict[str, Any]:
    """Resume the auto flow after human review.

    Pass ``human_feedback='approved'`` to proceed to the next phase, or
    provide revision notes to loop back and regenerate the current artifact.

    Args:
        backend: LLM backend name — ``"ollama"`` (default) or ``"anthropic"``.
    """
    backend_module = _resolve_backend(backend)
    graph = build_graph(checkpointer, backend_module)
    config = {"configurable": {"thread_id": thread_id}}
    graph.update_state(config, {"human_feedback": human_feedback})
    result = graph.invoke(None, config=config)
    return result
