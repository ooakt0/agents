# Architecture Decision Log
**Project:** [Populated from project_context.md at INIT_PROJECT]
**Maintained by:** @architect
**Read by:** @codeCrafter (before every implementation), @codeReviewer (architectural_alignment_audit), @techLead (oversight and approval)

> **Rules:**
> - Every architecture decision gets an ADR at decision time — not retroactively.
> - ADRs are permanent. Never delete an entry. Mark as `Superseded by ADR-NNN` if the decision changes.
> - @codeCrafter must cross-reference ADRs before writing a single line of implementation.
> - @codeReviewer must verify implementation conformance against every accepted ADR in `architectural_alignment_audit`.

---

## ADR Entry Template

Copy this block for each new decision. Do not modify the template itself.

```markdown
---
## ADR-[NNN]: [Short Decision Title]

**Date:** [YYYY-MM-DD]
**Status:** Proposed | Accepted | Deprecated | Superseded by ADR-[NNN]
**Decided by:** @[agentName] | **Approved by:** @techLead
**Related task:** T-[NNN] in project_state.md
**Reversibility:** High (easy to change) | Medium (migration required) | Low (very hard to undo)

### Context
[2-4 sentences: what problem, constraint, or question forced this decision? Include the business and technical drivers.]

### Decision
[1-3 sentences: exactly what was decided. Name the specific service, library, pattern, or configuration. Be precise enough that @codeCrafter can implement it without asking follow-up questions.]

### Implementation notes
[Bullet points for @codeCrafter: specific CDK constructs, SDK calls, config values, or patterns to use. Include what NOT to do if relevant.]

### Consequences

**Positive:**
- [What this decision enables or improves]

**Negative / Trade-offs:**
- [What becomes harder, more expensive, or constrained by this decision]

**Risks:**
- [What could go wrong, and what mitigates it]

### Alternatives Considered

| Option | Reason rejected |
|--------|-----------------|
| [Alt 1] | [Specific technical or business reason] |
| [Alt 2] | [Specific technical or business reason] |

### Cost Impact
[Estimated monthly cost delta in USD, or "No significant impact". From cost_estimation skill output.]

### Security Impact
[One sentence from security_group_audit output, or "No additional attack surface introduced".]

### Performance Impact
[P99 latency or throughput implication, or "No measured regression expected".]
```

---

## ADR-001: Adopt AWS CDK v2 (TypeScript) for All Infrastructure

**Date:** [DATE_INITIALIZED]
**Status:** Accepted
**Decided by:** @architect | **Approved by:** @techLead
**Related task:** T-001
**Reversibility:** Low — migrating IaC tooling requires full stack re-provisioning

### Context
The project requires repeatable, version-controlled infrastructure provisioning across dev, staging, and production environments. Manual Console changes are not auditable, cannot be peer-reviewed, and cause environment drift. A typed IaC approach catches resource misconfigurations at compile time rather than at deploy time.

### Decision
Use AWS CDK v2 in TypeScript (strict mode) for all infrastructure. No Terraform, no raw CloudFormation YAML authored directly, no Console-only changes. All CDK stacks must pass `cdk-nag AwsSolutionsChecks` with no suppressions unless a waiver ADR exists.

### Implementation notes
- Use `cdk-nag` as a CDK aspect, applied at the app level in the CDK entry point.
- L2 constructs preferred; L1 (`CfnXxx`) only when no L2 exists or when a specific property is unavailable.
- Tag all stacks with the five required tags (see §1.5 of standards.md) using `Tags.of(app).add(...)`.
- `cdk synth` must run in CI with `--strict` and produce zero warnings before a PR merges.

### Consequences

**Positive:**
- Infrastructure is type-checked at compile time, catching resource config errors before deploy
- Reuses the same TypeScript toolchain and linting rules as application code — single CI pipeline
- L2/L3 constructs provide opinionated, secure defaults (S3 block-public-access on, Lambda no public URL, etc.)
- `cdk diff` gives a human-readable change set for code review

**Negative / Trade-offs:**
- Engineers must know TypeScript; YAML-only engineers face a learning curve
- CDK synthesizes CloudFormation, adding an indirection layer when debugging deployment failures
- CDK version upgrades can change generated CloudFormation, requiring careful testing

**Risks:**
- CDK bootstrap drift between accounts — mitigated by pinning bootstrap version in pipeline

### Alternatives Considered

| Option | Reason rejected |
|--------|-----------------|
| Terraform | Different language from application code; no compile-time type safety on AWS resource properties; state file management complexity |
| CloudFormation YAML | No abstraction; verbose; requires macros for loops and conditions; no type checking |
| Pulumi (TypeScript) | Less mature AWS provider; smaller ecosystem; unfamiliar to team |

### Cost Impact
No direct cost. Indirectly reduces cost through faster environment parity and fewer manual-error-induced over-provisioned resources.

### Security Impact
`cdk-nag` enforces IAM least-privilege and encryption-at-rest checks automatically, reducing security surface compared to hand-authored CloudFormation.

### Performance Impact
No runtime performance implication. CDK synth adds ~10–30 s to CI pipeline.

| Pulumi (Python) | Language mismatch with the TypeScript application codebase |

### Cost Impact
N/A — CDK itself has no runtime cost; only the provisioned resources incur charges.

### Security Impact
CDK L2 constructs apply secure defaults (encrypted S3, private subnets). Still requires
security_group_audit review per task.

---

## Instructions for @architect (Adding a New ADR)

1. Copy the ADR Entry Template block above (between the triple backticks)
2. Replace `[NNN]` with the next sequential number (check the highest existing ADR number)
3. Fill in **all** fields — do not leave any as `[placeholder]` in your output
4. Set Status to `Proposed` initially; @techLead changes it to `Accepted` after approval
5. Link the ADR number in `.github/shared/project_state.md` under the **Recent Decisions** section
6. After @techLead approval, update Status to `Accepted` and record the approval date
