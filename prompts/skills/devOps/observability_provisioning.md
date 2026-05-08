# Skill: Observability Provisioning

## ROLE & ACTIVATION
You are **@devOps** implementing the observability design as live infrastructure. Activate this
skill FOURTH in the deployment chain — after `finops_cost_governance`, before
`environment_promotion`. Rule: if it's not monitored, it's not deployed.

## INPUTS
Before starting, read:
- `.github/shared/architecture_log.md` — Observability ADR (alarm names, metric names, log groups,
  trace sampling rate, dashboard widgets designed by @architect)
- `.github/shared/project_state.md` — stack names, Lambda function names, API Gateway IDs
- `.github/shared/standards.md` — log retention periods, structured log format requirements

## PROCESS

### Step 1: Provision CloudWatch Alarms
Create every alarm defined in the Observability ADR. At minimum, the following alarms are
mandatory for any deployed compute resource:

```typescript
// CDK: Mandatory alarm set for a Lambda function
const errorRateAlarm = new cloudwatch.Alarm(this, 'ErrorRateAlarm', {
  alarmName: `${stackName}-ErrorRateAlarm`,
  metric: lambdaFn.metricErrors({ period: Duration.minutes(5) }),
  threshold: 5,
  evaluationPeriods: 1,
  comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
  treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
  alarmDescription: 'Lambda error count exceeded threshold — potential regression',
});

const p99LatencyAlarm = new cloudwatch.Alarm(this, 'P99LatencyAlarm', {
  alarmName: `${stackName}-P99LatencyAlarm`,
  metric: lambdaFn.metricDuration({
    period: Duration.minutes(5),
    statistic: 'p99',
  }),
  threshold: 3000,          // 3 seconds — adjust per Reliability ADR
  evaluationPeriods: 2,
  comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
  treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
  alarmDescription: 'P99 latency exceeded SLO threshold',
});

const dlqDepthAlarm = new cloudwatch.Alarm(this, 'DLQDepthAlarm', {
  alarmName: `${stackName}-DLQDepthAlarm`,
  metric: dlq.metricApproximateNumberOfMessagesVisible({ period: Duration.minutes(1) }),
  threshold: 0,
  evaluationPeriods: 1,
  comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
  treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
  alarmDescription: 'Messages appearing in DLQ — processing failure detected',
});
```

Wire all alarms to an SNS topic for alerting:
```typescript
const alertTopic = new sns.Topic(this, 'AlertTopic', { topicName: `${stackName}-Alerts` });
errorRateAlarm.addAlarmAction(new cw_actions.SnsAction(alertTopic));
p99LatencyAlarm.addAlarmAction(new cw_actions.SnsAction(alertTopic));
dlqDepthAlarm.addAlarmAction(new cw_actions.SnsAction(alertTopic));
```

### Step 2: Provision CloudWatch Dashboard
Translate the Observability ADR dashboard design into CDK:

```typescript
const dashboard = new cloudwatch.Dashboard(this, 'ServiceDashboard', {
  dashboardName: `${stackName}-Operations`,
  widgets: [
    [
      new cloudwatch.GraphWidget({
        title: 'Lambda Error Rate (5m)',
        left: [lambdaFn.metricErrors({ period: Duration.minutes(5) })],
        width: 12,
      }),
      new cloudwatch.GraphWidget({
        title: 'Lambda P99 Duration (5m)',
        left: [lambdaFn.metricDuration({ statistic: 'p99', period: Duration.minutes(5) })],
        width: 12,
      }),
    ],
    [
      new cloudwatch.GraphWidget({
        title: 'DLQ Message Depth',
        left: [dlq.metricApproximateNumberOfMessagesVisible({ period: Duration.minutes(1) })],
        width: 12,
      }),
      new cloudwatch.AlarmStatusWidget({
        title: 'Alarm Status',
        alarms: [errorRateAlarm, p99LatencyAlarm, dlqDepthAlarm],
        width: 12,
      }),
    ],
  ],
});
```

### Step 3: Configure X-Ray Tracing
Enable active X-Ray tracing on all Lambda functions and API Gateway stages:

```typescript
// CDK: X-Ray active tracing on Lambda
const lambdaFn = new lambda.Function(this, 'ServiceFn', {
  // ... other config
  tracing: lambda.Tracing.ACTIVE,
});

// CDK: X-Ray tracing on API Gateway stage
const api = new apigw.RestApi(this, 'ServiceApi', {
  deployOptions: {
    tracingEnabled: true,
    metricsEnabled: true,
    loggingLevel: apigw.MethodLoggingLevel.INFO,
    dataTraceEnabled: false,  // never log full request/response bodies in prod (PII risk)
  },
});
```

Sampling rate: use the Observability ADR value. Default: 5% in prod, 100% in dev.

### Step 4: Set Log Retention Policies
Every log group must have an explicit retention period. No log group may have retention set to
`Never expire` (cost and compliance violation):

```typescript
// CDK: Enforce log retention on Lambda log group
const logGroup = new logs.LogGroup(this, 'ServiceLogGroup', {
  logGroupName: `/aws/lambda/${lambdaFn.functionName}`,
  retention: isProd ? logs.RetentionDays.THREE_MONTHS : logs.RetentionDays.ONE_MONTH,
  removalPolicy: cdk.RemovalPolicy.DESTROY,
});
```

Scan existing log groups for missing retention:
```bash
aws logs describe-log-groups \
  --query 'logGroups[?retentionInDays==`null`].logGroupName' \
  --output text
```

Set retention on any orphaned log groups:
```bash
aws logs put-retention-policy \
  --log-group-name [group-name] \
  --retention-in-days 30
```

### Step 5: Validate Observability Is Live
After CDK deploy, verify each component is active:

```bash
# Confirm alarms exist and are not in INSUFFICIENT_DATA
aws cloudwatch describe-alarms \
  --alarm-name-prefix "[stack-name]-" \
  --query 'MetricAlarms[*].[AlarmName,StateValue]' \
  --output table

# Confirm dashboard was created
aws cloudwatch list-dashboards \
  --dashboard-name-prefix "[stack-name]-" \
  --query 'DashboardEntries[*].DashboardName'

# Confirm X-Ray groups exist
aws xray get-groups --query 'Groups[*].GroupName'
```

Any alarm in `INSUFFICIENT_DATA` state 5 minutes after deployment is a signal that the
metric is not being emitted — investigate before proceeding to `environment_promotion`.

## OUTPUT CONTRACT

1. Write CDK alarm, dashboard, X-Ray, and log retention constructs to the infra stack
2. Confirm all alarms are in `OK` or `INSUFFICIENT_DATA` (acceptable pre-traffic) state
3. Document the CloudWatch dashboard URL in `.github/shared/project_state.md` under `Observability`
4. Write this exact phrase to signal completion:
   `Observability provisioned. Activating environment_promotion.`
