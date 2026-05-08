# Skill: Secure Coding Standards

## ROLE & ACTIVATION
You are **@codeCrafter** applying security hardening at the implementation phase. Activate after
`add_dependencies` and before `implement_logic`. Catching vulnerabilities here is cheaper than
catching them in `@qualityGuard/penetration_scan` — this skill is the shift-left security gate.

## INPUTS
Before starting, read:
- `.github/shared/standards.md` — security rules the project has committed to
- `.github/shared/architecture_log.md` — security ADRs (IAM posture, encryption decisions)
- The handoff from @techLead (what feature is being built, what data it touches)
- The API contract file produced by `api_contract_design` (inputs that will flow into the feature)

## PROCESS

### Step 1: Input Validation Rules
For every field in every request schema (from the contracts file), define explicit validation:

| Field Type | Required Validation |
|-----------|-------------------|
| String ID (UUID) | Regex: `/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i` |
| Free-text string | Max length, strip leading/trailing whitespace, no `<script>` tags (XSS) |
| Enum | Allowlist check only — reject anything not in the defined union |
| Numeric | Min/max bounds, integer-only where applicable, no NaN/Infinity |
| Date/time | ISO-8601 parse check, reject future dates where domain requires past |
| File upload | MIME type allowlist, max file size, filename sanitization |

Write a validation function per request type using the project's validation library (Zod for
TypeScript, Pydantic for Python, Bean Validation for Java). Never trust the framework to validate
by default — make it explicit.

```typescript
// TypeScript example with Zod
import { z } from 'zod';

export const CreateOrderRequestSchema = z.object({
  customerId: z.string().uuid(),
  items: z.array(z.object({
    productId: z.string().uuid(),
    quantity: z.number().int().min(1).max(999),
    unitPriceCents: z.number().int().positive(),
  })).min(1).max(100),
  idempotencyKey: z.string().uuid(),
});
```

### Step 2: Injection Attack Prevention

| Attack | Context | Mitigation |
|--------|---------|-----------|
| SQL Injection | RDS / Aurora | Parameterized queries only — never string concatenation |
| NoSQL Injection | DynamoDB | Use typed SDK methods — never raw expression with unvalidated input |
| Command Injection | Any `exec()` / `spawn()` / shell call | Allowlist args; never pass user input to shell commands |
| LDAP Injection | Auth flows | Escape special chars; prefer SDK/library over raw LDAP queries |
| Template Injection | Email / PDF generation | Use template engines with auto-escaping; never `eval()` |

For DynamoDB specifically — ensure expression attribute values are always used:
```typescript
// SAFE
const result = await client.send(new GetCommand({
  TableName: TABLE_NAME,
  Key: { pk: validatedCustomerId },   // validated UUID — safe
}));

// UNSAFE — never do this
const result = await client.send(new QueryCommand({
  FilterExpression: `customerId = ${rawInput}`,  // injection risk
}));
```

### Step 3: Authentication and Authorization Checks
For every endpoint in the API contract:

| Check | Requirement |
|-------|------------|
| Auth token validated | JWT signature verified using Cognito JWKS or equivalent — never `decode()` without verify |
| Claims extracted safely | Use `sub`, `email`, `custom:role` from verified token — never from request body |
| Resource ownership enforced | After fetching a resource, confirm `resource.ownerId === tokenSub` before returning |
| Admin actions gated | Privilege-elevated operations check a specific role claim — not just "is authenticated" |

Write the ownership check as a utility function, not inline per handler:
```typescript
function assertResourceOwnership(resource: { ownerId: string }, tokenSub: string): void {
  if (resource.ownerId !== tokenSub) {
    throw new ForbiddenError(`Token subject does not own resource`);
  }
}
```

### Step 4: Sensitive Data Handling
- Never log PII fields (email, phone, SSN, card numbers, account numbers)
- Never return more fields than the API contract specifies (no accidental over-fetch)
- Mask any ID in logs to last 4 characters: `***-${id.slice(-4)}`
- Secrets (API keys, DB passwords) sourced from Secrets Manager only — never `process.env` for secrets

```typescript
// Safe log helper
function maskId(id: string): string {
  return `***-${id.slice(-4)}`;
}
```

### Step 5: Dependency Security Snapshot
Before implementing, verify the dependencies added in `add_dependencies` have no known CVEs
at the versions pinned:

```
npm audit --audit-level=high
```

If any HIGH or CRITICAL CVEs are found: do not proceed to `implement_logic`. Document the finding
and propose a patched version or an alternative library. @techLead must approve before continuing.

### Step 6: Security Checklist
Run through this checklist for the specific feature in scope:

| OWASP Top 10 Control | Applied? | Notes |
|---------------------|---------|-------|
| A01 Broken Access Control | [ ] | Ownership check written? |
| A02 Cryptographic Failures | [ ] | No plaintext secrets? Encryption at rest confirmed? |
| A03 Injection | [ ] | All inputs validated + parameterized queries? |
| A05 Security Misconfiguration | [ ] | No debug endpoints in prod? Error messages safe? |
| A06 Vulnerable Components | [ ] | `npm audit` / `pip-audit` passed? |
| A07 Auth Failures | [ ] | Token verified (not just decoded)? |
| A09 Logging Failures | [ ] | No PII in logs? Audit trail for sensitive actions? |

## OUTPUT CONTRACT

1. Write validation schemas to `src/validation/[feature-name].schema.ts` (or equivalent path)
2. Write the auth/ownership utility to `src/utils/auth.ts` if it does not already exist
3. Append any HIGH/CRITICAL CVE findings to `.github/shared/project_state.md` as blockers
4. If a HIGH/CRITICAL CVE is found:
   - Write this exact phrase to block the workflow:
     `SECURITY FAIL: [CVE ID] found in [package@version] — blocks implementation`
5. If all checks pass:
   - Write this exact phrase to chain to implementation:
     `Secure coding baseline established. Activating implement_logic.`
