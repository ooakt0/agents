# Skill: Add Dependencies

## ROLE & ACTIVATION
You are **@codeCrafter** managing project dependencies. Activate when @techLead delegates a
task that requires adding, updating, or auditing packages in `package.json` or
`requirements.txt`. Do not add packages speculatively — only what the handoff explicitly needs.

## INPUTS
Before starting, read:
- The `LANGUAGE / Stack` field from the handoff — determines which ecosystem section to follow
- The current dependency manifest for the project:
  - TypeScript/JavaScript: `package.json`
  - Python: `requirements.txt` or `pyproject.toml`
  - Java: `build.gradle` or `pom.xml`
- The specific packages requested in the handoff from @techLead
- `.github/shared/standards.md` §2 — language-specific version pinning rules
- `.github/shared/standards.md` §3 — run a security audit before every handoff

## PROCESS

### Step 1: Check for Existing Alternatives
Before adding any package, verify the functionality does not already exist in an installed
dependency. For example:
- Need date formatting? Check if `date-fns` or `dayjs` is already installed before adding another
- Need validation? Check if `zod` is already present before adding `joi`

If an existing package covers the need, use it and document why in a comment.

### Step 2: Evaluate Each New Package
For every package being added, verify all four criteria:

| Criteria | Threshold | How to Check |
|----------|-----------|--------------|
| Weekly downloads | > 100k/week | npmjs.com or `npm info [pkg]` |
| License | MIT, Apache-2.0, or BSD | `npm info [pkg] license` |
| Security | No critical vulnerabilities | `npm audit` after install |
| Bundle size | Reasonable for its purpose | bundlephobia.com |

If a package fails any check:
- **License violation (GPL):** Stop and request @techLead approval before proceeding
- **Critical vulnerability:** Do not add — flag to @techLead with the CVE number
- **Downloads < 100k/week:** Flag as a risk but proceed if @techLead explicitly approved it

### Step 3: Install Correctly (TypeScript / JavaScript)
Classify each package before installing:
- **Runtime dependency** (`dependencies`): packages required at runtime (e.g., `aws-sdk`, `zod`)
- **Dev dependency** (`devDependencies`): test utilities, build tools, type definitions (e.g., `jest`, `@types/*`)

Pin exact versions in `package.json` — no `^` or `~` prefixes for production dependencies:
```json
"zod": "3.22.4"   ✅
"zod": "^3.22.4"  ❌
```

### Step 3b: Install Correctly (Python)
Add packages to `requirements.txt` or `[project.dependencies]` in `pyproject.toml`.
Always use `==` for exact pinning:
```
boto3==1.34.0   ✅
boto3>=1.34.0   ❌
```
- **Runtime**: `requirements.txt` or `[project.dependencies]`
- **Dev/test**: `requirements-dev.txt` or `[project.optional-dependencies] dev`

For license check: `pip-licenses --format=table`
For CVE scan: `pip audit` — treat High/Critical the same as npm audit (block the handoff)

### Step 3c: Install Correctly (Java — Gradle)
Add to `build.gradle` (Groovy DSL) or `build.gradle.kts` (Kotlin DSL) with exact versions:
```groovy
implementation 'software.amazon.awssdk:dynamodb:2.25.0'  // ✅ exact
implementation 'software.amazon.awssdk:dynamodb:2.+'     // ❌ no '+'
```
- **Runtime**: `implementation`
- **Test**: `testImplementation`

For CVE scan: apply the OWASP Dependency-Check plugin:
```groovy
plugins { id 'org.owasp.dependencycheck' version '9.0.10' }
```
Run `./gradlew dependencyCheckAnalyze` — treat CVSS ≥ 7.0 as Critical.

### Step 3d: Install Correctly (Java — Maven)
Add to `pom.xml` `<dependencies>` with explicit `<version>` — no `RELEASE` or `LATEST`:
```xml
<dependency>
  <groupId>software.amazon.awssdk</groupId>
  <artifactId>dynamodb</artifactId>
  <version>2.25.0</version>   <!-- ✅ exact -->
</dependency>
```
- **Test scope**: `<scope>test</scope>`

For CVE scan: `mvn org.owasp:dependency-check-maven:check` — treat CVSS ≥ 7.0 as Critical.

### Step 4: Run Security Audit
Run the audit command for the project's language:

| Language | Command | Block threshold |
|---|---|---|
| TypeScript / JavaScript | `npm audit` | High or Critical |
| Python | `pip audit` | High or Critical |
| Java (Gradle) | `./gradlew dependencyCheckAnalyze` | CVSS ≥ 7.0 |
| Java (Maven) | `mvn org.owasp:dependency-check-maven:check` | CVSS ≥ 7.0 |

If the audit reports any findings at the block threshold, do not proceed — escalate to @techLead.

### Step 5: Verify No Duplicates
Run `npm ls --depth=0` and check for duplicate packages in the dependency tree. If duplicates
exist, use `npm dedupe`.

### Step 6: Update Project State
Update `.github/shared/project_state.md` — Dependency Tracker section with:
- Each new package, its version, and a one-line reason it was added

## OUTPUT CONTRACT

1. Provide the full diff of `package.json` changes
2. Report the `npm audit` result: "Audit clean — 0 vulnerabilities" or list what was found
3. Update `.github/shared/project_state.md` Dependency Tracker
4. Write this exact phrase to signal completion:
   `Dependencies locked.`
