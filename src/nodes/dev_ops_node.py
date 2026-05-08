"""devOps node — POST to the deployment dashboard once tests pass."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from src.nodes._utils import base_state
from src.state import AgentState


def dev_ops_node(state: AgentState) -> AgentState:
    print("Agent devOps is working.")

    if not state.get("test_passed", False):
        return base_state(
            state,
            "[devOps] Deployment skipped — tests did not pass.",
            "devOps",
        )

    dashboard_url = os.environ.get("DEPLOY_DASHBOARD_URL", "")
    if not dashboard_url:
        return base_state(
            state,
            "[devOps] DEPLOY_DASHBOARD_URL not set — deployment skipped.",
            "devOps",
        )

    payload = json.dumps(
        {
            "repo": state.get("github_url", ""),
            "status": "ready",
            "triggered_by": "AgentHub",
        }
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

    return base_state(
        state,
        f"[devOps] Deployment triggered. {deploy_status}",
        "devOps",
    )
