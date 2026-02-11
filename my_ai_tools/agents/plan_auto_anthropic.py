"""LLM helpers for the auto planning flow (Anthropic HTTP backend).

Uses the Anthropic Messages API directly via urllib (no SDK dependency).

Environment variables:
    ANTHROPIC_API_KEY   Required. Your Anthropic API key.
    ANTHROPIC_MODEL     Model name (default: claude-sonnet-4-20250514).
"""

import json
import os
import urllib.request

from .planning_common import load_skill

_API_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"


def _get_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Export it before running: export ANTHROPIC_API_KEY='sk-ant-...'"
        )
    return key


def _get_model() -> str:
    return os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")


def _chat(system: str, user: str) -> str:
    """Single-turn Anthropic Messages API call. Returns assistant text."""
    api_key = _get_api_key()
    model = _get_model()

    headers = {
        "x-api-key": api_key,
        "anthropic-version": _API_VERSION,
        "content-type": "application/json",
    }
    body = json.dumps({
        "model": model,
        "max_tokens": 4096,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode("utf-8")

    req = urllib.request.Request(_API_URL, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        # Response: {"content": [{"type": "text", "text": "..."}], ...}
        return data["content"][0]["text"].strip()
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        return f"[Anthropic API error {e.code}: {error_body}]"
    except Exception as e:
        return f"[LLM error: {e}]"


def chat(system: str, user: str) -> str:
    """Single-turn chat (public). Used by pr_review and other flows."""
    return _chat(system, user)


# ---------------------------------------------------------------------------
# Public interface — same signatures as plan_auto_ollama
# ---------------------------------------------------------------------------

def generate_plan(task_description: str, project_root: str) -> str:
    """Generate a plan using the principal-ml-planning skill."""
    skill = load_skill()
    system = (
        "You are a principal ML engineer at a FANG company. "
        "Output a clear, actionable plan in markdown.\n\n"
    )
    if skill:
        system += f"Follow this planning framework:\n\n{skill}\n\n"
    system += "Write only the plan content, no preamble."
    user = (
        f"Task: {task_description}\n\nProject path: {project_root}\n\n"
        "Write plan.md content following the planning framework above."
    )
    return _chat(system, user)


def generate_plan_revision(
    task_description: str,
    project_root: str,
    existing_plan: str,
    feedback: str,
) -> str:
    """Revise an existing plan based on human feedback."""
    skill = load_skill()
    system = (
        "You are a principal ML engineer at a FANG company. "
        "Revise the given plan based on human feedback. Output improved markdown.\n\n"
    )
    if skill:
        system += f"Follow this planning framework:\n\n{skill}\n\n"
    system += "Write only the revised plan content, no preamble."
    user = (
        f"Task: {task_description}\n\nProject path: {project_root}\n\n"
        f"Current plan:\n{existing_plan}\n\n"
        f"Human feedback:\n{feedback}\n\n"
        "Revise the plan to address the feedback."
    )
    return _chat(system, user)


def generate_interface(plan_content: str, project_root: str) -> str:
    """Generate interface (type hints / class signatures) for interface.md."""
    system = (
        "You are a software architect. Output type hints, function signatures, and class "
        "signatures in markdown. Write only the interface content, no preamble."
    )
    user = (
        f"Plan:\n{plan_content}\n\nProject path: {project_root}\n\n"
        "Write interface.md content (APIs, types, signatures in markdown)."
    )
    return _chat(system, user)


def generate_interface_revision(
    plan_content: str,
    project_root: str,
    existing_interface: str,
    feedback: str,
) -> str:
    """Revise an existing interface based on human feedback."""
    system = (
        "You are a software architect. Revise the interface based on human feedback. "
        "Output type hints, function signatures, and class signatures in markdown. "
        "Write only the revised interface content, no preamble."
    )
    user = (
        f"Plan:\n{plan_content}\n\nProject path: {project_root}\n\n"
        f"Current interface:\n{existing_interface}\n\n"
        f"Human feedback:\n{feedback}\n\n"
        "Revise the interface to address the feedback."
    )
    return _chat(system, user)


def generate_code_and_tests(
    interface_content: str, project_root: str
) -> tuple[str, str]:
    """Generate boilerplate code and test_baseline.py content. Returns (code, tests)."""
    system = (
        "You are a Python developer. Output only valid Python code. "
        "First block: main module boilerplate. Second block: pytest test file content. "
        "Use clear section headers: ## MODULE and ## TEST if needed."
    )
    user = (
        f"Interface:\n{interface_content}\n\nProject path: {project_root}\n\n"
        "1) Generate Python module boilerplate. 2) Generate test_baseline.py with pytest tests."
    )
    raw = _chat(system, user)
    if "## TEST" in raw:
        parts = raw.split("## TEST", 1)
        code = parts[0].replace("## MODULE", "").strip()
        test = parts[1].strip()
    else:
        code = raw
        test = "# Add pytest tests here"
    return code, test
