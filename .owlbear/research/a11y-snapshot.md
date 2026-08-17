# Accessibility-Tree Snapshot for BrowserManager

> **Owning task:** #726 — Add accessibility-tree snapshot to BrowserManager
> **Date:** 2026-07-08  **Status:** Complete

## 1. Context and Question

Task #726 adds a `snapshot()` method to `BrowserManager` that returns a parsed accessibility tree. The original AC references Playwright's `page.accessibility.snapshot()` (via PinchTab research). **Critical finding:** this API is deprecated and removed from modern Playwright — the docs URL returns 404. Two replacement approaches exist. Which should OwlBear adopt?

## 2. Sources Studied

| Source | URL | Type | Relevance |
|--------|-----|------|-----------|
| Playwright ARIA Snapshots docs | <https://playwright.dev/python/docs/aria-snapshots> | Primary — modern API docs | .85 |
| CDP Accessibility domain spec | <https://chromedevtools.github.io/devtools-protocol/tot/Accessibility/> | Primary — protocol spec | .90 |
| browser-use `DomService` | <https://github.com/browser-use/browser-use> (`browser_use/dom/service.py`) | Primary — production prior art (80K stars) | .90 |
| PinchTab research (internal) | `docs/research/pinchtab.md` S3b, S4 | Internal — original recommendation | .80 |

## 3. Analysis

### 3a. `page.accessibility.snapshot()` — DEPRECATED

Playwright removed the `Accessibility` class. The URL `playwright.dev/python/docs/api/class-accessibility` returns 404. The task AC and PinchTab research S4.1 both reference this API — **both need updating**.

### 3b. Option comparison

| Criterion | A: `locator.aria_snapshot()` | B: CDP `getFullAXTree` |
|-----------|------------------------------|------------------------|
| API maturity | Playwright ≥1.49 (stable) | CDP EXPERIMENTAL (stable in practice) |
| Output format | YAML string | Array of `AXNode` objects (JSON) |
| Fields per node | role, name, attributes | nodeId, role, name, description, properties, backendDOMNodeId |
| Selector recovery | Not possible | Yes — via `backendDOMNodeId` → DOM node mapping |
| Filter capability | None built-in (post-process YAML) | Filter via `properties` (focusable, editable, etc.) |
| Matches PinchTab schema? | No (no id, no selector) | Yes (id=backendDOMNodeId, role, name, selector recoverable) |
| Dependencies | Playwright ≥1.49 (bump from ≥1.40) | Playwright CDPSession (available since 1.11) |
| Implementation complexity | ~30 LOC (parse YAML) | ~80-120 LOC (CDP session + node flattening + filter) |
| Prior art | Playwright test assertions | browser-use (80K stars, production) |
| Works in both modes? | Yes (launch + CDP) | Yes — `context.new_cdp_session(page)` works in both |
| Token efficiency | ~same (YAML vs flat list) | ~same (flattened node list) |

### 3c. CDP approach details (from browser-use)

browser-use's `DomService._get_ax_tree_for_all_frames()`:

1. Creates CDP session via `get_or_create_cdp_session(target_id)`
2. Calls `Accessibility.getFullAXTree(frameId=...)` per frame
3. Merges all `AXNode` arrays into one list
4. Builds lookup: `{backendDOMNodeId: AXNode}` for DOM correlation
5. Each `AXNode` has: `role`, `name`, `description`, `properties` (focusable, editable, etc.), `backendDOMNodeId`

OwlBear's simpler scope (single page, no cross-origin iframes) means we need ~20% of browser-use's complexity.

### 3d. Playwright CDPSession access

```python
# Available in both launch and CDP modes
cdp = await context.new_cdp_session(page)
result = await cdp.send("Accessibility.getFullAXTree")
nodes = result["nodes"]  # list[AXNode]
await cdp.detach()
```

Requires Chromium — not Firefox/WebKit. OwlBear already targets Chromium only.

### 3e. Filter modes mapping

| Filter | CDP implementation |
|--------|--------------------|
| `interactive` | Keep nodes where `properties` includes `focusable=True` or role in {button, link, textbox, combobox, checkbox, radio, menuitem, tab} |
| `full` | Return all non-ignored nodes |
| `text` | Keep only `StaticText` role nodes + headings — cheapest option (~800 tokens) |

### 3f. Output schema (aligned with PinchTab)

```python
@dataclass
class AXNodeInfo:
    id: int  # backendDOMNodeId from CDP
    role: str  # "button", "link", "textbox", etc.
    name: str  # accessible name
    description: str  # accessible description (optional)
    properties: dict  # focusable, editable, expanded, etc.
```

Note: PinchTab's original schema includes a `selector` field. Recovering CSS selectors from `backendDOMNodeId` requires an additional CDP call (`DOM.describeNode`) which adds latency. **Recommendation:** defer selector recovery to a separate method or future task — the `id` (backendDOMNodeId) is sufficient for element targeting via CDP.

## 4. Recommendation

**Option B: CDP `Accessibility.getFullAXTree`** — confidence **.80**

Rationale:

- Satisfies all AC requirements (id, role, name, filter modes)
- browser-use validates this approach at scale (80K stars, production)
- `backendDOMNodeId` enables future selector recovery without blocking this task
- No Playwright version bump needed (CDPSession available since 1.11)
- OwlBear already targets Chromium-only — no cross-browser concern

**Risk:** CDP Accessibility domain is marked EXPERIMENTAL. Mitigation: browser-use has relied on it for 2+ years without breakage. The "experimental" label is a Chrome convention for non-W3C-standard APIs.

**AC adjustments needed:**

- AC3 "Output format matches PinchTab's ref schema (id, role, text, selector)" → relax `selector` to be optional/deferred. The `backendDOMNodeId` serves as the stable identifier. Selector recovery is a separate concern.
- Remove any reference to `page.accessibility.snapshot()` — it no longer exists.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Implement BrowserManager.snapshot() via CDP Accessibility.getFullAXTree" --priority needed --status backlog --tags "phase-browser,scope:core,browser" --body "**Source:** docs/research/a11y-snapshot.md S4`n`nAdd async `snapshot(filter)` method to BrowserManager. Uses Playwright CDPSession to call `Accessibility.getFullAXTree`, flattens AXNode array, applies filter (interactive|full|text), returns list[AXNodeInfo].`n`n**AC:**`n- [ ] BrowserManager.snapshot(filter='full') returns list of AXNodeInfo dataclasses`n- [ ] filter='interactive' keeps only focusable/actionable nodes`n- [ ] filter='text' keeps only StaticText + heading nodes`n- [ ] CDP session created/detached per call (no leaked sessions)`n- [ ] Works in both launch and CDP modes`n- [ ] Tests mock CDPSession.send() with canned AXNode responses"

kanban\kanban-md.exe create "Add browser_snapshot tool to BrowserToolset" --priority important --status backlog --tags "phase-browser,scope:core,browser" --body "**Source:** docs/research/a11y-snapshot.md S4`n**Depends on:** BrowserManager.snapshot() implementation`n`nExpose snapshot() as a `browser_snapshot` tool in BrowserToolset (not VisualFeedbackToolset — keep browser tools together).`nInclude token-cost guidance in tool description.`n`n**AC:**`n- [ ] browser_snapshot tool registered in BrowserToolset`n- [ ] Tool description includes token cost guide (text ~800, interactive ~3600, full ~10500)`n- [ ] Default filter is 'interactive' (best cost/utility ratio)`n- [ ] Tests verify tool output format"
```
