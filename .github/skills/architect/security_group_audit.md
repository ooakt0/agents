# Skill: Security Group Audit

## ROLE & ACTIVATION
You are **@architect** performing a security audit. Activate after @codeCrafter completes
infrastructure code, or when @techLead requests a pre-deployment security check. This skill
is also triggered automatically when `generate_cdk_boilerplate` produces new stacks.

## INPUTS
Before starting, read:
- All files in the `infrastructure/` directory (CDK stacks, IAM policy documents)
- `.github/shared/standards.md` §1 — Least Privilege, encryption requirements
- `.github/shared/project_state.md` — which environment is being audited (Dev / Prod)
- `.github/shared/architecture_log.md` — intended security posture from prior ADRs

## PROCESS

### Step 1: IAM Audit
Scan every IAM role and policy statement in the CDK stacks:

| Check | PASS Condition | Verdict |
|-------|---------------|---------|
| No `Resource: "*"` | All policies scoped to specific ARNs | PASS / FAIL |
| No admin-level actions | No `iam:*`, `s3:*`, `dynamodb:*` wildcards | PASS / FAIL |
| One role per compute unit | Each Lambda/ECS task has its own role | PASS / FAIL |
| `grant*` methods preferred | L2 construct grants used where available | PASS / WARN |

For every `Resource: "*"` found: quote the exact code line and the role name.

### Step 2: Networking Audit
Scan all Security Group and VPC configuration:

| Check | PASS Condition | Verdict |
|-------|---------------|---------|
| No `0.0.0.0/0` ingress (except 80/443) | Only ALBs have public ingress | PASS / FAIL |
| Internal traffic uses SG references | No CIDR blocks for intra-VPC traffic | PASS / WARN |
| Compute in private subnets | `allowPublicSubnet: false` on Lambda | PASS / FAIL |
| No open egress rules | Egress scoped to required endpoints | PASS / WARN |

### Step 3: Encryption Audit
Verify all data-at-rest and data-in-transit encryption:

| Resource | Required Setting | Verdict |
|----------|-----------------|---------|
| DynamoDB | `encryption: AWS_MANAGED` or CMK | PASS / FAIL |
| S3 | `encryption: S3_MANAGED`, `blockPublicAccess: BLOCK_ALL` | PASS / FAIL |
| RDS | `storageEncrypted: true` | PASS / FAIL |
| Lambda env vars | Secrets in Secrets Manager, not env vars | PASS / FAIL |
| ALB | HTTPS listener only; HTTP redirects to HTTPS | PASS / FAIL |

### Step 4: Secret Management Check
Search all CDK stacks and environment files for:
- Hardcoded passwords, tokens, or API keys
- `secretValue` set to a literal string (not `SecretValue.ssmSecure()` or `secretsmanager`)
- Any `.env` file checked into version control

### Step 5: Produce the Verdict
Summarize all checks with an overall verdict per category:
- **PASS** — no violations found
- **WARN** — non-critical finding, should be addressed before production
- **FAIL** — critical violation, blocks deployment

## OUTPUT CONTRACT

1. Append the full audit report as a comment block in `.github/shared/architecture_log.md` under the
   relevant ADR (or create a new entry: `## ADR-[NNN]: Security Audit — [Task Name]`)
2. If **any FAIL verdict** exists:
   - Write this exact phrase (with colon) to block the workflow:
     `SECURITY FAIL: [one-sentence description of the violation]`
   - Do NOT proceed — @techLead must resolve the FAIL before @codeCrafter is unblocked
3. If all checks are PASS or WARN:
   - Update `.github/shared/project_state.md` — set the security audit task to ✅ DONE
   - Write this exact phrase to signal @codeCrafter can proceed:
     `Cleared for implementation.`
