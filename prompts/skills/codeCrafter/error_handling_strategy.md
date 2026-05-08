# Skill: Error Handling Strategy

## ROLE & ACTIVATION
You are **@codeCrafter** building the error handling layer. Activate after `implement_logic` and
before `ui_component_generator` (if applicable) or `resilience_patterns`. Business logic is written
first; then errors are standardised so every failure in the system is consistent, debuggable, and
safe to surface to callers.

## INPUTS
Before starting, read:
- All implementation files produced by `implement_logic` for this task
- `src/contracts/[feature-name].contracts.ts` — `StandardErrorResponse` definition
- `.github/shared/standards.md` — error handling and logging rules
- `.github/shared/architecture_log.md` — observability ADR (log schema, alarm thresholds)

## PROCESS

### Step 1: Audit Existing Error Usage in the Implementation
Scan every file produced by `implement_logic`:

| Anti-Pattern Found | Required Fix |
|-------------------|-------------|
| `catch (e) { console.log(e) }` | Re-throw as typed domain error with context |
| `catch (e) { return null }` | Throw `ResourceNotFoundError` or `OperationFailedError` |
| `throw new Error('something went wrong')` | Replace with specific domain error class |
| HTTP status code hardcoded in handler | Move to centralised error-to-status mapper |
| Error message exposes stack trace or internal path | Sanitise — safe message only in response |

### Step 2: Build the Domain Error Hierarchy
Create `src/errors/[domain]-errors.ts` with a typed hierarchy:

```typescript
// Base class — all domain errors extend this
export abstract class DomainError extends Error {
  abstract readonly errorCode: string;
  abstract readonly httpStatus: number;

  constructor(
    message: string,
    public readonly cause?: unknown,
  ) {
    super(message);
    this.name = this.constructor.name;
  }

  toJSON(): Record<string, unknown> {
    return {
      errorCode: this.errorCode,
      message: this.message,
      name: this.name,
    };
  }
}

// 4xx — caller is responsible
export class ValidationError extends DomainError {
  readonly errorCode = 'INVALID_REQUEST';
  readonly httpStatus = 400;
}

export class UnauthorizedError extends DomainError {
  readonly errorCode = 'UNAUTHORIZED';
  readonly httpStatus = 401;
}

export class ForbiddenError extends DomainError {
  readonly errorCode = 'FORBIDDEN';
  readonly httpStatus = 403;
}

export class ResourceNotFoundError extends DomainError {
  readonly errorCode: string;
  readonly httpStatus = 404;
  constructor(resource: string, id: string) {
    super(`${resource} not found: ***-${id.slice(-4)}`);
    this.errorCode = `${resource.toUpperCase().replace(' ', '_')}_NOT_FOUND`;
  }
}

export class ConflictError extends DomainError {
  readonly errorCode = 'IDEMPOTENCY_CONFLICT';
  readonly httpStatus = 409;
}

// 5xx — system is responsible
export class UpstreamError extends DomainError {
  readonly errorCode = 'UPSTREAM_UNAVAILABLE';
  readonly httpStatus = 502;
}

export class InternalError extends DomainError {
  readonly errorCode = 'INTERNAL_ERROR';
  readonly httpStatus = 500;
}
```

Rules:
- All domain error classes live in `src/errors/` — never inline in handler files
- `errorCode` is `SCREAMING_SNAKE_CASE` and matches the contract's `StandardErrorResponse`
- `message` is safe for external consumption — no stack traces, no internal paths, no SQL
- `cause` holds the original error for internal logging only — never serialised to response

### Step 3: Build the Centralised Error Handler
Create `src/middleware/errorHandler.ts` (or equivalent for the framework):

```typescript
import { StandardErrorResponse } from '../contracts/[feature-name].contracts';
import { DomainError, InternalError } from '../errors/[domain]-errors';

export function toErrorResponse(
  error: unknown,
  traceId: string,
  requestId: string,
): { status: number; body: StandardErrorResponse } {
  const domainError = error instanceof DomainError
    ? error
    : new InternalError('An unexpected error occurred', error);

  // Log with cause for internal debugging — never expose cause in response
  console.error(JSON.stringify({
    level: 'ERROR',
    message: domainError.message,
    errorCode: domainError.errorCode,
    traceId,
    requestId,
    cause: domainError.cause instanceof Error
      ? { name: domainError.cause.name, message: domainError.cause.message }
      : String(domainError.cause),
  }));

  return {
    status: domainError.httpStatus,
    body: {
      errorCode: domainError.errorCode,
      message: domainError.message,
      traceId,
      requestId,
    },
  };
}
```

### Step 4: Wire the Handler to Every Entry Point
In every Lambda handler or API route, wrap the core logic:

```typescript
export const handler = async (event: APIGatewayProxyEvent): Promise<APIGatewayProxyResult> => {
  const traceId = event.headers['X-Amzn-Trace-Id'] ?? 'unknown';
  const requestId = event.requestContext.requestId;

  try {
    const result = await coreBusinessLogic(event);
    return { statusCode: 200, body: JSON.stringify(result) };
  } catch (error) {
    const { status, body } = toErrorResponse(error, traceId, requestId);
    return { statusCode: status, body: JSON.stringify(body) };
  }
};
```

No handler may have its own `catch` logic beyond calling `toErrorResponse`.

### Step 5: Verify Error Coverage
For each function in the implementation, confirm:

| Check | PASS Condition | Verdict |
|-------|---------------|---------|
| All `catch` blocks typed | No bare `catch (e)` without typed re-throw | PASS / FAIL |
| AWS SDK errors wrapped | `ServiceException` caught and rethrown as `UpstreamError` | PASS / FAIL |
| No error message leaks internal state | Stack trace / SQL / file paths absent from `message` | PASS / FAIL |
| All handlers use `toErrorResponse` | No handler has bespoke error serialisation | PASS / FAIL |
| Error logged with `traceId` | Every error log includes the X-Ray trace ID | PASS / FAIL |

## OUTPUT CONTRACT

1. Write `src/errors/[domain]-errors.ts` with the full domain error hierarchy
2. Write `src/middleware/errorHandler.ts` with `toErrorResponse`
3. Update all handler files in-place to use the central error handler
4. Update `.github/shared/project_state.md` — note error handling layer complete for this task
5. Write this exact phrase to chain to the next skill:
   `Error handling strategy complete. Activating ui_component_generator.`
   (If no UI is involved, write instead: `Error handling strategy complete. Activating resilience_patterns.`)
