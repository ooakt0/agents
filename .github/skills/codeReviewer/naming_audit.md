# Skill: Naming Audit

## ROLE & ACTIVATION
You are **@codeReviewer** performing a naming convention audit. This skill runs immediately
after `complexity_check` passes — it is the second and final half of the code review. Do not
activate this skill if `complexity_check` returned a FAIL.

## INPUTS
Before starting, read:
- All files in scope for the current task (same set `complexity_check` reviewed)
- `.github/shared/standards.md` §2 — naming conventions (PascalCase, camelCase, UPPER_SNAKE_CASE)
- `.github/shared/standards.md` §1 — AWS resource naming conventions

## PROCESS

### Step 1: Variable and Parameter Naming

**Flag these patterns:**

| Pattern | Rule | Example violation | Required fix |
|---------|------|------------------|--------------|
| Single-letter variables (outside loops) | Must be descriptive | `const d = new Date()` | `const createdAt = new Date()` |
| Generic names | No `data`, `item`, `result`, `temp`, `obj`, `val`, `x`, `y` | `const result = fetch(url)` | `const userResponse = fetch(url)` |
| Boolean variables | Must start with `is`, `has`, `can`, `should` | `const active = true` | `const isActive = true` |
| camelCase verification | All variables and function names | `const User_Name = ...` | `const userName = ...` |

Loop indices `i`, `j`, `k` in `for` loops are acceptable — do not flag them.

### Step 2: Class, Interface, and Component Naming

| Type | Convention | Example violation | Required fix |
|------|-----------|------------------|--------------|
| Classes | PascalCase | `class userService` | `class UserService` |
| Interfaces | PascalCase (noun-based) | `interface iUser` | `interface User` or `interface UserProfile` |
| React components | PascalCase | `function productCard()` | `function ProductCard()` |
| Type aliases | PascalCase | `type apiResponse = ...` | `type ApiResponse = ...` |

Check for consistency: if the codebase uses `I`-prefix for interfaces (e.g., `IUser`), flag any
interface that doesn't follow the established pattern. Pick one convention and enforce it.

### Step 3: Constants and Environment Variables

| Pattern | Required | Example violation | Required fix |
|---------|----------|------------------|--------------|
| Module-level constants | UPPER_SNAKE_CASE | `const maxRetries = 3` | `const MAX_RETRIES = 3` |
| Environment variable names | UPPER_SNAKE_CASE | `process.env.dbUrl` | `process.env.DB_URL` |
| No raw config strings | Use named constants | `timeout: 5000` | `timeout: REQUEST_TIMEOUT_MS` |

### Step 4: AWS Resource Naming (CDK Stacks)

For every CDK construct in `infrastructure/`:

| Pattern | Convention | Example violation | Required fix |
|---------|-----------|------------------|--------------|
| Logical IDs | `{Environment}{ServiceName}{ResourceType}` | `OrdersTable` | `ProdOrdersTable` |
| S3 bucket physical names | lowercase, hyphens | `my_bucket_dev` | `my-bucket-dev` |
| Lambda function names | `{env}-{service}-{function}` | `OrderProcessor` | `prod-orders-processOrder` |
| DynamoDB table names | PascalCase logical ID, kebab-case physical name | N/A — CDK default is fine |

### Step 5: File Naming

| File type | Convention | Example violation | Required fix |
|-----------|-----------|------------------|--------------|
| Utility/service files | camelCase | `UserService.ts` | `userService.ts` |
| React component files | PascalCase | `productCard.tsx` | `ProductCard.tsx` |
| Test files | Same as source + `.test` | `userservice.test.ts` | `userService.test.ts` |
| Configuration files | kebab-case | `TailwindConfig.ts` | `tailwind.config.ts` |

## OUTPUT CONTRACT

**If any violations are found (FAIL):**
1. Produce a violation table:
   | File | Line | Current Name | Required Name | Rule |
   |------|------|-------------|---------------|------|
2. Do **NOT** hand off to @qualityGuard
3. Write: `Naming audit FAILED. Returning to @codeCrafter with [N] violations. Do not proceed until fixed.`

**If no violations are found (PASS):**
1. Write this exact phrase to activate the next review skill:
   `Naming audit passed. Activating dependency_audit.`
2. Immediately activate the `dependency_audit` skill — do not wait for user input
