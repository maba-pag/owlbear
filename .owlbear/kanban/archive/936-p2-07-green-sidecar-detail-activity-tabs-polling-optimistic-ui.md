---
id: 936
title: 'P2-07: GREEN — Sidecar (Detail + Activity tabs) + polling + optimistic UI'
status: archived
priority: important
created: 2026-04-17T19:59:03.599720+00:00
updated: 2026-04-19T12:45:15.935345+00:00
tags:
- cockpit
- frontend
- phase-2
- type:build
parent: 920
depends_on:
- 935
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #920

## Objective

Implement sidecar tabs, polling infrastructure, and optimistic UI to pass RED tests from #935.

## Acceptance Criteria

- [ ] Detail tab: allowlisted YAML fields as structured controls (PDS or Radix inputs, dropdowns, tag chips); markdown body rendered with react-markdown + remark-gfm + rehypeSanitize; toggle edit mode for body
- [ ] Save-time `updated` comparison (D9): on 409, show refresh-or-overwrite modal with current vs. server values
- [ ] History subtab: per-session breakdown from `GET /api/sessions?task_id={id}` (agent, duration, outcome)
- [ ] Activity tab: sessions from `GET /api/sessions?filter=`; default filter = active; switchable filters (all / failed-or-rejected / released)
- [ ] Click session row selects task in Detail tab + activates History subtab
- [ ] Polling: mtime-aware ~3s interval (TanStack Query refetchInterval or custom hook); skip 1 cycle after local mutation
- [ ] Connection health traffic light in status bar: green (poll within threshold) / yellow (lagging) / red (disconnected)
- [ ] Optimistic UI: snapshot state before mutation; immediate local update; rollback on API error
- [ ] Confirmation dialogs: backward moves, unclaim, unblock (surfaces block_reason before clearing)
- [ ] XSS hardening: strict CSP meta tag; no `dangerouslySetInnerHTML`; rehypeSanitize on all task-derived markdown
- [ ] Designed empty, loading, and error states for both tabs (no white-screen paths)
- [ ] All RED tests from #935 pass

## Files

- `serve/cockpit/web/src/components/DetailTab.tsx`
- `serve/cockpit/web/src/components/ActivityTab.tsx`
- `serve/cockpit/web/src/components/HistorySubtab.tsx`
- `serve/cockpit/web/src/components/ConfirmDialog.tsx`
- `serve/cockpit/web/src/hooks/usePolling.ts`
- `serve/cockpit/web/src/hooks/useOptimistic.ts`
- `serve/cockpit/web/src/hooks/useConnectionHealth.ts`
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/936-sidecar-green-gaps.md
- Sources: 7 studied, 5 high-relevance (S1–S2 external, S3–S7 codebase)
- Recommendation: close 5 AC gaps in order: G5 snapshot bug → G4 file extraction → G1 remark-gfm/rehype-sanitize → G2 CSP (production-only) → G3 PDS spike (confidence: 0.75)
- Follow-up tasks created: none — #936 itself covers all gaps
- Decision requests: none (all T1 autonomous)

## Challenge Results

- Challenger: reconsider (confidence in original: 0.45)
- Key challenges: C1 rehype-sanitize no-op without rehypeRaw, C2 CSP breaks Vite dev mode, C3 PDS shadow DOM may break test queries, C5 useOptimistic snapshot never updates before mutation
- Researcher response: accepted all — revised G2 to production-only CSP, revised G3 to spike-first approach, added G5 as new finding, dropped defense-in-depth framing for G1

## Key Findings Summary

1. **G5 (bug):** useOptimistic snapshot.current set at mount, never before mutation — rollback reverts to stale initial
2. **G4 (normative):** HistorySubtab, ConfirmDialog, useConnectionHealth listed as AC deliverables but inline
3. **G1 (compliance):** remark-gfm adds real GFM value; rehype-sanitize is AC compliance without rehypeRaw
4. **G2 (conflict):** Static CSP meta tag breaks Vite HMR; recommend production-only via transformIndexHtml
5. **G3 (risk):** PDS wrapper migration needs jsdom spike before committing — shadow DOM query breakage
[[2026-04-18]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | GREEN gap-closing task — all items serve one goal: close AC gaps identified by research. Splitting would orphan existing RED tests. |
| Interface clarity | PASS (after refinement) | 3 AC items refined below for precision. Research doc provides full implementation guidance. |
| Dependency correctness | PASS | depends_on #935 (done). No missing deps. |
| Module layering | PASS | Frontend-only. Shell → components → hooks layering is clean. |
| TDD compliance | PASS | 66 RED tests from #935 exist (DetailTab.test.tsx, ActivityTab.test.tsx, usePolling.test.ts, optimistic.test.ts). Test-writer should add gap-specific tests for G1/G5. |
| KISS/YAGNI | PASS | Research narrowed scope to 5 concrete gaps. No speculative work. |
| Premise challenge | PASS | Gaps are real: snapshot bug causes incorrect rollback, CSP absent, remark-gfm not wired, files mislocated. |
| Pattern consistency | PASS | Follows existing custom-hook + functional-component pattern. File reorg aligns with hooks/useBoard.ts convention. |
| Security surface | PASS | XSS: react-markdown is safe by default (no dSIH). rehypeSanitize is compliance without rehypeRaw. CSP is defense-in-depth. |
| Single domain | PASS | Frontend only. |

### AC Refinements (binding for builder)

**AC1 — PDS form controls:** RED tests from #935 use plain HTML selectors (`input[data-field="title"]`, `select[data-field="priority"]`). PDS wrapper migration MUST NOT break existing test selectors. Approach: plain HTML controls are the baseline. PDS wrappers are best-effort — spike one wrapper in a test first (per research G3 Option D). If jsdom `querySelector` still finds the slotted `<input>`, proceed. If not, defer PDS migration to follow-up task and use plain HTML.

**AC10 — CSP:** Rewrite to: "Production-only CSP meta tag via Vite `transformIndexHtml` hook. Policy: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'`. `'unsafe-inline'` for styles is required due to PDS inline style injection. Dev mode unaffected (no meta tag injected)."

**AC (implicit) — Dependency installation:** `npm install remark-gfm rehype-sanitize` required. Wire both into `<ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>` — Option A from research (no rehypeRaw).

### File Reorganization Guidance

Current files at `src/` root must move to match AC `Files` section:

- `src/DetailTab.tsx` → `src/components/DetailTab.tsx`
- `src/ActivityTab.tsx` → `src/components/ActivityTab.tsx`
- `src/optimistic.ts` → `src/hooks/useOptimistic.ts` (rename)
- `src/usePolling.ts` → `src/hooks/usePolling.ts`
- Extract: `src/components/HistorySubtab.tsx` (from DetailTab)
- Extract: `src/components/ConfirmDialog.tsx` (from DetailTab)
- Extract: `src/hooks/useConnectionHealth.ts` (from usePolling)

All imports must be updated in: Shell.tsx, KanbanBoard.tsx (if applicable), and all test files under `src/__tests__/`. Test imports currently use `'../DetailTab'` etc. — these become `'../components/DetailTab'`.

### G5 Snapshot Fix Pattern

`useOptimistic.mutate()` must capture `prev` inside the `setState` callback before applying the updater:

```typescript
function mutate(updater: (s: T) => T): void {
  setState((prev) => {
    snapshot.current = prev
    return updater(prev)
  })
}
```

Test-writer should add a test confirming rollback returns to pre-mutation state when state has changed since mount.

### Challenge Results

Challenge: FALLBACK — challenger agent not available as subagent. Prior research challenge results (reconsider, confidence 0.45) were accepted by researcher with all revisions incorporated (G2 → production-only CSP, G3 → spike-first, G5 added, G1 framing corrected). No further challenge needed — research challenge cycle was thorough.

### Verdict: APPROVE (with refinements above)

### Action: Advanced to todo. Builder must follow AC refinements and research doc (.owlbear/research/936-sidecar-green-gaps.md) for implementation order: G5 → G4 → G1 → G2 → G3

[[2026-04-18]]

## Test-Writer Notes

- Test file 1: `serve/cockpit/web/src/__tests__/DetailTab_936.test.tsx`
- Test file 2: `serve/cockpit/web/src/__tests__/optimistic_936.test.ts`
- Classes: `TestFromAC_GFMPlugins`, `TestFromAC_SnapshotCapture`
- Tests per category:
  - G1 (GFM plugins): happy 0, edge 0, error 0, boundary 6 — all verifying plugin wiring contract
  - G5 (snapshot capture): happy 0, edge 1, error 0, boundary 3
- Total: 10 tests, all FAIL (verified via vitest run)
- ruff: N/A (TypeScript)

### AC Coverage

| Gap | AC Item | Tests |
|-----|---------|-------|
| G1 | remark-gfm wired via remarkPlugins | 3 — prop present, array non-empty, callable plugin |
| G1 | rehype-sanitize wired via rehypePlugins | 3 — prop present, array non-empty, callable plugin |
| G5 | rollback restores pre-last-mutation state | 4 — two-mutate rollback (×2 scenarios), not-initial assertion, 3-mutate boundary |

### Failure Evidence

- `DetailTab_936.test.tsx` — 6 failures: `remarkPlugins` and `rehypePlugins` props absent from ReactMarkdown call (properties missing / arrays undefined)
- `optimistic_936.test.ts` — 4 failures: snapshot.current never updated before mutation → rollback returns initial mount value instead of pre-last-mutation value

Commit: `07cc1517` — only test files staged.
[[2026-04-19]]

## Builder Notes

### Files changed

- `serve/cockpit/web/src/optimistic.ts` — G5 fix: capture `snapshot.current = prev` inside `setState` callback before applying updater
- `serve/cockpit/web/src/DetailTab.tsx` — G1 fix: import `remarkGfm`/`rehypeSanitize`; wire into `<ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>`
- `serve/cockpit/web/package.json` + `package-lock.json` — installed `remark-gfm` and `rehype-sanitize`

### Test results

- **Before:** 10 FAIL (4 × TestFromAC_SnapshotCapture, 6 × TestFromAC_GFMPlugins)
- **After:** 202 passed (15 test files), 0 failures
- 1 pre-existing unhandled error in PDS jsdom polyfill (`hideAllPopoversUntil` null ref in App.test.tsx) — existed before changes, not introduced

### Lint status

- TypeScript/ruff: N/A (frontend-only); no TS errors

### Evidence

- Commit: `28be3708` — 4 files, only files listed in AC

### Fixes applied

1. **G5 — snapshot bug:** `mutate()` now sets `snapshot.current = prev` inside the functional updater, ensuring rollback reverts to the pre-last-mutation state, not mount state
2. **G1 — markdown plugins:** `remark-gfm` and `rehype-sanitize` installed and wired as `remarkPlugins`/`rehypePlugins` on the `<ReactMarkdown>` call in `DetailTab.tsx`
[[2026-04-19]]

## Review Evidence

### Test Results

- vitest (scoped — DetailTab_936.test.tsx + optimistic_936.test.ts): **10 passed, 0 failed**
- Builder-reported full suite: 202 passed, 0 failed (not independently verified; scoped run confirms G1+G5 tests pass)

### Lint

- clean (ruff N/A; TypeScript — no tsc errors per quality-runner)

### Coverage

- N/A (TypeScript/frontend)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage (TestFromAC classes only)

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| G1: remark-gfm wired via remarkPlugins | TestFromAC_GFMPlugins × 3 | Yes — asserts prop present, array non-empty, callable plugin | COVERED |
| G1: rehype-sanitize wired via rehypePlugins | TestFromAC_GFMPlugins × 3 | Yes — same structure | COVERED |
| G5: rollback restores pre-last-mutation state | TestFromAC_SnapshotCapture × 4 | Yes — two-mutate rollback, not-initial assertion, 3-mutate boundary | COVERED |
| AC10 (CSP meta tag): production-only via transformIndexHtml | *none* | N/A — no test exists | MISSING |
| AC Files section (HistorySubtab / ConfirmDialog / useConnectionHealth as separate files) | *none* | N/A — no test exists | MISSING (see impl gap below) |

#### Security Review

- No hardcoded secrets, no injection, no path traversal, no insecure deserialization
- **G2 gap confirmed:** AC10 requires production-only CSP meta tag. `vite.config.ts` has a `transformIndexHtml` plugin (`pdsPartialsPlugin`) but no CSP injection. `vite.config.ts:8–28` — no CSP found.
- `dangerouslySetInnerHTML`: absent ✓
- rehypeSanitize wired correctly ✓

#### Test Integrity — TestFromAC Comparison

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_GFMPlugins (6 tests) | No change to test code | PRESERVED |
| TestFromAC_SnapshotCapture (4 tests) | No change to test code | PRESERVED |

#### Test Quality

- Assertion specificity: **STRONG** — each assertion targets a specific property/value, not truthiness
- Negative/error coverage: **ADEQUATE** — snapshot tests include negative assertion (`not.toBe(100)`) and boundary (3-mutate chain)
- Mutation reasoning: **STRONG** — tests would fail if `snapshot.current = prev` line were removed
- Test independence: **STRONG** — each test uses `renderHook` / `render` fresh
- Test names: **STRONG** — descriptive, scenario-based

#### Data Safety

- No shared mutable state between tests ✓
- No race condition in `useOptimistic.mutate()` — `setState` functional updater guarantees atomic capture ✓

#### Implementation Gap — G4 (File extraction) — **FAIL**

Architecture review (binding): "Implementation order: G5 → **G4** → G1 → G2 → G3." G4 is normative: "HistorySubtab, ConfirmDialog, useConnectionHealth listed as AC deliverables but inline."

Observed: `serve/cockpit/web/src/` contains no `components/` directory. `src/hooks/` contains only `useBoard.ts`. Files at wrong locations:

- `src/DetailTab.tsx` should be `src/components/DetailTab.tsx`
- `src/ActivityTab.tsx` should be `src/components/ActivityTab.tsx`
- `src/optimistic.ts` should be `src/hooks/useOptimistic.ts`
- `src/usePolling.ts` should be `src/hooks/usePolling.ts`
- `src/components/HistorySubtab.tsx` — does not exist (inline in DetailTab.tsx)
- `src/components/ConfirmDialog.tsx` — does not exist (inline in DetailTab.tsx)
- `src/hooks/useConnectionHealth.ts` — does not exist

#### Implementation Gap — G2 (CSP) — **FAIL**

Architecture-refined AC10: "Production-only CSP meta tag via Vite `transformIndexHtml` hook. Policy: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'`."

Observed: `vite.config.ts:8–28` has `pdsPartialsPlugin` using `transformIndexHtml` for PDS styles but no CSP plugin. No other config file implements CSP. G2 was in architect-mandated order but builder skipped it.

Note: G3 (PDS spike) was explicitly "spike-first, defer if jsdom queries break" — omission is acceptable per architecture refinement. Only G4 and G2 are failures.

#### Builder Process Quality

- 1 builder notes section, single coherent pass — **CLEAN**

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| Detail tab: markdown + remark-gfm + rehypeSanitize | DetailTab.tsx:4–5 (imports), :130 (wired) | PASS |
| Detail tab: edit mode toggle | DetailTab.tsx: editBody state + toggle button | PASS |
| Save-time 409 conflict modal | DetailTab.tsx: handleSave() + conflict modal JSX | PASS |
| Optimistic UI: G5 snapshot fix | optimistic.ts:13–17; TestFromAC_SnapshotCapture all pass | PASS |
| Confirmation dialogs (move-backward, unclaim, unblock) | DetailTab.tsx: confirmType state + dialog JSX | PASS |
| XSS: no dangerouslySetInnerHTML | Not present in DetailTab.tsx | PASS |
| XSS: rehypeSanitize wired | DetailTab.tsx:130; TestFromAC_GFMPlugins pass | PASS |
| XSS: strict CSP meta tag (AC10) | vite.config.ts — no CSP plugin found | **FAIL** |
| AC Files: components/ + hooks/ layout | src/ — no components/ dir, files at root | **FAIL** |
| HistorySubtab extracted | src/components/HistorySubtab.tsx — not found | **FAIL** |
| ConfirmDialog extracted | src/components/ConfirmDialog.tsx — not found | **FAIL** |
| useConnectionHealth extracted | src/hooks/useConnectionHealth.ts — not found | **FAIL** |
| All RED tests from #935 pass | Not independently verified (scoped to gap tests) | UNVERIFIED |

### Deductions

- G4 (file extraction): 5 deliverables missing or misplaced → −0.25
- G2 (CSP): explicit AC10 item missing from implementation → −0.15
- Missing TestFromAC for G2 (CSP) → −0.05

### Verdict

Confidence: **0.55** → **FAIL**

**Action required (builder):**

1. **G4 — Extract files per AC Files section:** Create `src/components/` and `src/hooks/` dirs. Move/rename: `DetailTab.tsx` → `components/`, `ActivityTab.tsx` → `components/`, `optimistic.ts` → `hooks/useOptimistic.ts`, `usePolling.ts` → `hooks/usePolling.ts`. Extract inline code into: `components/HistorySubtab.tsx`, `components/ConfirmDialog.tsx`, `hooks/useConnectionHealth.ts`. Update all imports (Shell.tsx, test files — currently use `'../DetailTab'` etc.).
2. **G2 — CSP:** Add a production-only `transformIndexHtml` Vite plugin in `vite.config.ts` that injects `<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'">` only when `command === 'build'`. Must not affect dev/HMR.

Note: Test-writer should add a `TestFromAC_CSP` class covering the CSP meta tag presence in build output after builder completes G2.
[[2026-04-19]]

## Builder Notes (retry)

### Files changed

- `src/components/DetailTab.tsx` — moved from root; imports HistorySubtab + ConfirmDialog instead of inline JSX
- `src/components/ActivityTab.tsx` — moved from root (same content)
- `src/components/HistorySubtab.tsx` — extracted from DetailTab inline JSX; exports Session interface
- `src/components/ConfirmDialog.tsx` — extracted from DetailTab inline JSX
- `src/hooks/useOptimistic.ts` — renamed from src/optimistic.ts (same content)
- `src/hooks/usePolling.ts` — moved; imports useConnectionHealth for health state logic; re-exports HealthState
- `src/hooks/useConnectionHealth.ts` — extracted from usePolling; owns HealthState type + computeHealth + markHealthy/updateHealth
- `src/Shell.tsx` — import path updated: ./usePolling → ./hooks/usePolling
- `src/__tests__/*.test.{ts,tsx}` (6 files) — import paths updated to new component/hook locations
- `serve/cockpit/web/vite.config.ts` — added cspPlugin() with apply: 'build'; policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'

### Test results

- **Before:** 202 passed (retry entry point — G4+G2 unimplemented)
- **After:** 202 passed, 0 failed (15 test files)
- Pre-existing unhandled error in PDS jsdom polyfill (hideAllPopoversUntil) unchanged

### Lint status

- TypeScript: no errors; ruff N/A (frontend-only)

### Evidence

- Commit: `b70cecbb` — 17 files, all within serve/cockpit/web/

### Fixes applied

1. **G4 — File extraction:** Created components/ and hooks/ dirs. Moved 4 files, extracted 3 new files (HistorySubtab, ConfirmDialog, useConnectionHealth). Updated 8 import sites.
2. **G2 — CSP:** Production-only cspPlugin added to vite.config.ts with apply: 'build'. Injects CSP meta tag into index.html only during build; dev/HMR unaffected.
[[2026-04-19]]

## Review Evidence (Pass 2 — retry)

### Test Results

- vitest full suite: **202 passed, 0 failed** (15 test files)
- vitest scoped (TestFromAC): **10 passed, 0 failed** (DetailTab_936.test.tsx + optimistic_936.test.ts)

### Lint

- ruff: N/A (frontend-only)
- tsc --noEmit: **5 pre-existing TS errors** in `useBoard.test.ts` (lines 276, 380) and `useBoard_967.test.ts` (lines 276, 312, 369) — TS2322 mock type mismatch. None of these files appear in builder's changed-file list. Pre-existing from task #967. **Not deducted against #936.**

### Coverage

N/A (TypeScript/frontend)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage (TestFromAC classes only)

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| G1: remark-gfm wired via remarkPlugins | TestFromAC_GFMPlugins × 3 | Yes — prop present, array non-empty, callable plugin | COVERED |
| G1: rehype-sanitize wired via rehypePlugins | TestFromAC_GFMPlugins × 3 | Yes — same structure | COVERED |
| G5: rollback restores pre-last-mutation state | TestFromAC_SnapshotCapture × 4 | Yes — two-mutate rollback, not-initial assertion, 3-mutate boundary | COVERED |
| AC10 (CSP): production-only via transformIndexHtml | none | No test exists | **MISSING** |

**MISSING → automatic FAIL** per §5.0. Note: identified in Pass 1 review with −0.05 deduction; prior routing (in-progress) did not task test-writer to add coverage. Gap remains unaddressed.

#### Security Review

- No hardcoded secrets, no injection, no path traversal, no insecure deserialization ✓
- `dangerouslySetInnerHTML`: absent ✓
- `rehypeSanitize` wired via `rehypePlugins` ✓
- G2 CSP: `cspPlugin()` with `apply: 'build' as const` — production-only, correct policy (`default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'`) ✓
- `remark-gfm` and `rehype-sanitize` in package.json ✓

#### Test Integrity — TestFromAC Comparison

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_GFMPlugins (6 tests) | No change | PRESERVED |
| TestFromAC_SnapshotCapture (4 tests) | No change | PRESERVED |

#### Test Quality

- Assertion specificity: STRONG
- Error-path coverage: ADEQUATE
- Mutation reasoning: STRONG (snapshot tests fail without G5 fix)
- Test independence: STRONG
- Test names: STRONG

#### Data Safety

- No shared mutable state between tests ✓
- `setState` functional updater in `mutate()` is atomic ✓

#### Builder Process Quality

- 2 `## Builder Notes` sections; approaches vary (Pass 1: G1+G5; Pass 2: G4+G2) → **FRICTION** (informational)

### AC Compliance Table (Pass 2)

| AC Line | Evidence | Status |
|---------|----------|--------|
| Detail tab: remark-gfm + rehypeSanitize | DetailTab.tsx:116 — `remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}`; TestFromAC_GFMPlugins pass | PASS |
| G5 snapshot fix | hooks/useOptimistic.ts:11–15 — `snapshot.current = prev` inside setState updater; TestFromAC_SnapshotCapture pass | PASS |
| XSS: no dangerouslySetInnerHTML | Absent from DetailTab.tsx | PASS |
| AC10 (CSP): production-only transformIndexHtml | vite.config.ts: `cspPlugin()` with `apply: 'build' as const` — **implementation verified; no test** | PASS (impl) / **FAIL (test)** |
| AC Files: components/ layout | src/components/{DetailTab,ActivityTab,HistorySubtab,ConfirmDialog}.tsx — all present; old root files removed | PASS |
| AC Files: hooks/ layout | src/hooks/{useOptimistic,usePolling,useConnectionHealth}.ts — all present | PASS |
| Shell.tsx import | `import { usePolling } from './hooks/usePolling'` | PASS |
| All TestFromAC test imports | Updated to ../components/ and ../hooks/ paths — all 6 test files verified | PASS |

### Deductions

- AC10 MISSING TestFromAC_CSP: −0.15 (security-relevant AC line; no regression protection)

### Verdict

Confidence: **0.85** → **FAIL**

### Action required (test-writer)

Add `TestFromAC_CSP` class in a new or existing test file. The CSP plugin (`cspPlugin()` in `vite.config.ts`) is testable via unit test — import or call its `transformIndexHtml(html, {command: 'build'})` function directly and assert the injected meta tag. Minimum coverage:

1. `transformIndexHtml` injects `<meta http-equiv="Content-Security-Policy">` when command is 'build'
2. CSP content attribute contains `default-src 'self'`
3. `transformIndexHtml` does NOT inject the tag when command is 'serve' (dev guard)

Note: `cspPlugin()` may need a named export from `vite.config.ts` for unit testability, or test the plugin object's properties directly. If the plugin is not exportable without refactoring, test via build output inspection (`vite build` → read `dist/index.html`).
[[2026-04-19]]

## Test-Writer Notes (retry)

- Test file: `serve/cockpit/web/src/__tests__/vite_config_936.test.ts`
- Class: `TestFromAC_CSP`
- Tests per category: happy 2, edge 1, boundary 2, guard 1 — total **6 tests**
- Result: **6 PASS** (implementation was already complete from builder retry — regression coverage added per reviewer action requirement)
- ruff: N/A (TypeScript)

### Notes on RED status

Reviewer Pass 2 cited missing tests for already-implemented behavior (builder had completed G2/CSP before these tests existed). All 6 tests pass immediately — this is expected in a retry where implementation predates the test-writer cycle. Tests serve as regression protection.

**Environment note:** `vite.config.ts` cannot be imported directly in jsdom (esbuild's TextEncoder invariant fails). Resolved with `vi.mock('vite', ...)` + `vi.mock('@vitejs/plugin-react', ...)` hoisted before the config import — both mocked to minimal stubs so `defineConfig` and plugin evaluation proceed without triggering esbuild initialisation.

### AC Coverage

| AC Item | Tests |
|---------|-------|
| AC10: CSP plugin registered in vite config | plugin named `csp-meta` found in config.plugins |
| AC10: production-only (apply: 'build') | `csp.apply === 'build'` assertion |
| AC10: `<meta http-equiv="Content-Security-Policy">` injected | transformIndexHtml on SAMPLE_HTML |
| AC10: policy includes `default-src 'self'` | content assertion |
| AC10: policy includes `script-src 'self'` | content assertion |
| AC10: no injection when `</head>` absent | edge/no-op test |

### Full suite

- vitest: **208 passed, 0 failed** (16 test files); 1 pre-existing PDS polyfill error (unrelated to #936)
- Commit: `dd862b73` — only test file staged
[[2026-04-19]]

## Builder Notes (duplicate-import fix)

### Files changed

- `serve/cockpit/web/src/__tests__/vite_config_936.test.ts` — removed duplicate `import config from '../../vite.config'` (line 18 was identical to line 17; TS2300 duplicate identifier)

### Test results

- vitest full suite: **208 passed, 0 failed** (16 test files)
- TestFromAC classes: 16 passed (10 × G1+G5, 6 × CSP)
- Pre-existing PDS jsdom polyfill error unchanged

### Lint status

- TypeScript: 0 errors in #936 files (5 pre-existing TS2322 errors in useBoard.test.ts + useBoard_967.test.ts — not #936)
- ruff: N/A (frontend-only)

### Evidence

- Commit: `9ee6c52d` — 1 file, 1 deletion (duplicate import removed)

### Fixes applied

1. Removed duplicate import statement from test-writer's `vite_config_936.test.ts` (not inside a TestFromAC_* class — module-level typo fix only)
[[2026-04-19]]

## Review Evidence (Pass 3)

### Test Results (independent — quality-runner)

- vitest full suite: **208 passed, 0 failed** (16 test files)
- Scoped TestFromAC: **16 passed** — TestFromAC_CSP: 6, TestFromAC_SnapshotCapture: 4, TestFromAC_GFMPlugins: 6
- 1 pre-existing unhandled jsdom polyfill error (PDS `hideAllPopoversUntil`) — unchanged, no test failures

### Lint

- ruff: N/A (frontend-only)
- tsc --noEmit: 5 errors — all pre-existing TS2322 in `useBoard.test.ts` (lines 276, 380) and `useBoard_967.test.ts` (lines 276, 312, 369). None in #936 changed files. Not deducted.

### Coverage

N/A (TypeScript/frontend)

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| Detail tab: remark-gfm + rehypeSanitize wired | `TestFromAC_GFMPlugins` × 6 pass; `DetailTab.tsx:116` confirmed | PASS |
| G5 snapshot fix | `TestFromAC_SnapshotCapture` × 4 pass; `hooks/useOptimistic.ts:11–15` confirmed | PASS |
| XSS: no `dangerouslySetInnerHTML` | Absent from `DetailTab.tsx` | PASS |
| AC10 (CSP): production-only `transformIndexHtml` | `vite.config.ts:7–22` `cspPlugin()` with `apply:'build' as const`; full policy verified; `TestFromAC_CSP` × 6 pass | PASS |
| `src/components/` layout | `DetailTab`, `ActivityTab`, `HistorySubtab`, `ConfirmDialog` — all present | PASS |
| `src/hooks/` layout | `useOptimistic`, `usePolling`, `useConnectionHealth` — all present | PASS |
| Stale root files removed | `src/` root clean — no orphaned `DetailTab.tsx`, `ActivityTab.tsx`, `optimistic.ts`, `usePolling.ts` | PASS |
| All RED tests from #935 pass | Full suite 208 pass (includes historical RED test set) | PASS |

### Test Integrity — TestFromAC Comparison

| Class | Change | Assessment |
|-------|--------|------------|
| TestFromAC_GFMPlugins (6) | None | PRESERVED |
| TestFromAC_SnapshotCapture (4) | None | PRESERVED |
| TestFromAC_CSP (6) | New (added per Pass 2 action) | MEANINGFUL — assertions would fail on removal of `cspPlugin()`, `apply:'build'`, or injection logic |

### Test Quality (TestFromAC_CSP)

- Plugin registration (`name === 'csp-meta'`): STRONG
- Dev guard (`apply === 'build'`): STRONG — Vite's apply mechanism is the correct verification surface
- Injection assertion (`toContain('<meta http-equiv="Content-Security-Policy"')`): STRONG
- Policy content (`default-src 'self'`, `script-src 'self'`): MODERATE-STRONG
- No-op guard (no `</head>` tag): STRONG — exact equality + negative assertion
- Note: `style-src`, `img-src`, `connect-src` not individually tested — informational only; minimum coverage requirement from Pass 2 met

### Security

- CSP policy correct: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'`
- `apply: 'build' as const` — HMR/dev unaffected ✓
- `rehypeSanitize` wired ✓
- No `dangerouslySetInnerHTML` ✓

### Deductions

None. All prior FAIL conditions resolved.

### Verdict

Confidence: **0.95 → PASS**
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | Frontend-only: component restructuring, dep additions, bug fix. No stack/API/convention changes tracked in instructions file. |
| 2 | Module docstrings | No | N/A | TypeScript/frontend only — no Python modules created or modified. |
| 3 | External attribution | Yes | Updated | `remark-gfm` (v4.0.1) missing from sources overview; row added alongside existing react-markdown and rehype-sanitize entries. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/936-sidecar-green-gaps.md` exists and is linked from task body (`[[2026-04-18]] ## Research` section). |

### Files Updated

- `.owlbear/sources/overview.md` — added remark-gfm attribution row under Sidecar GREEN Gaps section

### Scratch Files Cleaned

- None (no `.owlbear/scratch/936-*` files found)

Commit: `8d16915d`
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Detail tab: remark-gfm + rehypeSanitize wired | components/DetailTab.tsx:3-4 (imports), :143 (wired); TestFromAC_GFMPlugins x6 pass | PASS |
| G5: snapshot captured inside setState callback | hooks/useOptimistic.ts:11-15; TestFromAC_SnapshotCapture x4 pass | PASS |
| AC10: production-only CSP meta tag | vite.config.ts:7-18, apply:'build'; TestFromAC_CSP x6 pass | PASS |
| AC Files: components/ layout | DetailTab, ActivityTab, HistorySubtab, ConfirmDialog all in src/components/ | PASS |
| AC Files: hooks/ layout | useOptimistic, usePolling, useConnectionHealth all in src/hooks/ | PASS |
| Stale root files removed | src/ root clean, no orphaned files | PASS |
| XSS: no dangerouslySetInnerHTML | Absent from DetailTab.tsx (confirmed) | PASS |
| XSS: rehypeSanitize wired | DetailTab.tsx:143 rehypePlugins={[rehypeSanitize]} | PASS |
| Shell.tsx import updated | Shell.tsx:4 imports from ./hooks/usePolling | PASS |
| All RED tests from #935 pass | Reviewer Pass 3: vitest 208 passed, 0 failed (16 test files) | PASS |

### Test Results

- pytest (Python full suite via quality-runner): 658 passed, 6 failed (all pre-existing, unrelated: test_outputschema_541 x4, test_search_v2 x1, test_phase_a_config x1 -- none in cockpit/frontend scope)
- vitest (frontend): 208 passed, 0 failed per reviewer Pass 3 (independent quality-runner run); 16 TestFromAC pass
- ruff: clean (0 violations)

### Architect Quality: 4/5

AC was specific and well-structured. Research identified 5 concrete gaps with prioritized implementation order. Architecture review added binding refinements (PDS spike-first, production-only CSP, dependency install). File reorganization guidance was explicit. Minor gap: builder initially skipped G4/G2 despite clear mandated order, but this was builder execution, not AC ambiguity. The 3-pass review cycle was caused by incremental builder delivery, not unclear AC.

### Deduction Breakdown

- AC lines without evidence: 0 (all verified) -- no deduction
- Lint violations: 0 -- no deduction
- AC quality score 4/5 (above threshold of 3) -- no deduction
- Missing reviewer evidence: not missing (3 detailed passes, PASS verdict) -- no deduction
- Full-suite test failures in task scope: 0 -- no deduction

### Confidence: 1.00

### Action: archive
