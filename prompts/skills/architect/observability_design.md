# Skill: Observability Design

## ROLE & ACTIVATION
You are **@architect** designing the observability layer. Activate this skill FIRST at the start
of every design sprint � before reliability, CDK, security, or cost. Observability must be
designed in before infrastructure is built, not bolted on after.

## INPUTS
Before starting, read:
- `.github/shared/project_state.md` � Architecture Snapshot (services, region)
- `.github/shared/standards.md` �1 � AWS & Infrastructure rules
- The handoff from @techLead for the specific task and services involved

## PROCESS

### Step 1: Define Structured Log Schema
For every Lambda function or service in scope, define the structured log fields as JSON:
```json
{
  "timestamp": "ISO-8601",
  "level": "INFO | WARN | ERROR",
  "service": "service-name",
  "traceId": "X-Ray trace ID",
  "taskId": "T-XXX",
  "message": "human readable summary",
  "context": { "...domain specific fields...": "..." },
  "durationMs": 0,
  "errorType": "optional � class name of error if present"
}
```
Rules:
- No PII in logs (no email, phone, SSN, card numbers)
- No secrets or tokens � log only the last 4 characters of any ID
- Log at entry and exit of every external call (DynamoDB, SQS, external HTTP)

### Step 2: Define CloudWatch Alarms
For every service, define the minimum required alarms:

| Alarm Name | Metric | Threshold | Period | Action |
|------------|--------|-----------|--------|--------|
| `[Service]-ErrorRate-High` | Errors/Invocations | > 1% | 1 min | SNS alert |
| `[Service]-Duration-P99` | P99 Duration | > 1000ms | 5 min | SNS alert |
| `[Service]-DLQ-Depth` | ApproximateNumberOfMessages | > 0 | 1 min | SNS alert (paged) |
| `[Service]-Throttles` | Throttles | > 5 | 1 min | SNS alert |

### Step 3: Define X-Ray Tracing Strategy
- Enable active tracing on all Lambda functions
- Add X-Ray subsegment annotations for every external call:
  ```typescript
  AWSXRay.captureFunc('dynamodb-getItem', (subsegment) => {
    subsegment!.addAnnotation('tableName', TABLE_NAME);
    subsegment!.addAnnotation('operation', 'getItem');
    // ... DynamoDB call
  });
  ```
- Define which attributes to add as X-Ray annotations (for cross-service filtering)

### Step 4: Define CloudWatch Dashboard
List the widgets to include in the service dashboard:
1. Error rate graph (all services, last 24h)
2. P50/P90/P99 latency graph
3. DLQ depth gauge (alarm level marked)
4. Invocation count (to correlate with errors)
5. Concurrent executions (to detect throttling)

### Step 5: Define Log Retention Policy
- Dev: 7 days
- Staging: 30 days
- Prod: 90 days (or as required by compliance)

State the retention setting for each log group in scope.

## OUTPUT CONTRACT

1. Write the observability design as a new ADR entry in `.github/shared/architecture_log.md`:
   `## ADR-[NNN]: Observability Design � [Task Name]`
   Include: log schema, alarm table, X-Ray strategy, dashboard widgets, retention policy.
2. Write this exact phrase to signal completion:
   `Observability design complete. Activating reliability_design.`
