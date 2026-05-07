# Skill: Performance Optimization

## ROLE & ACTIVATION
You are **@codeCrafter** optimizing the implementation for production-grade performance. Activate
after `resilience_patterns` and before `refactoring_refinement`. Do not optimize speculatively —
only address patterns with a measurable impact at the scale described in `project_context.md`.

## INPUTS
Before starting, read:
- All implementation files produced for this task (post resilience_patterns)
- `.github/shared/architecture_log.md` — observability ADR (P99 SLO thresholds)
- `.github/shared/project_context.md` — expected data volumes, traffic patterns, concurrency limits
- `.github/shared/standards.md` — performance rules (pagination requirements, index mandates)

## PROCESS

### Step 1: Query Pattern Audit
For every database interaction in the implementation, verify:

| Check | PASS Condition | Verdict |
|-------|---------------|---------|
| DynamoDB: access pattern matches key schema | Query by PK (and SK if needed) — no full table scans | PASS / FAIL |
| DynamoDB: `FilterExpression` on non-indexed attr | Replace with GSI or restructure data model | FAIL |
| DynamoDB: `Scan` operation present | Replace with `Query` + correct key design | FAIL |
| RDS: `SELECT *` on large tables | Select only required columns | WARN |
| RDS: query lacks WHERE clause index | Add index or restructure query | FAIL |
| RDS: N+1 query pattern | Use JOIN or batch load — never query inside a loop | FAIL |

**N+1 detection rule:** If a loop contains an `await` to a database or external service, it is an
N+1 problem. Replace with a batch operation:

```typescript
// N+1 — FAIL
const orders = await getOrders(customerId);
const enriched = await Promise.all(
  orders.map(order => getProduct(order.productId))   // N calls inside loop
);

// Batch — PASS
const orders = await getOrders(customerId);
const productIds = orders.map(o => o.productId);
const products = await batchGetProducts(productIds); // 1 call (DynamoDB BatchGetItem)
const productMap = new Map(products.map(p => [p.id, p]));
const enriched = orders.map(o => ({ ...o, product: productMap.get(o.productId) }));
```

### Step 2: Pagination Enforcement
Any query that can return more than 100 items must be paginated. Never load unbounded collections
into Lambda memory.

```typescript
// Required pattern for all list operations
export interface PaginatedResponse<T> {
  items: T[];
  nextToken?: string;   // base64-encoded DynamoDB LastEvaluatedKey, or cursor
  totalCount?: number;  // only if an efficient COUNT is available — omit otherwise
}

// DynamoDB paginated query
const result = await client.send(new QueryCommand({
  TableName: TABLE_NAME,
  Limit: pageSize,                    // max 100, default 20
  ExclusiveStartKey: decodedNextToken,
}));
return {
  items: result.Items ?? [],
  nextToken: result.LastEvaluatedKey
    ? Buffer.from(JSON.stringify(result.LastEvaluatedKey)).toString('base64')
    : undefined,
};
```

### Step 3: Caching Strategy
For read-heavy operations, evaluate caching at the appropriate layer:

| Layer | Tool | Use When | TTL Guidance |
|-------|------|---------|-------------|
| Lambda in-memory | Module-level variable | Config/reference data that rarely changes | Process lifetime (~15 min) |
| ElastiCache (Redis) | `ioredis` / `@aws-sdk/client-elasticache` | Shared read-heavy data, session state | 5 min – 1 hour |
| API Gateway cache | Built-in caching | GET endpoints with stable responses | 1 min – 1 hour |
| CloudFront | CDN | Static or near-static API responses | Minutes to days |

For each cacheable operation, define:
- **Cache key:** must include all parameters that affect the result
- **Invalidation strategy:** event-driven (DynamoDB Streams) or TTL-only
- **Cache miss behavior:** fetch from source, populate cache, return result

Only add caching where `project_context.md` indicates the operation is on the hot path or the
P99 SLO in the observability ADR cannot be met without it.

### Step 4: Lambda Cold Start Mitigation
For Lambdas on latency-sensitive paths (P99 SLO < 500ms):

| Mitigation | When to Apply |
|-----------|--------------|
| Move SDK client initialisation outside handler | Always — never inside `handler()` |
| Use Provisioned Concurrency | If P99 SLO cannot be met with cold starts at expected traffic |
| Use Lambda SnapStart (Java) | If Java runtime is in use |
| Minimise bundle size | Keep individual Lambda bundle < 5 MB; use tree-shaking |
| Lazy-load optional dependencies | `require()` / `import()` inside the code path that needs it |

```typescript
// CORRECT — initialised once per container lifetime
const ddbClient = new DynamoDBDocumentClient(new DynamoDBClient({}));

export const handler = async (event: ...) => {
  // use ddbClient — no re-initialisation cost
};
```

### Step 5: Frontend Performance (if UI task)
Only apply if this task includes a frontend component:

| Check | Requirement |
|-------|------------|
| Images | `next/image` or equivalent lazy-loading component |
| List rendering | Virtualisation (`@tanstack/react-virtual`) for > 50 items |
| Bundle size | New dependency must not increase bundle by > 10 KB gzipped without justification |
| API calls on mount | Use `Suspense` + server components (Next.js) or skeleton loaders |
| Debounce user-triggered queries | Search/filter inputs debounced ≥ 300ms |

### Step 6: Performance Sign-Off

| Check | PASS Condition | Verdict |
|-------|---------------|---------|
| No N+1 queries | All loops with DB calls replaced with batch operations | PASS / FAIL |
| No unbounded queries | All list operations paginated | PASS / FAIL |
| No `Scan` in DynamoDB | Replaced with `Query` + correct keys | PASS / FAIL |
| SDK clients outside handler | No re-initialisation per invocation | PASS / FAIL |
| Caching applied on hot path | Or documented reason it is not needed | PASS / WARN |

## OUTPUT CONTRACT

1. Update all implementation files in-place with performance fixes
2. Document any caching decisions (cache key, TTL, invalidation) as a comment block in the
   relevant file — these are non-obvious constraints worth preserving
3. Update `.github/shared/project_state.md` — note performance optimization complete for this task
4. Write this exact phrase to chain to the final skill:
   `Performance optimization complete. Activating refactoring_refinement.`
