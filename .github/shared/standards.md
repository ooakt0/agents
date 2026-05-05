# 🏛️ ENGINEERING STANDARDS & GUIDELINES
**Owner:** @techLead | **Auditor:** @codeReviewer

---

## 1. 🏗️ AWS & INFRASTRUCTURE (IaC)
*   **IaC Tooling:** Always use **AWS CDK (TypeScript)**. No manual Console changes.
*   **Principle of Least Privilege:** IAM roles must be scoped to specific resources. No `Resource: "*"` without @architect approval.
*   **Tagging Strategy:** Every resource must have `Project`, `Environment`, and `Owner` tags.
*   **Resilience:** Multi-AZ by default for production; use TTLs on DynamoDB items to manage costs.

---

## 2. 💻 CODING CONVENTIONS

**Universal rules (apply to ALL languages):**
*   **Functions:** Maximum 30 lines per function (blank lines excluded).
*   **Nesting:** Maximum 3 levels deep.
*   **Error Handling:** Use typed/custom error classes. No generic catch-and-log.
*   **No hardcoded secrets:** All config via environment variables.
*   **Constants:** `UPPER_SNAKE_CASE` in every language.

**TypeScript / JavaScript:**
*   TypeScript 5.x Strict Mode ON. No `any`. No `unknown` without immediate narrowing.
*   `PascalCase` — Components, Classes, Interfaces. `camelCase` — variables, functions, file names.
*   Custom error classes with `this.name` set. Never `catch (e) { console.log(e) }`.
*   ESM imports. Exact version pins in `package.json` (no `^` or `~`).

**Python:**
*   `snake_case` — functions, variables, file names. `PascalCase` — classes. `UPPER_SNAKE_CASE` — constants.
*   Type hints required on all function signatures (PEP 484). Use `from __future__ import annotations` for forward refs.
*   Custom exceptions: `class FooError(Exception): pass`. No bare `except:` — always `except SpecificError`.
*   Exact version pins in `requirements.txt` or `pyproject.toml` using `==` (e.g., `boto3==1.34.0`).
*   Run `pip audit` before every @codeCrafter handoff.

**Java / Kotlin:**
*   `PascalCase` — classes, interfaces. `camelCase` — methods, variables. `UPPER_SNAKE_CASE` — constants.
*   Use `record` (Java 16+) or `data class` (Kotlin) for DTOs — no boilerplate getters/setters.
*   Checked exceptions must be declared or wrapped in a domain exception. No `printStackTrace()`.
*   Use SLF4J / Logback for logging. No `System.out.println`.
*   Exact version pins in `build.gradle` (no `+`) or `pom.xml` (no `RELEASE`/`LATEST`).

**React / Next.js:**
*   Functional components only. No class components.
*   Props via TypeScript `interface`. No `any`, no inline object types in signatures.
*   Tailwind CSS only — no inline styles. Atomic Design hierarchy enforced (see §5).

**Angular:**
*   `ng generate` for all artifacts — no hand-crafted boilerplate.
*   Strictly typed `@Input()` / `@Output()` bindings. No `any`.
*   Angular CDK for all accessibility patterns (`aria-label`, focus management).
*   Standalone components preferred (Angular 17+). NgModules only if required by existing project structure.

---

## 3. 🧪 TESTING & QUALITY
*   **Coverage:** Minimum 80% unit test coverage for business logic.
*   **Frameworks:** Jest for Unit/Integration; Playwright for UI/E2E.
*   **Mocking:** Use `aws-sdk-client-mock` for AWS service testing. Never hit real AWS endpoints in Unit tests.
*   **Security:** Run `npm audit` or `safety check` before every @codeCrafter handoff.

---

## 4. 📝 DOCUMENTATION & COMMITS
*   **Commit Messages:** Use **Conventional Commits** (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`).
*   **Self-Documenting:** Code must be readable. Comments should explain "Why," not "What."
*   **Readme:** Every new module must include a local `README.md` explaining its purpose and local setup.

---

## 5. 🎨 UI & UX STANDARDS
*   **Components:** Atomic Design (Atoms -> Molecules -> Organisms).
*   **Styling:** Tailwind CSS. No inline styles.
*   **Accessibility:** All interactive elements must have `aria-labels` and keyboard navigation support.
*   **Performance:** All images must use Next.js `<Image />` optimization or equivalent.

---

## 🔗 AGENT INTEGRATION RULES
1.  **@codeCrafter:** Before saving a file, check against Section 2 (Coding) and Section 5 (UI).
2.  **@codeReviewer:** Your "Review" output must explicitly list which sections of this file were violated.
3.  **@qualityGuard:** Use Section 3 to define the test suite requirements.
