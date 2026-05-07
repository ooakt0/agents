"""
AgentHub MCP Server — stateless tool server wrapping the 6-agent LangGraph pipeline.

Usage
-----
  python main.py                          # stdio transport (default for Claude Code)
  python main.py --transport=sse          # SSE transport for VS Code / Cursor

Environment variables
---------------------
  GITHUB_TOKEN            PAT for authenticated git push inside codeCrafter
  DEPLOY_DASHBOARD_URL    POST endpoint for the deployment dashboard (devOps)

No LLM API key is required — the supervisor is fully deterministic.
"""

from __future__ import annotations

import re
import sys
import uuid
from typing import Any

from fastmcp import FastMCP
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from orchestrator import AgentState, build_graph

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
    "seagenthub",
    instructions=(
        "Use execute_software_pipeline to run the full CI/CD lifecycle "
        "(design → implement → review → test → deploy) on a GitHub repository. "
        "If the pipeline pauses for a refactoring decision, use resume_refactor_decision "
        "with the returned thread_id and your Yes/No answer."
    ),
)

# Strict GitHub HTTPS URL pattern — prevents shell injection via URL arg
_GITHUB_URL_RE = re.compile(
    r"^https://github\.com/[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+(?:\.git)?$"
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


def _format_complete(final_state: AgentState, github_repo_url: str) -> str:
    lines = [f"AgentHub pipeline complete for {github_repo_url}", ""]
    for msg in final_state["messages"]:
        role = getattr(msg, "name", None) or msg.__class__.__name__
        lines.append(f"[{role}] {msg.content}")
    subtasks = ", ".join(final_state.get("active_subtasks") or []) or "none"
    lines += [
        "",
        f"Tests passed   : {final_state.get('test_passed', False)}",
        f"Agents run     : {', '.join(final_state.get('completed_agents') or [])}",
        f"Subtasks added : {subtasks}",
    ]
    return "\n".join(lines)


def _github_url_from_state(final_state: AgentState) -> str:
    for msg in final_state.get("messages", []):
        if isinstance(msg, HumanMessage):
            for line in msg.content.splitlines():
                if line.startswith("Repository:"):
                    return line.split(":", 1)[1].strip()
    return ""


# ---------------------------------------------------------------------------
# Tool: execute_software_pipeline
# ---------------------------------------------------------------------------


@mcp.tool()
def execute_software_pipeline(github_repo_url: str, task_description: str) -> str:
    """Run the 6-agent software pipeline on a GitHub repository.

    Executes a deterministic sequence:
      architect → codeCrafter (clone/commit/push) → codeReviewer
      → qualityGuard (pytest) → devOps (deploy API)

    If codeCrafter detects a HIGH-severity performance bottleneck in a file outside
    the current task scope, the pipeline pauses and returns a PIPELINE_PAUSED message
    containing a thread_id. Use resume_refactor_decision to answer and continue.

    Args:
        github_repo_url:  HTTPS URL of a GitHub repository,
                          e.g. https://github.com/owner/repo
        task_description: Plain-English description of what the pipeline should accomplish.

    Returns:
        A pipeline summary string, or a PIPELINE_PAUSED prompt with a thread_id.
    """
    if not _GITHUB_URL_RE.match(github_repo_url):
        return (
            f"Error: Invalid GitHub URL {github_repo_url!r}. "
            "Must match https://github.com/<owner>/<repo>"
        )

    thread_id = uuid.uuid4().hex
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}

    initial_state: AgentState = {
        "messages": [
            HumanMessage(
                content=(
                    f"Repository: {github_repo_url}\n"
                    f"Task: {task_description}\n\n"
                    "Execute the full SDLC: design the architecture, implement "
                    "the necessary code changes, review the code, run all tests, "
                    "and deploy once tests pass."
                )
            )
        ],
        "next_node": "",
        "github_url": github_repo_url,
        "repo_path": "",
        "test_passed": False,
        "task_description": task_description,
        "completed_agents": [],
        "pending_refactor_proposal": None,
        "active_subtasks": [],
    }

    final_state: AgentState = _compiled_graph.invoke(initial_state, config=config)

    question = _pending_interrupt(thread_id, config)
    if question:
        _active_threads[thread_id] = config
        return _format_paused(thread_id, question)

    return _format_complete(final_state, github_repo_url)


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
        # Put config back so the caller can retry with a valid answer
        _active_threads[thread_id] = config
        return "Error: decision must be 'Yes' or 'No'."

    final_state: AgentState = _compiled_graph.invoke(
        Command(resume=decision), config=config
    )

    # The pipeline might pause again if multiple out-of-scope bottlenecks are found
    question = _pending_interrupt(thread_id, config)
    if question:
        _active_threads[thread_id] = config
        return _format_paused(thread_id, question)

    return _format_complete(final_state, _github_url_from_state(final_state))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    transport = "stdio"
    for arg in sys.argv[1:]:
        if arg.startswith("--transport="):
            transport = arg.split("=", 1)[1]
        elif arg == "--transport" and sys.argv.index(arg) + 1 < len(sys.argv):
            transport = sys.argv[sys.argv.index(arg) + 1]

    mcp.run(transport=transport)
