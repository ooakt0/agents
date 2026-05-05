# Architecture Decision Log

**Project:** [Populated from project_state.md on first use]
**Maintained by:** @architect
**Read by:** @codeCrafter (before every implementation), @codeReviewer (for context), @techLead (for oversight)

---

## ADR Entry Template

Copy this block for each new architecture decision. Do not modify the template itself.

```markdown
---
## ADR-[NNN]: [Short Decision Title]

**Date:** [YYYY-MM-DD]
**Status:** Proposed | Accepted | Deprecated | Superseded by ADR-[NNN]
**Decided by:** @[agentName] | Approved by: @techLead
**Related Task:** T-[NNN] in project_state.md

### Context
[1-3 sentences: what problem or question forced this decision?]

### Decision
[1-2 sentences: what was decided? Be specific — name the service, library, or pattern.]

### Consequences
**Positive:**
- [Bullet: what does this enable?]

**Negative / Trade-offs:**
- [Bullet: what does this make harder or more expensive?]

### Alternatives Considered
| Option | Reason Rejected |
|--------|-----------------|
| [Alt 1] | [Why not] |
| [Alt 2] | [Why not] |

### Cost Impact (if applicable)
[One sentence from cost_estimation skill output, or "N/A"]

### Security Impact (if applicable)
[One sentence from security_group_audit skill output, or "N/A"]
```

---

## ADR-001: Adopt AWS CDK v2 (TypeScript) for All Infrastructure

**Date:** [DATE_INITIALIZED]
**Status:** Accepted
**Decided by:** @architect | Approved by: @techLead
**Related Task:** T-001

### Context
The project requires repeatable, version-controlled infrastructure provisioning. Manual Console
changes are not auditable and cannot be peer-reviewed. A typed IaC approach reduces drift
between environments.

### Decision
Use AWS CDK v2 in TypeScript (strict mode) for all infrastructure. No Terraform, no raw
CloudFormation YAML authored directly.

### Consequences
**Positive:**
- Infrastructure is type-checked at compile time, catching resource config errors before deployment
- Reuses the same TypeScript toolchain and linting rules as application code
- L2/L3 constructs provide opinionated, secure defaults (e.g., S3 buckets with block-public-access on)

**Negative / Trade-offs:**
- Team members must know TypeScript; YAML-only engineers face a learning curve
- CDK synthesizes CloudFormation, adding an indirection layer when debugging deployment failures

### Alternatives Considered
| Option | Reason Rejected |
|--------|-----------------|
| Terraform | Different language from application code; no compile-time type safety on AWS resource properties |
| CloudFormation YAML | No abstraction; verbose; requires macros for loops and conditions |
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
