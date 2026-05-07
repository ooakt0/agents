# Multi-Agent Engineering Framework

A portable, AI-powered engineering team with two complementary layers:

1. **Prompt-driven agents** — structured personas for GitHub Copilot and Claude Code, coordinated through a shared state file and exact signal phrases.
2. **`seagenthub` MCP Server** — a FastMCP tool server that exposes the same 6-agent pipeline as a single callable tool, consumable from VS Code, Cursor, and Claude Code without any LLM API key.

Covers the full SDLC (design → implement → review → test → deploy) and all 6 pillars of the **AWS Well-Architected Framework**.

---

## Table of Contents

1. [What This Is](#what-this-is)
2. [Prerequisites](#prerequisites)
3. [seagenthub MCP Server](#seagenthub-mcp-server)
4. [Using in a New Project (Prompt Agent Layer)](#using-in-a-new-project-prompt-agent-layer)
5. [First Run: INIT_PROJECT](#first-run-init_project)
6. [Daily Usage](#daily-usage)
7. [Agent Reference](#agent-reference)
8. [Maintaining the Shared State Files](#maintaining-the-shared-state-files)
9. [Standards — What You Must Never Break](#standards--what-you-must-never-break)
10. [Adding a New Skill to an Existing Agent](#adding-a-new-skill-to-an-existing-agent)
11. [Adding a Brand New Agent](#adding-a-brand-new-agent)
12. [Troubleshooting](#troubleshooting)

---

## What This Is

Six AI agent personas, each with a defined role, a set of skill files, and strict handoff contracts. All six are orchestrated via a **deterministic LangGraph pipeline** inside the `seagenthub` MCP server — no LLM routing, no API key, no PowerShell hooks.

| Agent | Role | Activated By |
|---|---|---|
| `@techLead` | Orchestrator — decomposes goals, delegates, audits results | `@techLead`, `INIT_PROJECT`, `DELEGATE`, `AUDIT_RESULT`, `CHANGE_REQUEST` |
| `@architect` | Infrastructure designer — CDK, IAM, observability, cost | `DELEGATE [architect]` |
| `@codeCrafter` | Implementation — business logic, UI, resilience patterns | `DELEGATE [codeCrafter]`, `Cleared for implementation` |
| `@codeReviewer` | Quality gatekeeper — complexity, naming, CVEs, docs | `Handing off to @codeReviewer` (automatic) |
| `@qualityGuard` | Testing & security — unit/integration/load/pen testing | `Handing off to @qualityGuard` (automatic) |
| `@devOps` | Deployment — CI/CD, environment promotion, verification | `Handing off to @devOps` (automatic after `AUDIT_RESULT`) |

The **signal phrases** defined in each skill file's OUTPUT CONTRACT are the transition conditions LangGraph evaluates to advance between nodes. When used as prompt-driven agents inside an IDE (Copilot, Claude Code), the same phrases drive the conversational handoff — the contract is identical in both layers.

---

## Prerequisites

- **GitHub Copilot** (VS Code extension) or **Claude Code** (CLI) — the framework works with both
- **Python 3.10+** and the **FastMCP** library for the `seagenthub` MCP server (`pip install fastmcp langgraph langchain-core PyGithub`)
- AWS CDK v2 installed globally if you plan to use the infrastructure design skills (`npm i -g aws-cdk`)
- The project you're copying into must have a `.github/` directory (created automatically by Git)

---

## seagenthub MCP Server

`seagenthub` is a **stateless FastMCP tool server** that runs the 6-agent LangGraph pipeline on a GitHub repository. Each call is fully isolated — no state is shared between invocations.

### Architecture

```
seagenthub (FastMCP)
  └─▶ execute_software_pipeline(github_repo_url, task_description)
        └─▶ LangGraph StateGraph
              supervisor (deterministic)
                ├─▶ architect      — placeholder (extend with your IaC logic)
                ├─▶ codeCrafter    — git clone → apply changes → git commit → push
                ├─▶ codeReviewer   — placeholder (extend with your review logic)
                ├─▶ qualityGuard   — python -m pytest in cloned repo
                └─▶ devOps         — POST to DEPLOY_DASHBOARD_URL (if tests pass)
```

The supervisor is **deterministic** — no LLM required. It walks the fixed sequence `architect → codeCrafter → codeReviewer → qualityGuard → devOps` and marks each agent as complete in `AgentState.completed_agents`.

### Signal Phrase Contract

Signal phrases are the **transition conditions** LangGraph checks at each node boundary. They are defined in the `OUTPUT CONTRACT` section of every skill file and must be written verbatim — the graph will not advance if a phrase is paraphrased or missing.

| Phrase | LangGraph transition |
|---|---|
| `Cleared for implementation` | `architect` → `codeCrafter` |
| `Handing off to @codeReviewer` | `codeCrafter` → `codeReviewer` |
| `Handing off to @qualityGuard` | `codeReviewer` → `qualityGuard` |
| `Quality gate cleared` | `qualityGuard` → supervisor (triggers `devOps`) |
| `Returning to @techLead` | Any node → supervisor (review and re-route) |
| `SECURITY FAIL: [msg]` | **Terminates the graph** — no further nodes run |

Intra-agent phrases (e.g. `Observability design complete`, `Pipeline configured`) advance the skill sequence within a single node without crossing a node boundary.

### Key files

| File | Purpose |
|---|---|
| `orchestrator.py` | LangGraph graph definition — `AgentState`, supervisor, 5 worker nodes, `compiled_graph` |
| `main.py` | FastMCP server — exposes `execute_software_pipeline` tool |
| `.cursor/mcp.json` | Cursor project-level MCP config |
| `.github/agents/deploy_lead.agent.md` | VS Code Copilot custom agent backed by `seagenthub` |

### Installation

```bash
pip install fastmcp langgraph langchain-core PyGithub
```

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `GITHUB_TOKEN` | Optional | PAT for authenticated `git push` inside `codeCrafter` |
| `DEPLOY_DASHBOARD_URL` | Optional | POST endpoint called by `devOps` after tests pass |

No `OPENAI_API_KEY` is needed — the supervisor is fully deterministic.

### Running the server

```bash
# stdio transport — default, used by Claude Code and Cursor
python main.py

# SSE transport — for VS Code
python main.py --transport=sse
```

### IDE integration

**Claude Code:**
```bash
claude mcp add seagenthub -- python main.py
```

**Cursor:** `.cursor/mcp.json` is picked up automatically at project open.

**VS Code:** `.github/agents/deploy_lead.agent.md` is detected by GitHub Copilot from `.github/agents/`.

### The `execute_software_pipeline` tool

```python
execute_software_pipeline(
    github_repo_url: str,   # e.g. https://github.com/owner/repo
    task_description: str,  # e.g. "Add input validation to /checkout and deploy to staging"
) -> str                    # human-readable agent timeline + test/deploy status
```

Returns a formatted string:
```
AgentHub pipeline complete for https://github.com/owner/repo

[HumanMessage] Repository: ...  Task: ...
[architect]    [architect] Task processed.
[codeCrafter]  [codeCrafter] Clone ✓ | commit: True | push: pushed to origin
[codeReviewer] [codeReviewer] Task processed.
[qualityGuard] [qualityGuard] Tests PASSED.
[devOps]       [devOps] Deployment triggered. HTTP 200 — {"ok":true}

Tests passed : True
Agents run   : architect, codeCrafter, codeReviewer, qualityGuard, devOps
```

### AgentState fields

| Field | Type | Description |
|---|---|---|
| `messages` | `list[BaseMessage]` | Full conversation history |
| `next_node` | `str` | Agent name the supervisor selected next |
| `github_url` | `str` | Repo URL passed from the tool |
| `repo_path` | `str` | Absolute local path after `codeCrafter` clones the repo |
| `test_passed` | `bool` | Set by `qualityGuard`; gates `devOps` deployment |
| `task_description` | `str` | Human-readable goal forwarded from the MCP tool |
| `completed_agents` | `list[str]` | Agents that have already run this invocation |

---

## Using in a New Project (Prompt Agent Layer)

### Step 1 — Copy the framework

Copy these directories and files into your **project root**:

```
your-project/
  ├── .claude/
  │   └── skills/                 ← Claude Code skill descriptors (one per agent)
  ├── .cursor/
  │   └── mcp.json                ← Cursor MCP configuration for seagenthub
  ├── .github/
  │   ├── copilot-instructions.md ← GitHub Copilot agent routing
  │   ├── agents/                 ← Copilot agent persona files (incl. deploy_lead)
  │   ├── shared/                 ← State files (fill these in — see Step 2)
  │   └── skills/                 ← All agent skill instructions
  ├── orchestrator.py             ← LangGraph pipeline
  ├── main.py                     ← FastMCP seagenthub server
  └── CLAUDE.md                   ← Auto-loaded by Claude Code on every session
```

All internal paths are **relative to the project root** — nothing is hardcoded.

### Step 2 — Fill in the shared state files

Four files in `.github/shared/` need project-specific content before first use:

| File | What to fill in |
|---|---|
| `project_context.md` | Tech stack, directory structure, entry points, env vars — @techLead does this at `INIT_PROJECT` |
| `project_state.md` | Task board — @techLead populates this; the template has placeholder headings |
| `architecture_log.md` | Leave empty — @architect fills in ADRs during the design phase |
| `standards.md` | **Do not change** — this is the engineering law. Extend it only if your project has extra conventions |

### Step 3 — Start your first session

Trigger the agent chain with:

```
@techLead INIT_PROJECT: [describe your project]
```

---

## First Run: INIT_PROJECT

Always start a new project — or a new feature on an existing project — with:

```
@techLead INIT_PROJECT: [describe your goal in plain language]
```

@techLead will:
1. **Create or validate** `.github/shared/project_context.md` — fills in tech stack, directory structure, entry points, and known constraints from your description. **No agent will be delegated until this file exists.**
2. Break your goal into atomic tasks (`T-001`, `T-002`, ...) in `project_state.md`
3. Begin the agent chain by delegating to `@architect`

### For a change to an existing feature (not a new project):

```
@techLead CHANGE_REQUEST: [describe the change in plain language]
```

Or just describe the change directly — @techLead detects plain-language change descriptions automatically and activates the change analysis workflow instead of creating a new project.

---

## Daily Usage

### Start a new task

```
@techLead INIT_PROJECT: Build a booking cancellation Lambda that marks DynamoDB records as cancelled and publishes a BookingCancelled event to EventBridge
```

### Request a change to an existing feature

```
@techLead the cancel booking endpoint is returning a 200 when the booking doesn't exist, it should return a 404
```

### Manually delegate to a specific agent

```
@techLead DELEGATE [architect]: design the EventBridge rule and DLQ for the cancellation flow
```

### Audit quality results and proceed to deployment

```
@techLead AUDIT_RESULT
```

### The automatic chain

Once you trigger the first delegation, the LangGraph pipeline advances through each node automatically, driven by signal phrases in each agent's OUTPUT CONTRACT:

```
INIT_PROJECT → @architect → @codeCrafter → @codeReviewer → @qualityGuard → AUDIT_RESULT → @devOps → done
```

When running via the `seagenthub` MCP tool, the server executes this sequence end-to-end and returns a formatted timeline. When working through prompt-driven agents in an IDE, you direct the session — the same signal phrases tell the AI which agent to activate next.

You only need to intervene at two points regardless of layer:
- **After @architect:** review and approve the ADRs before writing `Cleared for implementation`
- **After @qualityGuard:** run `AUDIT_RESULT` to verify the quality gate and trigger @devOps

---

## Agent Reference

### @techLead

The only agent you talk to directly. Everyone else is triggered automatically.

**Commands:**
| Command | When to use |
|---|---|
| `INIT_PROJECT: [description]` | Starting a new project or a major new feature |
| `CHANGE_REQUEST: [description]` | Changing or fixing something in an existing feature |
| `DELEGATE [agentName]: [task]` | Manually sending work to a specific agent |
| `AUDIT_RESULT` | After @qualityGuard finishes — triggers @devOps if everything passes |

**@techLead reads before every response:**
1. `.github/shared/project_context.md` — project memory (creates it if missing)
2. `.github/shared/project_state.md` — task board
3. `.github/shared/standards.md` — engineering standards

### @architect

Runs five design skills in strict order: `observability_design` → `reliability_design` → `generate_cdk_boilerplate` → `security_group_audit` → `cost_estimation`.

Never writes code. Produces ADRs in `architecture_log.md`. Signals `Cleared for implementation` when the security audit passes.

### @codeCrafter

Reads the handoff template and selects the correct language section from `implement_logic.md` based on the `Language / Stack` field.

Supported languages: **TypeScript, JavaScript, Python, Java, Kotlin, React, Next.js, Angular**.

Skill order: `add_dependencies` → `implement_logic` → `ui_component_generator` (UI tasks only) → `resilience_patterns` (always last).

### @codeReviewer

Runs automatically on `Handing off to @codeReviewer`. Any single FAIL returns work to @codeCrafter immediately — the chain does not continue.

Skill order: `complexity_check` → `naming_audit` → `dependency_audit` → `documentation_check`.

### @qualityGuard

Runs automatically on `Handing off to @qualityGuard`. A `SECURITY FAIL:` from any skill blocks the entire workflow until @techLead resolves it.

Skill order: `write_unit_tests` → `mock_aws_responses` → `integration_test` → `load_test` → `penetration_scan`.

### @devOps

Runs automatically after `AUDIT_RESULT` passes. Never deploys to prod without a manual approval gate.

Skill order: `pipeline_setup` → `environment_promotion` → `deployment_verification`.

---

## Maintaining the Shared State Files

The `seagenthub` MCP server reads and writes the `.github/shared/` files directly during pipeline execution. This is how context is maintained across different AI sessions and IDEs — Cursor, Claude Code, and VS Code all connect to the same server and therefore read the same state files. Any agent, in any IDE, picks up where the last session left off.

### `project_context.md` — project memory

**Owner:** @techLead. The most important file — it saves every agent from scanning the entire codebase.

| Section | When to update |
|---|---|
| `## Tech Stack` | When a new language, framework, or tool is added (after ADR approval) |
| `## Directory Structure` | When a new top-level directory is created |
| `## Key Files & Entry Points` | When a new Lambda, service, or entry point is added |
| `## Environment & Config` | When a new env var or feature flag is added |
| `## Integration Boundaries` | When a new external API or AWS service is integrated |
| `## Known Constraints` | When a new off-limits pattern or tech debt note is agreed upon |
| `## Recent Changes` | After every `deployment_verification` PASS or `CHANGE_REQUEST` resolution (cap at 5 rows) |

**Never leave it stale.** If an agent reads incorrect project context, it will make wrong assumptions silently.

### `project_state.md` — task board

**Owner:** @techLead. Update after every agent handoff.

Task statuses: `🏗️ ACTIVE` → `🔍 REVIEW` → `✅ DONE`

### `architecture_log.md` — ADR ledger

**Owner:** @architect. Never delete an entry. ADRs are permanent records.

Format per entry: Title, Date, Status, Context, Decision, Consequences.

### `standards.md` — engineering law

**Owner:** @techLead. All agents defer to it.

Rules for changing it:
- Only extend it — never remove existing rules
- All changes must be discussed before editing (agents already have the rules in memory from past sessions)
- If you add a new language, add a naming sub-section to §2 following the same format as existing languages
- If you add a new test tool, add it to §3
- After any change, tell @techLead explicitly: `standards.md has been updated — re-read it before delegating`

---

## Standards — What You Must Never Break

These constraints are hard-wired into every agent's skill files. Breaking them causes FAIL signals and blocks the agent chain.

### Non-negotiable rules

| Rule | Enforced by | Breaks which agent |
|---|---|---|
| Functions ≤ 30 lines | `complexity_check.md` | @codeReviewer |
| Nesting ≤ 3 levels | `complexity_check.md` | @codeReviewer |
| No `any` in TypeScript | `naming_audit.md` + `implement_logic.md` | @codeReviewer, @codeCrafter |
| No hardcoded secrets | `penetration_scan.md` | @qualityGuard → `SECURITY FAIL:` |
| Exact version pins (no `^`, `~`, `+`) | `add_dependencies.md`, `dependency_audit.md` | @codeCrafter, @codeReviewer |
| ≥ 80% branch coverage | `write_unit_tests.md` | @qualityGuard |
| OIDC only in CI/CD (no long-lived AWS keys) | `pipeline_setup.md` | @devOps |
| No prod deploy without manual approval gate | `environment_promotion.md` | @devOps |
| `SECURITY FAIL:` blocks everything | Any agent's skill file | All agents |

### What @techLead checks at AUDIT_RESULT

Before writing `Handing off to @devOps`, @techLead cross-checks @qualityGuard's output against all five sections of `standards.md`:

- §1 AWS/IaC: CDK used, no Console-only changes, tagging present
- §2 Coding: naming, function size, no `any`, no hardcoded secrets
- §3 Testing: ≥80% coverage, no real AWS calls in unit tests
- §4 Documentation: README updated, `.env.example` present, no TODO/FIXME
- §5 UI/UX: Atomic Design hierarchy followed, ARIA present (if applicable)

---

## Adding a New Skill to an Existing Agent

A "skill" is a `.md` file in `.github/skills/[agentName]/`. When you add one, you need to update **5 places**. Follow this checklist:

### Step 1 — Create the skill file

Create `.github/skills/[agentName]/[skill_name].md`. Use this structure:

```markdown
# Skill: [Skill Name]

## ROLE & ACTIVATION
[Which agent runs this, and what triggers it]

## INPUTS
Before starting, read:
- [file 1] — [why]
- [file 2] — [why]

## PROCESS

### Step 1: [first action]
[instructions]

### Step 2: [second action]
[instructions]

## OUTPUT CONTRACT
[What this skill produces and what exact phrase it ends with]
Write exactly: `[Your exact signal phrase here]`
```

**Key rule:** The output contract must end with an exact phrase that either triggers the next skill or hands off to the next agent. Choose a phrase that does not appear anywhere else in the framework.

### Step 2 — Add to the agent's `.github/agents/[agentName].agent.md`

In the `## SKILL EXECUTION ORDER` section, add a new numbered entry for the skill. Specify the file path, what it does, and what phrase it ends with.

### Step 3 — Add to the agent's `.claude/skills/[agentName].SKILL.md`

In the skill execution table or COMMANDS section, add a row or bullet describing when to activate the skill.

### Step 4 — Add to `.github/copilot-instructions.md`

In the `## @[agentName]` section, add the skill to the "Run skills in this order" list with a one-line description.

### Step 5 — Add to `CLAUDE.md`

In the agent's sub-section under "Agent Skills Quick Reference", add a bullet for the new skill.

### Checklist summary

- [ ] `.github/skills/[agent]/[skill].md` — created with ROLE / INPUTS / PROCESS / OUTPUT CONTRACT
- [ ] `.github/agents/[agent].agent.md` — skill added to SKILL EXECUTION ORDER
- [ ] `.claude/skills/[agent].SKILL.md` — skill added to table or COMMANDS
- [ ] `.github/copilot-instructions.md` — skill added to agent's "Run skills in this order" list
- [ ] `CLAUDE.md` — skill added to Agent Skills Quick Reference

---

## Adding a Brand New Agent

Adding an agent requires all 5 skill steps above for each of its skills, plus these additional steps:

### Step 1 — Create the agent persona file

Create `.github/agents/[agentName].agent.md`:

```markdown
---
name: [agentName]
description: [One sentence for the agent directory in copilot-instructions.md]
tools: [read_file, write_file, terminal]
---

# [emoji] @[agentName] — [Role Title]

## ROLE & ACTIVATION
[What this agent does and what phrase activates it]

## BEFORE RESPONDING, READ
- `.github/shared/project_context.md` — **READ FIRST** — [what specifically to look for]
- [other required reads]

## SKILL EXECUTION ORDER
[numbered list of skills with file paths and signal phrases]

## RULES
[agent-specific constraints]
```

**Required:** `project_context.md` must always be the first item in `BEFORE RESPONDING, READ`.

### Step 2 — Create the Claude Code skill descriptor

Create `.claude/skills/[agentName].SKILL.md`:

```markdown
---
name: [agentName]
description: "[Activation description for Claude Code]"
applyTo: "**"
---

# @[agentName] Skill

## ACTIVATION
[Exact phrase or command that activates this agent]

## REQUIRED READS
[ordered list — project_context.md first]

## [COMMANDS or SKILL EXECUTION]
[skills or commands this agent runs]

## CONSTRAINTS
[hard rules]
```

### Step 3 — Create skill files

Create `.github/skills/[agentName]/` directory and add one `.md` file per skill (follow Step 1 of the skill checklist above for each).

### Step 4 — Add the routing section to `copilot-instructions.md`

Add a new `## @[agentName] — [Role Title]` section following the same format as existing agents:
- **Activate when:**
- **Before responding, read:** (project_context.md first)
- **Run skills in this order:**
- **Rules:**

### Step 5 — Register in the agent directory

Update all four of these locations:
- `.github/copilot-instructions.md` — add to `## Workflow Enforcement Rules` bullet on skipping, and to the agent directory table at the top if one exists in the instructions
- `.github/agents/techLead.agent.md` — add to `## AGENT DIRECTORY` section
- `.github/skills/techLead/system_prompt.md` — add to `## AGENT DIRECTORY`
- `CLAUDE.md` — add row to the Agent Directory table and a sub-section to Agent Skills Quick Reference

### New agent checklist summary

- [ ] `.github/agents/[agent].agent.md` — created (project_context.md as first read)
- [ ] `.claude/skills/[agent].SKILL.md` — created
- [ ] `.github/skills/[agent]/` — directory with all skill files created
- [ ] `.github/copilot-instructions.md` — agent section added
- [ ] `.github/agents/techLead.agent.md` — agent added to AGENT DIRECTORY
- [ ] `.github/skills/techLead/system_prompt.md` — agent added to AGENT DIRECTORY
- [ ] `CLAUDE.md` — agent added to table and Quick Reference

---

## Troubleshooting

### `SECURITY FAIL:` appeared and the workflow is blocked
This is intentional — the AI stops all work when a security violation is detected. To unblock:
1. Read the violation message after the colon
2. Fix the issue in the code (remove the secret, fix the OWASP vulnerability, etc.)
3. Tell @techLead what was fixed — it will re-run the affected quality check

### @techLead says "project_context.md does not exist" on an existing project
This file was added after the initial project setup. Create it by running:
```
@techLead INIT_PROJECT: [describe the existing project so @techLead can populate project_context.md]
```
@techLead will populate the file from your description without overwriting `project_state.md` or `architecture_log.md`.

### The agent chain is going in the wrong order
The chain order is enforced by signal phrases and the LangGraph node transition logic — agents can only proceed in the defined sequence. If the order is wrong, an agent wrote the wrong signal phrase. Check the skill file's OUTPUT CONTRACT section and compare it to the transition table in `orchestrator.py` and the [Signal Phrase Contract](#signal-phrase-contract) above.

### A skill file is empty or has placeholder content
All 21 skill files must contain real instructions to function. If you find a placeholder, write the skill content following the structure in [Adding a New Skill](#adding-a-new-skill-to-an-existing-agent). Reference the existing skill files as examples of the correct format.
