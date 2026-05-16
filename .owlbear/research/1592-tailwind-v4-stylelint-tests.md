# Tailwind v4 Vite Plugin + Stylelint Config — Test Research

> **Owning task:** #1592 — P0-03: Tests — Tailwind v4 Vite plugin + Stylelint config
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

Task #1592 requires RED-phase tests for three capabilities:
1. PDS Tailwind utility classes compile without error in `vite build`
2. `light-dark()` CSS functions are preserved in build output
3. `npm run lint:css` passes on files containing `@theme`, `@utility`, `@apply`

The builder (#1595) will install `tailwindcss` + `@tailwindcss/vite`, configure the PDS theme import, and update Stylelint. These tests must fail RED before that work and pass GREEN after.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | PDS v4 Tailwind Introduction | https://designsystem.porsche.com/v4/tailwindcss/introduction/ | 0.95 |
| 2 | PDS v4 Tailwind Color Examples | https://designsystem.porsche.com/v4/tailwindcss/color/examples/ | 0.90 |
| 3 | PDS v4 Migration Guide (Tailwind) | https://designsystem.porsche.com/v4/news/migration-guide/tailwindcss/ | 0.85 |
| 4 | PDS tailwindcss theme source | github:porsche-design-system/porsche-design-system `packages/styles/projects/tailwindcss/src/index.ts` | 0.95 |
| 5 | PDS installed theme file | `node_modules/@porsche-design-system/components-react/tailwindcss/index.css` (local, 789 lines) | 1.0 |
| 6 | Tailwind CSS v4 Vite install docs | https://tailwindcss.com/docs | 0.85 |
| 7 | `stylelint-config-tailwindcss` npm | https://github.com/zhilidali/stylelint-config-tailwindcss | 0.70 |
| 8 | SO: Tailwind v4 unknown at-rules | https://stackoverflow.com/questions/79513015 | 0.75 |

## 3. Analysis

### 3.1 AC-1: PDS Tailwind Utility Class Compilation

**Finding: `gap-md` does not exist in PDS Tailwind theme — AC needs correction.**

The PDS theme (`index.css`) defines these spacing variables:
- `--spacing-fluid-{xs,sm,md,lg,xl,2xl}` → utilities: `gap-fluid-md`, `p-fluid-sm`, etc.
- `--spacing-static-{2xs,xs,sm,md,lg,xl,2xl}` → utilities: `gap-static-md`, `p-static-xs`, etc.

There is NO `--spacing-md` defined. PDS does not reset `--spacing-*: initial`, so Tailwind v4 default numeric spacing (`gap-4`, `gap-8`) survives, but `gap-md` is not a valid class in either standard Tailwind v4 or PDS.

| AC class | PDS `@theme` variable | Valid? | Correct form |
|----------|----------------------|--------|-------------|
| `bg-canvas` | `--color-canvas` | ✅ | `bg-canvas` |
| `text-contrast-high` | `--color-contrast-high` | ✅ | `text-contrast-high` |
| `gap-md` | (none) | ❌ | `gap-fluid-md` or `gap-static-md` |
| `rounded-sm` | `--radius-sm` | ✅ | `rounded-sm` |

**Recommendation:** Tests should use `gap-fluid-md` (PDS convention) instead of `gap-md`. The brief's AC text has this error propagated from incomplete PDS spacing research.

### 3.2 AC-2: light-dark() Preservation

PDS v4 uses `light-dark()` in ALL color variables (verified in installed `index.css`):
```css
--color-canvas: light-dark(#fff, hsl(225 66.7% 1.2%));
--color-contrast-high: light-dark(hsl(240 7.1% 11% / 0.7), hsl(240 12.5% 96.9% / 0.67));
```

The existing `vite.config.ts` already excludes `Features.LightDark` from lightningcss (added by #1555). With `@tailwindcss/vite`, the Tailwind Oxide engine processes `@theme` blocks and emits CSS that preserves `light-dark()` natively — it does not compile it away.

The test should verify `light-dark(` appears in the built CSS output after a `vite build`.

### 3.3 AC-3: Stylelint for Tailwind v4 At-Rules

Current `.stylelintrc.json` has `"at-rule-no-unknown": true`, which rejects Tailwind v4 at-rules.

PDS theme file uses: `@theme` (1 block), `@utility` (47 rules), `@layer` (1 block), `@supports` (1 block).
Application CSS may also use: `@apply`, `@source`, `@reference`.

| Option | Approach | Pros | Cons | Confidence |
|--------|----------|------|------|------------|
| A: `stylelint-config-tailwindcss` | `extends` the npm package | Maintained by community, auto-tracks new Tailwind at-rules | Adds dependency; current npm health unclear | 0.55 |
| B: Manual `ignoreAtRules` | Add `["theme","utility","apply","source","reference","variant","custom-variant","plugin"]` to `at-rule-no-unknown` | Zero new deps, explicit control | Must update manually when Tailwind adds at-rules | 0.80 |

**Recommendation (0.80):** Option B — manual `ignoreAtRules`. KISS-aligned, zero dependencies, and the Tailwind at-rule set is stable across v4.x. The list is documented in Tailwind v4 docs. PDS repo itself uses Biome's `noUnknownAtRules` ignore rather than a Stylelint plugin.

### 3.4 Test Strategy

Tests should follow the existing Vitest pattern for build-level assertions (see `vite_config.test.ts`, `ViteConfigAlias_1555.test.ts`).

| AC | Test approach | Pattern |
|----|--------------|---------|
| AC-1 | Read vite config, verify `@tailwindcss/vite` plugin is registered. Create a temp CSS file with PDS utility classes, run `vite.build()` programmatically or shell out to `npm run build`, check exit code = 0 | Build-output assertion |
| AC-2 | After `vite build`, read `dist/assets/*.css`, assert `light-dark(` substring present | File-content scan (like PDSHexScan pattern) |
| AC-3 | Create a temp CSS file with `@theme {}`, `@utility name {}`, `@apply bg-canvas;`, run `stylelint --config .stylelintrc.json` on it, assert exit code = 0 | CLI invocation test |

**Risk:** Build-level tests are slow (~5-10s). Keep test count minimal — one per AC line.

### 3.5 Vite 8 + @tailwindcss/vite Compatibility

`@tailwindcss/vite` is at v4.3.0 (May 2026). GitHub Discussion #19624 (Jan 2026) confirmed Vite 8 support was being added via insiders tag. By v4.3.0 this should be resolved. The project uses Vite 8.0.13.

**Risk (low):** If `@tailwindcss/vite@^4` doesn't support Vite 8, install will fail at builder time. The test-writer should NOT install Tailwind — that's the builder's job. Tests should assert expected state after installation.

## 4. Recommendation

**Proceed with test writing (0.82 confidence).** Three test files or one combined file covering the three AC lines. Key adjustments:

1. **Fix `gap-md` → `gap-fluid-md`** in the test (and flag for AC correction on parent task).
2. **Stylelint: test with manual `ignoreAtRules`** approach — the test creates a CSS fixture with `@theme`/`@utility`/`@apply` and asserts `npm run lint:css` (or direct Stylelint invocation) passes.
3. **light-dark(): scan build output** after `vite build` for `light-dark(` substring.

Challenge: SKIPPED — trivial scope (test scaffolding, no architecture decision).

## 5. Follow-up Tasks

None needed — this task produces tests; the builder task (#1595) is already created as a dependency. The `gap-md` AC discrepancy should be noted in the task body for the test-writer to handle.
