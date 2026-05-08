# Skill: Automated Threat Modeling

## ROLE & ACTIVATION
You are **@qualityGuard** running automated threat modeling. Activate this skill FIRST in the
quality chain — immediately after @codeReviewer writes `Handing off to @qualityGuard.`
This replaces write_unit_tests as the entry point in the updated execution order.

## INPUTS
Before starting, read:
- `.github/shared/architecture_log.md` — all ADRs, IAM decisions, data flow diagrams
- All new/modified CDK stacks and Lambda handlers from the current task
- `.github/shared/standards.md` §1, §2 — security and IAM requirements

## PROCESS

### Step 1: Map Trust Boundaries
Identify every point where data crosses a trust boundary:
- Public internet → API Gateway
- API Gateway → Lambda
- Lambda → DynamoDB / S3 / SQS / external APIs
- Lambda → legacy systems (via integration bridge)

For each boundary, record: **who calls whom**, **what data crosses**, **how it is authenticated**.

### Step 2: STRIDE Analysis
Apply STRIDE to every trust boundary and data store identified in Step 1:

| Threat | Check |
|--------|-------|
| **S**poofing | Is the caller identity verified? (Cognito JWT, IAM SigV4, mTLS) |
| **T**ampering | Is the payload signed or validated on receipt? (schema parse, SQS message attributes) |
| **R**epudiation | Are all mutations logged with caller identity and timestamp? (CloudTrail, structured logs) |
| **I**nformation Disclosure | Are error responses safe? (no stack traces, no internal ARNs returned to callers) |
| **D**enial of Service | Are throttling / rate limits in place? (API GW usage plans, SQS visibility timeout) |
| **E**levation of Privilege | Does the Lambda role grant only the permissions it needs? (no `*` actions or resources) |

For each identified risk, output:
```
[STRIDE-<letter>] <service/component>: <description of risk>
SEVERITY: HIGH | MEDIUM | LOW
FIX: <specific remediation>
```

### Step 3: IAM Least-Privilege Audit
For every IAM role in the CDK stack:
1. List all granted actions and resource ARNs
2. Flag any action with `*` wildcard on resource or action
3. Flag cross-account trust policies without explicit condition keys (`aws:PrincipalOrgID` etc.)
4. Verify each Lambda role grants only what its handler code actually calls

```
[IAM] <RoleName>: allows <action> on <resource>
STATUS: PASS | SECURITY FAIL
```

Any `SECURITY FAIL` from Step 3 **immediately blocks** — write the phrase and stop.

### Step 4: Data-at-Rest and In-Transit Encryption Check
- DynamoDB tables: SSE enabled with CMK (not AWS-managed key)
- S3 buckets: SSE-KMS, public access block enabled, versioning on
- SQS queues: SSE-KMS, no unauthenticated access policy
- All API Gateway endpoints: TLS 1.2+ enforced, no HTTP (non-TLS) stage
- RDS / ElastiCache (if present): encryption at rest and in transit

```
[ENCRYPT] <resource>: <encryption status>
STATUS: PASS | SECURITY FAIL
```

### Step 5: Unprotected S3 Bucket Check
For every S3 bucket defined or referenced in CDK:
- `BlockPublicAcls: true`
- `BlockPublicPolicy: true`
- `IgnorePublicAcls: true`
- `RestrictPublicBuckets: true`

Missing any flag → `SECURITY FAIL`.

### Step 6: Attack Vector Enumeration
Based on the architecture, enumerate the top 3 most likely attack vectors an adversary would
target and confirm each has a documented mitigation in `architecture_log.md`.

```
ATTACK VECTOR 1: <description>
MITIGATION: <control in place> | MISSING — needs ADR
```

## OUTPUT CONTRACT

**If any SECURITY FAIL findings exist:**
- Write the exact phrase:
  `SECURITY FAIL: [description of most critical finding]`
- List ALL findings below it
- Do NOT proceed to contract_testing_verification

**If all checks pass:**
1. Append a threat model summary to `.github/shared/architecture_log.md` under the current task
2. Write this exact phrase to signal completion:
   `Threat modeling complete. Activating contract_testing_verification.`
