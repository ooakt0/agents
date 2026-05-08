# Multi-Agent Engineering Framework

A portable, AI-powered engineering team with two complementary layers:

1. **Prompt-driven agents** — structured personas for GitHub Copilot and Claude Code, coordinated through shared state files and exact signal phrases.
2. **`seagenthub` MCP Server** — a FastMCP tool server that exposes the same 6-agent pipeline as a single callable tool, consumable from VS Code, Cursor, and Claude Code without any LLM API key.

Covers the full SDLC (design → implement → review → test → deploy) and all 6 pillars of the **AWS Well-Architected Framework**.

---

## Table of Contents

1. [What This Is](#what-this-is)
2. [Repository Layout](#repository-layout)
3. [Prerequisites](#prerequisites)
4. [seagenthub MCP Server](#seagenthub-mcp-server)
5. [Using in a New Project (Prompt Agent Layer)](#using-in-a-new-project-prompt-agent-layer)
6. [First Run: INIT\_PROJECT](#first-run-init_project)
7. [Daily Usage](#daily-usage)
8. [Agent Reference](#agent-reference)
9. [Signal Phrase Contract](#signal-phrase-contract)
10. [Skill Reference](#skill-reference)
11. [Shared State Files](#shared-state-files)
12. [Adding a New Skill or Agent](#adding-a-new-skill-or-agent)
13. [Troubleshooting](#troubleshooting)

---

## What This Is

Six AI agent personas, each with a defined role, a set of skill files, and strict handoff contracts. All six are orchestrated via a **deterministic LangGraph pipeline** inside the `seagenthub` MCP server — no LLM routing, no API key, no hook scripts.

| Agent | Role | Activated By |
|---|---|---|
| `@techLead` | Orchestrator — decomposes goals, delegates, audits results | `@techLead`, `INIT_PROJECT`, `DELEGATE`, `AUDIT_RESULT`, `CHANGE_REQUEST` |
| `@architect` | Infrastructure designer — CDK, IAM, observability, cost | `DELEGATE [architect]` |
| `@codeCrafter` | Implementation — business logic, UI, resilience patterns | `DELEGATE [codeCrafter]`, `Cleared for implementation` |
| `@codeReviewer` | Quality gatekeeper — complexity, naming, CVEs, docs | `Handing off to @codeReviewer` (automatic) |
| `@qualityGuard` | Testing & security — unit / integration / load / pen testing | `Handing off to @qualityGuard` (automatic) |
| `@devOps` | Deployment — CI/CD, environment promotion, verification | automatic after `AUDIT_RESULT` |

The **signal phrases** defined in each skill file's OUTPUT CONTRACT are the transition conditions LangGraph evaluates at every node boundary. When used as prompt-driven agents in an IDE (Copilot, Claude Code), the same phrases drive the conversational handoff — the contract is identical in both layers.

---

## Repository Layout

```
agents/
├── src/                          ← MCP server source
│   ├── main.py                   ← FastMCP entry point — run this to start the server
│   ├── orchestrator.py           ← LangGraph graph assembly + template injection
│   ├── state.py                  ← AgentState TypedDict and shared types
│   └── nodes/                    ← One module per LangGraph node
│       ├── _utils.py             ← Shared helpers (base_state, make_worker, detect_bottleneck)
│       ├── supervisor_node.py    ← Deterministic router (no LLM)
│       ├── architect_node.py
│       ├── code_crafter_node.py  ← git clone → apply changes → commit → push
│       ├── code_reviewer_node.py
│       ├── quality_guard_node.py ← pytest runner
│       ├── dev_ops_node.py       ← POST to DEPLOY_DASHBOARD_URL
│       ├── tech_lead_gate_node.py      ← HITL deployment approval gate
│       ├── devops_manual_guide_node.py ← generates docs/deployment_guide.md
│       └── permission_gate_node.py     ← HITL refactor approval gate
│
├── prompts/                      ← Agent persona and skill files
│   ├── agents/                   ← Persona files (one per agent)
│   │   ├── techLead.agent.md
│   │   ├── architect.agent.md
│   │   ├── codeCrafter.agent.md
│   │   ├── codeReviewer.agent.md
│   │   ├── qualityGuard.agent.md
│   │   ├── devOps.agent.md
│   │   └── deploy_lead.agent.md  ← VS Code Copilot agent backed by seagenthub
│   └── skills/                   ← Skill files organised by agent
│       ├── techLead/             ← 12 skills (handoff_template, change_analysis, ...)
│       ├── architect/            ← 10 skills
│       ├── codeCrafter/          ← 9 skills
│       ├── codeReviewer/         ← 9 skills
│       ├── qualityGuard/         ← 10 skills
│       └── devOps/               ← 9 skills
│
├── templates/                    ← Canonical .github/shared/ files
│   ├── project_context.md        ← Auto-injected into new repos by src/orchestrator.py
│   ├── project_state.md
│   ├── standards.md
│   └── architecture_log.md
│
├── .github/
│   ├── copilot-instructions.md   ← Agent routing for GitHub Copilot
│   └── shared/                   ← Live project state (populated at runtime)
│       ├── project_context.md
│       ├── project_state.md
│       ├── standards.md
│       └── architecture_log.md
│
├── mcp.json                      ← MCP server config — copy to .cursor/ or .vscode/ in any project
├── pyproject.toml                ← Python package metadata + `seagenthub` CLI entry point
├── requirements.txt              ← Pinned runtime dependencies
├── CLAUDE.md                     ← Auto-loaded by Claude Code on every session
└── README.md
```

**Key distinction:** `templates/` holds the canonical blank copies. `src/orchestrator.py::inject_shared_templates()` copies them into `.github/shared/` of any **target repository** the first time the pipeline runs on it. The `.github/shared/` in this repo is the framework's own state, not a template.

---

## Prerequisites

- **GitHub Copilot** (VS Code extension) or **Claude Code** (CLI) — works with both
- **Python 3.10+** for the `seagenthub` MCP server
- Install the package and its dependencies:

```bash
# Option A — editable install (recommended for development)
pip install -e .

# Option B — install from requirements only
pip install -r requirements.txt
```

- AWS CDK v2 if using the infrastructure design skills:

```bash
npm i -g aws-cdk
```

---

## seagenthub MCP Server

`seagenthub` is a **stateless FastMCP tool server** that runs the 6-agent LangGraph pipeline on a GitHub repository. Each call is fully isolated — no state persists between invocations.

### Architecture

```
seagenthub (FastMCP)  ←  src/main.py
  └─▶ execute_software_pipeline(github_repo_url, task_description)
        └─▶ LangGraph StateGraph  ←  src/orchestrator.py
              │
              ├── supervisor_node          ← deterministic router
              │     reads PIPELINE_SEQUENCE, routes by completed_agents
              │
              ├── permission_gate_node     ← HITL: approve out-of-scope refactors
              │
              ├── architect_node           ← placeholder (extend with IaC logic)
              ├── code_crafter_node        ← git clone → apply changes → commit → push
              ├── code_reviewer_node       ← placeholder (extend with review logic)
              ├── quality_guard_node       ← python -m pytest --tb=short -q
              ├── tech_lead_gate_node      ← HITL: Approve or Manual deploy decision
              ├── devops_manual_guide_node ← generates docs/deployment_guide.md
              └── dev_ops_node             ← POST to DEPLOY_DASHBOARD_URL
```

### State schema (`src/state.py`)

| Field | Type | Description |
|---|---|---|
| `messages` | `list[BaseMessage]` | Full conversation history |
| `next_node` | `str` | Node name the supervisor selected next |
| `github_url` | `str` | Repo URL passed from the tool |
| `repo_path` | `str` | Absolute local path after `codeCrafter` clones the repo |
| `test_passed` | `bool` | Set by `qualityGuard`; gates `devOps` deployment |
| `task_description` | `str` | Human-readable goal forwarded from the MCP tool |
| `completed_agents` | `list[str]` | Agents that have already run this invocation |
| `pending_refactor_proposal` | `RefactorProposal \| None` | Out-of-scope refactor awaiting user approval |
| `active_subtasks` | `list[str]` | Approved refactors appended to `project_state.md` |
| `user_approval` | `str \| None` | `"Approve"` or `"Manual"` from the tech lead gate |
| `deployment_guide_path` | `str \| None` | Path to `docs/deployment_guide.md` when Manual selected |

### Human-in-the-loop gates

The graph has two `interrupt()` pause points:

| Gate | Node | Trigger | Options |
|---|---|---|---|
| Refactor approval | `permission_gate_node` | `codeCrafter` detects work outside task scope | Yes (append subtask) / No (discard) |
| Deployment authorization | `tech_lead_gate_node` | All tests pass, ready to deploy | Approve (automated deploy) / Manual (generate guide) |

Resume an interrupted run:

```python
resume_refactor_decision(thread_id, approved: bool)
resume_deployment_decision(thread_id, decision: str)  # "Approve" or "Manual"
```

### Running the server

```bash
# stdio — default, used by Claude Code and Cursor
python src/main.py

# SSE — for VS Code
python src/main.py --transport=sse
```

### IDE integration

**Claude Code:**
```bash
claude mcp add seagenthub -- python src/main.py
```

**Cursor / VS Code:** Copy `mcp.json` from the repo root into your project's `.cursor/` or `.vscode/` directory, then update `cwd` to point at this repo.

**After `pip install -e .`:** The `seagenthub` command is available globally:
```bash
seagenthub                        # stdio (default)
seagenthub --transport=sse        # SSE for VS Code / Cursor
```

### The `execute_software_pipeline` tool

```python
execute_software_pipeline(
    github_repo_url: str,   # e.g. "https://github.com/owner/repo"
    task_description: str,  # e.g. "Add input validation to /checkout and deploy to staging"
) -> str                    # human-readable agent timeline + test/deploy status
```

Example output:

```
AgentHub pipeline complete for https://github.com/owner/repo

[HumanMessage]  Repository: https://github.com/owner/repo  |  Task: Add input validation...
[architect]     Task processed.
[codeCrafter]   Clone ✓ | commit: True | push: pushed to origin
[codeReviewer]  Task processed.
[qualityGuard]  Tests PASSED — 42 passed, 0 failed
[devOps]        Deployment triggered. HTTP 200 — {"ok":true}

Tests passed : True
Agents run   : architect, codeCrafter, codeReviewer, qualityGuard, devOps
```

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `GITHUB_TOKEN` | Optional | PAT for authenticated `git push` in `codeCrafter` |
| `DEPLOY_DASHBOARD_URL` | Optional | POST endpoint called by `devOps` after tests pass |

No `OPENAI_API_KEY` required — the supervisor is fully deterministic.

### Template injection

When the pipeline first processes a target repository, `inject_shared_templates(repo_path)` copies the four files from `templates/` into `<repo>/.github/shared/` if that directory does not yet exist. This bootstraps the shared state without any manual setup.

---

## Using in a New Project (Prompt Agent Layer)

### Step 1 — Install the package

```bash
# Clone or copy the seagenthub repo, then install it
git clone https://github.com/your-org/seagenthub
cd seagenthub
pip install -e .
```

Then copy these files into your **target project root**:

```
your-project/
  ├── .github/
  │   ├── copilot-instructions.md ← copy from seagenthub/.github/
  │   └── shared/                 ← auto-populated at INIT_PROJECT
  ├── .cursor/mcp.json            ← copy from seagenthub/mcp.json, set cwd to seagenthub dir
  └── CLAUDE.md                   ← copy from seagenthub/CLAUDE.md
```

The `prompts/`, `templates/`, and `src/` directories stay inside the seagenthub package — they are not copied to your project.

### Step 2 — Fill in the shared state files

| File | Who fills it | When |
|---|---|---|
| `.github/shared/project_context.md` | @techLead | At `INIT_PROJECT` — auto-populated from your description |
| `.github/shared/project_state.md` | @techLead | At `INIT_PROJECT` — task board created from goal |
| `.github/shared/architecture_log.md` | @architect | During design phase — one ADR per decision |
| `.github/shared/standards.md` | @techLead | Pre-filled — extend only if your project has extra conventions |

### Step 3 — Start your first session

```
@techLead INIT_PROJECT: [describe your project]
```

---

## First Run: INIT\_PROJECT

Always start a new project — or a major new feature — with:

```
@techLead INIT_PROJECT: [describe your goal in plain language]
```

@techLead will:
1. Create or validate `.github/shared/project_context.md` — fills in tech stack, directory structure, entry points, and known constraints. **No agent is delegated until this file exists.**
2. Break the goal into atomic tasks (`T-001`, `T-002`, ...) in `project_state.md`.
3. Begin the agent chain by delegating to `@architect`.

### For a change to an existing feature:

```
@techLead CHANGE_REQUEST: [describe the change]
```

Or just describe the change in plain language — @techLead detects this automatically and activates the change analysis + impact assessment workflow before any delegation.

---

## Daily Usage

### Start a new task

```
@techLead INIT_PROJECT: Build a booking cancellation Lambda that marks DynamoDB records as cancelled and publishes a BookingCancelled event to EventBridge
```

### Request a change to an existing feature

```
@techLead the cancel booking endpoint is returning 200 when the booking doesn't exist — it should return 404
```

### Manually delegate to a specific agent

```
@techLead DELEGATE [architect]: design the EventBridge rule and DLQ for the cancellation flow
```

### Audit quality results and proceed to deployment

```
@techLead AUDIT_RESULT
```

### The automatic chain

```
INIT_PROJECT
  → @architect    (design + ADRs)
  → @codeCrafter  (implement)
  → @codeReviewer (review)
  → @qualityGuard (test + security)
  → AUDIT_RESULT
  → @devOps       (deploy + verify)
  → done
```

When running via the `seagenthub` MCP tool the server executes this sequence end-to-end. When working through prompt-driven agents in an IDE you direct the session — signal phrases tell the AI which agent activates next.

You only need to intervene at two points:
- **After @architect:** approve ADRs, then write `Cleared for implementation`
- **After @qualityGuard:** run `AUDIT_RESULT` to trigger @devOps

---

## Agent Reference

### @techLead

The only agent you address directly. All others are triggered by signal phrases.

| Command | When to use |
|---|---|
| `INIT_PROJECT: [description]` | New project or major new feature |
| `CHANGE_REQUEST: [description]` | Change or fix something in an existing feature |
| `DELEGATE [agentName]: [task]` | Send work to a specific agent manually |
| `AUDIT_RESULT` | After @qualityGuard finishes — triggers @devOps if gate clears |

**Reads before every response:**
1. `.github/shared/project_context.md` ← creates it if missing
2. `.github/shared/project_state.md`
3. `.github/shared/standards.md`

---

### @architect

Produces ADRs, CDK stacks, and security decisions. Never writes application code.

**Skills (in order):**

| Skill | Purpose | WAF Pillar |
|---|---|---|
| `service_boundary_analysis` | Domain boundaries, anti-coupling | Operational Excellence |
| `observability_design` | CloudWatch alarms, structured logs, X-Ray | Operational Excellence |
| `reliability_design` | Failure modes, RTO/RPO, DLQ config, Multi-AZ | Reliability |
| `disaster_recovery_strategy` | Multi-region failover, PITR, runbook | Reliability |
| `data_sovereignty_privacy` | PII isolation, residency, retention, CMK | Security |
| `generate_cdk_boilerplate` | CDK v2 TypeScript stacks, tagging, private subnets | All |
| `security_group_audit` | IAM least privilege, encryption, networking | Security |
| `cost_estimation` | Dev vs Prod sizing, idle-cost anti-patterns | Cost Optimization |
| `legacy_integration_bridge` | Adapter/Facade/ACL, resilience wrapping | Reliability |
| `adr_generation` | Formal ADR per decision, alternatives, reversibility | Operational Excellence |

End signal: `Cleared for implementation` (or `SECURITY FAIL: [description]`)

---

### @codeCrafter

Reads the handoff template and selects the correct language section from `implement_logic.md` based on the `Language / Stack` field.

**Supported languages:** TypeScript, JavaScript, Python, Java, Kotlin, React, Next.js, Angular.

**Skills (in order):**

| Skill | Purpose | WAF Pillar |
|---|---|---|
| `api_contract_design` | TypeScript interfaces, endpoint specs, StandardErrorResponse | Operational Excellence |
| `add_dependencies` | CVE audit, license check, exact version pinning | Security |
| `secure_coding_standards` | Input validation (Zod/Pydantic), injection prevention, OWASP | Security |
| `implement_logic` | TypeScript strict, ≤30 lines/fn, custom error classes | — |
| `error_handling_strategy` | Domain error hierarchy, central handler, safe messages | Reliability |
| `ui_component_generator` | Atomic Design, Tailwind, ARIA *(UI tasks only)* | — |
| `resilience_patterns` | Retry backoff, idempotency, DLQ wiring — **never skip** | Reliability |
| `performance_optimization` | N+1 fix, pagination, caching, Lambda cold start | Performance Efficiency |
| `refactoring_refinement` | DRY, SOLID, code smells, design patterns, naming | Operational Excellence |

End signal: `Refactoring complete. Handing off to @codeReviewer.`

**Out-of-scope refactor detection:** If `codeCrafter` identifies a bottleneck in a file outside the task scope it emits a `REFACTOR_PROPOSAL` and pauses for user approval. Approved proposals are appended to `project_state.md` as new subtasks.

---

### @codeReviewer

Runs automatically on `Handing off to @codeReviewer`. Any FAIL returns work to @codeCrafter immediately — the chain does not continue.

**Skills (in order):**

| Skill | Gate | FAIL Action |
|---|---|---|
| `architectural_alignment_audit` | Strategic | Return to @codeCrafter or HOLD for @architect |
| `breaking_change_detection` | Stability | Return to @codeCrafter |
| `security_surface_analysis` | Security | `SECURITY FAIL:` or return to @codeCrafter |
| `complexity_check` | Readability | Return to @codeCrafter |
| `naming_audit` | Conventions | Return to @codeCrafter |
| `performance_regression_check` | Efficiency | Return to @codeCrafter |
| `dependency_audit` | Security | Return to @codeCrafter |
| `testability_maintainability_audit` | Future-proofing | Return to @codeCrafter |
| `documentation_check` | Completeness | Return to @codeCrafter |

End signal: `Documentation check complete. Handing off to @qualityGuard.`

---

### @qualityGuard

Runs automatically on `Handing off to @qualityGuard`. A `SECURITY FAIL:` from any skill blocks the entire workflow.

**Skills (in order):**

| Skill | Purpose | WAF Pillar |
|---|---|---|
| `automated_threat_modeling` | STRIDE, IAM audit, encryption check | Security |
| `contract_testing_verification` | Pact consumer contracts, breaking payload detection | Reliability |
| `compliance_as_code_audit` | SOC 2 / PCI-DSS / GDPR, log retention, drift | Security |
| `write_unit_tests` | Jest, ≥80% branch coverage, aws-sdk-client-mock | — |
| `mock_aws_responses` | `__mocks__/aws.ts` typed barrel with realistic fixtures | — |
| `integration_test` | LocalStack end-to-end, DLQ flow, idempotency | Reliability |
| `chaos_engineering_simulation` | Failure injection, cascade prevention, RTO/RPO | Reliability |
| `performance_benchmark_gate` | Artillery SLO gate: P99 < 1000ms, error rate < 0.1% | Performance Efficiency |
| `penetration_scan` | Secret scan, OWASP Top 10, PII in logs, IDOR | Security |

End signal: `Quality gate cleared. Returning results to @techLead.`

**SLO failure:** `performance_benchmark_gate` SLO miss flags the issue to @architect for right-sizing. `penetration_scan` does not run until the benchmark gate clears.

---

### @devOps

Runs after `AUDIT_RESULT` passes. Never deploys to prod without a manual approval gate.

**Skills (in order):**

| Skill | Purpose | WAF Pillar |
|---|---|---|
| `pipeline_setup` | GitHub Actions CI/CD, OIDC auth, no long-lived keys | Operational Excellence |
| `deployment_strategy_engine` | Blue/Green or Canary selection, CodeDeploy wiring | Reliability |
| `finops_cost_governance` | Cost delta, idle-cost anti-patterns, tag compliance, budget gate | Cost Optimization |
| `observability_provisioning` | CloudWatch alarms/dashboards, X-Ray, log retention | Operational Excellence |
| `environment_promotion` | dev → staging → prod gates, canary routing | Reliability |
| `deployment_verification` | CloudWatch alarms green, DLQ=0, canary health | Operational Excellence |
| `automated_rollback_logic` | Trigger thresholds, alias/TG flip, Last Known Good state | Reliability |
| `drift_detection_audit` | CDK diff vs live, IAM/SG drift, tag compliance | Operational Excellence |
| `deployment_guide` | Human-executable guide *(MANUAL_DEPLOY_REQUESTED path only)* | — |

End signal: `Deployment verified. Returning to @techLead.`

---

## Signal Phrase Contract

Signal phrases are the **exact strings** LangGraph checks at node boundaries, and GitHub Copilot/Claude Code watches for in conversational handoffs. **Do not paraphrase them.**

### Inter-agent transitions

| Phrase | Routes to |
|---|---|
| `Cleared for implementation` | @codeCrafter |
| `Handing off to @codeReviewer` | @codeReviewer |
| `Documentation check complete. Handing off to @qualityGuard.` | @qualityGuard |
| `Quality gate cleared. Returning results to @techLead.` | @techLead (AUDIT_RESULT) |
| `GOVERNANCE_CHECK: PASS` | deployment approval gate |
| `RELEASE_AUTHORIZED` | @devOps (automated pipeline) |
| `MANUAL_DEPLOY_REQUESTED` | @devOps (generates `docs/deployment_guide.md`) |
| `DEPLOYMENT_GUIDE_READY` | **Pauses** — guide delivered to user |
| `Returning to @techLead` | @techLead (review and re-route) |
| `Deployment verified. Returning to @techLead.` | @techLead (final sign-off) |
| `SECURITY FAIL: [msg]` | **Blocks all work** |
| `REFACTOR_PROPOSAL: [file] \| [desc]` | **Pauses** — permission gate, user prompted Yes/No |

### Intra-agent chain signals

These advance the skill sequence within a single agent without crossing a node boundary:

```
Service boundary analysis complete  → observability_design
Observability design complete       → reliability_design
Reliability design complete         → disaster_recovery_strategy
Disaster recovery strategy complete → data_sovereignty_privacy
Data sovereignty review complete    → generate_cdk_boilerplate
Architecture records finalized      → return to @techLead

API contract defined                → add_dependencies
Secure coding baseline established  → implement_logic
Implementation complete for T-XXX   → resilience_patterns
Error handling strategy complete    → ui_component_generator (or resilience_patterns)
Resilience patterns complete        → performance_optimization
Performance optimization complete   → refactoring_refinement
Refactoring complete                → @codeReviewer

Architectural alignment audit passed → breaking_change_detection
Breaking change detection passed     → security_surface_analysis
Security surface analysis passed     → complexity_check
Complexity check passed              → naming_audit
Naming audit passed                  → performance_regression_check
Performance regression check passed  → dependency_audit
Dependency audit passed              → testability_maintainability_audit
Testability audit passed             → documentation_check

Threat modeling complete             → contract_testing_verification
Contract testing complete            → compliance_as_code_audit
Compliance audit complete            → write_unit_tests
Unit tests complete                  → mock_aws_responses
Mock responses complete              → integration_test
Integration tests complete           → chaos_engineering_simulation
Chaos simulation complete            → performance_benchmark_gate
Performance benchmark gate cleared   → penetration_scan

Pipeline configured                  → deployment_strategy_engine
Deployment strategy configured       → finops_cost_governance
Cost governance review complete      → observability_provisioning
Observability provisioned            → environment_promotion
Environment promotion complete       → deployment_verification
Deployment verified                  → automated_rollback_logic
Rollback logic verified              → drift_detection_audit
```

---

## Skill Reference

All skill files live in `prompts/skills/[agent]/`. Each file follows the same structure:

```
## ROLE & ACTIVATION
## INPUTS
## PROCESS
## OUTPUT CONTRACT   ← exact signal phrase(s) defined here
```

### @techLead (`prompts/skills/techLead/`)

`handoff_template.md` · `change_analysis.md` · `impact_assessment.md` · `system_prompt.md` · `governance_gatekeeper.md` · `deployment_approval_gate.md` · `audit_result.md` · `init_project.md` · `task_decomposition.md` · `agent_chain_selection.md` · `project_context_update.md` · `standards_enforcement.md`

### @architect (`prompts/skills/architect/`)

`service_boundary_analysis.md` · `observability_design.md` · `reliability_design.md` · `disaster_recovery_strategy.md` · `data_sovereignty_privacy.md` · `generate_cdk_boilerplate.md` · `security_group_audit.md` · `cost_estimation.md` · `legacy_integration_bridge.md` · `adr_generation.md`

### @codeCrafter (`prompts/skills/codeCrafter/`)

`api_contract_design.md` · `add_dependencies.md` · `secure_coding_standards.md` · `implement_logic.md` · `error_handling_strategy.md` · `ui_component_generator.md` · `resilience_patterns.md` · `performance_optimization.md` · `refactoring_refinement.md`

### @codeReviewer (`prompts/skills/codeReviewer/`)

`architectural_alignment_audit.md` · `breaking_change_detection.md` · `security_surface_analysis.md` · `complexity_check.md` · `naming_audit.md` · `performance_regression_check.md` · `dependency_audit.md` · `testability_maintainability_audit.md` · `documentation_check.md`

### @qualityGuard (`prompts/skills/qualityGuard/`)

`automated_threat_modeling.md` · `contract_testing_verification.md` · `compliance_as_code_audit.md` · `write_unit_tests.md` · `mock_aws_responses.md` · `integration_test.md` · `chaos_engineering_simulation.md` · `performance_benchmark_gate.md` · `penetration_scan.md`

### @devOps (`prompts/skills/devOps/`)

`pipeline_setup.md` · `deployment_strategy_engine.md` · `finops_cost_governance.md` · `observability_provisioning.md` · `environment_promotion.md` · `deployment_verification.md` · `automated_rollback_logic.md` · `drift_detection_audit.md` · `deployment_guide.md`

---

## Shared State Files

The `.github/shared/` directory is the single source of truth for all agents across all IDEs and sessions. Every agent reads `project_context.md` first before taking any action.

| File | Owner | Purpose |
|---|---|---|
| `project_context.md` | @techLead | Tech stack, directory structure, entry points, env vars, integration boundaries, known constraints, threat model. Created at `INIT_PROJECT`. |
| `project_state.md` | @techLead | Task board (`T-001`, ...), architecture snapshot, open risks, technical debt register, deployment history. |
| `architecture_log.md` | @architect | ADR ledger — one entry per architectural decision. Never delete entries. |
| `standards.md` | @techLead | Engineering law — all agents defer to this. §1 AWS/IaC · §2 Coding · §3 Testing · §4 Docs · §5 UI/UX · §6 Performance · §7 Agent Rules. |

Blank templates for these files are in `templates/` and are auto-injected into target repos by `src/orchestrator.py::inject_shared_templates()`.

---

## Adding a New Skill or Agent

### Add a skill to an existing agent

1. Create `prompts/skills/[agent]/[skill_name].md`
2. Follow the four-section structure: `ROLE & ACTIVATION` / `INPUTS` / `PROCESS` / `OUTPUT CONTRACT`
3. Define the exact end signal in `OUTPUT CONTRACT`
4. Add the signal to the routing tables in `.github/copilot-instructions.md` and `CLAUDE.md`
5. Wire the node in `src/nodes/[agent]_node.py` if the MCP server should call it

### Add a new agent

1. Create `prompts/agents/newAgent.agent.md`
2. Create `prompts/skills/newAgent/` with at least one skill file
3. Add the signal phrase(s) to the inter-agent routing table above
4. Add a routing section to `.github/copilot-instructions.md`
5. Add the agent to the Agent Directory in `CLAUDE.md` and `README.md`
6. Create `src/nodes/new_agent_node.py` and register it in `src/orchestrator.py::build_graph()`
7. Update `prompts/skills/techLead/system_prompt.md` Agent Directory

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Agent ignores a handoff phrase | Phrase was paraphrased | Copy the exact phrase from the OUTPUT CONTRACT |
| `SECURITY FAIL:` does not stop the chain | Missing colon in the phrase | Write `SECURITY FAIL: [description]` with the colon |
| `codeCrafter` loops — keeps re-running | `pending_refactor_proposal` not cleared | Call `resume_refactor_decision(thread_id, approved=False)` |
| MCP server not found in Cursor | Wrong path or `cwd` in `mcp.json` | Confirm `cwd` is the seagenthub directory and `args` points to `src/main.py` |
| Template injection skipped | `.github/shared/` already exists in target repo | Delete the directory to re-trigger injection |
| Tests fail in `qualityGuard` | No pytest in target repo | Add `pytest` to `requirements.txt` and re-run |
| Deployment skipped | `test_passed == False` | Fix failing tests; `devOps` will not run until tests pass |

