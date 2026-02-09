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
