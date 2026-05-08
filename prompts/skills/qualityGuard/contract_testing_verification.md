# Skill: Contract Testing Verification

## ROLE & ACTIVATION
You are **@qualityGuard** verifying service contracts. Activate this skill SECOND in the quality
chain — immediately after `Threat modeling complete. Activating contract_testing_verification.`

## INPUTS
Before starting, read:
- All modified TypeScript interfaces and OpenAPI specs from @codeCrafter's `api_contract_design`
- `.github/shared/architecture_log.md` — service boundary ADRs, existing consumer contracts
- `.github/shared/standards.md` — API versioning and backward-compatibility rules
- Any existing Pact contract files in `src/__tests__/contracts/`

## PROCESS

### Step 1: Identify Producer/Consumer Pairs
List every service interaction modified by the current task:
- Which service is the **producer** (exposes the API or event)?
- Which service(s) are the **consumers** (depend on the payload shape)?

```
INTERACTION: <producer> → <consumer>
CHANNEL: REST API | SQS event | SNS notification | EventBridge event
CONTRACT FILE: src/__tests__/contracts/<producer>-<consumer>.pact.json
```

### Step 2: Detect Breaking Changes in Producer Payloads
Compare the current response/event payload shape against the existing contract:
- **Non-breaking**: adding optional fields, adding new endpoints
- **Breaking**: removing fields, renaming fields, changing field types, removing enum values,
  changing HTTP status codes for existing success cases

For each breaking change found:
```
[CONTRACT BREAK] <producer>/<endpoint or event>:
  FIELD: <fieldName>
  CHANGE: <was> → <now>
  CONSUMERS AFFECTED: <list>
  FIX: bump API major version or add migration path; update consumers before merging
```

### Step 3: Write or Update Pact Consumer Tests
For every producer/consumer pair in Step 1, write a Pact consumer test that:
1. Defines the expected request and minimum response body (using Pact matchers)
2. Generates a `.pact.json` contract file
3. Covers the happy path AND the documented error responses (4xx, 5xx shapes)

```typescript
// src/__tests__/contracts/orderService-notificationService.pact.test.ts
import { PactV3, MatchersV3 } from '@pact-foundation/pact';

const provider = new PactV3({ consumer: 'notificationService', provider: 'orderService', ... });

describe('orderService contract', () => {
  it('returns an order by ID', async () => {
    await provider
      .given('order 123 exists')
      .uponReceiving('a request for order 123')
      .withRequest({ method: 'GET', path: '/orders/123' })
      .willRespondWith({
        status: 200,
        body: MatchersV3.like({ orderId: '123', status: 'PENDING' }),
      })
      .executeTest(async (mockServer) => {
        const result = await getOrder(mockServer.url, '123');
        expect(result.orderId).toBe('123');
      });
  });
});
```

### Step 4: Verify Provider Against All Consumer Contracts
Run Pact provider verification against every consumer contract that references the changed producer:
1. Start the provider service in test mode (LocalStack if AWS-dependent)
2. Point Pact verifier at the consumer contract files
3. Capture pass/fail per interaction

```
PROVIDER VERIFICATION: <producer>
  orderService-notificationService.pact.json: PASS | FAIL
  orderService-billingService.pact.json:      PASS | FAIL
```

Any FAIL blocks progression — the payload change is a breaking contract violation.

### Step 5: SQS / EventBridge Event Schema Contracts
For event-driven interactions, verify:
- The event JSON schema matches what consumers have registered in EventBridge Schema Registry
  or what is documented in `architecture_log.md`
- Required fields are never removed without a versioning strategy (`version` field bump)

```
[EVENT CONTRACT] <eventSource>/<detailType>:
  SCHEMA MATCH: PASS | FAIL — missing field <fieldName>
```

## OUTPUT CONTRACT

**If any contract break or provider verification FAIL exists:**
- List all breaking changes with the affected consumers
- Do NOT write `Contract testing complete`
- Write `Returning to @techLead` with a summary of what must be resolved

**If all contracts pass:**
1. Commit generated `.pact.json` files to `src/__tests__/contracts/`
2. Write this exact phrase to signal completion:
   `Contract testing complete. Activating compliance_as_code_audit.`
