"""
AgentHub MCP Server — stateless tool server wrapping the 6-agent LangGraph pipeline.

Usage
-----
  python src/main.py                                        # stdio (default — Claude Code / local)
  python src/main.py --transport=sse                        # SSE for VS Code / Cursor
  python src/main.py --transport=streamable-http --port=8080  # Lambda Web Adapter / Docker

Environment variables
---------------------
  DEPLOY_DASHBOARD_URL    POST endpoint for the deployment dashboard (devOps)
  PORT                    HTTP port override (default: 8080); used by Lambda Web Adapter

No LLM API key is required — the supervisor is fully deterministic.
"""

from __future__ import annotations

import os
import sys
import uuid
from typing import Any

from fastmcp import FastMCP
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from src.orchestrator import AgentState, build_graph, inject_shared_templates

# ---------------------------------------------------------------------------
# Graph compiled with a checkpointer (required for interrupt / human-in-the-loop)
# ---------------------------------------------------------------------------

_checkpointer = MemorySaver()
_compiled_graph = build_graph().compile(checkpointer=_checkpointer)

# thread_id → LangGraph config for in-flight interrupted pipelines
_active_threads: dict[str, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp: FastMCP = FastMCP(
    "SEagenthub",
    version="1.0.0",
    website_url="https://github.com/ooakt0/seagenthub",
    instructions=(
        "SEagenthub is a 6-agent AI engineering framework that runs the full SDLC pipeline "
        "on any local project directory, covering all 6 pillars of the AWS Well-Architected Framework.\n\n"
        "AGENTS\n"
        "  @architect    — service boundaries, CDK boilerplate, security groups, cost estimation, ADRs\n"
        "  @codeCrafter  — TypeScript/Python/Java implementation, resilience patterns, performance optimisation\n"
        "  @codeReviewer — architectural alignment, breaking-change detection, security surface analysis\n"
        "  @qualityGuard — unit/integration/load tests, chaos simulation, penetration scan\n"
        "  @devOps       — CI/CD pipeline, blue/green deployment, CloudWatch verification, rollback\n\n"
        "TOOLS\n"
        "  techLead                    — start a new pipeline run on a local project directory\n"
        "  resume_refactor_decision    — approve or reject a proposed out-of-scope refactor\n"
        "  resume_deployment_decision  — approve automated deploy or request a manual guide\n\n"
        "HUMAN-IN-THE-LOOP GATES\n"
        "  1. Refactor gate — approve/reject any out-of-scope refactoring proposals\n"
        "  2. Deploy gate — choose automated deployment or receive a manual deployment guide\n\n"
        "OPTIONAL ENV VARS\n"
        "  DEPLOY_DASHBOARD_URL  — POST endpoint for deployment status webhooks\n\n"
        "SOURCE  https://github.com/ooakt0/seagenthub\n"
        "LICENSE MIT"
    ),
)







# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pending_interrupt(thread_id: str, config: dict[str, Any]) -> str | None:
    """
    Return the interrupt question string if the graph is paused at a permission gate,
    or None if the graph has finished running.
    """
    snapshot = _compiled_graph.get_state(config)
    if not snapshot.next:
        return None
    for task in snapshot.tasks:
        for intr in task.interrupts:
            return str(intr.value)
    return None


def _format_paused(thread_id: str, question: str) -> str:
    return (
        f"PIPELINE_PAUSED — thread_id: {thread_id}\n\n"
        f"{question}\n\n"
        f"Respond with:\n"
        f"  resume_refactor_decision(thread_id='{thread_id}', decision='Yes')\n"
        f"  resume_refactor_decision(thread_id='{thread_id}', decision='No')"
    )


def _format_complete(final_state: AgentState, project_path: str) -> str:
    sections: list[str] = [f"# AgentHub — {project_path}"]

    # Artifacts first: diffs/files the IDE needs to apply changes
    artifacts = final_state.get("artifacts") or []
    if artifacts:
        sections.append("## Changes\n\n" + "\n\n".join(artifacts))

    # One final status line per agent — walk messages newest-first, deduplicate by name
    seen: set[str] = set()
    agent_lines: list[str] = []
    for msg in reversed(final_state["messages"]):
        name = getattr(msg, "name", None)
        if name and name not in seen:
            seen.add(name)
            agent_lines.insert(0, f"  {name}: {msg.content.strip()}")
    if agent_lines:
        sections.append("## Agent results\n\n" + "\n".join(agent_lines))

    subtasks = ", ".join(final_state.get("active_subtasks") or []) or "none"
    sections.append(
        "## Summary\n\n"
        f"Tests passed : {final_state.get('test_passed', False)}\n"
        f"Agents run   : {', '.join(final_state.get('completed_agents') or [])}\n"
        f"Subtasks     : {subtasks}"
    )
    return "\n\n".join(sections)


def _project_path_from_state(final_state: AgentState) -> str:
    return final_state.get("project_path") or ""


# ---------------------------------------------------------------------------
# Tool: techLead
# ---------------------------------------------------------------------------


@mcp.tool()
def techLead(project_path: str, task_description: str) -> str:
    """Run the 6-agent software pipeline on a local project directory.

    Executes a deterministic sequence:
      architect → codeCrafter (modify files) → codeReviewer → qualityGuard
      → tech_lead_gate (deploy approval) → devOps

    Before the pipeline starts, it injects canonical shared-state templates
    (.github/shared/) into the project directory if they do not already exist,
    giving every agent a structured project_context.md, project_state.md,
    standards.md, and architecture_log.md to work with.

    If codeCrafter detects a HIGH-severity performance bottleneck in a file outside
    the current task scope, the pipeline pauses and returns a PIPELINE_PAUSED message
    containing a thread_id.  Use resume_refactor_decision to answer and continue.

    Args:
        project_path:     The local absolute path to the project directory where
                          the agents should work.
        task_description: Plain-English description of what the pipeline should accomplish.

    Returns:
        A pipeline summary string, or a PIPELINE_PAUSED prompt with a thread_id.
    """
    thread_id = uuid.uuid4().hex

    # Inject shared templates so agents have structured working context immediately
    injected = inject_shared_templates(project_path)
    if injected:
        print(f"[SEagenthub] Injected shared templates: {', '.join(injected)}")

    initial_state: AgentState = {
        "messages": [
            HumanMessage(
                content=(
                    f"Project path: {project_path}\n"
                    f"Task: {task_description}\n\n"
                    "Execute the full SDLC: design the architecture, implement "
                    "the necessary code changes, review the code, run all tests, "
                    "and deploy once tests pass."
                )
            )
        ],
        "next_node": "",
        "project_path": project_path,
        "repo_path": project_path,
        "test_passed": False,
        "task_description": task_description,
        "completed_agents": [],
        "artifacts": [],
        "pending_refactor_proposal": None,
        "active_subtasks": [],
        "user_approval": None,
        "deployment_guide_path": None,
    }

    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    final_state: AgentState = _compiled_graph.invoke(initial_state, config=config)

    question = _pending_interrupt(thread_id, config)
    if question:
        _active_threads[thread_id] = config
        return _format_paused(thread_id, question)

    return _format_complete(final_state, project_path)


# ---------------------------------------------------------------------------
# Tool: resume_refactor_decision
# ---------------------------------------------------------------------------


@mcp.tool()
def resume_refactor_decision(thread_id: str, decision: str) -> str:
    """Resume a paused pipeline with a Yes or No decision on a refactoring proposal.

    When execute_software_pipeline returns PIPELINE_PAUSED, call this tool with the
    thread_id from that message and your decision.

    Args:
        thread_id: The thread_id from the PIPELINE_PAUSED message.
        decision:  'Yes' to approve — the file is added as an active sub-task in
                   project_state.md and codeCrafter will refactor it before continuing.
                   'No' to skip — the pipeline continues without touching the flagged file.

    Returns:
        Pipeline completion summary, or another PIPELINE_PAUSED if additional proposals
        are found during the resumed run.
    """
    config = _active_threads.pop(thread_id, None)
    if config is None:
        return (
            f"Error: No paused pipeline found for thread_id={thread_id!r}. "
            "It may have already been resumed or the server was restarted."
        )

    normalized = decision.strip().lower()
    if normalized not in {"yes", "no", "y", "n"}:
        _active_threads[thread_id] = config
        return "Error: decision must be 'Yes' or 'No'."

    final_state: AgentState = _compiled_graph.invoke(
        Command(resume=decision), config=config
    )

    question = _pending_interrupt(thread_id, config)
    if question:
        _active_threads[thread_id] = config
        return _format_paused(thread_id, question)

    return _format_complete(final_state, _project_path_from_state(final_state))


# ---------------------------------------------------------------------------
# Tool: resume_deployment_decision
# ---------------------------------------------------------------------------


@mcp.tool()
def resume_deployment_decision(thread_id: str, decision: str) -> str:
    """Resume a paused pipeline at the deployment approval gate.

    When execute_software_pipeline reaches the tech_lead_gate (after all quality
    checks pass), the pipeline pauses and asks for your explicit authorization
    before @devOps touches any infrastructure.

    Args:
        thread_id: The thread_id from the PIPELINE_PAUSED message.
        decision:  'Approve' — @devOps runs the full automated deployment pipeline.
                   'Manual'  — @devOps generates docs/deployment_guide.md with exact
                               commands for you to execute at your own pace.  No
                               automated deployment occurs.

    Returns:
        Pipeline completion summary (auto-deploy) or the path to the generated
        deployment guide (manual path).
    """
    config = _active_threads.pop(thread_id, None)
    if config is None:
        return (
            f"Error: No paused pipeline found for thread_id={thread_id!r}. "
            "It may have already been resumed or the server was restarted."
        )

    normalized = decision.strip().lower()
    if normalized not in {"approve", "manual", "yes", "no", "y", "n"}:
        _active_threads[thread_id] = config
        return "Error: decision must be 'Approve' or 'Manual'."

    final_state: AgentState = _compiled_graph.invoke(
        Command(resume=decision), config=config
    )

    question = _pending_interrupt(thread_id, config)
    if question:
        _active_threads[thread_id] = config
        return _format_paused(thread_id, question)

    guide_path = final_state.get("deployment_guide_path")
    if guide_path:
        return (
            f"DEPLOYMENT_GUIDE_READY\n\n"
            f"Manual deployment guide written to: {guide_path}\n\n"
            f"Open the file and follow the step-by-step instructions. "
            f"Rollback commands are included at the end."
        )

    return _format_complete(final_state, _project_path_from_state(final_state))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point — installed as the ``SEagenthub`` console script."""
    host = "0.0.0.0"
    _port_env = os.environ.get("PORT")
    port = int(_port_env) if _port_env else 8080
    # Lambda Web Adapter sets PORT; its presence signals HTTP transport is required
    transport = "streamable-http" if _port_env else "stdio"

    for arg in sys.argv[1:]:
        if arg.startswith("--transport="):
            transport = arg.split("=", 1)[1]
        elif arg.startswith("--port="):
            port = int(arg.split("=", 1)[1])
        elif arg.startswith("--host="):
            host = arg.split("=", 1)[1]

    if transport in ("streamable-http", "sse"):
        mcp.run(transport=transport, host=host, port=port, stateless_http=True)
    else:
        mcp.run(transport=transport)


if __name__ == "__main__":
    main()
