# Project Context
**Owner:** @techLead | **Last Updated:** [YYYY-MM-DD] | **Updated By:** [agent or user]

> **PURPOSE:** Single source of truth for all agents. Read this file FIRST — before any project file scan or cross-referencing other shared files. An agent that makes assumptions without reading this file is operating with incomplete context.
>
> **@techLead:** Populate at `INIT_PROJECT`. Update at every major milestone and after every `deployment_verification` PASS. No `DELEGATE` is issued until this file exists and is accurate.

---

## Project Overview

- **Name:** [Project name]
- **Purpose:** [One-sentence purpose — what problem does it solve for whom?]
- **Description:** [3-5 sentences: what it does, who uses it, business domain, why it exists now]
- **Stage:** [Greenfield | Active development | Maintenance | Legacy migration]
- **SLA target:** [e.g., 99.9% availability, < 500 ms P99 on /checkout]
- **RTO / RPO:** [e.g., RTO 1 h / RPO 15 min — documented in ADR-NNN]

---

## Tech Stack
<!-- @codeCrafter reads this to select the correct implement_logic.md language section.
     @architect reads this to ensure CDK stacks match the runtime and DB choice. -->

| Layer | Technology | Version | Notes |
|---|---|---|---|
| Language | [e.g. TypeScript / Python / Java] | [e.g. 5.x / 3.12 / 21] | [strict mode / PEP 484 / etc.] |
| Runtime | [e.g. Node.js 22.x Lambda / Spring Boot 3] | [version] | [e.g. arm64, 512 MB] |
| UI Framework | [e.g. Next.js App Router / Angular 17 / None] | [version] | |
| IaC | AWS CDK v2 TypeScript | [version] | [cdk-nag AwsSolutionsChecks enabled] |
| Test — Unit | [e.g. Jest 29 / pytest 8 / JUnit 5] | [version] | |
| Test — Integration | [e.g. LocalStack / moto] | [version] | |
| Test — Load | Artillery | [version] | [SLO: P99 < 1000 ms] |
| DB / Storage | [e.g. DynamoDB on-demand / RDS PostgreSQL 16] | | [PITR enabled in prod] |
| Event Bus | [e.g. EventBridge custom bus / SQS FIFO] | | |
| Auth | [e.g. Amazon Cognito User Pool / JWT RS256] | | |
| Observability | CloudWatch Logs + X-Ray + custom alarms | | [structured JSON logs] |
| Security scanning | [e.g. npm audit / pip audit / trivy] | | [zero high/critical gate] |

---

## Directory Structure
<!-- Top-level only. @codeCrafter uses this to place new modules.
     @codeReviewer uses this for documentation checks. -->

```
[project-root]/
  [dir]/           ← [purpose — e.g. "Lambda handlers, one file per function"]
  [dir]/           ← [purpose — e.g. "CDK stacks and constructs"]
  [dir]/           ← [purpose — e.g. "Domain services, error classes, validators"]
  [dir]/           ← [purpose — e.g. "Unit tests (mirrors src/ structure)"]
  [dir]/           ← [purpose — e.g. "Integration tests (LocalStack)"]
  [dir]/           ← [purpose — e.g. "OpenAPI specs and contract fixtures"]
  [file]           ← [purpose — e.g. "CDK app entry point"]
```

---

## Key Files & Entry Points
<!-- Files every agent must know without searching.
     @devOps reads this to identify which CDK stack to deploy.
     @codeCrafter reads this to know where new logic belongs. -->

| File | Purpose | Owner agent |
|---|---|---|
| `[path/to/handler.ts]` | Main Lambda handler — entry point for all API Gateway events | @codeCrafter |
| `[path/to/stack.ts]` | CDK stack — all AWS resources for this service | @architect |
| `[path/to/errors.ts]` | Domain error class hierarchy — all custom exceptions | @codeCrafter |
| `[path/to/env.ts]` | Env var schema — validated at startup with Zod / pydantic | @codeCrafter |
| `[path/to/openapi.yaml]` | OpenAPI 3.1 spec — source of truth for this service's API | @codeReviewer |
| `.env.example` | Canonical list of required env vars with placeholder values | @techLead |

---

## Environment & Config
<!-- Env var NAMES only — never values or secrets.
     @devOps uses this to configure SSM paths and pipeline secrets.
     @codeCrafter uses this to know which names to reference in code. -->

| Variable | Used By | Source | Purpose |
|---|---|---|---|
| `[VAR_NAME]` | [handler or service] | [SSM / Secrets Manager / .env] | [what it configures] |
| `[VAR_NAME]` | | | |

- **Config source:** [e.g. AWS SSM Parameter Store — path prefix `/project/env/`]
- **Secret source:** [e.g. AWS Secrets Manager — ARN prefix `arn:aws:secretsmanager:...`]
- **Feature flags:** [list flags, or "None"]
- **Env promotion:** [e.g. `dev` → `staging` → `prod` — different SSM paths per stage]

---

## Integration Boundaries
<!-- Every external system this project touches. Agents use this to assess blast radius
     and to mock dependencies correctly in tests.
     @architect reads this when designing new resources or event contracts. -->

| System | Type | Direction | Circuit breaker | Mock in tests |
|---|---|---|---|---|
| [e.g. Stripe API] | External HTTP | Outbound | Yes — timeout 3 s | `__mocks__/stripe.ts` |
| [e.g. DynamoDB bookings] | AWS service | Read/Write | N/A | `aws-sdk-client-mock` |
| [e.g. SQS booking-dlq] | AWS service | Write on error | N/A | `aws-sdk-client-mock` |
| [e.g. EventBridge default bus] | AWS service | Publish | N/A | `aws-sdk-client-mock` |
| [e.g. Cognito User Pool] | AWS service | Auth verify | N/A | JWT fixture in tests |

---

## Known Constraints
<!-- Hard technical constraints, off-limits patterns, agreed tech debt, critical gotchas.
     @codeCrafter MUST read before writing any code.
     @codeReviewer uses these as additional checks beyond standards.md.
     Format: constraint — reason — added by — date. -->

- [e.g. No DynamoDB Scan — all reads must use GSI or table key — @architect — 2026-01-15]
- [e.g. Payments Lambda must stay ≤ 128 MB memory — SLA cost constraint — @techLead — 2026-01-15]
- [e.g. All public API routes require Cognito JWT — security baseline — ADR-003]
- [e.g. Node.js runtime only on Lambda — no Python Lambdas — team skill constraint]
- [e.g. DynamoDB table names injected via env vars — never hardcoded — §2.1 of standards.md]

---

## Threat Model Summary
<!-- High-level threat surface for this service. @architect populates during security_group_audit.
     @qualityGuard uses this to scope the penetration_scan. -->

| Threat | Mitigation | Status |
|---|---|---|
| [e.g. Unauthorized API access] | [Cognito JWT validation on all routes] | [Mitigated / Open] |
| [e.g. Secret exfiltration] | [Secrets Manager + no env literals in code] | [Mitigated] |
| [e.g. Injection via query params] | [Zod schema validation at handler boundary] | [Mitigated] |
| [e.g. DLQ message replay attack] | [Idempotency key on all processors] | [Mitigated] |

---

## Recent Changes
<!-- Rolling log of the 5 most recent changes. @techLead appends after every deployment_verification PASS
     or CHANGE_REQUEST resolution. Remove the oldest row when a 6th is added. -->

| Date | Task / CR | Agent chain | Files touched | Summary |
|---|---|---|---|---|
| [YYYY-MM-DD] | [T-001 / CR-001] | [e.g. codeCrafter → codeReviewer → qualityGuard → devOps] | [file list] | [one-line summary] |
