---
id: 727
title: Add browser_snapshot tool to BrowserToolset
status: archived
priority: important
created: 2026-03-10T18:19:22.6932355+01:00
updated: 2026-03-13T16:17:03.0909516+01:00
started: 2026-03-10T19:23:33.867777+01:00
completed: 2026-03-13T16:13:39.7176055+01:00
tags:
    - phase-browser
    - scope:core
    - browser
depends_on:
    - 726
    - 736
class: standard
---

**Source:** docs/research/pinchtab.md S4.3

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
- **Output format:** `[id] role: name` per line -- validated by browser-snapshot-tool.md S3d. Matches browser-use's display format. LLM-native (string, no JSON parsing).
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

[[2026-03-13]] Fri 12:12
## Test-Writer Notes
- Tests already written via companion task #736 (RED phase for #727)
- Test file: tests/test_browser_toolset.py
- Classes: TestFromAC_BrowserSnapshotDelegation, TestFromAC_BrowserSnapshotOutput, TestFromAC_BrowserSnapshotDescription
- Tests per category: happy 9, edge 2, error 0, boundary 1
- Total: 15 tests (12 new + 3 modified existing from #736)
- Implementation already exists (builder completed via #736 pipeline)
- All 48 tests PASS (33 existing + 15 from #736)
- AC coverage: all 4 AC lines mapped to tests

[[2026-03-13]] Fri 13:59
## Builder Notes
- Files changed: none (implementation already complete from #736 builder phase)
- Tests: 48 passed (all test_browser_toolset.py), 12 TestFromAC_BrowserSnapshot* tests all green
- Coverage: 96% on src/owlbear/tools/browser/toolset.py (3 lines missing: 221, 244-245)
- Lint: ruff clean
- Evidence: No code changes needed; verified existing implementation satisfies all AC

[[2026-03-13]] Fri 15:12
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Browser row already documents 'a11y snapshot via CDP getFullAXTree'; tech stack doesn't list individual tools |
| 2 | Docstrings complete | Yes | Pass | Module docstring lists all 7 tools incl browser_snapshot; class docstring accurate; _snapshot() has docstring; all public API covered |
| 3 | sources/overview.md | Yes | Pass | 'Browser Snapshot Tool Design (Task #727)' section already present (L287) with browser-use, Stagehand, Playwright attributions; PinchTab attributed at L1224 |
| 4 | README.md | No | N/A | No CLI changes  browser_snapshot is an agent tool |
| 5 | Research doc linked | Yes | Pass | docs/research/browser-snapshot-tool.md exists; task body references docs/research/pinchtab.md S4.3 |
| 6 | No impact | N/A |  | Items 2, 3, 5 apply |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/727-* files found)

[[2026-03-13]] Fri 16:13
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| browser_snapshot registered in BrowserToolset | toolset.py L186: add_function(_snapshot, name='browser_snapshot') in _register_tools() -- 7th tool. Module docstring updated. | PASS |
| Token cost guide in description | toolset.py L189-194: 'text (~800)...interactive (~3600)...full (~10500)'. 6 tests confirm. | PASS |
| filter=interactive for action tasks | toolset.py L257: filter: str = 'interactive' default. 3 delegation tests confirm. | PASS |
| Tests verify output schema | TestFromAC_BrowserSnapshotOutput (3), TestFromAC_BrowserSnapshotDelegation (3), TestFromAC_BrowserSnapshotDescription (6) = 12 snapshot tests. 48/48 pass. | PASS |

### Test Results
- pytest (scoped): 48 passed, 0 failed (test_browser_toolset.py)
- pytest (full): 3199 passed, 48 failed (all pre-existing: regex/trafilatura env 6, kanban descriptions 24, role policies 4, inter-doc pipeline 8, misc 6). Zero browser failures.
- ruff: All checks passed

### Confidence: .97
### Action: archive

[[2026-03-13]] Fri 16:17
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 42ff2c6 | feat | 399 (MONOLITHIC -- picked up staged research renames + kanban updates) | #727 |

Push status: auto-pushed (VS Code). WARNING: commit includes 399 files beyond #727 scope due to previously staged files being swept in.
