---
id: 727
title: Add browser_snapshot tool to BrowserToolset
status: todo
priority: important
created: 2026-03-10T18:19:22.6932355+01:00
updated: 2026-03-11T16:52:05.286854+01:00
started: 2026-03-10T19:23:33.867777+01:00
tags:
    - phase-browser
    - scope:core
    - browser
depends_on:
    - 726
    - 736
claimed_by: test-writer
claimed_at: 2026-03-11T16:52:05.286854+01:00
class: standard
---

**Source:** docs/research/pinchtab-research.md S4.3

Expose BrowserManager.snapshot() as a browser_snapshot tool. Include token-cost guidance in tool description so agents prefer cheap extraction.

**AC:**
- [ ] browser_snapshot tool registered in BrowserToolset
- [ ] Tool description includes token cost guide (text ~800, interactive ~3600, full ~10500)
- [ ] Agents can request filter=interactive for action-oriented tasks
- [ ] Tests verify tool output schema

[[2026-03-10]] Tue 20:13
## Architecture Review
**Verdict:** APPROVED (with refinements applied)

### AC Assessment
| AC Line (original) | Assessment | Action |
|---------------------|------------|--------|
| browser_snapshot tool registered in BrowserToolset | Adequate concept, missing specifics (tool count, method name, registration pattern) | Rewritten: 7th tool via `_register_tools()`, `_snapshot` wrapper |
| Tool description includes token cost guide | Adequate | Kept, made verifiable with exact token values |
| Agents can request filter=interactive for action-oriented tasks | Vague -- doesn't specify parameter type, default, or accepted values | Rewritten: `filter: str = 'interactive'` with literal text `\|` interactive `\|` full |
| Tests verify tool output schema | Vague -- no output format specified | Rewritten: `[id] role: name` per line; created #736 test task |

### Architecture Notes
- **Module placement:** New `_snapshot` wrapper in existing `BrowserToolset` in `src/owlbear/tools/browser/toolset.py`. Correct layer per architecture-standards (tools layer). No upward imports.
- **Pattern consistency:** Follows existing wrapper pattern: `_register_tools()` calls `self.add_function()`, wrapper injects `self._manager` / `self.page`. Format-to-string in the wrapper (like `_read_text` returns a string).
- **Output format:** `[id] role: name` per line -- validated by browser-snapshot-tool-research.md S3d. Matches browser-use's display format. LLM-native (string, no JSON parsing).
- **Default filter:** `interactive` -- validated by both PinchTab and browser-use as best cost/utility ratio.
- **Token-cost description:** Embedded in tool description string so LLM agents see it before calling. Transferable pattern from PinchTab.
- **Security:** No new system boundaries introduced. Snapshot reads a11y tree (read-only). No user input flows in beyond the filter literal.
- **Single domain:** Browser tools only -- no cross-domain concerns.

### Changes Made
- Rewrote task body with 9 precise, verifiable AC lines
- Added implementation guidance referencing existing patterns in toolset.py
- Created #736: Tests: browser_snapshot tool in BrowserToolset (RED phase)
- Added dependency: #727 depends on #736 (test-first) and #726 (BrowserManager.snapshot())

### Dependencies
- Verified: #726 (BrowserManager.snapshot()) -- in `todo` status, architect-approved
- Added: #736 (test task, RED phase) -- preceding TDD task, in `backlog`
- No circular dependencies
