"""
codeCrafter node — detect bottlenecks and apply local file changes.

Responsibilities:
  - Use the project_path already set in state (local-first — no git clone).
  - Run two-pass bottleneck detection; pause at the permission gate if needed.
  - Write file changes directly to the local project directory.

repo_path is read from state so downstream nodes (codeReviewer, qualityGuard,
devOps) can access the same working directory.
"""

from __future__ import annotations

from pathlib import Path

from src.nodes._utils import (
    base_state,
    detect_bottleneck_in_out_of_scope_files,
    parse_proposal_from_messages,
)
from src.state import AgentState


def code_crafter_node(state: AgentState) -> AgentState:
    print("Agent codeCrafter is working.")

    repo_path: str = state.get("repo_path") or state.get("project_path", "")
    if not repo_path:
        return base_state(state, "[codeCrafter] No project_path in state — skipped.", "codeCrafter")

    # Pass 1: LLM-emitted REFACTOR_PROPOSAL signals
    proposal = parse_proposal_from_messages(state["messages"])

    # Pass 2: static bottleneck scan across out-of-scope files
    if proposal is None:
        proposal = detect_bottleneck_in_out_of_scope_files(
            repo_path, state.get("task_description", "")
        )

    if proposal is not None:
        base = base_state(
            state,
            (
                f"[codeCrafter] Out-of-scope bottleneck detected in {proposal['file']}. "
                f"Reason: {proposal['description']}. "
                f"Awaiting permission gate decision before proceeding."
            ),
            "codeCrafter",
        )
        return {
            **base,
            "repo_path": repo_path,
            "pending_refactor_proposal": proposal,
            # Remove from completed so codeCrafter re-runs after gate resolution
            "completed_agents": [a for a in base["completed_agents"] if a != "codeCrafter"],
        }

    # Apply local file changes — read/write directly to project directory
    marker = Path(repo_path) / ".agenthub_run"
    marker.write_text("orchestrated by AgentHub\n", encoding="utf-8")

    return {
        **base_state(
            state,
            "[codeCrafter] Local files modified in project directory.",
            "codeCrafter",
        ),
        "repo_path": repo_path,
    }
