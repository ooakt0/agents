"""
Shared LangGraph state types and pipeline constants.

All node modules import from here — never from each other — to avoid circular imports.
"""

from __future__ import annotations

from typing import Literal, Optional, TypedDict

from langchain_core.messages import BaseMessage

# ---------------------------------------------------------------------------
# Pipeline Sequence
# ---------------------------------------------------------------------------

WORKER_AGENTS = [
    "architect",
    "codeCrafter",
    "codeReviewer",
    "qualityGuard",
    "devOps",
]

# Fixed left-to-right execution order.  tech_lead_gate is the human-in-the-loop
# breakpoint that interrupts for deployment approval before devOps runs.
PIPELINE_SEQUENCE = [
    "architect",
    "codeCrafter",
    "codeReviewer",
    "qualityGuard",
    "tech_lead_gate",
    "devOps",
]

RouteTarget = Literal[
    "architect",
    "codeCrafter",
    "codeReviewer",
    "qualityGuard",
    "tech_lead_gate",
    "devOps",
    "generate_manual_guide",
    "permission_gate",
    "FINISH",
]

# ---------------------------------------------------------------------------
# Shared TypedDicts
# ---------------------------------------------------------------------------


class RefactorProposal(TypedDict):
    file: str          # repo-relative path, forward-slash separated
    description: str   # one-sentence bottleneck description
    task_id: str       # e.g. REFACTOR-3A7F2B


class AgentState(TypedDict):
    messages: list[BaseMessage]
    next_node: str
    # Pipeline-specific fields
    github_url: str
    repo_path: str           # absolute local path after clone
    test_passed: bool
    task_description: str    # human-readable goal forwarded from the MCP tool
    completed_agents: list[str]
    # Permission-gate fields
    pending_refactor_proposal: Optional[RefactorProposal]
    active_subtasks: list[str]   # task_ids approved by the user this run
    # Deployment approval gate fields
    user_approval: Optional[str]          # "Approve" | "Manual" | None
    deployment_guide_path: Optional[str]  # populated when MANUAL_DEPLOY_REQUESTED
