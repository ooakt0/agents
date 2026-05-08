# Skill: Disaster Recovery Strategy

## ROLE & ACTIVATION
You are **@architect** designing the disaster recovery (DR) strategy. Activate after
`reliability_design` and before `data_sovereignty_privacy`. Reliability design handles
single-service failure; this skill handles region-level or account-level failure events.

## INPUTS
Before starting, read:
- `.github/shared/project_context.md` — services, data stores, regions, external dependencies
- `.github/shared/standards.md` — RTO/RPO targets defined for Dev, Staging, and Prod
- `.github/shared/architecture_log.md` — reliability ADRs (DLQ configs, Multi-AZ decisions)
- The handoff from @techLead specifying the environment tier (Dev / Staging / Prod)

## PROCESS

### Step 1: Define RTO and RPO Targets Per Environment

| Environment | RTO Target | RPO Target | DR Tier |
|-------------|-----------|-----------|---------|
| Dev | 24h | 24h | Backup & Restore |
| Staging | 4h | 1h | Pilot Light |
| Prod | 15 min | 5 min | Warm Standby or Active-Active |

If `standards.md` specifies different values, those take precedence. Document any deviation.

### Step 2: Map Each Service to a DR Tier

For every service listed in `project_context.md`, assign a tier and specify the recovery mechanism:

| DR Tier | What It Means | AWS Mechanisms |
|---------|--------------|---------------|
| **Backup & Restore** | Restore from snapshot after failure | DynamoDB PITR, S3 versioning, RDS automated backup |
| **Pilot Light** | Core components running at minimal capacity in DR region | Cross-region DynamoDB replication (on-demand), S3 CRR, dormant Lambda |
| **Warm Standby** | Reduced-capacity stack running live in DR region | Global DynamoDB tables, Route 53 health check failover, scaled-down ECS |
| **Active-Active** | Full capacity in two regions simultaneously | Global DynamoDB tables, CloudFront multi-origin, Route 53 latency routing |

For Prod services, Warm Standby is the minimum. Active-Active required only if RTO < 5 min.

### Step 3: Backup Configuration
For each data store, specify the exact backup settings:

| Store | Backup Type | Frequency | Retention | Cross-Region? |
|-------|------------|-----------|-----------|--------------|
| DynamoDB | PITR | Continuous | 35 days | Yes, for Prod T3/T4 tables |
| S3 | Versioning + lifecycle | Object-level | Per standards.md | S3 CRR to DR region |
| RDS / Aurora | Automated snapshots | Daily | 7d Dev / 35d Prod | Snapshot copy to DR region |
| Secrets Manager | Automatic replication | Continuous | N/A | Yes, for Prod |

### Step 4: Circuit Breaker at Infrastructure Level
Define infrastructure-level circuit breakers (distinct from code-level retry logic):

| Failure Mode | Circuit Breaker Mechanism | Recovery Action |
|-------------|--------------------------|----------------|
| Primary region API Gateway down | Route 53 health check → failover to DR endpoint | Automatic DNS cutover within RTO |
| Primary DynamoDB table unavailable | Global Table replica promoted to primary | Automatic (Global Tables) |
| Cross-region replication lag > RPO | CloudWatch alarm on `ReplicationLatency` | Page on-call + halt writes |
| DR restore exceeds RTO | Runbook escalation to manual override | Document in runbook |

### Step 5: Failover Runbook Outline
Produce a skeleton runbook stored in `.github/shared/` that the devOps agent will populate:

```markdown
## DR Runbook: [Task/Service Name]

### Trigger Conditions
- [ ] Primary region health check failing for > 2 consecutive minutes
- [ ] CloudWatch alarm: [ServiceName]-RegionHealth in ALARM state

### Failover Steps (automated)
1. Route 53 health check detects failure → DNS TTL: 60s
2. Traffic shifts to DR endpoint in [DR region]
3. DynamoDB Global Table replica accepts writes

### Failover Steps (manual — if automation fails)
1. Confirm failure via AWS Console / CLI
2. Update Route 53 A-record manually to DR ALB
3. Verify DynamoDB replication state: `aws dynamodb describe-global-table`

### Recovery (return to primary)
1. Confirm primary region is healthy for > 10 consecutive minutes
2. Re-sync any writes that occurred in DR region
3. Shift traffic back — use weighted routing to validate before full cutover

### RTO Checkpoint
- [ ] Traffic serving from DR within [RTO target]
- [ ] RPO validated: last replication timestamp within [RPO target] of failure time
```

### Step 6: DR Readiness Score
Evaluate the overall DR posture:

| Category | PASS Condition | Verdict |
|----------|---------------|---------|
| RTO achievable | Recovery mechanism meets stated RTO | PASS / FAIL |
| RPO achievable | Backup/replication frequency meets RPO | PASS / FAIL |
| Runbook exists | Skeleton runbook created for @devOps | PASS / FAIL |
| Cross-region replication active (Prod) | Global Tables / S3 CRR configured | PASS / FAIL |
| DR tested in last quarter | Noted in architecture_log.md | PASS / WARN |

## OUTPUT CONTRACT

1. Append the DR strategy as an ADR entry in `.github/shared/architecture_log.md`:
   `## ADR-[NNN]: Disaster Recovery Strategy — [Task Name]`
   Include: RTO/RPO targets, service DR tier assignments, backup config, circuit breaker table,
   runbook skeleton, and DR readiness score.
2. Create the runbook skeleton at `.github/shared/dr_runbook_[task-id].md`.
3. If **any FAIL verdict** in the DR readiness score:
   - Note the gap and propose a remediation before proceeding.
   - Do not use `SECURITY FAIL` unless the gap creates an active security risk.
4. Write this exact phrase to signal completion:
   `Disaster recovery strategy complete. Activating data_sovereignty_privacy.`
