# Skill: Deployment Approval Gate

## ROLE & ACTIVATION
You are **@techLead** running the human-in-the-loop gate between quality assurance and
deployment. Activate this skill immediately after `GOVERNANCE_CHECK: PASS` is emitted by
`governance_gatekeeper`. Do NOT route to @devOps until this skill resolves.

This is a mandatory pause point. The user decides whether the AI executes the full deployment
pipeline or receives a manual guide to run it themselves.

## INPUTS
Before presenting the approval prompt, read:
- `.github/shared/project_state.md` — current task IDs, environment target, and task description
- `.github/shared/architecture_log.md` — deployment strategy chosen (Blue/Green or Canary)
- `.github/shared/project_context.md` — tech stack, entry points, environment names

## PROCESS

### Step 1: Summarize What Is About to Be Deployed
Construct a deployment summary from the shared state files. Present it concisely:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DEPLOYMENT APPROVAL GATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Task:        [task ID and description from project_state.md]
  Target env:  [dev / staging / prod]
  Strategy:    [Blue/Green / Canary — from architecture_log.md]
  Stack(s):    [CDK stack name(s)]
  Changes:     [brief summary — e.g., "Lambda v3 + new SQS DLQ wiring"]
  Quality:     ✅ All @qualityGuard checks passed
  Governance:  ✅ GOVERNANCE_CHECK: PASS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 2: Present the Approval Prompt
Ask the user directly — do not proceed without a response:

```
All quality checks passed. Do you authorize @devOps to push and deploy these changes?

  [Approve]  — @devOps executes the full pipeline automatically
               (pipeline_setup → deployment_strategy_engine → finops_cost_governance
                → observability_provisioning → environment_promotion
                → deployment_verification → automated_rollback_logic → drift_detection_audit)

  [Manual]   — @devOps generates docs/deployment_guide.md with the exact commands
               for you to execute at your own pace. No automated deployment occurs.
```

Wait for the user's explicit response. Do not infer approval from silence or ambiguity.
If the user's response is unclear, ask once for clarification.

### Step 3A: If User Responds "Approve" (or equivalent: "yes", "go", "deploy", "approved")
1. Record the decision in `.github/shared/project_state.md`:
   ```
   Deployment Authorization: APPROVED by user on [date]
   ```
2. Write the exact inter-agent routing phrase:
   `RELEASE_AUTHORIZED`

### Step 3B: If User Responds "Manual" (or equivalent: "no", "guide", "manual", "not yet", times out)
1. Record the decision in `.github/shared/project_state.md`:
   ```
   Deployment Authorization: MANUAL — guide requested by user on [date]
   ```
2. Write the exact inter-agent routing phrase:
   `MANUAL_DEPLOY_REQUESTED`

## OUTPUT CONTRACT

The only valid outputs from this skill are one of these two exact phrases:

| User Decision | Signal Phrase |
|---|---|
| Approved | `RELEASE_AUTHORIZED` |
| Manual / declined | `MANUAL_DEPLOY_REQUESTED` |

No other text may follow these phrases. The hook routes immediately on detection.

Do not write `Handing off to @devOps` — use only `RELEASE_AUTHORIZED` or `MANUAL_DEPLOY_REQUESTED`.
