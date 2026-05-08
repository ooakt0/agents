# Skill: Integration Tests

## ROLE & ACTIVATION
You are **@qualityGuard** writing integration tests. Activate this skill THIRD in the quality
chain � after mock_aws_responses completes.

## INPUTS
Before starting, read:
- All implementation files from @codeCrafter
- `.github/shared/architecture_log.md` � Reliability ADR (DLQ config, idempotency, RTO/RPO)
- All unit test files (to avoid duplication � integration tests test flow, not units)

## PROCESS

### Step 1: Spin Up LocalStack
Integration tests run against LocalStack for real AWS service behaviour without incurring costs.
Add a `jest.globalSetup.ts` if not already present:
```typescript
// jest.globalSetup.ts
import { execSync } from 'child_process';

export default async function globalSetup() {
  execSync('docker-compose -f docker-compose.localstack.yml up -d --wait', { stdio: 'inherit' });
}
```

And a `docker-compose.localstack.yml` at project root if not present:
```yaml
version: '3.8'
services:
  localstack:
    image: localstack/localstack:3
    ports:
      - '4566:4566'
    environment:
      - SERVICES=dynamodb,sqs,s3,secretsmanager,ssm
      - DEFAULT_REGION=us-east-1
```

### Step 2: Bootstrap Test Infrastructure
Before tests run, create all required AWS resources in LocalStack via CDK or AWS SDK:
```typescript
// tests/integration/setup.ts
import { CreateTableCommand, DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { CreateQueueCommand, SQSClient } from '@aws-sdk/client-sqs';

const ENDPOINT = 'http://localhost:4566';
const ddb = new DynamoDBClient({ endpoint: ENDPOINT, region: 'us-east-1' });
const sqs = new SQSClient({ endpoint: ENDPOINT, region: 'us-east-1' });

export async function bootstrapResources() {
  await ddb.send(new CreateTableCommand({
    TableName: process.env.TABLE_NAME!,
    AttributeDefinitions: [{ AttributeName: 'id', AttributeType: 'S' }],
    KeySchema: [{ AttributeName: 'id', KeyType: 'HASH' }],
    BillingMode: 'PAY_PER_REQUEST',
  }));
  await sqs.send(new CreateQueueCommand({ QueueName: process.env.QUEUE_NAME! }));
}
```

### Step 3: Write End-to-End Flow Tests
Test the complete happy path through the system:
1. Trigger the entry point (HTTP event, SQS message, etc.)
2. Assert all intermediate state changes (DynamoDB writes, SQS sends)
3. Assert the final output matches the expected result

Example:
```typescript
it('should process an order end-to-end', async () => {
  // Arrange: seed DynamoDB
  await putItem({ id: 'cust-001', balance: 500 });
  // Act: trigger handler
  const result = await handler(orderEvent);
  // Assert: response
  expect(result.statusCode).toBe(200);
  // Assert: DynamoDB state
  const order = await getItem('ord-001');
  expect(order.status).toBe('CONFIRMED');
});
```

### Step 4: Test DLQ Flow
For every SQS consumer Lambda:
1. Send a message that will cause the Lambda to throw (e.g., malformed body)
2. Allow the maximum receive count to be reached (set `maxReceiveCount: 1` in test queue)
3. Assert the message appears in the DLQ
4. Assert a structured error log was emitted

```typescript
it('should route failed messages to DLQ', async () => {
  await sqs.send(new SendMessageCommand({ QueueUrl: QUEUE_URL, MessageBody: 'INVALID' }));
  // Invoke handler directly with the malformed message
  await expect(handler(malformedEvent)).rejects.toThrow();
  // Assert DLQ has message
  const dlq = await sqs.send(new ReceiveMessageCommand({ QueueUrl: DLQ_URL }));
  expect(dlq.Messages).toHaveLength(1);
});
```

### Step 5: Test Idempotency End-to-End
1. Submit the same request twice with the same `idempotencyKey`
2. Assert the handler is only called once (check DynamoDB write count or spy)
3. Assert the second call returns the same result as the first

```typescript
it('should be idempotent for the same key', async () => {
  const key = 'idem-key-001';
  const result1 = await handler({ ...event, idempotencyKey: key });
  const result2 = await handler({ ...event, idempotencyKey: key });
  expect(result1).toEqual(result2);
  // Verify only one DynamoDB write (not two)
  const record = await getIdempotencyRecord(key);
  expect(record.processedAt).toBe(result1.processedAt);
});
```

## OUTPUT CONTRACT

1. Write all integration test files to `tests/integration/`
2. Write `docker-compose.localstack.yml` at project root if not already present
3. Write `jest.globalSetup.ts` if not already present
4. Update `jest.config.ts` to include `globalSetup` for the integration test project
5. Write this exact phrase to signal completion:
   `Integration tests complete. Activating load_test.`
