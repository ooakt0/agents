# Skill: Service Boundary Analysis

## ROLE & ACTIVATION
You are **@architect** enforcing microservice domain boundaries. Activate this skill FIRST — before
observability, reliability, or any infrastructure design. A feature that belongs in a separate service
must be identified before code is written, not after.

## INPUTS
Before starting, read:
- `.github/shared/project_context.md` — existing services, data stores, entry points, integration boundaries
- `.github/shared/architecture_log.md` — prior boundary decisions and domain definitions
- `.github/shared/standards.md` — coupling and cohesion rules
- The handoff from @techLead describing the feature or capability to be built

## PROCESS

### Step 1: Map the Feature to an Existing Domain
List all existing services/Lambdas from `project_context.md`. For the new feature, answer:

1. **What data does it own?** (creates, mutates, or is the source-of-truth for)
2. **What is its deployment lifecycle?** (does it change independently of other services?)
3. **Who calls it?** (single upstream caller = potentially a module, many callers = separate service)
4. **What does it need to read from others?** (high read dependency = likely wrong boundary)

Place the feature in the existing service that owns the same data, or flag it as a new service
candidate if it owns distinct data and has an independent lifecycle.

### Step 2: Coupling Check
For each proposed Lambda-to-Lambda or Lambda-to-database relationship, evaluate:

| Relationship | Pattern | Verdict |
|-------------|---------|---------|
| Synchronous call chain > 2 hops | Tight coupling — refactor | FAIL |
| Shared database table between two services | Data coupling — separate ownership | FAIL |
| Direct Lambda invoke (non-idempotent) | Replace with SQS/SNS | WARN |
| Lambda reads another service's DynamoDB directly | Cross-domain read — use API or event | FAIL |
| Event consumer adds no new data | May be a module, not a service | WARN |

For each FAIL: name the specific services/resources involved and the coupling type.

### Step 3: Async Decoupling Recommendations
Where coupling violations are found, specify the decoupling mechanism:

| Coupling Type | Recommended Fix | When to Apply |
|---------------|----------------|--------------|
| Sync call for non-critical notification | Replace with SNS publish | Always |
| Sync call for durable work | Replace with SQS + Lambda trigger | When retries matter |
| Bidirectional sync dependency | Introduce EventBridge event bus | Complex domains |
| Shared table for status updates | Stream DynamoDB Streams to consumer | Read-only fan-out |

### Step 4: New Service Decision Gate
If the feature does not belong in any existing service, evaluate whether to create a new one:

**Create a new service if ALL of:**
- [ ] It owns data no existing service owns
- [ ] It has a different deployment frequency than existing services
- [ ] It would be called by 2 or more upstream services
- [ ] It has distinct scalability requirements

**Keep it as a module if ANY of:**
- [ ] It shares the same data store as an existing service
- [ ] It is only ever called by one service
- [ ] It has no independent failure mode worth isolating

Document the decision and rationale explicitly.

### Step 5: Anti-Pattern Check
Scan `project_context.md` for known distributed-monolith anti-patterns:

| Anti-Pattern | Detection Signal | Action |
|-------------|-----------------|--------|
| Chatty microservices | > 3 sync calls per request path | Consolidate or introduce BFF |
| God Lambda | Single function > 200 lines or > 5 responsibilities | Split by domain |
| Shared mutable state | Two services write to same DynamoDB table | Assign a single owner |
| Synchronous fan-out | One Lambda calling 3+ others inline | Replace with parallel Step Functions or SNS |

## OUTPUT CONTRACT

1. Write the boundary analysis as an ADR entry in `.github/shared/architecture_log.md`:
   `## ADR-[NNN]: Service Boundary Analysis — [Task Name]`
   Include: domain map, coupling check table, decoupling recommendations, new-service decision.
2. If **any FAIL verdict** exists that blocks implementation:
   - Write this exact phrase to hold the workflow:
     `SECURITY FAIL: [one-sentence description of the boundary violation]`
     *(Uses the SECURITY FAIL hook to halt — boundary violations are architectural blockers.)*
3. If all checks pass or only WARNs remain:
   - Update `.github/shared/project_state.md` with boundary decisions.
   - Write this exact phrase:
     `Service boundary analysis complete. Activating observability_design.`
