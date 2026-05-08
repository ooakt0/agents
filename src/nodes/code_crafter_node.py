"""
codeCrafter node — clone repo, detect bottlenecks, apply changes, push.

Bottleneck detection runs in two passes:
  1. Parse REFACTOR_PROPOSAL signals from LLM-generated messages (if any).
  2. Static regex scan of out-of-scope source files (always runs as a fallback).

If a proposal is found, the node sets pending_refactor_proposal and returns to
the supervisor without committing — the permission_gate must resolve it first.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from github import Auth, Github

from src.nodes._utils import (
    base_state,
    detect_bottleneck_in_out_of_scope_files,
    parse_proposal_from_messages,
)
from src.state import AgentState


def code_crafter_node(state: AgentState) -> AgentState:
    print("Agent codeCrafter is working.")

    github_url: str = state.get("github_url", "")
    if not github_url:
        return base_state(state, "[codeCrafter] No github_url in state — skipped.", "codeCrafter")

    repo_path = state.get("repo_path") or ""
    if not repo_path:
        tmp = tempfile.mkdtemp(prefix="agenthub_")
        subprocess.run(
            ["git", "clone", "--depth", "1", github_url, tmp],
            check=True,
            timeout=120,
        )
        repo_path = tmp

    # Pass 1: LLM-emitted REFACTOR_PROPOSAL signals
    proposal = parse_proposal_from_messages(state["messages"])

    # Pass 2: static bottleneck scan across out-of-scope files
    if proposal is None:
        proposal = detect_bottleneck_in_out_of_scope_files(
            repo_path, state.get("task_description", "")
        )

    if proposal is not None:
        # Surface proposal — do not commit until the user resolves the gate
        base = base_state(
            state,
            (
                f"[codeCrafter] Out-of-scope bottleneck detected in {proposal['file']}. "
                f"Reason: {proposal['description']}. "
                f"Awaiting permission gate decision before committing."
            ),
            "codeCrafter",
        )
        return {
            **base,
            "repo_path": repo_path,
            "pending_refactor_proposal": proposal,
            # Remove codeCrafter from completed so it re-runs after gate resolution
            "completed_agents": [a for a in base["completed_agents"] if a != "codeCrafter"],
        }

    # No out-of-scope issues — apply changes and push
    marker = Path(repo_path) / ".agenthub_run"
    marker.write_text("orchestrated by AgentHub\n", encoding="utf-8")

    subprocess.run(["git", "add", "-A"], cwd=repo_path, check=True, timeout=30)
    commit_result = subprocess.run(
        ["git", "commit", "-m", "chore: apply AgentHub orchestration changes"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=30,
    )

    push_output = "nothing to commit"
    if commit_result.returncode == 0:
        gh_token = os.environ.get("GITHUB_TOKEN", "")
        if gh_token:
            auth = Auth.Token(gh_token)
            gh = Github(auth=auth)
            _ = gh.get_user().login
            gh.close()
            authed_url = github_url.replace(
                "https://", f"https://x-access-token:{gh_token}@"
            )
            subprocess.run(
                ["git", "remote", "set-url", "origin", authed_url],
                cwd=repo_path,
                check=True,
                timeout=10,
            )
        subprocess.run(
            ["git", "push", "origin", "HEAD"],
            cwd=repo_path,
            check=True,
            timeout=60,
        )
        push_output = "pushed to origin"

    return {
        **base_state(
            state,
            f"[codeCrafter] Clone ✓ | commit: {commit_result.returncode == 0} | push: {push_output}",
            "codeCrafter",
        ),
        "repo_path": repo_path,
    }
