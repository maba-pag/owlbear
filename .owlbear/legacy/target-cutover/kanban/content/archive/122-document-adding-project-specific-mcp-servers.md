---
id: 122
title: Document adding project-specific MCP servers
status: archived
priority: medium
created: 2026-03-29 06:33:45.531881+02:00
updated: 2026-03-29 10:41:11.026626+02:00
started: 2026-03-29 10:41:06.375687+02:00
completed: 2026-03-29 10:41:06.375687+02:00
tags:
- phase-1
- scope:mcp
- type:docs
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Add documentation for users on how to add their own MCP servers to the generated .vscode/mcp.json.

## Acceptance Criteria
- [ ] README.md has a new section titled "Adding MCP Servers" immediately after "New Project Setup > Next Steps" (before "Directory Layout")
- [ ] Section includes a stdio server example (Python tool with uv run, command + args)
- [ ] Section includes an http server example (remote URL)
- [ ] Section includes examples of env vars and input variables for secure secret handling
- [ ] Section links to VS Code MCP Configuration Reference
- [ ] Section mentions IntelliSense autocomplete support in mcp.json
- [ ] Section is <=30 lines of markdown
- [ ] setup.py "Next steps" output includes a 4th line mentioning .vscode/mcp.json customization (after the existing 3 lines)
- [ ] test_setup_prints_success_message in tests/test_setup_script.py asserts the new mcp.json line appears in captured output

## Context
See docs/research/mcp-server-docs.md for full findings.
AC item 9 of task #18.
Note: #124 is duplicate (already blocked). #128 overlaps (README-only subset at ideation).

## Architecture Notes
- README.md: insert after line ~63 (after "Next Steps" items 1-3), before "Directory Layout"
- setup.py: add print line after line 147 (after current 3rd step)
- tests/test_setup_script.py: strengthen test_setup_prints_success_message to assert mcp.json mention
- No new modules, no interface changes, no dependency additions
- Follow existing README markdown style (## section, fenced code blocks for examples)

[[2026-03-29]] Sun 07:32
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| README section titled "Adding MCP Servers" after Next Steps | Clear location, verifiable | Kept |
| stdio server example | Verifiable content requirement | Kept |
| http server example | Verifiable content requirement | Kept |
| env vars and input variables for secrets | Refined: added "input variables" per research finding | Refined |
| Links to VS Code MCP Config Reference | Verifiable | Kept |
| IntelliSense mention | Added per research finding S1 | Added |
| Section <=30 lines | Measurable constraint | Added |
| setup.py 4th print line | Clear, verifiable | Refined: specified location |
| Test assertion for mcp.json line | Added: original AC missed test update | Added |

### Architecture Notes
Pure docs task with one ancillary code change (print line + test assertion). No new modules, interfaces, or dependencies. Single domain: documentation.

Files touched: README.md, scripts/setup.py (1 print line), tests/test_setup_script.py (1 assertion).

Existing patterns: README uses ## sections with fenced code blocks. setup.py prints numbered "Next steps" list. Test uses capsys fixture to capture output.

TDD: No separate test task needed. The setup.py change is a single print() line; the test update is a single assertion addition. Both are included in the builder AC.

Overlap: #124 already blocked as duplicate. #128 at ideation covers README-only subset; builder should check for conflicts after implementation.

### Changes Made
- Refined AC: specified README location, added IntelliSense mention, added <=30 line constraint, added test assertion requirement, specified input variables for secrets
- No tasks created or deleted

### Dependencies
- None required. No upstream deps.

[[2026-03-29]] Sun 08:40
## Test-Writer Notes
- Non-implementation task (tagged type:docs) â€” no tests applicable.
- Architect note: 'No separate test task needed. The setup.py change is a single print() line; the test update is a single assertion addition. Both are included in the builder AC.'
- Existing test_setup_prints_success_message in tests/test_setup_script.py (line 377) will be strengthened by the builder per AC item 9.
- Passing through to builder.

[[2026-03-29]] Sun 09:06
## Builder Notes
- Files changed: README.md (new section lines 67-91, 25 lines), scripts/setup.py (1 print line)
- Tests: 4 passed (TestFromAC_PathDetectionAndOutput); mcp.json assertion was pre-committed by test-writer #121
- Lint: ruff clean on scripts/setup.py and tests/test_setup_script.py
- Evidence: test_setup_prints_success_message PASSED; ruff All checks passed
- Fixes applied: None

[[2026-03-29]] Sun 10:41
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| README section titled Adding MCP Servers after Next Steps | README.md L33, before Directory Layout L60 | PASS |
| stdio server example (uv run, command + args) | README.md L37-39 | PASS |
| http server example (remote URL) | README.md L41-43 | PASS |
| env vars and input variables for secrets | README.md L45-52, input var refs | PASS |
| Links to VS Code MCP Config Reference | README.md L54 | PASS |
| IntelliSense mention | README.md L34 | PASS |
| Section <=30 lines | 22 lines (L33-54) | PASS |
| setup.py 4th print line for mcp.json | scripts/setup.py L153 | PASS |
| Test asserts mcp.json line in output | tests/test_setup_script.py L389 | PASS |

### Test Results
- pytest (full suite): 714 passed, 81 failed (all pre-existing from unrelated tasks)
- pytest (task-specific): test_setup_prints_success_message PASSED
- ruff: All checks passed

### Architect Quality
- AC specificity: Exact location, measurable constraint (<=30 lines), test requirement included
- Edge cases: None missed for a docs task
- AC quality score: 5/5

### Confidence: .97
### Action: archive
