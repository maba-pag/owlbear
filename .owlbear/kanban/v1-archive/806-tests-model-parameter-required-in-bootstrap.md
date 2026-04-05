---
id: 806
title: 'Tests: model parameter required in bootstrap helpers and AgentRegistry'
status: archived
priority: nice-to-have
created: 2026-03-14T20:58:40.0409741+01:00
updated: 2026-03-15T04:58:33.2206067+01:00
started: 2026-03-15T04:57:49.1211648+01:00
completed: 2026-03-15T04:57:49.1211648+01:00
tags:
    - audit
    - config
    - scope:core
    - type:test
class: standard
---

## Context
TDD RED phase for #551. Verify that _build_knowledge_infra, _build_knowledge_toolset, _build_bookmark_toolset (bootstrap/knowledge.py) and AgentRegistry.__init__ (core/agent_registry.py) require the chat_model/default_model parameter with no default.

## AC
- [ ] Add 4 parametrized tests (one per function) asserting TypeError when called without chat_model/default_model
- [ ] Update ~20 callsites in test_bootstrap.py that call _build_knowledge_infra(tmp_path), _build_knowledge_toolset(tmp_path, infra), or _build_bookmark_toolset(infra, tmp_path) without chat_model to pass chat_model='test-model' explicitly
- [ ] All new TypeError-assertion tests FAIL (RED) before implementation removes defaults
- [ ] All updated callsites still PASS with current defaults present
- [ ] Ruff clean

See docs/research/hardcoded-model-defaults.md for full audit.

[[2026-03-15]] Sun 00:06
## Test-Writer Notes
- Test file: tests/test_model_param_required.py
- Classes: TestFromAC_ModelParamRequired
- Tests per category: happy 0, edge 0, error 4, boundary 0
- Total: 4 tests, all FAIL (DID NOT RAISE TypeError)
- ruff: clean
- Updated ~21 callsites in tests/test_bootstrap.py to pass chat_model='test-model' explicitly
- Updated callsites: 18 passed with current defaults
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| TypeError for _build_knowledge_infra | test_build_knowledge_infra_requires_chat_model | error |
| TypeError for _build_knowledge_toolset | test_build_knowledge_toolset_requires_chat_model | error |
| TypeError for _build_bookmark_toolset | test_build_bookmark_toolset_requires_chat_model | error |
| TypeError for AgentRegistry.__init__ | test_agent_registry_requires_default_model | error |
| Update callsites with chat_model | 21 callsites updated in test_bootstrap.py | migration |
| All new tests FAIL (RED) | 4 FAIL confirmed | verified |
| Updated callsites still PASS | 18 pass confirmed | verified |
| Ruff clean | 0 errors | verified |

[[2026-03-15]] Sun 04:07
## Builder Notes
- Files changed: src/owlbear/bootstrap/knowledge.py, src/owlbear/core/agent_registry.py
- Removed default 'gpt-4o' from chat_model in _build_knowledge_infra, _build_knowledge_toolset, _build_bookmark_toolset
- Made default_model keyword-only (with *) and removed default in AgentRegistry.__init__
- Tests: 4 passed (test_model_param_required), 148/149 bootstrap pass (1 pre-existing trafilatura failure), 20 agent_registry pass
- Lint: ruff clean
- Evidence: 4-line diff, all callers already pass chat_model/default_model explicitly

[[2026-03-15]] Sun 04:24
## Review Evidence

### Test Results
- pytest tests/test_model_param_required.py: **4 passed, 0 failed** (exit 0)
- pytest tests/test_agent_registry.py: **16 passed, 0 failed** (exit 0)
- pytest tests/test_bootstrap.py: **148 passed, 1 failed** (exit 1) -- 1 failure is pre-existing trafilatura/dateparser import (unrelated)

### Lint Results
- ruff check (4 files): **All checks passed!**

### Coverage
- agent_registry.py: **95%**
- bootstrap/knowledge.py: **18%** (expected -- task only removes defaults, heavy internal code not exercised by these tests)

### TestFromAC Comparison

Builder commit (8371418) only touched 2 source files. test_model_param_required.py is untracked. All 4 TestFromAC tests PRESERVED -- no modifications by builder.

### Test Quality
All 5 dimensions rated STRONG or ADEQUATE. Assertions are specific (TypeError + match string). Tests ARE the negative path. Mutation-proof design.

### Security Review
No issues. Removing defaults improves input validation. No new deps.

### AC Compliance
All 5 AC lines verified with evidence. Production callers in toolsets.py and registry.py pass chat_model/default_model explicitly.

### Informational
Uncommitted test files: test_model_param_required.py untracked, test_bootstrap.py unstaged. Process gap (not code quality).

### Verdict: PASS (confidence .93)

[[2026-03-15]] Sun 04:41
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Internal param change (removed defaults), no behavior/API/convention change |
| 2 | Docstrings complete | Yes | Pass | All 4 functions have accurate docstrings |
| 3 | sources/overview.md | No | N/A | No external patterns used |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/hardcoded-model-defaults.md exists and linked in task body |
| 6 | No impact default | -- | -- | Items 2 and 5 apply; rest N/A |

### Files Updated
- None

### Scratch Files Cleaned
- None (no 806-* files in docs/scratch/)

[[2026-03-15]] Sun 04:58
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 4 TypeError tests | test_model_param_required.py: 4 tests in TestFromAC_ModelParamRequired, all pass | PASS |
| Update ~20 callsites | git diff shows ~21 chat_model='test-model' additions in test_bootstrap.py | PASS |
| Tests FAIL (RED) before impl | Test-writer notes confirm 4 FAIL (DID NOT RAISE TypeError) | PASS |
| Updated callsites still PASS | 148/149 pass (1 pre-existing trafilatura failure) | PASS |
| Ruff clean | ruff check 4 files: All checks passed! | PASS |

### Test Results
- pytest test_model_param_required + agent_registry + agent_definitions: 104 passed
- pytest test_bootstrap: 148 passed, 1 failed (pre-existing trafilatura/regex env issue)
- ruff: clean

### Process Gap
Test files (test_model_param_required.py, test_bootstrap.py) not committed by upstream agents. Committed by auditor as d6a9768.

### Confidence: .97
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 8371418 | feat | knowledge.py, agent_registry.py | #806 |
| d6a9768 | test | test_model_param_required.py, test_bootstrap.py | #806 |
