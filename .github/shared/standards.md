# Engineering Standards & Guidelines
**Owner:** @techLead | **Auditor:** @codeReviewer | **Last Reviewed:** 2026-05-07
**Status:** Authoritative — all agents defer to this file. Extend only; never remove rules.

> These are non-negotiable. Any violation produces a FAIL signal from the relevant agent and blocks the pipeline until fixed.

---

## §1 — AWS & Infrastructure (IaC)

### 1.1 Tooling
- **CDK v2 (TypeScript strict mode) is the only approved IaC tool.** No Terraform, no raw CloudFormation YAML authored by hand, no Console-only changes that are not later committed to a CDK stack.
- CDK synth must produce zero diff on a clean checkout (`cdk diff` returns empty before a PR merges).
- Every CDK construct must pass `cdk-nag AwsSolutionsChecks` with no suppressions unless a documented waiver exists in `architecture_log.md`.

### 1.2 IAM & Least Privilege
- IAM roles must use **resource-level ARNs** — `Resource: "*"` requires an explicit ADR approved by @architect.
- Lambda execution roles may not share roles across functions. One function = one role.
- Inline policies are forbidden; use managed policies or `grant*` CDK methods.
- No long-lived IAM user keys in CI/CD. **OIDC only** (GitHub Actions federated identity).
- Secrets Manager or Parameter Store for all runtime secrets; no environment variable literals in CDK stack code.

### 1.3 Networking
- All Lambda functions run inside a VPC with private subnets unless the function has zero AWS resource dependencies.
- Security groups: default-deny inbound. Explicit ingress rules only. No `0.0.0.0/0` ingress on non-public-facing resources.
- VPC endpoints required for S3, DynamoDB, and SSM to avoid NAT Gateway costs and public traffic.

### 1.4 Encryption
- Encryption at rest: **mandatory** for all data stores (DynamoDB, S3, RDS, SQS, SNS). CMK (KMS) required in production; AWS-managed key acceptable in dev/staging.
- Encryption in transit: TLS 1.2 minimum; TLS 1.3 required for new endpoints. No plaintext HTTP for inter-service traffic.
- KMS key rotation must be enabled (`enableKeyRotation: true` in CDK).

### 1.5 Tagging Strategy
Every resource must carry all five tags:

| Tag key | Example value | Purpose |
|---|---|---|
| `Project` | `booking-service` | Cost allocation |
| `Environment` | `prod` / `staging` / `dev` | Pipeline targeting |
| `Owner` | `platform-team` | Runbook ownership |
| `CostCenter` | `cc-1042` | Finance reporting |
| `ManagedBy` | `cdk` | Drift detection |

### 1.6 Resilience & Availability
- Multi-AZ deployment by default for production. Single-AZ only for non-production and only with an ADR.
- DynamoDB: enable Point-In-Time Recovery (PITR) in production. Set TTL on all transient records.
- All asynchronous integrations (SQS consumers, EventBridge rules) must define a Dead Letter Queue (DLQ) with `maxReceiveCount ≤ 5`.
- Lambda concurrency limits must be set per function. No unrestricted concurrency in production.
- Circuit breaker pattern required for all synchronous downstream calls with latency > 50 ms P50.

### 1.7 Observability Baseline
- Structured JSON logs on every Lambda: `{ "level", "requestId", "traceId", "msg", ...context }`.
- X-Ray active tracing enabled on all Lambda functions and API Gateway stages.
- CloudWatch alarms required at deployment for: error rate, P99 latency, throttles, DLQ depth.
- Log retention: 90 days for production, 30 days for non-production. Set explicitly; do not rely on "Never expire."
- No PII (names, emails, phone numbers, payment data) in log payloads — ever.

---

## §2 — Coding Conventions

### 2.1 Universal Rules (all languages)
- **Function length:** ≤ 30 executable lines (blank lines and comments excluded). Extract to named helpers; never suppress with a comment.
- **Nesting depth:** ≤ 3 levels. Guard clauses over nested conditionals.
- **Error handling:** Typed, domain-specific error classes only. No bare `catch (e)` that swallows context. Every error must either be re-thrown with added context, logged at `ERROR` level, or escalated to the caller.
- **No hardcoded secrets or environment-specific strings** in source code. All config via environment variables validated at startup.
- **Constants:** `UPPER_SNAKE_CASE` in every language.
- **Idempotency:** All Lambda handlers and message processors must be idempotent. Use a deduplication key pattern or conditional writes.
- **Input validation:** Validate and sanitize all external input at the system boundary (API handler, queue consumer, CLI entry point) before it reaches business logic. Use schema validation libraries (Zod, Pydantic, Bean Validation) — never manual string checks.

### 2.2 TypeScript / JavaScript
- TypeScript 5.x, `strict: true`, `noUncheckedIndexedAccess: true`, `exactOptionalPropertyTypes: true`.
- `any` is forbidden. `unknown` is allowed only with an immediate type guard or narrowing.
- `PascalCase` — classes, interfaces, type aliases, enums, React/Angular components.
- `camelCase` — variables, functions, method names, file names (exception: CDK stack files use PascalCase).
- Custom error classes must extend `Error`, set `this.name`, and call `super(message)`. Example:
  ```typescript
  export class BookingNotFoundError extends Error {
    constructor(bookingId: string) {
      super(`Booking ${bookingId} not found`);
      this.name = 'BookingNotFoundError';
    }
  }
  ```
- ESM imports only. No `require()` in new files.
- Exact version pins in `package.json` — no `^`, no `~`, no `*`.
- `tsconfig.json` must enable `paths` aliases; no `../../..` chains longer than two levels.
- `Promise<void>` return types must be awaited at call sites. No floating promises.

### 2.3 Python
- Python 3.12+. `from __future__ import annotations` in every module.
- Type hints required on **all** function and method signatures (parameters and return type). `Any` requires a `# type: ignore` comment with justification.
- `snake_case` — functions, variables, modules. `PascalCase` — classes. `UPPER_SNAKE_CASE` — module-level constants.
- Custom exceptions: domain base class (e.g., `class BookingError(Exception): pass`) with leaf exceptions inheriting from it — never directly from `Exception` in leaf classes.
- No bare `except:` or `except Exception:` without re-raising or logging at `ERROR`. Always `except SpecificError as exc:`.
- Exact version pins in `requirements.txt` using `==` (e.g., `boto3==1.34.0`). Use `pip-compile` from `pip-tools` for lock files.
- `pyproject.toml` with `[tool.mypy]` `strict = true` for all new services.
- Run `pip audit` before every @codeCrafter handoff; zero high/critical CVEs allowed.

### 2.4 Java / Kotlin
- Java 21 LTS or Kotlin 1.9+. Use `record` (Java) or `data class` (Kotlin) for DTOs — no boilerplate getters/setters.
- `PascalCase` — classes, interfaces, annotations. `camelCase` — methods, variables, parameters. `UPPER_SNAKE_CASE` — constants.
- Checked exceptions must be declared or wrapped in a domain exception with a cause chain. No `e.printStackTrace()`, no `throws Exception` on public APIs.
- SLF4J + Logback for logging. `{}` placeholders — no string concatenation in log calls.
- Exact version pins in `build.gradle` (no dynamic `+`) or `pom.xml` (no `RELEASE`/`LATEST`/`SNAPSHOT` in production dependencies).
- Use `Optional<T>` for nullable return values on domain service methods. Never return `null` from a public API.

### 2.5 React / Next.js
- Functional components only. Zero class components in new code.
- Props via TypeScript `interface` — exported and named (e.g., `BookingCardProps`). No `any`, no anonymous inline object types in signatures.
- Tailwind CSS exclusively — no inline styles, no CSS modules for new components (unless migrating existing).
- Atomic Design hierarchy: Atoms → Molecules → Organisms → Templates → Pages.
- `React.memo` for pure display components with stable props. `useCallback`/`useMemo` only where a profiler confirms a regression — not preemptively.
- All data fetching via React Query or SWR. No raw `fetch` with `useEffect` for server data.
- Server Components by default in Next.js 14+. Client Components (`'use client'`) only for interactivity or browser APIs.

### 2.6 Angular
- `ng generate` for all artifacts. No hand-crafted boilerplate.
- Standalone components (Angular 17+) by default. NgModules only when required by existing project structure.
- Strictly typed `@Input()` / `@Output()` — no `any` in signal/event types.
- Angular CDK for focus management, overlays, and accessibility patterns. Every interactive element must have an `aria-label` or `aria-labelledby`.
- Lazy-load all feature routes. No eagerly loaded feature modules.
- `inject()` function over constructor injection in new components (Angular 14+ style).

### 2.7 API Design
- REST: follow RFC 9110. Use `GET`, `POST`, `PUT`, `PATCH`, `DELETE` semantics strictly. No RPC-style verbs in URLs.
- All API responses use a consistent envelope:
  ```json
  { "data": {}, "meta": { "requestId": "...", "timestamp": "..." } }
  ```
- Error responses use `StandardErrorResponse`:
  ```json
  { "error": { "code": "BOOKING_NOT_FOUND", "message": "...", "requestId": "..." } }
  ```
- HTTP 4xx for client errors, 5xx for server errors. Never 200 with an error body.
- API versioning via URL path prefix (`/v1/`, `/v2/`). No header-based versioning.
- Idempotency keys required on all `POST` mutations that are not naturally idempotent.
- OpenAPI 3.1 spec must be committed alongside every new or modified endpoint.

---

## §3 — Testing & Quality

### 3.1 Coverage
- **≥ 80% branch coverage** on all business logic. Measured with Jest (`--coverage`) or pytest-cov. Coverage gate enforced in CI; a PR that drops below 80% on changed files is blocked.
- 100% coverage on error paths and edge cases in domain services.

### 3.2 Frameworks & Tooling
| Layer | Tool | Notes |
|---|---|---|
| Unit | Jest (TS/JS) / pytest (Python) / JUnit 5 (Java/Kotlin) | Isolated; no I/O |
| Integration | Jest + LocalStack / pytest + moto | Real AWS API shape, local execution |
| E2E / UI | Playwright | Against deployed staging environment |
| Load | Artillery | SLO gate: P99 < 1000 ms, error rate < 0.1% |
| Security scan | `npm audit` / `pip audit` / `trivy` | Zero high/critical before merge |

### 3.3 Test Authoring Rules
- No real AWS calls in unit tests. Use `aws-sdk-client-mock` (Node) or `moto` (Python). Any test hitting a real AWS endpoint is an integration test and must be tagged accordingly.
- Test names describe behavior: `should return 404 when booking does not exist`, not `test_booking_missing`.
- Each test file covers exactly one module. No cross-module assertions in a single `describe` block.
- Test data fixtures live in `__fixtures__/` or `test/fixtures/`. No magic inline literals in test bodies.
- Integration tests must verify DLQ behavior: publish a poison-pill message and assert it lands in the DLQ after `maxReceiveCount` retries.
- Load tests must verify idempotency under concurrent load: send the same idempotency key from N workers and assert exactly one write occurs.

### 3.4 Security Scanning (pre-merge)
- `npm audit --audit-level=high` or `pip audit` with zero high/critical findings.
- `trivy fs .` for container images and dependency trees.
- Secret scanning via `git-secrets` or `trufflehog` in the pre-commit hook and CI.
- OWASP Dependency-Check on every PR that adds or upgrades a dependency.

---

## §4 — Documentation & Commits

### 4.1 Commit Messages
- **Conventional Commits** strictly: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `perf:`, `ci:`.
- Breaking changes: append `!` after the type (`feat!:`) and include a `BREAKING CHANGE:` footer.
- Commit scope required for multi-module repos: `feat(booking): add cancellation endpoint`.
- No `WIP`, `temp`, `misc`, or similar non-descriptive commits on main. Squash before merge.

### 4.2 Code Comments
- Comments explain **why**, not **what**. If the what needs a comment, rename the variable or extract a function.
- No `TODO` or `FIXME` on merge. Raise a tracked issue instead. CI lint blocks these from reaching main.
- No commented-out code on merge. Delete dead code; version control is the history.

### 4.3 Module Documentation
- Every new module must have a `README.md` with: purpose, local setup, environment variables required, how to run tests, and how to deploy.
- `.env.example` must be updated whenever a new env var is introduced.
- OpenAPI spec committed alongside every new or modified REST endpoint.
- ADRs written for every architecture decision at decision time, not retroactively.

### 4.4 PR Standards
- PRs must link to the task ID (`T-NNN`) in the description.
- Max PR size: 400 lines changed (excluding generated/lock files). Larger changes require stacked PRs.
- Every PR requires at least one approval from a human reviewer before merge.
- Branch name convention: `feat/T-NNN-short-description`, `fix/T-NNN-short-description`.

---

## §5 — UI & UX Standards

### 5.1 Component Architecture
- Atomic Design enforced: Atoms → Molecules → Organisms → Templates → Pages.
- No business logic in components. Components render state; hooks own logic.
- Custom hooks live in `/hooks/` and follow the `use` prefix convention.

### 5.2 Styling
- Tailwind CSS exclusively. No inline styles. No CSS-in-JS.
- Design tokens defined in `tailwind.config.ts`. No magic hex values in JSX.

### 5.3 Accessibility (WCAG 2.1 AA)
- All interactive elements: `aria-label` or `aria-labelledby`, keyboard navigation, visible focus ring.
- Color contrast ratio ≥ 4.5:1 for normal text, ≥ 3:1 for large text.
- No motion without `prefers-reduced-motion` support.

### 5.4 Performance Budgets
- LCP ≤ 2.5 s on a simulated 4G connection.
- CLS ≤ 0.1.
- Total bundle size (JS, first load) ≤ 200 kB gzipped.
- Images: Next.js `<Image />` or equivalent. No unoptimized `<img>` in production builds.

---

## §6 — Performance & Scalability

- **Lambda cold start:** P95 init duration ≤ 1 s. Use provisioned concurrency for latency-critical paths. Avoid heavy dependencies in the handler bundle.
- **Database:** No unbounded table scans. All DynamoDB reads via table key or GSI. All SQL queries reviewed with `EXPLAIN ANALYZE` before merge.
- **N+1 prevention:** DataLoader or equivalent batching required for any nested relationship fetch.
- **Pagination:** All list endpoints paginate. Default page size ≤ 100 items. Cursor-based pagination preferred over offset for large datasets.
- **Caching:** Cache TTL and invalidation strategy defined at design time in the ADR. CDN caching headers required on static and semi-static responses.
- **Async first:** Operations expected to run > 5 s must be decoupled via SQS or EventBridge. Never block a synchronous API response on a deferrable operation.

---

## §7 — Agent Integration Rules

| Agent | Sections enforced | FAIL action |
|---|---|---|
| @architect | §1 (all) | `SECURITY FAIL:` or return ADR to @techLead |
| @codeCrafter | §2, §6 | Fix before handoff |
| @codeReviewer | §2, §3.1, §4, §5 (if UI) | Return to @codeCrafter with section citation |
| @qualityGuard | §3, §1.7 (log PII check) | `SECURITY FAIL:` blocks; others return to @codeCrafter |
| @devOps | §1.2 (OIDC), §1.5 (tags), §4.1 (commit) | Block pipeline, return to @techLead |

**@codeReviewer rule:** Every FAIL output must cite the specific section and sub-point violated (e.g., `§2.2 — floating Promise in src/handlers/cancel.ts:42`).

**@qualityGuard rule:** Coverage gate failure (< 80%) must list the specific branches missed, not just the percentage.

**SECURITY FAIL format:** `SECURITY FAIL: [§section] [description] in [file]:[line]`
Example: `SECURITY FAIL: §2.1 hardcoded secret in src/config/db.ts:17`
