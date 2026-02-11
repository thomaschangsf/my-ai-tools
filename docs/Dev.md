# Dev.md

```bash
# -------------------------------------------
# Start/develop  my-ai-tools mcp server
# -------------------------------------------
cd ... my-ai-tools
uv run mcp-bridge

uv run python -c "
from mcp_bridge import run_hello
print(run_hello('test'))"

# -------------------------------------------
# MCP tools registered:
# -------------------------------------------
run_hello: OK
plan_auto_start: OK
plan_auto_resume: OK
plan_interactive_start: OK
plan_interactive_resume: OK

### Difference between auto and interactive
- IMOW: auto vs interactive controls whether the MCP tool (using its configured LLM backend) generates the planning artifacts (auto) or whether the client/user supplies the artifact content while the tool mainly provides context and advances phases (interactive).
- plan_auto_* (auto)
    The tool’s backend LLM generates the planning artifacts for you (planner → review → interfacer → review → executor).
    You mainly provide the task description up front, then provide approval or revision feedback at review gates.
    You can pick the LLM backend via backend (per the docstring: "ollama" default or "anthropic").
- plan_interactive_* (interactive) (cursor)
    The tool is LLM-agnostic: it returns a context bundle, and you (or an external LLM / your own reasoning) produce the artifact text.
    You then send that artifact back via plan_interactive_resume(content=...) to advance phases, or send feedback=... to regenerate the context for the same phase.

### Difference between start and resume
- IMOW: start creates a new planning thread and resume continues it via a thread_id, which provides persistence across the multi-step human review/feedback loop.
- *_start
    Creates a new planning thread for a given task_description.
    Returns a thread_id (and, for interactive, a context bundle; for auto, it writes the first artifact and pauses for review).
- *_resume
    Continues an existing thread identified by thread_id.
    You either:
    Approve to advance (auto: feedback="approved"), or
    Provide revision feedback (auto: feedback="<notes>"), or
    For interactive: provide the next artifact (content="...") or feedback to re-issue context for the same phase.

# -------------------------------------------
# Use in any cursor proejct
# -------------------------------------------


put this in ~/.cursor/mcp.json
{
  "mcpServers": {
    "my-ai-tools": {
      "type": "stdio",
      "command": "bash",
      "args": [
        "-lc",
        "cd \"/Users/thomaschang/Documents/dev/git/thomaschangsf/my-ai-tools\" && uv run mcp-bridge"
      ]
    }

  }
}

# How to use from cursor:
Use the MCP tool my-ai-tools.run_hello with input_text = "hi"

# Bad: one time flow
my-ai-tools.plan_interactive_start with these input parameters:
	task_description: "url shortner"
	project_root: /Users/chang/Documents/dev/git/ml/my-ai-tools/tmp


# I might need to switch to plan mode
Run my-ai-tools.plan_interactive in stage-gated mode. After each phase (plan → interface → code → test), stop and ask me whether to proceed. Don’t call *_resume until I reply with either approved or feedback. If I give feedback, apply it and show me the updated artifact before asking to proceed again. Pass in these input parameters:
	task_description: "url shortner"
	project_root: /Users/chang/Documents/dev/git/ml/my-ai-tools/tmp

# From current cursor project, reload cursor everytime my-ai-tools changes
Cursor Command Pallete: "Developer: reload Window"


# -------------------------------------------
# Auto flow (plan_auto): LLM generates internally
# -------------------------------------------
# The graph calls an LLM at each stage. You only review and approve/revise.
# The backend is pluggable: "ollama" (default) or "anthropic".
#
# Prerequisites (Ollama):
#   - Ollama running:  uv run ollama-serve
#   - Model pulled:    ollama pull llama3.2
#
# Prerequisites (Anthropic):
#   - export ANTHROPIC_API_KEY="sk-ant-..."
#   - Optionally: export ANTHROPIC_MODEL="claude-sonnet-4-20250514"
#
# === From Cursor chat (awkward — see "why" below) ===
#
# Step 1 — Start:
#   "Use plan_auto_start with task_description 'Build a URL shortener'
#    and project_root '/path/to/my-project'"
#   Cursor returns a thread_id. Open plan.md and review it.
#
# Step 2 — Revise or approve:
#   To revise:
#     "Use plan_auto_resume with thread_id '<paste-thread-id>'
#      and feedback 'Add more detail on monitoring and rollback'"
#   To approve:
#     "Use plan_auto_resume with thread_id '<paste-thread-id>' and feedback 'approved'"
#
# Step 3 — Approve interface:
#     "Use plan_auto_resume with thread_id '<paste-thread-id>' and feedback 'approved'"
#   Executor writes generated_module.py and test_baseline.py. Done.
#
# Why auto flow is awkward in Cursor chat:
#   - You must manually copy/paste the thread_id between messages.
#   - You must explicitly ask Cursor to call the MCP tool each time.
#   - Cursor's agent doesn't drive the loop — you do, one tool call at a time.
#   - The intelligence comes from local Ollama (llama3.2), not Cursor's LLM,
#     so quality is limited by the local model.
#   - The interactive flow (plan_interactive_start / plan_interactive_resume) fixes this by letting
#     Cursor's own LLM generate the content.
#
# === From the command line (step by step) ===
#
# Step 1 — Start the plan:
uv run python -c "
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from my_ai_tools.agents.plan_auto import start_auto_plan
conn = sqlite3.connect('/tmp/test-auto/state.db', check_same_thread=False)
cp = SqliteSaver(conn)
cp.setup()
result = start_auto_plan('Build a URL shortener', '/tmp/test-auto', thread_id='test-1', checkpointer=cp)
print('Phase:', result.get('phase'))
conn.close()
"
# Review /tmp/test-auto/plan.md

# Step 2 — Revise (optional, repeat as needed):
uv run python -c "
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from my_ai_tools.agents.plan_auto import resume_auto_plan
conn = sqlite3.connect('/tmp/test-auto/state.db', check_same_thread=False)
cp = SqliteSaver(conn)
cp.setup()
result = resume_auto_plan(thread_id='test-1', human_feedback='Add rollback strategy details', checkpointer=cp)
print('Phase:', result.get('phase'))
conn.close()
"  

# Step 3 — Approve plan, proceed to interface:
uv run python -c "
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from my_ai_tools.agents.plan_auto import resume_auto_plan
conn = sqlite3.connect('/tmp/test-auto/state.db', check_same_thread=False)
cp = SqliteSaver(conn)
cp.setup()
result = resume_auto_plan(thread_id='test-1', human_feedback='approved', checkpointer=cp)
print('Phase:', result.get('phase'))
conn.close()
"

# Step 4 — Approve interface, run executor:
uv run python -c "
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from my_ai_tools.agents.plan_auto import resume_auto_plan
conn = sqlite3.connect('/tmp/test-auto/state.db', check_same_thread=False)
cp = SqliteSaver(conn)
cp.setup()
result = resume_auto_plan(thread_id='test-1', human_feedback='approved', checkpointer=cp)
print('Phase:', result.get('phase'))
conn.close()
"

# Expected phase progression:
#   Step 1: plan_review  (planner ran, waiting for review)
#   Step 2: plan_review  (planner revised, still waiting)
#   Step 3: interface_review  (interfacer ran, waiting for review)
#   Step 4: done  (executor ran, all files written)

# === Auto flow with Anthropic backend ===
#
# Same flow, just pass backend="anthropic":
#
# From Cursor chat:
#   "Use plan_auto_start with task_description 'Build a URL shortener',
#    project_root '/tmp/test-anthropic', and backend 'anthropic'"
#
# From the command line:
export ANTHROPIC_API_KEY="sk-ant-..."
uv run python -c "
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from my_ai_tools.agents.plan_auto import start_auto_plan
conn = sqlite3.connect('/tmp/test-anthropic/state.db', check_same_thread=False)
cp = SqliteSaver(conn)
cp.setup()
import os; os.makedirs('/tmp/test-anthropic', exist_ok=True)
result = start_auto_plan('Build a URL shortener', '/tmp/test-anthropic', thread_id='test-1', checkpointer=cp, backend='anthropic')
print('Phase:', result.get('phase'))
conn.close()
"


# -------------------------------------------
# Interactive flow (plan_interactive): caller provides content
# -------------------------------------------
# The graph assembles context (including SKILL.md) and pauses.
# The caller — Cursor's LLM, a CLI, or a human — generates content.
# The graph never calls an LLM itself.
#
# WHY it's LLM-agnostic: the interface is just strings.
#   Agent → context_bundle (str) → [ANY caller] → content (str) → Agent
# The graph doesn't know or care what produced the content.
# This means Cursor, Ollama, Anthropic, OpenAI, or a human all work
# without any code change to plan_interactive.py.
#
# === From Cursor chat (natural conversation) ===
#
# Step 1 — Start:
#   "Use plan_interactive_start with task_description 'Build a URL shortener'
#    and project_root '/path/to/my-project'"
#   Cursor gets a context bundle (includes SKILL.md + task). It generates
#   a plan based on the context — no manual copy/paste needed.
#
# Step 2 — Save plan & get interface context:
#   "Use plan_interactive_resume with thread_id '<id>' and content '<the plan you generated>'"
#   Tool saves plan.md and returns interface design context.
#   Cursor generates the interface.
#
# Step 3 — Save interface & get code context:
#   "Use plan_interactive_resume with thread_id '<id>' and content '<the interface>'"
#
# Step 4 — Save code, done:
#   "Use plan_interactive_resume with thread_id '<id>' and content '<the code>'"
#
# To revise at any step:
#   "Use plan_interactive_resume with thread_id '<id>'
#    and feedback 'Add more detail on caching strategy'"
#   Tool re-assembles context with feedback. Cursor regenerates.
#
# Cross-session: close Cursor, come back later, resume with same thread_id.
#
# === From the terminal (interactive CLI) ===
#
# Uses the same LangGraph graph but drives it with a configurable LLM.
#
# With Ollama (default):
uv run python scripts/plan_cli.py "Build a URL shortener" /tmp/test-interactive

# Manual mode (paste content yourself):
PLANNING_LLM=none uv run python scripts/plan_cli.py "Build a URL shortener" /tmp/test-interactive

# The CLI loops through plan -> interface -> code, generating via LLM
# and pausing for your review at each stage. Enter revision feedback
# or press Enter to accept and continue.


# -------------------------------------------
# Verification
# -------------------------------------------
# All agents (hello + interactive + auto):
uv run python scripts/verify_agents.py

# Interactive only (no LLM needed):
uv run python scripts/verify_plan_interactive.py

# Auto only (requires Ollama):
uv run python scripts/verify_plan_auto.py

# Full check (lint + MCP bridge + all agents):
uv run check
```
