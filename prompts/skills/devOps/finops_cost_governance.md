# Skill: FinOps Cost Governance

## ROLE & ACTIVATION
You are **@devOps** enforcing cost governance before code goes live. Activate this skill THIRD
in the deployment chain — after `deployment_strategy_engine`, before `observability_provisioning`.

## INPUTS
Before starting, read:
- `.github/shared/architecture_log.md` — Cost Estimation ADR (budget ceiling, Dev vs Prod sizing decisions)
- `.github/shared/project_state.md` — environment being deployed (dev/staging/prod)
- `.github/shared/standards.md` — resource tagging requirements, idle-cost anti-patterns

## PROCESS

### Step 1: Estimate Deployment Cost Delta
Use AWS Cost Explorer or the Pricing API to estimate the monthly cost of new or changed resources:

```bash
# Get cost forecast for the stack (requires Cost Explorer enabled)
aws ce get-cost-forecast \
  --time-period Start=$(date +%Y-%m-01),End=$(date -d 'next month' +%Y-%m-01) \
  --metric UNBLENDED_COST \
  --granularity MONTHLY \
  --filter '{
    "Tags": {
      "Key": "aws:cloudformation:stack-name",
      "Values": ["[stack-name]"]
    }
  }' \
  --query 'Total.Amount'
```

If Cost Explorer is not yet enabled, estimate from the Cost Estimation ADR and compare against
the CDK resource list from `cdk synth`.

### Step 2: Flag Idle-Cost Anti-Patterns
Check every resource in the CDK stack against this list of known idle-cost offenders:

| Anti-Pattern | Check | Action |
|---|---|---|
| NAT Gateway with no traffic | Verify VPC design needs NAT; Lambda in private subnet? | Flag if dev env |
| Provisioned Lambda Concurrency on dev | `ProvisionedConcurrencyConfig` in template | Remove for dev; keep only in prod |
| RDS instance left running in dev | Non-Aurora Serverless instance in non-prod | Flag for scheduled stop |
| Oversized ECS task definition | CPU/Memory above 50% average utilization | Downsize to match ADR sizing |
| S3 Intelligent Tiering disabled | Objects > 128KB without lifecycle rule | Add lifecycle rule |
| CloudWatch Log retention = never | Log group with no `RetentionInDays` | Set to 30 days (dev) / 90 days (prod) |

For each anti-pattern found, write a line to the drift report:
```
[COST] Anti-pattern detected: [description] in [resource-id] — estimated waste: $X/month
```

### Step 3: Verify Mandatory Resource Tags
All resources must be tagged for cost allocation. Missing tags = unattributed costs.

Required tags (from `standards.md`):
- `Project` — project name
- `Environment` — dev / staging / prod
- `Owner` — team or squad name
- `CostCenter` — budget code

```bash
# Find untagged resources in the stack
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=aws:cloudformation:stack-name,Values=[stack-name] \
  --query 'ResourceTagMappingList[*].{ARN:ResourceARN,Tags:Tags}' \
  --output json | jq '.[] | select(.Tags | map(.Key) | contains(["Project","Environment","Owner","CostCenter"]) | not)'
```

Any resource missing a required tag must be tagged before promotion to the next environment.

### Step 4: Compare Against Budget Ceiling
Read the budget ceiling from the Cost Estimation ADR. If the forecasted cost exceeds the ceiling:

| Environment | Threshold Action |
|---|---|
| dev | Log warning, continue deployment |
| staging | Log warning + notify @techLead via `project_state.md` note |
| prod | **Block deployment** — write `Returning to @techLead` with cost overrun details |

For prod budget overruns, do NOT proceed. @techLead must approve a budget amendment or descope.

### Step 5: Confirm Provisioned Concurrency Is Intentional (Lambda Only)
Provisioned Concurrency is the single largest Lambda cost driver. Verify it is justified:

```bash
aws lambda list-provisioned-concurrency-configs \
  --function-name [function-name] \
  --query 'ProvisionedConcurrencyConfigs[*].[FunctionArn,RequestedProvisionedConcurrentExecutions,Status]' \
  --output table
```

If Provisioned Concurrency is configured and the Cost Estimation ADR does NOT mention it:
```
[COST] Unbudgeted Provisioned Concurrency: [function-name] — $X/month not in ADR. Returning to @techLead.
```

## OUTPUT CONTRACT

**If a prod budget ceiling is exceeded or unbudgeted Provisioned Concurrency is found:**
1. Document the finding in `.github/shared/project_state.md` under `Cost Governance Flags`
2. Write this exact phrase:
   `Returning to @techLead — cost governance blocked deployment: [reason]`

**If anti-patterns or tag violations are found but budget is within ceiling:**
1. List all findings in `.github/shared/project_state.md` under `Cost Governance Flags`
2. Write this exact phrase:
   `Cost governance review complete — [N] findings logged. Activating observability_provisioning.`

**If no issues found:**
1. Write this exact phrase:
   `Cost governance review complete — no issues. Activating observability_provisioning.`
