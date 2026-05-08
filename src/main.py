"""
SEagenthub MCP Server — Incremental Interactive Workflow.

The pipeline runs one agent at a time.  After each step the IDE receives a
STEP_COMPLETE response with files_to_create and a continuation_token.  The IDE
writes the files locally, then calls advance_pipeline to trigger the next agent.

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
    version="2.0.0",
    instructions=(
        "SEagenthub is a 6-agent AI engineering framework covering the full SDLC "
        "across all 6 AWS Well-Architected pillars.\n\n"
        "INCREMENTAL WORKFLOW\n"
        "  1. Call techLead — architect runs first.\n"
        "     → STEP_COMPLETE: write files_to_create to disk, note the continuation_token.\n"
        "  2. Call advance_pipeline(continuation_token) to trigger the next agent.\n"
        "     Repeat until status=PIPELINE_COMPLETE.\n"
        "  3. requires_approval=true means confirm with the user before advancing.\n"
        "  4. status=PIPELINE_PAUSED means a decision is required — use a resume tool.\n\n"
        "TOOLS\n"
        "  techLead                    — start a new pipeline run\n"
        "  advance_pipeline            — proceed to the next agent step\n"
        "  resume_refactor_decision    — approve or reject an out-of-scope refactor\n"
        "  resume_deployment_decision  — choose automated deploy or a manual guide\n\n"
        "RESPONSE STATUS VALUES\n"
        "  STEP_COMPLETE          — agent finished; files_to_create is ready to write\n"
        "  PIPELINE_PAUSED        — user decision required\n"
        "  PIPELINE_COMPLETE      — full SDLC done\n"
        "  DEPLOYMENT_GUIDE_READY — manual deployment guide written\n"
    ),
)


@mcp.tool()
def techLead(project_path: str, task_description: str) -> str:
    """Start the 6-agent SDLC pipeline on a local project directory.

    Runs architect first and returns a STEP_COMPLETE response immediately.
    The IDE should write files_to_create to disk, then call advance_pipeline
    with the continuation_token to proceed to the next agent (codeCrafter).

    Shared-state templates (.github/shared/) are injected into the project
    directory if they do not already exist.

    Args:
        project_path:     Absolute local path to the project directory.
        task_description: Plain-English description of the task to accomplish.

    Returns:
        JSON — status=STEP_COMPLETE with continuation_token, files_to_create,
        status_update, requires_approval, completed_tasks, pending_tasks.
    """
    return start_pipeline(project_path, task_description)


@mcp.tool()
def advance_pipeline(continuation_token: str) -> str:
    """Advance the pipeline to the next agent step.

    Call this after writing the files from the previous STEP_COMPLETE response
    to disk.  If requires_approval was true, confirm with the user first.

    Args:
        continuation_token: The token from the previous STEP_COMPLETE response.

    Returns:
        JSON — status=STEP_COMPLETE | PIPELINE_PAUSED | PIPELINE_COMPLETE
        | DEPLOYMENT_GUIDE_READY.
    """
    return advance_step(continuation_token)


@mcp.tool()
def resume_refactor_decision(thread_id: str, decision: str) -> str:
    """Resume a pipeline paused at the refactor permission gate.

    Args:
        thread_id: The continuation_token from the PIPELINE_PAUSED response.
        decision:  'Yes' to approve the refactor, 'No' to skip it.

    Returns:
        JSON — status=STEP_COMPLETE | PIPELINE_PAUSED | PIPELINE_COMPLETE.
    """
    return resume_refactor(thread_id, decision)


@mcp.tool()
def resume_deployment_decision(thread_id: str, decision: str) -> str:
    """Resume a pipeline paused at the deployment approval gate.

    Args:
        thread_id: The continuation_token from the PIPELINE_PAUSED response.
        decision:  'Approve' for automated deployment, 'Manual' for a guide file.

    Returns:
        JSON — status=STEP_COMPLETE | PIPELINE_COMPLETE | DEPLOYMENT_GUIDE_READY.
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
