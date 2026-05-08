"""Step-by-step pipeline execution — Step-and-Wait Interactive Protocol.

Every agent step returns a response with:
  - proposed_changes:       files the IDE must write to disk
  - next_agent_instruction: what to do after applying the files
  - is_task_complete:       False until all agents have verified their work

The IDE MUST apply proposed_changes before calling advance_pipeline again.
If the files are not on disk, advance_pipeline returns WAITING_FOR_FILES and
refuses to proceed.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from src.orchestrator import build_graph, inject_shared_templates
from src.state import AgentState, FileOperation, PIPELINE_SEQUENCE

_checkpointer = MemorySaver()

# Pause BEFORE each agent; permission_gate / tech_lead_gate self-interrupt via interrupt().
_INTERRUPT_BEFORE = ["codeCrafter", "codeReviewer", "qualityGuard"]

_compiled_graph = build_graph().compile(
    checkpointer=_checkpointer,
    interrupt_before=_INTERRUPT_BEFORE,
)

# thread_id → (langgraph_config, file_ops_count_before_this_step)
_active_threads: dict[str, tuple[dict[str, Any], int]] = {}

_PREREQ_APPROVAL = {"qualityGuard"}

# Session persistence — written to {project_path}/.seahub/session.json
_SESSION_SUBDIR = ".seahub"
_SESSION_FILENAME = "session.json"


# ---------------------------------------------------------------------------
# Per-transition instructions
# ---------------------------------------------------------------------------

def _next_agent_instruction(next_step: str) -> str:
    _INSTRUCTIONS: dict[str, str] = {
        "codeCrafter": (
            "Architecture scaffold proposed. Apply the files above to disk, then call "
            "advance_pipeline — CodeCrafter will read the local filesystem to verify "
            "compatibility before beginning implementation."
        ),
        "codeReviewer": (
            "Implementation complete. Apply the files above to disk, then call advance_pipeline — "
            "CodeReviewer will inspect the actual local files to validate alignment with the ADR "
            "before writing review annotations."
        ),
        "qualityGuard": (
            "Code review passed. Apply the files above to disk, then call advance_pipeline — "
            "QualityGuard will run tests against the local filesystem."
        ),
        "tech_lead_gate": (
            "Quality gate cleared. Apply the files above to disk, then call advance_pipeline — "
            "TechLead will prompt for deployment approval."
        ),
        "devOps": (
            "Deployment approved. Apply the files above to disk, then call advance_pipeline — "
            "DevOps will verify the local deployment configuration before releasing."
        ),
        "generate_manual_guide": (
            "Manual deployment requested. Apply the files above to disk, then call advance_pipeline — "
            "DevOps will generate a human-executable deployment guide."
        ),
        "FINISH": (
            "All agents have verified their work. The pipeline is complete. "
            "Review and apply the final generated files."
        ),
    }
    return _INSTRUCTIONS.get(
        next_step,
        f"Apply the files above to disk, then call advance_pipeline to proceed to {next_step}.",
    )


# ---------------------------------------------------------------------------
# Session persistence
# ---------------------------------------------------------------------------

def _resolve_project_path(project_path: str) -> Path:
    """Return an absolute, OS-canonical Path for project_path.

    Handles forward-slash Windows paths (k:/foo/bar), relative paths, and
    mixed separators uniformly on Linux, macOS, and Windows.
    """
    return Path(project_path).resolve()


def _session_path(project_path: str) -> Path:
    return _resolve_project_path(project_path) / _SESSION_SUBDIR / _SESSION_FILENAME


def _save_session(
    project_path: str,
    session_id: str,
    task_description: str,
    completed_agents: list[str],
    verification_paths: list[str],
) -> None:
    """Persist session metadata to disk so the pipeline can verify state on resumption."""
    if not project_path:
        return
    try:
        sp = _session_path(project_path)
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(
            json.dumps({
                "session_id": session_id,
                "project_path": project_path,
                "task_description": task_description,
                "completed_agents": completed_agents,
                "pending_verification_paths": verification_paths,
            }, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass  # non-fatal — session file is best-effort


def _load_session(project_path: str) -> dict[str, Any] | None:
    """Read the on-disk session file; returns None if missing or corrupt."""
    if not project_path:
        return None
    try:
        sp = _session_path(project_path)
        if not sp.exists():
            return None
        data = json.loads(sp.read_text(encoding="utf-8"))
        # Normalise the stored project_path so subsequent comparisons use the
        # same resolved form regardless of how it was originally supplied.
        if "project_path" in data:
            data["project_path"] = str(_resolve_project_path(data["project_path"]))
        return data
    except (json.JSONDecodeError, OSError):
        return None


def _collect_new_create_paths(
    project_path: str,
    file_ops: list[FileOperation],
) -> list[str]:
    """Return relative paths of create-ops that do NOT yet exist on disk.

    Only newly-created files are tracked for verification — update/delete ops
    cannot reliably be checked by existence alone.

    Paths are normalised to forward-slash POSIX strings so that the values
    stored in session.json are portable across Linux, macOS, and Windows.
    """
    if not project_path:
        return []
    root = _resolve_project_path(project_path)
    pending: list[str] = []
    for op in file_ops:
        if op.get("action") != "create":
            continue
        # Normalise to forward slashes for cross-platform JSON storage.
        rel = Path(op["path"]).as_posix()
        if not (root / rel).exists():
            pending.append(rel)
    return pending


def _find_missing_files(project_path: str, pending_paths: list[str]) -> list[str]:
    """Return any paths from pending_paths that are still absent on disk.

    Uses a resolved absolute root so that forward-slash Windows paths
    (k:/foo/bar) and relative project paths all resolve correctly on every OS.
    """
    if not project_path or not pending_paths:
        return []
    root = _resolve_project_path(project_path)
    return [p for p in pending_paths if not (root / Path(p)).exists()]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _pending_interrupt(config: dict[str, Any]) -> str | None:
    snapshot = _compiled_graph.get_state(config)
    if not snapshot.next:
        return None
    for task in snapshot.tasks:
        for intr in task.interrupts:
            return str(intr.value)
    return None


def _context_file_op(task: str, completed: list[str]) -> FileOperation:
    pending = [s for s in PIPELINE_SEQUENCE if s not in completed]
    content = (
        f"# Project Context\n\n**Task:** {task}\n\n## Completed Tasks\n"
        + "".join(f"- [x] {a}\n" for a in completed)
        + "\n## Pending Tasks\n"
        + "".join(f"- [ ] {a}\n" for a in pending)
    )
    return {"path": ".github/shared/project_context.md", "content": content, "action": "create"}


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------

def _step_response(
    thread_id: str,
    config: dict[str, Any],
    state: AgentState,
    prev_count: int,
) -> str:
    all_ops: list[FileOperation] = list(state.get("file_operations") or [])
    completed = list(state.get("completed_agents") or [])
    snapshot = _compiled_graph.get_state(config)
    next_step = snapshot.next[0] if snapshot.next else "FINISH"

    if next_step in _INTERRUPT_BEFORE:
        idx = _INTERRUPT_BEFORE.index(next_step)
        agent = _INTERRUPT_BEFORE[idx - 1] if idx > 0 else "architect"
    else:
        agent = completed[-1] if completed else "architect"

    msgs = state.get("messages") or []
    status = msgs[-1].content.strip() if msgs else f"[{agent}] completed."
    ctx_op = _context_file_op(state.get("task_description", ""), completed)
    new_ops: list[FileOperation] = [*all_ops[prev_count:], ctx_op]

    project_path = state.get("project_path", "")
    verification_paths = _collect_new_create_paths(project_path, new_ops)
    _save_session(
        project_path, thread_id, state.get("task_description", ""),
        completed, verification_paths,
    )

    return json.dumps({
        "status": "STEP_COMPLETE",
        "session_id": thread_id,
        "continuation_token": thread_id,
        "current_agent": agent,
        "status_update": status,
        "proposed_changes": new_ops,
        "next_agent_instruction": _next_agent_instruction(next_step),
        "is_task_complete": False,
        "requires_approval": next_step in _PREREQ_APPROVAL,
        "pending_tasks": [s for s in PIPELINE_SEQUENCE if s not in completed],
        "completed_tasks": completed,
    }, indent=2)


def _paused_response(thread_id: str, question: str, state: AgentState) -> str:
    completed = list(state.get("completed_agents") or [])
    file_ops: list[FileOperation] = list(state.get("file_operations") or [])
    ctx_op = _context_file_op(state.get("task_description", ""), completed)
    new_ops: list[FileOperation] = [*file_ops, ctx_op]

    project_path = state.get("project_path", "")
    verification_paths = _collect_new_create_paths(project_path, new_ops)
    _save_session(
        project_path, thread_id, state.get("task_description", ""),
        completed, verification_paths,
    )

    return json.dumps({
        "status": "PIPELINE_PAUSED",
        "session_id": thread_id,
        "continuation_token": thread_id,
        "question": question,
        "requires_approval": True,
        "proposed_changes": new_ops,
        "next_agent_instruction": (
            "A decision is required. Apply any proposed_changes to disk, then call "
            "resume_refactor_decision or resume_deployment_decision."
        ),
        "is_task_complete": False,
        "resume_hint": (
            f"Call resume_refactor_decision(thread_id='{thread_id}', decision='Yes'|'No') "
            f"or resume_deployment_decision(thread_id='{thread_id}', decision='Approve'|'Manual')"
        ),
    }, indent=2)


def _complete_response(state: AgentState) -> str:
    completed = list(state.get("completed_agents") or [])
    file_ops: list[FileOperation] = list(state.get("file_operations") or [])
    msgs = state.get("messages") or []
    ctx_op = _context_file_op(state.get("task_description", ""), completed)
    base: dict[str, Any] = {
        "proposed_changes": [*file_ops, ctx_op],
        "completed_tasks": completed,
        "status_update": msgs[-1].content.strip() if msgs else "Pipeline complete.",
        "next_agent_instruction": _next_agent_instruction("FINISH"),
        "is_task_complete": True,
    }
    guide = state.get("deployment_guide_path")
    if guide:
        return json.dumps({"status": "DEPLOYMENT_GUIDE_READY", "guide_path": guide, **base}, indent=2)
    return json.dumps({"status": "PIPELINE_COMPLETE", **base}, indent=2)


def _waiting_response(
    thread_id: str,
    missing_files: list[str],
    next_step: str,
) -> str:
    """Returned when the IDE has not yet applied the previous step's proposed_changes."""
    files_list = ", ".join(f"`{f}`" for f in missing_files)
    return json.dumps({
        "status": "WAITING_FOR_FILES",
        "session_id": thread_id,
        "continuation_token": thread_id,
        "missing_files": missing_files,
        "next_agent_instruction": (
            f"I am waiting for the previous changes to be applied to the filesystem "
            f"before I can proceed with the {next_step} phase. "
            f"Please write the following files to disk and then call advance_pipeline again: "
            f"{files_list}"
        ),
        "is_task_complete": False,
    }, indent=2)


def _after_invoke(
    thread_id: str,
    config: dict[str, Any],
    state: AgentState,
    prev_count: int,
) -> str:
    """Route to the correct response after any graph invocation."""
    question = _pending_interrupt(config)
    new_count = len(list(state.get("file_operations") or []))
    if question:
        _active_threads[thread_id] = (config, new_count)
        return _paused_response(thread_id, question, state)
    snapshot = _compiled_graph.get_state(config)
    if snapshot.next:
        _active_threads[thread_id] = (config, new_count)
        return _step_response(thread_id, config, state, prev_count)
    _active_threads.pop(thread_id, None)
    return _complete_response(state)


def _pop_thread(thread_id: str) -> tuple[dict[str, Any], int] | None:
    return _active_threads.pop(thread_id, None)


def _err(msg: str) -> str:
    return json.dumps({"status": "ERROR", "message": msg})


# ---------------------------------------------------------------------------
# Public pipeline API
# ---------------------------------------------------------------------------


def start_pipeline(project_path: str, task_description: str) -> str:
    """Inject shared templates, start the graph, run architect, return step 1.

    Reads .seahub/session.json from the project directory (if it exists) to
    surface any prior session context before running the architect node.
    """
    # Resolve early so every downstream consumer gets a canonical absolute path
    # that works identically on Linux, macOS, and Windows (including paths
    # passed with forward slashes like k:/foo/bar from VS Code on Windows).
    project_path = str(_resolve_project_path(project_path))
    thread_id = uuid.uuid4().hex
    injected = inject_shared_templates(project_path)
    if injected:
        print(f"[SEagenthub] Injected shared templates: {', '.join(injected)}")

    # Read any prior session context into the initial message so agents can
    # pick up where they left off.
    prior_context = ""
    prior_session = _load_session(project_path)
    if prior_session:
        prior_agents = prior_session.get("completed_agents", [])
        if prior_agents:
            prior_context = (
                f"\n\nPrior session context: agents {prior_agents} have already "
                f"completed work in this project. Review .github/shared/project_context.md "
                f"and .github/shared/architecture_log.md before proceeding."
            )

    initial_state: AgentState = {
        "messages": [HumanMessage(content=(
            f"Project path: {project_path}\nTask: {task_description}\n\n"
            "Execute the full SDLC: design the architecture, implement the necessary "
            "code changes, review the code, run all tests, and deploy once tests pass."
            + prior_context
        ))],
        "next_node": "", "project_path": project_path, "repo_path": project_path,
        "test_passed": False, "task_description": task_description,
        "completed_agents": [], "artifacts": [], "file_operations": [],
        "pending_refactor_proposal": None, "active_subtasks": [],
        "user_approval": None, "deployment_guide_path": None,
    }
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    state: AgentState = _compiled_graph.invoke(initial_state, config=config)
    return _after_invoke(thread_id, config, state, 0)


def advance_step(thread_id: str) -> str:
    """Verify that previous proposed_changes are on disk, then resume the next agent.

    Returns WAITING_FOR_FILES (without advancing) if any file from the last
    STEP_COMPLETE response has not been written to disk yet.
    """
    entry = _pop_thread(thread_id)
    if entry is None:
        return _err(
            f"No active pipeline for token={thread_id!r}. "
            "The server may have been restarted. Start a new pipeline with techLead."
        )
    config, prev_count = entry

    # Determine next node name for display in any blocking message.
    snapshot = _compiled_graph.get_state(config)
    next_step = snapshot.next[0] if snapshot.next else "FINISH"

    # Load session to retrieve project_path and pending verification paths.
    project_path: str = (snapshot.values or {}).get("project_path", "")
    session = _load_session(project_path) if project_path else None

    if session:
        # Re-read project_context.md to confirm we know where we left off.
        ctx_path = Path(project_path) / ".github" / "shared" / "project_context.md"
        if ctx_path.exists():
            print(
                f"[SEagenthub] Resuming session {thread_id[:8]}… "
                f"context: {ctx_path}"
            )

        pending_paths = session.get("pending_verification_paths", [])
        if pending_paths:
            missing = _find_missing_files(project_path, pending_paths)
            if missing:
                # Re-register so the client can retry after writing the files.
                _active_threads[thread_id] = (config, prev_count)
                return _waiting_response(thread_id, missing, next_step)

    state: AgentState = _compiled_graph.invoke(None, config=config)
    return _after_invoke(thread_id, config, state, prev_count)


def resume_refactor(thread_id: str, decision: str) -> str:
    """Resume a permission_gate interrupt with a Yes/No decision."""
    entry = _pop_thread(thread_id)
    if entry is None:
        return _err(f"No paused pipeline for thread_id={thread_id!r}.")
    config, prev_count = entry
    if decision.strip().lower() not in {"yes", "no", "y", "n"}:
        _active_threads[thread_id] = (config, prev_count)
        return _err("decision must be 'Yes' or 'No'.")
    state: AgentState = _compiled_graph.invoke(Command(resume=decision), config=config)
    return _after_invoke(thread_id, config, state, prev_count)


def resume_deployment(thread_id: str, decision: str) -> str:
    """Resume a tech_lead_gate interrupt with an Approve/Manual decision."""
    entry = _pop_thread(thread_id)
    if entry is None:
        return _err(f"No paused pipeline for thread_id={thread_id!r}.")
    config, prev_count = entry
    if decision.strip().lower() not in {"approve", "manual", "yes", "no", "y", "n"}:
        _active_threads[thread_id] = (config, prev_count)
        return _err("decision must be 'Approve' or 'Manual'.")
    state: AgentState = _compiled_graph.invoke(Command(resume=decision), config=config)
    return _after_invoke(thread_id, config, state, prev_count)
