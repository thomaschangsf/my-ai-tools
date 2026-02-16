# Workflows
# 1 TLDR

### How to Trigger Prompt form prompt-vault
```bash
cd /Users/thomaschang/Documents/dev/git/reviews

gu pr_review_v2 https://git.soma.salesforce.com/a360/edc-python/pull/488

# Copy the command at end of run

cursor .

Cursor --> File --> Add Folder To Workspace --> my-ai-tools

Chat: Use @pr-review.md on this PR
```



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
