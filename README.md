# my-ai-tools

UV project for AI tools: Python, Jupyter, LangGraph, and local Ollama over HTTP.

## Project structure

There is **no `src/` directory**. The project uses a single top-level package:

```
my-ai-tools/
├── my_ai_tools/              # The one installable Python package
│   ├── __init__.py
│   ├── cli.py                 # UV commands: check, tests, notebook, ollama-serve
│   ├── ollama_client.py       # Helper for local Ollama HTTP client
│   └── agents/                # LangGraph agents (MCP / principal flow)
│       ├── __init__.py
│       ├── hello_world.py
│       ├── principal_flow.py
│       └── principal_flow_llm.py
├── scripts/
│   └── verify_agents.py       # Verification script for agents
├── mcp_bridge.py              # MCP server entry point (Cursor)
├── specs/
├── pyproject.toml
└── README.md
```

- **`my_ai_tools`** is the only package. It is installed when you `uv sync` and provides the CLI entry points and the agents. Everything lives under this package.
- **`scripts/`** holds one-off runnable scripts (e.g. verification) that use the installed package.
- **`mcp_bridge.py`** is at the repo root so Cursor can be pointed at it; it imports from `my_ai_tools.agents`.

## Setup

```bash
# Install dependencies (include dev for check + tests)
uv sync --extra dev
```

## Commands

- **`uv run check`** — Run Ruff (lint), MCP bridge check (loads bridge and validates tools), and `scripts/verify_agents.py`. All must pass.
- **`uv run tests`** — Run pytest.
- **`uv run notebook`** — Start Jupyter Notebook (opens in browser). Or use **`uv run jupyter notebook`**.
- **`uv run ollama-serve`** — Start Ollama locally if not already running (requires [Ollama](https://ollama.com) installed).
- **`uv run python scripts/verify_agents.py`** — Run agent verification only (included in `uv run check`).

## Local Ollama

Ollama is used over HTTP at `http://localhost:11434` (default). Ensure Ollama is running locally, then in Python:

```python
from my_ai_tools.ollama_client import get_client

client = get_client()  # or get_client(host="http://localhost:11434")
# or use the ollama package directly:
# from ollama import Client
# client = Client(host="http://localhost:11434")
```

## MCP: Global Agents (Cursor)

This repo provides an MCP server with stateful LangGraph agents (hello_world, principal_flow) that can be invoked from any local project in Cursor.

**Cursor registration:** add an MCP server with this command (replace the path with your absolute repo path):

```bash
python3 /ABSOLUTE_PATH_TO_FILE/mcp_bridge.py
```

Example if the repo is at `/Users/me/my-ai-tools`:

```bash
python3 /Users/me/my-ai-tools/mcp_bridge.py
```

Or from the repo directory with uv:

```bash
uv run python mcp_bridge.py
```

**Tools:**

- **run_hello** — Hello-world agent: prepends `"Global Agent Response:"` to the input.
- **run_principal_flow** — Planner → Interfacer → Executor: writes `plan.md`, `interface.md`, `generated_module.py`, and `test_baseline.py` to the given `project_root` (or current working directory). Uses local Ollama for generation; set `OLLAMA_MODEL` if needed (default: `llama3.2`).

### Verifying the agents

**1. One command (recommended)** — From the repo root:

```bash
uv run python scripts/verify_agents.py
```

This runs **hello_world** (always) and **principal_flow** in a temp directory. For principal_flow you need Ollama running and a model (e.g. `ollama pull llama3.2`).

**2. Quick hello_world check** — From the repo root:

```bash
uv run python -c "from my_ai_tools.agents.hello_world import run_hello; print(run_hello('hi'))"
```

Expected output: `Global Agent Response: hi`.

**3. Via MCP in Cursor** — After registering the MCP server, use the **run_hello** and **run_principal_flow** tools from the Cursor AI panel; they call the same agents.