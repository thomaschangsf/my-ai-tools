"""Principal Flow agent: Planner -> Interfacer -> Executor with SQLite checkpointer."""

import os
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver

from .principal_flow_llm import (
    generate_plan,
    generate_interface,
    generate_code_and_tests,
)

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")


class PrincipalState(TypedDict):
    """State for the principal flow: task and project path."""

    task_description: str
    project_root: str


def _ensure_project_path(project_root: str) -> Path:
    """Resolve project path; use cwd if not provided."""
    path = (project_root or os.getcwd()).strip()
    return Path(path).resolve()


def _planner(state: PrincipalState) -> dict[str, Any]:
    """Read task + project path; write plan.md to the project path."""
    try:
        root = _ensure_project_path(state["project_root"])
        root.mkdir(parents=True, exist_ok=True)
        plan_content = generate_plan(state["task_description"], str(root), OLLAMA_MODEL)
        plan_path = root / "plan.md"
        plan_path.write_text(plan_content, encoding="utf-8")
        return {}
    except Exception as e:
        return {"_error": str(e)}


def _interfacer(state: PrincipalState) -> dict[str, Any]:
    """Read plan.md from project path; write interface.md."""
    try:
        root = _ensure_project_path(state["project_root"])
        plan_path = root / "plan.md"
        if not plan_path.exists():
            return {"_error": "plan.md not found; run planner first."}
        plan_content = plan_path.read_text(encoding="utf-8")
        interface_content = generate_interface(plan_content, str(root), OLLAMA_MODEL)
        (root / "interface.md").write_text(interface_content, encoding="utf-8")
        return {}
    except Exception as e:
        return {"_error": str(e)}


def _executor(state: PrincipalState) -> dict[str, Any]:
    """Read interface.md; write boilerplate code and test_baseline.py."""
    try:
        root = _ensure_project_path(state["project_root"])
        interface_path = root / "interface.md"
        if not interface_path.exists():
            return {"_error": "interface.md not found; run interfacer first."}
        interface_content = interface_path.read_text(encoding="utf-8")
        code_content, test_content = generate_code_and_tests(
            interface_content, str(root), OLLAMA_MODEL
        )
        (root / "generated_module.py").write_text(code_content, encoding="utf-8")
        (root / "test_baseline.py").write_text(test_content, encoding="utf-8")
        return {}
    except Exception as e:
        return {"_error": str(e)}


def build_graph(checkpointer: SqliteSaver):
    """Build and compile the principal_flow graph with the given checkpointer."""
    workflow = StateGraph(PrincipalState)
    workflow.add_node("planner", _planner)
    workflow.add_node("interfacer", _interfacer)
    workflow.add_node("executor", _executor)
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "interfacer")
    workflow.add_edge("interfacer", "executor")
    workflow.add_edge("executor", END)
    return workflow.compile(checkpointer=checkpointer)


def run_principal_flow(
    task_description: str,
    project_root: str,
    *,
    thread_id: str,
    checkpointer: SqliteSaver,
) -> dict[str, Any]:
    """Invoke the principal flow graph. Writes to project_root (not global dir)."""
    graph = build_graph(checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    initial = {
        "task_description": task_description,
        "project_root": project_root or os.getcwd(),
    }
    result = graph.invoke(initial, config=config)
    return result
