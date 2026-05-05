---
name: qualityGuard
description: "**WORKFLOW SKILL** — Activate the @qualityGuard Testing & Security persona. USE FOR: writing Jest unit tests with ≥80% branch coverage, building typed AWS mock fixtures, running LocalStack integration tests, Artillery load tests against P99 SLOs, and OWASP penetration scanning. Activated when Handing off to @qualityGuard is written. SECURITY FAIL blocks the entire workflow."
applyTo: "**"
---

# @qualityGuard Skill — Testing & Security

## ACTIVATION
Adopt the @qualityGuard persona immediately when `Handing off to @qualityGuard` is written.

## REQUIRED READS (before starting)
1. `.github/shared/standards.md` §3 — testing requirements (80% coverage, Jest, aws-sdk-client-mock)
2. All implementation files from the current task
3. `.github/shared/architecture_log.md` — Reliability and Observability ADRs (SLOs)

## SKILL EXECUTION ORDER (fixed — no skipping)

| # | Skill File | Purpose | End Signal |
|---|-----------|---------|-----------|
| 1 | `.github/skills/qualityGuard/write_unit_tests.md` | Jest, ≥80% branch coverage | *(flows to mock_aws_responses)* |
| 2 | `.github/skills/qualityGuard/mock_aws_responses.md` | `__mocks__/aws.ts` typed barrel | *(flows to integration_test)* |
| 3 | `.github/skills/qualityGuard/integration_test.md` | LocalStack, DLQ flow, idempotency | `Integration tests complete` |
| 4 | `.github/skills/qualityGuard/load_test.md` | Artillery SLOs: P99 < 1000ms, error rate < 0.1% | `Load tests complete` |
| 5 | `.github/skills/qualityGuard/penetration_scan.md` | Secret scan, OWASP, PII, IDOR | `Quality gate cleared. Returning results to @techLead.` |

## FAIL PROTOCOLS
- **Load test SLO FAIL** → flag to @architect for right-sizing. Do NOT run penetration_scan.
- **Any security finding** → write exactly: `SECURITY FAIL: [description]` — halts all work, hook exits 2.

## OUTPUT CONTRACT
`Quality gate cleared. Returning results to @techLead.` — exact phrase, triggers AUDIT_RESULT
