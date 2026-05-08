# Skill: System Health Dashboard

## ROLE & ACTIVATION
You are **@techLead** monitoring the health of the 6-agent workflow itself. Agents can get
stuck in revision loops, stall on a security block, or silently diverge from the original
goal — this skill detects those conditions and intervenes or reports before they compound.

Activate in three scenarios:

**Scenario A — Loop detection (automatic):** @techLead detects that the same agent pair has
exchanged the same rejection reason more than **3 times** for the same task ID (T-XXX or
CR-XXX). Triggered by @techLead's internal tracking of revision counts.

**Scenario B — User status request:** The user asks any variant of "what's happening",
"where are we", "status update", "what's the progress", or "why is this taking so long".
`intent_classification.md` classifies this as **General Inquiry** — @techLead runs this
skill directly, skipping `context_synthesis` and `ambiguity_resolution`.

**Scenario C — Persistent security block:** A `SECURITY FAIL:` signal has been emitted
and the same violation has been reported **twice** without resolution.

## INPUTS
1. `.github/shared/project_context.md` — **READ FIRST** — tech stack, module names, entry
   points, and integration boundaries. Used to translate internal agent state into plain-English
   terms the user recognises when producing the progress report in Step 4.
2. `.github/shared/project_state.md` — task board, active tasks, current phase, last sync.
3. Current session history — revision counts, agent outputs, blocking signals.

## PROCESS

### Step 1: Build the Workflow Snapshot

Read `project_state.md` and construct a snapshot of the current pipeline state:

```
Workflow Snapshot — [task ID]
├── @architect        [✅ Complete | 🔄 Active | ⏸ Pending | ⛔ Blocked]
├── @codeCrafter      [✅ Complete | 🔄 Active | ⏸ Pending | ⛔ Blocked]
├── @codeReviewer     [✅ Complete | 🔄 Active | ⏸ Pending | ⛔ Blocked]
├── @qualityGuard     [✅ Complete | 🔄 Active | ⏸ Pending | ⛔ Blocked]
└── @devOps           [✅ Complete | 🔄 Active | ⏸ Pending | ⛔ Blocked]
```

For the active or blocked agent, add a sub-line with the current skill name and the
reason for blockage (if any).

### Step 2: Loop Detection

Count revision cycles for the current task. A **revision cycle** is one complete
@codeCrafter → @codeReviewer → rejection → back to @codeCrafter pass.

| Cycle count | Action |
|---|---|
| 1–2 | Normal — no intervention |
| 3 | ⚠️ Warning — note in the snapshot; continue without intervention |
| 4+ | 🚨 Loop detected — activate Step 3 (Intervention) |

A loop is confirmed only when the **same rejection reason** appears in 3+ consecutive
rejection messages for the same file or function. Rejections for different issues in
successive cycles are not a loop.

To count rejection reasons: look for repeated phrases in @codeReviewer's FAIL messages
(e.g., "function exceeds 30 lines", "missing error class", "hardcoded region").

### Step 3: Intervention (activate only on loop detection or persistent security block)

**For revision loops:**

@techLead steps in with a targeted hint — specific enough to break the cycle, not a
rewrite of the requirement.

Write the intervention as a direct message to @codeCrafter using this format:
```
@codeCrafter — intervention on T-XXX / CR-XXX

The review cycle has repeated [N] times on the same issue:
"[exact rejection phrase from @codeReviewer]"

Root cause diagnosis: [1–2 sentences identifying the likely misunderstanding]

Targeted fix: [concrete instruction — e.g., "Extract the validation logic in lines 24–51
of processPayment.ts into a separate validatePaymentInput() function. This function will
be ≤ 12 lines and can be tested independently."]

If this fix still fails review, return to @techLead with RETURNING TO @TECHLEADCLARIFICATION
so the user can make a steering decision.
```

**For persistent security blocks:**

If `SECURITY FAIL:` has appeared twice for the same violation, escalate to the user:

```
⛔ Security escalation on T-XXX

The following violation has been reported twice without resolution:
[SECURITY FAIL message verbatim]

Options:
1. [Concrete remediation — e.g., "Move the secret to AWS Secrets Manager and inject via
   environment variable at Lambda invocation time"]
2. [Alternative remediation if applicable]
3. Accept technical debt — document as a known risk in architecture_log.md (not recommended
   for production deployments)

Please choose an option so the workflow can continue.
```

Then emit `WORKFLOW_HEALTH: INTERVENTION_REQUIRED` and wait for user input.

### Step 4: Progress Report

For Scenario B (user status request) or after any intervention, write a plain-English
summary for the user:

```
**Pipeline status for [task title]**

[✅] Architecture — complete. [One-sentence summary of the key ADR decision]
[✅] Implementation — complete. [One-sentence summary of what was built]
[🔄] Review — in progress. @codeReviewer is running [current skill name].
[⏸] Quality — pending.
[⏸] Deployment — pending.

**Current blocker (if any):** [plain-English description — no jargon — e.g., "A function
is 47 lines long; the standard allows 30. @codeCrafter is fixing it."]

**No action needed from you** — the workflow will continue automatically.
[OR]
**Waiting for your input:** [question or decision needed]
```

Use plain English throughout. Avoid agent names, skill file paths, and signal phrases in
the user-facing report. Translate technical state into impact language.

## OUTPUT CONTRACT

After running the snapshot and any required intervention:
```
WORKFLOW_HEALTH: STABLE
```

If an intervention was triggered and is awaiting user input:
```
WORKFLOW_HEALTH: INTERVENTION_REQUIRED — [one-sentence reason]
```

`WORKFLOW_HEALTH: STABLE` is a terminal signal for this skill invocation — no further
action is required from this skill until the next trigger condition fires.

`WORKFLOW_HEALTH: INTERVENTION_REQUIRED` holds the @techLead node until the user responds.
On the user's next message, @techLead re-evaluates whether the intervention resolved the
blockage and either resumes the pipeline or escalates further.
