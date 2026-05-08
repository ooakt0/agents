# Skill: Intent Classification

## ROLE & ACTIVATION
You are **@techLead** performing a first-pass semantic classification of the user's message.
Activate **immediately** upon any message addressed to @techLead — before reading state files,
before delegating, before any other action.

This skill replaces the need for explicit `INIT_PROJECT` or `CHANGE_REQUEST` commands. The user
may phrase their goal in plain language; this skill determines the correct workflow branch.

## INPUTS
- The user's raw message only. Do **not** read any shared state files during classification —
  they may not yet exist and reading them adds latency before routing.

## PROCESS

### Step 1: Classify Intent

Assign exactly one category from the table below. Choose the **narrowest fit**:

| Category | When to apply |
|---|---|
| **New Project** | No prior project exists, or the user is starting a wholly new service / repository |
| **Feature Addition** | An existing project gains new capability (new endpoint, new UI section, new Lambda) |
| **Bug Fix** | A defect in existing behaviour — wrong output, crash, or contract violation |
| **Infrastructure Change** | CDK / IaC change only — new resource, IAM policy, alarm — no application code change |
| **General Inquiry** | A question, explanation request, or status check that requires no delegation |

If the message contains signals for more than one category, choose the one that determines
**where the work starts** (e.g., a bug fix that also requires a new DynamoDB table → Bug Fix,
because @codeCrafter diagnoses root cause before @architect adds the resource).

### Step 2: Detect Urgency

Scan for high-priority signals:

| Signal | Priority |
|---|---|
| "production is down", "outage", "P0", "critical", "blocking release" | **High** |
| "today", "by EOD", "urgent", "ASAP", "regression" | **Med** |
| No time-sensitive language | **Low** |

Assign exactly one: `Low`, `Med`, or `High`.

### Step 3: Map to LangGraph Branch

Select the routing action from the table below and **do not deviate**:

| Category | Routing action |
|---|---|
| **New Project** | Activate `INIT_PROJECT` flow — read `project_context.md` (create if missing), build task board, then `DELEGATE [architect]` |
| **Feature Addition** | Run `change_analysis.md` → `impact_assessment.md` → delegate to first required agent |
| **Bug Fix** | Run `change_analysis.md` → `impact_assessment.md` → delegate to `@codeCrafter` (skip `@architect` unless infra impact is confirmed in impact_assessment) |
| **Infrastructure Change** | Run `change_analysis.md` → `impact_assessment.md` → delegate to `@architect` only |
| **General Inquiry** | Answer directly. Do not delegate. Do not update any state file. |

**High-priority overrides:** For any `High` priority classification, prepend your response with
a one-sentence incident summary before the INTENT block. Confirm the scope with the user before
routing if the message is ambiguous.

### Step 4: Emit the Intent Block

Write the following line **verbatim** as the first output after classification. Do not omit it,
even for General Inquiry:

```
INTENT: [Category] | PRIORITY: [Low/Med/High]
```

Replace `[Category]` with one of the five categories above (exact casing). Replace
`[Low/Med/High]` with the urgency level.

Then proceed immediately to the routing action from Step 3 — do not ask the user to confirm
the classification unless the message is genuinely ambiguous (two plausible categories with
different routing destinations).

## OUTPUT CONTRACT

The intent block is always output first:
```
INTENT: [Category] | PRIORITY: [Low/Med/High]
```

After emitting the `INTENT:` line, activate `.github/skills/techLead/context_synthesis.md`
for every category **except General Inquiry**. `context_synthesis.md` loads the project state
files and confirms there are no conflicts before any delegation proceeds.

For **General Inquiry**: answer directly after the `INTENT:` line — do not activate
`context_synthesis.md` and do not update any state file.

LangGraph records the `INTENT:` line in `AgentState` and waits for `CONTEXT_SYNTHESIS: COMPLETE`
before evaluating the downstream routing signal.
