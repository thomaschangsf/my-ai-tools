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
│       ├── planning_common.py      # Shared state, file I/O, skill loading, context assembly
│       ├── plan_auto.py            # Auto flow (LLM generates internally)
│       ├── plan_auto_ollama.py     # Ollama LLM helpers for auto flow
│       ├── plan_auto_anthropic.py  # Anthropic HTTP LLM helpers for auto flow
│       ├── plan_interactive.py     # Interactive flow (caller provides content)
│       └── pr_review.py            # PR review flow (git-utils + one recommendation at a time)
├── prompt-vault/
│   ├── INDEX.md                    # One-line description + asks_for per prompt
│   ├── _template.md                # Scaffold for new prompts
│   └── prompts/
│       └── pr-review.md            # Principal ML Eng PR review prompt
├── scripts/
│   ├── git-utils.sh                # pr_review_v2: clone/fetch PR, emit eval command
│   ├── verify_agents.py            # Master verification (hello + interactive + auto)
│   ├── verify_plan_interactive.py  # Interactive flow tests (no LLM needed)
│   ├── verify_plan_auto.py         # Auto flow tests (requires Ollama)
│   └── plan_cli.py                 # Terminal CLI for interactive flow
├── mcp_bridge.py              # MCP server entry point (Cursor)
├── docs/
│   ├── Architecture.md        # Architecture, diagrams, rationale
│   └── Dev.md                 # Developer cookbook & worked examples
├── specs/
├── pyproject.toml
└── README.md
```

## Design: Two orthogonal axes

> Full architecture, diagrams, and rationale: [docs/Architecture.md](docs/Architecture.md)
> Developer cookbook and worked examples: [docs/Dev.md](docs/Dev.md)

The planning system separates **control flow** from **LLM backend**:

### Axis 1: Control flow (who drives the loop?)

| | **Auto** | **Interactive** |
|---|---|---|
| **Direction** | Push — graph calls LLM internally | Pull — graph returns context, caller provides content |
| **Human role** | Review & approve/revise between stages | Generate (or delegate to LLM) + review at each stage |
| **Graph** | `plan_auto.py` | `plan_interactive.py` |
| **MCP tools** | `plan_auto_start`, `plan_auto_resume` | `plan_interactive_start`, `plan_interactive_resume` |

### Axis 2: LLM backend (who generates the content?)

| Backend | Auto flow | Interactive flow |
|---|---|---|
| **Ollama** (local) | Yes — `plan_auto_ollama.py` | Yes — via `plan_cli.py` |
| **Anthropic** (HTTP) | Yes — `plan_auto_anthropic.py` | Yes — via `plan_cli.py` with `PLANNING_LLM=anthropic` |
| **Cursor's LLM** | No (Cursor can't be called from inside a tool) | Yes — Cursor reads context and generates |
| **OpenAI / others** | Add `plan_auto_<name>.py` + register in `_BACKENDS` | Yes — via `plan_cli.py` with new backend |
| **Manual** (human) | No | Yes — `PLANNING_LLM=none plan_cli.py` |

### Why interactive mode is LLM-agnostic

The interactive graph **never calls an LLM**. Its information flow is:

```
Agent  ──context_bundle (str)──▶  [ANY caller]  ──content (str)──▶  Agent
```

At each phase the graph:
1. **Assembles** a context string (task + SKILL.md + prior artifacts + feedback)
2. **Returns** it to the caller (pauses)
3. **Receives** generated content back as a plain string

Because the interface is *strings in, strings out*, any LLM backend works — the
graph doesn't know or care what produced the content.

**Example — same graph, three different backends:**

```
# 1. Cursor's LLM (in chat)
#    plan_interactive_start returns context → Cursor generates plan → plan_interactive_resume(content=...)

# 2. Ollama (via CLI)
PLANNING_LLM=ollama uv run python scripts/plan_cli.py "Build a cache" /tmp/proj
#    plan_cli.py sends context to Ollama, feeds response back to graph

# 3. Anthropic (via CLI)
PLANNING_LLM=anthropic uv run python scripts/plan_cli.py "Build a cache" /tmp/proj
#    plan_cli.py sends context to Anthropic API, feeds response back to graph

# 4. Manual (human pastes content)
PLANNING_LLM=none uv run python scripts/plan_cli.py "Build a cache" /tmp/proj
```

In contrast, the **auto** flow embeds the LLM call inside the graph nodes. Switching
backends requires passing a different `backend=` parameter (e.g. `"ollama"` or
`"anthropic"`), which selects the corresponding `plan_auto_*.py` module.

### What's shared (`planning_common.py`)

- `PlanningState` — state schema
- File conventions — `plan.md`, `interface.md`, `generated_module.py`, `test_baseline.py`
- `load_skill()` — loads `~/.cursor/skills/principal-ml-planning/SKILL.md`
- Context assembly — `assemble_plan_context()`, `assemble_interface_context()`, `assemble_code_context()`

## Setup

```bash
# Install dependencies (include dev for check + tests)
uv sync --extra dev
```

## Commands

- **`uv run check`** — Run Ruff (lint), MCP bridge check, and verify all agents.
- **`uv run tests`** — Run pytest.
- **`uv run notebook`** — Start Jupyter Notebook (opens in browser).
- **`uv run ollama-serve`** — Start Ollama locally if not already running.
- **`uv run mcp-bridge`** — Start the MCP bridge server.
- **`uv run python scripts/plan_cli.py "task" /path`** — Terminal planning CLI.

## MCP: Global Agents (Cursor)

Register the MCP server in `~/.cursor/mcp.json` or via Cursor settings.

From the repo directory with uv:

```bash
uv run mcp-bridge
```

**MCP tools (7):**

| Tool | Flow | What it does |
|---|---|---|
| `run_hello` | — | Test tool: prepends "Global Agent Response:" to input |
| `plan_auto_start` | Auto | Start auto flow — LLM generates plan.md. `backend`: `"ollama"` (default) or `"anthropic"`. |
| `plan_auto_resume` | Auto | Approve (`'approved'`) or revise (feedback text). LLM regenerates. |
| `plan_interactive_start` | Interactive | Start interactive flow — returns context bundle. Caller generates content. |
| `plan_interactive_resume` | Interactive | Save content (advances phase) or send feedback (revise same phase). |
| `pr_review_start` | PR review | Start PR review: pull PR via git-utils, run review, show first recommendation. |
| `pr_review_resume` | PR review | Next recommendation (`feedback='approved'`) or abort (`feedback='abort'`). |

### Auto flow

```
START -> Planner -> [review] -> Interfacer -> [review] -> Executor -> END
                  \-- revise --/            \-- revise --/
```

The LLM backend generates all content. You just review and approve/revise.
Default backend is Ollama; pass `backend="anthropic"` to use the Anthropic API.

```bash
# Anthropic backend (requires ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY="sk-ant-..."
# Then use plan_auto_start with backend="anthropic"
```

### Interactive flow

```
START -> Assemble context -> [caller generates] -> Save -> Assemble next -> ... -> END
                               \--- feedback ----/
```

The graph never calls an LLM. It assembles context (including SKILL.md) and pauses. The caller — Cursor's agent, a terminal CLI, or a human — generates the content and feeds it back.

Cross-session: LangGraph checkpoints persist to SQLite, so you can resume with the same thread_id across sessions.

### PR review flow

Runs `scripts/git-utils.sh pr_review_v2 <PR URL>` to clone/fetch the PR locally (the workflow executes the emitted command in a subprocess; your shell does not change). Then runs one LLM review using `prompt-vault/prompts/pr-review.md` and presents recommendations one at a time. Call `pr_review_resume` with `feedback='approved'` for the next recommendation or `feedback='abort'` to stop. Requires `ANTHROPIC_API_KEY` for the review LLM.

### Terminal CLI

```bash
# With Ollama (default)
uv run python scripts/plan_cli.py "Build a URL shortener" /tmp/my-project

# With Anthropic
PLANNING_LLM=anthropic ANTHROPIC_API_KEY="sk-ant-..." \
  uv run python scripts/plan_cli.py "Build a URL shortener" /tmp/my-project

# Manual mode (paste content yourself)
PLANNING_LLM=none uv run python scripts/plan_cli.py "Build a URL shortener" /tmp/my-project
```

### Verifying the agents

```bash
# All agents (hello + interactive + auto)
uv run python scripts/verify_agents.py

# Interactive only (no LLM needed)
uv run python scripts/verify_plan_interactive.py

# Auto only (requires Ollama)
uv run python scripts/verify_plan_auto.py
```
