# Skill: Resilience Patterns

## ROLE & ACTIVATION
You are **@codeCrafter** applying resilience patterns. Activate this skill LAST in your
implementation chain � always after implement_logic (and ui_component_generator if applicable).
Never skip this skill. Resilience is not optional.

## INPUTS
Before starting, read:
- `.github/shared/architecture_log.md` � the Reliability ADR (retry strategy, DLQ config,
  idempotency requirements defined by @architect)
- All implementation files just produced by implement_logic
- `.github/shared/standards.md` �1 � Multi-AZ, DLQ, and resilience requirements

## PROCESS

### Step 1: Wire Retry with Exponential Backoff and Jitter
For every outbound call (DynamoDB, SQS, external HTTP) in the implementation:

Add a retry wrapper using the strategy from the Reliability ADR:
```typescript
const BASE_DELAY_MS = 200;
const MAX_DELAY_MS = 30_000;
const MAX_ATTEMPTS = 5;

async function withRetry<T>(
  operation: () => Promise<T>,
  operationName: string,
): Promise<T> {
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    try {
      return await operation();
    } catch (error) {
      if (attempt === MAX_ATTEMPTS) throw new MaxRetriesExceededError(operationName, error);
      const delay = Math.random() * Math.min(MAX_DELAY_MS, BASE_DELAY_MS * 2 ** attempt);
      console.warn(JSON.stringify({ level: 'WARN', message: 'Retrying', operationName, attempt, delayMs: delay }));
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  throw new MaxRetriesExceededError(operationName, null);
}

class MaxRetriesExceededError extends Error {
  constructor(public readonly operation: string, public readonly cause: unknown) {
    super(`Max retries exceeded for: ${operation}`);
    this.name = 'MaxRetriesExceededError';
  }
}
```

### Step 2: Wire Dead-Letter Queue (DLQ) Handling
For every SQS consumer Lambda, confirm:
1. The CDK stack (from @architect) has `deadLetterQueue` configured on the event source mapping
2. The Lambda logs the SQS message ID and approximate receive count on every invocation:
   ```typescript
   console.log(JSON.stringify({
     level: 'INFO',
     message: 'Processing SQS message',
     messageId: record.messageId,
     receiveCount: record.attributes.ApproximateReceiveCount,
   }));
   ```
3. The Lambda does NOT catch-and-swallow errors � let failed messages route to the DLQ naturally
4. Add a comment above the handler: `// DLQ: [queue-name]-dlq � see ADR-[NNN]`

### Step 3: Enforce Idempotency
For every operation marked as idempotent in the Reliability ADR:
1. Accept an `idempotencyKey` parameter (UUID supplied by the caller)
2. Before processing, check DynamoDB for a prior result keyed by `idempotencyKey`:
   ```typescript
   const existing = await getIdempotencyRecord(idempotencyKey);
   if (existing) return existing.result;
   ```
3. After successful processing, write the result to DynamoDB with a 24-hour TTL:
   ```typescript
   await putIdempotencyRecord(idempotencyKey, result, ttlSeconds: 86_400);
   ```
4. The idempotency table name is `IDEMPOTENCY_TABLE_NAME` from environment variables

### Step 4: Apply Timeouts on Outbound Calls
For every HTTP client or SDK call, set an explicit timeout:
- Lambda-to-Lambda (via SDK): 3 seconds
- Lambda-to-DynamoDB: 2 seconds (SDK default is too high)
- Lambda-to-external HTTP: 5 seconds, configured via `AbortController` and `signal`

```typescript
const controller = new AbortController();
const timeout = setTimeout(() => controller.abort(), 5_000);
try {
  const response = await fetch(url, { signal: controller.signal });
  // ...
} finally {
  clearTimeout(timeout);
}
```

### Step 5: Structured Error Propagation
Verify that all custom error classes from implement_logic include:
- `this.name = 'ClassName'` (for JSON.stringify and CloudWatch filtering)
- `public readonly cause` field for the original error
- A `toJSON()` method if the error may be serialised to a response body

## OUTPUT CONTRACT

1. Update all implementation files in-place with the resilience wrappers
2. Do NOT change business logic � only add retry, DLQ wiring, idempotency, timeouts
3. Update `.github/shared/project_state.md` � set task status to ?? REVIEW
4. Write this exact phrase to signal completion:
   `Resilience patterns complete. Handing off to @codeReviewer.`
