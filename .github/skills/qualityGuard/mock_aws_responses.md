# Skill: Mock AWS Responses

## ROLE & ACTIVATION
You are **@qualityGuard** building the AWS mock barrel. Activate this skill SECOND in the
quality chain � after write_unit_tests completes.

## INPUTS
Before starting, read:
- All unit test files just written by write_unit_tests
- All implementation files from @codeCrafter
- `.github/shared/architecture_log.md` � identify every AWS service used (DynamoDB tables,
  SQS queues, S3 buckets, SSM parameters, Secrets Manager secrets)

## PROCESS

### Step 1: Inventory All AWS Service Calls
List every AWS SDK client used in the implementation:
- `DynamoDBDocumentClient` � which commands: `GetCommand`, `PutCommand`, `QueryCommand`, etc.
- `SQSClient` � which commands: `SendMessageCommand`, `ReceiveMessageCommand`, etc.
- `S3Client` � which commands: `GetObjectCommand`, `PutObjectCommand`, etc.
- `SecretsManagerClient` � `GetSecretValueCommand`
- `SSMClient` � `GetParameterCommand`

### Step 2: Create the Mock Barrel
Create `src/__mocks__/aws.ts` as a centralized, typed barrel of all mock clients and
realistic fixture data:

```typescript
// src/__mocks__/aws.ts
import { mockClient } from 'aws-sdk-client-mock';
import { DynamoDBDocumentClient } from '@aws-sdk/lib-dynamodb';
import { SQSClient } from '@aws-sdk/client-sqs';
import { S3Client } from '@aws-sdk/client-s3';
import { SecretsManagerClient } from '@aws-sdk/client-secrets-manager';

export const ddbMock = mockClient(DynamoDBDocumentClient);
export const sqsMock = mockClient(SQSClient);
export const s3Mock = mockClient(S3Client);
export const secretsMock = mockClient(SecretsManagerClient);

// -- Realistic Fixtures --------------------------------------------------------

export const fixtures = {
  order: {
    id: 'ord-001',
    customerId: 'cust-001',
    status: 'PENDING',
    amount: 99.99,
    createdAt: '2024-01-15T10:00:00.000Z',
  },
  sqsMessage: {
    MessageId: 'msg-001',
    ReceiptHandle: 'receipt-handle-001',
    Body: JSON.stringify({ orderId: 'ord-001' }),
    Attributes: { ApproximateReceiveCount: '1' },
  },
  secret: {
    SecretString: JSON.stringify({ apiKey: 'test-key-001', endpoint: 'https://test.example.com' }),
  },
};

// -- Reset Helper (call in beforeEach) -----------------------------------------

export function resetAllMocks() {
  ddbMock.reset();
  sqsMock.reset();
  s3Mock.reset();
  secretsMock.reset();
}
```

### Step 3: Update Unit Tests to Import from Barrel
Replace any inline `mockClient()` calls in unit tests with imports from `src/__mocks__/aws.ts`:
```typescript
import { ddbMock, fixtures, resetAllMocks } from '../__mocks__/aws';

beforeEach(() => resetAllMocks());
```

### Step 4: Add Error Scenario Fixtures
Add realistic AWS error fixtures for every error path tested:
```typescript
import { DynamoDBServiceException } from '@aws-sdk/client-dynamodb';

export const errors = {
  dynamoDBThrottle: new DynamoDBServiceException({
    name: 'ProvisionedThroughputExceededException',
    message: 'The level of configured provisioned throughput has been exceeded.',
    $fault: 'client',
    $metadata: { httpStatusCode: 400 },
  }),
  dynamoDBNotFound: new DynamoDBServiceException({
    name: 'ResourceNotFoundException',
    message: 'Requested resource not found',
    $fault: 'client',
    $metadata: { httpStatusCode: 400 },
  }),
};
```

### Step 5: Verify Type Safety
All mock setups and fixtures must be fully typed � no `as any`:
- Use the actual command input/output types from the AWS SDK
- Verify `fixtures.order` matches the DynamoDB item type used in the implementation

## OUTPUT CONTRACT

1. Write `src/__mocks__/aws.ts` with all mock clients, fixtures, and error scenarios
2. Update all unit test files to import from the barrel
3. Write this exact phrase to signal completion:
   `Mock AWS responses complete. Activating integration_test.`
