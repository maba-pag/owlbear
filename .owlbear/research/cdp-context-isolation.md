# CDP Browser Context Isolation

> **Owning task:** #495 — Isolate browser context in CDP mode
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

SEC-07 from `docs/security-audit.md`: `BrowserManager._enter_cdp()` uses `self._browser.contexts[0]` — the user's default browser context — giving OwlBear full access to authenticated sessions, cookies, and localStorage. Can we create an isolated context via `browser.new_context()` on a CDP-connected browser, and what are the trade-offs?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Playwright `Browser.new_context()` API | https://playwright.dev/python/docs/api/class-browser#browser-new-context | .95 |
| 2 | CDP `Target.createBrowserContext` | https://chromedevtools.github.io/devtools-protocol/tot/Target/#method-createBrowserContext | .90 |
| 3 | Playwright `connect_over_cdp` API | https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp | .85 |
| 4 | Playwright `Browser.close()` API | https://playwright.dev/python/docs/api/class-browser#browser-close | .70 |

## 3. Analysis

### 3.1 Feasibility: `browser.new_context()` on CDP connections

| Criterion | Evidence | Source |
|-----------|----------|--------|
| API support | `browser.new_context()` documented on `Browser` class, no CDP exclusion noted | [1] |
| Protocol mechanism | CDP `Target.createBrowserContext` — "Creates a new empty BrowserContext. Similar to an incognito profile but you can have more than one." | [2] |
| Cleanup semantics | `browser.close()` on connected browser "clears all created contexts belonging to this browser and disconnects" — confirms created contexts are expected | [4] |
| Fidelity caveat | `connect_over_cdp` is "significantly lower fidelity" than Playwright protocol — but this is about general feature coverage, not `new_context()` specifically | [3] |

**Verdict:** `browser.new_context()` works on CDP-connected browsers. Playwright delegates to `Target.createBrowserContext` in the CDP protocol, which is a stable, non-experimental API.

### 3.2 Isolation guarantees

| What's isolated | Mechanism | Source |
|----------------|-----------|--------|
| Cookies | "It won't share cookies/cache with other browser contexts" | [1] |
| Cache | Same — separate cache per context | [1] |
| localStorage | Each BrowserContext has its own storage partition | [2] |
| Service workers | Scoped per context | [1] |
| Extensions | Shared (browser-level, not context-level) | Chrome architecture |

### 3.3 Implementation options

| Option | Description | KISS | Risk |
|--------|-------------|------|------|
| A. Always isolate | Replace `contexts[0]` with `new_context()` unconditionally | High | Low — no config flag needed |
| B. Config flag | Add `cdp_isolated_context: bool = True`, allow opt-out | Medium | Low — but adds config surface for no clear use case |
| C. Keep current + warn | Only add docs, no code change | High | High — SEC-07 remains open |

### 3.4 Code changes required (Option A)

| File | Change | Impact |
|------|--------|--------|
| `manager.py` `_enter_cdp()` | `self._context = await self._browser.new_context(viewport=...)` instead of `self._browser.contexts[0]` | Core fix |
| `manager.py` `_exit_cdp()` | Add `self._context.close()` before `self._browser.disconnect()` | Cleanup: close owned context |
| `toolset.py` `setup()` | Update log message — no longer "full session access" | Cosmetic |
| `test_browser_manager.py` | Update CDP mock chain: assert `new_context()` called, `contexts[0]` NOT used; assert `context.close()` in cleanup | Test alignment |

### 3.5 What stays the same

- All 6 browser action tools (`navigate`, `click`, `type`, `select`, `read_text`, `screenshot`) work through `self.page` — no change needed.
- `ScreenshotService` and `VisualFeedbackToolset` use the page from BrowserManager — no change.
- `BrowserConfig` — no new fields needed (YAGNI: Option A).
- Title-prefix logic in `BrowserToolset.setup()` still applies to the new page.

## 4. Recommendation (.90 confidence)

**Option A: Always isolate.** Replace `contexts[0]` with `browser.new_context()` in `_enter_cdp()`.

- KISS-aligned: no config flag, no opt-out complexity.
- YAGNI-aligned: no use case for deliberately sharing the user's session.
- Minimal diff: ~10 lines in `manager.py`, ~30 lines in tests.
- Risk: extensions remain shared (browser-level), but this is inherent to CDP and not a cookie/session concern.

**Bonus fix:** The current CDP path doesn't pass viewport to the context. The new code should include `viewport={"width": w, "height": h}` matching the launch path.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement CDP context isolation in BrowserManager" --priority needed --status todo --tags "security,browser,phase-3" --body "Replace contexts[0] with browser.new_context(viewport=...) in _enter_cdp(). Close owned context in _exit_cdp(). Update warning log. See docs/research/cdp-context-isolation.md S4. AC: (1) _enter_cdp uses browser.new_context(), (2) _exit_cdp closes context before disconnect, (3) viewport applied in CDP mode, (4) all existing tests updated + new isolation assertion, (5) ruff clean, tests green."
```

```
kanban\kanban-md.exe create "Update security-audit.md: mark SEC-07 as resolved" --priority important --status todo --tags "docs,security" --depends-on "<implementation-task-id>" --body "After CDP context isolation is implemented, update docs/security-audit.md to mark SEC-07 as resolved with implementation reference. AC: SEC-07 entry updated with resolution status and link to implementation."
```
