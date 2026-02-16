# Architecture

## Overview

**my-ai-tools** is a personal AI toolbox with two main surfaces:

1. **MCP** — Planning and PR-review flows exposed as tools for Cursor (or any MCP client). Structured, multi-phase flows with human-in-the-loop and persistence.
2. **Prompt vault** — Markdown prompts for use in Cursor chat (e.g. self-correction cycle: write from spec → check code → repeat). No server; you @ the files and run the workflow in chat.

---

## Key directories

| Directory | Purpose |
|-----------|--------|
| **`prompt-vault/`** | Prompts used in Cursor chat. `prompts/*.md` = one prompt per file; `INDEX.md` = id, description, `asks_for`. Not executed by MCP—you attach them in chat. |
| **`my_ai_tools/agents/`** | LangGraph flows and LLM backends. Plan (auto + interactive), PR review, hello. Shared state and context in `planning_common.py`. |
| **`scripts/`** | CLI and helpers: `plan_cli.py` (interactive flow), `verify_*.py` (tests), `git-utils.sh` (e.g. `pr_review_v2` for cloning PRs). |
| **`docs/`** | Architecture, Dev cookbook, Scratchpad, and design notes (e.g. Multi-Agent-Flow, Self-Correction-Cycle). |
| **Repo root** | `mcp_bridge.py` = MCP entry (stdio); `pyproject.toml`, README. |

---

## System diagram

```mermaid
flowchart TB
    subgraph Callers["Callers"]
        Cursor["Cursor (MCP + @ prompts)"]
        CLI["CLI / scripts"]
    end

    subgraph MCP["MCP (mcp_bridge.py)"]
        Tools["7 tools: hello, plan_auto_*, plan_interactive_*, pr_review_*"]
    end

    subgraph Vault["Prompt vault (no server)"]
        Prompts["pr-review, agent-check-code,\nagent-write-code-from-spec,\nagent-wf-code-check"]
    end

    subgraph Agents["my_ai_tools/agents"]
        Auto["plan_auto"]
        Interactive["plan_interactive"]
        PRReview["pr_review"]
    end

    subgraph Shared["Shared"]
        Common["planning_common"]
        SQLite["agents_state.db"]
    end

    Cursor -->|stdio| MCP
    Cursor -->|@ files| Prompts
    CLI --> Agents
    MCP --> Auto
    MCP --> Interactive
    MCP --> PRReview
    Auto --> Common
    Interactive --> Common
    PRReview --> Shared
    Common --> SQLite
```

---

## MCP Bridge (`mcp_bridge.py`)

- **Role:** FastMCP server over stdio. Cursor (or another client) talks to it; it delegates to the agents package.
- **Tools (7):**

| Tool | Delegates to |
|------|--------------|
| `run_hello` | `hello_world.run_hello` |
| `plan_auto_start` / `plan_auto_resume` | `plan_auto` (auto flow) |
| `plan_interactive_start` / `plan_interactive_resume` | `plan_interactive` (interactive flow) |
| `pr_review_start` / `pr_review_resume` | `pr_review` (PR review flow) |

- Owns the SQLite checkpointer (`agents_state.db`) and issues `thread_id`s for sessions.

---

## Prompt vault (`prompt-vault/`)

- **Purpose:** Reusable prompts for Cursor chat. You @ a file (or several) and provide inputs in the same message; Cursor does not auto-run them.
- **Layout:** `INDEX.md` (id, description, asks_for) and `prompts/<id>.md` per prompt.
- **Current prompts:**

| id | Purpose |
|----|--------|
| `pr-review` | Full PR review: uncommitted + branch vs base, then Principal ML Eng checklist. |
| `agent-check-code` | Code check for self-correction; local changes only, relevant to design spec; outputs **## Recommendations** for the write agent. |
| `agent-write-code-from-spec` | Write code from spec or from check Recommendations; run verification; suggest next check. |
| `agent-wf-code-check` | Orchestrator: in one chat, run write → check → write → … until clean or max iterations (use with @agent-write-code-from-spec and @agent-check-code). |

- **Template:** `_template.md` for new prompts. No MCP tools read the vault; it’s file-based and manual.

---

## Agents (`my_ai_tools/agents/`)

### Flows (LangGraph)

| Flow | Direction | Use |
|------|-----------|-----|
| **Auto** (`plan_auto.py`) | Push: graph calls LLM (Ollama/Anthropic). | plan → review → interface → review → code. Interrupts for human approve/revise. |
| **Interactive** (`plan_interactive.py`) | Pull: graph returns context; caller (Cursor/CLI) provides content. | plan → interface → code. LLM-agnostic. |
| **PR review** (`pr_review.py`) | Push: clone PR via git-utils, one LLM review, present recommendations one at a time. | `pr_review_start(url)` → … → `pr_review_resume(thread_id, feedback)`. |

### Backends and shared

- **Auto backends:** `plan_auto_ollama.py`, `plan_auto_anthropic.py` — same interface (generate_plan, generate_interface, generate_code_and_tests, etc.). Chosen by name in `plan_auto_start(..., backend=...)`.
- **Shared:** `planning_common.py` — state, file names, `load_skill()`, context assembly. Used by both plan flows and by PR review (e.g. pr-review prompt path).

### State

- LangGraph checkpoints to SQLite after each node. Resume with `thread_id`. Supports long-running or multi-session review.

---

## Design in brief

- **Control flow:** Auto = graph calls LLM (push). Interactive = caller provides content (pull). Cursor can’t be invoked by a tool, so “Cursor as LLM” only works in the pull/interactive style.
- **Prompt vault vs MCP:** Vault = prompts you run in Cursor by @’ing. MCP = tools that run LangGraph flows (with their own LLM or with you supplying content). They complement each other; vault is not wired into MCP.
- **Adding an auto backend:** New `plan_auto_<name>.py` with the same function set, register in `plan_auto.py`; no graph or bridge changes.
- **Adding a prompt:** New `prompts/<id>.md`, add a row to `INDEX.md`.

---

## File map

```
my-ai-tools/
├── mcp_bridge.py                 # MCP entry (7 tools)
├── my_ai_tools/
│   ├── cli.py                    # UV: check, tests, mcp-bridge, etc.
│   ├── ollama_client.py
│   └── agents/
│       ├── planning_common.py
│       ├── plan_auto.py
│       ├── plan_auto_ollama.py
│       ├── plan_auto_anthropic.py
│       ├── plan_interactive.py
│       ├── pr_review.py
│       └── hello_world.py
├── prompt-vault/
│   ├── INDEX.md
│   ├── _template.md
│   └── prompts/
│       ├── pr-review.md
│       ├── agent-check-code.md
│       ├── agent-write-code-from-spec.md
│       └── agent-wf-code-check.md
├── scripts/
│   ├── git-utils.sh              # pr_review_v2, etc.
│   ├── plan_cli.py
│   ├── verify_agents.py
│   ├── verify_plan_interactive.py
│   └── verify_plan_auto.py
├── docs/
│   ├── Architecture.md
│   ├── Workflows.md
│   └── ...
├── pyproject.toml
└── README.md
```
