# Skill: Compliance as Code Audit

## ROLE & ACTIVATION
You are **@qualityGuard** running the compliance audit. Activate this skill THIRD in the quality
chain — immediately after `Contract testing complete. Activating compliance_as_code_audit.`

## INPUTS
Before starting, read:
- `.github/shared/standards.md` — regulatory requirements section (SOC 2, PCI-DSS, GDPR flags)
- `.github/shared/architecture_log.md` — data classification ADR, encryption decisions
- All CDK stacks and Lambda handlers in the current task
- `.github/shared/project_context.md` — compliance tier (e.g., PCI in-scope: yes/no)

## PROCESS

### Step 1: Determine Applicable Compliance Frameworks
Check `project_context.md` for declared compliance tiers:
- **SOC 2 Type II** — always applicable (default baseline)
- **PCI-DSS** — if cardholder data or payment flows are in scope
- **GDPR / Data Privacy** — if EU personal data is processed
- **HIPAA** — if PHI is stored or transmitted

Run only the checklist(s) that apply. Skip inapplicable frameworks explicitly:
```
FRAMEWORK: PCI-DSS — NOT IN SCOPE (no payment data). Skipping.
FRAMEWORK: SOC 2 — IN SCOPE. Running checklist.
```

### Step 2: SOC 2 Checklist (Always Run)
| Control | Check | Status |
|---------|-------|--------|
| CC6.1 | CloudTrail enabled in all regions with log file validation | PASS/FAIL |
| CC6.2 | MFA required for AWS Console access (enforce via SCP) | PASS/FAIL |
| CC6.3 | IAM roles have no inline policies; all policies are managed and versioned | PASS/FAIL |
| CC6.7 | All data encrypted at rest (DynamoDB, S3, SQS with CMK) | PASS/FAIL |
| CC7.2 | CloudWatch alarms set on error rates, DLQ depth, and auth failures | PASS/FAIL |
| CC8.1 | Change management: all infra changes via CDK/IaC; no console-driven changes | PASS/FAIL |
| A1.2 | Backups: DynamoDB PITR enabled; S3 versioning enabled | PASS/FAIL |

For each FAIL:
```
[SOC2] <control-id>: <description of gap>
FIX: <specific remediation with CDK property or config change>
```

### Step 3: PCI-DSS Checklist (If In Scope)
| Requirement | Check | Status |
|-------------|-------|--------|
| 2.2 | No default credentials; SSM Parameter Store used for all secrets | PASS/FAIL |
| 3.4 | PANs stored in masked/tokenized form only; never in plaintext DynamoDB | PASS/FAIL |
| 4.1 | TLS 1.2+ enforced on all API Gateway stages; no TLS 1.0/1.1 | PASS/FAIL |
| 6.3 | Dependency CVE scan completed (covered by dependency_audit) | PASS/FAIL |
| 7.1 | IAM least privilege: Lambda roles scoped to minimum required actions | PASS/FAIL |
| 10.2 | All access to cardholder data logged with user identity and timestamp | PASS/FAIL |
| 10.5 | CloudWatch log groups have retention set (≥1 year for PCI logs) | PASS/FAIL |

### Step 4: GDPR / Data Privacy Checklist (If In Scope)
| Article | Check | Status |
|---------|-------|--------|
| Art. 5 | Data minimisation: only necessary PII fields collected and stored | PASS/FAIL |
| Art. 17 | Right to erasure: deletion path exists for user PII in DynamoDB | PASS/FAIL |
| Art. 25 | Privacy by default: PII fields not logged; anonymisation in analytics | PASS/FAIL |
| Art. 30 | Records of processing: data flows documented in architecture_log.md | PASS/FAIL |
| Art. 32 | Encryption at rest and in transit for all PII data stores | PASS/FAIL |
| Art. 44 | Cross-border transfers: PII does not leave the declared AWS region | PASS/FAIL |

### Step 5: Log Retention and Audit Trail Verification
For all CloudWatch log groups created by the current task:
- Retention policy set (not infinite — must match compliance tier: SOC2 ≥90d, PCI ≥365d)
- Log group encrypted with CMK
- Log group name follows naming convention from `standards.md`

```
[LOGS] /aws/lambda/<functionName>: retention=<days>, encrypted=<yes/no>
STATUS: PASS | FAIL
```

### Step 6: Infrastructure Drift Check
Compare declared CDK resource properties against the compliance requirements:
- No `removalPolicy: DESTROY` on production data stores (DynamoDB, S3, RDS)
- No `publicRead: true` or `websiteIndexDocument` on non-public buckets
- All Lambda functions have reserved concurrency set (prevents runaway cost and DDoS amplification)

```
[DRIFT] <resource>: <non-compliant property>
FIX: <CDK property change>
```

## OUTPUT CONTRACT

**If any FAIL findings exist:**
- List all non-compliant controls with their fix instructions
- Write `SECURITY FAIL: Compliance audit failed — <summary of top gap>`
- Do NOT proceed to write_unit_tests

**If all applicable controls pass:**
1. Append a compliance sign-off table to `.github/shared/project_state.md` under the current task
2. Write this exact phrase to signal completion:
   `Compliance audit complete. Activating write_unit_tests.`
