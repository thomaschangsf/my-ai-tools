"""CLI entry points for uv run check, uv run tests, uv run jupyter."""

import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from shutil import which

OLLAMA_HOST = "http://localhost:11434"

# Common paths when "ollama" isn't on PATH (e.g. under uv run)
_OLLAMA_PATHS = [
    "/usr/local/bin/ollama",
    "/opt/homebrew/bin/ollama",
    "/Applications/Ollama.app/Contents/Resources/ollama",
]


def _ollama_binary() -> str | None:
    """Return path to ollama executable, or None if not found."""
    cmd = which("ollama")
    if cmd:
        return cmd
    for path in _OLLAMA_PATHS:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def _ollama_is_running() -> bool:
    try:
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as _:
            return True
    except (urllib.error.URLError, OSError):
        return False


def ollama_serve() -> None:
    """Start Ollama locally if not already running."""
    if _ollama_is_running():
        print("Ollama is already running at", OLLAMA_HOST)
        return
    binary = _ollama_binary()
    if not binary:
        print("Ollama not found. Install from https://ollama.com", file=sys.stderr)
        print("  macOS: install the app; it may add /usr/local/bin/ollama to PATH.", file=sys.stderr)
        sys.exit(1)
    try:
        subprocess.Popen(
            [binary, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as e:
        print(f"Failed to start Ollama: {e}", file=sys.stderr)
        sys.exit(1)
    print("Starting Ollama...")
    for _ in range(15):
        time.sleep(1)
        if _ollama_is_running():
            print("Ollama is running at", OLLAMA_HOST)
            return
    print(f"Ollama started in background; it may take a moment to be ready. Check {OLLAMA_HOST}")


def _check_mcp_bridge() -> bool:
    """Verify MCP bridge loads and exposes the expected tools. Returns True if OK."""
    code = """
import sys
import os
root = os.getcwd()
if root not in sys.path:
    sys.path.insert(0, root)
import mcp_bridge
assert mcp_bridge.mcp.name == "GlobalAgents"

# Verify all expected MCP tools are registered
from my_ai_tools.agents.hello_world import run_hello
assert run_hello("x") == "Global Agent Response: x"

expected_tools = [
    "run_hello",
    "plan_auto_start",
    "plan_auto_resume",
    "plan_interactive_start",
    "plan_interactive_resume",
    "pr_review_start",
    "pr_review_resume",
]
print("MCP tools registered:")
for name in expected_tools:
    found = hasattr(mcp_bridge, name)
    print(f"  {name}: {'OK' if found else 'MISSING'}")
    assert found, f"MCP tool {name!r} not found in mcp_bridge"

print("MCP bridge OK")
"""
    r = subprocess.call([sys.executable, "-c", code])
    return r == 0


def check() -> None:
    """Run ruff, MCP bridge check, and verify_agents (hello_world + cursor + ollama)."""
    root = os.getcwd()
    steps = [
        ("Ruff", [sys.executable, "-m", "ruff", "check", "."]),
        ("MCP bridge", None),  # run via _check_mcp_bridge
        ("verify_agents", [sys.executable, os.path.join(root, "scripts", "verify_agents.py")]),
    ]
    for name, cmd in steps:
        if name == "MCP bridge":
            if not _check_mcp_bridge():
                print(f"check failed: {name}", file=sys.stderr)
                sys.exit(1)
        else:
            if subprocess.call(cmd, cwd=root) != 0:
                print(f"check failed: {name}", file=sys.stderr)
                sys.exit(1)
    print("All checks passed.")


def tests() -> None:
    """Run pytest."""
    sys.exit(subprocess.call([sys.executable, "-m", "pytest"], cwd=None))


def jupyter() -> None:
    """Start Jupyter notebook server."""
    sys.exit(
        subprocess.call(
            [sys.executable, "-m", "jupyter", "notebook"],
            cwd=None,
        )
    )


def mcp_bridge() -> None:
    """Start the MCP bridge server (mcp_bridge.py)."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bridge = os.path.join(root, "mcp_bridge.py")
    sys.exit(subprocess.call([sys.executable, bridge]))
