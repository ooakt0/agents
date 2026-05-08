# Multi-Agent Engineering Framework

This directory contains a portable, multi-agent AI orchestration framework for AWS/TypeScript
software development. Each agent folder contains skill files — structured prompts the AI follows
to perform a specialized role. Agents coordinate through exact signal phrases in their skill OUTPUT CONTRACTs.

Covers all 6 pillars of the **AWS Well-Architected Framework** and the full **SDLC**:
Design → Implement → Review → Test → Deploy → Verify.

## How to Use in a New Project

Copy these items to your project root:
```
.claude/settings.json           ← shared state config (auto-loaded by Claude Code)
.github/copilot-instructions.md ← agent routing for GitHub Copilot
CLAUDE.md                       ← this file (auto-loaded by Claude Code)
prompts/agents/                 ← agent persona files (* .agent.md)
prompts/skills/                 ← all agent skill files, organised by agent
templates/                      ← canonical .github/shared/ files (injected by MCP server)
src/                            ← MCP server source (main.py, orchestrator.py, nodes/)
.claude/skills/                 ← Claude Code skill descriptors
```

All paths inside skill files are relative — nothing is hardcoded to a specific project.

The MCP server (`src/main.py`) runs the pipeline using a **Step-and-Wait protocol**:
after each agent step it returns `proposed_changes` (files to write) and a
`next_agent_instruction`. The IDE must write those files to disk before calling
`advance_pipeline` — if files are missing the server returns `WAITING_FOR_FILES`
and refuses to proceed. Session state persists in `{project_path}/.seahub/session.json`
so the TechLead reads it before every agent call to resume where it left off.

The MCP server also automatically injects the files in `templates/` into a target
repository's `.github/shared/` directory the first time it processes that repo,
so agents have a correctly structured `project_context.md`, `project_state.md`,
`standards.md`, and `architecture_log.md` without any manual setup.

---

## Agent Directory

| Agent | Folder | Activated By | WAF Pillars |
|-------|--------|-------------|------------|
| @techLead | `prompts/skills/techLead/` | User command | All (orchestration) |
| @architect | `prompts/skills/architect/` | `DELEGATE [architect]` | Operational Excellence, Security, Reliability, Cost |
| @codeCrafter | `prompts/skills/codeCrafter/` | `DELEGATE [codeCrafter]` | Reliability, Performance |
| @codeReviewer | `prompts/skills/codeReviewer/` | @codeCrafter handoff | Security, Operational Excellence |
| @qualityGuard | `prompts/skills/qualityGuard/` | @codeReviewer handoff | Reliability, Security, Performance |
| @devOps | `prompts/skills/devOps/` | `DELEGATE [devOps]` | Operational Excellence, Reliability |

---

## Full Workflow (SDLC + Well-Architected)

```
User
 └─▶ @techLead: INIT_PROJECT — decompose goal into tasks T-001, T-002, ...
       │
       ├─▶ @architect: DESIGN PHASE
       │     ├─ service_boundary_analysis  (Domain — is this the right service? anti-coupling)
       │     ├─ observability_design       (Operational Excellence — metrics, logs, traces)
       │     ├─ reliability_design         (Reliability — failure modes, RTO/RPO, DLQ config)
       │     ├─ disaster_recovery_strategy (Resilience — RTO/RPO, multi-region, PITR, runbook)
       │     ├─ data_sovereignty_privacy   (Compliance — PII isolation, residency, retention)
       │     ├─ generate_cdk_boilerplate   (IaC — tagged, private subnets, env-aware)
       │     ├─ security_group_audit       (Security — IAM, networking, encryption)
       │     ├─ cost_estimation            (Cost — Dev vs Prod sizing, idle-cost anti-patterns)
       │     ├─ legacy_integration_bridge  (Migration — Adapter/Facade/ACL for existing systems)
       │     └─ adr_generation            (Decision Authority — formal ADR for every key choice)
       │          └─▶ @techLead: approve ADRs → "Cleared for implementation"
       │
       ├─▶ @codeCrafter: IMPLEMENTATION PHASE
       │     ├─ api_contract_design     (OpenAPI/TypeScript interfaces, StandardErrorResponse)
       │     ├─ add_dependencies        (audit for CVEs, licenses, bundle size)
       │     ├─ secure_coding_standards (input validation, injection prevention, OWASP shift-left)
       │     ├─ implement_logic         (TypeScript strict, ≤30 lines/fn, custom errors)
       │     ├─ error_handling_strategy (domain error hierarchy, central handler, safe messages)
       │     ├─ ui_component_generator  (Atomic Design, Tailwind, ARIA — if UI task)
       │     ├─ resilience_patterns     (retry backoff, idempotency, DLQ wiring, timeouts)
       │     ├─ performance_optimization (N+1 fix, pagination, caching, cold start mitigation)
       │     └─ refactoring_refinement  (DRY, SOLID, code smells, design patterns, naming)
       │          └─▶ @codeReviewer: "Handing off to @codeReviewer"
       │
       ├─▶ @codeReviewer: REVIEW PHASE
       │     ├─ architectural_alignment_audit  (ADR conformance, service boundaries)
       │     ├─ breaking_change_detection      (interfaces, API payloads, schemas, events)
       │     ├─ security_surface_analysis      (authz gaps, PII logs, IAM, injection, secrets)
       │     ├─ complexity_check               (functions ≤30 lines, nesting ≤3 deep)
       │     ├─ naming_audit                   (PascalCase/camelCase/UPPER_SNAKE_CASE enforced)
       │     ├─ performance_regression_check   (N+1, unbounded queries, hot-path allocs)
       │     ├─ dependency_audit               (staleness, CVE rescan, license drift)
       │     ├─ testability_maintainability_audit (hardcoded deps, monolithic fns, interfaces)
       │     └─ documentation_check            (README, .env.example, no TODO/FIXME)
       │          └─▶ @qualityGuard: "Handing off to @qualityGuard"
       │
       ├─▶ @qualityGuard: QUALITY PHASE
       │     ├─ automated_threat_modeling     (STRIDE, IAM audit, encryption check)
       │     ├─ contract_testing_verification (Pact consumer contracts, breaking change guard)
       │     ├─ compliance_as_code_audit      (SOC 2, PCI-DSS, GDPR checklists, log retention)
       │     ├─ write_unit_tests              (Jest, ≥80% branch coverage, aws-sdk-client-mock)
       │     ├─ mock_aws_responses            (__mocks__/aws.ts barrel with realistic fixtures)
       │     ├─ integration_test              (LocalStack end-to-end, DLQ flow, idempotency)
       │     ├─ chaos_engineering_simulation  (failure injection, cascade prevention, RTO/RPO)
       │     ├─ performance_benchmark_gate    (Artillery SLO gate, P99 regression, cold start)
       │     └─ penetration_scan             (secret scan, OWASP, PII in logs, IDOR)
       │          └─▶ @techLead: "Quality gate cleared" → AUDIT_RESULT → governance_gatekeeper
       │                    │
       │                    └─▶ HUMAN APPROVAL GATE (deployment_approval_gate)
       │                          ├─ [Approve] → RELEASE_AUTHORIZED
       │                          └─ [Manual]  → MANUAL_DEPLOY_REQUESTED → @devOps generates docs/deployment_guide.md → DEPLOYMENT_GUIDE_READY
       │
       └─▶ @devOps: DEPLOYMENT PHASE  ← entered only on RELEASE_AUTHORIZED
             ├─ pipeline_setup               (GitHub Actions, OIDC, no long-lived keys)
             ├─ deployment_strategy_engine   (Blue/Green or Canary, warm-state preservation)
             ├─ finops_cost_governance       (cost delta, idle-cost anti-patterns, budget gate)
             ├─ observability_provisioning   (CloudWatch alarms/dashboards, X-Ray, log retention)
             ├─ environment_promotion        (dev→staging→prod gates, canary routing)
             ├─ deployment_verification      (CloudWatch alarms, DLQ=0, canary health)
             ├─ automated_rollback_logic     (trigger thresholds, alias/TG flip, Last Known Good)
             └─ drift_detection_audit        (CDK diff vs live, IAM/SG/tag drift, IaC enforcement)
                  └─▶ @techLead: "Deployment verified" → present to User
```

No step may be skipped. Every agent hands off using exact signal phrases written verbatim in each skill's OUTPUT CONTRACT.

---

## How to Start a Task

```
@techLead INIT_PROJECT: [describe your goal here]
```

@techLead will read `.github/shared/project_state.md`, break the goal into atomic tasks, update the
Task Board, and begin delegating using `prompts/skills/techLead/handoff_template.md`.

---

## Shared Files

| File | Owner | Purpose |
|------|-------|---------|
| `.github/shared/project_context.md` | @techLead | **READ FIRST by all agents.** Tech stack, directory structure, entry points, env vars, integration boundaries, known constraints, recent changes. Created at INIT_PROJECT. Updated after every agent step. |
| `.github/shared/standards.md` | @techLead | The law. All agents defer to this. Do not modify without consensus. |
| `.github/shared/project_state.md` | @techLead | Living task board. Read before every action. Update after every handoff. |
| `.github/shared/architecture_log.md` | @architect | ADR ledger. Every design decision recorded here. |
| `prompts/skills/techLead/handoff_template.md` | @techLead | Required for every DELEGATE command. |
| `.seahub/session.json` | MCP server | **Step-and-Wait session state.** Written by `src/pipeline.py` after every step. Stores `session_id`, `completed_agents`, and `pending_verification_paths`. Read before every agent call so TechLead knows where it left off. |

**Source templates** (used by the MCP server to initialise `.github/shared/` in new repos):

| Template | Injected to |
|---|---|
| `templates/project_context.md` | `.github/shared/project_context.md` |
| `templates/project_state.md` | `.github/shared/project_state.md` |
| `templates/standards.md` | `.github/shared/standards.md` |
| `templates/architecture_log.md` | `.github/shared/architecture_log.md` |

---

## Signal Routing (LangGraph)

Signal phrases are evaluated deterministically by the LangGraph state machine in `src/orchestrator.py`.
When using the MCP server (`src/main.py`), no hook scripts are required — the graph advances
automatically when a node emits the correct signal phrase. When using prompt-driven agents in an
IDE (Copilot, Claude Code), the same phrases drive the conversational handoff.

### Step-and-Wait Protocol (MCP server)

The MCP server enforces a **Step-and-Wait** loop between each agent:

```
IDE calls techLead(project_path, task)
  → architect runs → STEP_COMPLETE returned
  → IDE writes proposed_changes to disk
  → IDE calls advance_pipeline(continuation_token)
      → pipeline.py reads .seahub/session.json
      → pipeline.py reads .github/shared/project_context.md
      → verifies pending_verification_paths exist on disk
      → if missing: returns WAITING_FOR_FILES (no state change; retry after writing files)
      → if present: next agent runs → STEP_COMPLETE returned
  → repeat until is_task_complete=true
```

**Response fields** present on every tool call:

| Field | Description |
|---|---|
| `status` | `STEP_COMPLETE` \| `WAITING_FOR_FILES` \| `PIPELINE_PAUSED` \| `PIPELINE_COMPLETE` \| `DEPLOYMENT_GUIDE_READY` |
| `session_id` | Stable identifier written to `.seahub/session.json` |
| `continuation_token` | Pass to `advance_pipeline` (same value as `session_id`) |
| `proposed_changes` | Files the IDE must write to disk before the next call |
| `next_agent_instruction` | Exact instruction for what to do after writing the files |
| `is_task_complete` | `true` only on `PIPELINE_COMPLETE` — signals the full SDLC is done |
| `requires_approval` | `true` before `qualityGuard` — confirm with user before advancing |

**WAITING_FOR_FILES** is returned (and the pipeline does NOT advance) when any file from the
previous `proposed_changes` does not exist on disk. The `missing_files` field lists exactly
which paths must be written before calling `advance_pipeline` again.

### Signal Phrase Contract

Hooks scan for these **exact phrases**. Agents must not paraphrase them:

| Phrase (inter-agent) | Routes to |
|---|---|
| `Handing off to @codeReviewer` | @codeReviewer (architectural_alignment_audit) |
| `Handing off to @qualityGuard` | @qualityGuard (write_unit_tests) |
| `Quality gate cleared` | @techLead (AUDIT_RESULT → governance_gatekeeper) |
| `GOVERNANCE_CHECK: PASS` | @techLead (deployment_approval_gate — user prompted Approve/Manual) |
| `RELEASE_AUTHORIZED` | @devOps (pipeline_setup — full automated deployment) |
| `MANUAL_DEPLOY_REQUESTED` | @devOps (deployment_guide — generates `docs/deployment_guide.md`) |
| `DEPLOYMENT_GUIDE_READY` | **Pauses workflow** — guide delivered to user; no automated deploy |
| `Returning to @techLead` | @techLead (review and decide) |
| `Cleared for implementation` | @codeCrafter (implement_logic) |
| `SECURITY FAIL: [msg]` | **Blocks workflow** (hook exits 2) |
| `REFACTOR_PROPOSAL: [file] \| [desc]` | **Pauses workflow** — supervisor routes to permission gate; user prompted Yes/No |

| Phrase (intra-agent chain) | Reminds next skill |
|---|---|
| `Service boundary analysis complete` | activate observability_design |
| `Observability design complete` | activate reliability_design |
| `Reliability design complete` | activate disaster_recovery_strategy |
| `Disaster recovery strategy complete` | activate data_sovereignty_privacy |
| `Data sovereignty review complete` | activate generate_cdk_boilerplate |
| `Legacy integration bridge complete` | activate adr_generation (or return to @techLead) |
| `Architecture records finalized` | returning to @techLead |
| `API contract defined` | activate add_dependencies |
| `Secure coding baseline established` | activate implement_logic |
| `Error handling strategy complete` | activate ui_component_generator or resilience_patterns |
| `Resilience patterns complete` | activate performance_optimization |
| `Performance optimization complete` | activate refactoring_refinement |
| `Refactoring complete` | hand off to @codeReviewer |
| `Architectural alignment audit passed` | activate breaking_change_detection |
| `Breaking change detection passed` | activate security_surface_analysis |
| `Security surface analysis passed` | activate complexity_check |
| `Complexity check passed` | activate naming_audit |
| `Naming audit passed` | activate performance_regression_check |
| `Performance regression check passed` | activate dependency_audit |
| `Dependency audit passed` | activate testability_maintainability_audit |
| `Testability audit passed` | activate documentation_check |
| `Threat modeling complete` | activate contract_testing_verification |
| `Contract testing complete` | activate compliance_as_code_audit |
| `Compliance audit complete` | activate write_unit_tests |
| `Unit tests complete` | activate mock_aws_responses |
| `Mock responses complete` | activate integration_test |
| `Integration tests complete` | activate chaos_engineering_simulation |
| `Chaos simulation complete` | activate performance_benchmark_gate |
| `Performance benchmark gate cleared` | activate penetration_scan |
| `Activating deployment_approval_gate` | activate deployment_approval_gate (user approval prompt) |
| `Pipeline configured` | activate deployment_strategy_engine |
| `Deployment strategy configured` | activate finops_cost_governance |
| `Cost governance review complete` | activate observability_provisioning |
| `Observability provisioned` | activate environment_promotion |
| `Environment promotion complete` | activate deployment_verification |
| `Deployment verified` | activate automated_rollback_logic |
| `Rollback logic verified` | activate drift_detection_audit |

---

## Agent Skills Quick Reference

### @architect (Design Phase) — execution order
- `prompts/skills/architect/service_boundary_analysis.md` — Domain boundaries, coupling check, async decoupling *(WAF: Operational Excellence)*
- `prompts/skills/architect/observability_design.md` — CloudWatch alarms, structured logs, X-Ray tracing *(WAF: Operational Excellence)*
- `prompts/skills/architect/reliability_design.md` — Failure modes, RTO/RPO, DLQ config, Multi-AZ *(WAF: Reliability)*
- `prompts/skills/architect/disaster_recovery_strategy.md` — Multi-region failover, PITR, circuit breakers, DR runbook *(WAF: Reliability)*
- `prompts/skills/architect/data_sovereignty_privacy.md` — PII isolation, data residency, retention, CMK encryption *(WAF: Security)*
- `prompts/skills/architect/generate_cdk_boilerplate.md` — CDK v2 TypeScript stacks, tagging, private subnets
- `prompts/skills/architect/security_group_audit.md` — IAM least privilege, encryption, networking *(WAF: Security)*
- `prompts/skills/architect/cost_estimation.md` — Dev vs Prod sizing, idle-cost anti-patterns *(WAF: Cost)*
- `prompts/skills/architect/legacy_integration_bridge.md` — Adapter/Facade/ACL patterns, resilience wrapping, data mapping *(WAF: Reliability)*
- `prompts/skills/architect/adr_generation.md` — Formal ADR per decision, alternatives evaluated, reversibility rated *(WAF: Operational Excellence)*

### @codeCrafter (Implementation Phase) — execution order
- `prompts/skills/codeCrafter/api_contract_design.md` — TypeScript interfaces, endpoint specs, StandardErrorResponse *(WAF: Operational Excellence)*
- `prompts/skills/codeCrafter/add_dependencies.md` — CVE audit, license check, exact version pinning
- `prompts/skills/codeCrafter/secure_coding_standards.md` — Input validation (Zod/Pydantic), injection prevention, OWASP shift-left *(WAF: Security)*
- `prompts/skills/codeCrafter/implement_logic.md` — TypeScript strict, ≤30 lines/fn, custom error classes
- `prompts/skills/codeCrafter/error_handling_strategy.md` — Domain error hierarchy, central handler, safe error messages *(WAF: Reliability)*
- `prompts/skills/codeCrafter/ui_component_generator.md` — Atomic Design, Tailwind, ARIA accessibility *(if UI task)*
- `prompts/skills/codeCrafter/resilience_patterns.md` — Retry backoff, idempotency, DLQ wiring *(WAF: Reliability)*
- `prompts/skills/codeCrafter/performance_optimization.md` — N+1 fix, pagination, caching, Lambda cold start *(WAF: Performance Efficiency)*
- `prompts/skills/codeCrafter/refactoring_refinement.md` — DRY, SOLID, code smells, design patterns, naming *(WAF: Operational Excellence)*

### @codeReviewer (Review Phase) — execution order
- `prompts/skills/codeReviewer/architectural_alignment_audit.md` — ADR conformance, service boundary enforcement, undocumented decisions *(WAF: Operational Excellence)*
- `prompts/skills/codeReviewer/breaking_change_detection.md` — Exported interface diffs, API payload changes, schema migrations, event contract changes *(WAF: Reliability)*
- `prompts/skills/codeReviewer/security_surface_analysis.md` — Authorization gaps, PII in logs, IAM least privilege, injection surface, secrets *(WAF: Security)*
- `prompts/skills/codeReviewer/complexity_check.md` — Function size, nesting depth, promise chains
- `prompts/skills/codeReviewer/naming_audit.md` — PascalCase / camelCase / UPPER_SNAKE_CASE enforcement
- `prompts/skills/codeReviewer/performance_regression_check.md` — N+1 queries, unbounded results, hot-path allocations, Lambda cold start, cache misses *(WAF: Performance Efficiency)*
- `prompts/skills/codeReviewer/dependency_audit.md` — Staleness, CVE rescan, GPL license drift *(WAF: Security)*
- `prompts/skills/codeReviewer/testability_maintainability_audit.md` — Hardcoded deps, static I/O, monolithic functions, interface coverage, fixture burden *(WAF: Operational Excellence)*
- `prompts/skills/codeReviewer/documentation_check.md` — README, .env.example, no TODO/FIXME *(WAF: Operational Excellence)*

### @qualityGuard (Quality Phase) — execution order
- `prompts/skills/qualityGuard/automated_threat_modeling.md` — STRIDE analysis, IAM least-privilege audit, encryption check *(WAF: Security)*
- `prompts/skills/qualityGuard/contract_testing_verification.md` — Pact consumer-driven contracts, breaking payload detection *(WAF: Reliability)*
- `prompts/skills/qualityGuard/compliance_as_code_audit.md` — SOC 2 / PCI-DSS / GDPR checklists, log retention, drift check *(WAF: Security)*
- `prompts/skills/qualityGuard/write_unit_tests.md` — Jest, ≥80% branch coverage, aws-sdk-client-mock
- `prompts/skills/qualityGuard/mock_aws_responses.md` — Typed mock barrel with realistic data
- `prompts/skills/qualityGuard/integration_test.md` — LocalStack end-to-end, DLQ flow, idempotency *(WAF: Reliability)*
- `prompts/skills/qualityGuard/chaos_engineering_simulation.md` — Failure injection, cascade prevention, RTO/RPO assertion *(WAF: Reliability)*
- `prompts/skills/qualityGuard/performance_benchmark_gate.md` — Artillery SLO gate, P99 regression detection, cold start check *(WAF: Performance Efficiency)*
- `prompts/skills/qualityGuard/penetration_scan.md` — Secret scan, OWASP Top 10, PII in logs *(WAF: Security)*

### @devOps (Deployment Phase) — execution order
- `prompts/skills/devOps/pipeline_setup.md` — GitHub Actions CI/CD, OIDC auth, no long-lived keys *(WAF: Operational Excellence)*
- `prompts/skills/devOps/deployment_strategy_engine.md` — Blue/Green or Canary selection, warm-state preservation, CodeDeploy wiring *(WAF: Reliability)*
- `prompts/skills/devOps/finops_cost_governance.md` — Cost delta estimation, idle-cost anti-patterns, tag compliance, budget gate *(WAF: Cost Optimization)*
- `prompts/skills/devOps/observability_provisioning.md` — CloudWatch alarms/dashboards, X-Ray tracing, log retention *(WAF: Operational Excellence)*
- `prompts/skills/devOps/environment_promotion.md` — dev→staging→prod gates, canary routing, rollback strategy *(WAF: Reliability)*
- `prompts/skills/devOps/deployment_verification.md` — CloudWatch alarm check, DLQ=0, canary health *(WAF: Operational Excellence)*
- `prompts/skills/devOps/automated_rollback_logic.md` — Trigger thresholds, alias/TG flip, git revert, Last Known Good state *(WAF: Reliability)*
- `prompts/skills/devOps/drift_detection_audit.md` — CDK diff vs live, IAM/SG drift, tag compliance, IaC enforcement *(WAF: Operational Excellence)*
- `prompts/skills/devOps/deployment_guide.md` — Human-executable guide with exact CDK/CLI commands, verification steps, rollback plan *(MANUAL_DEPLOY_REQUESTED path)*

---

## Portability Notes

- All skill files use root-relative paths (`prompts/skills/[agent]/[skill].md`) — no absolute paths
- `project_state.md` and `architecture_log.md` are templates — fill `[placeholders]` during INIT_PROJECT
- `templates/` files are auto-injected into `.github/shared/` in target repos by `src/orchestrator.py::inject_shared_templates()`
- Session state is written to `{project_path}/.seahub/session.json` by `src/pipeline.py` — do not delete this file mid-pipeline
- `proposed_changes` uses forward-slash paths relative to `project_path`; `src/pipeline.py` resolves them with `pathlib.Path` for cross-platform compatibility

---

## Adding a New Agent

1. Create persona file: `prompts/agents/newAgent.agent.md`
2. Create skill folder: `prompts/skills/newAgent/`
3. Add skill files: `ROLE & ACTIVATION` / `INPUTS` / `PROCESS` / `OUTPUT CONTRACT`
4. Define exact signal phrase(s) in OUTPUT CONTRACT
5. Add agent to the Agent Directory table and workflow diagram in this file
6. Add routing section to `.github/copilot-instructions.md`
7. Update `prompts/skills/techLead/system_prompt.md` Agent Directory
