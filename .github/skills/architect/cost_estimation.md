# Skill: Cost Estimation

## ROLE & ACTIVATION
You are **@architect** performing a cost estimation analysis. Activate this skill when @techLead
delegates with `DELEGATE [architect]` and the objective involves resource sizing, pricing review,
or budget planning for AWS services.

## INPUTS
Before starting, read:
- `.github/shared/project_state.md` — Architecture Snapshot section (services, region, compute type)
- `.github/shared/standards.md` §1 — AWS & Infrastructure rules
- The specific AWS services listed in the handoff from @techLead

## PROCESS

### Step 1: Inventory All AWS Services
List every AWS service mentioned or implied by the architecture. For each service, state:
- The specific configuration (e.g., Lambda: 512 MB, 3s timeout, ~10k invocations/month)
- The deployment environment (Dev / Staging / Prod)

### Step 2: Estimate Monthly Cost Per Service
Use public AWS pricing models for each service. Provide:
- A realistic monthly estimate at the stated load
- The pricing model used (e.g., "DynamoDB: On-Demand, $1.25/million write request units")

Produce a cost table:

| Service | Configuration | Est. Monthly Cost (Prod) | Est. Monthly Cost (Dev) |
|---------|--------------|--------------------------|-------------------------|
| ...     | ...          | $X.XX                    | $X.XX                   |

### Step 3: Flag Cost Risks
Identify any configuration that is a known cost anti-pattern:
- Idle NAT Gateways (charged per hour even when unused)
- Over-provisioned RDS instances (right-size or consider Aurora Serverless)
- CloudWatch log retention set to "Never Expire"
- S3 without lifecycle policies (storage accumulates indefinitely)
- Lambda functions with over-allocated memory that don't need it

### Step 4: Recommend Tiered Sizing
Provide explicit Dev vs Prod sizing recommendations:
- Dev: prefer pay-per-request, minimal reserved capacity, single-AZ
- Prod: right-sized reserved capacity, Multi-AZ, auto-scaling enabled

### Step 5: Identify the Top Cost Driver
State which single service will account for the largest monthly spend and why.

## OUTPUT CONTRACT

1. Write the cost table and analysis as a new ADR entry in `.github/shared/architecture_log.md` under:
   `## ADR-[NNN]: Cost Analysis — [Task Name]`
2. Update `.github/shared/project_state.md` — set the cost estimation task to ✅ DONE
3. Write this exact phrase to signal completion:
   `Returning to @techLead for approval.`
