"""
PR review flow: pull PR via git-utils pr_review_v2, assemble context, then
present recommendations one at a time. Like plan_interactive — no LLM inside
the graph; Cursor's LLM (or the caller) generates the review from the context.

Graph:
    START -> pull_data -> assemble_review_context -> [interrupt]
        -> (caller provides review content) -> gate_review (inject) -> present_recommendation
        -> [interrupt] -> gate (approved/abort) -> present_recommendation or END

Invoked from Cursor via pr_review_start(pr_url) and pr_review_resume(thread_id, content=..., feedback=...).
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver

# Repo root: my_ai_tools/agents/pr_review.py -> ../../.. = repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PROMPT_PATH = _REPO_ROOT / "prompt-vault" / "prompts" / "pr-review.md"
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "git-utils.sh"
DEFAULT_REVIEWS_DIR = os.environ.get("REVIEWS_DIR", "/Users/thomaschang/Documents/dev/git/reviews")
DEFAULT_BASE_BRANCH = os.environ.get("BASE_BRANCH", "master")


class PRReviewState(TypedDict):
    pr_url: str
    repo_path: str
    recommendations: list
    current_index: int
    human_feedback: str
    phase: str
    full_review_text: str
    current_recommendation_text: str
    # Interactive: context for caller's LLM; caller sends back the review text
    review_context_bundle: str
    generated_review_content: str


# ---------------------------------------------------------------------------
# Helpers: PR number, git-utils invocation, repo context, LLM, parsing
# ---------------------------------------------------------------------------

def parse_pr_number(pr_url: str) -> int | None:
    """Extract PR number from URL (e.g. /pull/123 -> 123)."""
    clean = (pr_url or "").strip().lstrip("@")
    m = re.search(r"/pull/([0-9]+)", clean)
    return int(m.group(1)) if m else None


def run_pr_review_v2_and_sync(pr_url: str) -> tuple[str, str]:
    """
    Run scripts/git-utils.sh pr_review_v2 <url>, capture the one-line eval command
    from stdout, execute it in a subprocess, return (repo_path, pr_branch).

    Raises on failure (script error or missing stdout).
    """
    if not _SCRIPT_PATH.exists():
        raise FileNotFoundError(f"git-utils script not found: {_SCRIPT_PATH}")
    # Run as command (not sourced) so script emits the one-line eval to stdout
    result = subprocess.run(
        ["bash", str(_SCRIPT_PATH), "pr_review_v2", pr_url],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    line = (result.stdout or "").strip().splitlines()
    line = line[-1].strip() if line else ""
    if not line:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(
            f"pr_review_v2 produced no stdout (exit {result.returncode}). stderr: {stderr[:500]}"
        )
    # Execute the command so the repo is cloned/updated and on the PR branch
    subprocess.run(line, shell=True, cwd=str(_REPO_ROOT), timeout=120, check=True)
    # Parse repo_path from "cd \"path\" && ..."
    m = re.match(r'cd\s+"([^"]+)"', line)
    repo_path = m.group(1) if m else ""
    if not repo_path:
        pr_num = parse_pr_number(pr_url)
        repo_path = str(Path(DEFAULT_REVIEWS_DIR) / f"pr-review-{pr_num}")
    pr_num = parse_pr_number(pr_url)
    pr_branch = f"pr-{pr_num}" if pr_num else "pr-0"
    return repo_path, pr_branch


def get_repo_context(repo_path: str, base_branch: str = DEFAULT_BASE_BRANCH) -> dict[str, str]:
    """Run git status, diff, branch diff, optional log in repo_path; return dict of outputs."""
    path = Path(repo_path).resolve()
    if not path.is_dir():
        return {"error": f"Not a directory: {path}"}

    def run(cmd: list[str], max_bytes: int = 200_000) -> str:
        try:
            out = subprocess.run(
                cmd,
                cwd=str(path),
                capture_output=True,
                text=True,
                timeout=30,
            )
            text = (out.stdout or "") + (out.stderr or "")
            if len(text) > max_bytes:
                text = text[:max_bytes] + "\n\n... (truncated)"
            return text
        except Exception as e:
            return str(e)

    status = run(["git", "status"])
    diff = run(["git", "diff"])
    branch_diff = run(["git", "diff", f"origin/{base_branch}...HEAD"])
    log = run(["git", "log", "--oneline", "--decorate", "--graph", "--max-count", "25", "--first-parent"])
    return {
        "status": status,
        "diff": diff,
        "branch_diff": branch_diff,
        "log": log,
    }


def load_pr_review_prompt() -> str:
    """Load prompt-vault/prompts/pr-review.md; use content under ## Prompt if present."""
    try:
        if _PROMPT_PATH.exists():
            text = _PROMPT_PATH.read_text(encoding="utf-8")
            if "## Prompt" in text:
                text = text.split("## Prompt", 1)[1].strip()
            return text
    except OSError:
        pass
    return "You are a Principal Machine Learning Engineer doing a rigorous code review."


def parse_recommendations(full_text: str) -> list[str]:
    """
    Parse a numbered list from a "## Recommendations" section.
    Fallback: if no section or parse fails, return [full_text] as single recommendation.
    """
    if not full_text or not full_text.strip():
        return []
    text = full_text.strip()
    # Find ## Recommendations (or similar)
    section_match = re.search(
        r"##\s*Recommendations?\s*\n(.*)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if section_match:
        section = section_match.group(1).strip()
    else:
        section = text
    # Split by lines that start with number and . or )
    parts = re.split(r"\n(?=\s*\d+[.)]\s+)", section)
    items = [p.strip() for p in parts if p.strip()]
    # Remove leading "1. " etc from first line of each item
    cleaned = []
    for p in items:
        p = re.sub(r"^\s*\d+[.)]\s*", "", p, count=1).strip()
        if p:
            cleaned.append(p)
    if cleaned:
        return cleaned
    if section.strip():
        return [section]
    return [full_text]


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

def _pull_data(state: PRReviewState) -> dict[str, Any]:
    """Run pr_review_v2, execute eval command, set repo_path and phase."""
    pr_url = state["pr_url"]
    try:
        repo_path, _ = run_pr_review_v2_and_sync(pr_url)
        return {
            "repo_path": repo_path,
            "phase": "review",
            "recommendations": [],
            "current_index": 0,
        }
    except Exception as e:
        return {
            "phase": "error",
            "full_review_text": str(e),
            "recommendations": [str(e)],
        }


def _assemble_review_context(state: PRReviewState) -> dict[str, Any]:
    """Build context bundle for the caller's LLM. No LLM call inside the graph."""
    repo_path = state.get("repo_path") or ""
    base_branch = DEFAULT_BASE_BRANCH
    ctx = get_repo_context(repo_path, base_branch)
    if ctx.get("error"):
        return {
            "phase": "error",
            "review_context_bundle": "",
            "recommendations": [ctx["error"]],
        }
    system = load_pr_review_prompt()
    system += "\n\nEnd your response with a **## Recommendations** section containing a numbered list (1. 2. 3. ...) of actionable recommendations, most important first (blockers → high → medium → low)."
    user_parts = [
        "Use the following git outputs as source of truth.\n",
        "--- git status ---\n", ctx.get("status", ""),
        "\n--- git diff (uncommitted) ---\n", ctx.get("diff", ""),
        "\n--- git diff origin/", base_branch, "...HEAD (branch vs base) ---\n", ctx.get("branch_diff", ""),
        "\n--- git log (optional) ---\n", ctx.get("log", ""),
    ]
    user_content = "".join(user_parts)
    bundle = f"## System / role\n\n{system}\n\n## User / repo context\n\n{user_content}"
    return {
        "phase": "review",
        "review_context_bundle": bundle,
        "generated_review_content": "",
    }


def _gate_review(state: PRReviewState) -> dict[str, Any]:
    """Inject caller-provided review content: parse recommendations and set state."""
    content = (state.get("generated_review_content") or "").strip()
    if not content:
        return {}
    recommendations = parse_recommendations(content)
    if not recommendations:
        recommendations = [content]
    return {
        "phase": "recommendation",
        "full_review_text": content,
        "recommendations": recommendations,
        "current_index": 0,
        "current_recommendation_text": recommendations[0] if recommendations else "",
        "generated_review_content": "",
    }


def _present_recommendation(state: PRReviewState) -> dict[str, Any]:
    """Pass-through: set current_recommendation_text for display. Gate runs after interrupt."""
    recs = state.get("recommendations") or []
    idx = state.get("current_index", 0)
    text = recs[idx] if 0 <= idx < len(recs) else ""
    return {"current_recommendation_text": text, "phase": "recommendation"}


def _gate(state: PRReviewState) -> dict[str, Any]:
    """Update current_index on approved, route to present_recommendation or END."""
    feedback = (state.get("human_feedback") or "").strip().lower()
    recs = state.get("recommendations") or []
    idx = state.get("current_index", 0)
    if feedback == "abort":
        return {"phase": "aborted", "current_index": idx}
    if feedback in ("approved", "next", "continue", "yes", "ok"):
        next_idx = idx + 1
        if next_idx >= len(recs):
            return {"phase": "done", "current_index": next_idx}
        return {"phase": "recommendation", "current_index": next_idx}
    # "ask more" or other: stay on same recommendation (no index change)
    return {"phase": "recommendation", "current_index": idx}


def _route_after_gate(state: PRReviewState) -> str:
    """Route: abort/done -> END; else -> present_recommendation."""
    phase = state.get("phase", "")
    if phase in ("aborted", "done"):
        return "__end__"
    return "present_recommendation"


def _route_after_gate_review(state: PRReviewState) -> str:
    """Route: error -> END; else -> present_recommendation."""
    if state.get("phase") == "error":
        return "__end__"
    return "present_recommendation"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph(checkpointer: SqliteSaver):
    workflow = StateGraph(PRReviewState)
    workflow.add_node("pull_data", _pull_data)
    workflow.add_node("assemble_review_context", _assemble_review_context)
    workflow.add_node("gate_review", _gate_review)
    workflow.add_node("present_recommendation", _present_recommendation)
    workflow.add_node("gate", _gate)

    workflow.add_edge(START, "pull_data")
    workflow.add_edge("pull_data", "assemble_review_context")
    workflow.add_edge("assemble_review_context", "gate_review")
    workflow.add_conditional_edges(
        "gate_review",
        _route_after_gate_review,
        {"present_recommendation": "present_recommendation", "__end__": END},
    )
    workflow.add_edge("present_recommendation", "gate")
    workflow.add_conditional_edges(
        "gate",
        _route_after_gate,
        {"present_recommendation": "present_recommendation", "__end__": END},
    )

    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["gate_review", "gate"],
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_pr_review(
    pr_url: str,
    *,
    thread_id: str,
    checkpointer: SqliteSaver,
) -> dict[str, Any]:
    """Start the PR review flow. Runs pull_data and assemble_review_context, then pauses.
    Returns review_context_bundle for the caller's LLM to generate the review.
    Caller then calls resume_pr_review(thread_id, content=<review text>) to submit it."""
    graph = build_graph(checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    initial: PRReviewState = {
        "pr_url": pr_url,
        "repo_path": "",
        "recommendations": [],
        "current_index": 0,
        "human_feedback": "",
        "phase": "pull",
        "full_review_text": "",
        "current_recommendation_text": "",
        "review_context_bundle": "",
        "generated_review_content": "",
    }
    result = graph.invoke(initial, config=config)
    return result


def resume_pr_review(
    *,
    thread_id: str,
    content: str = "",
    human_feedback: str = "",
    checkpointer: SqliteSaver,
) -> dict[str, Any]:
    """Resume the PR review flow.
    - content: the full review text (with ## Recommendations) from the caller's LLM; submit after start.
    - human_feedback: approved/next/abort when stepping through recommendations."""
    graph = build_graph(checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    update: dict[str, str] = {}
    if content:
        update["generated_review_content"] = content
    if human_feedback:
        update["human_feedback"] = human_feedback
    if update:
        graph.update_state(config, update)
    result = graph.invoke(None, config=config)
    return result
