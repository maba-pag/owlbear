# Theme Bootstrap Script + useTheme Hook — Implementation Research

> **Owning task:** #1545 — P2-02: impl — theme bootstrap script + useTheme hook
> **Date:** 2026-05-14 **Status:** Complete

## 1. Context and Question

Task #1545 requires implementing: (AC-1) a synchronous `<script>` in `index.html` preventing flash-of-wrong-theme, (AC-2) a `useTheme` hook with `{ theme, toggle, isDark }`, and (AC-3) a 3-state toggle with localStorage persistence.

**Critical finding:** AC-2 and AC-3 are already satisfied by the existing `useTheme` hook at `serve/cockpit/web/src/hooks/useTheme.ts`, implemented in dependency task #1537 (archived, confidence 0.97). The hook exports `applyTheme()` and `useTheme()`, both passing 15 tests. The builder's primary deliverable is AC-1: the inline bootstrap script in `index.html`.

**Current state:** `index.html` has no `<script>` in `<head>` — only a `<div id="root">` and a `type="module"` entry point. The `@media (prefers-color-scheme: dark)` CSS fallback in `tokens.css` (#1543) prevents flash for users without stored preferences, but users with a stored dark preference on a light-OS system will see a flash because the CSS fallback targets `:root:not([data-theme])`.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Static Signal — Dark Mode Without the Flash | staticsignal.io/posts/dark-mode-without-the-flash/ | 0.95 — canonical pattern: inline blocking script in `<head>`, 3 pieces (vars + script + toggle) |
| dev.to (gaisdav) — Prevent Theme Flash in React | dev.to/gaisdav/how-to-prevent-theme-flash-in-a-react-instant-dark-mode-switching-o20 | 0.90 — implementation in Vite/React, localStorage + matchMedia + data-theme |
| next-themes script.ts | github.com/pacocoursey/next-themes/blob/main/next-themes/src/script.ts | 0.85 — production bootstrap: localStorage → validate → system fallback → updateDOM |
| next-themes index.tsx (ThemeScript) | github.com/pacocoursey/next-themes/blob/main/next-themes/src/index.tsx#L165-L215 | 0.80 — injection mechanism: `dangerouslySetInnerHTML` with IIFE, nonce support |
| Existing useTheme hook | serve/cockpit/web/src/hooks/useTheme.ts | 1.00 — already implements `applyTheme()` + `useTheme()` per AC-2/AC-3 |
| Existing tokens.css | serve/cockpit/web/src/tokens.css | 1.00 — `[data-theme="dark"]` + `@media` fallback already in place |

## 3. Analysis

### 3.1 Bootstrap Script Approach

| Option | Description | FOUC Prevention | Deps | Duplication | KISS |
|--------|-------------|-----------------|------|-------------|------|
| **A: Inline IIFE in `<head>`** | ~10-line plain `<script>` reading localStorage + matchMedia | Yes — runs before paint | 0 | ~10 LOC (intentional) | High |
| B: Vite plugin injection | Build-time script injection from shared source | Yes | 1+ | 0 | Low |
| C: Call in `main.tsx` | `applyTheme()` at top of module entry | **No** — `type="module"` is deferred | 0 | 0 | — |
| D: Separate blocking script file | `<script src="bootstrap.js">` in `<head>` | Depends on network | 0 | 0 | Medium |

**Option C is fundamentally flawed.** Per HTML spec, `type="module"` scripts are always deferred — the browser may paint before they execute. Every source confirms this is the root cause of FOUC.

**Option D adds network latency** and Vite build config complexity (separate entry point). Not worth it for 10 lines.

**Option B is over-engineering** — a Vite plugin to avoid duplicating 10 lines violates YAGNI.

### 3.2 Duplication Concern

The inline script duplicates logic from `applyTheme()` in `useTheme.ts`. This is **intentional and accepted** by all sources:

- Static Signal: "the inline script... is a literal `<script>` in your template"
- dev.to: "A quick way to prevent the theme flicker is to add a simple inline script"
- next-themes: ships a separate `script.ts` that duplicates resolution logic from the provider

The inline script is a frozen, minimal subset. It reads, validates, and sets. The hook manages lifecycle, state, and toggle. Different concerns, different execution contexts.

### 3.3 Script Placement

All sources agree: the script must be **inline, synchronous, in `<head>`, before stylesheets**.

Current `index.html` structure has no stylesheets in `<head>` (Vite injects them). Placing the script as the first child of `<head>` (after `<meta>` tags) ensures it runs before any Vite-injected CSS.

### 3.4 Implementation Scope

| AC | Status | Builder Action |
|----|--------|----------------|
| AC-1 | Not started | Add inline `<script>` to `index.html` |
| AC-2 | **Complete** (#1537) | Verify existing `useTheme` hook meets AC |
| AC-3 | **Complete** (#1537) | Verify existing toggle cycle meets AC |

The builder's deliverable is essentially a **single-file edit** to `index.html` plus verification.

### 3.5 Script Content

The inline script should mirror `applyTheme()` logic:

```html
<script>
  (function() {
    try {
      var s = localStorage.getItem('owlbear-theme');
      var v = s === 'dark' || s === 'light' ? s
            : window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      document.documentElement.dataset.theme = v;
    } catch (e) {}
  })();
</script>
```

Key properties: IIFE (no globals), `try/catch` (Safari private mode safety), validates against `['dark', 'light']`, falls back to `matchMedia`, sets `dataset.theme`.

## 4. Recommendation

**Proceed with Option A: inline IIFE in `<head>`** (confidence: 0.90)

- Proven pattern across next-themes (7.5K stars), multiple authoritative articles
- Zero dependencies, zero build config changes
- ~10 LOC duplication is intentional and accepted industry-wide
- Single-file edit to `index.html`; existing hook code unchanged
- Existing 15 tests in `theme_1537.test.tsx` cover AC-2/AC-3; RED tests for AC-1 inline script already exist (bootstrap function tests validate the same logic)

**Risk:** The inline script and `applyTheme()` could diverge. Mitigation: the logic is 3 lines (read → validate → set) — drift is unlikely and easily caught by existing tests.

**Challenge: FALLBACK — trivial implementation with unanimous source consensus; no novel architectural decisions warranting challenger dispatch.**

## 5. Follow-up Tasks

No additional follow-up tasks needed. The existing task decomposition under #1534 covers all downstream work:
- #1548 (theme toggle UI) depends on #1545
- #1553 (PDS dark-mode verification) depends on #1545
- Tests already exist in `theme_1537.test.tsx`
