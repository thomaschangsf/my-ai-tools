"""Hello World agent: single-node graph that prepends a prefix to the input."""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class HelloState(TypedDict):
    """State with input and output."""

    input: str
    output: str


def _respond(state: HelloState) -> dict[str, str]:
    """Single node: prepend 'Global Agent Response:' to input."""
    try:
        inp = state.get("input", "") or ""
        return {"output": f"Global Agent Response: {inp}"}
    except Exception as e:
        return {"output": f"Global Agent Response: [error: {e}]"}


def build_graph():
    """Build and compile the hello_world graph."""
    workflow = StateGraph(HelloState)
    workflow.add_node("respond", _respond)
    workflow.add_edge(START, "respond")
    workflow.add_edge("respond", END)
    return workflow.compile()


def run_hello(input_text: str) -> str:
    """Invoke the hello_world graph and return the output."""
    graph = build_graph()
    result = graph.invoke({"input": input_text, "output": ""})
    return result.get("output", "")
