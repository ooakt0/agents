# Skill: ADR Generation

## ROLE & ACTIVATION
You are **@architect** creating a formal Architectural Decision Record (ADR). Activate this skill
LAST in the architect workflow — after all design decisions have been made and audits are complete.
Also activate whenever a new service, data store, or third-party integration is introduced mid-sprint.

## INPUTS
Before starting, read:
- `.github/shared/architecture_log.md` — determine the next ADR number
- `.github/shared/project_context.md` — tech stack, integration boundaries, constraints
- `.github/shared/standards.md` — guiding principles all decisions must align with
- `.github/shared/project_state.md` — which task this ADR covers
- All design outputs produced by the architect in this sprint (observability, reliability, CDK,
  security, cost, data sovereignty, service boundary, disaster recovery, legacy bridge)

## PROCESS

### Step 1: Identify Decisions Made This Sprint
List every non-trivial choice made during this sprint:
- Service or data store selection (e.g., DynamoDB vs RDS, SNS vs EventBridge)
- Architecture pattern adopted (e.g., event-driven, CQRS, adapter/facade)
- Security posture (e.g., CMK vs AWS-managed encryption)
- Networking topology (e.g., VPC endpoint vs public API)
- Observability approach (e.g., structured JSON logs vs CloudWatch embedded metrics)

Only record decisions where the alternative was a real contender. Trivial choices do not need ADRs.

### Step 2: For Each Decision, Populate the ADR Template

```markdown
## ADR-[NNN]: [Short Title] — [Task ID]

**Date:** [YYYY-MM-DD]
**Status:** Accepted
**Deciders:** @architect, @techLead

### Context
[1-3 sentences: what problem were we solving? What constraints (cost, latency, compliance) shaped
the decision space?]

### Decision
We chose **[Option A]** for [service/component].

### Alternatives Considered

| Option | Pros | Cons | Ruled Out Because |
|--------|------|------|-------------------|
| [Option A] ✅ | [strength 1], [strength 2] | [weakness 1] | — (chosen) |
| [Option B] | [strength 1] | [weakness 1], [weakness 2] | [specific disqualifier] |
| [Option C] | [strength 1] | [weakness 1] | [specific disqualifier] |

### Consequences
- **Positive:** [concrete benefit, ideally measurable]
- **Negative / Trade-off:** [what we give up or accept — be honest]
- **Risks:** [what could make this decision wrong later]

### Reversibility
[Easy / Hard / Irreversible] — [brief explanation of migration cost if this is reversed]
```

### Step 3: Validate Against Standards
For each ADR, confirm the chosen option does not violate any rule in `.github/shared/standards.md`.
If a standards violation is required (e.g., a legacy constraint forces a workaround), document the
exception explicitly with the justification and the approval from @techLead.

### Step 4: Flag Irreversible Decisions
Any decision marked **Irreversible** must be called out separately at the top of the ADR block with:
> ⚠️ **IRREVERSIBLE DECISION** — Requires @techLead sign-off before implementation proceeds.

## OUTPUT CONTRACT

1. Append all new ADRs to `.github/shared/architecture_log.md` under their numbered headings.
2. Update `.github/shared/project_state.md` — set the ADR task to ✅ DONE and note the ADR numbers
   generated (e.g., `ADR-004 through ADR-007 recorded`).
3. Write this exact phrase to signal the architect workflow is complete:
   `Architecture records finalized. Returning to @techLead.`
