---
id: 471
title: Add end_work compound tool to mcp-kanban server
status: archived
priority: medium
created: 2026-03-31 05:21:15.447030+02:00
updated: 2026-04-01 16:00:27.448372+02:00
started: 2026-04-01 16:00:15.235633+02:00
completed: 2026-04-01 16:00:15.235633+02:00
tags:
- scope:mcp
- ' type:build'
- ' phase-2'
depends_on:
- 497
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] New `end_work(task_id, note, outcome, block_reason?, move_to?, claim?)` tool registered via `@mcp.tool()` in `server.py`
- [ ] `outcome` parameter: `Literal["success", "fail", "block", "reject"]` (default `"success"`)
- [ ] `claim` parameter: optional `str = ""`. When provided, pass to edit's claim flag; when absent, read `claimed_by` from show JSON output
- [ ] `success`: append note w/ timestamp, move to next status (derived from cached statuses), release claim. If current status is last (`done`), use `archive` command instead
- [ ] `fail`: append note w/ timestamp, stay in current status, release claim
- [ ] `block`: append note w/ timestamp, block with `block_reason` (required when outcome=block), release claim
- [ ] `reject`: append note w/ timestamp, move to `move_to` (default: `ideation`), release claim
- [ ] Extend `AppContext` with `statuses: list[str]` field, populated from `config` subprocess (JSON mode) during `app_lifespan` (cached once at startup)
- [ ] Next-status derivation: lookup current status index in `AppContext.statuses`, use `statuses[index + 1]`
- [ ] All outcomes use single `edit` call with `-a NOTE -t [status] [block REASON] release json` flags except done-to-archive which requires `edit` then `archive` (two sequential calls, non-atomic; if archive fails after edit succeeds, return the error so the agent can retry)
- [ ] Return JSON string: output from the final CLI call (JSON mode)
- [ ] Validation: return error if outcome=block and block_reason is empty (fail fast before any CLI calls)
- [ ] Tool respects KANBAN_TOOLS_EXCLUDE if implemented (#473)
- [ ] Update `skills/mcp-kanban/SKILL.md` to document the new tool (add row to Tools table, document outcomes)

## Design Notes

- Replaces 2-3 tool calls per agent exit with a single call
- The four outcomes map to every agent exit path in the pipeline:
  - success: normal progression (builder to review, reviewer to docs, etc.)
  - fail: agent couldn't complete, task stays for retry
  - block: needs human intervention
  - reject: fundamental issue, send back to earlier stage
- Cache statuses at lifespan; config is static during MCP session, server restart picks up changes
- Optional claim parameter enables optimized path when start_work (#470) provides claim_name; fallback reads from show JSON
- Depends on: #497 (TDD RED tests)

[[2026-03-31]] Tue 07:21
## Architecture Review
**Verdict:** REFINE (approved after AC tightening)
**DR Verification:** N/A; T1 classification (convenience composition of existing CLI commands, no new capabilities). Research doc exists but no DR required.

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| end_work signature | Missing optional claim param from research rec | Added claim param |
| outcome Literal | Clear, verifiable | Kept |
| success path | Good but next status source implicit | Made AppContext caching explicit |
| fail path | Clear | Kept |
| block path | Clear | Kept |
| reject path | Clear | Kept |
| Next-status derivation | Said read from config but didn't specify caching | Explicit: extend AppContext, cache at lifespan |
| Return JSON | Clear | Kept |
| Validation | Clear | Kept |
| Tests in AC | TDD violation: tests embedded in impl task | Extracted to #497 (TDD RED test task) |
| KANBAN_TOOLS_EXCLUDE | Soft dep on #473, if implemented is fine | Kept |
| SKILL.md update | Clear | Kept |
| Non-atomicity risk | Not mentioned in original AC | Added note about done-to-archive two-call path |

### Architecture Notes
- Single domain: packages/mcp-kanban (standalone MCP server). No module layering concerns.
- Pattern: follows existing @mcp.tool() + _run_kanban pattern in server.py (7 existing tools).
- AppContext extension: adding statuses list is minimal, cached at lifespan via config subprocess.
- Companion to #470 (start_work, at todo). Independent but claim param enables optimized path. No hard dependency.
- #473 (KANBAN_TOOLS_EXCLUDE) is soft dependency, correctly conditioned.
- Security: no new system boundaries. Uses existing _run_kanban subprocess pattern.
- Failure mode: done-to-archive is two sequential CLI calls (non-atomic). Acceptable risk.

### Changes Made
- Created #497 (Test: end_work compound tool, TDD RED) at todo, priority needed
- Refined AC: added optional claim param, explicit AppContext/statuses caching, non-atomicity note
- Extracted test requirements from impl AC to #497
- Added depends_on: [497] to #471 frontmatter

### Dependencies
- Added: #497 (TDD RED tests, must complete before builder starts #471)
- Verified: #470 (start_work) at todo, independent sibling (no hard dependency)
- Verified: #473 (KANBAN_TOOLS_EXCLUDE) at backlog, soft dependency

[[2026-04-01]] Wed 01:47
## Test-Writer Notes
- Non-standard pass-through: all testable AC was extracted to #497 (TDD RED task) per architect review.
- Test file: packages/mcp-kanban/tests/test_server.py (extended in #497)
- Classes: TestFromAC_AppContextStatuses, TestFromAC_EndWork (written in #497)
- Confirmed: 18 tests pass against existing implementation (delivered by #497 builder).
- Remaining AC: SKILL.md documentation update — non-testable, builder responsibility.
- No new tests written for this task (all coverage delivered via #497).

[[2026-04-01]] Wed 03:55
## Builder Notes
- Non-standard pass-through: all implementation delivered by #497 (builder + writer).
- Verified: server.py has end_work tool (commit aa1ada0, #497 builder)
- Verified: skills/mcp-kanban/SKILL.md documents end_work (commit 45338b5, #497 writer)
- Tests: 53 passed in packages/mcp-kanban/tests/test_server.py (includes TestFromAC_AppContextStatuses and TestFromAC_EndWork)
- Coverage: 87% on server.py (pre-existing, no code touched in #471)
- Lint: ruff clean on packages/mcp-kanban/
- No code commits needed for this task (all delivered upstream via #497)

[[2026-04-01]] Wed 05:22
## Review Evidence
See docs/scratch/471-reviewer.md for full evidence.

[[2026-04-01]] Wed 06:30
## Test-Writer Notes (retry)
- Retry reason: reviewer cited MISSING test for outcome default to 'success'; coverage gap at line 444 success-path edit failure
- Added: test_outcome_defaults_to_success_when_omitted (FAILS: TypeError, outcome has no default - exposes AC violation)
- Added: test_success_edit_failure_returns_error (PASSES: code at line 444 already handles this, gap now closed)
- Preserved: 53 existing tests (all PASS)
- ruff: clean
- Commit: ef458da

[[2026-04-01]] Wed 07:56
## Builder Notes (retry)
- Fix: added Literal default outcome='success' to end_work signature
- Added Literal to typing import
- Files changed: packages/mcp-kanban/src/owlbear_mcp_kanban/server.py (2-line diff)
- Tests: 55 passed (was 53+2 new from test-writer retry)
- Coverage: 87% on server.py (pre-existing, no regression)
- Lint: ruff clean
- Commit: a96e2f0

[[2026-04-01]] Wed 14:03
## Review Evidence (retry 2)
See docs/scratch/471-reviewer.md for full evidence.

[[2026-04-01]] Wed 14:49
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | No convention or server-count changes; mcp-kanban tool-level docs live in SKILL.md |
| 2 | Docstrings | Yes | Pass | end_work in server.py has docstring covering all 4 outcomes (lines 405-411) |
| 3 | docs/sources/overview.md | Yes | Pass | ## end_work Compound Tool (Task #471) section already present (FastMCP + MCP Spec sources) |
| 4 | README.md | No | N/A | No CLI command changes |
| 5 | Research doc | Yes | Pass | docs/research/end-work-compound-tool.md exists; referenced in sources/overview.md |
| 6 | skills/mcp-kanban/SKILL.md | Yes | Pass | end_work row in Tools table + full end_work details section (confirmed by builder commit 45338b5) |

### Files Updated
- None

### Scratch Files Cleaned
- docs/scratch/471-reviewer.md (deleted)

[[2026-04-01]] Wed 16:00
## Audit
### AC Verification
All 14 AC lines verified with code evidence. Signature, outcome paths (success/fail/block/reject), AppContext.statuses caching, next-status derivation, validation, KANBAN_TOOLS_EXCLUDE, SKILL.md update all confirmed.

### Test Results
- pytest (mcp-kanban): 95 passed, 0 failed
- pytest (full suite): 222 failures, all pre-existing from unrelated tasks (quality-runner, rename-todo, skill-validation, stop-commit-guard-hooks, v2-test-infra, voice-channel)
- ruff: All checks passed

### Reviewer Evidence
Review Evidence section present (retry 2). Docs Gate passed with full checklist.

### AC Quality Score: 4
AC was thorough (14 verifiable lines). Minor gap: optional claim param added during architecture review, not in original AC. Well-documented refinement.

### Deduction breakdown: none
### Confidence: 1.0
### Action: archive

[[2026-04-01]] Wed 16:00
## Audit
### AC Verification
All 14 AC lines verified with code evidence. Signature, outcome paths (success/fail/block/reject), AppContext.statuses caching, next-status derivation, validation, KANBAN_TOOLS_EXCLUDE, SKILL.md update all confirmed.

### Test Results
- pytest (mcp-kanban): 95 passed, 0 failed
- pytest (full suite): 222 failures, all pre-existing from unrelated tasks (quality-runner, rename-todo, skill-validation, stop-commit-guard-hooks, v2-test-infra, voice-channel)
- ruff: All checks passed

### Reviewer Evidence
Review Evidence section present (retry 2). Docs Gate passed with full checklist.

### AC Quality Score: 4
AC was thorough (14 verifiable lines). Minor gap: optional claim param added during architecture review, not in original AC. Well-documented refinement.

### Deduction breakdown: none
### Confidence: 1.0
### Action: archive
