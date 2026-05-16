# Tailwind v4 + Stylelint Config — Task Redundancy Analysis

> **Owning task:** #1595 — P0-04: Install @tailwindcss/vite + configure Stylelint for Tailwind v4
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

Task #1595 requires installing `@tailwindcss/vite` as a Vite plugin, importing the PDS Tailwind theme, pinning `tailwindcss ^4` + `@tailwindcss/vite ^4`, and updating Stylelint config for Tailwind v4 at-rules. This task depends on #1592 (the RED tests).

**Core question:** Is any implementation work remaining, or was it already completed during the #1592 builder phase?

## 2. Sources Studied

| # | Source | URL / Path | Relevance |
|---|--------|-----------|-----------|
| 1 | Task #1592 builder notes | `.owlbear/kanban/archive/` (task body) | 1.0 |
| 2 | Commit 6a5b07b3 | builder for #1592 — installed Tailwind, configured Vite, Stylelint | 1.0 |
| 3 | Current `package.json` | `serve/cockpit/web/package.json` | 1.0 |
| 4 | Current `vite.config.ts` | `serve/cockpit/web/vite.config.ts` | 1.0 |
| 5 | Current `.stylelintrc.json` | `serve/cockpit/web/.stylelintrc.json` | 1.0 |
| 6 | Current `tailwind.css` | `serve/cockpit/web/src/tailwind.css` | 1.0 |
| 7 | PDS theme file | `node_modules/@porsche-design-system/components-react/tailwindcss/index.css` | 0.90 |
| 8 | Sibling research doc | `.owlbear/research/1592-tailwind-v4-stylelint-tests.md` | 0.95 |
| 9 | Task #1592 audit notes | Audit archived at .97 confidence | 0.85 |

## 3. Analysis

### 3.1 AC-by-AC Verification Against Current Codebase

| AC | Required State | Current State | Evidence | Satisfied? |
|----|---------------|---------------|----------|-----------|
| AC-1: PDS Tailwind utilities compile + light-dark() preserved | `bg-canvas`, `text-contrast-high`, `gap-md` compile; `light-dark()` in build output | `@tailwindcss/vite` registered in `vite.config.ts:3,72`; PDS theme imported in `tailwind.css:1-2`; 8/8 tests pass including utility compilation + light-dark() assertions | Commit `6a5b07b3` (#1592 builder) | ✅ |
| AC-2: package.json pins + no PostCSS + LightningCSS | `tailwindcss ^4`, `@tailwindcss/vite ^4` in devDeps; no `postcss.config.*`; `css.lightningcss` in vite config | `package.json:34` has `@tailwindcss/vite: ^4.3.0`; `package.json:47` has `tailwindcss: ^4.3.0`; no PostCSS config exists; `vite.config.ts:86-90` has `css.lightningcss` | File inspection | ✅ |
| AC-3: `npm run lint:css` passes on @theme/@utility/@apply | Stylelint `ignoreAtRules` includes Tailwind v4 at-rules | `.stylelintrc.json:6-14` has 8-entry allowlist: `theme`, `utility`, `apply`, `source`, `reference`, `variant`, `custom-variant`, `plugin` | File inspection + #1592 AC-3 tests pass | ✅ |

### 3.2 How This Happened

Task #1592 (RED tests for Tailwind+Stylelint) went through the full pipeline: test-writer → builder → reviewer → docs → audit → archived. The **builder phase of #1592** implemented the GREEN changes — which is the exact same scope as #1595. This is a standard TDD outcome: the test task's GREEN phase implemented the feature.

The #1592 reviewer explicitly noted this overlap:
> `#1595` remains in `research` with overlapping implementation scope [...] downstream coordination should resolve whether `#1595` is now redundant before it is dispatched.

### 3.3 AC-1 Discrepancy: `gap-md` vs `gap-fluid-md`

The #1595 AC text says `gap-md`. PDS does NOT define `--spacing-md` — verified by searching `node_modules/@porsche-design-system/components-react/tailwindcss/index.css`. PDS uses `--spacing-fluid-{xs..2xl}` and `--spacing-static-{2xs..2xl}`. This was already identified and corrected during #1592 research and architecture review. The tests use `gap-fluid-md`.

## 4. Recommendation

**Archive #1595 as superseded by #1592 (confidence: 0.95).**

All three ACs are satisfied by work already committed and audited under #1592 (commit `6a5b07b3`, audit confidence .97). No remaining implementation work exists. Dispatching this task through the full pipeline would produce zero code changes.

| Option | Action | Confidence | Risk |
|--------|--------|-----------|------|
| A: Archive as superseded | Archive with `archival_refs: [1592]` | 0.95 | Minimal — all evidence in #1592 audit |
| B: Run through pipeline anyway | Builder finds nothing to do, reviewer confirms | 0.30 | Wastes 4+ agent cycles for zero output |

Challenge: SKIPPED — no competing recommendation; finding is factual (code already exists).

## 5. Follow-up Tasks

None needed — all implementation work was completed under #1592. The `gap-md` AC discrepancy is a documentation note, not an implementation gap.
