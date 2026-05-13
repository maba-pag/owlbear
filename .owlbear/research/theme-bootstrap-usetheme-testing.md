# Theme Bootstrap + useTheme Hook Testing Strategy

> **Owning task:** #1537 — P2-01: test — theme bootstrap script + useTheme hook
> **Date:** 2026-05-13 **Status:** Complete

## 1. Context and Question

Task #1537 requires Vitest tests for three behaviors: (AC-1) synchronous bootstrap script setting `data-theme` from localStorage, (AC-2) `useTheme()` hook returning `{ theme, toggle, isDark }`, and (AC-3) OS preference fallback via `prefers-color-scheme`. The implementation doesn't exist yet — tests are written first (TDD RED).

**Current codebase state:** `tokens.css` uses `--pds-theme-light-*` naming (light only). No `useTheme` hook, no bootstrap script in `index.html`. All component CSS hard-references light tokens.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| next-themes test suite | github.com/pacocoursey/next-themes (\_\_tests\_\_/index.test.tsx) | 0.95 — proven patterns for localStorage mock, matchMedia mock, data-theme assertion |
| next-themes inline script | github.com/pacocoursey/next-themes (src/script.ts) | 0.90 — canonical bootstrap pattern: read localStorage → validate → fallback to OS pref → set attribute |
| tanstack-themes FOUC prevention | deepwiki.com/juliusmarminge/tanstack-themes/3.3 | 0.85 — architecture for synchronous script injection, mode resolution logic |
| vitest-matchmedia-mock | npmjs.com/package/vitest-matchmedia-mock | 0.60 — alternative matchMedia mock library; 14.8K weekly downloads |
| Mantine Vitest setup | mantine.dev/guides/vitest/ | 0.70 — matchMedia mock pattern in vitest.setup |
| Existing Cockpit tests | serve/cockpit/web/src/\_\_tests\_\_/*.test.ts | 0.95 — local conventions: renderHook, vi.fn, vi.stubGlobal |

## 3. Analysis

### 3.1 matchMedia Mock Strategy

| Approach | Deps | Change events | Complexity | KISS alignment |
|----------|------|---------------|------------|----------------|
| **A: Manual mock** (Object.defineProperty) | 0 | Manual dispatch | Low | High |
| **B: vitest-matchmedia-mock** | 1 | Built-in | Low | Medium |

**Recommendation: Option A (manual mock)** — confidence 0.85. next-themes uses this pattern at scale (7.5K stars). No added dependency. Aligns with existing Cockpit test patterns (`vi.fn()`, `vi.stubGlobal()`). The brief specifies no React Context for theme, so change event simulation is minimal.

### 3.2 Bootstrap Script Testability

| Approach | Tests what | Isolation | Matches brief |
|----------|-----------|-----------|---------------|
| **A: Test extracted function** | Pure logic: localStorage → validate → apply attribute | Full | Yes |
| **B: Test via DOM script injection** | E2E-style script execution in jsdom | Partial | Over-engineers |

**Recommendation: Option A** — confidence 0.90. The brief says "synchronous script in `index.html`". The test-writer should test the bootstrap logic as an exported function. The "runs before React" timing guarantee is architectural and verified by Playwright E2E, not Vitest unit tests.

### 3.3 useTheme Hook Test Pattern

| Concern | Pattern | Prior art |
|---------|---------|-----------|
| Hook rendering | `renderHook(() => useTheme())` | All existing Cockpit hook tests |
| DOM attribute setup | `document.documentElement.setAttribute('data-theme', 'dark')` before render | next-themes tests |
| Toggle assertion | Call `result.current.toggle()` via `act()` → re-read attribute | next-themes `setTheme` tests |
| isDark derivation | Assert `result.current.isDark === true` when `data-theme === 'dark'` | Trivial boolean |

**Key design point:** Brief says "No React Context — theme is a DOM attribute, CSS cascade propagates it. Zero re-renders on theme change." The hook should use `useSyncExternalStore` or a MutationObserver to subscribe to the DOM attribute. Tests should verify both read and write.

### 3.4 localStorage Handling

jsdom provides a working `localStorage`. Tests can use it directly or spy on it:

- **Read:** `localStorage.setItem('owlbear-theme', 'dark')` before calling bootstrap → assert attribute
- **Clear:** `localStorage.clear()` in `afterEach` cleanup
- **Invalid values:** `localStorage.setItem('owlbear-theme', 'garbage')` → assert fallback

No custom mock needed — jsdom's built-in localStorage suffices. Add `vi.spyOn(Storage.prototype, 'getItem')` only if AC requires verifying the call was made.

## 4. Recommendation

**Implementation approach (confidence: 0.87):**

1. **AC-1 tests:** Import bootstrap function → set localStorage → call it → assert `document.documentElement.dataset.theme`. Test cases: valid "dark", valid "light", localStorage pre-set.
2. **AC-2 tests:** `renderHook(() => useTheme())` → assert `{ theme, toggle, isDark }` shape. Set attribute to "dark" → assert isDark. Call toggle → assert attribute flips.
3. **AC-3 tests:** Mock `window.matchMedia` via `Object.defineProperty` → clear localStorage → call bootstrap → assert falls back to OS preference. Test both dark and light OS preferences.

**No new npm dependencies.** All patterns use existing `@testing-library/react` + `vitest` + jsdom.

**Challenge: proceed — confidence in original: 0.87.** The testing patterns are well-established across next-themes (7.5K stars) and tanstack-themes. The Cockpit codebase already uses `renderHook` extensively. No novel techniques required.

## 5. Follow-up Tasks

- Task remains at research → advance to backlog for test-writer pickup.
- No separate follow-up tasks needed — AC is well-scoped for a single test-writer pass.
