---
name: h-vitest-and-linting
description: "Handbook: Vitest, ESLint, and coverage commands for the Cockpit frontend"
user-invocable: false
---

# Vitest, ESLint, and Coverage Reference

All commands below run from `serve/cockpit/web/`. Running from the repo root causes `ReferenceError: HTMLElement is not defined` — the jsdom environment in `vite.config.ts` is not discovered.

## Vitest Commands

### Working directory

```shell
cd serve/cockpit/web
```

Every vitest invocation below assumes this cwd.

### Scoped runs

```shell
NODE_OPTIONS='--max-old-space-size=2048' npx vitest run src/__tests__/MyComponent.test.tsx
```

Multiple files:

```shell
NODE_OPTIONS='--max-old-space-size=2048' npx vitest run src/__tests__/A.test.tsx src/__tests__/B.test.tsx
```

### Full suite

```shell
NODE_OPTIONS='--max-old-space-size=2048' npx vitest run
```

Matches all `src/**/*.{test,spec}.{ts,tsx}` files (configured in `vite.config.ts`).

### Default flags

- `NODE_OPTIONS='--max-old-space-size=2048'` — matches the `test` script in `package.json`. Without it, PDS test suites can OOM.
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

## Coverage

```shell
cd serve/cockpit/web && NODE_OPTIONS='--max-old-space-size=2048' npx vitest run --coverage.reporter=text --coverage.provider=v8
```

Scoped with coverage:

```shell
cd serve/cockpit/web && NODE_OPTIONS='--max-old-space-size=2048' npx vitest run src/__tests__/MyComponent.test.tsx --coverage.reporter=text --coverage.provider=v8
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

## Known Gotchas

- **Must `cd serve/cockpit/web` first.** This is the #1 cause of quality-runner frontend failures. Vitest reads `vite.config.ts` from the cwd — running from the repo root skips the jsdom environment entirely.
- **PDS console noise.** PDS components emit thousands of `console.error` / `console.warn` lines in jsdom (e.g. `variant 'tertiary'`, `CDN request blocked`). These are cosmetic — only the vitest summary line (`Test Files: N passed`, `Tests: N passed`) determines pass/fail.
- **Output volume.** PDS noise can produce 100K+ characters. When parsing output, look for the last `Test Files:` and `Tests:` lines. If output is truncated, use the file-capture fallback: redirect to `.owlbear/scratch/vitest-{task_id}.log` and grep for the summary.
- **`npx vitest run` vs `npx vitest`.** Always use `run`. Without it, vitest enters watch mode and never exits.
- **No `--reporter=verbose` by default.** The default reporter is sufficient for summary counts. Use `--reporter=verbose` only when individual test names are needed for debugging.
