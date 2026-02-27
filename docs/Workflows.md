# Workflows
# 1 TLDR


## 1.1 How to Trigger PR Review form prompt-vault
```bash
cd /Users/thomaschang/Documents/dev/git/reviews

gu pr_review_v2 https://git.soma.salesforce.com/a360/edc-python/pull/488

# Copy the command at end of run; includes ln -s

cursor .

Cursor --> File --> Add Folder To Workspace --> my-ai-tools

Chat: Use @pr-review.md on this PR
```

## 1.2 Convert PDF to MD
- See [[README]]
```bash

# For more flags, read README
TORCH_DEVICE=cpu uv run pdf2md convert \ /Users/thomaschang/Documents/dev/git/thomaschangsf/compendium/thinking/2_agents/paper/skills.pdf \
 --output /Users/thomaschang/Documents/dev/git/thomaschangsf/compendium/thinking/2_agents/paper/output
 
```

## 1.3 Convert MarkDown to RemNote
```bash
@prompt-vault/prompts/learn-convert-to-remnote-v2.md on this file /Users/chang/Documents/dev/git/foundation/compendium/thinking/2_agents/agents_F.P.C.Q.md . Save remnote to tmp/
```

## 1.4 Agentic Dev/Review Cycle
- WIP: See [[Scratchpad.md]]

# 2 Setup
```bash
# ------------------------------
# Set up my-ai-tools
# ------------------------------
git clone https://github.com/thomaschangsf/my-ai-tools

# Start MCP servver
uv run mcp-bridge


# ------------------------------
# Global Cursor MCP config mcp.json
# ------------------------------
cd ~/.cursor/

# Edit mcp.json; make sure the cd path below is the right directory
"my-ai-tools": {
	"type": "stdio",
	"command": "bash",
	"args": [
		"-lc",
		"cd \"/Users/chang/Documents/dev/git/ml/my-ai-tools\" && uv run mcp-bridge"
	]
}
```

# 3 Common Commands

## 3.1 Smoke test MCP
```bash

# ------------------------------
# PR Review Workflow: Set up Clone Project
# ------------------------------
cd /Users/chang/Documents/dev/git/ml/my-ai-tools/tmp/reviews

# cannot be agent
cursor

# Check mcp servier is up
cmd + shift + p --> View: Open MCP Settings

# Smoke test
I want to use the MCP tool my-ai-tools.run_hello with input_text = "hi"


I want to use the MCP tool pr_review_start with pr_url = https://github.com/thomaschangsf/openclaw-fortress/compare/feature/security-readme

```
