# Skill: Deployment Verification

## ROLE & ACTIVATION
You are **@devOps** verifying the deployment. Activate this skill THIRD and LAST in the
deployment chain � after environment_promotion completes. This is the final gate before
returning control to @techLead.

## INPUTS
Before starting, read:
- `.github/shared/architecture_log.md` � Observability ADR (alarm names, DLQ names)
- `.github/shared/project_state.md` � CDK stack names and environment
- The canary deployment state from environment_promotion

## PROCESS

### Step 1: CloudWatch Alarm State Check
For every alarm defined in the Observability ADR, verify state is `OK` (not `ALARM` or
`INSUFFICIENT_DATA`):

```bash
aws cloudwatch describe-alarms \
  --alarm-names "[stack-name]-ErrorRateAlarm" "[stack-name]-P99LatencyAlarm" "[stack-name]-DLQDepthAlarm" \
  --state-value OK \
  --region us-east-1 \
  --query 'MetricAlarms[*].[AlarmName,StateValue]' \
  --output table
```

Expected output: all alarms in `OK` state.

For each alarm NOT in `OK` state:
```
[ALARM] FAIL: [alarm-name] is in [state] state � deployment verification blocked
```

### Step 2: DLQ Depth Check
Verify all Dead-Letter Queues have zero messages:

```bash
# Get DLQ URL
DLQ_URL=$(aws sqs get-queue-url --queue-name "[queue-name]-dlq" --query 'QueueUrl' --output text)

# Check approximate message count
DEPTH=$(aws sqs get-queue-attributes \
  --queue-url "$DLQ_URL" \
  --attribute-names ApproximateNumberOfMessages \
  --query 'Attributes.ApproximateNumberOfMessages' \
  --output text)

echo "DLQ depth: $DEPTH"
```

Expected: `DEPTH = 0`

If DLQ depth > 0:
```
[DLQ] FAIL: [queue-name]-dlq has [N] messages � investigate before proceeding
```

### Step 3: Canary Health Check
For a canary deployment (10% traffic stage), run targeted health checks:

```bash
# Call the health endpoint 20 times and count 200 responses
PASS=0
for i in $(seq 1 20); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_ENDPOINT/health")
  if [ "$STATUS" = "200" ]; then PASS=$((PASS+1)); fi
done

echo "$PASS/20 health checks passed"
if [ $PASS -lt 19 ]; then
  echo "FAIL: canary health check � less than 95% success rate"
  exit 1
fi
```

### Step 4: Lambda Version Verification
Verify the deployed Lambda function version matches the expected artifact:

```bash
DEPLOYED_VERSION=$(aws lambda get-alias \
  --function-name [function-name] \
  --name live \
  --query 'FunctionVersion' \
  --output text)

echo "Deployed version: $DEPLOYED_VERSION"
echo "Expected version: $EXPECTED_VERSION"

if [ "$DEPLOYED_VERSION" != "$EXPECTED_VERSION" ]; then
  echo "FAIL: version mismatch � rollback may be in progress"
  exit 1
fi
```

### Step 5: Structured Log Verification
Verify structured logs are flowing correctly post-deployment by querying CloudWatch Logs Insights:

```bash
aws logs start-query \
  --log-group-name "/aws/lambda/[function-name]" \
  --start-time $(date -d '5 minutes ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, level, message | filter level = "ERROR" | stats count() as errorCount'
```

Expected: `errorCount = 0` or within acceptable baseline for the environment.

### Step 6: Promote Canary to 100% (if all checks pass)
If all verification steps pass and canary has been running for at least 10 minutes:

```bash
# Remove weighted routing � all traffic to new version
aws lambda update-alias \
  --function-name [function-name] \
  --name live \
  --function-version $DEPLOYED_VERSION \
  --routing-config AdditionalVersionWeights={} \
  --region us-east-1
```

## OUTPUT CONTRACT

**If any verification step FAILS:**
1. Immediately trigger rollback (use the rollback procedure from environment_promotion)
2. Write the exact phrase:
   `Deployment FAILED: [reason � e.g., "DLQ depth > 0 on prod-orders-dlq"]. Rollback initiated. Returning to @techLead.`

**If all verification steps PASS:**
1. Update `.github/shared/project_state.md` � set task status to ? DONE
2. Write this exact phrase to signal successful completion:
   `Deployment verified. Returning to @techLead.`
