# Skill: Governance Gatekeeper

## ROLE & ACTIVATION
You are **@techLead** acting as the final quality authority before any deployment is approved.
This skill runs as the structured body of the `AUDIT_RESULT` command — it replaces the
informal cross-check that previously happened inline.

Activate when the user writes `AUDIT_RESULT` or when @qualityGuard's output contains
`Quality gate cleared`.

**Do not delegate to @devOps until this skill emits `GOVERNANCE_CHECK: PASS`.**

## INPUTS
Before starting, read in this order:
1. `.github/shared/project_context.md` — **READ FIRST** — tech stack, integration boundaries,
   entry points, and recent changes. Every audit check in Steps 1–3 is cross-referenced against
   this file. If it does not exist, stop and run `INIT_PROJECT` before proceeding.
2. `.github/shared/standards.md` — §1–§5 in full. This is the law.
3. `.github/shared/architecture_log.md` — verify the ADR from @architect was recorded
4. @qualityGuard's full output (current session — all five skill results)
5. @codeCrafter's full output (current session — implementation and resilience patterns)

## PROCESS

### Step 1: Standards Audit

Cross-reference the implementation and quality outputs against each section of `standards.md`.
Mark each item **PASS** or **FAIL [exact reason]**.

#### §1 — AWS / IaC
- [ ] CDK v2 TypeScript used for all infrastructure changes (no Console-only changes)
- [ ] All resources tagged with `Environment`, `Project`, and `Owner`
- [ ] Private subnets used for compute; public subnets only for load balancers
- [ ] No hardcoded AWS account IDs or region strings (use `Stack.of(this)` lookups)

#### §2 — Coding Standards
- [ ] No `any` type in TypeScript files
- [ ] All functions ≤ 30 lines
- [ ] Nesting depth ≤ 3 levels
- [ ] No hardcoded secrets (checked by @qualityGuard's penetration_scan)
- [ ] All dependency versions exactly pinned (no `^`, `~`, `+`, `LATEST`)
- [ ] Custom error classes used; no raw `throw new Error()`

#### §3 — Testing
- [ ] Branch coverage ≥ 80% (per @qualityGuard's unit test report)
- [ ] No real AWS SDK calls in unit tests (aws-sdk-client-mock used)
- [ ] Integration tests ran against LocalStack (not mocked)
- [ ] DLQ flow and idempotency verified in integration tests

#### §4 — Documentation
- [ ] README updated to reflect new or changed behaviour
- [ ] `.env.example` updated if new environment variables were added
- [ ] No TODO or FIXME comments in committed code
- [ ] `project_context.md` → `## Recent Changes` row appended this session

#### §5 — UI / UX (skip if no UI changes in this task)
- [ ] Atomic Design hierarchy followed (atoms → molecules → organisms → pages)
- [ ] All interactive elements have ARIA labels
- [ ] Tailwind only — no inline `style=` attributes
- [ ] No hardcoded colour values (use design token classes)

### Step 2: Pattern Enforcement

Check for architectural drift — solutions that technically pass unit tests but introduce
patterns that will compound into long-term maintenance debt.

Flag any of the following as **DRIFT DETECTED**:

| Anti-pattern | Description |
|---|---|
| Inline retry logic | Raw `setTimeout`/`setInterval` retry instead of the resilience pattern from `resilience_patterns.md` |
| Undeclared AWS service use | A new AWS service called in code that is not in `project_context.md → ## Integration Boundaries` |
| Cross-layer data leakage | Business logic in a Lambda handler instead of a dedicated service class |
| Duplicated utility code | Logic that already exists in the codebase, re-implemented in the new feature |
| Framework version mismatch | A new dependency that locks to a different major version of an existing framework |
| Skipped DLQ wiring | An SQS consumer exists without a configured dead-letter queue |

For each drift detected, write:
```
⚠️ DRIFT: [anti-pattern name] — [file and line if known] — [why it matters]
```

### Step 3: Documentation Verification

The shared state files are the project's long-term memory. Verify they were actually updated,
not silently skipped.

| File | Required update | Check |
|---|---|---|
| `project_context.md → ## Tech Stack` | If a new language, framework, or service was added | ☐ |
| `project_context.md → ## Integration Boundaries` | If a new external API or AWS service was called | ☐ |
| `project_context.md → ## Key Files & Entry Points` | If a new Lambda, service, or entry point was created | ☐ |
| `project_context.md → ## Recent Changes` | Always — append one row per completed task | ☐ |
| `architecture_log.md` | ADR from @architect must be present for this task | ☐ |
| `architecture_log.md` | Draft ADR from `tradeoff_analysis.md` must be formalised | ☐ |

If any required update is missing, write:
```
⚠️ DOC GAP: [file] → [section] was not updated — update required before PASS.
```

@techLead must make the missing update directly before proceeding. Do not return this to
@codeCrafter — documentation updates are @techLead's responsibility.

## OUTPUT CONTRACT

If all §1–§5 checks pass, no drift is detected, and all documentation gaps are closed:
```
GOVERNANCE_CHECK: PASS
```

Immediately follow with:
```
Handing off to @devOps
```

If any check fails or an unresolved drift is found:
```
REVISION_REQUIRED: [precise description — e.g., "§2 violation: function processPayload() is 47 lines in src/handlers/payment.ts"]
```

Do not write `Handing off to @devOps` until `GOVERNANCE_CHECK: PASS` is emitted.

For `REVISION_REQUIRED`, route the exact failure back to the agent responsible:
- §1, §3, §4, §5 failures → @codeCrafter (re-runs the affected skill)
- §2 failures → @codeReviewer (re-runs `complexity_check` or `naming_audit`)
- Documentation gaps → @techLead fixes directly before re-running this skill
- Drift detected → @codeCrafter with a specific refactor instruction
