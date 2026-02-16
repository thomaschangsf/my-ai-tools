

# 1 Ideas
- How can cursor idea auto-complete a prompt template? for my uber code-review agent.
- Paper to Code agent
- Spec Review/Quality
- Eval prompts so my prompt-vault has no regression
- Interview agent with langgraph + persistence so it knows what to ask


# 2 Multiple Agents
- Multi-agent = separate **prompts** (same node, swap role) and/or separate **nodes** (distinct steps in a graph).
- Ways to orchestrate:
  - **LangGraph:** Conditional steps, interrupts, resume, shared state. Use when you need pause-between-steps or persistence.
  - **Cursor skill:** Instruction playbook (do Step 1, then Step 2). One run, no built-in pause or state.
  - **Cursor chat:** Human drives the sequence; no automation.
  - **Scripts (e.g. Python/shell):** Call tools or flows in sequence; each tool owns its own state.

## Art of good multi-agent prompts
- **Role + scope:** One clear persona and one job (e.g. "Code Critic", not "review and also suggest tests" unless that's one coherent task).
- **Inputs explicit:** Say exactly what this agent receives (e.g. "You are given: repo path, base branch, primary goal").
- **Output shape:** Specify format so the next node or human can parse (e.g. "End with ## Recommendations as a numbered list").
- **Handoff:** If there's a next step, say what the output is for (e.g. "Each recommendation will be shown one at a time; user may approve or ask follow-up").

### Example: Code-Critique agent
- **Role:** Principal ML Engineer performing a code critique (not full PR process—focused on correctness, clarity, and maintainability).
- **Inputs:** Code snippet or diff, optional context (file path, ticket goal). No git commands—caller provides the text.
- **Output:** Structured critique:
  1. **Summary** (2–3 sentences).
  2. **Critical issues** (must-fix): list with location + fix suggestion.
  3. **Suggestions** (nice-to-have): same format.
  4. **Praise** (what’s good): brief.
- **Handoff:** Output is consumed by a "present one finding at a time" node or by the user directly; no follow-up agent required unless you add a "Fix proposer" step.

## Self Correction Agent Code/Review Workflow

Triggering the self-correction workflow in Cursor

### Option 1: Iterative
1. First pass (from spec)
In chat: @agent-write-code-from-spec
Say: repo (or “this workspace”), path to design spec, and optional target path.
Agent writes code, runs checks, then suggests running agent-check-code.

2. Check
In chat: @agent-check-code
Say: repo, design spec (path or one line), and optional local scope (unstaged/staged/committed/untracked).
Agent prints ## Recommendations for agent-write-code-from-spec.

3. Next pass (from check)
In chat: @agent-write-code-from-spec
Paste the ## Recommendations block (or the full check output).
Agent fixes items, reports Addressed/Deferred, then suggests running agent-check-code again.

4. Repeat
Re-run agent-check-code (step 2) on the same repo/spec/scope, then paste the new Recommendations into agent-write-code-from-spec (step 3) until you’re satisfied or there are no more actionable items.


### Option 2: Via One Uber Prompt
```bash
   @agent-wf-code-check @agent-write-code-from-spec @agent-check-code

   Run the self-correction workflow:
   - Repo: this workspace
   - Spec: specs/data-loader.md
   - Target path: src/loaders/ #OPTIONAL
   - Max iterations: 3
```