"""
SEagenthub MCP Server — Step-and-Wait Interactive Protocol.

The pipeline runs one agent at a time.  After each step the IDE receives a
STEP_COMPLETE response with proposed_changes and a next_agent_instruction.
The IDE MUST write the files to disk, then call advance_pipeline.  If the
files are not on disk when advance_pipeline is called, the server returns
WAITING_FOR_FILES and refuses to proceed.

Session state is persisted in {project_path}/.seahub/session.json so the
TechLead can read it before every agent call and resume where it left off.

Usage
-----
  python src/main.py                                           # stdio (default)
  python src/main.py --transport=sse                          # SSE for VS Code / Cursor
  python src/main.py --transport=streamable-http --port=8080  # Lambda / Docker

Environment variables
---------------------
  PORT  HTTP port override (default 8080); its presence selects streamable-http.
"""
from __future__ import annotations

import os
import sys

from fastmcp import FastMCP

from src.pipeline import advance_step, resume_deployment, resume_refactor, start_pipeline

mcp: FastMCP = FastMCP(
    "SEagenthub",
    version="3.0.0",
    instructions=(
        "SEagenthub is a 6-agent AI engineering framework covering the full SDLC "
        "across all 6 AWS Well-Architected pillars.\n\n"
        "STEP-AND-WAIT PROTOCOL\n"
        "  Every response includes:\n"
        "    proposed_changes       — files the IDE must write to disk\n"
        "    next_agent_instruction — exact instruction to follow after applying files\n"
        "    is_task_complete       — false until all 6 agents have verified their work\n\n"
        "  RULE: The IDE must apply ALL proposed_changes before calling advance_pipeline.\n"
        "  If files are missing, advance_pipeline returns WAITING_FOR_FILES and blocks.\n\n"
        "WORKFLOW\n"
        "  1. Call techLead — architect runs first.\n"
        "     → STEP_COMPLETE: write proposed_changes to disk.\n"
        "     → Follow next_agent_instruction (usually: call advance_pipeline).\n"
        "  2. Call advance_pipeline(continuation_token) to trigger the next agent.\n"
        "     The server verifies all proposed_changes exist on disk before proceeding.\n"
        "     Repeat until is_task_complete=true.\n"
        "  3. requires_approval=true means confirm with the user before advancing.\n"
        "  4. status=PIPELINE_PAUSED means a decision is required — use a resume tool.\n"
        "  5. status=WAITING_FOR_FILES means previous files must be written first.\n\n"
        "STATE PERSISTENCE\n"
        "  Session metadata is written to {project_path}/.seahub/session.json.\n"
        "  The TechLead reads this file before every agent call to resume correctly.\n"
        "  .github/shared/project_context.md tracks completed and pending tasks.\n\n"
        "TOOLS\n"
        "  techLead                    — start a new pipeline run\n"
        "  advance_pipeline            — proceed to the next agent step\n"
        "  resume_refactor_decision    — approve or reject an out-of-scope refactor\n"
        "  resume_deployment_decision  — choose automated deploy or a manual guide\n\n"
        "RESPONSE STATUS VALUES\n"
        "  STEP_COMPLETE          — agent finished; write proposed_changes then advance\n"
        "  WAITING_FOR_FILES      — previous files not on disk; write them and retry\n"
        "  PIPELINE_PAUSED        — user decision required before proceeding\n"
        "  PIPELINE_COMPLETE      — full SDLC done; is_task_complete=true\n"
        "  DEPLOYMENT_GUIDE_READY — manual deployment guide written\n"
    ),
)


@mcp.tool()
def techLead(project_path: str, task_description: str) -> str:
    """Start the 6-agent SDLC pipeline on a local project directory.

    Reads any prior session from {project_path}/.seahub/session.json so the
    TechLead can resume where a previous run left off.  Runs the architect
    agent first and returns a STEP_COMPLETE response immediately.

    The IDE must:
      1. Write all files listed in proposed_changes to disk.
      2. Follow next_agent_instruction (call advance_pipeline when ready).

    Shared-state templates (.github/shared/) are injected into the project
    directory if they do not already exist.

    Args:
        project_path:     Absolute local path to the project directory.
        task_description: Plain-English description of the task to accomplish.

    Returns:
        JSON with fields: status, session_id, continuation_token, current_agent,
        proposed_changes, next_agent_instruction, is_task_complete,
        requires_approval, completed_tasks, pending_tasks, status_update.
    """
    return start_pipeline(project_path, task_description)


@mcp.tool()
def advance_pipeline(continuation_token: str) -> str:
    """Advance the pipeline to the next agent step.

    IMPORTANT: Call this only AFTER writing all files from the previous
    proposed_changes to disk.  If any required file is missing the server
    returns WAITING_FOR_FILES and does NOT advance — write the files and
    call advance_pipeline again.

    The server reads {project_path}/.seahub/session.json and
    .github/shared/project_context.md before invoking the next agent,
    so the agent sees the verified local filesystem state.

    Args:
        continuation_token: The token from the previous STEP_COMPLETE response.

    Returns:
        JSON — status: STEP_COMPLETE | WAITING_FOR_FILES | PIPELINE_PAUSED
        | PIPELINE_COMPLETE | DEPLOYMENT_GUIDE_READY.
        Every response includes proposed_changes, next_agent_instruction,
        and is_task_complete.
    """
    return advance_step(continuation_token)


@mcp.tool()
def resume_refactor_decision(thread_id: str, decision: str) -> str:
    """Resume a pipeline paused at the refactor permission gate.

    Args:
        thread_id: The continuation_token from the PIPELINE_PAUSED response.
        decision:  'Yes' to approve the refactor, 'No' to skip it.

    Returns:
        JSON — status: STEP_COMPLETE | PIPELINE_PAUSED | PIPELINE_COMPLETE.
        Includes proposed_changes, next_agent_instruction, is_task_complete.
    """
    return resume_refactor(thread_id, decision)


@mcp.tool()
def resume_deployment_decision(thread_id: str, decision: str) -> str:
    """Resume a pipeline paused at the deployment approval gate.

    Args:
        thread_id: The continuation_token from the PIPELINE_PAUSED response.
        decision:  'Approve' for automated deployment, 'Manual' for a guide file.

    Returns:
        JSON — status: STEP_COMPLETE | PIPELINE_COMPLETE | DEPLOYMENT_GUIDE_READY.
        Includes proposed_changes, next_agent_instruction, is_task_complete.
    """
    return resume_deployment(thread_id, decision)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point — installed as the ``SEagenthub`` console script."""
    host = "0.0.0.0"
    _port_env = os.environ.get("PORT")
    port = int(_port_env) if _port_env else 8080
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
