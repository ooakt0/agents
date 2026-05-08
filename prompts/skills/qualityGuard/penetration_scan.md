# Skill: Penetration Scan

## ROLE & ACTIVATION
You are **@qualityGuard** running the penetration scan. Activate this skill FIFTH and LAST in
the quality chain � after load_test completes successfully. This is the final security gate
before @techLead signs off.

## INPUTS
Before starting, read:
- All implementation files from @codeCrafter
- `.github/shared/standards.md` �1, �2 � security requirements
- `.github/shared/architecture_log.md` � Security ADR from @architect's security_group_audit

## PROCESS

### Step 1: Secret Scan
Scan all source files for hardcoded credentials, API keys, or tokens.
Look for patterns: `AWS_SECRET`, `password =`, `apiKey:`, `token:`, `Bearer `, private key headers.

Tools: `git-secrets`, `trufflehog`, or manual regex scan.

For each finding:
```
[SECRET] SECURITY FAIL: src/[file].ts line [N] � hardcoded [credential type] detected
FIX: move to AWS Secrets Manager, reference via SECRETS_MANAGER_ARN env variable
```

Any secret finding is an **immediate workflow blocker** � write `SECURITY FAIL:` and stop.

### Step 2: OWASP Top 10 Checklist
Review the implementation against the OWASP Top 10:

| # | Risk | Check |
|---|------|-------|
| A01 | Broken Access Control | All Lambda endpoints validate caller identity (Cognito JWT or IAM auth) |
| A02 | Cryptographic Failures | No plaintext secrets; all data at rest encrypted (DynamoDB SSE, S3 SSE-KMS) |
| A03 | Injection | All DynamoDB queries use parameterised expressions (never string concatenation) |
| A04 | Insecure Design | Business logic reviewed in ADR; threat model documented |
| A05 | Security Misconfiguration | No `*` in IAM policies; no public S3 buckets; SGs have no 0.0.0.0/0 ingress |
| A06 | Vulnerable Components | Covered by dependency_audit CVE scan |
| A07 | Auth Failures | JWT expiry checked; no long-lived tokens; Cognito MFA enabled |
| A08 | Integrity Failures | SQS messages validated against schema before processing |
| A09 | Logging Failures | All errors logged in structured JSON; no sensitive data in logs |
| A10 | SSRF | No user-controlled URLs passed to fetch/http clients |

For each FAIL:
```
[OWASP] SECURITY FAIL: A0X [risk name] � [description of finding]
FIX: [specific remediation step]
```

### Step 3: PII in Logs Check
Scan all `console.log`, `console.warn`, `console.error`, and structured logging statements for
potential PII: email addresses, phone numbers, full names, credit card patterns, SSNs, passwords.

Pattern examples: `email`, `phone`, `ssn`, `password`, `creditCard`, `cardNumber`, `dob`.

```
[PII] SECURITY FAIL: src/[file].ts line [N] � field '[fieldName]' logged � potential PII
FIX: redact field before logging or use a sanitise() helper
```

### Step 4: IDOR Review (Insecure Direct Object Reference)
For every endpoint that accepts a resource ID (order ID, user ID, etc.) in the request:
1. Verify the handler fetches the resource and checks ownership before returning it
2. Verify the handler does NOT trust a `userId` from the request body � only from the verified JWT

```
[IDOR] SECURITY FAIL: src/handlers/getOrder.ts � userId taken from request body, not JWT
FIX: extract userId from event.requestContext.authorizer.claims.sub only
```

### Step 5: Input Validation Boundary Check
For every Lambda handler that accepts external input (API Gateway, SQS, SNS):
1. Verify input is validated against a schema at the top of the handler (using zod, joi, or similar)
2. Verify validation errors return 400 with a safe message (no internal detail leaked)
3. Verify no user-supplied data is used in DynamoDB `TableName`, `IndexName`, or IAM policy arns

```
[INPUT] WARN: src/handlers/createOrder.ts � no schema validation on request body
FIX: add zod schema parse at top of handler, catch ZodError and return 400
```

## OUTPUT CONTRACT

**If any SECURITY FAIL findings exist:**
- Write the exact phrase (hooks will block the workflow):
  `SECURITY FAIL: [description of the most critical finding]`
- List ALL findings below it for @techLead to review
- Do NOT write `Quality gate cleared`

**If all checks pass (no SECURITY FAIL findings):**
1. Write a security summary in `.github/shared/project_state.md` under the task
2. Write this exact phrase to signal completion and return control:
   `Quality gate cleared. Returning results to @techLead.`
