# 📦 Project Context
**Owner:** @techLead | **Last Updated:** [YYYY-MM-DD] | **Updated By:** [agent or user]

> **PURPOSE:** This file is the single source of project knowledge for all agents.
> Read this file FIRST — before scanning any project files or reading any other shared files.
> This eliminates token-burning reconnaissance on every agent activation.
>
> **@techLead:** Populate this at `INIT_PROJECT`. Update it at every major milestone.
> If this file does not exist in a real project, create it before issuing any `DELEGATE`.

---

## Project Overview
<!-- What is this project? Who uses it? What problem does it solve?
     Keep to 3-5 sentences. Agents use this to understand domain context. -->

- **Name:** [Project name]
- **Purpose:** [One-sentence purpose]
- **Description:** [2-4 sentences: what it does, who uses it, why it exists]
- **Stage:** [Greenfield | Active development | Maintenance | Legacy]

---

## Tech Stack
<!-- List every language, framework, runtime, and tooling decision.
     @codeCrafter reads this to select the right implement_logic.md section.
     @architect reads this to ensure CDK stacks match the runtime. -->

| Layer | Technology | Version | Notes |
|---|---|---|---|
| Language | [e.g. TypeScript / Python / Java] | [e.g. 5.x / 3.12 / 21] | [strict mode / PEP 484 / etc.] |
| Runtime | [e.g. Node.js / Lambda Python / Spring Boot] | [version] | |
| UI Framework | [e.g. React / Next.js / Angular / None] | [version] | |
| IaC | [e.g. AWS CDK v2 TypeScript] | [version] | |
| Test Framework | [e.g. Jest / pytest / JUnit 5] | [version] | |
| DB / Storage | [e.g. DynamoDB / RDS PostgreSQL / S3] | | |
| Other | [e.g. Artillery, LocalStack, pip-audit] | | |

---

## Directory Structure
<!-- Top-level dirs only. One line per entry. Agents use this to know where to put files.
     @codeCrafter uses this to place new modules. @codeReviewer uses it for doc checks. -->

```
[project-root]/
  [dir]/           ← [purpose, e.g. "Lambda handlers"]
  [dir]/           ← [purpose, e.g. "CDK infrastructure stacks"]
  [dir]/           ← [purpose, e.g. "Shared utilities and error classes"]
  [dir]/           ← [purpose, e.g. "Unit and integration tests"]
  [file]           ← [purpose, e.g. "Entry point / main stack"]
```

---

## Key Files & Entry Points
<!-- The files every agent should know by name, without searching.
     Include the path and one-line description.
     @devOps reads this to know which CDK stack to deploy.
     @codeCrafter reads this to know where to add new logic. -->

| File | Purpose |
|---|---|
| `[path/to/file]` | [e.g. Main Lambda handler — entry point for all API Gateway requests] |
| `[path/to/file]` | [e.g. CDK stack — defines all AWS resources for this service] |
| `[path/to/file]` | [e.g. Shared error classes — all custom exceptions live here] |
| `[path/to/file]` | [e.g. Environment variable schema — validated at startup with Zod/pydantic] |

---

## Environment & Config
<!-- List env var NAMES only — never values or secrets.
     @devOps uses this to configure pipeline secrets and parameter store paths.
     @codeCrafter uses this to know which process.env.X names are available. -->

| Variable | Used By | Purpose |
|---|---|---|
| `[VAR_NAME]` | [service or module] | [what it configures] |
| `[VAR_NAME]` | | |

- **Config source:** [e.g. AWS SSM Parameter Store / .env file / Secrets Manager]
- **Feature flags:** [list any feature flags, or "None"]

---

## Integration Boundaries
<!-- External systems this project talks to. Agents use this to understand blast radius
     for a change and to correctly mock dependencies in tests.
     @architect uses this when designing new resources. -->

| System | Type | Direction | Notes |
|---|---|---|---|
| [e.g. Stripe API] | [External API] | [Outbound] | [e.g. payments module only] |
| [e.g. DynamoDB bookings table] | [AWS service] | [Read/Write] | [e.g. table name in SSM] |
| [e.g. SQS booking-dlq] | [AWS service] | [Write on error] | [e.g. max receive count = 3] |
| [e.g. EventBridge bus] | [AWS service] | [Publish] | [e.g. booking-confirmed events] |

---

## Known Constraints
<!-- Tech debt, off-limits patterns, non-negotiable decisions, critical gotchas.
     @codeCrafter must read this before writing any code.
     @codeReviewer uses this as an additional check beyond standards.md. -->

- [e.g. Do NOT use DynamoDB scan — all reads must use GSI or table key]
- [e.g. The payments Lambda must stay under 128 MB memory — do not add heavy deps]
- [e.g. All public API endpoints require Cognito JWT auth — no unauthenticated routes]
- [e.g. Node.js runtime only on Lambda — no Python Lambdas in this project]

---

## Recent Changes
<!-- Rolling log of the last 5 major changes. @techLead appends after every milestone.
     @codeCrafter reads this to understand what recently changed context before implementing.
     Oldest entry is removed when a 6th is added (keep exactly 5). -->

| Date | Task / CR | Agent Chain | Files Touched | Summary |
|---|---|---|---|---|
| [YYYY-MM-DD] | [T-001 / CR-001] | [agents used] | [file list] | [one-line summary] |
