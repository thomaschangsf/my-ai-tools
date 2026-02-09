"""
Cursor-agent-backed planning flow (stub).

Unlike plan_with_ollama (where the LLM work happens inside the agent via Ollama),
this flow is designed so that Cursor's LLM is the intelligence layer.  The MCP
tools here manage state and context; Cursor does the actual generation.

TODO: implement Cursor-driven planning tools.
"""
