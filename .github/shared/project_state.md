# Project State: [Project Name]
**Current Phase:** DISCOVERY | DESIGN | BUILD | TEST | DEPLOY
**Last Sync:** [YYYY-MM-DD HH:MM UTC]
**Lead Agent:** @techLead

> **Rule:** Read this file before every agent action. Update it after every handoff. This is the only task tracker — do not maintain a parallel list elsewhere.

---

## Active Mission

- **Goal:** [Precise, testable goal — e.g., "Add booking cancellation Lambda that marks DynamoDB records as CANCELLED and publishes BookingCancelled to EventBridge"]
- **Stakeholder:** [Team / individual requesting the change]
- **Success criteria:** [How we know it is done — e.g., "All tests pass, P99 latency < 500 ms on load test, deployed to prod with zero alarm triggers"]
- **Deadline / priority:** [e.g., P1 — blocking release / P2 — next sprint]

---

## Task Board

| ID | Task | Agent | Status | Blocked by | Notes |
|:---|:---|:---|:---|:---|:---|
| T-001 | [e.g. Requirement decomposition & project_context.md] | @techLead | ✅ DONE | — | |
| T-002 | [e.g. Architecture design — EventBridge rule, DLQ, IAM] | @architect | 🏗️ ACTIVE | — | ADR-NNN pending |
| T-003 | [e.g. Implement cancellation handler] | @codeCrafter | ⏳ BACKLOG | T-002 | Handoff template ready |
| T-004 | [e.g. Code review] | @codeReviewer | ⏳ BACKLOG | T-003 | |
| T-005 | [e.g. Unit + integration tests] | @qualityGuard | ⏳ BACKLOG | T-004 | |
| T-006 | [e.g. Pipeline setup & deployment] | @devOps | ⏳ BACKLOG | T-005 | Needs AUDIT_RESULT |

**Status legend:** ✅ DONE | 🏗️ ACTIVE | 🔍 REVIEW | ⏳ BACKLOG | 🚫 BLOCKED

---

## Architecture Snapshot

- **Region:** `[e.g. us-east-1]`
- **Compute:** [e.g. Lambda (Node.js 22.x arm64) behind API Gateway v2]
- **Data:** [e.g. DynamoDB on-demand — bookings table, GSI on status+createdAt]
- **Messaging:** [e.g. SQS FIFO + DLQ (maxReceiveCount=3), EventBridge custom bus]
- **Networking:** [e.g. VPC with private subnets, VPC endpoints for S3/DynamoDB/SSM]
- **Auth:** [e.g. Cognito User Pool — JWT RS256, verified in Lambda authorizer]
- **CDK stacks:** [e.g. `BookingServiceStack` (main), `BookingServicePipelineStack` (CI/CD)]
- **Deployment target:** [e.g. dev: `booking-dev`, staging: `booking-staging`, prod: `booking-prod`]

---

## Open Risks & Blockers

| # | Risk / Blocker | Severity | Owner | Resolution / ETA |
|---|---|---|---|---|
| 1 | [e.g. DynamoDB GSI capacity not confirmed for peak load] | High | @architect | Pending load test results |
| 2 | [e.g. Stripe API rate limit undocumented] | Medium | @techLead | Waiting on vendor response |

---

## Technical Debt Register

| ID | Description | Introduced by | Impact | Target task |
|---|---|---|---|---|
| TD-001 | [e.g. Payment handler lacks retry on 429 from Stripe] | T-003 | Medium — silent failures under load | T-NNN |

---

## Recent Decisions

<!-- Lightweight record of decisions not large enough for a full ADR.
     Full architectural decisions go to architecture_log.md. -->

| Date | Decision | Rationale | Made by |
|---|---|---|---|
| [YYYY-MM-DD] | [e.g. Use cursor pagination over offset] | [DynamoDB does not support offset; consistent performance at scale] | @architect |
| [YYYY-MM-DD] | [e.g. Conventional Commits enforced via commitlint] | [Automated changelog and semantic versioning] | @techLead |

---

## Deployment History

| Date | Environment | Task / CR | Deployed by | Outcome | Rollback available |
|---|---|---|---|---|---|
| [YYYY-MM-DD] | [prod] | [T-NNN] | @devOps | [✅ Green / ❌ Rolled back] | [Yes — Last Known Good: commit SHA] |
