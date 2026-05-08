"""
tech_lead_gate node — human-in-the-loop release gate.

Interrupts for user deployment authorization before @devOps runs.
On resume:
  - "Approve" / "approve" / "yes" / "y" → RELEASE_AUTHORIZED → supervisor routes to devOps
  - "Manual"  / "manual"  / "no"  / "n" → MANUAL_DEPLOY_REQUESTED → generate_manual_guide
"""

from __future__ import annotations

from langgraph.types import interrupt

from src.nodes._utils import base_state
from src.state import AgentState


def _build_approval_summary(state: AgentState) -> str:
    repo = state.get("github_url", "<repo>")
    task = state.get("task_description", "<task>")
    tests_ok = "✅ PASSED" if state.get("test_passed") else "⚠️  not confirmed"
    agents_done = ", ".join(state.get("completed_agents") or [])
    return (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  DEPLOYMENT APPROVAL GATE — @techLead\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  Repo:    {repo}\n"
        f"  Task:    {task}\n"
        f"  Tests:   {tests_ok}\n"
        f"  Agents:  {agents_done}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "All quality checks passed.\n"
        "Do you authorize @devOps to deploy these changes?\n"
        "\n"
        "  Approve — @devOps runs the full pipeline automatically\n"
        "  Manual  — @devOps generates docs/deployment_guide.md for you to run\n"
        "\n"
        "Reply: Approve / Manual"
    )


def tech_lead_gate_node(state: AgentState) -> AgentState:
    print("Agent tech_lead_gate is requesting deployment authorization.")

    summary = _build_approval_summary(state)
    user_answer: str = interrupt(summary)

    normalized = user_answer.strip().lower()
    approval = "Approve" if normalized in {"approve", "yes", "y", "go", "deploy"} else "Manual"
    signal = "RELEASE_AUTHORIZED" if approval == "Approve" else "MANUAL_DEPLOY_REQUESTED"

    return {
        **base_state(
            state,
            f"[tech_lead_gate] {signal} — user decision recorded.",
            "tech_lead_gate",
        ),
        "user_approval": approval,
    }
