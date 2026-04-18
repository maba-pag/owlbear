# Sidecar GREEN — Remaining AC Gaps

> **Owning task:** #936 — P2-07: GREEN — Sidecar (Detail + Activity tabs) + polling + optimistic UI
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Task #936's core functionality was already implemented under #935 commits. All 66 RED tests pass. Five AC items have gaps between the passing tests and the full AC requirements. This research identifies those gaps, assesses risks, and recommends implementation approaches.

## 2. Sources Studied

| # | Source | Relevance | What was used |
|---|--------|-----------|---------------|
| S1 | react-markdown npm (v10.1.0) | 0.95 | Safe by default (no dSIH), HTML in markdown escaped to text nodes unless rehypeRaw enabled |
| S2 | rehype-sanitize npm (v6.0.0) | 0.90 | Only sanitizes HTML in hast tree; without rehypeRaw, react-markdown produces no HTML nodes to sanitize |
| S3 | PDS docs (v3.34.0) — form wrappers | 0.85 | `p-text-field-wrapper` uses slotted native `<input>` child; query depends on light vs shadow DOM |
| S4 | Vite HMR architecture | 0.90 | Dev server injects inline `<script type="module">` for HMR; static `script-src 'self'` CSP blocks it |
| S5 | Existing DetailTab.test.tsx | 1.0 | react-markdown fully mocked; remark-gfm/rehype-sanitize never exercised by existing tests |
| S6 | Existing optimistic.ts | 1.0 | snapshot.current = initial at mount; never updated before mutation — rollback reverts to mount state |
| S7 | `h-frontend-conventions` skill | 0.85 | "Do not duplicate PDS functionality with custom components" — mandates PDS form controls |

## 3. Analysis

### 3.1 Gap Assessment

| # | AC Item | Current State | Gap | Tier |
|---|---------|---------------|-----|------|
| G1 | remark-gfm + rehypeSanitize | Only react-markdown installed | Missing deps + wiring | T1 |
| G2 | Strict CSP meta tag | No CSP in index.html | Missing; conflicts with Vite dev mode | T1 |
| G3 | PDS form components | Plain HTML controls | Design system non-compliance | T1 |
| G4 | File extraction (HistorySubtab, ConfirmDialog, useConnectionHealth) | Inline in DetailTab / usePolling | AC lists as separate file deliverables | T1 |
| G5 | useOptimistic snapshot bug | snapshot captures mount state only | Rollback after server update reverts to stale initial | T1 |

### 3.2 G1: remark-gfm + rehype-sanitize

react-markdown v10 escapes HTML by default — it doesn't use dangerouslySetInnerHTML. rehype-sanitize without rehypeRaw is effectively a no-op because no HTML nodes exist in the hast tree to sanitize. However, the AC explicitly requires both. Install for compliance; do not frame as security fix.

remark-gfm adds real value: task bodies use GFM tables, strikethrough, and task lists. Without it, these render as plain text.

**Risk:** Existing tests mock react-markdown entirely (test stub renders children as plain text). New tests needed to verify GFM rendering and confirm sanitize doesn't strip legitimate markup.

| Option | Approach | Risk |
|--------|----------|------|
| A. Install both, default schema | `npm install remark-gfm rehype-sanitize`; add to `<ReactMarkdown>` props | Low — no-op sanitize, GFM adds functionality |
| B. Install both + rehypeRaw | Enables HTML-in-markdown; sanitize becomes meaningful | Medium — expands attack surface, needs careful schema |
| C. Install remark-gfm only, skip rehype-sanitize | GFM value without cosmetic compliance | **Violates AC** |

**Recommendation: Option A** (confidence: 0.85). AC compliance + GFM functionality. rehypeRaw not needed (task bodies are agent-written markdown, not user HTML).

### 3.3 G2: CSP Meta Tag

The AC requires a "strict CSP meta tag." Three conflicts:

1. **Vite dev mode** injects inline `<script type="module">` for HMR — blocked by `script-src 'self'`
2. **PDS** injects inline `<style>` via `pdsPartialsPlugin` at build time — blocked without `'unsafe-inline'` for styles
3. `'unsafe-inline'` for styles contradicts "strict CSP" (per Google CSP Evaluator)

| Option | Approach | Dev mode | Strictness |
|--------|----------|----------|------------|
| A. Static meta tag, permissive | `script-src 'self' 'unsafe-inline'` | Works | Weak |
| B. Vite plugin (vite-plugin-csp) | Nonce-based injection per build | Automatic | Strong |
| C. Production-only meta tag | Injected by Vite build, absent in dev | Dev unaffected | Strong for prod |
| D. HTTP header via FastAPI | Backend serves CSP header | Dev unaffected | Strong for prod |

**Recommendation: Option C** (confidence: 0.75). Add CSP meta tag via Vite's `transformIndexHtml` hook — present only in production builds. Policy: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'`. `'unsafe-inline'` for styles is unavoidable due to PDS inline style injection. Document the trade-off.

### 3.4 G3: PDS Form Components

PDS 3.34 wrapper components (`p-text-field-wrapper`, `p-select-wrapper`) expect a native `<input>` as a slotted child. In jsdom (Vitest test env), shadow DOM behavior is incomplete — `container.querySelector('input[data-field="title"]')` may fail if the input moves inside shadow DOM.

| Option | Approach | Test breakage risk |
|--------|----------|--------------------|
| A. Full PDS migration | Replace all HTML controls with PDS wrappers | High — shadow DOM query issues in jsdom |
| B. PDS wrappers with explicit test updates | Migrate + update test selectors | Medium — significant test churn |
| C. Defer PDS migration, document as tech debt | Plain HTML stays, add task for PDS polish | Low — tests unchanged |
| D. Verify PDS slot behavior first, then decide | Spike: render one PDS wrapper in test, check querySelector | Minimal |

**Recommendation: Option D then A or C** (confidence: 0.70). The builder should spike one PDS wrapper component in a test to verify jsdom queryability before committing to full migration. If slots are queryable, proceed with A. If not, document as tech debt (C) and create a follow-up task.

### 3.5 G4: File Extraction

AC lists these as explicit file deliverables:
- `src/components/HistorySubtab.tsx` — currently inline in DetailTab
- `src/components/ConfirmDialog.tsx` — currently inline in DetailTab
- `src/hooks/useConnectionHealth.ts` — currently merged into usePolling

Import paths change for all consuming components and test files (~12+ files). This is mechanical refactoring but normative per AC.

**Recommendation:** Extract during GREEN phase. Update imports in all tests. Confidence: 0.90.

### 3.6 G5: useOptimistic Snapshot Bug

`snapshot.current` is set to `initial` at mount and never updated. If server data arrives via polling between mount and mutation, rollback restores the stale initial state, not the last-known-good state. Fix: capture current state before applying mutation.

```typescript
function mutate(updater: (s: T) => T): void {
  setState((prev) => {
    snapshot.current = prev  // capture pre-mutation state
    return updater(prev)
  })
}
```

**Recommendation:** Fix in GREEN phase. Add a test: mutate after state update → rollback → verify rollback to pre-mutation (not initial) state. Confidence: 0.90.

## 4. Recommendation

Close all 5 gaps in priority order: G5 (bug fix) → G4 (file extraction) → G1 (remark-gfm + rehype-sanitize) → G2 (CSP) → G3 (PDS spike). All T1 — no decision requests needed.

**Overall confidence: 0.75**

Challenge: reconsider — confidence in original: 0.45. Revised based on: C1 (rehype-sanitize no-op framing), C2 (CSP/Vite conflict), C3 (PDS shadow DOM risk), C5 (snapshot bug). Accepted all challenges; revised recommendations for G2 and G3.

## 5. Follow-up Tasks

No new tasks needed — #936 itself covers all gaps. The builder uses this research to guide implementation within #936's scope.
