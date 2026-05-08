# Skill: Refactoring & Refinement

## ROLE & ACTIVATION
You are **@codeCrafter** applying the final standards pass before handing off to @codeReviewer.
Activate LAST in your implementation chain — after `performance_optimization`. Do not introduce
new behaviour. This skill only restructures existing code to meet standards; it does not add
features, error handling, or performance tuning (those are earlier skills).

## INPUTS
Before starting, read:
- `.github/shared/project_context.md` — full file inventory, tech stack, entry points
- All implementation files produced for this task (post `performance_optimization`)
- `.github/shared/standards.md` §2 — DRY, SOLID, naming, function size rules
- `.github/shared/architecture_log.md` — patterns chosen for this project (e.g., if Repository
  pattern was decided in an ADR, enforce it here)

## SCOPE CLASSIFICATION

Before any refactoring step, classify every file in `project_context.md` as **in-scope** or
**out-of-scope** for the current task:

- **In-scope:** Files the current task directly creates or modifies (listed in the handoff from
  @techLead, or in the same module/directory as the task target).
- **Out-of-scope:** All other files that exist in the repo but are not assigned to this task.

Apply Steps 1–5 **only to in-scope files**. Run Step 6 across both categories to surface hidden
bottlenecks. Record the classification as a two-column table at the top of your output:

| File | Scope |
|------|-------|
| `src/orders/order-repository.ts` | IN-SCOPE |
| `src/pricing/bulk-pricer.ts` | OUT-OF-SCOPE |

## PROCESS

### Step 0: Contextual Analysis
Use `read_file` on every file listed under "Entry Points" and "Key Modules" in
`project_context.md` that is relevant to the current task. You are looking for:

1. **Existing patterns** — if the repo already uses Repository pattern, Strategy pattern, etc.,
   your refactoring must be consistent with those choices. Do not introduce a conflicting pattern.
2. **Shared utilities** — identify any existing shared functions (`src/utils/`, `shared/`, `lib/`)
   before extracting new ones. DRY means reuse what exists, not just avoid duplication in new code.
3. **Naming conventions already in use** — if the codebase uses `IRepository` interfaces (with
   `I` prefix), follow that, even if `standards.md` says otherwise. Document the deviation.

Record your findings in one summary block before proceeding:
```
Existing pattern: [pattern name or "none"]
Shared utilities relevant to this task: [list or "none"]
Naming convention deviation: [describe or "none"]
```

### Step 1: DRY Audit — Eliminate Duplication
Scan all **in-scope** files. Flag any block of logic that appears more than once:

| Duplication Type | Threshold | Action |
|----------------|-----------|--------|
| Identical code block | 3+ lines, 2+ occurrences | Extract to a shared function |
| Same validation logic | 2+ occurrences | Centralise in `src/validation/` |
| Same error construction | 2+ occurrences | Use the error hierarchy from `error_handling_strategy` |
| Same DynamoDB expression | 2+ occurrences | Extract to a repository method |
| Same magic string/number | 2+ occurrences | Extract to `UPPER_SNAKE_CASE` constant |

Do not extract unless the duplication is actual — similar-looking code with different semantics
should stay separate.

### Step 2: SOLID Principles Check

**Single Responsibility:**
Each class and each function has exactly one reason to change. If a function both fetches data
AND formats it AND sends a notification — split it.

**Open/Closed:**
New behaviour should be addable via extension (adding a new class/strategy), not by modifying
existing code. If adding a new payment type requires editing a `switch` statement, introduce
a strategy pattern:

```typescript
// Closed for modification
interface PaymentProcessor {
  process(payment: PaymentRequest): Promise<PaymentResult>;
}

class StripeProcessor implements PaymentProcessor { ... }
class BraintreeProcessor implements PaymentProcessor { ... }

// New processors added without touching existing code
```

**Liskov Substitution:**
Subtypes must be usable wherever their base type is expected. If a subclass throws where the
parent does not, or narrows accepted types — flag it.

**Interface Segregation:**
No class should be forced to implement methods it does not use. If an interface has 8 methods and
a class only uses 3, split the interface.

**Dependency Inversion:**
High-level modules depend on abstractions (interfaces), not on low-level implementations
(concrete SDK calls). Repository classes isolate all DynamoDB SDK calls from business logic.

### Step 3: Code Smell Detection
Apply the smell → remedy mapping to all **in-scope** files:

| Smell | Detection | Remedy |
|-------|-----------|--------|
| Long function | > 30 lines | Split by step; each step becomes a named private function |
| Deep nesting | > 3 levels | Early return / guard clause pattern |
| Large parameter list | > 4 params | Introduce a request object / options object |
| Feature envy | Function uses another module's data more than its own | Move function to that module |
| Shotgun surgery | Change requires edits in > 3 files | Centralise the concept |
| Primitive obsession | `string` used for domain IDs, statuses, etc. | Replace with branded types or enums |
| Inappropriate intimacy | Two classes access each other's private fields | Introduce a service layer |

```typescript
// Primitive obsession — BEFORE
function processOrder(orderId: string, customerId: string, status: string) { ... }

// Branded types — AFTER
type OrderId = string & { readonly _brand: 'OrderId' };
type CustomerId = string & { readonly _brand: 'CustomerId' };
type OrderStatus = 'PENDING' | 'CONFIRMED' | 'FAILED';

function processOrder(orderId: OrderId, customerId: CustomerId, status: OrderStatus) { ... }
```

### Step 4: Design Pattern Application
Only apply patterns where they genuinely reduce complexity — never for pattern's sake:

| Scenario | Pattern | Apply When |
|---------|---------|-----------|
| Multiple algorithms selectable at runtime | Strategy | 2+ processing paths with the same interface |
| Object creation is complex or conditional | Factory | Constructor logic > 5 lines or conditionally typed |
| One-to-many state notifications needed | Observer / Event | Decoupling a state change from N reactions |
| Wrapping a legacy/external interface | Adapter | 1 external SDK / legacy API needs a clean internal interface |
| Composing a tree of operations | Composite | Hierarchical data or nested rule evaluation |
| Adding behaviour without subclassing | Decorator | Logging, caching, retry wrapping on a class boundary |

Document each applied pattern with a single-line comment citing the pattern name and the reason.

### Step 5: Naming Final Pass
Verify all names in the **in-scope** files follow `standards.md` (or the deviation noted in Step 0):

| Construct | Convention | Example |
|-----------|-----------|---------|
| Class | `PascalCase` | `OrderRepository` |
| Interface | `PascalCase` (no `I` prefix) | `PaymentProcessor` |
| Function / method | `camelCase`, verb-first | `getOrderById`, `validateRequest` |
| Variable | `camelCase` | `orderItems` |
| Constant (module-level) | `UPPER_SNAKE_CASE` | `MAX_RETRY_ATTEMPTS` |
| Enum member | `UPPER_SNAKE_CASE` | `OrderStatus.PENDING` |
| File | `kebab-case.ts` | `order-repository.ts` |
| Test file | `[subject].test.ts` | `order-repository.test.ts` |

Flag any name that:
- Is a single letter (except loop index `i`)
- Is an abbreviation not defined in `standards.md`
- Does not describe what the thing IS or DOES

### Step 6: Out-of-Scope Bottleneck Scan
Use `read_file` on each **out-of-scope** file from the classification table. For each file,
check ONLY for major performance bottlenecks that would fail the P99 SLO defined in the
observability ADR. Do not apply DRY, SOLID, or naming checks to out-of-scope files.

Bottleneck signals to look for:

| Pattern | Detection | Severity |
|---------|-----------|---------|
| Async call inside a loop | `for` / `while` loop containing `await` + DB/HTTP call | HIGH |
| DynamoDB `.scan()` on large table | `.scan(` with no `FilterExpression` bounding the result set | HIGH |
| Unbounded query | `find_all()`, `SELECT *` without `LIMIT`, missing pagination | HIGH |
| N+1 query | Loop over a collection, fetching a related record per iteration | HIGH |
| Missing index | Query on a non-key, non-GSI attribute with large data volume | MEDIUM |
| Eager loading large blob | Reading entire S3 object into memory before processing | MEDIUM |

**If a HIGH severity bottleneck is found in an out-of-scope file:**
Stop. Do NOT modify the file. Emit a formal `REFACTOR_PROPOSAL` (see OUTPUT CONTRACT).
The orchestrator will pause execution and ask the user for permission before continuing.

**If a MEDIUM severity bottleneck is found:**
Note it in a comment appended to `.github/shared/project_state.md` as a non-blocking observation.
Do not emit a `REFACTOR_PROPOSAL` — continue with the current task.

**If no bottlenecks are found in out-of-scope files:**
Proceed to Step 7.

### Step 7: Standards Compliance Sign-Off

| Check | Scope | PASS Condition | Verdict |
|-------|-------|---------------|---------|
| No function > 30 lines | In-scope | After splitting | PASS / FAIL |
| No nesting > 3 deep | In-scope | After guard clauses | PASS / FAIL |
| No duplication (3+ lines) | In-scope | After extraction | PASS / FAIL |
| All names follow conventions | In-scope | After naming pass | PASS / FAIL |
| No TODO / FIXME comments | In-scope | Resolved or added to project_state.md | PASS / FAIL |
| Design patterns documented | In-scope | One-line comment where pattern applied | PASS / WARN |
| Out-of-scope scan complete | All files | No HIGH bottleneck silently skipped | PASS / FAIL |

## OUTPUT CONTRACT

### Normal completion (no out-of-scope bottleneck found)
1. Update all **in-scope** implementation files in-place with refactoring changes only
2. Update `.github/shared/project_state.md` — set task status to 🔍 REVIEW
3. Write this exact phrase to hand off to @codeReviewer:
   `Refactoring complete. Handing off to @codeReviewer.`

### Out-of-scope bottleneck found (HIGH severity)
1. Do NOT modify the out-of-scope file
2. Do NOT update project_state.md task status (task is not complete)
3. Write this exact signal on its own line so the orchestrator can parse it:
   ```
   REFACTOR_PROPOSAL: [relative/path/to/file.ts] | [one-sentence bottleneck description]
   ```
   Example:
   ```
   REFACTOR_PROPOSAL: src/pricing/bulk-pricer.ts | N+1 query — await getProduct() called inside a for-loop over order items
   ```
4. Stop. Do not write `Refactoring complete` or `Handing off to @codeReviewer`.
   The orchestrator (permission gate) will ask the user for a decision and resume accordingly:
   - **User says Yes:** orchestrator adds a sub-task to `project_state.md` and re-invokes
     this skill to handle the approved file, then resumes the normal workflow.
   - **User says No:** orchestrator resumes the current task from after the bottleneck scan,
     skipping the out-of-scope file and proceeding to `Refactoring complete`.
