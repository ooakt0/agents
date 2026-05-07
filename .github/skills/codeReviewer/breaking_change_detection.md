# Skill: Breaking Change Detection

## ROLE & ACTIVATION
You are **@codeReviewer** scanning for breaking changes. Activate this skill SECOND in your
review chain — immediately after `architectural_alignment_audit` passes.
Protect every consumer — internal services, external API clients, mobile apps — from accidental
regressions before a single line merges.

## INPUTS
Before starting, read:
- All files written or modified by @codeCrafter in the current task
- `CHANGELOG.md` or `package.json` version field (to check for deliberate version bumps)
- `.github/shared/architecture_log.md` — any ADR that approved a breaking change with a migration plan
- `.github/shared/project_context.md` — known consumers (services, clients, mobile apps)

## PROCESS

### Step 1: Exported TypeScript Interface / Type Changes
Diff every exported `interface`, `type`, `enum`, and `class` signature against the prior version
(use `git diff HEAD~1` context or the last committed state):

Flag any of the following as BREAKING:
- Removing a property from an exported interface
- Changing a property type (e.g., `string` → `number`, optional → required)
- Renaming an exported symbol
- Removing an exported function or narrowing its parameter types
- Adding a required parameter to an existing exported function

```
[BREAKING] interface `OrderPayload` — removed property `discountCode?: string`
CONSUMERS AT RISK: OrderService, CheckoutLambda
FIX OPTIONS:
  1. Keep property as deprecated optional: `discountCode?: string // @deprecated use promotionCode`
  2. Bump major version and provide migration guide
  3. Add a Legacy Bridge per ADR-XXX
```

### Step 2: REST API Payload / Response Shape Changes
For every modified API handler or route:
- Compare request body schema: removed fields, type changes, new required fields → BREAKING
- Compare response shape: removed fields, renamed fields, type narrowing → BREAKING
- Compare HTTP status codes: changed success code (200→202) or error code semantics → BREAKING
- Check for removed endpoints (any route deletion is BREAKING unless version-scoped)

```
[BREAKING] GET /orders/:id — response removed `estimatedDelivery` field
CONSUMERS AT RISK: mobile app v2.x, partner webhook listeners
FIX: Add field back as nullable or version the endpoint as /v2/orders/:id
```

### Step 3: Database Schema Changes
For every migration file or schema change:
- Column removal or rename → BREAKING (existing queries will fail)
- NOT NULL constraint added to existing column without default or backfill → BREAKING
- Foreign key constraint added without pre-existing data validation → BREAKING
- Index removal on a column used in known queries → PERFORMANCE BREAKING

```
[BREAKING] Migration 0042 — drops column `users.legacy_id`
CONSUMERS AT RISK: ReportingService reads this column directly
FIX: Coordinate with ReportingService migration or add a deprecation window
```

### Step 4: Event / Message Contract Changes
For every SQS/SNS/EventBridge message schema:
- Removed or renamed fields in the message body → BREAKING for all consumers
- Changed event type string (e.g., `order.created` → `order.placed`) → BREAKING
- Changed envelope structure (e.g., added mandatory wrapper) → BREAKING

```
[BREAKING] SQS message `order.created` — field `customerId` renamed to `userId`
CONSUMERS AT RISK: InventoryLambda, FulfillmentService
FIX: Emit both field names during transition period, per Strangler Fig pattern
```

### Step 5: Version Bump Verification
If any BREAKING changes are found, check whether a corresponding version bump exists:
- `package.json` major version incremented: ACCEPTABLE (breaking change was intentional)
- No version bump: FAIL — intentional or accidental breaking change with no signaling

If an ADR exists that explicitly approved the breaking change with a migration plan, mark as
APPROVED-BREAKING and note the ADR number. Approved breaking changes still require the version bump.

## OUTPUT CONTRACT

**If any unapproved BREAKING findings exist (FAIL):**
1. List every breaking change with: location, consumers at risk, fix options
2. Do NOT proceed to `security_surface_analysis`
3. Write:
   `Breaking change detection FAILED. Returning to @codeCrafter with [N] breaking changes. Do not proceed until fixed.`

**If only APPROVED-BREAKING findings (version-bumped or ADR-covered):**
1. List them with their ADR reference for the record
2. Write: `Breaking change detection passed (approved breaking changes noted).`
3. Immediately activate the `security_surface_analysis` skill

**If no breaking changes (PASS):**
1. Write: `Breaking change detection passed.`
2. Immediately activate the `security_surface_analysis` skill — do not wait for user input
