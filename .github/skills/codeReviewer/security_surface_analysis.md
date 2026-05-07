# Skill: Security Surface Analysis

## ROLE & ACTIVATION
You are **@codeReviewer** performing a proactive security surface analysis. Activate this skill
THIRD in your review chain — immediately after `breaking_change_detection` passes.
Go beyond CVE scanning: find logic-level vulnerabilities and measure how the new code expands
the application's attack surface.

## INPUTS
Before starting, read:
- All files written or modified by @codeCrafter in the current task
- `.github/shared/standards.md` §security — authentication, authorization, and data handling rules
- `.github/shared/architecture_log.md` — IAM decisions, security group rules, approved data flows
- `.github/shared/project_context.md` — integration boundaries, known sensitive data types

## PROCESS

### Step 1: Authorization Coverage Audit
For every new or modified API endpoint, Lambda handler, or queue consumer:

Check for the presence of an authorization check **before** any business logic executes:
- Is the caller's identity verified (JWT validation, Cognito authorizer, API Gateway IAM)?
- Is the caller's permission checked (RBAC role check, ownership assertion, policy evaluation)?
- Is there a missing `if (!user.hasRole('admin'))` before a privileged operation?

```
[AUTH MISSING] POST /admin/users — no authorization check found before user creation
RISK: Any authenticated user can create admin accounts
FIX: Add role check `requireRole(req, 'admin')` before handler logic (line X)
```

### Step 2: Sensitive Data Exposure in Logs
Scan all `console.log`, `logger.info`, `logger.error`, and structured log statements for:
- PII fields: email, name, phone, address, SSN, date of birth
- Secrets: passwords, tokens, API keys, private keys
- Financial data: card numbers, account numbers, CVV
- Internal system identifiers that could aid enumeration attacks

```
[PII LEAK] logger.info('User login', { user }) in auth.service.ts:47
RISK: Full user object including email and role written to CloudWatch
FIX: Log only user.id and user.role — never the full object
```

### Step 3: IAM Least Privilege Check
For every new IAM role, policy, or permission added in CDK or CloudFormation:
- Flag any `*` resource wildcard on write actions (e.g., `s3:PutObject` on `*`)
- Flag any `*` action wildcard (e.g., `"Action": "*"`)
- Flag cross-account trust policies not present in `architecture_log.md`
- Verify KMS key policies restrict access to the named service only

```
[IAM OVER-PRIVILEGE] LambdaExecutionRole grants s3:* on arn:aws:s3:::*
RISK: Lambda can read/write/delete any bucket in the account
FIX: Scope to s3:GetObject, s3:PutObject on arn:aws:s3:::my-specific-bucket/*
```

### Step 4: Injection Surface Check
For every location where external input (request body, query params, path params, message body,
environment variables) flows into a downstream call:

- **SQL**: Is input passed through parameterized queries or an ORM? Raw string concatenation → FAIL
- **NoSQL**: Is input used in a filter query without schema validation (Zod/class-validator)? → FAIL
- **Shell**: Is any `exec()`, `spawn()`, or `child_process` call present? → FAIL unless justified
- **SSRF**: Is a user-supplied URL passed to `fetch()`, `axios`, or `http.request()`? → FAIL unless allowlisted
- **Path traversal**: Is user input used to construct a file path without sanitization? → FAIL

```
[INJECTION] db.query(`SELECT * FROM orders WHERE id = '${req.params.id}'`) in orders.repo.ts:23
RISK: SQL injection — attacker controls query structure
FIX: db.query('SELECT * FROM orders WHERE id = $1', [req.params.id])
```

### Step 5: Secrets and Configuration Hygiene
Scan all new and modified files for:
- Hardcoded credentials, API keys, tokens, or passwords (any string matching common secret patterns)
- Any secret value committed to source (even in test files or comments)
- Environment variables read with a fallback to a hardcoded default secret value

```
[SECRET] const API_KEY = 'sk-live-abc123' in integrations/stripe.ts:5
RISK: Secret committed to repository history
FIX: Use process.env.STRIPE_API_KEY — rotate the exposed key immediately
```

If any secret is found, output `SECURITY FAIL: hardcoded secret in [file]:[line]` — this phrase
triggers the hook that blocks the entire workflow.

### Step 6: Attack Surface Delta Summary
After all checks, produce a concise summary of how the new code changes the attack surface:

```
ATTACK SURFACE DELTA for T-XXX:
+ New public endpoints: POST /orders, GET /orders/:id
+ New IAM permissions: s3:GetObject on order-attachments bucket
+ New external integrations: Stripe webhook receiver
- Removed: legacy /admin/legacy-import endpoint (attack surface reduced)
NET CHANGE: [EXPANDED / NEUTRAL / REDUCED] — [one-sentence justification]
```

## OUTPUT CONTRACT

**If `SECURITY FAIL` phrase was produced (CRITICAL BLOCK):**
- The hook will block the workflow automatically
- Also write:
  `Security surface analysis CRITICAL FAIL. Workflow blocked. @techLead must review before any further action.`

**If HIGH or CRITICAL findings exist without a secret (FAIL):**
1. List every finding with file, line, risk, and fix
2. Do NOT proceed to `complexity_check`
3. Write:
   `Security surface analysis FAILED. Returning to @codeCrafter with [N] findings. Do not proceed until fixed.`

**If only LOW/INFO findings (PASS WITH NOTES):**
1. Record findings in `.github/shared/project_state.md` under the task
2. Write: `Security surface analysis passed.`
3. Immediately activate the `complexity_check` skill — do not wait for user input

**If no findings (PASS):**
1. Write: `Security surface analysis passed.`
2. Immediately activate the `complexity_check` skill — do not wait for user input
