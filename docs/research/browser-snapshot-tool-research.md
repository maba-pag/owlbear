# Browser Snapshot Tool Design for BrowserToolset

> **Owning task:** #727 — Add browser_snapshot tool to BrowserToolset
> **Date:** 2026-03-10  **Status:** Complete

## 1. Context and Question

Task #727 (from PinchTab research S4.3) adds a `browser_snapshot` tool to `BrowserToolset` that exposes `BrowserManager.snapshot()` (task #726, not yet implemented). Key design questions: (a) tool API parameters, (b) tool description with token-cost guidance, (c) output format, (d) placement within the toolset pattern.

## 2. Sources Studied

| Source | URL | Type | Relevance |
|--------|-----|------|-----------|
| browser-use `Agent.service` + `BrowserStateSummary` | `github.com/browser-use/browser-use` (agent/service.py, browser/views.py) | Primary — 80K star framework | .90 |
| PinchTab SKILL.md token cost guide | `docs/research/pinchtab-research.md` S3c | Internal — token cost model | .85 |
| OwlBear BrowserToolset (toolset.py) | `src/owlbear/tools/browser/toolset.py` | Internal — existing pattern | .95 |
| OwlBear a11y-snapshot research (#726) | `docs/research/a11y-snapshot-research.md` | Internal — upstream API design | .90 |
| Playwright CDPSession docs | `playwright.dev/python/docs/api/class-cdpsession` | Primary — API reference | .85 |
| Stagehand `observe()` API | `github.com/browserbase/stagehand` | Secondary — alternative pattern | .65 |

## 3. Analysis

### 3a. Tool API design comparison

| Approach | Parameters | Pros | Cons |
|----------|-----------|------|------|
| **A: Single filter param** (PinchTab) | `filter: text\|interactive\|full` | Simple, LLM-friendly, one arg | Less flexible |
| **B: Separate include flags** (browser-use) | `include_text: bool, include_interactive: bool` | Fine-grained | Too many combinations, confusing |
| **C: filter + max_nodes** | `filter: str, max_nodes: int` | Cost control built in | Over-engineered for v1 |

**Recommendation (.85): Option A** — single `filter` param with 3 modes. Matches PinchTab's proven design, simplest for LLM agents, aligns with KISS/YAGNI.

### 3b. Filter modes from #726 research (validated by PinchTab)

| Filter | What it returns | Approx tokens | Use case |
|--------|----------------|---------------|----------|
| `text` | StaticText + headings only | ~800 | Reading page content |
| `interactive` | Focusable/actionable nodes (buttons, links, inputs) | ~3,600 | Finding clickable elements |
| `full` | All non-ignored accessibility nodes | ~10,500 | Full page understanding |

### 3c. Default filter selection

| Option | Default | Rationale | Confidence |
|--------|---------|-----------|------------|
| `text` | Cheapest but useless for actions | .40 |
| **`interactive`** | **Best cost/utility — action-oriented agents need this most** | **.80** |
| `full` | Most complete but expensive | .30 |

browser-use defaults to showing all interactive elements every step. PinchTab defaults to `interactive` filter. Both validate `interactive` as the default.

### 3d. Output format

| Option | Format | Pros | Cons |
|--------|--------|------|------|
| **A: Formatted string** | `"[id] role: name\n..."` | LLM-native, no parsing needed | Less structured |
| B: JSON string | `json.dumps(list[dict])` | Machine-parseable | LLM must parse JSON |
| C: Return structured object | `list[AXNodeInfo]` | Typed | PydanticAI tools return strings |

**Recommendation (.85): Option A** — formatted string. OwlBear's existing tools (`browser_read_text`, `browser_navigate`) all return human-readable strings. LLM agents consume strings natively. Example format:

```
[14] button: "Submit"
[23] link: "Documentation"
[31] textbox: "Search..."
```

This matches browser-use's `selector_map` display format (index-based element references).

### 3e. Tool description with token-cost guidance

PinchTab embeds a token cost table directly in the tool description so LLM agents can make cost-aware decisions. This is a transferable pattern — the tool description is the only metadata LLMs see before calling a tool.

Proposed description:

```
Get accessibility tree snapshot of the current page. Token cost by filter:
text (~800 tokens) — page text only; interactive (~3600) — clickable
elements; full (~10500) — complete tree. Default: interactive.
```

### 3f. Placement: BrowserToolset vs VisualFeedbackToolset

| Option | Location | Rationale |
|--------|----------|-----------|
| **BrowserToolset** | Same toolset as navigate, click, read_text | Browser state extraction is a browser action |
| VisualFeedbackToolset | Alongside share_screenshot | Snapshot is "visual" in a sense |

**Recommendation (.90): BrowserToolset.** The snapshot is a browser introspection tool (like `browser_read_text`), not a visual delivery tool. All browser state ops should live together. This matches the #726 research recommendation.

### 3g. Testing strategy

Tests should follow the existing pattern in `test_browser_toolset.py`:

- Mock `BrowserManager.snapshot()` return value (list of `AXNodeInfo`)
- Verify tool wrapper delegates to `snapshot()` with correct filter
- Verify output string format matches expected schema
- Verify tool is registered with correct name and description
- Verify `EXPECTED_TOOL_NAMES` updated to include `browser_snapshot` (7 tools)

## 4. Recommendation (.85 confidence)

Add `browser_snapshot` as the 7th tool in `BrowserToolset`:

- **Parameter:** `filter: str = "interactive"` (literal: text|interactive|full)
- **Output:** Formatted string with `[id] role: "name"` per line
- **Description:** Includes token-cost guide per filter mode
- **Depends on:** #726 (`BrowserManager.snapshot()` implementation)

Risk: #726 not yet implemented — tool wrapper will call a method that doesn't exist yet. Mitigation: implement #726 first, or stub `snapshot()` to raise `NotImplementedError` and test the toolset layer independently.

## 5. Follow-up Tasks

The task already exists as #727. These are refined sub-tasks:

```powershell
# #726 must be completed first (BrowserManager.snapshot via CDP)
# Then #727 can be implemented:

kanban\kanban-md.exe create "Implement browser_snapshot wrapper in BrowserToolset" --priority important --status backlog --tags "phase-browser,scope:core,browser" --depends-on 726 --body "**Source:** docs/research/browser-snapshot-tool-research.md S4`n`nAdd browser_snapshot as the 7th tool in BrowserToolset.`n`n**Implementation:**`n- Add _snapshot wrapper method that calls self._manager.snapshot(filter)`n- Format AXNodeInfo list as '[id] role: name' string`n- Register via add_function with token-cost description`n- Default filter='interactive'`n`n**AC:**`n- [ ] browser_snapshot tool registered in BrowserToolset (7 tools total)`n- [ ] Tool description includes token cost guide`n- [ ] filter param accepts text|interactive|full, defaults to interactive`n- [ ] Output is formatted string with [id] role: name per line`n- [ ] Tests mock BrowserManager.snapshot() and verify delegation + output format"
```

Note: This follow-up task overlaps significantly with #727 itself. The research validates #727's existing AC and refines the implementation approach. No additional tasks needed — #727 is ready for architect review.
