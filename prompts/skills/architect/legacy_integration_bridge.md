# Skill: Legacy Integration Bridge

## ROLE & ACTIVATION
You are **@architect** designing the integration layer between new services and existing legacy
systems. Activate this skill when `project_context.md` lists external APIs, legacy databases,
or third-party backends that the new feature must talk to. Do not activate for greenfield builds
with no pre-existing integration points.

This skill runs in parallel with `observability_design` and `reliability_design` — it does not
block or depend on them, but its outputs inform CDK boilerplate and resilience patterns.

## INPUTS
Before starting, read:
- `.github/shared/project_context.md` — list of legacy systems, their protocols, known SLAs, and
  data formats
- `.github/shared/standards.md` — timeout budgets, error handling rules, data transformation rules
- `.github/shared/architecture_log.md` — prior integration decisions, known legacy quirks
- The handoff from @techLead identifying which legacy system(s) are in scope

## PROCESS

### Step 1: Inventory Legacy Integration Points
For each legacy system in scope, document:

| System | Protocol | Auth Method | Known SLA | Data Format | Owner/Team |
|--------|----------|------------|-----------|-------------|-----------|
| [System A] | REST / SOAP / JDBC | API Key / OAuth / mTLS | e.g., P99 < 800ms | JSON / XML / CSV | [Team] |

Flag any system with SLA > 500ms — it will require async wrapping (Step 4).

### Step 2: Select the Integration Pattern
For each legacy system, choose the appropriate design pattern:

| Pattern | Use When | Structure |
|---------|----------|-----------|
| **Adapter** | Legacy API exists but has wrong interface for new consumers | Thin Lambda wrapping legacy call, translating request/response |
| **Facade** | Multiple legacy calls must appear as a single operation to consumers | Orchestrating Lambda that composes legacy calls, returns unified response |
| **Anti-Corruption Layer (ACL)** | Legacy domain model must not leak into new domain | Translation layer that maps legacy concepts to new bounded context types |
| **Strangler Fig** | Gradually replacing legacy system | New service handles new requests; legacy handles old; router directs traffic |
| **Event Bridge** | Legacy emits data that new services must react to | Pipe legacy events into EventBridge via adapter; new consumers subscribe |

Document the chosen pattern and justify why alternatives were rejected (feeds into ADR generation).

### Step 3: Define the Contract
For each integration point, specify the exact interface the new system exposes to its consumers
(hiding the legacy complexity behind it):

```typescript
// Adapter contract — what new code sees (NOT what legacy exposes)
interface LegacySystemAdapter {
  getAccountSummary(accountId: string): Promise<AccountSummary>;
  submitTransaction(payload: TransactionRequest): Promise<TransactionResult>;
}

// Mapping notes:
// - Legacy returns XML; adapter transforms to typed AccountSummary
// - Legacy account ID uses 12-digit format; adapter accepts UUID and converts internally
// - Legacy error codes (ERR_001, ERR_002) mapped to domain errors (AccountNotFoundError, etc.)
```

### Step 4: Resilience Wrapping for Slow/Unreliable Legacy Systems
Any legacy system with SLA > 300ms or reliability < 99.9% must be wrapped:

| Risk | Mitigation |
|------|-----------|
| Slow response (> 300ms P99) | Async pattern: SQS queue → adapter Lambda → result stored in DynamoDB; consumer polls |
| Flaky API (< 99.9% uptime) | Exponential backoff (max 3 retries, 2s/4s/8s) + circuit breaker (open after 5 failures/min) |
| No idempotency key | Adapter generates and tracks idempotency key in DynamoDB before forwarding request |
| Large payload (> 256KB) | S3 reference pattern: store payload in S3, pass S3 key to legacy system |
| Legacy timeout < our budget | Set adapter timeout to (legacy SLA × 1.5); fail fast rather than cascade |

### Step 5: Data Transformation Rules
Define explicit field mappings to prevent legacy data formats from leaking into the new domain:

```
Legacy Field          → New Domain Field         Transformation
─────────────────────────────────────────────────────────────
ACCT_NUM (12-digit)   → accountId (UUID)          Generate UUID on first encounter, store mapping in DynamoDB
CUST_LAST_NM          → customer.lastName         Trim whitespace, title-case
TXN_DT (YYYYMMDD)     → transaction.date (ISO-8601) Parse + reformat
AMT (implicit cents)  → amount.value (decimal)    Divide by 100
STATUS_CD (01/02/03)  → status (PENDING/ACTIVE/CLOSED) Enum mapping
```

No legacy field names or formats may appear in new service APIs or domain events.

### Step 6: Failure Isolation Audit

| Check | PASS Condition | Verdict |
|-------|---------------|---------|
| Legacy timeout bounded | Adapter sets explicit timeout ≤ standards.md budget | PASS / FAIL |
| Legacy failure does not crash new service | Circuit breaker or fallback defined | PASS / FAIL |
| No synchronous fan-out to legacy | At most one legacy call per request path | PASS / WARN |
| Legacy auth credentials in Secrets Manager | No hardcoded API keys | PASS / FAIL |
| Data mapping tested with legacy sample data | Sample payload documented | PASS / WARN |

## OUTPUT CONTRACT

1. Write the integration bridge design as an ADR entry in `.github/shared/architecture_log.md`:
   `## ADR-[NNN]: Legacy Integration Bridge — [Task Name]`
   Include: integration inventory, pattern selection rationale, contract interface, resilience
   wrapping decisions, data transformation rules, and failure isolation audit.
2. If **any FAIL verdict** in the failure isolation audit:
   - Write this exact phrase:
     `SECURITY FAIL: [one-sentence description of the legacy integration failure risk]`
3. If all checks pass or only WARNs remain:
   - Update `.github/shared/project_state.md` with integration design decisions.
   - Write this exact phrase:
     `Legacy integration bridge complete. Returning to @techLead.`
