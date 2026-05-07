# Skill: Chaos Engineering Simulation

## ROLE & ACTIVATION
You are **@qualityGuard** running chaos engineering simulations. Activate this skill SEVENTH in
the quality chain — immediately after `Integration tests complete. Activating chaos_engineering_simulation.`

## INPUTS
Before starting, read:
- `.github/shared/architecture_log.md` — reliability ADR: failure modes, RTO/RPO targets, DLQ config
- @codeCrafter's `resilience_patterns` output: retry logic, circuit breakers, timeouts, DLQ wiring
- All Lambda handlers and integration points in the current task

## PROCESS

### Step 1: Enumerate Failure Scenarios
From the architecture_log.md reliability ADR, list every declared failure mode. Add any not covered:

| # | Failure Scenario | Expected Behaviour | Resilience Control |
|---|-----------------|-------------------|-------------------|
| 1 | Downstream API returns 503 | Retry with backoff; DLQ after MAX_ATTEMPTS | withRetry + DLQ |
| 2 | DynamoDB throttles (ProvisionedThroughputExceeded) | Retry with exponential backoff | AWS SDK built-in |
| 3 | SQS message processing takes > visibility timeout | Message reappears; idempotency prevents double-processing | Idempotency key |
| 4 | Lambda cold start spike > 3s | Response still within P99 SLO (warm pool or Provisioned Concurrency) | ProvisionedConcurrency |
| 5 | Legacy bridge API times out | Graceful degradation: fallback response or fail-open/closed per ADR | Circuit breaker |
| 6 | S3 PUT fails mid-workflow | Transaction rolled back; no partial state | Saga / compensation |

For each scenario not covered by `resilience_patterns`, raise a gap:
```
[CHAOS GAP] Scenario <N>: <failure> — no resilience control documented in ADR
ACTION REQUIRED: @architect must update reliability ADR; @codeCrafter must add control
```

### Step 2: Write Chaos Unit Tests
For every scenario in Step 1, write a Jest test that injects the failure and asserts the
expected degraded behaviour:

```typescript
// src/__tests__/chaos/downstreamTimeout.chaos.test.ts
import { mockClient } from 'aws-sdk-client-mock';
import { SQSClient, SendMessageCommand } from '@aws-sdk/client-sqs';

const sqsMock = mockClient(SQSClient);

describe('chaos: downstream API timeout', () => {
  it('should enqueue to DLQ after MAX_ATTEMPTS retries', async () => {
    // Simulate persistent 503 from downstream
    fetchMock.mockReject(new Error('ServiceUnavailableError'));

    await expect(processOrder(mockEvent)).rejects.toThrow('MaxRetriesExceededError');

    // Verify DLQ received the failed message
    expect(sqsMock.commandCalls(SendMessageCommand)).toHaveLength(1);
    const dlqMsg = sqsMock.commandCalls(SendMessageCommand)[0].args[0].input;
    expect(dlqMsg.QueueUrl).toContain('-dlq');
  });
});
```

For each scenario, assert:
- The error is caught (service does NOT crash or return 500 to the caller unhandled)
- The correct fallback behaviour occurs (DLQ write, circuit open, cached response returned)
- Structured error log is emitted with the correct severity and error type

### Step 3: Partial Failure and Cascade Prevention
Test that a failure in one component does NOT cascade to unrelated components:
1. Mock one Lambda dependency to always throw
2. Verify other Lambda invocations in the same workflow still succeed
3. Verify the failed branch is isolated (DLQ, dead-letter, or circuit open)

```typescript
it('should isolate notification failure from order processing success', async () => {
  notificationMock.mockRejectedValue(new Error('NotificationServiceDown'));

  const result = await processOrder(mockEvent); // Order processing still completes

  expect(result.status).toBe('PROCESSED');
  expect(result.notificationStatus).toBe('DEFERRED'); // Not 'FAILED'
});
```

### Step 4: Recovery Simulation
For each failure scenario in Step 1, write a recovery test:
- After failure is injected for N calls, remove the mock failure
- Verify the service self-heals without a restart (circuit breaker closes, retry succeeds)

```typescript
it('should recover and succeed after transient 503 storm', async () => {
  let callCount = 0;
  fetchMock.mockImplementation(() => {
    callCount++;
    if (callCount <= 3) throw new Error('503');
    return Promise.resolve({ status: 200, json: async () => ({ ok: true }) });
  });

  const result = await processOrderWithRetry(mockEvent);
  expect(result.ok).toBe(true);
  expect(callCount).toBe(4); // 3 failures + 1 success
});
```

### Step 5: RTO/RPO Assertion
From the reliability ADR, extract declared RTO and RPO targets. Assert:
- **RTO**: the time from failure detection to service resuming normal operation (mocked timer)
  is within the declared RTO
- **RPO**: after a simulated crash-recovery cycle, the most recent committed write is recoverable
  from DynamoDB PITR or the SQS message replay

If no RTO/RPO is declared in the ADR:
```
[CHAOS GAP] No RTO/RPO targets declared in architecture_log.md
ACTION REQUIRED: @architect must define recovery targets in the reliability ADR
```

## OUTPUT CONTRACT

**If any CHAOS GAP findings exist:**
- List all gaps and tag @architect and @codeCrafter for each
- Write `Returning to @techLead` with the gap list before proceeding

**If all chaos scenarios pass:**
1. Write chaos test files to `src/__tests__/chaos/`
2. Append a resilience sign-off summary to `.github/shared/project_state.md`
3. Write this exact phrase to signal completion:
   `Chaos simulation complete. Activating performance_benchmark_gate.`
