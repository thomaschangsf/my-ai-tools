# Self-Correction Cycle: Prompt Critique & Improvements

**Goal:** End-to-end loop for ML code: spec → write → check → [fix from feedback] → check → … until acceptable.

**Status:** Simplified agent-check-code and agent-write-code-from-spec per this doc (batch-first check, narrow scope, handoff, Addressed/Deferred). See `prompt-vault/prompts/` for current prompts.

---

**Original gap:** The three prompts (agent-check-code, agent-write-code-from-spec, pr-review) don’t explicitly form a **cycle** with a shared handoff format and “next step” instructions. The loop exists only in the user’s head.

---

## 1. What’s missing for a true self-correction cycle

| Need | Current state | Issue |
|------|----------------|--------|
| **Structured feedback (check → write)** | agent-check-code is interactive, summary-first or one-at-a-time | Write agent gets free-form text; no guaranteed numbered list with location + fix. Hard to “implement items 1–5” reliably. |
| **Explicit “next step” after write** | agent-write-code says “ask if user wants … agent-check-code again” | Doesn’t say “suggest running agent-check-code on **this scope** (e.g. staged)” to close the loop. |
| **Cycle awareness** | Neither prompt says “you are step N of a loop” | Agent doesn’t know to preserve context (e.g. “iteration 2; these items already fixed”). |
| **ML-specific verification** | Write runs pytest/linters only | ML code often needs a minimal train/eval smoke run; not mentioned. |
| **ML-specific review** | agent-check-code has generic “contracts, types” | No explicit ML bullets: data contracts, feature consistency, serialization, reproducibility (seeds/versions). |

---

## 2. Recommended prompt changes

### agent-check-code

- **Add optional output mode:** When the user says “give feedback for agent-write-code” (or “batch” / “export”), output a single block at the end:
  - `## Recommendations for agent-write-code-from-spec`
  - Numbered list: `N. [severity] **location** (file:line or path). Finding. Suggested fix.`
  - So the write agent can consume it unambiguously.
- **Add ML-specific review bullets** (in “Your review tasks”):
  - Data contracts and feature consistency (shapes, dtypes, nulls).
  - Model/serialization (save/load, versioning, backward compat).
  - Reproducibility (seeds, env, dependency versions) where relevant.
- **Handoff line:** “If the user will pass this to agent-write-code-from-spec, provide the structured Recommendations block above.”

### agent-write-code-from-spec

- **When input is agent-check-code feedback:**
  - “Look for a ## Recommendations or numbered list. Implement each item; at the end list **Addressed** (with numbers) and **Deferred** (with reason).”
  - Reduces duplicate work and gives the next check a clear baseline.
- **After delivering code:**
  - “Suggested next step: run **agent-check-code** on &lt;scope: staged or path X&gt; to verify and close the loop. If issues remain, paste the new feedback here for another iteration.”
- **ML verification:**
  - “For ML code: if the repo has training/eval or smoke scripts, run a minimal run (e.g. 1 step or tiny data) if feasible; report success/failure and any errors.”

### Optional: cycle “meta” prompt or vault doc

- One short doc (e.g. `prompts/cycle-spec-check-write.md` or a section in Scratchpad):
  - “Self-correction cycle: 1) Provide spec or prior check feedback. 2) Use agent-write-code-from-spec. 3) Run agent-check-code on the written scope (staged or path). 4) If there are blockers/highs, paste feedback into agent-write-code-from-spec and repeat from 2. Stop when check passes or after N iterations.”
  - Helps you (or a future script) run the loop without remembering the order.

---

## 3. Summary table

| Prompt | Change |
|--------|--------|
| **agent-check-code** | Optional structured “Recommendations for agent-write-code” block; ML-specific review bullets; handoff note. |
| **agent-write-code-from-spec** | Parse numbered feedback; report Addressed/Deferred; suggest “run agent-check-code on &lt;scope&gt;”; ML smoke-run verification. |
| **Optional** | One cycle doc: spec → write → check → [feedback → write] until clean. |

---

## 4. What to leave as-is

- **pr-review** is for full PR context (uncommitted + branch vs base + checklist). Keep it separate; the self-correction cycle is spec + check + write. You can run pr-review after the cycle when you’re ready to open a PR.
- **Interactive style** of agent-check-code is still useful for ad-hoc Q&A; the “batch” format is an add-on when the user wants to feed the write agent.

Implementing the changes above gives you a clear, repeatable loop and makes the handoff between check and write explicit and parseable.
