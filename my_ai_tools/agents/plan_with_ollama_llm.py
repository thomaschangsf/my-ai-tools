"""LLM helpers for the Ollama-backed planning flow."""

import ollama

from .planning_common import load_skill


def _chat(model: str, system: str, user: str) -> str:
    """Single turn with system + user message. Returns assistant content."""
    try:
        r = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return (r.get("message") or {}).get("content", "").strip()
    except Exception as e:
        return f"[LLM error: {e}]"


def generate_plan(task_description: str, project_root: str, model: str) -> str:
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
    return _chat(model, system, user)


def generate_plan_revision(
    task_description: str,
    project_root: str,
    existing_plan: str,
    feedback: str,
    model: str,
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
    return _chat(model, system, user)


def generate_interface(plan_content: str, project_root: str, model: str) -> str:
    """Generate interface (type hints / class signatures) for interface.md."""
    system = (
        "You are a software architect. Output type hints, function signatures, and class "
        "signatures in markdown. Write only the interface content, no preamble."
    )
    user = (
        f"Plan:\n{plan_content}\n\nProject path: {project_root}\n\n"
        "Write interface.md content (APIs, types, signatures in markdown)."
    )
    return _chat(model, system, user)


def generate_interface_revision(
    plan_content: str,
    project_root: str,
    existing_interface: str,
    feedback: str,
    model: str,
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
    return _chat(model, system, user)


def generate_code_and_tests(
    interface_content: str, project_root: str, model: str
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
    raw = _chat(model, system, user)
    if "## TEST" in raw:
        parts = raw.split("## TEST", 1)
        code = parts[0].replace("## MODULE", "").strip()
        test = parts[1].strip()
    else:
        code = raw
        test = "# Add pytest tests here"
    return code, test
