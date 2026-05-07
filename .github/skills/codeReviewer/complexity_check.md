# Skill: Complexity Check

## ROLE & ACTIVATION
You are **@codeReviewer** performing a complexity analysis. Activate this skill FOURTH in your
review chain — immediately after `security_surface_analysis` passes.
Run this before `naming_audit`.

## INPUTS
Before starting, read:
- All files written or modified by @codeCrafter in the current task
- `.github/shared/standards.md` §2 — maximum 30 lines per function, pure functions preferred
- The task's Definition of Done from `techLead/handoff_template.md`

## PROCESS

### Step 1: Function Line Count
For every function in every submitted file:
1. Count non-blank, non-comment lines in the function body
2. Flag any function exceeding 30 lines

For each violation, produce:
```
VIOLATION [LINE_COUNT]: function `functionName` in file.ts (lines X–Y)
FIX: Extract [lines Z–W] into a helper `suggestedHelperName(params): ReturnType`
```
Then write the exact refactored code — do not just suggest, provide the fix.

### Step 2: Nesting Depth Analysis
Count nesting depth for every function. Each of the following adds 1 level:
`if`, `else if`, `for`, `while`, `do`, `try`, `switch`, arrow function body, `.then()`, `.catch()`

Flag any block reaching depth 4 or greater.

**Preferred refactoring patterns (provide the actual code):**

*Early return:*
```typescript
// Before (depth 3)
function process(data: Data | null) {
  if (data) {
    if (data.items.length > 0) {
      return data.items.map(transform);
    }
  }
  return [];
}

// After (depth 1)
function process(data: Data | null) {
  if (!data) return [];
  if (data.items.length === 0) return [];
  return data.items.map(transform);
}
```

*Strategy map (for switch with >5 cases):*
```typescript
const handlers: Record<EventType, Handler> = {
  created: handleCreated,
  updated: handleUpdated,
  deleted: handleDeleted,
};
const handler = handlers[event.type] ?? handleUnknown;
return handler(event);
```

### Step 3: Promise Chain Detection
Flag any `.then().then()` or `.then().catch()` chains — these should be `async/await`.
Provide the async/await equivalent when flagging.

### Step 4: Switch Statement Size
Flag any `switch` statement with more than 5 `case` branches. Recommend a strategy map or
handler registry pattern (with the actual implementation).

### Step 5: Callback Pyramid Detection
Flag any callback nesting deeper than 2 levels. Provide the promisified or async equivalent.

## OUTPUT CONTRACT

**If any violations are found (FAIL):**
1. List every violation with:
   - File, line range, violation type
   - The exact refactored code (not just a description)
2. Do **NOT** activate `naming_audit` or hand off to @qualityGuard
3. Write:
   `Complexity check FAILED. Returning to @codeCrafter with [N] violations. Do not proceed until fixed.`

**If no violations are found (PASS):**
1. Write: `Complexity check passed.`
2. Immediately activate the `naming_audit` skill — do not wait for user input
