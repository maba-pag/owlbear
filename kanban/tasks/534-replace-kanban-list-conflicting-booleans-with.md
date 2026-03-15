---
id: 534
title: Replace kanban_list conflicting booleans with block_filter enum
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:39.627003+01:00
updated: 2026-03-15T12:25:38.1379933+01:00
started: 2026-03-07T00:29:36.3343606+01:00
completed: 2026-03-15T12:25:33.0279319+01:00
tags:
    - audit
    - code-quality
    - tools
depends_on:
    - 820
class: standard
---

Replace 3 mutually exclusive boolean params with a single Literal enum. See docs/code-quality-audit.md F-24.

## Acceptance Criteria

- [ ] `kanban_list` signature: replace `blocked: bool = False`, `not_blocked: bool = False`, `unblocked: bool = False` with `block_filter: Literal['blocked', 'not_blocked', 'unblocked'] | None = None`
- [ ] When `block_filter` is set, append `--{value with _ replaced by -}` to CLI args (e.g. `'not_blocked'` -> `--not-blocked`)
- [ ] When `block_filter` is `None` (default), no block-related flag is appended
- [ ] The `# noqa: PLR0913` comment is removed (param count drops from 7 to 5)
- [ ] Docstring updated to document the `block_filter` parameter
- [ ] All tests from #820 pass (GREEN)
- [ ] ruff clean

## Architecture Notes

- Pattern precedent: `Literal[...]` is used in `config.py`, `circuit_breaker.py`, `models.py`, `browser/config.py`
- Flag mapping: `block_filter.replace('_', '-')` then prepend `--`
- No callers outside tests reference these booleans (tool is called by LLM via schema)

## Files

- `src/owlbear/tools/kanban.py` (`kanban_list` method, ~15 lines changed)

## Dependencies

- #820 (test task, must be RED before implementation)

[[2026-03-15]] Sun 08:06
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Replace 3 bools with block_filter Literal | Precise, verifiable by grep | Kept |
| Flag mapping with _ to - replacement | Clear implementation spec | Kept |
| None default = no flag | Verifiable in test | Kept |
| Remove PLR0913 noqa | Mechanical, verifiable | Added |
| Docstring updated | Verifiable by reading code | Added |
| Tests from #820 pass GREEN | Links to test task | Added |
| ruff clean | Standard gate | Kept |

### Architecture Notes
- Literal[...] is established pattern in codebase (config.py L27/47/226/232, circuit_breaker.py L32, models.py L56, browser/config.py L46)
- Single param eliminates LLM conflict risk (can't set multiple=True)
- No callers outside tests (LLM calls via PydanticAI schema)
- No module layering concerns (change stays within tools/kanban.py)
- No security surface change (subprocess args already sanitized by kanban-md CLI)
- No new failure modes (Literal type enforced by PydanticAI at schema level)

### Changes Made
- Refined AC from vague 'single filter param, no conflicts' to 7 verifiable AC lines
- Created test task #820 (todo, nice-to-have, tags: test, tools)
- Added depends_on: [820] to #534
- Moved #534 backlog -> todo

### Dependencies
- Added: #820 (test task, must be RED before implementation)

[[2026-03-15]] Sun 10:19
## Test-Writer Notes
- Tests already written and verified via dependency #820 (TestFromAC_BlockFilterEnum, 4 tests in test_kanban_tools.py)
- Implementation already complete (block_filter param in kanban.py)
- All 4 tests PASS (GREEN): block_filter blocked/not_blocked/unblocked/None
- Remaining AC items (PLR0913 removal, docstring) are code-quality gates, not behavioral contracts
- Passing through to builder for final verification.

[[2026-03-15]] Sun 11:22
## Builder Notes
- Files changed: src/owlbear/tools/kanban.py (2 lines)
- Changed block_filter type: str -> Literal['blocked', 'not_blocked', 'unblocked']
- Added Literal import to typing imports
- Tests: 88 passed, coverage 100% on tools/kanban.py
- Lint: ruff clean
- PLR0913 noqa already removed (by #820)
- Docstring already updated (by #820)

[[2026-03-15]] Sun 11:46
## Review Evidence

### Test Results
- pytest (scoped): 88 passed, 0 failed (test_kanban_tools.py)
- ruff: All checks passed
- Coverage: unable to measure (terminal KeyboardInterrupt corruption); visual inspection of 2-line diff confirms no uncovered paths

### Pass 1 - CRITICAL

#### Security Review
No security issues. Change is purely a type annotation tightening (str -> Literal). No new I/O, no new dependencies, no secrets, no injection surface.

#### Test Integrity (TestFromAC comparison)
Builder for #534 made ZERO changes to test file (git diff d1ed66a..a3c5aac empty).
All 4 TestFromAC_BlockFilterEnum tests: PRESERVED.

#### Test Quality
All dimensions STRONG or ADEQUATE. Each test asserts exact flag present AND other flags absent. Fresh mocks per test. Descriptive names.

#### Data Safety
No data safety issues. Type annotation change only.

### AC Compliance
All 7 AC lines verified with evidence. See full review in docs/scratch/534-reviewer.md.

### Verdict: PASS
Confidence: .95

[[2026-03-15]] Sun 12:05
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Internal refactor (3 bools -> Literal enum), no behavior/API/convention change |
| 2 | Docstrings complete | Yes | Pass | kanban_list docstring documents block_filter with all 3 values + None (L162-164) |
| 3 | sources/overview.md | No | N/A | No external patterns; originated from internal code-quality-audit F-24 |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | No | N/A | No research phase |
| 6 | No impact | -- | -- | Item 2 applies (pass); rest are N/A |

### Files Updated
- None

### Scratch Files Cleaned
- None (no 534-* files found)

[[2026-03-15]] Sun 12:25
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Replace 3 bools with block_filter Literal | kanban.py L155: block_filter: Literal[...] | PASS |
| Flag mapping _ to - | kanban.py L167-172: _block_flags dict, L180: append | PASS |
| None default = no flag | kanban.py L179: if block_filter is not None guard | PASS |
| PLR0913 noqa removed | grep: PLR0913 only on kanban_edit L242, not kanban_list | PASS |
| Docstring updated | kanban.py L161-164: block_filter documented | PASS |
| All #820 tests pass GREEN | 88 passed, 0 failed (test_kanban_tools.py) | PASS |
| ruff clean | All checks passed | PASS |

### Test Results
- pytest (scoped): 88 passed, 0 failed
- pytest (full): 5 collection errors (pre-existing trafilatura/regex env issue)
- ruff: All checks passed

### Confidence: .97
### Action: archive
