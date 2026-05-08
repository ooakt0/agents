"""Permission gate node — pauses pipeline for out-of-scope refactor approval."""

from __future__ import annotations

from langgraph.types import interrupt

from src.nodes._utils import append_subtask_to_project_state
from src.state import AgentState, RefactorProposal


def permission_gate_node(state: AgentState) -> AgentState:
    """
    Pause execution via LangGraph interrupt() and ask the user whether to apply an
    out-of-scope refactoring proposal.  Requires a checkpointer compiled into the graph.

    Resume path:
      - "Yes" / "y"  → write sub-task to project_state.md, mark sub-task active
      - "No"  / "n"  → discard proposal, continue pipeline unchanged
    """
    proposal: RefactorProposal = state["pending_refactor_proposal"]  # type: ignore[assignment]

    user_answer: str = interrupt(
        f"I found a performance bottleneck in {proposal['file']}. "
        f"It is outside the current task scope. "
        f"Should I optimize this now? (Yes/No)\n"
        f"Details: {proposal['description']}"
    )

    accepted = user_answer.strip().lower().startswith("y")
    active_subtasks = list(state.get("active_subtasks") or [])

    if accepted:
        append_subtask_to_project_state(state.get("repo_path", ""), proposal)
        active_subtasks.append(proposal["task_id"])

    return {
        **state,
        "pending_refactor_proposal": None,
        "active_subtasks": active_subtasks,
        "next_node": "supervisor",
    }
