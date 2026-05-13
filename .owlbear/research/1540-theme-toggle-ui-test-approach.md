# Theme Toggle UI: Status Bar Button — Test Approach

> **Owning task:** #1540 — P3-05: test — theme toggle UI: status bar button
> **Date:** 2026-05-13 **Status:** Complete

## 1. Context and Question

Task #1540 requires Vitest tests for a ThemeToggle button component placed in the Shell status bar (right side). The tests cover: (AC-1) button renders in the status bar area, (AC-2) clicking invokes `useTheme().toggle` to cycle theme, (AC-3) button label/icon reflects current theme state (light/dark/auto). The component and `useTheme` hook don't exist yet — tests are written first (TDD RED).

**Current codebase state:** The status bar is a `display: flex` header (`shell__status-bar`) in `Shell.tsx` with health indicators, cleanup panel, and DR indicator. No theme toggle exists. No `useTheme` hook exists (researched in #1537, implementation pending in #1545).

**Dependency note:** The `useTheme` hook is tested separately in #1537 and implemented in #1545. This task tests only the ThemeToggle UI component, mocking the hook.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| OneUptime — Unit Test React with Vitest | oneuptime.com/blog/post/2026-01-15-unit-test-react-vitest-testing-library | 0.90 — ThemeToggle test example: click toggle, assert text reflects state |
| next-themes issue #21 — testing implementations | github.com/pacocoursey/next-themes/issues/21 | 0.85 — ThemeSpy pattern, fireEvent on theme selector, data-testid convention |
| Stack Overflow — test theme toggler with RTL | stackoverflow.com/questions/72561602 | 0.75 — userEvent.click toggle, assert style/text change |
| Existing Cockpit vi.mock patterns | serve/cockpit/web/src/__tests__/ActivityTab.sse-refetch.test.tsx | 0.95 — local convention: vi.mock hook module, vi.mocked() assertions |
| #1537 research doc | .owlbear/research/theme-bootstrap-usetheme-testing.md | 0.95 — useTheme API shape: `{ theme, toggle, isDark }`, no React Context |
| Brief D12 | .owlbear/briefs/draft-board-visual-design/brief.md | 1.00 — toggle in status bar right side, cycles light/dark/auto |

## 3. Analysis

### 3.1 Hook Mocking Strategy

| Approach | Isolation | Matches codebase | Complexity |
|----------|-----------|-------------------|------------|
| **A: vi.mock('../hooks/useTheme')** | Full — tests component in isolation | Yes — ActivityTab.sse-refetch uses identical pattern | Low |
| **B: Render with real useTheme + DOM setup** | Partial — couples to hook behavior | No — violates scope boundary ("Out: useTheme hook") | High |

**Recommendation: Option A** — confidence 0.92. The codebase already uses `vi.mock` for hook modules extensively. The task explicitly scopes out the hook. Mock `useTheme` to return `{ theme, toggle: vi.fn(), isDark }` and vary `theme` per test case.

### 3.2 AC-1: Status Bar Placement

jsdom cannot verify visual layout (CSS flex positioning). The test should verify:
- Button renders with `data-testid="theme-toggle"` (or `role="button"` query)
- Component is designed to be placed in the status bar — actual placement is a Shell integration concern

Testing the button exists and has correct attributes is the appropriate unit test boundary. Visual positioning is verified by the migration grep gate (#1552) or E2E tests.

### 3.3 AC-2: Click → Toggle

| Pattern | Source | Approach |
|---------|--------|----------|
| userEvent.click | OneUptime guide, RTL best practices | `const user = userEvent.setup(); await user.click(button); expect(mockToggle).toHaveBeenCalledTimes(1)` |
| fireEvent.click | next-themes issue #21 | Simpler but less realistic |

**Recommendation: userEvent** — matches RTL best practices and provides more realistic interaction simulation.

### 3.4 AC-3: Theme State Reflection

Brief specifies 3 states: light, dark, auto. Test each by varying the mock return:

| Mock return | Expected label/content |
|-------------|----------------------|
| `{ theme: 'light', toggle: fn, isDark: false }` | Indicates light mode |
| `{ theme: 'dark', toggle: fn, isDark: true }` | Indicates dark mode |
| `{ theme: 'auto', toggle: fn, isDark: false }` | Indicates auto mode |

Whether the component uses text labels, icons, or aria-labels is an implementation detail. Tests should assert that the rendered content differs per theme state (e.g., `getByRole('button', { name: /light/i })` or `data-theme="light"` attribute).

### 3.5 PDS Provider Wrapping

Existing component tests wrap in `<PorscheDesignSystemProvider>`. ThemeToggle tests should follow this convention. Render helper:

```tsx
function renderToggle(themeOverrides?: Partial<UseThemeReturn>) {
  const defaults = { theme: 'light', toggle: vi.fn(), isDark: false }
  vi.mocked(useTheme).mockReturnValue({ ...defaults, ...themeOverrides })
  return render(
    <PorscheDesignSystemProvider>
      <ThemeToggle />
    </PorscheDesignSystemProvider>,
  )
}
```

## 4. Recommendation

**Implementation approach (confidence: 0.92):**

1. **AC-1 tests:** Mock `useTheme`, render `<ThemeToggle />` in PDS provider, assert button element exists via `getByRole('button')` or `data-testid="theme-toggle"`.
2. **AC-2 tests:** Set up `userEvent`, click the button, assert `mockToggle` called once.
3. **AC-3 tests:** Parameterize across 3 theme states (light/dark/auto), assert button content/label differs per state.

**No new npm dependencies.** All patterns use existing `@testing-library/react` + `vitest` + `userEvent`.

**Expected test file:** `serve/cockpit/web/src/__tests__/ThemeToggle.test.tsx` (~60-80 lines).

**Challenge: skipped** — trivial test scaffolding for a button component with well-established patterns. No design trade-offs or architecture decisions. All 3 ACs map 1:1 to standard RTL patterns already in use across the codebase.

## 5. Follow-up Tasks

- No additional follow-up tasks needed. Task #1540 is well-scoped for a single test-writer pass.
- Implementation task #1548 (P3-06) already exists and depends on this task + #1545.
