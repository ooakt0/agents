# Skill: Impact Assessment

## ROLE & ACTIVATION
You are **@techLead** deciding which agent chain to activate for a change request.
Activate immediately after `Change analysis complete. Activating impact_assessment.` is written.

## INPUTS
Before starting, read:
- The Change Analysis Block just written to `.github/shared/project_state.md` (CR-XXX)
- `.github/shared/standards.md` — to confirm which reviews are mandatory for the scope
- `.github/skills/techLead/handoff_template.md` — to prepare the DELEGATE output

## PROCESS

### Step 1: Select the Agent Chain
Use the routing table below. Match the **Change Type** and apply the corresponding chain.
If scope is **Breaking**, always escalate to the full chain regardless of type.

| Change Type | Mandatory Agents | Agents That May Be Skipped |
|---|---|---|
| **UI-only** | @codeCrafter (ui_component_generator only) → @codeReviewer (naming + documentation only) → @qualityGuard (unit tests only) | @architect, load_test, penetration_scan |
| **Bug fix** | @codeCrafter → @codeReviewer (full) → @qualityGuard (unit + integration) → @devOps | @architect (unless fix touches infra) |
| **API change** | @codeCrafter → @codeReviewer (full) → @qualityGuard (full) → @devOps | @architect (unless schema or infra changes — see Step 2) |
| **Backend / data** | @architect (if new resource or schema) → @codeCrafter → full chain | Nothing skipped when scope is Significant or Breaking |
| **Infrastructure only** | @architect → @devOps | @codeCrafter, @codeReviewer, @qualityGuard |
| **Config / env** | @codeReviewer (documentation_check only) → @devOps | @architect, @codeCrafter, @qualityGuard |

**Override rule:** If `Scope = Breaking`, run the **full chain** regardless of change type.
Document the override in the justification.

### Step 2: Determine if @architect is Needed
Always include @architect if the CR analysis (Step 5 of change_analysis.md) answered **yes** to
either infra question. Skip @architect only when:
- No new AWS resource is created
- No CDK stack is modified
- No IAM policy is added or changed

### Step 3: List Skipped Agents and Justify Each
For every agent or skill that is being skipped, write one sentence justifying the skip.
Example justifications:
- "@architect skipped — no new AWS resources or CDK changes."
- "load_test skipped — change is a CSS-only UI update with no backend traffic impact."
- "penetration_scan skipped — bug fix does not touch authentication, input handling, or data access layer."

Do not skip without justification. Unjustified skips are treated as full-chain by @codeReviewer.

### Step 4: Set the Task in project_state.md
Update the CR-XXX block status from `🔍 ANALYSED` to `🏗️ ACTIVE`.
Add a `**Agent Chain:**` line listing the agents in order.
Add a `**Skipped:**` line listing skipped agents and their justification.

### Step 5: Fill the Handoff Template
Use `.github/skills/techLead/handoff_template.md` for the first agent in the chain.
In the METADATA section:
- Set `**Change Type:**` to the CR type
- Set `**Language / Stack:**` from the CR affected files
- Include a `**Shortened Chain:**` field listing which agents are active and which are skipped

## OUTPUT CONTRACT
After completing all steps, write:
`Impact assessment complete. Delegating to @[first-agent-name].`

Then immediately produce the filled handoff template for the first agent in the chain.

This exact phrase is detected by the hook, which reminds you to begin the DELEGATE handoff.