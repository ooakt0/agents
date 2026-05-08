# Skill: Environment Promotion

## ROLE & ACTIVATION
You are **@devOps** managing environment promotion. Activate this skill SECOND in the deployment
chain � after pipeline_setup completes.

## INPUTS
Before starting, read:
- `.github/shared/architecture_log.md` � Reliability ADR (rollback strategy, RTO target)
- `.github/shared/project_state.md` � environment names and CDK stack names
- The GitHub Actions workflow written by pipeline_setup

## PROCESS

### Step 1: Add Staging Smoke Test Job
After `deploy-staging` completes, add a smoke test job to the pipeline:

```yaml
  smoke-test-staging:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ vars.STAGING_DEPLOY_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}
      - name: Run smoke tests
        run: |
          # Check API health endpoint
          STATUS=$(curl -s -o /dev/null -w "%{http_code}" ${{ vars.STAGING_API_ENDPOINT }}/health)
          if [ "$STATUS" != "200" ]; then
            echo "Smoke test FAILED: health endpoint returned $STATUS"
            exit 1
          fi
          echo "Smoke test PASSED: health endpoint returned 200"
```

### Step 2: Add Manual Approval Gate for Prod
In `.github/workflows/deploy.yml`, add the prod deployment with an environment that requires
manual approval (configure the `prod` GitHub environment to require a reviewer):

```yaml
  deploy-prod-canary:
    needs: smoke-test-staging
    runs-on: ubuntu-latest
    environment: prod           # This environment has required reviewers configured in GitHub
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ vars.PROD_DEPLOY_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}
      - run: npm ci
      - name: Deploy canary (10% traffic)
        run: npx cdk deploy --app "npx ts-node bin/app.ts" --context env=prod --context canaryWeight=10 --require-approval never
```

### Step 3: Define Canary Traffic Routing
In the CDK stack, implement weighted alias routing for Lambda (or weighted target groups for ALB):

```typescript
// Canary routing for Lambda via alias weights
const liveAlias = fn.addAlias('live');
const canaryAlias = fn.addAlias('canary');

// During canary: route 10% of traffic to new version, 90% to previous
new lambda.CfnAlias(this, 'WeightedAlias', {
  functionName: fn.functionName,
  name: 'live',
  functionVersion: fn.currentVersion.version,
  routingConfig: {
    additionalVersionWeights: [{
      functionVersion: previousVersionArn,
      functionWeight: 0.9,
    }],
  },
});
```

Canary stages:
- **10%** � initial canary, observe for 10 minutes
- **50%** � if error rate < 0.1% and P99 < 1000ms after 10 min, promote to 50%
- **100%** � if still healthy after 10 min at 50%, promote to full

### Step 4: Rollback Procedure
For every environment, document the rollback command:

**Dev / Staging rollback:**
```bash
# Re-deploy the previous commit
git revert HEAD
git push origin develop
```

**Production rollback (immediate � before CDK re-deploy):**
```bash
# Roll alias back to previous Lambda version
aws lambda update-alias \
  --function-name [function-name] \
  --name live \
  --function-version [previous-version-number] \
  --region us-east-1
```

**Production rollback via CDK:**
```bash
npx cdk deploy --app "npx ts-node bin/app.ts" --context env=prod --context rollback=true
```

Add a `rollback` workflow trigger in `.github/workflows/rollback.yml` for one-click rollback:
```yaml
name: Production Rollback
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Lambda version to roll back to'
        required: true
```

### Step 5: Update CloudWatch Alarms for Canary Monitoring
During canary deployment, verify these alarms are active (from Observability ADR):
- Error rate alarm: threshold 0.1%, evaluation period 5 minutes
- P99 latency alarm: threshold 1000ms, evaluation period 5 minutes
- DLQ depth alarm: threshold 1, evaluation period 1 minute

If any alarm fires during canary window ? automatic rollback (configure via CodeDeploy or
a CloudWatch alarm action that invokes the rollback SSM document).

## OUTPUT CONTRACT

1. Update `.github/workflows/deploy.yml` with smoke test, manual approval, and canary stages
2. Write `.github/workflows/rollback.yml` for one-click production rollback
3. Update CDK stack with Lambda alias weighted routing
4. Write this exact phrase to signal completion:
   `Environment promotion complete. Activating deployment_verification.`
