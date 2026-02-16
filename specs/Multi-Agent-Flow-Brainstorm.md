# Multi-Agent Flow for Coding — Brainstorm

**Context:** Prompts (vault), MCP (my-ai-tools), Cursor rules, Cursor skills. How to implement and use multi-agent flows as an ML engineer.

---

## 1. Landscape map: where each piece fits

| Layer | What it is | Role in multi-agent flow |
|-------|------------|---------------------------|
| **Prompt vault** | Markdown prompts + INDEX, `asks_for` | **Per-agent system prompts & task templates.** One prompt per “agent role” or phase (e.g. `pr-review`, `design-review`, `test-gen`). Parameters filled at runtime. |
| **MCP** | Bridge + LangGraph flows, checkpointer, thread_id | **Orchestration & persistence.** Defines graphs (nodes = agents/phases), interrupts, resume. Cursor (or CLI) invokes tools; state lives across sessions. |
| **Cursor rules** | Project/workspace conventions (e.g. `.cursor/rules/`, RULE.md) | **Guardrails for every agent in this workspace.** Style, patterns, “never do X.” Applied automatically when the LLM runs in Cursor. |
| **Cursor skills** | SKILL.md playbooks (procedure-as-prompt) | **Structured methodology for a phase.** E.g. ml-engineer-planning (RFC, trade-offs, mermaid). Loaded into context for Planner/Designer nodes. |

**Multi-agent = multiple “roles” or “phases” in a single flow.** Each role can be:

- A **node** in a LangGraph (like your Planner / Interfacer / Executor).
- A **prompt** from the vault (e.g. “you are the Reviewer”).
- A **skill** loaded for that node (e.g. Principal ML Eng checklist for the Reviewer).

So: **MCP = graph + persistence**, **vault = agent prompts**, **skills = phase-specific playbooks**, **rules = global guardrails.**

---

## 2. How to implement multi-agent flows (patterns)

### Pattern A — Add a new LangGraph flow (like PR review)

- **Where:** New file under `my_ai_tools/agents/`, e.g. `design_review.py`.
- **What:** StateGraph with nodes (e.g. `load_spec` → `design_review` → `present_findings` → `gate`).
- **Prompts:** Either inline in the node, or `load_skill()` / read from `prompt-vault/prompts/<id>.md`.
- **MCP:** Register `design_review_start` and `design_review_resume` in `mcp_bridge.py`; same checkpointer, new thread_id namespace.
- **Best for:** Flows that need interrupt/resume and cross-session state.

### Pattern B — Compose existing flows (sequential)

- **Idea:** One MCP tool could “finish” one flow and return a summary; the user (or another tool) starts the next flow with that summary as input.
- **Example:** `plan_auto_*` produces `plan.md` + `interface.md` → user runs `pr_review_start` on the *generated* branch (review the plan + code as a “PR”).
- **Implementation:** No new graph; use existing tools in sequence. Optional: a “meta” CLI or Cursor instruction that says “run plan_auto, then open the repo and run pr_review with prompt X.”

### Pattern C — One graph, multiple “agent” nodes with different prompts/skills

- **Idea:** Same graph, but each node uses a different prompt (vault) and/or skill.
- **Example:** Planner (skill: ml-engineer-planning) → Security Reviewer (prompt: `security-review.md`) → Executor (prompt: `code-gen.md`).
- **Implementation:** In each node, `load_skill()` or read vault by id; pass to LLM backend. Backend stays pluggable (Ollama/Anthropic).

### Pattern D — Interactive (pull) flow as “orchestrator”

- **Idea:** The interactive flow already returns `context_bundle` and accepts `content`. The *caller* can be “another agent”: e.g. Cursor for phase 1, a script that calls Ollama for phase 2.
- **Implementation:** No change to the graph. Use `plan_interactive_start` / `plan_interactive_resume`; vary who generates the content (human, Cursor, or another service).

### Pattern E — Vault + MCP “prompt loader” (optional upgrade)

- **Idea:** MCP tools `prompts_list`, `prompts_get(id)`, `prompts_render(id, params)` that read from the Markdown vault. Then any flow can say “use prompt id=design-review with params X.”
- **Implementation:** Lightweight tools in mcp_bridge that read `prompt-vault/` and return prompt text + `asks_for`. Keeps vault as single source of truth for agent prompts.

---

## 3. Five useful multi-agent flows for an ML engineer

Below are five flows that fit your stack (MCP + vault + skills + rules) and ML engineering daily work.

---

### Flow 1 — Plan → Interface → Code → Review (extended auto with review)

**What:** Your current auto flow (Planner → Interfacer → Executor) plus a **final review node** that runs the Principal ML Engineer PR checklist on the generated code.

**Agents:** Planner (skill: ml-engineer-planning), Interfacer, Executor, Reviewer (prompt: `pr-review.md` or a “self-review” variant).

**Why useful:** Catches design and code issues before you treat the output as “done.” One thread_id, one resume flow.

**Implementation:** Add node `review_generated` after Executor; load `prompt-vault/prompts/pr-review.md` (or a `self-review.md` that doesn’t need a real PR URL). Input = `plan.md` + `interface.md` + `generated_module.py` + diff. One interrupt before “apply fixes” so human can approve or add feedback.

**Fits:** Pattern C (one graph, multiple agent prompts/skills).

---

### Flow 2 — Design review (RFC / ADR on a spec or doc)

**What:** You have a spec or ADR (e.g. `specs/feature-x.md`). The flow: load doc → **Design Reviewer** (Principal ML Eng lens) → present findings one-by-one with approve/revise.

**Agents:** Loader (read spec + repo context), Design Reviewer (skill: ml-engineer-planning + checklist from vault).

**Why useful:** Consistent, rigorous design review without a live human reviewer; reuse your SKILL.md and vault prompts.

**Implementation:** New graph `design_review.py`: `load_spec` → `review` (LLM with design checklist + trade-offs, scalability) → `present_finding` → `gate` (like PR review: one finding at a time, approve/abort). Prompt from vault: e.g. `design-review.md` with `asks_for: spec_path, primary_goal`.

**Fits:** Pattern A (new flow) + vault + skill.

---

### Flow 3 — Bug triage → Reproduce → Fix proposal (debugging loop)

**What:** Input: bug report or failing test. Agent 1: triage and suggest reproduction steps. Agent 2 (or same agent, next node): propose a fix (patch or code edit). Human approves or gives feedback; loop until “approved.”

**Agents:** Triage (summarize bug, suggest repro), Fix proposer (code + test change), optional Reviewer.

**Why useful:** Structured debugging with clear handoffs; you can use a “debugging playbook” skill and vault prompt for each phase.

**Implementation:** New graph: `triage` → `propose_fix` → `gate` (interrupt; human says “approved” / “revise: …”). Optional: add `review_fix` node with `pr-review.md`-style checklist. Vault: `bug-triage.md`, `fix-proposal.md`.

**Fits:** Pattern A + vault; optional Pattern C if you add a dedicated Reviewer node.

---

### Flow 4 — Dataset / feature spec → Data contract + validation code

**What:** Input: short spec of a dataset or feature (e.g. “user events with fields X, Y, Z”). Agent 1: produce a data contract (schema, semantics, constraints). Agent 2: generate validation code (or Great Expectations / Pandera snippets). Human reviews contract and code.

**Agents:** Contract author (schema + docs), Validator coder (code from contract).

**Why useful:** ML pipelines live or die on data contracts; having a repeatable flow keeps contracts and validation in sync.

**Implementation:** New graph: `contract_from_spec` → `review_contract` (interrupt) → `generate_validation` → `review_code` (interrupt). Vault: `data-contract.md`, `validation-code.md`. Skill: optional “data contract” playbook in a SKILL.md.

**Fits:** Pattern A + vault; two-phase review (contract then code).

---

### Flow 5 — Experiment log → Report + recommendations

**What:** Input: experiment log (e.g. MLflow run, or a markdown log of runs). Agent 1: summarize results and compare. Agent 2: produce short recommendations (next experiments, hyperparameters, or “ship it / don’t ship”).

**Agents:** Summarizer, Recommender.

**Why useful:** Turn raw logs into actionable narrative; good for weekly reviews or before writing a formal report.

**Implementation:** New graph: `load_log` → `summarize` → `recommend` → `present` (one block at a time, gate). Can be interactive (pull): Cursor or CLI provides the log path; backend does summarize + recommend. Vault: `experiment-summary.md`, `experiment-recommendations.md`.

**Fits:** Pattern A or D (interactive if you want “paste log, get report” in Cursor).

---

## 4. Summary table

| Flow | Main agents | Vault prompts | Skill | MCP pattern |
|------|-------------|---------------|-------|-------------|
| 1. Plan → … → Review | Planner, Interfacer, Executor, Reviewer | pr-review (or self-review) | ml-engineer-planning | Extend auto (C) |
| 2. Design review | Loader, Design Reviewer | design-review | ml-engineer-planning | New flow (A) |
| 3. Bug triage → Fix | Triage, Fix proposer, (Reviewer) | bug-triage, fix-proposal | optional debug playbook | New flow (A) |
| 4. Data contract + validation | Contract author, Validator coder | data-contract, validation-code | optional | New flow (A) |
| 5. Experiment log → Report | Summarizer, Recommender | experiment-summary, experiment-recommendations | — | New flow (A) or interactive (D) |

---

## 5. Suggested next steps

1. **Implement one new flow** (e.g. Design review or Bug triage) using Pattern A: new file in `agents/`, two MCP tools, one or two vault prompts.
2. **Add a “self-review” prompt** to the vault and optionally a **Reviewer node** to the auto flow (Flow 1).
3. **Optionally** add MCP prompt-loader tools (Pattern E) so every flow can resolve prompts by id and `asks_for` from the vault.
4. **Document** in Architecture.md how “agent” = node + (vault prompt + optional skill), and how new flows are added (file map + MCP table).

This keeps your existing split: **vault = what each agent says**, **skills = how they reason**, **MCP = how they’re chained and resumed**, **rules = how the workspace constrains them.**
