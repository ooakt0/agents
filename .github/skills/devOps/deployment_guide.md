# Skill: Deployment Guide Generator

## ROLE & ACTIVATION
You are **@devOps** generating a human-executable deployment guide. Activate this skill when
`MANUAL_DEPLOY_REQUESTED` is received — the user has chosen to deploy manually rather than via the
automated pipeline.

This skill produces a concrete, runnable guide tailored to the current task. It is NOT a
generic template — every command must reference the actual stack names, function names, and
environment values from the shared state files.

## INPUTS
Before generating the guide, read ALL of the following:
- `.github/shared/project_state.md` — task ID, stack names, environment target, deployment strategy
- `.github/shared/project_context.md` — tech stack, CDK app entry point (`bin/app.ts`), environment names
- `.github/shared/architecture_log.md` — deployment strategy ADR (Canary or Blue/Green details)
- `.github/shared/standards.md` — required tags, IAM role naming conventions

## PROCESS

### Step 1: Extract Concrete Values
From the shared state files, extract and hold these values for use in every command:

```
STACK_NAME:      [from project_state.md]
ENV_TARGET:      [dev / staging / prod — from project_state.md]
AWS_REGION:      [from project_context.md]
CDK_APP:         [entry point — e.g., "npx ts-node bin/app.ts"]
DEPLOY_ROLE_ARN: [from project_context.md or architecture_log.md]
FUNCTION_NAME:   [Lambda function name — if applicable]
STRATEGY:        [Canary / Blue/Green — from architecture_log.md]
```

### Step 2: Generate `docs/deployment_guide.md`
Write the file with the following sections, filled with the actual values extracted in Step 1.

---

#### Section 1: Prerequisites
```markdown
## Prerequisites

### Required Tools
| Tool | Version | Install |
|---|---|---|
| AWS CLI | ≥ 2.13 | `winget install Amazon.AWSCLI` / `brew install awscli` |
| Node.js | 20.x LTS | https://nodejs.org |
| AWS CDK | ≥ 2.x | `npm install -g aws-cdk` |
| TypeScript | ≥ 5.x | `npm install -g typescript` |

### Required IAM Permissions
The identity deploying these stacks needs the following IAM permissions on the
`[ENV_TARGET]` account:

- `cloudformation:*` on `arn:aws:cloudformation:[AWS_REGION]:*:stack/[STACK_NAME]/*`
- `iam:PassRole` on the CDK execution role
- `lambda:UpdateFunctionCode`, `lambda:PublishVersion`, `lambda:UpdateAlias`
- `s3:PutObject` on the CDK asset bucket

Recommended: assume the deploy role directly:
```bash
aws sts assume-role \
  --role-arn [DEPLOY_ROLE_ARN] \
  --role-session-name manual-deploy-$(date +%s) \
  --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]'
```
Export the returned credentials as `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
`AWS_SESSION_TOKEN` before proceeding.
```

#### Section 2: Pre-Deployment Checklist
```markdown
## Pre-Deployment Checklist

Run these checks before issuing any deploy command:

- [ ] You are authenticated to the correct AWS account:
  ```bash
  aws sts get-caller-identity
  # Expected: account ID matches [ENV_TARGET] account
  ```
- [ ] All tests pass locally:
  ```bash
  npm ci && npm test -- --ci
  ```
- [ ] CDK synth completes without errors:
  ```bash
  npx cdk synth --app "[CDK_APP]" --context env=[ENV_TARGET] 2>&1
  ```
- [ ] Review the change set (diff against live):
  ```bash
  npx cdk diff --app "[CDK_APP]" --context env=[ENV_TARGET] [STACK_NAME]
  ```
  Read every `[+]` and `[-]` line. If a resource deletion is unexpected, stop.
```

#### Section 3: Step-by-Step Deployment
```markdown
## Step-by-Step Deployment

### Step 1: Install Dependencies
```bash
npm ci
```

### Step 2: Build TypeScript
```bash
npm run build
# Verify: no errors in dist/ output
```

### Step 3: Synthesize CloudFormation Templates
```bash
npx cdk synth \
  --app "[CDK_APP]" \
  --context env=[ENV_TARGET] \
  --output cdk.out
```

### Step 4: Deploy the Stack
```bash
npx cdk deploy [STACK_NAME] \
  --app "[CDK_APP]" \
  --context env=[ENV_TARGET] \
  --require-approval broadening \
  --region [AWS_REGION]
```

> `--require-approval broadening` will pause and ask for confirmation before
> any change that broadens security (e.g., new IAM policy, open security group rule).
> Review carefully before typing `y`.

[IF STRATEGY = Canary]
### Step 4b: Monitor Canary Traffic Shift
After deploy completes, CodeDeploy shifts traffic automatically (10% per 10 minutes).
Monitor the shift:
```bash
aws deploy list-deployments \
  --application-name [STACK_NAME]-App \
  --deployment-group-name [STACK_NAME]-CanaryGroup \
  --query 'deployments[0]'

# Watch deployment progress
aws deploy get-deployment \
  --deployment-id [deployment-id-from-above] \
  --query 'deploymentInfo.[status,deploymentOverview]'
```
[END IF]

[IF STRATEGY = Blue/Green]
### Step 4b: Approve Blue/Green Traffic Switch
After green environment passes health checks on port 8080, approve traffic promotion
in the AWS Console under: CodeDeploy → Deployments → [deployment-id] → Actions → Approve

Or via CLI:
```bash
aws deploy continue-deployment \
  --deployment-id [deployment-id] \
  --deployment-wait-type READY_WAIT
```
[END IF]
```

#### Section 4: Verification
```markdown
## Verification

Run these checks after deployment completes:

### 1. CloudWatch Alarm Health
```bash
aws cloudwatch describe-alarms \
  --alarm-name-prefix "[STACK_NAME]-" \
  --query 'MetricAlarms[*].[AlarmName,StateValue]' \
  --output table
# Expected: all alarms in OK state
```

### 2. DLQ Depth Check
```bash
DLQ_URL=$(aws sqs get-queue-url \
  --queue-name "[STACK_NAME]-dlq" \
  --query 'QueueUrl' --output text)

aws sqs get-queue-attributes \
  --queue-url "$DLQ_URL" \
  --attribute-names ApproximateNumberOfMessages \
  --query 'Attributes.ApproximateNumberOfMessages'
# Expected: "0"
```

### 3. Health Endpoint Smoke Test
```bash
for i in $(seq 1 10); do
  curl -s -o /dev/null -w "Check $i: %{http_code}\n" [API_ENDPOINT]/health
done
# Expected: all 200
```

### 4. Lambda Version Confirmation
```bash
aws lambda get-alias \
  --function-name [FUNCTION_NAME] \
  --name live \
  --query '[FunctionVersion,AliasArn]'
```
```

#### Section 5: Rollback Plan
```markdown
## Rollback Plan

If any verification check fails, roll back immediately. Do not wait.

### Option A: Lambda Alias Rollback (< 60 seconds)
```bash
# Revert alias to previous version
PREVIOUS_VERSION=[manually record this from Step 4 output]
aws lambda update-alias \
  --function-name [FUNCTION_NAME] \
  --name live \
  --function-version $PREVIOUS_VERSION \
  --routing-config AdditionalVersionWeights={} \
  --region [AWS_REGION]
```

### Option B: CloudFormation Stack Rollback
```bash
aws cloudformation rollback-stack --stack-name [STACK_NAME]
# Monitor:
aws cloudformation describe-stacks \
  --stack-name [STACK_NAME] \
  --query 'Stacks[0].StackStatus'
# Wait for: UPDATE_ROLLBACK_COMPLETE
```

### Option C: Git Revert + Redeploy
```bash
git revert HEAD --no-edit
git push origin [BRANCH_NAME]
# Repeat Steps 1–4 with the reverted commit
```
```

### Step 3: Finalize the Guide
Append a footer to `docs/deployment_guide.md`:

```markdown
---
Generated by: @devOps — deployment_guide skill
Task: [TASK_ID from project_state.md]
Generated on: [current date]
Stack: [STACK_NAME] | Environment: [ENV_TARGET] | Strategy: [STRATEGY]
```

## OUTPUT CONTRACT

1. Write the completed guide to `docs/deployment_guide.md` (create `docs/` if it does not exist)
2. Update `.github/shared/project_state.md` — append under the active task:
   ```
   Manual deployment guide generated: docs/deployment_guide.md
   Status: awaiting manual execution by user
   ```
3. Write this exact phrase to signal completion:
   `DEPLOYMENT_GUIDE_READY`
