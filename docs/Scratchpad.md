

# 1 Design PR Review Workflow
- Original prompt

```bash
Use cursor skill @/Users/chang/.cursor/skills/ml-engineer-planning/SKILL.md for this chat.

I want to design a langgraph workflow to do pr review

1. We have a similar data pull flow like plan_auto_start and plan_auto_resume; I will call this workflow from cursor
2. Use @scripts/git-utils.sh  pr_review_v2 <Pull request http address> to pull the pr local to directory.  Execute the last command outputed on the output terminal, which changes to the right branch
3. Apply @prompt-vault/prompts/pr-review.md to do a PR review.
4. Issue 1 recommendation at a time; show the most important one first, user may ask more questions.  
5. Ask user for approval before going to the next recommendation
6. This continues until users says abort or all recommendation have been exhausted

Divide this workflow into pr_review_start and pr_review_resume
```

- To trigger in Cursor
```bash
Terminal

cd <PR reviews directory>

agent

Use the MCP tool pr_review_start with pr_url = ‘https://github.com/owner/repo/pull/123

```