"""
Interactive planning flow: the graph assembles context and pauses; the caller
provides generated content (or revision feedback).

The caller can be Cursor's agent, a terminal CLI with any LLM, or a human
pasting content manually.  The graph itself never calls an LLM.

Graph topology (3-node cycle):

    START -> assemble -> [interrupt] -> gate -> save -> assemble -> ... -> END
                                          |              ^
                                          +-- revise ----+

The graph pauses before ``gate`` each time.  The caller provides either:
- ``generated_content``: the LLM's output to save (advances to next phase)
- ``human_feedback``: revision notes (loops back to ``assemble`` with feedback)

Control flow: interactive (pull) — the caller drives content generation.
LLM backend: none (the graph is LLM-agnostic).

Phases: plan -> interface -> code -> done
"""

import os
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver

from .planning_common import (
    ensure_project_path,
    assemble_plan_context,
    assemble_interface_context,
    assemble_code_context,
    PLAN_FILE,
    INTERFACE_FILE,
    CODE_FILE,
    TEST_FILE,
)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class InteractivePlanningState(TypedDict):
    """State for the interactive planning flow."""

    task_description: str
    project_root: str
    phase: str  # "plan", "interface", "code", "done"
    context_bundle: str  # assembled prompt/context for the external LLM
    generated_content: str  # content from the external LLM to save
    human_feedback: str  # revision notes (triggers re-assembly)


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

def _assemble(state: InteractivePlanningState) -> dict[str, Any]:
    """Build the context bundle for the current phase."""
    phase = state["phase"]
    root = ensure_project_path(state["project_root"])
    feedback = state.get("human_feedback", "")

    if phase == "plan":
        existing = ""
        plan_path = root / PLAN_FILE
        if feedback and plan_path.exists():
            existing = plan_path.read_text(encoding="utf-8")
        context = assemble_plan_context(
            state["task_description"], str(root), feedback, existing,
        )
    elif phase == "interface":
        plan = (root / PLAN_FILE).read_text(encoding="utf-8")
        existing = ""
        iface_path = root / INTERFACE_FILE
        if feedback and iface_path.exists():
            existing = iface_path.read_text(encoding="utf-8")
        context = assemble_interface_context(plan, str(root), feedback, existing)
    elif phase == "code":
        interface = (root / INTERFACE_FILE).read_text(encoding="utf-8")
        existing = ""
        code_path = root / CODE_FILE
        if feedback and code_path.exists():
            existing = code_path.read_text(encoding="utf-8")
        context = assemble_code_context(interface, str(root), feedback, existing)
    else:
        context = ""

    return {"context_bundle": context, "generated_content": "", "human_feedback": ""}


def _gate(state: InteractivePlanningState) -> dict[str, Any]:
    """Pass-through node; routing is handled by the conditional edge."""
    return {}


def _route_gate(state: InteractivePlanningState) -> str:
    """Route after gate: save if content provided, otherwise loop back for revision."""
    if state.get("generated_content", "").strip():
        return "save"
    return "assemble"


def _save(state: InteractivePlanningState) -> dict[str, Any]:
    """Write the generated content to the appropriate file and advance the phase."""
    phase = state["phase"]
    root = ensure_project_path(state["project_root"])
    root.mkdir(parents=True, exist_ok=True)
    content = state["generated_content"]

    if phase == "plan":
        (root / PLAN_FILE).write_text(content, encoding="utf-8")
        next_phase = "interface"
    elif phase == "interface":
        (root / INTERFACE_FILE).write_text(content, encoding="utf-8")
        next_phase = "code"
    elif phase == "code":
        # Try to split into module + tests
        if "## TEST" in content:
            parts = content.split("## TEST", 1)
            code = parts[0].replace("## MODULE", "").strip()
            test = parts[1].strip()
        else:
            code = content
            test = "# Add pytest tests here"
        (root / CODE_FILE).write_text(code, encoding="utf-8")
        (root / TEST_FILE).write_text(test, encoding="utf-8")
        next_phase = "done"
    else:
        next_phase = "done"

    return {"phase": next_phase, "generated_content": "", "context_bundle": ""}


def _route_after_save(state: InteractivePlanningState) -> str:
    """Route after save: continue to assemble if more phases, otherwise end."""
    if state["phase"] == "done":
        return "__end__"
    return "assemble"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph(checkpointer: SqliteSaver):
    """Build the interactive planning graph (assemble -> gate -> save cycle)."""
    workflow = StateGraph(InteractivePlanningState)

    workflow.add_node("assemble", _assemble)
    workflow.add_node("gate", _gate)
    workflow.add_node("save", _save)

    workflow.add_edge(START, "assemble")
    workflow.add_edge("assemble", "gate")
    workflow.add_conditional_edges(
        "gate",
        _route_gate,
        {"save": "save", "assemble": "assemble"},
    )
    workflow.add_conditional_edges(
        "save",
        _route_after_save,
        {"assemble": "assemble", "__end__": END},
    )

    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["gate"],
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_interactive_plan(
    task_description: str,
    project_root: str,
    *,
    thread_id: str,
    checkpointer: SqliteSaver,
) -> dict[str, Any]:
    """Start an interactive planning session.

    Runs the first ``assemble`` node (builds plan context), then pauses.
    Returns state with ``context_bundle`` for the external LLM / human to use.
    """
    graph = build_graph(checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    initial: InteractivePlanningState = {
        "task_description": task_description,
        "project_root": project_root or os.getcwd(),
        "phase": "plan",
        "context_bundle": "",
        "generated_content": "",
        "human_feedback": "",
    }
    result = graph.invoke(initial, config=config)
    return result


def resume_interactive_plan(
    *,
    thread_id: str,
    checkpointer: SqliteSaver,
    content: str = "",
    feedback: str = "",
) -> dict[str, Any]:
    """Resume an interactive planning session.

    Provide exactly one of:
    - ``content``: the generated artifact to save (advances to next phase)
    - ``feedback``: revision notes (loops back to regenerate the current phase)
    """
    graph = build_graph(checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    update: dict[str, str] = {}
    if content:
        update["generated_content"] = content
    if feedback:
        update["human_feedback"] = feedback
    graph.update_state(config, update)
    result = graph.invoke(None, config=config)
    return result
