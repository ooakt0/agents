"""
Multi-Agent Orchestration — LangGraph graph definition.

Assembles the 9-node pipeline from individual node modules and provides
build_graph() for the MCP server and a standalone __main__ entry point.

Template Injection
------------------
When a target repository is processed by codeCrafter and does NOT yet have a
.github/shared/ directory, this module copies the canonical shared-state
templates from  <project-root>/templates/  into the cloned repo.  This ensures
every repository that passes through AgentHub gets a correctly structured
project_context.md, project_state.md, standards.md, and architecture_log.md
without requiring the operator to copy files manually.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph

from src.nodes.architect_node import architect_node
from src.nodes.code_crafter_node import code_crafter_node
from src.nodes.code_reviewer_node import code_reviewer_node
from src.nodes.dev_ops_node import dev_ops_node
from src.nodes.devops_manual_guide_node import devops_manual_guide_node
from src.nodes.permission_gate_node import permission_gate_node
from src.nodes.quality_guard_node import quality_guard_node
from src.nodes.supervisor_node import route_supervisor, supervisor_node
from src.nodes.tech_lead_gate_node import tech_lead_gate_node
from src.state import AgentState, WORKER_AGENTS
# ---------------------------------------------------------------------------
# Template directory — resolved relative to this file's package root
# ---------------------------------------------------------------------------
_TEMPLATES_DIR: Path = Path(__file__).parent.parent / "templates"

# ---------------------------------------------------------------------------
# Template Injection
# ---------------------------------------------------------------------------

def inject_shared_templates(repo_path: str) -> list[str]:
    """
    Copy .github/shared/ template files into the target repo if that directory
    does not already exist.

    Returns a list of the file names that were copied, or an empty list if the
    directory already existed (no injection performed).
    """
    if not repo_path or not _TEMPLATES_DIR.is_dir():
        return []

    target_shared = Path(repo_path).resolve() / ".github" / "shared"
    if target_shared.exists():
        return []   # repo already has shared state — do not overwrite

    target_shared.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for template_file in _TEMPLATES_DIR.iterdir():
        if template_file.is_file():
            shutil.copy2(template_file, target_shared / template_file.name)
            copied.append(template_file.name)

    return copied


# ---------------------------------------------------------------------------
# Graph Assembly
# ---------------------------------------------------------------------------


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("architect", architect_node)
    graph.add_node("codeCrafter", code_crafter_node)
    graph.add_node("codeReviewer", code_reviewer_node)
    graph.add_node("qualityGuard", quality_guard_node)
    graph.add_node("tech_lead_gate", tech_lead_gate_node)
    graph.add_node("devOps", dev_ops_node)
    graph.add_node("generate_manual_guide", devops_manual_guide_node)
    graph.add_node("permission_gate", permission_gate_node)

    graph.set_entry_point("supervisor")

    graph.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "architect": "architect",
            "codeCrafter": "codeCrafter",
            "codeReviewer": "codeReviewer",
            "qualityGuard": "qualityGuard",
            "tech_lead_gate": "tech_lead_gate",
            "devOps": "devOps",
            "generate_manual_guide": "generate_manual_guide",
            "permission_gate": "permission_gate",
            "FINISH": END,
        },
    )

    for agent_name in [*WORKER_AGENTS, "tech_lead_gate", "generate_manual_guide"]:
        graph.add_edge(agent_name, "supervisor")

    graph.add_edge("permission_gate", "supervisor")

    return graph


# ---------------------------------------------------------------------------
# Entry Point (standalone smoke test)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Compiled here (not at module level) so importing orchestrator from main.py
    # doesn't trigger a second, unused graph compilation on every cold start.
    compiled_graph = build_graph().compile()
    initial_state: AgentState = {
        "messages": [
            HumanMessage(
                content=(
                    "We need to design and deploy a new serverless API. "
                    "Start with architecture, then implement, review, test, and deploy."
                )
            )
        ],
        "next_node": "",
        "project_path": "",
        "repo_path": "",
        "test_passed": False,
        "task_description": "Design and deploy a new serverless API.",
        "completed_agents": [],
        "artifacts": [],
        "file_operations": [],
        "pending_refactor_proposal": None,
        "active_subtasks": [],
        "user_approval": None,
        "deployment_guide_path": None,
    }

    print("=== Starting multi-agent orchestration ===\n")
    for step in compiled_graph.stream(initial_state):
        node_name, node_state = next(iter(step.items()))
        print(f"[{node_name}] next_node={node_state.get('next_node', '')}")

    print("\n=== Orchestration complete ===")
