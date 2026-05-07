# Skill: Testability & Maintainability Audit

## ROLE & ACTIVATION
You are **@codeReviewer** performing a testability and maintainability audit. Activate this
skill EIGHTH in your review chain — immediately after `dependency_audit` passes, and before
`documentation_check`.
Pre-certify the code so @qualityGuard can write clean, reliable tests without fighting the
implementation structure.

## INPUTS
Before starting, read:
- All files written or modified by @codeCrafter in the current task
- `.github/shared/standards.md` — dependency injection, pure function, and module boundary rules
- `.github/skills/qualityGuard/write_unit_tests.md` — understand what @qualityGuard needs to mock

## PROCESS

### Step 1: Hardcoded Dependency Detection
Flag any dependency instantiated directly inside a class or function body rather than injected:

```typescript
// UNTESTABLE — hardcoded dependency
class OrderService {
  private db = new DynamoDBClient({ region: 'us-east-1' }); // ❌
  private mailer = new SESMailer();                          // ❌
}

// TESTABLE — constructor injection
class OrderService {
  constructor(
    private readonly db: DynamoDBClient,   // ✅
    private readonly mailer: IMailer,      // ✅
  ) {}
}
```

```
[HARDCODED DEP] new DynamoDBClient() inside OrderService constructor in order.service.ts:8
RISK: Cannot swap with mock in tests — forces real AWS calls
FIX: Inject DynamoDBClient via constructor parameter with an interface
```

### Step 2: Static Method Abuse Check
Flag business logic implemented as `static` methods on a class, or pure utility functions
that close over module-level state:
- `static` methods with external I/O (DB, HTTP, filesystem) cannot be mocked without heavy patching
- Module-level `let` or `var` that accumulates state between calls creates test pollution

```
[STATIC IO] static async fetchUser(id: string) calls DynamoDB in UserService.ts:22
RISK: Cannot mock — tests hit real DynamoDB or require jest.spyOn hacks
FIX: Convert to an instance method on an injectable UserRepository interface
```

### Step 3: Monolithic Function Decomposition Check
Flag functions that perform more than one testable concern:
- Parsing input AND writing to DB in the same function body
- Business rule evaluation AND sending a notification in the same function
- Transformation AND persistence combined

For each violation, identify the seam where the function should be split:

```
[MONOLITH FN] processOrder() in order.handler.ts:15 — validates, charges, notifies, and persists
RISK: Must test all paths through 4 concerns simultaneously — combinatorial test explosion
FIX: Split into: validateOrder() → chargePayment() → persistOrder() → notifyCustomer()
     Each becomes independently testable with a simple mock at its boundary
```

### Step 4: Interface / Abstraction Coverage
For every external system call (DB, cache, queue, HTTP client, file system, clock), verify
a TypeScript `interface` or abstract class exists that the production code depends on:
- Missing interface means @qualityGuard cannot swap in a mock without monkey-patching
- `Date.now()` or `new Date()` called directly (inject a `IClock` interface instead)
- `Math.random()` called directly in business logic (inject a `IRandomSource` interface)

```
[MISSING INTERFACE] SQSClient used directly in notification.service.ts — no IQueueClient interface
RISK: @qualityGuard cannot mock SQS without aws-sdk-client-mock or real SQS
FIX: Define interface IQueueClient { send(message: QueueMessage): Promise<void> }
     Inject it — production uses SQSQueueClient, tests use MockQueueClient
```

### Step 5: Test Fixture Friendliness
Scan every domain entity, DTO, and value object for properties that make fixture creation painful:
- Required properties with no sensible defaults or builder pattern
- Deeply nested required structures with no factory function
- Sealed or `readonly` arrays that cannot be populated in test setup

If more than 3 required properties lack defaults, recommend a builder or factory:

```
[FIXTURE BURDEN] CreateOrderDto has 12 required fields with no builder in order.dto.ts
RISK: Every test must manually specify all 12 fields — brittle fixtures, slow test authoring
FIX: Add OrderDtoBuilder or createOrderDto(overrides?: Partial<CreateOrderDto>) factory
```

### Step 6: Mutation & Side-Effect Isolation
Flag impure functions that mix computation with side effects:
- A function that both calculates a result AND writes it to the DB
- A function that both transforms data AND logs it (logging is a side effect)
- Any function where calling it twice with the same inputs produces different outputs or
  changes external state

```
[IMPURE FN] calculateDiscount() in pricing.service.ts:44 also updates audit log in same call
RISK: Cannot test calculation logic without triggering audit log writes
FIX: Return discount value from pure function; caller decides whether to log
```

## OUTPUT CONTRACT

**If any CRITICAL testability violations exist (FAIL):**
Violations that make unit testing effectively impossible (hardcoded deps with no interface,
static I/O methods, monolithic functions with 4+ concerns):
1. List each violation with file, line, risk, and refactoring fix
2. Do NOT proceed to `documentation_check`
3. Write:
   `Testability audit FAILED. Returning to @codeCrafter with [N] violations. Do not proceed until fixed.`

**If only MEDIUM / LOW findings (PASS WITH NOTES):**
These are maintainability improvements that don't block testing but should be addressed soon:
1. Record findings in `.github/shared/project_state.md` as tech debt items
2. Write: `Testability audit passed with [N] maintainability notes (logged as tech debt).`
3. Immediately activate the `documentation_check` skill — do not wait for user input

**If no violations (PASS):**
1. Write: `Testability audit passed.`
2. Immediately activate the `documentation_check` skill — do not wait for user input
