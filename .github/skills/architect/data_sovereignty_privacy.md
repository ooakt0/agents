# Skill: Data Sovereignty & Privacy

## ROLE & ACTIVATION
You are **@architect** performing a data compliance audit. Activate after `disaster_recovery_strategy`
and before `generate_cdk_boilerplate`. Any design that stores, transmits, or processes user data
must pass this skill — skipping it is not permitted regardless of environment.

## INPUTS
Before starting, read:
- `.github/shared/project_context.md` — data flows, external integrations, storage services listed
- `.github/shared/standards.md` — retention policy, PII handling rules, encryption requirements
- `.github/shared/architecture_log.md` — prior ADRs describing data storage decisions
- The handoff from @techLead identifying the task and the data categories involved

## PROCESS

### Step 1: Classify All Data in Scope
For every data store and data-in-transit path identified in `project_context.md`, assign a
sensitivity tier:

| Tier | Examples | Handling Required |
|------|----------|------------------|
| **T1 — Public** | Product catalog, static content | No special handling |
| **T2 — Internal** | Aggregated metrics, audit logs | Encryption-at-rest, access logging |
| **T3 — Confidential** | Account details, transaction history | Encryption at rest + in transit, RBAC, 90-day retention max |
| **T4 — PII / Regulated** | SSN, DOB, card numbers, email, phone | Masking/tokenization, isolated storage, audit trail, legal hold capable |

List every field stored or transmitted and its tier. If tier is unknown, default to T4.

### Step 2: PII Isolation Audit

| Check | PASS Condition | Verdict |
|-------|---------------|---------|
| PII stored in dedicated table/bucket | T4 data not co-mingled with T1-T2 | PASS / FAIL |
| PII fields masked in logs | No raw PII in CloudWatch Logs | PASS / FAIL |
| PII tokenized or encrypted at field level | Sensitive fields use envelope encryption or tokenization | PASS / FAIL |
| PII excluded from search indexes | T4 fields not indexed in OpenSearch/ElasticSearch | PASS / WARN |
| Data minimization applied | Only fields required for business function are stored | PASS / WARN |

For every FAIL: quote the exact field name, storage location, and the violated rule from `standards.md`.

### Step 3: Data Residency Check
- Confirm all storage services are deployed to the region(s) approved in `project_context.md`.
- If cross-region replication exists (for DR), confirm the replica region is also approved.
- Flag any third-party integration (e.g., a SaaS analytics tool) that may transfer T3/T4 data
  outside approved jurisdictions. These require explicit approval from @techLead.

| Check | PASS Condition | Verdict |
|-------|---------------|---------|
| Primary storage in approved region | e.g., `us-east-1` only | PASS / FAIL |
| Replica region approved | Listed in `project_context.md` DR regions | PASS / FAIL |
| No unapproved cross-border T4 transfer | Third-party APIs verified | PASS / FAIL |

### Step 4: Retention Policy Enforcement
For each data store, confirm a retention/TTL policy exists and aligns with `standards.md`:

| Store | Required Retention | Actual Setting | Verdict |
|-------|--------------------|----------------|---------|
| DynamoDB (T3/T4) | Per standards.md | TTL attribute defined? | PASS / FAIL |
| S3 (T3/T4) | Per standards.md | Lifecycle rule defined? | PASS / FAIL |
| CloudWatch Logs | Dev: 7d / Prod: 90d | Log group retention set? | PASS / FAIL |
| RDS / Aurora | Per standards.md | Backup retention + PITR? | PASS / FAIL |

### Step 5: Encryption Verification (T3/T4 Focus)
- All T3/T4 DynamoDB tables must use Customer Managed Keys (CMK), not AWS-managed keys.
- S3 buckets holding T4 data must have `blockPublicAccess: BLOCK_ALL` and SSE-KMS.
- Secrets Manager must be used for all credentials — no Secrets in environment variables.
- KMS key policies must restrict decrypt to only the IAM roles that require it.

### Step 6: Produce the Privacy Verdict
Overall verdict per category (PII Isolation / Data Residency / Retention / Encryption):
- **PASS** — fully compliant
- **WARN** — risk present, must be addressed before production
- **FAIL** — blocks implementation

## OUTPUT CONTRACT

1. Append the full data privacy audit as an ADR entry in `.github/shared/architecture_log.md`:
   `## ADR-[NNN]: Data Sovereignty & Privacy Audit — [Task Name]`
2. If **any FAIL verdict** exists:
   - Write this exact phrase to block the workflow:
     `SECURITY FAIL: [one-sentence description of the data privacy violation]`
   - Do NOT proceed.
3. If all checks are PASS or WARN:
   - Update `.github/shared/project_state.md` — set the privacy audit task to ✅ DONE.
   - Write this exact phrase:
     `Data sovereignty review complete. Activating generate_cdk_boilerplate.`
