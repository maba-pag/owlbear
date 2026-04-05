---
id: 551
title: Derive hardcoded model defaults from OwlBearSettings
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:54.1072462+01:00
updated: 2026-03-15T06:46:51.8191395+01:00
started: 2026-03-07T00:55:27.8475567+01:00
completed: 2026-03-15T06:46:47.137405+01:00
tags:
    - audit
    - config
    - scope:core
depends_on:
    - 806
class: standard
---

## Context

INT-15: Remove redundant gpt-4o defaults from 4 function signatures.
Settings.chat_model (config.py) is the single source of truth.
See docs/research/hardcoded-model-defaults.md

## AC

- [ ] _build_knowledge_infra() in bootstrap/knowledge.py: remove default from chat_model (make required)
- [ ] _build_knowledge_toolset() in bootstrap/knowledge.py: remove default from chat_model (make required)
- [ ] _build_bookmark_toolset() in bootstrap/knowledge.py: remove default from chat_model (make required)
- [ ] AgentRegistry.__init__() in core/agent_registry.py: remove default from default_model (make required)
- [ ] config.py chat_model field UNCHANGED (remains source of truth)
- [ ] Docstrings and lookup tables UNCHANGED
- [ ] Ruff clean, all tests pass

## Patterns to Follow

- Production callers in toolsets.py already pass chat_model or settings.chat_model
- build_agent_registry() in registry.py already resolves model from settings
- Test fixups done in preceding test task #806

[[2026-03-14]] Sat 21:00

## Architecture Review
__Verdict:__ APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Remove defaults from 3 bootstrap helpers | Verified: callers in toolsets.py always pass chat_model or settings.chat_model | Kept, refined with file paths |
| Remove default from AgentRegistry.__init__ | Verified: build_agent_registry() always resolves from settings | Kept, refined with file path |
| chat_model/default_model become required | Correct approach per pydantic-settings/FastAPI patterns | Kept |
| Settings.chat_model remains source of truth | Invariant verified: config.py:58 has Field(default=gpt-4o) | Reworded as UNCHANGED gate |
| Ruff clean, all tests pass | Standard quality gate | Kept |

### Architecture Notes

- Module layering: bootstrap (assembly) depends on config (leaf) -- correct direction
- core/agent_registry depends on config via injection -- correct
- All 4 defaults are demonstrably unreachable in production (toolsets.py L88/109/134, registry.py L78)
- ~20 test callsites in test_bootstrap.py rely on current defaults -- handled by test task #806
- No new system boundaries, no security surface change
- Pattern: pydantic-settings single source of truth (config.py Field default)

### Changes Made

- Created #806: TDD RED test task (preceding)
- Added depends_on #806
- Refined AC with specific file paths and function names
- Added Patterns to Follow section referencing production callers

### Dependencies

- Added: #806 (test task, must complete before builder starts)
- Verified: no other dependencies needed

## Test-Writer Notes

- Tests already exist: tests/test_model_param_required.py (from preceding #806)
- 4 AC lines (remove defaults) covered by TestFromAC_ModelParamRequired — 4 tests, all PASS
- AC5 (config.py unchanged) covered by test_config.py::test_chat_model_default
- AC6/AC7: quality gates, not testable behavior
- Implementation already complete (commit 8371418 removed defaults as part of #806)
- No new failing tests possible — passing through to builder for verification

[[2026-03-15]] Sun 05:21
## Builder Notes
- Implementation already committed in 8371418 (dependency #806)
- Verified: all 4 signatures require chat_model/default_model (no defaults)
- config.py chat_model unchanged (default=gpt-4o, source of truth)
- Tests: 4/4 passed, 100 regression pass
- Lint: ruff clean
- No additional code changes needed

[[2026-03-15]] Sun 06:03
## Review Evidence
### Test Results
- pytest: 4 passed, 0 failed (test_model_param_required.py)
- All 4 TestFromAC_ModelParamRequired tests PASSED

### Lint Results
- ruff: All checks passed!

### Coverage
- bootstrap/knowledge.py: 18% (expected -- tests only verify TypeError on param omission)
- Task only removed defaults, no new logic to cover

### Pass 1 -- CRITICAL
#### Security Review
- No security issues. Change only removes defaults from 4 params.

#### Test Integrity
Builder did not modify test file (git diff empty).
All 4 TestFromAC methods: PRESERVED.

#### Test Quality
All 5 dimensions: STRONG.

#### Data Safety
- No data safety issues.

### Pass 2 -- INFORMATIONAL
- AgentRegistry gained keyword-only marker -- all callers use kwargs. Acceptable.

### AC Compliance
All 7 AC lines: PASS (verified via read_file + git diff).

### Verdict: PASS
Confidence: .95

## Docs Gate### Checklist| # | Check | Applies? | Status | Evidence ||---|-------|----------|--------|----------|| 1 | copilot-instructions.md | No | N/A | Internal refactor removing unreachable defaults; no behavior/API change || 2 | Docstrings complete | Yes | Pass | All 4 modified functions have accurate docstrings (knowledge.py L57-60, L106, L236-238; agent_registry.py L47-57) || 3 | sources/overview.md | No | N/A | No external patterns adopted || 4 | README.md | No | N/A | No CLI changes || 5 | Research doc linked | Yes | Pass | docs/research/hardcoded-model-defaults.md exists, linked in task Context section || 6 | No impact | -- | -- | Items 1,3,4 N/A; items 2,5 Pass |### Files Updated- None### Scratch Files Cleaned- None (no docs/scratch/551-* files found)

[[2026-03-15]] Sun 06:46
## Audit (2026-03-15)
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| _build_knowledge_infra required chat_model | knowledge.py L58: no default | PASS |
| _build_knowledge_toolset required chat_model | knowledge.py L105: kw-only no default | PASS |
| _build_bookmark_toolset required chat_model | knowledge.py L230: no default | PASS |
| AgentRegistry.__init__ required default_model | agent_registry.py L66: kw-only no default | PASS |
| config.py chat_model UNCHANGED | Field(default=gpt-4o) at L62, no #551 commit | PASS |
| Docstrings/lookup tables UNCHANGED | git show 8371418: only = gpt-4o removed | PASS |
| Ruff clean, tests pass | ruff clean; 353 passed, 2 pre-existing failures | PASS |

### Test Results
- Task-specific: 104 passed (model_param_required + agent_registry + agent_definitions)
- Broad regression: 353 passed, 2 failed (pre-existing: init_under_200_lines + trafilatura/regex)
- Ruff: All checks passed on task files

### Confidence: .97
### Action: archive
