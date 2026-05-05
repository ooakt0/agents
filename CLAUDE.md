# Multi-Agent Engineering Framework

This directory contains a portable, multi-agent AI orchestration framework for AWS/TypeScript
software development. Each agent folder contains skill files — structured prompts the AI follows
to perform a specialized role. Claude Code hooks wire agents together automatically.

Covers all 6 pillars of the **AWS Well-Architected Framework** and the full **SDLC**:
Design → Implement → Review → Test → Deploy → Verify.

## How to Use in a New Project

Copy these items to your project root:
```
.claude/settings.json           ← hooks configuration (auto-loaded by Claude Code)
.github/copilot-instructions.md ← agent routing for GitHub Copilot
CLAUDE.md                       ← this file (auto-loaded by Claude Code)
.github/hooks/                  ← hook scripts (wires agent-to-agent routing)
.github/shared/                 ← state files and standards
.github/agents/                 ← GitHub Copilot agent personas
.github/skills/                 ← all agent skill files
.claude/skills/                 ← Claude Code skill descriptors
```

All paths inside skill files and hooks are relative — nothing is hardcoded to a specific project.

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
       │     ├─ observability_design    (Operational Excellence — metrics, logs, traces)
       │     ├─ reliability_design      (Reliability — failure modes, RTO/RPO, DLQ config)
       │     ├─ generate_cdk_boilerplate (IaC — tagged, private subnets, env-aware)
       │     ├─ security_group_audit    (Security — IAM, networking, encryption)
       │     └─ cost_estimation         (Cost — Dev vs Prod sizing, idle-cost anti-patterns)
       │          └─▶ @techLead: approve ADRs → "Cleared for implementation"
       │
       ├─▶ @codeCrafter: IMPLEMENTATION PHASE
       │     ├─ add_dependencies        (audit for CVEs, licenses, bundle size)
       │     ├─ implement_logic         (TypeScript strict, ≤30 lines/fn, custom errors)
       │     ├─ ui_component_generator  (Atomic Design, Tailwind, ARIA — if UI task)
       │     └─ resilience_patterns     (retry backoff, idempotency, DLQ wiring, timeouts)
       │          └─▶ @codeReviewer: "Handing off to @codeReviewer"
       │
       ├─▶ @codeReviewer: REVIEW PHASE
       │     ├─ complexity_check        (functions ≤30 lines, nesting ≤3 deep)
       │     ├─ naming_audit            (PascalCase/camelCase/UPPER_SNAKE_CASE enforced)
       │     ├─ dependency_audit        (staleness, CVE rescan, license drift)
       │     └─ documentation_check     (README, .env.example, no TODO/FIXME)
       │          └─▶ @qualityGuard: "Handing off to @qualityGuard"
       │
       ├─▶ @qualityGuard: QUALITY PHASE
       │     ├─ write_unit_tests        (Jest, ≥80% branch coverage, aws-sdk-client-mock)
       │     ├─ mock_aws_responses      (__mocks__/aws.ts barrel with realistic fixtures)
       │     ├─ integration_test        (LocalStack end-to-end, DLQ flow, idempotency)
       │     ├─ load_test               (Artillery, P99 SLOs, DLQ depth under load)
       │     └─ penetration_scan        (secret scan, OWASP, PII in logs, IDOR)
       │          └─▶ @techLead: "Quality gate cleared" → AUDIT_RESULT
       │
       └─▶ @devOps: DEPLOYMENT PHASE
             ├─ pipeline_setup          (GitHub Actions, OIDC, no long-lived keys)
             ├─ environment_promotion   (dev→staging→prod gates, canary routing, rollback)
             └─ deployment_verification (CloudWatch alarms, DLQ=0, canary health)
                  └─▶ @techLead: "Deployment verified" → present to User
```

No step may be skipped. Every agent hands off using exact signal phrases that the hooks layer
detects and routes automatically.

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
| `Handing off to @codeReviewer` | @codeReviewer (complexity_check) |
| `Handing off to @qualityGuard` | @qualityGuard (write_unit_tests) |
| `Handing off to @devOps` | @devOps (pipeline_setup) |
| `Quality gate cleared` | @techLead (AUDIT_RESULT → delegate devOps) |
| `Returning to @techLead` | @techLead (review and decide) |
| `Cleared for implementation` | @codeCrafter (implement_logic) |
| `SECURITY FAIL: [msg]` | **Blocks workflow** (hook exits 2) |

| Phrase (intra-agent chain) | Reminds next skill |
|---|---|
| `Observability design complete` | activate reliability_design |
| `Reliability design complete` | activate generate_cdk_boilerplate |
| `Resilience patterns complete` | hand off to @codeReviewer |
| `Dependency audit passed` | activate documentation_check |
| `Integration tests complete` | activate load_test |
| `Load tests complete` | activate penetration_scan |
| `Pipeline configured` | activate environment_promotion |
| `Environment promotion complete` | activate deployment_verification |

---

## Agent Skills Quick Reference

### @architect (Design Phase)
- `.github/skills/architect/observability_design.md` — CloudWatch alarms, structured logs, X-Ray tracing *(WAF: Operational Excellence)*
- `.github/skills/architect/reliability_design.md` — Failure modes, RTO/RPO, DLQ config, Multi-AZ *(WAF: Reliability)*
- `.github/skills/architect/generate_cdk_boilerplate.md` — CDK v2 TypeScript stacks, tagging, private subnets
- `.github/skills/architect/security_group_audit.md` — IAM least privilege, encryption, networking *(WAF: Security)*
- `.github/skills/architect/cost_estimation.md` — Dev vs Prod sizing, idle-cost anti-patterns *(WAF: Cost)*

### @codeCrafter (Implementation Phase)
- `.github/skills/codeCrafter/add_dependencies.md` — CVE audit, license check, exact version pinning
- `.github/skills/codeCrafter/implement_logic.md` — TypeScript strict, ≤30 lines/fn, custom error classes
- `.github/skills/codeCrafter/ui_component_generator.md` — Atomic Design, Tailwind, ARIA accessibility
- `.github/skills/codeCrafter/resilience_patterns.md` — Retry backoff, idempotency, DLQ wiring *(WAF: Reliability)*

### @codeReviewer (Review Phase)
- `.github/skills/codeReviewer/complexity_check.md` — Function size, nesting depth, promise chains
- `.github/skills/codeReviewer/naming_audit.md` — PascalCase / camelCase / UPPER_SNAKE_CASE enforcement
- `.github/skills/codeReviewer/dependency_audit.md` — Staleness, CVE rescan, GPL license drift *(WAF: Security)*
- `.github/skills/codeReviewer/documentation_check.md` — README, .env.example, no TODO/FIXME *(WAF: Operational Excellence)*

### @qualityGuard (Quality Phase)
- `.github/skills/qualityGuard/write_unit_tests.md` — Jest, ≥80% branch coverage, aws-sdk-client-mock
- `.github/skills/qualityGuard/mock_aws_responses.md` — Typed mock barrel with realistic data
- `.github/skills/qualityGuard/integration_test.md` — LocalStack end-to-end, DLQ flow, idempotency *(WAF: Reliability)*
- `.github/skills/qualityGuard/load_test.md` — Artillery SLO verification, P99/error rate *(WAF: Performance)*
- `.github/skills/qualityGuard/penetration_scan.md` — Secret scan, OWASP Top 10, PII in logs *(WAF: Security)*

### @devOps (Deployment Phase)
- `.github/skills/devOps/pipeline_setup.md` — GitHub Actions CI/CD, OIDC auth, no long-lived keys *(WAF: Operational Excellence)*
- `.github/skills/devOps/environment_promotion.md` — dev→staging→prod gates, canary routing, rollback strategy *(WAF: Reliability)*
- `.github/skills/devOps/deployment_verification.md` — CloudWatch alarm check, DLQ=0, canary health *(WAF: Operational Excellence)*

---

## Portability Notes

- All hook paths in `.claude/settings.json` are relative to the project root
- Hook scripts are in `.github/hooks/`; `$PSScriptRoot` provides portable internal path resolution
- All skill files use root-relative paths (`.github/skills/[agent]/[skill].md`) — no absolute paths
- `project_state.md` and `architecture_log.md` are templates — fill `[placeholders]` during INIT_PROJECT

**Legacy path note:** Older files reference `AGENTS/` prefix. Treat `AGENTS/shared/foo.md`
as equivalent to `.github/shared/foo.md` — the prefix is a legacy convention.

---

## Known Issues

- PowerShell 5.1 (Windows default) does not support `??` or `-AsHashtable`.
  Hook scripts use `PSObject.Properties` checks and `if/else` instead.
- Hook scripts require script execution. The settings.json passes `-ExecutionPolicy Bypass` automatically.

---

## Adding a New Agent

1. Create a new folder: `newAgent/`
2. Add skill files: `ROLE & ACTIVATION` / `INPUTS` / `PROCESS` / `OUTPUT CONTRACT`
3. Define exact signal phrase(s) in OUTPUT CONTRACT
4. Add phrases to `.github/hooks/on_write.ps1` routing block
5. Add agent to the Agent Directory table and workflow diagram in this file
6. Add routing section to `.github/copilot-instructions.md`
7. Update `.github/skills/techLead/system_prompt.md` Agent Directory
