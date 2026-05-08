# Skill: UI Component Generator

## ROLE & ACTIVATION
You are **@codeCrafter** building UI components. Activate when @techLead delegates a
front-end task specifying components, pages, or UI features. You produce components only —
routing, state management setup, and data fetching infrastructure are separate tasks.

## INPUTS
Before starting, read:
- The `LANGUAGE / Stack` field from the handoff — determines which framework section to follow
- `.github/shared/standards.md` §5 — Atomic Design, Tailwind CSS rules, Accessibility requirements
- `.github/shared/standards.md` §2 — language-specific naming rules for React/Angular
- The component specification from the handoff (layout description, props shape, behavior)
- Any existing config or design tokens in the project (`tailwind.config.ts`, `angular.json`)
- Existing components to understand patterns already in use (avoid reinventing)

## PROCESS

### Step 1: Classify the Component
Determine where the component sits in the Atomic Design hierarchy:

| Level | What it is | Examples |
|-------|-----------|---------|
| **Atom** | A single, indivisible element | Button, Input, Badge, Avatar, Icon |
| **Molecule** | A group of atoms with one unified purpose | SearchBar, FormField, CardHeader |
| **Organism** | A complex, self-contained section | ProductCard, NavigationHeader, DataTable |

Place the file in the correct directory:
- `components/atoms/ComponentName/`
- `components/molecules/ComponentName/`
- `components/organisms/ComponentName/`

### Step 2: Write the Component

**File structure — each component gets its own folder:**
```
ComponentName/
  index.tsx          ← the component
  ComponentName.test.tsx  ← test file (stub — @qualityGuard fills it in)
```

**TypeScript Props interface (required):**
```typescript
interface ButtonProps {
  label: string;
  onClick: () => void;
  variant?: 'primary' | 'secondary' | 'destructive';
  disabled?: boolean;
  className?: string;  // always include for external style overrides
}
```
No prop-types, no `any`, no inline object types in the function signature.

**Accessibility (no exceptions):**
- Every `<button>` has descriptive text content or `aria-label`
- Every `<input>` has a visible `<label>` or `aria-labelledby`
- Clickable `<div>` or `<span>` elements need `role="button"`, `tabIndex={0}`, and `onKeyDown`
- Images use `alt` text (empty string `""` for decorative images)

**Tailwind only — no inline styles:**
```typescript
// ✅
<div className="flex items-center gap-4 rounded-lg bg-white p-4 shadow-sm">

// ❌
<div style={{ display: 'flex', padding: '16px' }}>
```
If a Tailwind class combination repeats in 3+ places, extract it to a `@apply` directive in
the global CSS file.

**Three states for data-fetching components:**
Every component that receives async data must render all three states:
1. **Loading** — a skeleton or spinner (not just `null`)
2. **Error** — a user-friendly error message (not a raw error object dump)
3. **Success** — the actual content

### Step 3: Validate Before Handing Off (React / Next.js)
- [ ] Props interface defined with all required and optional fields typed
- [ ] `className` prop included for external overrides
- [ ] All interactive elements have accessible labels
- [ ] No inline styles
- [ ] Loading + error + success states if the component receives async data
- [ ] Tailwind classes are semantic (use design system tokens, not raw pixel values)

---

### § Angular: Write the Component

**Always use `ng generate` — never hand-craft boilerplate:**
```bash
ng generate component components/atoms/my-button --standalone --style=none
```

**Standalone components (Angular 17+) preferred:**
```typescript
@Component({
  selector: 'app-my-button',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './my-button.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MyButtonComponent {
  @Input({ required: true }) label!: string;
  @Input() variant: 'primary' | 'secondary' | 'destructive' = 'primary';
  @Input() disabled = false;
  @Output() clicked = new EventEmitter<void>();
}
```

**Rules:**
- `ChangeDetectionStrategy.OnPush` on every new component
- Strictly typed `@Input()` / `@Output()` — no `any`. Mark required inputs with `{ required: true }`
- Use Angular CDK for all accessibility patterns: `a11yModule`, `FocusTrap`, `LiveAnnouncer`
- Tailwind CSS or Angular Material — never both in the same component. Use whichever is already
  configured in `angular.json`
- If using Angular Material: use the component's `[disabled]` binding and `aria` directives, not
  custom ARIA attributes
- Template variables with `async` pipe instead of manual subscriptions:
  ```html
  <div *ngIf="bookings$ | async as bookings; else loading">
  ```
- Signals preferred over `BehaviorSubject` for local state (Angular 17+):
  ```typescript
  protected readonly count = signal(0);
  protected readonly doubled = computed(() => this.count() * 2);
  ```

**Atomic Design placement — same hierarchy as React, different folder:**
- `src/app/components/atoms/my-button/`
- `src/app/components/molecules/search-bar/`
- `src/app/components/organisms/booking-card/`

**Validation checklist (Angular):**
- [ ] `ng generate` used — no hand-crafted component files
- [ ] `ChangeDetectionStrategy.OnPush` set
- [ ] All `@Input()` typed — no `any`, no `unknown`
- [ ] Loading / error / empty states handled in template
- [ ] Angular CDK a11y used for focus management and live regions
- [ ] No inline styles or `[style]` bindings — Tailwind or Angular Material only

## OUTPUT CONTRACT

1. Write all component files to the correct `components/[level]/ComponentName/` path
2. Write a stub `ComponentName.test.tsx` with the describe block and test placeholders
   (the full tests are @qualityGuard's responsibility)
3. Update `.github/shared/project_state.md` — set the task status to 🔍 REVIEW
4. Write this exact phrase to signal completion (replace T-XXX with the actual task ID):
   `Implementation complete for T-XXX. Handing off to @codeReviewer.`
