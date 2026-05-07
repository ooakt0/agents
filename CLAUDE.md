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
.github/shared/                 ← state files and standards
.github/agents/                 ← GitHub Copilot agent personas
.github/skills/                 ← all agent skill files
.claude/skills/                 ← Claude Code skill descriptors
```

All paths inside skill files are relative — nothing is hardcoded to a specific project.

---

## Agent Directory

| Agent | Folder | Activated By | WAF Pillars |
|-------|--------|-------------|------------|
| @techLead | `.github/skills/techLead/` | User command | All (orchestration) |
| @architect | `.github/skills/architect/` | `DELEGATE [architect]` | Operational Excellence, Security, Reliability, Cost |
| @codeCrafter | `.github/skills/codeCrafter/` | `DELEGATE [codeCrafter]` | Reliability, Performance |
| @codeReviewer | `.github/skills/codeReviewer/` | @codeCrafter handoff | Security, Operational Excellence |
| @qualityGuard | `.github/skills/qualityGuard/` | @codeReviewer handoff | Reliability, Security, Performance |
| @devOps | `.github/skills/devOps/` | `DELEGATE [devOps]` | Operational Excellence, Reliability |

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
       │          └─▶ @techLead: "Quality gate cleared" → AUDIT_RESULT
       │
       └─▶ @devOps: DEPLOYMENT PHASE
             ├─ pipeline_setup          (GitHub Actions, OIDC, no long-lived keys)
             ├─ environment_promotion   (dev→staging→prod gates, canary routing, rollback)
             └─ deployment_verification (CloudWatch alarms, DLQ=0, canary health)
                  └─▶ @techLead: "Deployment verified" → present to User
```

No step may be skipped. Every agent hands off using exact signal phrases written verbatim in each skill's OUTPUT CONTRACT.

---

## How to Start a Task

```
@techLead INIT_PROJECT: [describe your goal here]
```

@techLead will read `.github/shared/project_state.md`, break the goal into atomic tasks, update the
Task Board, and begin delegating using `.github/skills/techLead/handoff_template.md`.

---

## Shared Files

| File | Owner | Purpose |
|------|-------|---------|
| `.github/shared/project_context.md` | @techLead | **READ FIRST by all agents.** Tech stack, directory structure, entry points, env vars, integration boundaries, known constraints, recent changes. Created at INIT_PROJECT. |
| `.github/shared/standards.md` | @techLead | The law. All agents defer to this. Do not modify without consensus. |
| `.github/shared/project_state.md` | @techLead | Living task board. Read before every action. Update after every handoff. |
| `.github/shared/architecture_log.md` | @architect | ADR ledger. Every design decision recorded here. |
| `.github/skills/techLead/handoff_template.md` | @techLead | Required for every DELEGATE command. |

---

## Hook Behavior (Automatic)

| Hook | Script | Trigger |
|------|--------|---------|
| PostToolUse (Write/Edit) | `.github/hooks/on_write.ps1` | Routes between agents on signal phrase detection |
| PostToolUse (Write) | `.github/hooks/on_task_complete.ps1` | Outputs full DoD checklist when ✅ DONE appears in project_state.md |
| Stop | `.github/hooks/on_stop.ps1` | Reminds about open 🏗️ ACTIVE tasks at session end |

### Signal Phrase Contract

Hooks scan for these **exact phrases**. Agents must not paraphrase them:

| Phrase (inter-agent) | Routes to |
|---|---|
| `Handing off to @codeReviewer` | @codeReviewer (architectural_alignment_audit) |
| `Handing off to @qualityGuard` | @qualityGuard (write_unit_tests) |
| `Handing off to @devOps` | @devOps (pipeline_setup) |
| `Quality gate cleared` | @techLead (AUDIT_RESULT → delegate devOps) |
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
| `Pipeline configured` | activate environment_promotion |
| `Environment promotion complete` | activate deployment_verification |

---

## Agent Skills Quick Reference

### @architect (Design Phase) — execution order
- `.github/skills/architect/service_boundary_analysis.md` — Domain boundaries, coupling check, async decoupling *(WAF: Operational Excellence)*
- `.github/skills/architect/observability_design.md` — CloudWatch alarms, structured logs, X-Ray tracing *(WAF: Operational Excellence)*
- `.github/skills/architect/reliability_design.md` — Failure modes, RTO/RPO, DLQ config, Multi-AZ *(WAF: Reliability)*
- `.github/skills/architect/disaster_recovery_strategy.md` — Multi-region failover, PITR, circuit breakers, DR runbook *(WAF: Reliability)*
- `.github/skills/architect/data_sovereignty_privacy.md` — PII isolation, data residency, retention, CMK encryption *(WAF: Security)*
- `.github/skills/architect/generate_cdk_boilerplate.md` — CDK v2 TypeScript stacks, tagging, private subnets
- `.github/skills/architect/security_group_audit.md` — IAM least privilege, encryption, networking *(WAF: Security)*
- `.github/skills/architect/cost_estimation.md` — Dev vs Prod sizing, idle-cost anti-patterns *(WAF: Cost)*
- `.github/skills/architect/legacy_integration_bridge.md` — Adapter/Facade/ACL patterns, resilience wrapping, data mapping *(WAF: Reliability)*
- `.github/skills/architect/adr_generation.md` — Formal ADR per decision, alternatives evaluated, reversibility rated *(WAF: Operational Excellence)*

### @codeCrafter (Implementation Phase) — execution order
- `.github/skills/codeCrafter/api_contract_design.md` — TypeScript interfaces, endpoint specs, StandardErrorResponse *(WAF: Operational Excellence)*
- `.github/skills/codeCrafter/add_dependencies.md` — CVE audit, license check, exact version pinning
- `.github/skills/codeCrafter/secure_coding_standards.md` — Input validation (Zod/Pydantic), injection prevention, OWASP shift-left *(WAF: Security)*
- `.github/skills/codeCrafter/implement_logic.md` — TypeScript strict, ≤30 lines/fn, custom error classes
- `.github/skills/codeCrafter/error_handling_strategy.md` — Domain error hierarchy, central handler, safe error messages *(WAF: Reliability)*
- `.github/skills/codeCrafter/ui_component_generator.md` — Atomic Design, Tailwind, ARIA accessibility *(if UI task)*
- `.github/skills/codeCrafter/resilience_patterns.md` — Retry backoff, idempotency, DLQ wiring *(WAF: Reliability)*
- `.github/skills/codeCrafter/performance_optimization.md` — N+1 fix, pagination, caching, Lambda cold start *(WAF: Performance Efficiency)*
- `.github/skills/codeCrafter/refactoring_refinement.md` — DRY, SOLID, code smells, design patterns, naming *(WAF: Operational Excellence)*

### @codeReviewer (Review Phase) — execution order
- `.github/skills/codeReviewer/architectural_alignment_audit.md` — ADR conformance, service boundary enforcement, undocumented decisions *(WAF: Operational Excellence)*
- `.github/skills/codeReviewer/breaking_change_detection.md` — Exported interface diffs, API payload changes, schema migrations, event contract changes *(WAF: Reliability)*
- `.github/skills/codeReviewer/security_surface_analysis.md` — Authorization gaps, PII in logs, IAM least privilege, injection surface, secrets *(WAF: Security)*
- `.github/skills/codeReviewer/complexity_check.md` — Function size, nesting depth, promise chains
- `.github/skills/codeReviewer/naming_audit.md` — PascalCase / camelCase / UPPER_SNAKE_CASE enforcement
- `.github/skills/codeReviewer/performance_regression_check.md` — N+1 queries, unbounded results, hot-path allocations, Lambda cold start, cache misses *(WAF: Performance Efficiency)*
- `.github/skills/codeReviewer/dependency_audit.md` — Staleness, CVE rescan, GPL license drift *(WAF: Security)*
- `.github/skills/codeReviewer/testability_maintainability_audit.md` — Hardcoded deps, static I/O, monolithic functions, interface coverage, fixture burden *(WAF: Operational Excellence)*
- `.github/skills/codeReviewer/documentation_check.md` — README, .env.example, no TODO/FIXME *(WAF: Operational Excellence)*

### @qualityGuard (Quality Phase) — execution order
- `.github/skills/qualityGuard/automated_threat_modeling.md` — STRIDE analysis, IAM least-privilege audit, encryption check *(WAF: Security)*
- `.github/skills/qualityGuard/contract_testing_verification.md` — Pact consumer-driven contracts, breaking payload detection *(WAF: Reliability)*
- `.github/skills/qualityGuard/compliance_as_code_audit.md` — SOC 2 / PCI-DSS / GDPR checklists, log retention, drift check *(WAF: Security)*
- `.github/skills/qualityGuard/write_unit_tests.md` — Jest, ≥80% branch coverage, aws-sdk-client-mock
- `.github/skills/qualityGuard/mock_aws_responses.md` — Typed mock barrel with realistic data
- `.github/skills/qualityGuard/integration_test.md` — LocalStack end-to-end, DLQ flow, idempotency *(WAF: Reliability)*
- `.github/skills/qualityGuard/chaos_engineering_simulation.md` — Failure injection, cascade prevention, RTO/RPO assertion *(WAF: Reliability)*
- `.github/skills/qualityGuard/performance_benchmark_gate.md` — Artillery SLO gate, P99 regression detection, cold start check *(WAF: Performance Efficiency)*
- `.github/skills/qualityGuard/penetration_scan.md` — Secret scan, OWASP Top 10, PII in logs *(WAF: Security)*

### @devOps (Deployment Phase)
- `.github/skills/devOps/pipeline_setup.md` — GitHub Actions CI/CD, OIDC auth, no long-lived keys *(WAF: Operational Excellence)*
- `.github/skills/devOps/environment_promotion.md` — dev→staging→prod gates, canary routing, rollback strategy *(WAF: Reliability)*
- `.github/skills/devOps/deployment_verification.md` — CloudWatch alarm check, DLQ=0, canary health *(WAF: Operational Excellence)*

---

## Portability Notes

- All skill files use root-relative paths (`.github/skills/[agent]/[skill].md`) — no absolute paths
- `project_state.md` and `architecture_log.md` are templates — fill `[placeholders]` during INIT_PROJECT

**Legacy path note:** Older files reference `AGENTS/` prefix. Treat `AGENTS/shared/foo.md`
as equivalent to `.github/shared/foo.md` — the prefix is a legacy convention.

---

## Adding a New Agent

1. Create a new folder: `newAgent/`
2. Add skill files: `ROLE & ACTIVATION` / `INPUTS` / `PROCESS` / `OUTPUT CONTRACT`
3. Define exact signal phrase(s) in OUTPUT CONTRACT
4. Add agent to the Agent Directory table and workflow diagram in this file
5. Add routing section to `.github/copilot-instructions.md`
6. Update `.github/skills/techLead/system_prompt.md` Agent Directory
