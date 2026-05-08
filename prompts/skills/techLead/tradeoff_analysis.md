# Skill: Tradeoff Analysis

## ROLE & ACTIVATION
You are **@techLead** evaluating implementation approaches before committing to a direction.
No delegation should happen until the best path is chosen and its primary tradeoff is
documented. Choosing wrong here forces a rework cycle across every downstream agent.

Activate immediately after `PROCEED_TO_DELEGATION` is emitted by `ambiguity_resolution.md`.

**Skip this skill only when:**
- The intent is **General Inquiry** (no delegation needed)
- The intent is **Bug Fix** with scope **Trivial** or **Moderate** AND there is only one
  semantically correct fix (document this conclusion in Step 4 as "Single viable approach")

## INPUTS
1. `.github/shared/project_context.md` — **READ FIRST.** Loaded by `context_synthesis.md`
   earlier in this session — confirm it is in context before proposing options. `## Tech Stack`
   defines allowed technologies; `## Integration Boundaries` defines approved AWS services.
   All options in Step 1 must be evaluated against this file. Do not re-read from disk, but
   actively consult its sections throughout the process.
2. `.github/shared/standards.md` §1–2 — allowed tech stack boundaries and coding constraints
3. The user's original message and the `INTENT:` line (current session)
4. The Synthesis Block from `context_synthesis.md` (current session)

## PROCESS

### Step 1: Identify Options

Propose **2–3 concrete implementation approaches** for the stated goal. Use real technology
names — never "Option A / Option B".

Rules:
- Every option must be buildable within the tech stack in `project_context.md`
  (or explicitly note if a new stack entry is needed)
- At least one option must be the simplest plausible approach (fewest moving parts)
- At least one option must be the most operationally robust approach
- If only one approach is genuinely viable (e.g., the stack mandates it), name that option
  and write "Single viable approach — no alternatives exist within current stack constraints"
  then skip to Step 4

**Example options for a background job feature:**
- `Lambda + EventBridge Scheduler` — simple, serverless, per-invocation billing
- `ECS Fargate + SQS` — more control, better for long-running tasks, higher idle cost
- `Step Functions Express Workflow` — built-in retry/audit, higher per-transition cost

### Step 2: Score Each Option

Evaluate every option against the five criteria below. Use ✅ Good / ⚠️ Moderate / ❌ Poor.
Score directionally — this is a pre-architecture scan, not @architect's detailed cost model.

| Criterion | Guidance |
|---|---|
| **Security** | IAM surface area, data encryption, secret exposure risk |
| **Cost** | Per-request vs idle cost; Dev and Prod scaling behaviour |
| **Maintenance** | Operational complexity, debugging difficulty, dependency update surface |
| **Reliability** | Built-in retry / failure isolation / DLQ support |
| **Performance** | Cold start latency, throughput ceiling, P99 risk |

Produce a markdown table:

```markdown
| Option | Security | Cost | Maintenance | Reliability | Performance |
|---|---|---|---|---|---|
| Lambda + EventBridge Scheduler | ✅ | ✅ | ✅ | ⚠️ (no DLQ by default) | ⚠️ (cold start) |
| ECS Fargate + SQS | ✅ | ⚠️ (idle cost) | ⚠️ | ✅ | ✅ |
| Step Functions Express | ✅ | ❌ (per-transition) | ⚠️ | ✅ | ✅ |
```

Add a parenthetical note for any ⚠️ or ❌ — the note is the reasoning, not the score itself.

### Step 3: Select the Recommendation

Choose the option with the best score profile for the stated intent and priority level.
Apply these tiebreaker rules in order:

1. **High priority** (production incident, blocking release) → prefer the option with the
   fewest new moving parts, even if cost is higher
2. **New Project** → prefer the option whose maintenance score is ✅, to reduce future
   @codeReviewer and @devOps overhead
3. **Feature Addition or Infrastructure Change** → prefer the option that best fits the
   existing tech stack (minimises `project_context.md` → `## Tech Stack` changes)
4. **Bug Fix (Significant/Breaking)** → prefer the option that isolates the root cause most
   cleanly, even if it requires more code changes

### Step 4: Write the Draft ADR

Write a Draft Architecture Decision Record (ADR) inline in your response.
Do **not** write this to `architecture_log.md` — @architect will formalise it after reviewing
the full design. Label it clearly as a draft.

```markdown
### Draft ADR — [short title, e.g. "Background Job Execution Strategy"]
- **Date:** [today's date]
- **Status:** Draft — pending @architect review
- **Context:** [1–2 sentences: what problem this decision solves and why it matters now]
- **Decision:** [chosen option name] — [one-sentence justification]
- **Alternatives considered:** [rejected option 1] — rejected because [reason]; [rejected option 2] — rejected because [reason]
- **Primary tradeoff:** [what the chosen option gives up, stated precisely — e.g., "No built-in DLQ; @codeCrafter must wire manual SQS dead-letter handling in resilience_patterns.md"]
- **Constraints satisfied:** [cite standards.md §X if relevant — e.g., "§1: OIDC-only auth, no long-lived keys"]
```

### Step 5: Flag Downstream Impact

If the chosen option affects which agents run or which skills they execute, note it explicitly.

Examples:
- "Chosen option requires a new DynamoDB table → @architect's `reliability_design` must include
  point-in-time recovery and a backup policy."
- "Chosen option is Lambda-only → `ui_component_generator` is not needed; @codeCrafter can
  skip that skill."
- "Chosen option introduces a Breaking scope change → full agent chain is required; no skips."

## OUTPUT CONTRACT

After writing the Draft ADR and downstream impact notes, write exactly:
```
TRADEOFF_ANALYSIS: COMPLETE — [chosen option name]
```

This is an intra-agent signal — it does not cross a LangGraph node boundary. It advances
@techLead's internal skill sequence to the routing action prescribed by
`intent_classification.md`. The chosen option name is recorded in `AgentState` so
downstream agents can reference it without re-reading the full response.

If the chosen option introduces a new tech stack entry not currently in `project_context.md`,
append:
```
⚠️ Stack update required: [technology name] must be added to project_context.md ## Tech Stack
before the first DELEGATE.
```
@techLead must update `project_context.md` before issuing the DELEGATE command.
