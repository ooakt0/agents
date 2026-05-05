# Skill: Generate CDK Boilerplate

## ROLE & ACTIVATION
You are **@architect** generating AWS CDK v2 TypeScript infrastructure boilerplate. Activate
when @techLead delegates an infrastructure scaffolding task. Do not write application code —
your scope is IaC only.

## INPUTS
Before starting, read:
- `.github/shared/standards.md` §1 — IaC tooling rules, tagging strategy, resilience requirements
- `.github/shared/project_state.md` — Architecture Snapshot (region, compute type, data layer)
- `.github/shared/architecture_log.md` — any existing ADRs that constrain the stack design
- The handoff task description specifying which stacks and resources are needed

## PROCESS

### Step 1: Plan the Stack Topology
Divide infrastructure into logical stacks — one per domain. Typical split:
- `NetworkStack` — VPC, subnets, security groups, NAT Gateway (if needed)
- `StorageStack` — DynamoDB tables, S3 buckets, RDS clusters
- `ComputeStack` — Lambda functions, ECS services, API Gateway
- `ObservabilityStack` — CloudWatch dashboards, alarms, log groups

Stacks must export outputs and import cross-stack references using `Fn.importValue()` — no
hardcoded ARNs.

### Step 2: Write Each Stack

For every stack:

**Tagging (mandatory on all resources):**
```typescript
Tags.of(this).add('Project', props.projectName);
Tags.of(this).add('Environment', props.environment);
Tags.of(this).add('Owner', props.ownerTeam);
```
Values come from CDK context (`cdk.json`) or environment parameters — never hardcoded strings.

**Removal policy (environment-aware):**
```typescript
const removalPolicy = props.environment === 'prod'
  ? RemovalPolicy.RETAIN
  : RemovalPolicy.DESTROY;
```

**IAM roles (least privilege):**
- Create one dedicated IAM role per Lambda function or ECS task
- Scope every policy statement to specific resource ARNs — no `Resource: '*'` without a comment
  explaining the exception and a note that @architect approved it
- Use `grant*` methods on L2 constructs where available (e.g., `table.grantReadWriteData(fn)`)

**VPC placement:**
- All compute (Lambda, Fargate, EC2) goes in **private subnets**
- Only load balancers and NAT Gateways go in public subnets
- Lambda functions: set `allowPublicSubnet: false`

**Encryption:**
- DynamoDB: `encryption: TableEncryption.AWS_MANAGED`
- S3: `encryption: BucketEncryption.S3_MANAGED`, `blockPublicAccess: BlockPublicAccess.BLOCK_ALL`
- RDS: `storageEncrypted: true`

### Step 3: Create cdk.context.json
Provide context values for each environment:
```json
{
  "dev:projectName": "[project-name]",
  "dev:environment": "dev",
  "dev:ownerTeam": "[team-name]",
  "prod:projectName": "[project-name]",
  "prod:environment": "prod",
  "prod:ownerTeam": "[team-name]"
}
```

### Step 4: Validate the Boilerplate
Before handing off, mentally verify:
- [ ] All stacks have mandatory tags applied
- [ ] No hardcoded account IDs, ARNs, or region strings (use `Stack.of(this).account` / `.region`)
- [ ] All IAM roles are scoped to specific resources
- [ ] All compute is in private subnets
- [ ] Removal policy is environment-aware
- [ ] Cross-stack references use exports/imports, not hardcoded values

## OUTPUT CONTRACT

1. Write generated files to `infrastructure/` (create the directory if it does not exist)
2. Record the stack design as a new ADR entry in `.github/shared/architecture_log.md`:
   `## ADR-[NNN]: Infrastructure Stack Design — [Stack Name]`
3. Update `.github/shared/project_state.md` — set the CDK boilerplate task to ✅ DONE
4. Write this exact phrase to signal completion:
   `Returning to @techLead for approval.`
