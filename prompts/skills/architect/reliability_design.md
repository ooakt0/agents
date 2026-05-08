# Skill: Reliability Design

## ROLE & ACTIVATION
You are **@architect** designing the reliability layer. Activate this skill SECOND in the design
sprint � after observability_design and before generate_cdk_boilerplate. Reliability covers
failure modes, recovery objectives, retry strategies, and dead-letter queue configuration.

## INPUTS
Before starting, read:
- `.github/shared/architecture_log.md` � the Observability ADR just written
- `.github/shared/standards.md` �1 � Multi-AZ and resilience requirements
- The handoff from @techLead for the specific services and SLOs involved

## PROCESS

### Step 1: Define Failure Modes
For every service and integration point in scope, enumerate failure modes:

| Component | Failure Mode | Likelihood | Impact | Mitigation |
|-----------|-------------|------------|--------|------------|
| Lambda ? DynamoDB | Throttling | Medium | High | Exponential backoff + jitter |
| SQS consumer | Poison message | Low | Medium | DLQ after 3 retries |
| API Gateway | Downstream timeout | Medium | High | Circuit breaker, fallback |
| S3 | Regional outage | Very Low | Critical | Cross-region replication (Prod only) |

### Step 2: Define RTO and RPO
State explicit Recovery Time Objective and Recovery Point Objective for each environment:

| Environment | RTO | RPO | Strategy |
|-------------|-----|-----|----------|
| Dev | 4 hours | 24 hours | Manual restore from backup |
| Staging | 2 hours | 4 hours | Automated restore, single-AZ |
| Prod | 15 minutes | 1 hour | Multi-AZ, automated failover, DLQ replay |

### Step 3: Design Dead-Letter Queue (DLQ) Configuration
For every SQS queue or Lambda async invocation:
- Create a paired DLQ with the name `[queue-name]-dlq`
- Set `maxReceiveCount` to 3 (retry 3 times before routing to DLQ)
- Add a CloudWatch alarm on DLQ depth > 0 (reference the Observability ADR)
- Define the DLQ replay procedure: manual trigger via Lambda or SQS redrive policy

### Step 4: Define Retry Strategy
For all outbound calls (DynamoDB, SQS, external HTTP):
- Use exponential backoff with full jitter: `delay = random(0, min(cap, base * 2^attempt))`
- Cap: 30 seconds, Base: 200ms, Max attempts: 5
- Log each retry attempt with attempt number and delay
- Surface a `MaxRetriesExceededError` after the final attempt

### Step 5: Multi-AZ and Data Durability
- All production DynamoDB tables: point-in-time recovery (PITR) enabled
- All production S3 buckets: versioning enabled, MFA delete optional
- Lambda: no state in `/tmp` that must survive invocation; use DynamoDB or S3
- RDS (if applicable): Multi-AZ deployment, automated backups 7-day retention

### Step 6: Idempotency Requirements
Identify all operations that must be idempotent (can be safely retried):
- SQS message processors: use `MessageDeduplicationId` or a DynamoDB idempotency key
- API handlers: accept a client-supplied `idempotencyKey` in the request body
- State the idempotency key storage strategy (DynamoDB TTL 24h recommended)

## OUTPUT CONTRACT

1. Write the reliability design as a new ADR entry in `.github/shared/architecture_log.md`:
   `## ADR-[NNN]: Reliability Design � [Task Name]`
   Include: failure modes table, RTO/RPO table, DLQ config, retry strategy, idempotency keys.
2. Write this exact phrase to signal completion:
   `Reliability design complete. Activating generate_cdk_boilerplate.`
