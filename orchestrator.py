"""
Multi-Agent Orchestration System using LangGraph Supervisor/Manager pattern.

Agents: architect, codeCrafter, codeReviewer, qualityGuard, devOps, techLead (supervisor)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Literal, Optional, TypedDict

from github import Auth, Github
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

# ---------------------------------------------------------------------------
# Shared State
# ---------------------------------------------------------------------------

WORKER_AGENTS = [
    "architect",
    "codeCrafter",
    "codeReviewer",
    "qualityGuard",
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

# Fixed execution order — supervisor walks this list left-to-right.
# tech_lead_gate is a human-in-the-loop breakpoint: it interrupts for deployment
# approval before devOps runs. devOps is never reached without RELEASE_AUTHORIZED.
PIPELINE_SEQUENCE = [
    "architect",
    "codeCrafter",
    "codeReviewer",
    "qualityGuard",
    "tech_lead_gate",
    "devOps",
]


class RefactorProposal(TypedDict):
    file: str         # repo-relative path, forward-slash separated
    description: str  # one-sentence bottleneck description
    task_id: str      # e.g. REFACTOR-3A7F2B


class AgentState(TypedDict):
    messages: list[BaseMessage]
    next_node: str
    # Pipeline-specific fields
    github_url: str
    repo_path: str          # absolute local path after clone
    test_passed: bool
    task_description: str   # human-readable goal forwarded from the MCP tool
    completed_agents: list[str]
    # Permission-gate fields
    pending_refactor_proposal: Optional[RefactorProposal]
    active_subtasks: list[str]  # task_ids approved by the user this run
    # Deployment approval gate fields
    user_approval: Optional[str]          # "Approve" | "Manual" | None
    deployment_guide_path: Optional[str]  # populated when MANUAL_DEPLOY_REQUESTED


# ---------------------------------------------------------------------------
# Bottleneck Detection
# ---------------------------------------------------------------------------

# Matches "REFACTOR_PROPOSAL: path/to/file.ts | description text"
_PROPOSAL_RE = re.compile(
    r"REFACTOR_PROPOSAL:\s*(.+?)\s*\|\s*(.+)",
    re.MULTILINE,
)

# Static patterns applied to out-of-scope source files
_BOTTLENECK_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"for\b.+?:\n(?:[ \t]+.+\n)*?[ \t]+await\s+", re.MULTILINE),
        "Async call inside a for-loop (N+1 query pattern)",
    ),
    (
        re.compile(r"\.scan\s*\(", re.IGNORECASE),
        "DynamoDB .scan() — replace with .query() + correct key design",
    ),
    (
        re.compile(r"\bfind_all\s*\(\s*\)", re.IGNORECASE),
        "Unbounded find_all() — missing pagination or LIMIT",
    ),
    (
        re.compile(r"SELECT\s+\*\s+FROM\b", re.IGNORECASE),
        "SELECT * — select only required columns",
    ),
    (
        re.compile(r"while\s+True\s*:.*\n(?:[ \t]+.+\n){10,}", re.MULTILINE),
        "Potentially unbounded while-True loop accumulating results in memory",
    ),
]

_SOURCE_EXTENSIONS: frozenset[str] = frozenset({".py", ".ts", ".js", ".tsx", ".jsx"})

_SKIP_DIRS: frozenset[str] = frozenset({".git", "node_modules", "__pycache__", ".venv", "dist"})


def _in_scope_keywords(task_description: str) -> set[str]:
    """Lowercase, length > 3 tokens from the task description used for scope matching."""
    return {w for w in re.findall(r"[\w/.\-]+", task_description.lower()) if len(w) > 3}


def _detect_bottleneck_in_out_of_scope_files(
    repo_path: str,
    task_description: str,
) -> Optional[RefactorProposal]:
    """
    Scan source files unrelated to the current task for known HIGH-severity bottleneck
    patterns. Returns the first proposal found, or None.
    """
    root = Path(repo_path)
    keywords = _in_scope_keywords(task_description)

    for file_path in root.rglob("*"):
        if file_path.suffix not in _SOURCE_EXTENSIONS:
            continue
        if any(part in _SKIP_DIRS for part in file_path.parts):
            continue

        rel = file_path.relative_to(root)
        rel_str = str(rel).replace("\\", "/").lower()

        # Skip files whose path contains a keyword from the task (heuristic for in-scope)
        if any(kw in rel_str for kw in keywords):
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        for pattern, description in _BOTTLENECK_PATTERNS:
            if pattern.search(content):
                return RefactorProposal(
                    file=str(rel).replace("\\", "/"),
                    description=description,
                    task_id=f"REFACTOR-{uuid.uuid4().hex[:6].upper()}",
                )

    return None


def _parse_proposal_from_messages(messages: list[BaseMessage]) -> Optional[RefactorProposal]:
    """
    Extract a REFACTOR_PROPOSAL emitted by the LLM following refactoring_refinement.md.
    Walks messages in reverse so the most recent proposal wins.
    """
    for msg in reversed(messages):
        text = msg.content if isinstance(msg.content, str) else ""
        match = _PROPOSAL_RE.search(text)
        if match:
            return RefactorProposal(
                file=match.group(1).strip(),
                description=match.group(2).strip(),
                task_id=f"REFACTOR-{uuid.uuid4().hex[:6].upper()}",
            )
    return None


# ---------------------------------------------------------------------------
# project_state.md Writer
# ---------------------------------------------------------------------------


def _append_subtask_to_project_state(repo_path: str, proposal: RefactorProposal) -> None:
    """Write an approved REFACTOR_PROPOSAL as an active sub-task in project_state.md."""
    if not repo_path:
        return
    project_state_path = Path(repo_path) / ".github" / "shared" / "project_state.md"
    if not project_state_path.exists():
        return
    entry = (
        f"\n### Sub-task: {proposal['task_id']}\n"
        f"**Status:** 🏗️ ACTIVE\n"
        f"**File:** `{proposal['file']}`\n"
        f"**Description:** {proposal['description']}\n"
        f"**Origin:** Approved via REFACTOR_PROPOSAL permission gate\n"
    )
    with project_state_path.open("a", encoding="utf-8") as fh:
        fh.write(entry)


# ---------------------------------------------------------------------------
# Supervisor Node  (deterministic — no LLM required)
# ---------------------------------------------------------------------------


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


def _route_supervisor(state: AgentState) -> RouteTarget:
    """Conditional-edge router: reads next_node set by the supervisor."""
    return state["next_node"]  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Permission Gate Node
# ---------------------------------------------------------------------------


def permission_gate_node(state: AgentState) -> AgentState:
    """
    Pause execution via LangGraph interrupt() and ask the user whether to apply an
    out-of-scope refactoring proposal. Requires a checkpointer to be compiled into the graph.

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
        _append_subtask_to_project_state(state.get("repo_path", ""), proposal)
        active_subtasks.append(proposal["task_id"])

    return {
        **state,
        "pending_refactor_proposal": None,
        "active_subtasks": active_subtasks,
        "next_node": "supervisor",
    }


# ---------------------------------------------------------------------------
# Worker Agent Nodes
# ---------------------------------------------------------------------------

def _base_state(state: AgentState, content: str, name: str) -> AgentState:
    """Return a new state dict with one appended AIMessage, next_node reset, and agent marked done."""
    completed = list(state.get("completed_agents") or [])
    if name not in completed:
        completed.append(name)
    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=content, name=name)],
        "next_node": "supervisor",
        "completed_agents": completed,
    }


def _make_worker(name: str):
    """Factory for agents that are still placeholder (no live I/O)."""

    def worker(state: AgentState) -> AgentState:
        print(f"Agent {name} is working.")
        return _base_state(state, f"[{name}] Task processed.", name)

    worker.__name__ = f"{name}_node"
    return worker


architect_node = _make_worker("architect")
code_reviewer_node = _make_worker("codeReviewer")


def code_crafter_node(state: AgentState) -> AgentState:
    """
    Clone the repo, scan for out-of-scope bottlenecks, apply changes, stage and push.

    Bottleneck detection runs in two passes:
      1. Parse REFACTOR_PROPOSAL signals from LLM-generated messages (if present).
      2. Static regex scan of out-of-scope source files (always runs as a fallback).

    If a proposal is found, the node sets pending_refactor_proposal and returns control
    to the supervisor without committing — the permission gate must resolve it first.
    """
    print("Agent codeCrafter is working.")

    github_url: str = state.get("github_url", "")
    if not github_url:
        return _base_state(state, "[codeCrafter] No github_url in state — skipped.", "codeCrafter")

    repo_path = state.get("repo_path") or ""
    if not repo_path:
        tmp = tempfile.mkdtemp(prefix="agenthub_")
        subprocess.run(["git", "clone", "--depth", "1", github_url, tmp], check=True, timeout=120)
        repo_path = tmp

    # Pass 1: look for LLM-emitted REFACTOR_PROPOSAL signals
    proposal = _parse_proposal_from_messages(state["messages"])

    # Pass 2: static bottleneck scan across out-of-scope files
    if proposal is None:
        proposal = _detect_bottleneck_in_out_of_scope_files(
            repo_path, state.get("task_description", "")
        )

    if proposal is not None:
        # Surface proposal — do not commit until user resolves the gate
        base = _base_state(
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
            authed_url = github_url.replace("https://", f"https://x-access-token:{gh_token}@")
            subprocess.run(
                ["git", "remote", "set-url", "origin", authed_url],
                cwd=repo_path,
                check=True,
                timeout=10,
            )
        subprocess.run(["git", "push", "origin", "HEAD"], cwd=repo_path, check=True, timeout=60)
        push_output = "pushed to origin"

    return {
        **_base_state(
            state,
            f"[codeCrafter] Clone ✓ | commit: {commit_result.returncode == 0} | push: {push_output}",
            "codeCrafter",
        ),
        "repo_path": repo_path,
    }


def quality_guard_node(state: AgentState) -> AgentState:
    """Run the test suite in repo_path and record pass/fail in state."""
    print("Agent qualityGuard is working.")

    repo_path = state.get("repo_path", "")
    if not repo_path or not Path(repo_path).is_dir():
        return {
            **_base_state(state, "[qualityGuard] No repo_path available — tests skipped.", "qualityGuard"),
            "test_passed": False,
        }

    result = subprocess.run(
        ["python", "-m", "pytest", "--tb=short", "-q"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=300,
    )
    test_passed = result.returncode == 0
    summary = (result.stdout + result.stderr).strip().splitlines()
    last_lines = "\n".join(summary[-10:])

    return {
        **_base_state(
            state,
            f"[qualityGuard] Tests {'PASSED' if test_passed else 'FAILED'}.\n{last_lines}",
            "qualityGuard",
        ),
        "test_passed": test_passed,
    }


def dev_ops_node(state: AgentState) -> AgentState:
    """Call the deployment dashboard API once tests pass."""
    print("Agent devOps is working.")

    if not state.get("test_passed", False):
        return _base_state(
            state,
            "[devOps] Deployment skipped — tests did not pass.",
            "devOps",
        )

    dashboard_url = os.environ.get("DEPLOY_DASHBOARD_URL", "")
    if not dashboard_url:
        return _base_state(
            state,
            "[devOps] DEPLOY_DASHBOARD_URL not set — deployment skipped.",
            "devOps",
        )

    payload = json.dumps(
        {"repo": state.get("github_url", ""), "status": "ready", "triggered_by": "AgentHub"}
    ).encode("utf-8")

    req = urllib.request.Request(
        dashboard_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            body = resp.read().decode("utf-8", errors="replace")
        deploy_status = f"HTTP {resp.status} — {body[:200]}"
    except urllib.error.URLError as exc:
        deploy_status = f"ERROR: {exc}"

    return _base_state(
        state,
        f"[devOps] Deployment triggered. {deploy_status}",
        "devOps",
    )


# ---------------------------------------------------------------------------
# Deployment Approval Gate  (@techLead — human-in-the-loop)
# ---------------------------------------------------------------------------


def _build_approval_summary(state: AgentState) -> str:
    """Construct the approval prompt shown to the user at the release gate."""
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
    """
    Human-in-the-loop release gate. Interrupts for user approval before @devOps runs.

    On resume:
      - "Approve" / "approve" / "yes" / "y" → RELEASE_AUTHORIZED → supervisor routes to devOps
      - "Manual" / "manual" / "no" / "n"    → MANUAL_DEPLOY_REQUESTED → supervisor routes to
        generate_manual_guide; devOps is never entered
    """
    print("Agent tech_lead_gate is requesting deployment authorization.")

    summary = _build_approval_summary(state)
    user_answer: str = interrupt(summary)

    normalized = user_answer.strip().lower()
    approval = "Approve" if normalized in {"approve", "yes", "y", "go", "deploy"} else "Manual"
    signal = "RELEASE_AUTHORIZED" if approval == "Approve" else "MANUAL_DEPLOY_REQUESTED"

    return {
        **_base_state(
            state,
            f"[tech_lead_gate] {signal} — user decision recorded.",
            "tech_lead_gate",
        ),
        "user_approval": approval,
    }


# ---------------------------------------------------------------------------
# Manual Deployment Guide Generator  (@devOps — MANUAL_DEPLOY_REQUESTED path)
# ---------------------------------------------------------------------------


def devops_manual_guide_node(state: AgentState) -> AgentState:
    """
    Generate docs/deployment_guide.md with concrete, copy-pasteable commands
    derived from the current task context. Activated when user selects Manual.
    """
    print("Agent devOps is generating the manual deployment guide.")

    repo_path = state.get("repo_path", "")
    github_url = state.get("github_url", "<repo-url>")
    task = state.get("task_description", "<task>")

    guide_lines = [
        "# Deployment Guide",
        f"",
        f"**Task:** {task}",
        f"**Repository:** {github_url}",
        f"",
        "## Prerequisites",
        "",
        "| Tool | Version | Install |",
        "|---|---|---|",
        "| AWS CLI | ≥ 2.13 | `winget install Amazon.AWSCLI` / `brew install awscli` |",
        "| Node.js | 20.x LTS | https://nodejs.org |",
        "| AWS CDK | ≥ 2.x | `npm install -g aws-cdk` |",
        "| TypeScript | ≥ 5.x | `npm install -g typescript` |",
        "",
        "## Pre-Deployment Checklist",
        "",
        "- [ ] Authenticated to the correct AWS account: `aws sts get-caller-identity`",
        "- [ ] CDK synth passes: `npx cdk synth --context env=prod`",
        "- [ ] Change set reviewed: `npx cdk diff --context env=prod`",
        "",
        "## Step-by-Step Deployment",
        "",
        "```bash",
        "# 1. Install dependencies",
        "npm ci",
        "",
        "# 2. Build TypeScript",
        "npm run build",
        "",
        "# 3. Review what will change (read every [+] and [-] line)",
        "npx cdk diff --context env=prod",
        "",
        "# 4. Deploy — pauses on any broadening security change",
        "npx cdk deploy --all --context env=prod --require-approval broadening",
        "```",
        "",
        "## Verification",
        "",
        "```bash",
        "# CloudWatch alarms must all be OK",
        "aws cloudwatch describe-alarms --state-value OK --query 'MetricAlarms[*].[AlarmName,StateValue]' --output table",
        "",
        "# DLQ must be empty",
        'aws sqs get-queue-attributes --queue-url "$DLQ_URL" --attribute-names ApproximateNumberOfMessages',
        "",
        "# Health endpoint smoke test",
        'for i in $(seq 1 10); do curl -s -o /dev/null -w "Check $i: %{http_code}\\n" "$API_ENDPOINT/health"; done',
        "```",
        "",
        "## Rollback Plan",
        "",
        "```bash",
        "# Option A: Lambda alias rollback (< 60 seconds)",
        "aws lambda update-alias --function-name <function> --name live --function-version <prev-version> --routing-config AdditionalVersionWeights={}",
        "",
        "# Option B: CloudFormation stack rollback",
        "aws cloudformation rollback-stack --stack-name <stack-name>",
        "",
        "# Option C: Git revert + redeploy",
        "git revert HEAD --no-edit && git push origin main",
        "```",
        "",
        "---",
        f"Generated by: @devOps — deployment_guide skill  ",
        f"Signal: DEPLOYMENT_GUIDE_READY",
    ]

    guide_content = "\n".join(guide_lines)

    guide_path = "docs/deployment_guide.md"
    if repo_path:
        out = Path(repo_path) / guide_path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(guide_content, encoding="utf-8")
    else:
        # No local repo — write relative to cwd
        out = Path(guide_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(guide_content, encoding="utf-8")

    return {
        **_base_state(
            state,
            f"[devOps] DEPLOYMENT_GUIDE_READY — guide written to {guide_path}",
            "generate_manual_guide",
        ),
        "deployment_guide_path": guide_path,
    }


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
        _route_supervisor,
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


# Standalone compile (no checkpointer — HITL interrupt not available in __main__)
compiled_graph = build_graph().compile()


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
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
        "github_url": "",
        "repo_path": "",
        "test_passed": False,
        "task_description": "Design and deploy a new serverless API.",
        "completed_agents": [],
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
