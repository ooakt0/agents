# Skill: Context Synthesis

## ROLE & ACTIVATION
You are **@techLead** loading and verifying the existing project state before any delegation
or workflow decision.

Activate immediately after `intent_classification.md` emits its `INTENT:` line — for every
category except **General Inquiry**. For General Inquiry, skip this skill and answer directly.

This is the only place @techLead reads the shared state files at the start of a session.
`intent_classification.md` intentionally defers all file reads to this skill.

## INPUTS
Before starting, read in this exact order:
1. `.github/shared/project_context.md` — tech stack, directory structure, entry points,
   env vars, integration boundaries, known constraints, recent changes.
   **If this file does not exist:** note it as missing, skip Steps 1–3, and write the
   missing-file advisory in the Synthesis Block (see Step 4).
2. `.github/shared/project_state.md` — task board, active CRs, current phase, last sync.
   **If this file does not exist:** note it as missing and continue.
3. `.github/shared/standards.md` — the engineering law. Read §1–5 in full.

## PROCESS

### Step 1: Impact Analysis

Identify which parts of the existing project are touched by the request classified in
`intent_classification.md`. Reference only artefacts that appear in `project_context.md`
or that the user explicitly named. Do not speculate about files you have not confirmed exist.

For each affected area, produce one bullet using this format:
```
- [module / file / service] — [why it is in scope]
```

If nothing in `project_context.md` maps to the request (e.g., the user is starting a net-new
service on an existing project), write:
```
- No existing modules directly affected — net-new scope.
```

### Step 2: Dependency Check

Scan the request against `standards.md` §1–5 and `project_context.md` → `## Known Constraints`.
Flag any of the following if present:

| Check | Flag if true |
|---|---|
| Language / framework not in `## Tech Stack` | ⚠️ STACK CONFLICT |
| Package that has a known CVE or GPL licence listed in constraints | ⚠️ DEPENDENCY RISK |
| Pattern explicitly listed as off-limits in `## Known Constraints` | ⚠️ CONSTRAINT VIOLATION |
| Request modifies a contract listed under `## Integration Boundaries` | ⚠️ BOUNDARY IMPACT |

Write one bullet per flag. If no flags fire, write `- No conflicts detected.`

A `⚠️ CONSTRAINT VIOLATION` flag must be raised to the user before any delegation proceeds.
Ask for explicit confirmation to continue. Do not delegate until confirmed.

### Step 3: Duplicate Work Check

Scan `project_state.md` for any task (`T-XXX`) or change request (`CR-XXX`) that overlaps
with the current request. Overlap means the same file, module, or service is already listed
as `🏗️ ACTIVE`.

- If overlap exists: list the conflicting task ID and its current status. Ask the user whether
  to merge the new request into the existing task or treat it as a new task. Do not proceed
  until answered.
- If no overlap: write `- No duplicate tasks found.`

### Step 4: Write the Synthesis Block

Append the following block as a fenced section in your response (do **not** write it to any
file — it is a working-memory summary for the current session only):

```
## Context Synthesis
**Intent:** [copy the INTENT line from intent_classification verbatim]
**Project state file:** [exists | missing]
**Project context file:** [exists | missing]

### Affected Scope
[bullets from Step 1]

### Dependency / Constraint Flags
[bullets from Step 2]

### Duplicate Work Check
[bullets from Step 3]

### Ready to proceed
[Yes — continue to routing action from intent_classification]
[No — blocked by: [reason]. Waiting for user confirmation.]
```

If the project context file is missing and the intent is **New Project**, write:
```
Project context file not found — this is a fresh project.
@techLead will create .github/shared/project_context.md during INIT_PROJECT.
```
and mark **Ready to proceed: Yes**.

## OUTPUT CONTRACT

After writing the Synthesis Block, write exactly:
```
CONTEXT_SYNTHESIS: COMPLETE
```

This is an intra-agent signal — it does not cross a LangGraph node boundary. It advances
@techLead's internal skill sequence to `.github/skills/techLead/ambiguity_resolution.md`,
which validates that the specification is detailed enough to delegate before any action proceeds.

If the block is blocked (duplicate work conflict or constraint violation awaiting user
confirmation), write instead:
```
CONTEXT_SYNTHESIS: BLOCKED — [one-sentence reason]
```

LangGraph holds the graph at the @techLead node on `CONTEXT_SYNTHESIS: BLOCKED` and waits
for the next user message before re-evaluating. Do not activate `ambiguity_resolution.md`
while blocked.
