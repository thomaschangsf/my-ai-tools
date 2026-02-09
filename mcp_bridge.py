"""
MCP bridge for Global Stateful AI Agent Orchestrator.
Cursor entry point: run this file so Cursor can invoke run_hello and run_principal_flow.
"""
import os
import sqlite3
import uuid
from pathlib import Path

from fastmcp import FastMCP
from langgraph.checkpoint.sqlite import SqliteSaver

from my_ai_tools.agents.hello_world import run_hello as _run_hello
from my_ai_tools.agents.principal_flow import run_principal_flow as _run_principal_flow

# SQLite checkpointer in global directory (same dir as this file; not the target project)
_REPO_ROOT = Path(__file__).resolve().parent
_AGENTS_DB = _REPO_ROOT / "agents_state.db"
_conn = sqlite3.connect(str(_AGENTS_DB), check_same_thread=False)
_checkpointer = SqliteSaver(_conn)

mcp = FastMCP("GlobalAgents")


@mcp.tool()
def run_hello(input_text: str) -> str:
    """Invoke the hello_world agent. Returns a string with 'Global Agent Response:' prepended to the input."""
    return _run_hello(input_text or "")


@mcp.tool()
def run_principal_flow(task_description: str, project_root: str = "") -> str:
    """
    Run the principal flow agent: Planner -> Interfacer -> Executor.
    Writes plan.md, interface.md, generated_module.py, and test_baseline.py to the given project path.
    Uses project_root if provided, otherwise the current working directory (e.g. active Cursor project).
    """
    project_path = (project_root or os.getcwd()).strip()
    thread_id = str(uuid.uuid4())
    try:
        _run_principal_flow(
            task_description=task_description,
            project_root=project_path,
            thread_id=thread_id,
            checkpointer=_checkpointer,
        )
        return f"Principal flow completed. Outputs written to {project_path}"
    except Exception as e:
        return f"Principal flow error: {e}"


if __name__ == "__main__":
    mcp.run()
