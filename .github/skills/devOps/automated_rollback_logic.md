# Skill: Automated Rollback Logic

## ROLE & ACTIVATION
You are **@devOps** defining automated rollback triggers and procedures. Activate this skill
SEVENTH in the deployment chain — after `deployment_verification` completes (or is called
immediately if verification fails). This is the "panic button" that actually works.

## INPUTS
Before starting, read:
- `.github/shared/architecture_log.md` — Observability ADR (alarm names, thresholds), Reliability ADR (RTO)
- `.github/shared/project_state.md` — `Active Deployment Window`, chosen strategy, Lambda alias/ECS service names
- CloudWatch alarm state from `deployment_verification`

## PROCESS

### Step 1: Define Rollback Trigger Thresholds
Read the Reliability ADR for error budgets. If not specified, use these defaults:

| Metric | Trigger Threshold | Measurement Window |
|---|---|---|
| 5XX error rate | > 1% of requests | 5-minute rolling |
| P99 latency | > 2× pre-deploy baseline | 5-minute rolling |
| DLQ depth | > 0 messages | Immediate |
| Lambda error rate | > 0.5% invocations | 5-minute rolling |
| Health check failures | < 95% success | 1-minute rolling |

### Step 2: Wire CloudWatch Alarms to Auto-Rollback
For Lambda/Canary deployments, CodeDeploy alarms already trigger rollback automatically
(configured in `deployment_strategy_engine`). Verify the alarm linkage:

```bash
aws deploy get-deployment-group \
  --application-name [app-name] \
  --deployment-group-name [group-name] \
  --query 'deploymentGroupInfo.alarmConfiguration'
```

Expected: `enabled: true` with at least `ErrorRateAlarm` and `P99LatencyAlarm` listed.

For ECS Blue/Green deployments, add a CloudWatch alarm–driven rollback action:

```typescript
// CDK: Rollback alarm — triggers CodeDeploy auto-rollback
const rollbackAlarm = new cloudwatch.Alarm(this, 'RollbackTriggerAlarm', {
  metric: api.metricServerError({ period: Duration.minutes(5) }),
  threshold: 0.01,         // 1% error rate
  evaluationPeriods: 1,
  comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
  treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
  alarmName: `${stackName}-RollbackTrigger`,
});

// Attach to deployment group (see deployment_strategy_engine for deploymentGroup ref)
deploymentGroup.addAlarm(rollbackAlarm);
```

### Step 3: Define the "Last Known Good" Rollback Procedure
Document the exact rollback steps for each strategy:

**Canary / Lambda Alias Rollback (< 60 seconds):**
```bash
# Flip alias fully back to previous version — all traffic
aws lambda update-alias \
  --function-name [function-name] \
  --name live \
  --function-version $PREVIOUS_VERSION \
  --routing-config AdditionalVersionWeights={} \
  --region $AWS_REGION
```

**Blue/Green ECS Rollback (< 3 minutes):**
```bash
# Re-route load balancer listener back to blue target group
aws elbv2 modify-listener \
  --listener-arn $HTTPS_LISTENER_ARN \
  --default-actions Type=forward,TargetGroupArn=$BLUE_TG_ARN
```

**CDK Stack Rollback (infrastructure drift):**
```bash
# Retrieve previous CloudFormation template and redeploy
aws cloudformation continue-update-rollback \
  --stack-name [stack-name]
# If above fails (UPDATE_ROLLBACK_FAILED), use:
aws cloudformation rollback-stack --stack-name [stack-name]
```

### Step 4: Git Revert Trigger (Code-Level Rollback)
If automated infrastructure rollback succeeds but the root cause is a code defect,
trigger a git revert to remove the offending commit from the release branch:

```bash
# Identify the bad commit SHA from the failed deployment annotation
BAD_COMMIT=$(git log --oneline -1 origin/main | awk '{print $1}')

git revert $BAD_COMMIT --no-edit
git push origin main
```

This re-triggers the pipeline automatically, deploying the reverted code through the
standard canary/blue-green path.

### Step 5: Post-Rollback Checklist
After any rollback (automated or manual):

- [ ] CloudWatch alarms returned to `OK` state
- [ ] DLQ depth confirmed at 0
- [ ] Health checks passing at ≥ 95%
- [ ] Update `.github/shared/project_state.md` — set task to 🏗️ ACTIVE with note `Rolled back: [reason]`
- [ ] Write incident summary to `.github/shared/architecture_log.md` under `Rollback Events`

## OUTPUT CONTRACT

**If rollback was NOT triggered (no failures):**
1. Write this exact phrase:
   `Rollback logic verified — no trigger conditions met. Activating drift_detection_audit.`

**If rollback WAS triggered:**
1. Document rollback event in `.github/shared/architecture_log.md`
2. Reset task status to 🏗️ ACTIVE in `.github/shared/project_state.md`
3. Write this exact phrase:
   `Rollback executed: [reason]. Returning to @techLead.`
