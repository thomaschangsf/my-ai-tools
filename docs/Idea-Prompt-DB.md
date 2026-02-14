# Idea-Prompt-DB.md

## Goal

Maintain a small personal “prompt DB” (~20 prompts) that works **across projects**, is **manually triggered** (not automatic), and **hints required parameters** while ensuring **internal URLs/keys are entered at runtime** (never stored).

---

## Mechanisms to store/trigger prompts

### 1) Cursor Skills (procedure-as-prompt)

- **Store**: A `SKILL.md` with a structured playbook (steps, constraints, expected outputs).
- **Trigger**: Explicitly invoke the skill (or rely on Cursor to apply it when relevant).
- **Best for**: Repeatable multi-step workflows (reviews, eval protocols, debugging playbooks).
- **Trade-off**: More “framework” than “snippet”; great structure, slightly heavier to author/edit.

### 2) MCP (my-ai-tools) persistence (prompt DB as a tool)

- **Store**: Prompts/metadata in a persisted store (e.g., SQLite or files managed by the MCP server).
- **Trigger**: Call MCP tools like `list_prompts`, `get_prompt(id)`, `render_prompt(id, params=...)`.
- **Best for**: Guided retrieval (IDs, tags, recency), and returning “required params” before the prompt.
- **Trade-off**: Requires implementing/maintaining the tool surface and storage schema.

### 3) Markdown files (prompt vault)

- **Store**: A personal folder/repo of `.md` prompt files (one per prompt), plus an `INDEX.md`.
- **Trigger**: Manual search/open/copy in Cursor (fast for ~20 prompts).
- **Best for**: Simple, transparent, git-friendly, easy editing; works without any runtime.
- **Trade-off**: Parameter “hinting” is by convention (file schema), not enforced by tooling.

---

## Key decisions you’ve made

- **Scale**: ~20 prompts → optimize for simplicity and speed over heavy infra.
- **Scope**: Personal, cross-project → keep prompts outside any single work repo.
- **Retrieval**: Manually triggered → no auto-injection; user chooses the prompt explicitly.
- **Usability**: Prefer prompts to advertise **required parameters** up front.
- **Security**: Internal URLs and keys must be **entered at runtime** (placeholders only; never stored).
- **Workflow preference**: Work primarily in **Cursor IDE**, with optional CLI usage.

---

## Given those decisions: next steps (with pros/cons)

### Next step A — Create a personal Markdown “Prompt Vault” + a small schema

**What**
- Create a vault directory (outside work repos), e.g. `~/prompt-vault/`.
- Add:
  - `prompts/<id>.md` (one prompt per file)
  - `INDEX.md` (one-line description + required params)
  - `_template.md` (copy/paste scaffold)
- Standardize headers like: `id`, `tags`, `asks_for`, `outputs`, then `## Prompt`.

**Pros**
- Lowest friction; perfect for ~20 prompts.
- Easy to search in Cursor by `id`.
- Easy to review/edit without any tooling.
- Works everywhere (no server running).

**Cons**
- No “form UI” unless you add tooling later.
- Parameter completeness is convention-driven (not enforced).

### Next step B — Add lightweight MCP tools for guided retrieval (optional upgrade)

**What**
- Implement minimal commands in `my-ai-tools`:
  - `prompts_list` → IDs + summaries
  - `prompts_get(id)` → prompt + `asks_for`
  - `prompts_render(id)` → returns a fill-in checklist + template with placeholders
- Storage options:
  - read from the Markdown vault directory (simple), or
  - store in SQLite (more control; more effort).

**Pros**
- Best UX for “hint me what to fill in” before pasting.
- Can support tags/recency (“show my top 5 most-used prompts”).
- Keeps secrets safe by design (placeholders + runtime entry).

**Cons**
- More code + maintenance.
- You’ll want tests to prevent regressions in rendering/parsing.

### Next step C — Add a tiny CLI helper (optional, complements Cursor)

**What**
- A command like:
  - `prompt list`
  - `prompt show <id>` (prints required params first, then the prompt)
  - `prompt copy <id>` (copies to clipboard on macOS)

**Pros**
- Fast retrieval outside Cursor too.
- Pairs well with a Markdown vault (no new storage needed).

**Cons**
- Slight packaging/shell integration overhead.

### Next step D — Reserve Cursor Skills for “playbooks”, not every prompt

**What**
- Only convert prompts into Skills when they represent a multi-step methodology.
- Keep quick “snippets” in Markdown vault instead.

**Pros**
- Clear separation: **Skills = procedures**, **Vault = snippets/templates**.
- Reduces skill sprawl while retaining high leverage.

**Cons**
- Two places to update (vault + skills) if you blur the boundary.

---

## Suggested default path (minimal, high ROI)

- **Start with Next step A** (Markdown vault + schema + index).
- If you feel friction after 1–2 weeks, add **Next step B** (MCP guided retrieval).
- Add **Next step C** only if you often work in terminal contexts.

---

## Current state: using the prompt-vault via PR review (example)

This is the current “happy path” for using `my-ai-tools` + the prompt-vault to drive a PR review **in a different review directory** (so the review workspace is separate from the `my-ai-tools` repo).

### Example flow — trigger a code review in a separate review directory

```bash
cd /Users/thomaschang/Documents/dev/git/reviews

gu pr_review_v2 https://git.soma.salesforce.com/a360/edc-python/pull/488

# Copy the command at end of run

cursor .
```

Then in Cursor:

- **Add the tools repo to the current workspace**: `Cursor -> File -> Add Folder To Workspace -> my-ai-tools`
- **Apply the prompt-vault review prompt in chat**: “Use `@pr-review.md` on this PR”


