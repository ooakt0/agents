# Skill: Deployment Strategy Engine

## ROLE & ACTIVATION
You are **@devOps** selecting and orchestrating the deployment strategy. Activate this skill
SECOND in the deployment chain — after `pipeline_setup` completes, before `finops_cost_governance`.

## INPUTS
Before starting, read:
- `.github/shared/architecture_log.md` — ADRs for service type, Lambda aliases, traffic pattern
- `.github/shared/project_state.md` — environment, stack names, criticality rating
- `.github/shared/standards.md` — HA and RTO/RPO requirements

## PROCESS

### Step 1: Select Deployment Strategy
Evaluate the service against the following decision matrix:

| Condition | Strategy |
|---|---|
| Stateless Lambda / API Gateway | **Canary** (traffic shifting via alias weights) |
| ECS/EKS service, stateful workload | **Blue/Green** (full parallel environment) |
| CDK-only infra change (no compute) | **Rolling update** (CDK deploy with change set review) |
| Database migration required | **Blue/Green** with read-replica promotion |

Record the chosen strategy in `.github/shared/project_state.md` under `Deployment Strategy`.

### Step 2: Canary Strategy (Lambda / API Gateway)
Configure Lambda alias weighted routing to shift traffic incrementally:

```typescript
// CDK: Canary alias with initial 10% weight on new version
const liveAlias = new lambda.Alias(this, 'LiveAlias', {
  aliasName: 'live',
  version: fn.currentVersion,
  additionalVersions: [{
    version: previousVersion,
    weight: 0.9, // 90% stays on old version initially
  }],
});

// CodeDeploy linear canary — shifts 10% every 10 minutes
const deployment = new codedeploy.LambdaDeploymentGroup(this, 'CanaryGroup', {
  alias: liveAlias,
  deploymentConfig: codedeploy.LambdaDeploymentConfig.LINEAR_10PERCENT_EVERY_10MINUTES,
  alarms: [errorRateAlarm, p99LatencyAlarm],
});
```

Traffic shift schedule:
- T+0 min: 10% new / 90% old
- T+10 min: 20% new / 80% old
- T+20 min: 30% new / 70% old
- T+60 min: 100% new (if all alarms remain OK)

If any alarm fires during shift: CodeDeploy auto-rolls back to 0% new.

### Step 3: Blue/Green Strategy (ECS / Stateful)
Provision a parallel "green" environment alongside the live "blue" environment:

```typescript
// CDK: ECS Blue/Green with CodeDeploy
const deploymentGroup = new codedeploy.EcsDeploymentGroup(this, 'BlueGreenGroup', {
  service: ecsService,
  blueGreenDeploymentConfig: {
    blueTargetGroup,
    greenTargetGroup,
    listener: httpsListener,
    testListener: testListener, // port 8080 for pre-promotion smoke tests
    terminationWaitTime: Duration.minutes(10),
  },
  deploymentConfig: codedeploy.EcsDeploymentConfig.CANARY_10PERCENT_5MINUTES,
  alarms: [errorRateAlarm],
});
```

Blue/Green promotion gates:
1. Green passes all health checks on port 8080
2. Zero 5XX errors in CloudWatch for 5 minutes
3. Manual approval in GitHub environment settings (prod only)

### Step 4: Document Warm-State Preservation
Record how the old environment stays "warm" until promotion is confirmed:

```
Old (Blue) environment:
- Remains fully provisioned and receiving 90% traffic during canary window
- Will not be terminated until deployment_verification gives full clearance
- Rollback = flip alias/TG back to blue in < 60 seconds (within RTO target)
```

Write this summary to `.github/shared/project_state.md` under `Active Deployment Window`.

### Step 5: Validate Strategy Alignment with ADRs
- Confirm chosen strategy meets RTO defined in the Reliability ADR
- Confirm rollback time estimate ≤ RTO
- If strategy conflicts with an ADR, write `Returning to @techLead` with the conflict details

## OUTPUT CONTRACT

1. Update `.github/shared/project_state.md` with `Deployment Strategy` and `Active Deployment Window`
2. Write CDK/CodeDeploy constructs for the chosen strategy to the infra stack
3. Write this exact phrase to signal completion:
   `Deployment strategy configured. Activating finops_cost_governance.`
