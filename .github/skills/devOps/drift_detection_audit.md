# Skill: Drift Detection Audit

## ROLE & ACTIVATION
You are **@devOps** auditing for infrastructure drift. Activate this skill EIGHTH and LAST in
the deployment chain — after `automated_rollback_logic` completes. This is the final
consistency gate before returning control to @techLead.

## INPUTS
Before starting, read:
- `.github/shared/architecture_log.md` — ADR for every infrastructure decision
- `.github/shared/project_state.md` — CDK stack names, environments deployed
- `.github/shared/standards.md` — "Infrastructure as Code" mandate: all changes via CDK/Terraform only

## PROCESS

### Step 1: Run CDK Diff Against Live Environment
A non-empty `cdk diff` against a freshly deployed stack means someone made a manual Console
change. This is a standards violation.

```bash
# Diff CDK code against live CloudFormation stack
npx cdk diff \
  --app "npx ts-node bin/app.ts" \
  --context env=prod \
  2>&1 | tee /tmp/cdk-drift-report.txt

# Check for unexpected diffs (post-deploy diff should be empty)
if grep -q "^[+-]" /tmp/cdk-drift-report.txt; then
  echo "DRIFT DETECTED — manual changes found in live environment"
  cat /tmp/cdk-drift-report.txt
fi
```

Expected: zero lines beginning with `+` or `-` after a clean deployment.

### Step 2: Scan IAM Policies for Console-Applied Changes
Manual IAM changes are high-risk drift. Detect them by comparing CDK-synthesized policy
documents against what is live in IAM:

```bash
# Export live IAM role policies
aws iam list-role-policies --role-name [role-name] --output json > /tmp/live-policies.json

# Compare against CDK-synthesized output (cdk synth writes to cdk.out/)
diff \
  <(jq -S . cdk.out/[stack-name].template.json | grep -A100 '"Policies"') \
  <(jq -S . /tmp/live-policies.json)
```

Any difference signals an out-of-band change. Document it as a violation.

### Step 3: Security Group Drift Check
Manual security group rule additions are a common Console-click failure mode:

```bash
# List all inbound rules for every SG in the stack
aws ec2 describe-security-groups \
  --filters "Name=tag:aws:cloudformation:stack-name,Values=[stack-name]" \
  --query 'SecurityGroups[*].{ID:GroupId,Name:GroupName,Ingress:IpPermissions}' \
  --output json > /tmp/live-sgs.json

# Compare against CDK-synthesized security group definitions
diff \
  <(jq -S . cdk.out/[stack-name].template.json | grep -A200 '"SecurityGroup"') \
  <(jq -S . /tmp/live-sgs.json)
```

Any extra ingress rule (especially 0.0.0.0/0) must be flagged and removed.

### Step 4: Tag Compliance Audit
All resources must carry the mandatory tags defined in `standards.md`. Detect untagged or
mis-tagged resources:

```bash
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=Project,Values=[project-name] \
  --query 'ResourceTagMappingList[?Tags[?Key==`Environment`] == `[]`].ResourceARN' \
  --output text
```

Any resource returned is missing the `Environment` tag — flag for remediation.

### Step 5: Drift Report and Remediation
For every drift item found:

| Severity | Condition | Action |
|---|---|---|
| **CRITICAL** | Security group 0.0.0.0/0 added manually | Write `SECURITY FAIL: open ingress rule on [sg-id] — manual Console change detected` |
| **HIGH** | IAM policy expanded out-of-band | Flag to @techLead; open remediation task in `project_state.md` |
| **MEDIUM** | CDK resource property changed manually | Trigger `cdk deploy` to restore IaC state |
| **LOW** | Missing tag on non-critical resource | Tag the resource via CLI; document in `architecture_log.md` |

For CRITICAL severity, write the `SECURITY FAIL:` phrase exactly — it triggers the hook
that blocks the workflow.

### Step 6: Remediate Medium/Low Drift Automatically
For medium severity (property drift), restore IaC state without manual approval:

```bash
# Re-apply CDK to overwrite console changes
npx cdk deploy \
  --app "npx ts-node bin/app.ts" \
  --context env=prod \
  --require-approval never \
  --exclusively [stack-name]
```

Confirm post-remediation diff is clean:
```bash
npx cdk diff --app "npx ts-node bin/app.ts" --context env=prod
# Must show: "There were no differences"
```

## OUTPUT CONTRACT

**If CRITICAL drift is detected:**
1. Write this exact phrase (blocks the workflow):
   `SECURITY FAIL: [describe the specific drift — e.g., "open 0.0.0.0/0 ingress on sg-0abc123 added via Console"]`

**If drift was found and remediated (medium/low):**
1. Document all drift items in `.github/shared/architecture_log.md` under `Drift Events`
2. Write this exact phrase:
   `Drift remediated: [summary]. Deployment verified. Returning to @techLead.`

**If no drift detected:**
1. Write this exact phrase:
   `Drift detection audit passed — environment matches IaC. Returning to @techLead.`
