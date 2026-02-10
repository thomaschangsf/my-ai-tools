"""Shared state, file I/O, and skill loading for planning flows."""

import os
from pathlib import Path
from typing import TypedDict

SKILL_PATH = Path.home() / ".cursor" / "skills" / "principal-ml-planning" / "SKILL.md"

# Output filenames (shared convention across all planning backends)
PLAN_FILE = "plan.md"
INTERFACE_FILE = "interface.md"
CODE_FILE = "generated_module.py"
TEST_FILE = "test_baseline.py"


class PlanningState(TypedDict):
    """State shared by all planning flows (Ollama, Cursor, etc.)."""

    task_description: str
    project_root: str
    human_feedback: str  # latest feedback from human review ("approved" or revision notes)
    phase: str  # planning, plan_review, interfacing, interface_review, executing, done, error


def ensure_project_path(project_root: str) -> Path:
    """Resolve project path; use cwd if not provided."""
    path = (project_root or os.getcwd()).strip()
    return Path(path).resolve()


def load_skill() -> str:
    """Load the principal-ml-planning SKILL.md content, or return empty string."""
    try:
        if SKILL_PATH.exists():
            return SKILL_PATH.read_text(encoding="utf-8")
    except OSError:
        pass
    return ""


# ---------------------------------------------------------------------------
# Context assembly helpers (used by plan_interactive and CLI)
# ---------------------------------------------------------------------------

def assemble_plan_context(
    task_description: str,
    project_root: str,
    feedback: str = "",
    existing_plan: str = "",
) -> str:
    """Build the prompt/context bundle for the planning phase."""
    skill = load_skill()
    parts = [
        "# Planning Task\n",
        f"**Task:** {task_description}\n",
        f"**Project:** {project_root}\n",
    ]
    if skill:
        parts.append(f"\n## Planning Framework\n\n{skill}\n")
    if existing_plan:
        parts.append(f"\n## Current Plan (needs revision)\n\n{existing_plan}\n")
    if feedback:
        parts.append(f"\n## Revision Feedback\n\n{feedback}\n")
    if existing_plan or feedback:
        parts.append("\nPlease revise the plan to address the feedback above.\n")
    else:
        parts.append(
            "\nGenerate a comprehensive plan in markdown following the planning framework above.\n"
        )
    return "\n".join(parts)


def assemble_interface_context(
    plan_content: str,
    project_root: str,
    feedback: str = "",
    existing_interface: str = "",
) -> str:
    """Build the prompt/context bundle for the interface design phase."""
    parts = [
        "# Interface Design\n",
        f"**Project:** {project_root}\n",
        f"\n## Plan\n\n{plan_content}\n",
    ]
    if existing_interface:
        parts.append(f"\n## Current Interface (needs revision)\n\n{existing_interface}\n")
    if feedback:
        parts.append(f"\n## Revision Feedback\n\n{feedback}\n")
    if existing_interface or feedback:
        parts.append("\nPlease revise the interface to address the feedback above.\n")
    else:
        parts.append(
            "\nGenerate type hints, function signatures, and class signatures in markdown.\n"
        )
    return "\n".join(parts)


def assemble_code_context(
    interface_content: str,
    project_root: str,
    feedback: str = "",
    existing_code: str = "",
) -> str:
    """Build the prompt/context bundle for the code generation phase."""
    parts = [
        "# Code Generation\n",
        f"**Project:** {project_root}\n",
        f"\n## Interface\n\n{interface_content}\n",
    ]
    if existing_code:
        parts.append(f"\n## Current Code (needs revision)\n\n{existing_code}\n")
    if feedback:
        parts.append(f"\n## Revision Feedback\n\n{feedback}\n")
    if existing_code or feedback:
        parts.append("\nPlease revise the code to address the feedback above.\n")
    else:
        parts.append(
            "\nGenerate two sections:\n"
            "1. A Python module implementing the interface (headed with `## MODULE`)\n"
            "2. A pytest test file (headed with `## TEST`)\n"
        )
    return "\n".join(parts)
