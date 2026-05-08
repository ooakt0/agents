# Skill: API Contract Design

## ROLE & ACTIVATION
You are **@codeCrafter** defining the API contract before any implementation begins. Activate this
skill FIRST — before `add_dependencies`, before `implement_logic`. No logic is written until the
contract is locked. The contract is the shared source of truth between frontend and backend and
between services.

## INPUTS
Before starting, read:
- The handoff from @techLead (task ID, objective, services involved)
- `.github/shared/project_context.md` — existing endpoints, data models, integration boundaries
- `.github/shared/architecture_log.md` — ADRs describing the domain model and service boundaries
- `.github/shared/standards.md` §2 — naming conventions for fields and endpoints

## PROCESS

### Step 1: Define Endpoints (REST) or Operations (GraphQL / Events)

For each operation in scope, specify:

**REST:**
```
METHOD /resource/{id}/sub-resource
Request body: { field: type, field: type }
Response 200: { field: type, field: type }
Response 4xx: StandardErrorResponse (see Step 3)
Response 5xx: StandardErrorResponse
```

**Event / Message:**
```
Event name: [domain].[entity].[past-tense-verb]   (e.g., orders.payment.captured)
Producer: [service name]
Consumer(s): [service name(s)]
Payload: { field: type, field: type }
Idempotency key field: [field name]
```

**Rules:**
- Resource names are plural nouns: `/orders`, `/accounts`, `/payments`
- No verbs in REST paths — use HTTP methods for intent
- Event names follow `[domain].[entity].[verb]` — dot-separated, lowercase, past tense
- No internal database field names exposed (no `pk`, `sk`, `createdAt` from DynamoDB key schema)

### Step 2: Define TypeScript Interfaces (Source of Truth)
Write all request/response shapes as exported TypeScript interfaces in a shared contracts file.
Do not generate code yet — write interfaces only:

```typescript
// contracts/[feature-name].contracts.ts

export interface CreateOrderRequest {
  customerId: string;        // UUID
  items: OrderLineItem[];
  idempotencyKey: string;    // UUID — caller must supply
}

export interface OrderLineItem {
  productId: string;
  quantity: number;          // positive integer, 1–999
  unitPriceCents: number;    // positive integer
}

export interface CreateOrderResponse {
  orderId: string;           // UUID
  status: OrderStatus;
  createdAt: string;         // ISO-8601
  totalCents: number;
}

export type OrderStatus = 'PENDING' | 'CONFIRMED' | 'FAILED';
```

Rules:
- All monetary values in integer cents — never floating point
- All timestamps as ISO-8601 strings — never Unix epoch integers
- All IDs as `string` (UUID) — never number or composite
- Status fields as string union types — never raw string
- Arrays and optional fields must be explicitly typed: `items?: OrderLineItem[]`

### Step 3: Define the Standard Error Response
Every error across all endpoints must return this exact shape:

```typescript
export interface StandardErrorResponse {
  errorCode: string;    // SCREAMING_SNAKE_CASE — machine-readable (e.g., ORDER_NOT_FOUND)
  message: string;      // human-readable, safe to display
  traceId: string;      // X-Ray trace ID for cross-referencing logs
  requestId: string;    // API Gateway request ID
}
```

Map HTTP status codes:
| Scenario | Status | `errorCode` example |
|----------|--------|-------------------|
| Caller input invalid | 400 | `INVALID_REQUEST` |
| Auth token missing/expired | 401 | `UNAUTHORIZED` |
| Caller lacks permission | 403 | `FORBIDDEN` |
| Resource not found | 404 | `ORDER_NOT_FOUND` |
| Idempotency key conflict | 409 | `IDEMPOTENCY_CONFLICT` |
| Unhandled internal error | 500 | `INTERNAL_ERROR` |
| Downstream unavailable | 502 | `UPSTREAM_UNAVAILABLE` |

### Step 4: Validate Against Project Context
Check every interface field against `project_context.md`:
- No field exposes an internal implementation detail (database key names, internal service IDs)
- All required fields are actually available from the data sources listed in `project_context.md`
- No breaking change to an existing contract without a version bump (`/v2/orders`)

| Check | PASS Condition | Verdict |
|-------|---------------|---------|
| No internal DB fields exposed | PK/SK, GSI names absent from response | PASS / FAIL |
| All fields sourced from known data | Every field traceable to a data store in project_context | PASS / FAIL |
| No breaking change to existing contract | Additive only, or new version path | PASS / FAIL |
| Monetary values in cents (integer) | No `float` or `decimal` in money fields | PASS / FAIL |
| Error shape consistent | StandardErrorResponse used for all errors | PASS / FAIL |

## OUTPUT CONTRACT

1. Write the contract file to `src/contracts/[feature-name].contracts.ts` (or the equivalent
   path for the project's language/framework as defined in `project_context.md`)
2. Append a contract summary as a comment in `.github/shared/architecture_log.md` under the
   relevant ADR, or create: `## ADR-[NNN]: API Contract — [Task Name]`
3. If **any FAIL verdict** in Step 4:
   - Do not proceed to `add_dependencies`
   - Describe the contract violation and ask @techLead to resolve it
4. If all checks pass:
   - Write this exact phrase to chain to the next skill:
     `API contract defined. Activating add_dependencies.`
