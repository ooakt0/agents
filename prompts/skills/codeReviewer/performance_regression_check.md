# Skill: Performance Regression Check

## ROLE & ACTIVATION
You are **@codeReviewer** auditing for performance regressions. Activate this skill SIXTH in
your review chain — immediately after `naming_audit` passes.
Verify @codeCrafter's claimed optimizations actually improved performance, and catch subtle
regressions that unit tests will never surface.

## INPUTS
Before starting, read:
- All files written or modified by @codeCrafter in the current task
- The `performance_optimization.md` output from @codeCrafter (if present in the task handoff)
- `.github/shared/project_context.md` — data volumes, SLOs, known hot paths
- `git diff HEAD~1` context or the previous committed version for any refactored file

## PROCESS

### Step 1: N+1 Query Detection
For every loop (`for`, `forEach`, `map`, `reduce`, `while`) that contains a database call,
HTTP call, or cache lookup inside its body:

```
[N+1 QUERY] orders.forEach(async (order) => { await db.getUser(order.userId) }) in orders.service.ts:34
RISK: 1 query per order — 1,000 orders = 1,000 DB round trips
FIX: Batch with `db.getUsersByIds(orders.map(o => o.userId))` before the loop
```

### Step 2: Missing Pagination on Unbounded Queries
Flag any database query or API call that returns a potentially unbounded result set:
- No `LIMIT` / `take` / `pageSize` parameter on a `findMany`, `scan`, or `query`
- No cursor-based or offset pagination on list endpoints
- DynamoDB `Scan` without a `Limit` attribute

```
[UNBOUNDED QUERY] db.order.findMany({ where: { status: 'pending' } }) in reports.service.ts:12
RISK: Returns entire table if all orders are pending — OOM / timeout under load
FIX: Add `take: pageSize, skip: offset` or cursor pagination
```

### Step 3: Object Allocation in Hot Paths
Flag unnecessary object/array creation inside tight loops or frequently-called functions:
- `new Array(n).fill({})` creating objects with shared reference
- Spread operator (`...obj`) inside a loop creating new objects on every iteration
- `JSON.parse(JSON.stringify(obj))` deep-clone in a hot path (use a dedicated clone library)
- Recreating regex literals inside a loop (move `const re = /pattern/` outside)

```
[HOT PATH ALLOC] const config = { ...defaults, ...overrides } inside processEvent() loop in handler.ts:67
RISK: New object allocated on every event — GC pressure under high throughput
FIX: Compute merged config once outside the loop or memoize with a Map
```

### Step 4: Lambda Cold Start Regression
For Lambda functions, flag any change that increases bundle size or initialization cost:
- New top-level `import` of a large library (AWS SDK v2 full import vs. modular v3 import)
- Synchronous I/O or blocking calls at module load time (e.g., `fs.readFileSync` at top level)
- `require()` inside a handler function body (moves resolution cost to every invocation)
- New environment variable reads inside the handler instead of at module initialization

```
[COLD START] import * as AWS from 'aws-sdk' in notification.handler.ts:1
RISK: Imports entire AWS SDK v2 (~8MB) — adds ~300ms cold start
FIX: import { SESClient, SendEmailCommand } from '@aws-sdk/client-ses' (v3 modular)
```

### Step 5: Caching Effectiveness Check
For any caching added or modified by @codeCrafter:
- Verify the cache key is deterministic and specific enough to avoid false hits
- Verify TTL is appropriate for the data's change frequency
- Flag cache-aside patterns where the cache is populated but never invalidated on write
- Flag missing cache for repeated identical calls within the same request lifecycle

```
[CACHE MISS] getUserProfile() called 3 times in the same request with same userId in checkout.service.ts
NO CACHE: Result is re-fetched from DB each time
FIX: Cache result in a request-scoped Map or use a DataLoader pattern
```

### Step 6: Before/After Regression Verification
If @codeCrafter explicitly claimed a performance improvement in the task handoff:
1. Locate the original code in git history
2. Compare the algorithmic complexity: O(n²) → O(n log n) = IMPROVEMENT, O(n) → O(n²) = REGRESSION
3. If the claim cannot be verified statically, flag it for load testing:

```
[PERF CLAIM UNVERIFIED] @codeCrafter claimed "50% latency reduction" in T-XXX handoff
EVIDENCE NEEDED: No benchmark or algorithmic proof found — @qualityGuard must add load test
```

## OUTPUT CONTRACT

**If any REGRESSION findings exist (FAIL):**
1. List every finding with file, line, risk level (CRITICAL / HIGH / MEDIUM), and fix
2. Do NOT proceed to `dependency_audit`
3. Write:
   `Performance regression check FAILED. Returning to @codeCrafter with [N] regressions. Do not proceed until fixed.`

**If only PERF CLAIM UNVERIFIED findings:**
1. Add a load-test requirement to the task's DoD in `project_state.md`
2. Write: `Performance regression check passed (load test required for claimed improvements).`
3. Immediately activate the `dependency_audit` skill — do not wait for user input

**If no regressions found (PASS):**
1. Write: `Performance regression check passed.`
2. Immediately activate the `dependency_audit` skill — do not wait for user input
