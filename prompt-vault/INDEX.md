# Prompt Vault Index

One-line description and required params. Files live in `prompts/<id>.md`.

| id | description | asks_for |
|----|-------------|----------|
| pr-review | Principal ML Engineer code review: uncommitted diff + branch vs base, then PR checklist | repo, base_branch, primary_goal_brief |
| agent-check-code | Code check for self-correction; local only (unstaged/staged/committed/untracked), relevant to design spec; batch Recommendations | repo, design spec (path or one-line), local scope (optional) |
| agent-write-code-from-spec | Write from spec or check feedback; run verification; Addressed/Deferred; suggest next agent-check-code | input (spec path or Recommendations), repo, target path (optional) |
| agent-wf-code-check | Orchestrator: run write→check→write→… in one thread until clean or max iterations | repo, design spec, target path (optional), max_iterations (optional) |
