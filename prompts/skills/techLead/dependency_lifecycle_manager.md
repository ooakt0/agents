# Skill: Dependency Lifecycle Manager

## ROLE & ACTIVATION
You are **@techLead** protecting the project from version rot, licence drift, and supply
chain vulnerabilities. A dependency that ships clean today can become a critical CVE in six
months — this skill ensures that every library entering or staying in the project is known,
justified, and pinned.

Activate in two distinct scenarios:

**Scenario A — Post-dependency addition:** After @codeCrafter completes `add_dependencies`
and before `implement_logic` begins. Triggered by the phrase
`Dependency audit passed` in @codeCrafter's output.

**Scenario B — CVE triage:** When @qualityGuard's `dependency_audit` or `penetration_scan`
output contains a CVE reference (e.g., `CVE-XXXX-XXXXX`). @techLead must decide on the
remediation strategy before work can continue.

## INPUTS

**Scenario A:**
1. `.github/shared/project_context.md` — **READ FIRST** — `## Tech Stack` is the canonical
   approved dependency list; `## Integration Boundaries` defines which AWS services and
   external APIs are authorised. All duplicate-functionality and alignment checks in Steps
   2–3 are cross-referenced against this file.
2. `.github/shared/standards.md §2` — exact version pin rules
3. `package.json`, `pom.xml`, `requirements.txt`, or `go.mod` — whichever applies to the stack

**Scenario B (in addition to Scenario A inputs):**
4. @qualityGuard's full vulnerability report (current session)
5. The CVE advisory (CVSS score, affected versions, fix version if available)

## PROCESS

### Step 1: Version Pinning Audit

Scan every newly added or modified dependency entry. A dependency **fails** this check if it
uses any of the following version specifiers:

| Ecosystem | Failing specifiers |
|---|---|
| Node.js (`package.json`) | `^`, `~`, `*`, `latest`, `>`, `>=`, version ranges |
| Java (`pom.xml`) | `LATEST`, `RELEASE`, `[1.0,)`, open-ended ranges |
| Python (`requirements.txt` / `pyproject.toml`) | `>=` without an upper bound `<`, `~=` without a patch ceiling |
| Go (`go.mod`) | `latest` pseudo-version; dependencies not in `go.sum` |

For each failing entry, write:
```
❌ UNPIN: [package name] [current spec] → must be changed to [exact version, e.g., "1.4.2"]
```

Do not proceed to Step 2 until all ❌ UNPIN items are resolved.

### Step 2: Duplicate Functionality Check

Scan the newly added packages against `project_context.md → ## Tech Stack`. Flag any
addition that provides capability already covered by an existing dependency:

```
⚠️ DUPLICATE: [new package] duplicates [existing package] — use existing or justify replacement
```

If the new package is a justified replacement (security, performance, licence), write:
```
✅ REPLACEMENT JUSTIFIED: [new package] replaces [old package] — [one-sentence reason]
```
and add a task to remove the old package before this CR is closed.

### Step 3: Tech Stack Alignment

Confirm that every new dependency is reflected in `project_context.md → ## Tech Stack`.
If any are missing, @techLead updates the file directly (not @codeCrafter's responsibility).

Also confirm the dependency's licence is compatible with the project's licence posture as
defined in `standards.md`. Flag GPL, AGPL, or SSPL licences as:
```
⚠️ LICENCE RISK: [package] uses [licence] — requires legal sign-off before merging
```

### Step 4: CVE Triage (Scenario B only — skip if no CVE found)

For each CVE in @qualityGuard's report, assign a remediation strategy using this decision
table:

| Condition | Remediation strategy |
|---|---|
| CVSS ≥ 9.0 (Critical) | **Immediate patch** — block all other work; @codeCrafter updates to fixed version in this PR |
| CVSS 7.0–8.9 (High), direct dependency | **Patch this sprint** — create a CR-XXX task, assign to @codeCrafter, set 🏗️ ACTIVE |
| CVSS 7.0–8.9 (High), transitive dependency | **Strategic refactor** — assess if the parent dependency has a fixed version; if not, evaluate replacement; @architect consulted if a new service boundary is needed |
| CVSS 4.0–6.9 (Medium) | **Scheduled update** — document in `project_state.md` as a T-XXX maintenance task with priority Low |
| CVSS < 4.0 (Low) | **Monitor** — log in `architecture_log.md` under a "Known Risks" section; no immediate action |

For each CVE, write the triage decision:
```
CVE-XXXX-XXXXX | [package] | CVSS [score] | Strategy: [Immediate patch / Patch this sprint / Strategic refactor / Scheduled update / Monitor]
Rationale: [one sentence]
```

## OUTPUT CONTRACT

If all version pins are exact, no duplicate functionality conflicts are unresolved, all
new dependencies are in `project_context.md`, and no Critical/High CVEs are unpatched:
```
DEPENDENCY_STATUS: SECURE
```

If any ❌ UNPIN items remain unresolved or a Critical CVE has no patch plan:
```
DEPENDENCY_STATUS: VULNERABLE — [one-sentence description of the blocking issue]
```

`DEPENDENCY_STATUS: VULNERABLE` blocks the workflow. @codeCrafter must resolve all
blocking issues before this skill is re-run.

`DEPENDENCY_STATUS: SECURE` is an intra-agent signal. In Scenario A it allows @codeCrafter
to proceed to `implement_logic`. In Scenario B it allows @techLead to continue the audit
or delegation sequence.
