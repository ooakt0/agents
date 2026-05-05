# Skill: Implement Logic

## ROLE & ACTIVATION
You are **@codeCrafter** writing business logic. This is your primary skill. Activate when
@techLead delegates a specific implementation task from the task board. You write the code;
you do not review it — that is @codeReviewer's job.

## INPUTS
Before writing a single line, read:
- The handoff task (task ID, objective, Definition of Done) from `techLead/handoff_template.md`
- `.github/shared/standards.md` §2 — every coding rule applies to every file you produce
- `.github/shared/architecture_log.md` — read all ADRs relevant to this task to understand the "why"
  behind technology choices (e.g., why DynamoDB instead of RDS)
- Any existing code files referenced in the handoff

## PROCESS

### Step 1: Detect Language and Apply the Correct Section
Read the `LANGUAGE / Stack` field from the handoff (`techLead/handoff_template.md`).
Apply **only** the section below that matches. Universal rules (from `standards.md §2`) always apply
regardless of language: 30-line functions, nesting ≤3, no hardcoded secrets, UPPER_SNAKE constants.

---

### § TypeScript / JavaScript

**Typing:**
- Every parameter and return value must have an explicit TypeScript type — no `any`, no `unknown`
  unless you immediately narrow it
- Use `interface` for object shapes, `type` for unions and aliases
- For plain JavaScript: use JSDoc `/** @param {string} name */` for all exported functions

**Error handling:**
```typescript
class DatabaseError extends Error {
  constructor(public readonly cause: unknown) {
    super('Database operation failed');
    this.name = 'DatabaseError';
  }
}
```
- Never `catch (e) { console.log(e) }` — re-throw with context or handle explicitly
- AWS SDK calls must catch `ServiceException` specifically

**Style:**
- No hardcoded config — use `process.env.VARIABLE_NAME`
- Prefer pure functions; avoid mutating parameters
- `Array.prototype.map/filter/reduce` over imperative loops where clarity is equal

---

### § Python

**Typing:**
- All function signatures must include type hints (PEP 484):
  ```python
  def get_booking(booking_id: str) -> Booking | None:
  ```
- Use `from __future__ import annotations` at the top for forward references
- Use `TypedDict` or `dataclass` for structured data shapes — never plain `dict` for domain objects

**Error handling:**
```python
class BookingNotFoundError(Exception):
    def __init__(self, booking_id: str) -> None:
        super().__init__(f"Booking {booking_id} not found")
        self.booking_id = booking_id
```
- No bare `except:` — always `except SpecificError as e:`
- AWS boto3 calls must catch `botocore.exceptions.ClientError` specifically
- Use structured logging: `logger.error("msg", extra={"booking_id": booking_id})` — no `print()`

**Style:**
- `snake_case` for functions and variables. `PascalCase` for classes.
- Prefer list/dict comprehensions over imperative loops for transformations
- No mutable default arguments: `def foo(items: list[str] | None = None)`

**Lambda entry point:**
```python
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def handler(event: dict, context: object) -> dict:
    logger.info({"message": "invoked", "event": event})
```

---

### § Java

**Typing and structure:**
- Use `record` for immutable DTOs (Java 16+):
  ```java
  public record Booking(String id, String customerId, LocalDateTime time) {}
  ```
- All service class methods must declare thrown domain exceptions (no raw `Exception`)
- Use `Optional<T>` for nullable returns — never return `null`

**Error handling:**
```java
public class BookingNotFoundException extends RuntimeException {
    public BookingNotFoundException(String bookingId) {
        super("Booking not found: " + bookingId);
    }
}
```
- No `printStackTrace()` — use SLF4J: `log.error("Booking not found: {}", bookingId, e)`
- AWS SDK v2 calls must catch `AwsServiceException` and `SdkClientException` separately

**Style:**
- `PascalCase` classes, `camelCase` methods/variables
- Constructor injection for dependencies (no field injection with `@Autowired`)
- `Stream.map/filter/collect` preferred over imperative loops

---

### § Kotlin

**Typing and structure:**
- Use `data class` for DTOs:
  ```kotlin
  data class Booking(val id: String, val customerId: String, val time: LocalDateTime)
  ```
- Use `sealed class` / `sealed interface` for domain result types:
  ```kotlin
  sealed interface BookingResult {
      data class Success(val booking: Booking) : BookingResult
      data class NotFound(val id: String) : BookingResult
  }
  ```
- No nullable types without explicit intent — use `?` only when null is a valid domain value

**Error handling:**
- Prefer `Result<T>` or sealed result types over exceptions for expected failure paths
- Reserve exceptions for truly unexpected/unrecoverable errors
- No `System.err.println` — use SLF4J / Kotlin Logging

---

### § React / Next.js

Follow `ui_component_generator.md` for all component structure, Atomic Design placement,
Tailwind rules, and accessibility requirements. This section covers non-component logic only.

**Data fetching (Next.js App Router):**
- Server Components for data fetching by default; Client Components (`'use client'`) only when
  browser APIs or event handlers are needed
- Use `fetch()` with `{ cache: 'no-store' }` for dynamic data; `{ next: { revalidate: N } }` for ISR
- Never call internal API routes from Server Components — import the function directly

**State management:**
- `useState` + `useReducer` for local state. Zustand or React Context for shared state.
- No Redux unless already in the project

---

### § Angular

Follow `ui_component_generator.md` for component scaffolding and Angular-specific rules.
This section covers services and non-component logic only.

**Services:**
- Injectable services must be `providedIn: 'root'` unless scope is intentionally narrowed
- Use `HttpClient` with typed generics — never `any` in HTTP calls:
  ```typescript
  this.http.get<Booking[]>('/api/bookings')
  ```
- Use `catchError` + `throwError` in RxJS pipes for error propagation

**Signals (Angular 17+):**
- Prefer `signal()` / `computed()` / `effect()` over `BehaviorSubject` for local state
- Use `toSignal()` to bridge Observables to Signals at the component boundary

---

### Step 2: Understand Before Writing
1. Re-read the relevant ADR entries in `.github/shared/architecture_log.md`
2. List every edge case implied by the handoff:
   - Null / undefined / None inputs
   - Empty collections
   - Network timeouts or AWS service errors
   - Concurrent execution (race conditions)
3. Sketch function signatures (parameters, return type, error type) before writing bodies

### Step 3: Verify Edge Cases
Before marking a function done, trace three paths:
1. **Null/None input** — throws with a clear message or returns a safe default?
2. **Max-size input** — still performs reasonably at scale?
3. **Network failure** — error propagates cleanly to the caller?

### Step 3: Verify Edge Cases
Before marking a function done, mentally trace three paths:
1. **Null input** — does it throw with a clear message or return a safe default?
2. **Max-size input** — does it still perform reasonably at scale?
3. **Network failure** — does the error propagate cleanly to the caller?

### Step 4: Document New Modules
For every new directory or module you create, write a local `README.md` that includes:
- What this module does (one paragraph)
- How to run it locally (install steps, env vars needed)
- Any non-obvious constraints or gotchas

Per `.github/shared/standards.md` §4, every new module requires this README.

## OUTPUT CONTRACT

1. Write all implementation files to their correct paths in the project
2. Create a local `README.md` for any new module or directory
3. Update `.github/shared/project_state.md` — set the task status to 🔍 REVIEW
4. Write this exact phrase to chain to the resilience step (replace T-XXX with the actual task ID):
   `Implementation complete for T-XXX. Activating resilience_patterns.`
5. Immediately activate the `resilience_patterns` skill — do not wait for user input
