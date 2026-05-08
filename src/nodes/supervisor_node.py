"""Supervisor node — deterministic router, no LLM required."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.state import AgentState, PIPELINE_SEQUENCE, RouteTarget

if TYPE_CHECKING:
    pass


def supervisor_node(state: AgentState) -> AgentState:
    """
    Route to the permission gate if a refactor proposal is pending.
    Route to the manual guide if the user declined automated deployment.
    Otherwise advance to the next agent in PIPELINE_SEQUENCE, or FINISH.
    """
    if state.get("pending_refactor_proposal"):
        return {**state, "next_node": "permission_gate"}

    completed: list[str] = state.get("completed_agents") or []

    # Manual-deploy path: tech_lead_gate resolved to "Manual" — skip devOps entirely.
    if state.get("user_approval") == "Manual" and "generate_manual_guide" not in completed:
        return {**state, "next_node": "generate_manual_guide"}

    for agent_name in PIPELINE_SEQUENCE:
        if agent_name not in completed:
            return {**state, "next_node": agent_name}

    return {**state, "next_node": "FINISH"}


def route_supervisor(state: AgentState) -> RouteTarget:
    """Conditional-edge router: reads next_node set by the supervisor."""
    return state["next_node"]  # type: ignore[return-value]
