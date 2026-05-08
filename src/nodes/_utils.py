"""
Shared utilities for agent node implementations.

Provides:
  - _base_state()              — append an AIMessage and mark an agent done
  - _make_worker()             — factory for placeholder agent nodes
  - _detect_bottleneck_*()     — static and LLM-signal bottleneck detection
  - _append_subtask_to_project_state() — write approved proposals to project_state.md
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Optional

from langchain_core.messages import AIMessage

from src.state import AgentState, RefactorProposal

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
    """Lowercase tokens (len > 3) from the task description used for scope matching."""
    return {w for w in re.findall(r"[\w/.\-]+", task_description.lower()) if len(w) > 3}


def detect_bottleneck_in_out_of_scope_files(
    repo_path: str,
    task_description: str,
) -> Optional[RefactorProposal]:
    """
    Scan source files unrelated to the current task for known HIGH-severity bottleneck
    patterns.  Returns the first proposal found, or None.
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


def parse_proposal_from_messages(
    messages: list,
) -> Optional[RefactorProposal]:
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


def append_subtask_to_project_state(
    repo_path: str,
    proposal: RefactorProposal,
) -> None:
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
# Base State Helper
# ---------------------------------------------------------------------------


def base_state(state: AgentState, content: str, name: str) -> AgentState:
    """Return a new state dict with one appended AIMessage and the agent marked done."""
    completed = list(state.get("completed_agents") or [])
    if name not in completed:
        completed.append(name)
    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=content, name=name)],
        "next_node": "supervisor",
        "completed_agents": completed,
    }


# ---------------------------------------------------------------------------
# Placeholder Worker Factory
# ---------------------------------------------------------------------------


def make_worker(name: str):
    """Factory for agents that are still placeholder (no live I/O)."""

    def worker(state: AgentState) -> AgentState:
        print(f"Agent {name} is working.")
        return base_state(state, f"[{name}] Task processed.", name)

    worker.__name__ = f"{name}_node"
    return worker
