"""Architect node — generates an ADR entry and emits it as a FileOperation."""

from __future__ import annotations

from datetime import date

from src.nodes._utils import base_state
from src.state import AgentState, FileOperation


def architect_node(state: AgentState) -> AgentState:
    print("Agent architect is working.")

    task = state.get("task_description", "new feature")
    project_path = state.get("project_path", "")
    today = date.today().strftime("%Y-%m-%d")

    adr_entry = (
        f"\n---\n\n"
        f"## ADR-{today}: {task[:80]}\n\n"
        f"**Status:** Accepted  \n"
        f"**Date:** {today}  \n\n"
        f"**Context:**  \n"
        f"{task}\n\n"
        f"**Decision:**  \n"
        f"Implement the required changes directly in "
        f"`{project_path or 'the project directory'}` using the skill chain defined "
        f"in `prompts/skills/`. No remote repository operations.\n\n"
        f"**Consequences:**  \n"
        f"- @codeCrafter applies code changes to the local filesystem.\n"
        f"- @codeReviewer validates alignment before tests run.\n"
        f"- @qualityGuard must pass before @devOps triggers deployment.\n"
    )

    file_ops: list[FileOperation] = list(state.get("file_operations") or [])
    file_ops.append({
        "path": ".github/shared/architecture_log.md",
        "content": adr_entry,
        "action": "update",
    })

    return {
        **base_state(
            state,
            "[architect] ADR generated and queued for .github/shared/architecture_log.md.",
            "architect",
        ),
        "file_operations": file_ops,
    }
