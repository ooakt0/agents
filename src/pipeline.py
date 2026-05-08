"""Step-by-step pipeline execution — Incremental Interactive Workflow."""
from __future__ import annotations

import json
import uuid
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

# Advancing to qualityGuard leads into the uninterruptible deployment gate.
_PREREQ_APPROVAL = {"qualityGuard"}


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


def _step_response(thread_id: str, config: dict[str, Any], state: AgentState, prev_count: int) -> str:
    all_ops: list[FileOperation] = list(state.get("file_operations") or [])
    completed = list(state.get("completed_agents") or [])
    snapshot = _compiled_graph.get_state(config)
    next_step = snapshot.next[0] if snapshot.next else "FINISH"

    # Derive which agent just finished from its position relative to next_step.
    if next_step in _INTERRUPT_BEFORE:
        idx = _INTERRUPT_BEFORE.index(next_step)
        agent = _INTERRUPT_BEFORE[idx - 1] if idx > 0 else "architect"
    else:
        agent = completed[-1] if completed else "architect"

    msgs = state.get("messages") or []
    status = msgs[-1].content.strip() if msgs else f"[{agent}] completed."
    ctx_op = _context_file_op(state.get("task_description", ""), completed)
    return json.dumps({
        "status": "STEP_COMPLETE",
        "continuation_token": thread_id,
        "current_agent": agent,
        "status_update": status,
        "files_to_create": [*all_ops[prev_count:], ctx_op],
        "requires_approval": next_step in _PREREQ_APPROVAL,
        "pending_tasks": [s for s in PIPELINE_SEQUENCE if s not in completed],
        "completed_tasks": completed,
    }, indent=2)


def _paused_response(thread_id: str, question: str, state: AgentState) -> str:
    completed = list(state.get("completed_agents") or [])
    file_ops: list[FileOperation] = list(state.get("file_operations") or [])
    ctx_op = _context_file_op(state.get("task_description", ""), completed)
    return json.dumps({
        "status": "PIPELINE_PAUSED",
        "continuation_token": thread_id,
        "question": question,
        "requires_approval": True,
        "files_to_create": [*file_ops, ctx_op],
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
        "files_to_create": [*file_ops, ctx_op],
        "completed_tasks": completed,
        "status_update": msgs[-1].content.strip() if msgs else "Pipeline complete.",
    }
    guide = state.get("deployment_guide_path")
    if guide:
        return json.dumps({"status": "DEPLOYMENT_GUIDE_READY", "guide_path": guide, **base}, indent=2)
    return json.dumps({"status": "PIPELINE_COMPLETE", **base}, indent=2)


def _after_invoke(thread_id: str, config: dict[str, Any], state: AgentState, prev_count: int) -> str:
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
    """Inject shared templates, start the graph, run architect, return step 1."""
    thread_id = uuid.uuid4().hex
    injected = inject_shared_templates(project_path)
    if injected:
        print(f"[SEagenthub] Injected shared templates: {', '.join(injected)}")

    initial_state: AgentState = {
        "messages": [HumanMessage(content=(
            f"Project path: {project_path}\nTask: {task_description}\n\n"
            "Execute the full SDLC: design the architecture, implement the necessary "
            "code changes, review the code, run all tests, and deploy once tests pass."
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
    """Resume an interrupt_before pause and run the next agent."""
    entry = _pop_thread(thread_id)
    if entry is None:
        return _err(f"No active pipeline for token={thread_id!r}. It may have completed or the server was restarted.")
    config, prev_count = entry
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
