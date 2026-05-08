"""qualityGuard node — run pytest in the cloned repo and record pass/fail."""

from __future__ import annotations

import subprocess
from pathlib import Path

from src.nodes._utils import base_state
from src.state import AgentState


def quality_guard_node(state: AgentState) -> AgentState:
    print("Agent qualityGuard is working.")

    repo_path = state.get("repo_path", "")
    if not repo_path or not Path(repo_path).is_dir():
        return {
            **base_state(
                state,
                "[qualityGuard] No repo_path available — tests skipped.",
                "qualityGuard",
            ),
            "test_passed": False,
        }

    result = subprocess.run(
        ["python", "-m", "pytest", "--tb=short", "-q"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=300,
    )
    test_passed = result.returncode == 0
    summary = (result.stdout + result.stderr).strip().splitlines()
    last_lines = "\n".join(summary[-10:])

    return {
        **base_state(
            state,
            f"[qualityGuard] Tests {'PASSED' if test_passed else 'FAILED'}.\n{last_lines}",
            "qualityGuard",
        ),
        "test_passed": test_passed,
    }
