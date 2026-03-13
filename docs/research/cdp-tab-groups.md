# CDP Tab Groups Research

> **Owning task:** #65 — P6-01: Research CDP tab groups via DevTools Protocol
> **Date:** 2026-02-27
> **Status:** Complete

## 1. Context and Question

OwlBear's browser module opens tabs in Edge via CDP for web research and interaction. The goal is to visually group OwlBear-opened tabs under a named group like "OwlBear - {task}" so the user can distinguish OwlBear tabs from personal browsing. Currently, `BrowserToolset.setup()` prefixes the document title with `[OwlBear]` in CDP mode — a minimal visual indicator.

**Core question:** Can Chrome Tab Groups be created/managed via CDP (Chrome DevTools Protocol), or is a different mechanism required?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| CDP Target Domain (tip-of-tree) | chromedevtools.github.io/devtools-protocol/tot/Target/ | .95 | Full Target domain spec — `createTarget`, `TargetInfo`, all parameters |
| Chrome Extensions `tabGroups` API | developer.chrome.com/docs/extensions/reference/api/tabGroups | .90 | Official tab group management — `get`, `move`, `query`, `update` |
| Chrome Extensions `tabs.group()` | developer.chrome.com/docs/extensions/reference/api/tabs#method-group | .90 | `chrome.tabs.group()` — assigns tabs to groups |
| Puppeteer issue #13215 | github.com/puppeteer/puppeteer/issues/13215 | .85 | Feature request for tab groups — closed as "not planned" |
| Playwright Chrome Extensions docs | playwright.dev/python/docs/chrome-extensions | .80 | Extension loading via `--load-extension`, persistent context requirement |
| Chromium issue tracker | issues.chromium.org (search: "devtools tab group") | .60 | No CDP tab group domain proposals found |
| StackOverflow (CDP + tab-groups tags) | stackoverflow.com/questions/tagged/chrome-devtools-protocol+tab-groups | .50 | 0 questions — confirms this is not a solved space |

## 3. Analysis

### 3.1 CDP Has No Tab Group Support

The CDP Target domain was reviewed exhaustively. Key findings:

- `Target.createTarget` parameters: `url`, `width`, `height`, `browserContextId`, `newWindow`, `background`, `forTab`, `hidden`, `focus` — **no group parameter**
- `TargetInfo` properties: `targetId`, `type`, `title`, `url`, `attached`, `openerId`, `browserContextId` — **no groupId**
- No `TabGroups` domain exists in CDP (stable, experimental, or tip-of-tree)
- Puppeteer maintainer explicitly stated: "Puppeteer focuses on automation of the page and at this point there aren't any plans to support 'Browser UI' bits" (#13215)

**Conclusion:** CDP cannot create, read, or modify tab groups. This is a browser UI feature exposed only through the Chrome Extensions API.

### 3.2 Approaches Comparison

| Criterion | A: Helper Extension (.70) | B: Title Prefix (.85) | C: Separate Window (.60) |
|-----------|--------------------------|----------------------|--------------------------|
| **Mechanism** | MV3 extension loaded at launch uses `chrome.tabs.group()` | `document.title = '[OwlBear] ...'` (current) | `Target.createTarget` with `newWindow: true` |
| **Visual grouping** | Native tab group (colored, named, collapsible) | Title text only | Separate browser window |
| **CDP connect mode** | Not possible (can't load extensions post-launch) | Works | Works |
| **Launch mode** | Requires `--load-extension` flag | Works | Works |
| **Edge Stable compat** | Blocked — Edge removed `--load-extension` flag | Full | Full |
| **Edge Dev/Canary** | Likely works (flags still accepted) | Full | Full |
| **Playwright Chromium** | Works (bundled Chromium supports sideloading) | Full | Full |
| **Dependency count** | +1 extension dir, messaging boilerplate | 0 (already implemented) | 0 |
| **KISS score** | Low | High | Medium |
| **User experience** | Best (native UI) | Adequate | Disruptive (window switch) |

### 3.3 Helper Extension Approach — Deep Dive

If pursued, the extension would need:

```
owlbear-ext/
  manifest.json    # MV3, permissions: ["tabs", "tabGroups"]
  background.js    # Service worker listening for messages
```

**Communication path:** Playwright page → `Runtime.evaluate` on extension service worker → `chrome.tabs.group()` + `chrome.tabGroups.update()`

**Critical blockers:**

1. **Edge Stable removed `--load-extension`** — Playwright docs confirm Chrome and Edge removed sideloading flags. Only Playwright's bundled Chromium retains them.
2. **CDP connect mode incompatible** — When OwlBear connects to an already-running Edge, it cannot inject extensions.
3. **Tab ID mismatch** — CDP `targetId` ≠ Chrome extension `tabId`. Mapping between them requires additional plumbing.

### 3.4 Enhanced Title Prefix Approach — Deep Dive

Current behavior: `document.title = '[OwlBear] ' + document.title`

Enhanced version could:

- Include task ID: `[OwlBear #65] Original Title`
- Use a MutationObserver to persist the prefix across SPA navigations
- Apply via `BrowserManager` (not just `BrowserToolset`) for broader coverage

**Advantages:** Works in both modes, zero dependencies, already partially implemented.

## 4. Recommendation (.80 confidence)

**Enhance the title-prefix approach (Option B)** as the primary strategy. It is KISS-aligned, works in both CDP and launch modes, requires no additional dependencies, and is already partially implemented.

**Do NOT pursue the helper extension (Option A)** for MVP. The Edge Stable sideloading block makes it unreliable on the target browser. If tab grouping becomes a hard requirement later, revisit with one of:

- A properly installed Edge Add-on (requires Edge Add-ons Store or enterprise sideloading policy)
- Switching to Playwright's bundled Chromium for launch mode

**Specific enhancements to implement:**

1. Accept a `task_label` parameter in `BrowserToolset.setup()` / `BrowserManager`
2. Format title as `[OwlBear {task_label}] {original_title}`
3. Install a `MutationObserver` on `document.title` to re-apply prefix after SPA navigations
4. Consider adding a favicon badge via canvas injection for additional visual differentiation

## 5. Follow-up Tasks

1. **Enhance tab title prefix with task label** — Add `task_label` parameter to `BrowserToolset.setup()`, format as `[OwlBear {task_label}]`, apply MutationObserver persistence
2. **Investigate Edge extension sideloading** — Test whether `--load-extension` works on current Edge Stable (flags may have been re-enabled); document results for future reference
3. **Spike: favicon badge injection** — Prototype canvas-based favicon overlay showing "OB" badge on OwlBear-controlled tabs
