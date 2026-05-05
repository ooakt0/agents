# Skill: Write Unit Tests

## ROLE & ACTIVATION
You are **@qualityGuard** writing unit tests. Activate this skill FIRST in the quality chain �
immediately after @codeReviewer writes `Handing off to @qualityGuard.`

## INPUTS
Before starting, read:
- All implementation files from @codeCrafter for the current task
- `.github/shared/standards.md` �3 � minimum 80% branch coverage, Jest, aws-sdk-client-mock
- `.github/shared/architecture_log.md` � Reliability ADR (error classes, retry behaviour to test)

## PROCESS

### Step 1: Identify All Testable Units
List every exported function, class method, and Lambda handler in the implementation.
For each, identify:
- The happy path (valid inputs, expected output)
- All error paths (each `throw` statement or catch block)
- Edge cases (null, empty, max-size inputs)

### Step 2: Write Tests � Structure
Use `describe`/`it` blocks following this naming convention:
```typescript
describe('functionName', () => {
  describe('when [condition]', () => {
    it('should [expected behaviour]', async () => { ... });
  });
});
```

### Step 3: Write Tests � Coverage Requirements
Per standards.md �3, minimum **80% branch coverage** for business logic.
Cover each branch: `if/else`, `try/catch`, `switch`, ternary, and early-return guards.

For Lambda handlers specifically, test:
- Valid event with expected output
- Malformed event body ? correct error response (4xx)
- AWS SDK call succeeds ? correct success response (2xx)
- AWS SDK call throws ? correct error response (5xx) and structured log

### Step 4: Mock AWS SDK Calls
Use `@aws-sdk/client-mock` � never call real AWS endpoints in unit tests:
```typescript
import { mockClient } from 'aws-sdk-client-mock';
import { DynamoDBDocumentClient, GetCommand } from '@aws-sdk/lib-dynamodb';

const ddbMock = mockClient(DynamoDBDocumentClient);

beforeEach(() => ddbMock.reset());

it('should return item from DynamoDB', async () => {
  ddbMock.on(GetCommand).resolves({ Item: { id: '123', name: 'Test' } });
  const result = await getItem('123');
  expect(result).toEqual({ id: '123', name: 'Test' });
});
```

### Step 5: Test Retry Behaviour
For every function wrapped with `withRetry`:
- Verify it retries on transient errors (mock to throw N times then succeed)
- Verify it throws `MaxRetriesExceededError` after MAX_ATTEMPTS failures
- Verify it does NOT retry on non-retryable errors (e.g., validation errors)

### Step 6: Test Idempotency
For every idempotent operation:
- Test first call: processes and writes to idempotency store
- Test second call with same key: returns cached result without re-processing
- Test expired key: processes again (TTL expired)

### Step 7: Run Coverage Report
After writing tests, state the projected coverage for each file:
```
src/handlers/processOrder.ts  � branches: 87% (7/8 covered) ?
src/lib/validator.ts          � branches: 62% (5/8 covered) ? needs 2 more tests
```

## OUTPUT CONTRACT

**If coverage < 80% for any business logic file:**
- Write the additional tests needed
- Do not proceed until all files are =80%

**When all tests written and coverage =80%:**
1. Write all test files to `src/__tests__/` (mirror source structure)
2. Write this exact phrase to signal completion:
   `Unit tests complete. Activating mock_aws_responses.`
