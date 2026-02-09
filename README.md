# my-ai-tools

UV project for AI tools: Python, Jupyter, LangGraph, and local Ollama over HTTP.

## Project structure

There is **no `src/` directory**. The project uses a single top-level package:

```
my-ai-tools/
├── my_ai_tools/              # The one installable Python package
│   ├── __init__.py
│   ├── cli.py                 # UV commands: check, tests, notebook, ollama-serve, mcp-bridge
│   ├── ollama_client.py       # Helper for local Ollama HTTP client
│   └── agents/                # LangGraph agents (MCP / planning flows)
│       ├── __init__.py
│       ├── hello_world.py
│       ├── planning_common.py      # Shared state, file I/O, skill loading
│       ├── plan_with_ollama.py     # Ollama-backed planning flow (autonomous)
│       ├── plan_with_ollama_llm.py # Ollama LLM helpers
│       └── plan_with_cursor.py     # Cursor-agent-backed planning flow (stub)
├── scripts/
│   └── verify_agents.py       # Verification script for agents
├── mcp_bridge.py              # MCP server entry point (Cursor)
├── specs/
├── pyproject.toml
└── README.md
```

- **`my_ai_tools`** is the only package. It is installed when you `uv sync` and provides the CLI entry points and the agents. Everything lives under this package.
- **`planning_common.py`** holds the shared `PlanningState`, file conventions, and SKILL.md loading used by both `plan_with_ollama` and (future) `plan_with_cursor`.
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
- **`uv run mcp-bridge`** — Start the MCP bridge server (`mcp_bridge.py`).
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

This repo provides an MCP server with stateful LangGraph agents that can be invoked from any local project in Cursor.

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
uv run mcp-bridge
```

**Tools:**

- **run_hello** — Hello-world agent: prepends `"Global Agent Response:"` to the input.
- **plan_with_ollama** — Start the Ollama-backed iterative planning flow (see below). Returns a `thread_id` for use with `resume_flow`.
- **resume_flow** — Resume the planning flow after human review. Pass `feedback='approved'` to proceed or provide revision notes to loop back.

### Planning flow (human-in-the-loop)

The planning flow is iterative with human review at each stage:

```
START -> Planner -> [human review] -> Interfacer -> [human review] -> Executor -> END
                  \--- revise ------/             \--- revise ------/
```

1. **`plan_with_ollama(task_description, project_root)`** — Runs the planner (using `~/.cursor/skills/principal-ml-planning/SKILL.md` as the planning framework) and writes `plan.md`. The flow pauses and returns a `thread_id`.
2. **Review `plan.md`** in the project directory.
3. **`resume_flow(thread_id, 'approved')`** — Approves the plan and runs the interfacer, which writes `interface.md`. The flow pauses again.
   - Or **`resume_flow(thread_id, '<revision notes>')`** — Sends the plan back to the planner with your feedback for revision.
4. **Review `interface.md`**.
5. **`resume_flow(thread_id, 'approved')`** — Approves the interface and runs the executor, which writes `generated_module.py` and `test_baseline.py`. The flow completes.
   - Or provide revision feedback to loop back to the interfacer.

Uses local Ollama for generation; set `OLLAMA_MODEL` if needed (default: `llama3.2`).

### Architecture: Ollama vs Cursor backends

The planning logic is split so that both Ollama and Cursor can serve as the intelligence layer:

| | `plan_with_ollama` | `plan_with_cursor` (future) |
|---|---|---|
| **Intelligence** | Local Ollama model | Cursor's LLM |
| **Flow** | Autonomous — LLM calls happen inside the agent | Collaborative — MCP tools provide state/context, Cursor generates |
| **Shared** | `PlanningState`, file conventions, SKILL.md | Same |

### Verifying the agents

**1. One command (recommended)** — From the repo root:

```bash
uv run python scripts/verify_agents.py
```

This runs **hello_world** (always) and **plan_with_ollama** in a temp directory. For plan_with_ollama you need Ollama running and a model (e.g. `ollama pull llama3.2`).

**2. Quick hello_world check** — From the repo root:

```bash
uv run python -c "from my_ai_tools.agents.hello_world import run_hello; print(run_hello('hi'))"
```

Expected output: `Global Agent Response: hi`.

**3. Via MCP in Cursor** — After registering the MCP server, use the **run_hello** and **plan_with_ollama** tools from the Cursor AI panel.
