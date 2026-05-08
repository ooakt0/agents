# Skill: Documentation Check

## ROLE & ACTIVATION
You are **@codeReviewer** auditing documentation completeness. Activate this skill NINTH and
LAST in your review chain — after `testability_maintainability_audit` passes. This is the final
gate before handing off to @qualityGuard.

## INPUTS
Before starting, read:
- All files written or modified by @codeCrafter in the current task
- `.github/shared/standards.md` �4 � documentation and commit message requirements
- The handoff Definition of Done from `techLead/handoff_template.md`

## PROCESS

### Step 1: README Completeness
For every new directory or module created by @codeCrafter, verify a `README.md` exists with:
- [ ] **Purpose**: one paragraph explaining what this module does
- [ ] **Local setup**: install steps and required environment variables
- [ ] **Usage example**: at least one code snippet or curl example
- [ ] **Constraints**: any non-obvious limits or gotchas

For each missing section:
```
[README] FAIL: src/[module]/README.md � missing section: [section name]
```

### Step 2: .env.example Completeness
If new environment variables were introduced, verify `.env.example` exists at the project root
and includes every new variable with a placeholder value and inline comment:
```
# Description of what this variable does
NEW_VARIABLE_NAME=placeholder-value
```

Flag any variable present in code but absent from `.env.example`:
```
[ENV] FAIL: VARIABLE_NAME used in src/[file] but not documented in .env.example
```

### Step 3: TODO and FIXME Scan
Scan all submitted files for `TODO`, `FIXME`, `HACK`, `XXX`, or `NOTE:` comments.
These are not acceptable in deliverable code:
```
[TODO] FAIL: src/[file].ts line [N] � TODO comment must be resolved before handoff
```

### Step 4: JSDoc / TSDoc on Exported Symbols
For every exported function, class, or interface that is part of the public API of a module:
- Verify a JSDoc block comment exists with at minimum: `@param`, `@returns`
- Flag any exported symbol without documentation

```
[DOCS] WARN: export function functionName in src/[file].ts � missing JSDoc
```

### Step 5: Commit Message Convention
Per `.github/shared/standards.md` �4, commits must use Conventional Commits format:
`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`

If the handoff references any staged changes, verify the proposed commit message matches
this format. Flag violations:
```
[COMMIT] WARN: proposed message "update stuff" � must use Conventional Commits format
FIX: "feat: [T-XXX] add [description]"
```

### Step 6: No Dead Code
Scan for unreachable code, unused imports, and unused variables.
- TypeScript strict mode should catch most unused variables � verify `noUnusedLocals: true`
  is set in `tsconfig.json`
- Flag any `import` statement where the imported symbol is never referenced

```
[DEAD CODE] WARN: src/[file].ts line [N] � imported symbol 'X' is never used
```

## OUTPUT CONTRACT

**If any FAIL findings exist:**
- Do NOT hand off to @qualityGuard
- Return the full findings list to @codeCrafter
- Write: `Documentation check FAILED. Returning to @codeCrafter.`

**If only WARN/INFO findings (all FAILs resolved):**
1. Log all WARN findings in `.github/shared/project_state.md` under the task
2. Write this exact phrase to signal completion and trigger the next agent:
   `Documentation check complete. Handing off to @qualityGuard.`
