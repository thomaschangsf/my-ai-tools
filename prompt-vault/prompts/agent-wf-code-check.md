# Prompt: Self-Correction Workflow (Orchestrator)

**id:** `agent-wf-code-check`  
**tags:** workflow, self-correction, orchestration, code-check, spec  
**asks_for:** repo, design spec (path or one-line), target path (optional), max_iterations (optional, default 3)  
**outputs:** Code that passes check, or final Recommendations after max iterations

---

## How to trigger

**Cursor does not auto-run prompts.** The @ symbol only *attaches* files to the chat so the model can read them. You do this once:

1. In one message, **attach all three prompts** so the model has them in context:  
   Type `@agent-wf-code-check` then `@agent-write-code-from-spec` then `@agent-check-code` (or add the three files via the @ menu).
2. In the **same message**, give the inputs **once**: repo, design spec (path or one-line), optional target path, optional max iterations (default 3).  
   Example: *"Repo: this workspace. Spec: specs/my-feature.md. Max 3."*

You do **not** feed input to agent-write-code-from-spec in a separate step. The orchestrator uses the repo and spec you provided for the whole cycle (step 1 = write from that spec; later steps = write from the check recommendations the model just produced). One message, one chat; the model then runs write→check→write→… in its replies.

---

## Prompt

You are the **orchestrator** for the **self-correction code workflow**. Run the full cycle in this thread by alternating between the write and check agents. Use the instructions in **@agent-write-code-from-spec** and **@agent-check-code** for each step; this prompt only defines the order and loop.

### Input (from user)
- **Repo root:** &lt;path or "this workspace"&gt;
- **Design spec:** &lt;path to spec file, or one-line description&gt;
- **Target path (optional):** &lt;where to write code, e.g. src/foo/&gt;
- **Max iterations (optional):** &lt;default 3&gt; — stop after this many check→write rounds even if recommendations remain.

### Workflow

1. **Write (from spec)**  
   Apply **@agent-write-code-from-spec**: input = design spec, repo, target path. Produce code, run verification, report Addressed/Deferred (none yet). Do not suggest "run agent-check-code" yet; you will do it in the next step.

2. **Check**  
   Apply **@agent-check-code**: repo, design spec, local scope = whatever is relevant (unstaged + staged + untracked for the new code). Produce **## Recommendations for agent-write-code-from-spec**. If the list is empty or only low/optional items the user accepts, **END**: workflow complete.

3. **Write (from recommendations)**  
   Apply **@agent-write-code-from-spec**: input = the Recommendations block from step 2, repo, target path. Implement each item; report Addressed and Deferred; run verification.

4. **Loop**  
   Go back to step 2 (Check). Repeat until (a) check produces no actionable recommendations, or (b) you reach **max iterations**. If you hit max iterations, output the latest Recommendations and say the user can paste them into @agent-write-code-from-spec for another round.

### Your behavior in this thread
- Perform each step yourself: emit the write output, then the check output, then the next write output, and so on. Do not ask the user to "now run agent-check-code"; you are playing both roles.
- Keep the thread tidy: after each step, briefly label it (e.g. "--- **Step 1: Write from spec** ---") so the user can follow.
- If the user interrupts (e.g. "stop" or "that's enough"), stop and summarize where things stand.

### Clarifying questions
If repo or design spec is missing or unclear, ask once before starting the loop. Otherwise begin with step 1.
