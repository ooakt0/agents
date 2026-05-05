# Skill: Dependency Audit

## ROLE & ACTIVATION
You are **@codeReviewer** auditing project dependencies. Activate this skill THIRD in your
review chain � after naming_audit passes. Check for CVE vulnerabilities, stale packages,
and license drift.

## INPUTS
Before starting, read:
- `package.json` (and `package-lock.json` or `yarn.lock` if present)
- `.github/shared/standards.md` �3 � security and quality requirements
- The output of the naming_audit step

## PROCESS

### Step 1: Run CVE Scan
Run `npm audit --json` (or equivalent) and parse the output:
- **Critical / High severity**: FAIL � workflow blocked until resolved
- **Moderate severity**: WARN � must be fixed before deployment, not a blocker today
- **Low severity**: INFO � log and continue

For each Critical/High finding, output:
```
[CVE] FAIL: package@version � CVE-XXXX-XXXXX � [description]
FIX: npm install package@[safe-version]
```

### Step 2: Check for Stale Packages
Run `npm outdated` (or equivalent). Flag any package that is:
- **More than 2 major versions behind**: WARN � schedule upgrade
- **More than 6 months behind latest patch**: INFO � note in audit

For each flagged package:
```
[STALE] WARN: package@current � latest: @latest � [months] months behind
```

### Step 3: License Drift Audit
For every direct dependency, check the SPDX license identifier:
- **Allowed**: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC
- **Requires legal review**: LGPL-2.0, LGPL-3.0, MPL-2.0
- **FAIL � blocked**: GPL-2.0, GPL-3.0, AGPL-3.0 (copyleft incompatible with proprietary use)

```
[LICENSE] FAIL: package@version � GPL-3.0 � copyleft, incompatible with project license
[LICENSE] WARN: package@version � LGPL-3.0 � requires legal review
```

### Step 4: Verify Exact Version Pinning
Per `.github/shared/standards.md` and `codeCrafter/add_dependencies.md` rules:
- All dependencies in `package.json` must use exact versions (no `^` or `~`)
- Flag any `^` or `~` prefix in `dependencies` or `devDependencies`

```
[PINNING] WARN: package � uses "^1.2.3", should be "1.2.3"
```

### Step 5: Check for Unused Dependencies
List any package in `dependencies` (not `devDependencies`) that is not imported in any
source file. These inflate the Lambda bundle size unnecessarily.

```
[UNUSED] INFO: package � declared in dependencies but no import found in src/
```

## OUTPUT CONTRACT

**If any FAIL findings exist:**
- Do NOT continue to documentation_check
- Return to @codeCrafter with the exact list of CVE and license FIX commands
- Write: `Dependency audit FAILED. Returning to @codeCrafter.`

**If only WARN/INFO findings:**
1. Write all findings as a comment block in `.github/shared/project_state.md` under the task
2. Write this exact phrase to signal completion and trigger the next skill:
   `Dependency audit passed. Activating documentation_check.`
