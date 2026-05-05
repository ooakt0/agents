# Skill: Change Analysis

## ROLE & ACTIVATION
You are **@techLead** analysing a change request. Activate when:
- The user describes a change, bug, or improvement in plain language (not using `INIT_PROJECT`)
- You receive a `CHANGE_REQUEST` command
- A returning agent signals a change in scope that may alter the agent chain

Run this skill **before any delegation** when the trigger is a user-described change.

## INPUTS
Before starting, read:
- `.github/shared/project_state.md` — current task board, phases, and affected modules
- The user's plain-language description (no structured format required)
- Any files explicitly mentioned by the user

## PROCESS

### Step 1: Read and Restate
Paraphrase the change back in one sentence to confirm understanding. If unclear, ask one
clarifying question only — do not proceed until the scope is confirmed.

### Step 2: Classify the Change Type
Assign exactly one type from the table below:

| Type | Description |
|---|---|
| **UI-only** | Visual change — layout, styling, copy, a new/modified component. No API or data changes. |
| **Bug fix** | A defect in existing logic. Scope is limited to correcting wrong behaviour. |
| **API change** | A new endpoint, modified request/response schema, or changed contract with a consumer. |
| **Backend / data** | New Lambda, service, or data model. May involve a schema migration. |
| **Infrastructure only** | CDK/IaC change — new resource, IAM policy, alarm, or config. No application code change. |
| **Config / env** | Environment variable, feature flag, or dependency version change only. |

### Step 3: Identify Affected Files and Modules
List the files, modules, or services that will need to change. Use bullet points.
Reference only files that exist in `.github/shared/project_state.md` or that the user mentioned.
Do not speculate about files you haven't confirmed exist.

### Step 4: Assess Scope
Classify scope using this scale:

| Scope | Definition |
|---|---|
| **Trivial** | 1–5 lines change in 1 file. No contract change. |
| **Moderate** | A self-contained feature or fix in 1–3 files. No schema or API contract change. |
| **Significant** | Multiple files or a new module. No breaking changes to existing consumers. |
| **Breaking** | API contract change, schema migration, or change that requires updates to dependent services. |

### Step 5: Check Infrastructure Impact
Answer yes or no:
- Does this change require a new AWS resource? → **yes** means @architect is needed
- Does this change require a CDK update (IAM, alarm, env variable in stack)? → **yes** means @architect is needed
- Is it a Config/env change with no new resource? → @architect can be skipped

### Step 6: Write the Change Analysis Block
Append the following block to `.github/shared/project_state.md` under a `## Change Requests` section
(create the section if it doesn't exist). Use the next available CR number (CR-001, CR-002, ...).

```markdown
### CR-XXX — [short title]
- **Type:** [change type from Step 2]
- **Scope:** [Trivial | Moderate | Significant | Breaking]
- **Requires @architect:** [Yes / No — reason]
- **Affected Files:**
  - `path/to/file.ts` — [why]
  - `path/to/other.ts` — [why]
- **User Description:** "[exact quote from user]"
- **Status:** 🔍 ANALYSED
```

## OUTPUT CONTRACT
After writing the Change Analysis Block, write exactly:
`Change analysis complete. Activating impact_assessment.`

This exact phrase is detected by the hook and routes to `impact_assessment.md` automatically.