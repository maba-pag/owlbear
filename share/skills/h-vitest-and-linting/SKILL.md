---
name: h-vitest-and-linting
description: "Handbook: Vitest, Playwright, ESLint, Stylelint, and coverage commands for the Cockpit frontend"
user-invocable: false
---

# Frontend Test, Lint, and Coverage Reference

All commands below run from the Cockpit frontend package root: `serve/cockpit/web/`. Running Vitest from the repo root causes `ReferenceError: HTMLElement is not defined` because the jsdom environment in `vite.config.ts` is not discovered.

For other projects, substitute the equivalent frontend package root.

Quality-runner's normal frontend evidence path is Vitest plus ESLint. Use the Playwright, build, CSS, or HTML commands below when AC, Architecture Review notes, or caller instructions explicitly require those proof types.

## Vitest Commands

### Working directory

```shell
cd serve/cockpit/web
```

Every vitest invocation below assumes this cwd.

### Scoped runs

```shell
NODE_OPTIONS='--max-old-space-size=2048' npx vitest run --silent src/__tests__/MyComponent.test.tsx
```

Multiple files:

```shell
NODE_OPTIONS='--max-old-space-size=2048' npx vitest run --silent src/__tests__/A.test.tsx src/__tests__/B.test.tsx
```

### Full suite

```shell
NODE_OPTIONS='--max-old-space-size=2048' npx vitest run --silent
```

Matches all `src/**/*.{test,spec}.{ts,tsx}` files (configured in `vite.config.ts`).

### Default flags

- `NODE_OPTIONS='--max-old-space-size=2048'` — matches the `test` script in `package.json`. Without it, PDS test suites can OOM.
- `--silent` — suppresses `console.log` / `console.warn` / `console.error` from test code. PDS components emit hundreds of thousands of console lines in jsdom; without `--silent`, output can exceed 600K lines, making logs unreadable. Vitest still reports test names, pass/fail status, and assertion errors — only console noise is hidden.
- `npx vitest run` (not `npx vitest`) — `run` disables watch mode. Without it, vitest stays open waiting for file changes.

## ESLint

```shell
cd serve/cockpit/web && npx eslint src/components/MyComponent.tsx
```

Lint all source:

```shell
cd serve/cockpit/web && npx eslint src/
```

ESLint uses a flat config (`eslint.config.js`) with `@eslint/js` + `typescript-eslint`. The rule set is intentionally minimal — `@typescript-eslint/no-unused-vars` as a warning.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | No violations (or warnings only) |
| 1 | Lint violations found |
| 2 | Misconfiguration / fatal error |

## CSS and HTML Lint

CSS lint:

```shell
cd serve/cockpit/web && npm run lint:css
```

HTML lint:

```shell
cd serve/cockpit/web && npm run lint:html
```

Use these when CSS or `index.html` changed, or when AC names layout/CSS/HTML validity. ESLint does not inspect CSS files.

## Build and E2E

Build:

```shell
cd serve/cockpit/web && npm run build
```

Playwright E2E:

```shell
cd serve/cockpit/web && npm run test:e2e
```

The Playwright config runs Chromium only and starts through `npm run build && npm run preview` on port 4173. If TypeScript or Vite build fails, Playwright may report a webServer/startup failure before any E2E assertions execute.

Browser binaries are not bundled with `@playwright/test`; one-time setup is `npx playwright install chromium`.

## Coverage

```shell
cd serve/cockpit/web && NODE_OPTIONS='--max-old-space-size=2048' npx vitest run --silent --coverage.reporter=text --coverage.provider=v8
```

Scoped with coverage:

```shell
cd serve/cockpit/web && NODE_OPTIONS='--max-old-space-size=2048' npx vitest run --silent src/__tests__/MyComponent.test.tsx --coverage.reporter=text --coverage.provider=v8
```

Coverage reports module-level percentages only — no per-branch analysis.

## Vitest Configuration

Config lives in `vite.config.ts` (not a separate `vitest.config.ts`):

```typescript
test: {
  environment: 'jsdom',
  setupFiles: ['./vitest.setup.ts'],
  globals: true,
  include: ['src/**/*.{test,spec}.{ts,tsx}'],
  testTimeout: 10_000,
  teardownTimeout: 3_000,
}
```

### Setup file (`vitest.setup.ts`)

Imports and shims applied before every test:

- `@porsche-design-system/components-react/jsdom-polyfill` — PDS jsdom support
- `@testing-library/jest-dom/vitest` — DOM matchers
- `skipPorscheDesignSystemCDNRequestsDuringTests()` — blocks PDS CDN fetches
- `HTMLDialogElement.showModal` / `.close` — jsdom stub (vitest `vi.fn()`)
- `HTMLElement.attachInternals` — jsdom stub for PDS form components
- `EventSource` — closed-by-default stub
- PDS `ownerDocument` TypeError suppression (global error handler)

### PDS component testing notes

- PDS custom elements are host elements in jsdom. Prefer selectors such as `p-select`, `p-input-text`, and `p-multi-select` when Testing Library roles are unavailable.
- `PSelect` changes are commonly driven with `CustomEvent('change', { detail: { value }, bubbles: true })`.
- `PMultiSelect` changes are driven with `CustomEvent('update', { detail: { value: [...] }, bubbles: true })`.
- If a behavior depends on layout, focus trapping, browser geometry, or actual rendered viewport width, use Playwright instead of Vitest.

## Known Gotchas

- **Must `cd` to your frontend package root first.** This is the #1 cause of quality-runner frontend failures. Vitest reads `vite.config.ts` from the cwd, so running from the repo root skips the jsdom environment entirely.
  > Example (OwlBear-dev): `cd serve/cockpit/web`
- **Build failures can mask E2E assertions.** When Playwright fails before tests run, inspect the build output first; the failure may belong to TypeScript/Vite rather than the E2E test body.
- **PDS console noise.** PDS components emit thousands of `console.error` / `console.warn` lines in jsdom (e.g. `variant 'tertiary'`, `CDN request blocked`). The `--silent` flag suppresses this noise. If you omit `--silent` for debugging, only the vitest summary line (`Test Files: N passed`, `Tests: N passed`) determines pass/fail.
- **Output volume.** Without `--silent`, PDS noise can produce 600K+ lines. Always use `--silent`. If output is still truncated, use the file-capture fallback: redirect to `.owlbear/scratch/vitest-{task_id}.log` and `grep` or `tail -50` for the summary — **never `read_file` on a vitest log** (they can be hundreds of thousands of lines).
- **`npx vitest run` vs `npx vitest`.** Always use `run`. Without it, vitest enters watch mode and never exits.
- **No `--reporter=verbose` by default.** The default reporter is sufficient for summary counts. Use `--reporter=verbose` only when individual test names are needed for debugging.
- **Never `read_file` on vitest log files.** If you redirected output to a file, use `tail -50` to get the summary or `grep -E 'FAIL|Test Files:|Tests:' <file>` to extract results. Log files can be 600K+ lines; reading them with `read_file` wastes context and tokens.
