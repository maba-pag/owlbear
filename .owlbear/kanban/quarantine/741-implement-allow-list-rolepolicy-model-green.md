---
id: 741
title: Implement allow-list RolePolicy model (GREEN)
status: archived
priority: needed
created: 2026-03-11T10:43:30.7903268+01:00
updated: 2026-03-11T19:56:12.9886182+01:00
started: 2026-03-11T18:50:31.0075564+01:00
completed: 2026-03-11T19:56:12.9886182+01:00
tags:
    - security
    - scope:core
depends_on:
    - 740
class: standard
---

TDD GREEN phase for #524 split. See docs/research/validator-role-policy.md Section 5.

AC:

1. RolePolicy gains allowed_tools: frozenset[str] field (default frozenset() = no restriction)
2. apply_role_policy filter: if allowed_tools non-empty, tool must be in allowed_tools AND not in denied_tools
3. VALIDATOR_POLICY redefined with allow-list per research doc Section 5, with these deviations from research:
   - INCLUDE run_command (validators need pytest/ruff execution, protected by CommandSafetyGuard)
   - INCLUDE kanban_edit and kanban_move (validators must append pipeline notes and advance task status per agent-common protocol)
   - EXCLUDE delegate_to_agent (validators report findings, orchestrator re-dispatches)
4. BUILDER_POLICY unchanged (empty allowed_tools = full access)
5. All tests in tests/test_roles.py pass (including RED phase tests from #740)
6. ruff check src/owlbear/core/roles.py clean

Design notes:

- Keep RolePolicy as frozen dataclass with slots
- Empty allowed_tools means no allowlist restriction (backwards-compatible)
- The apply_role_policy function signature is unchanged
- #561 addresses the double-build in AgentRegistry separately  do not refactor _build_agent here

Files: src/owlbear/core/roles.py
Ref: docs/research/validator-role-policy.md

[[2026-03-11]] Wed 16:58

## Test-Writer Notes

[[2026-03-11]] Wed 16:59

- Test file: tests/test_roles.py

[[2026-03-11]] Wed 16:59

- Modified 4 tests (run_command denial to acceptance per #741 deviations)

[[2026-03-11]] Wed 16:59

- New: TestFromAC_ValidatorPolicyDeviations741 (7), TestFromAC_BuilderPolicyUnchanged741 (2)

[[2026-03-11]] Wed 16:59

- Total: 13 new/modified tests, all FAIL

[[2026-03-11]] Wed 16:59

- AC3: run_command INCL, kanban_edit INCL, kanban_move INCL, delegate_to_agent EXCL

[[2026-03-11]] Wed 16:59

- AC4: builder unchanged (empty allowed_tools)

[[2026-03-11]] Wed 16:59

- ruff: clean

[[2026-03-11]] Wed 16:59
Modified 4 tests, added 9 new. Total 13, all FAIL. ruff clean.

[[2026-03-11]] Wed 17:49

## Builder Notes

- Files changed: src/owlbear/core/roles.py, src/owlbear/core/agent_registry.py
- Tests: 57 passed (was 36 FAIL + 13 pass, now all 57 pass)
- Coverage: roles.py 100%, agent_registry.py 75%
- Lint: ruff clean (all checks passed)
- Changes: (1) Added allowed_tools field to RolePolicy dataclass, (2) Redefined VALIDATOR_POLICY with 25-tool allow-list per AC3 deviations (run_command, kanban_edit, kanban_move included; delegate_to_agent excluded), (3) Updated apply_role_policy to check allow-list + deny-list, (4) Fixed agent_registry condition to trigger on allowed_tools too
- BUILDER_POLICY unchanged (empty allowed_tools = full access)

[[2026-03-11]] Wed 18:50

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Internal extension to existing RolePolicy; no new top-level convention |
| 2 | Docstrings complete | Yes | Pass | RolePolicy, apply_role_policy, BUILDER_POLICY, VALIDATOR_POLICY all have accurate docstrings |
| 3 | sources/overview.md | No | N/A | External sources (OWASP, NeMo) already attributed under #524 |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/validator-role-policy.md exists, linked in task body |

### Files Updated

- None

### Scratch Files Cleaned

- None (no 741-* scratch files found)

[[2026-03-11]] Wed 19:56

## Audit

### AC Verification

| AC | Evidence | Status |
|-----|----------|--------|
| AC1: allowed_tools frozenset field | roles.py L53: `allowed_tools: frozenset[str] = frozenset()` on frozen dataclass | PASS |
| AC2: apply_role_policy filter logic | roles.py L118-128: denied check first, then allow-list check. 57 tests confirm both paths | PASS |
| AC3: VALIDATOR_POLICY allow-list w/ deviations | roles.py L67-103: 25-tool allow-list. run_command IN, kanban_edit IN, kanban_move IN, delegate_to_agent OUT | PASS |
| AC4: BUILDER_POLICY unchanged | roles.py L61-63: empty denied_tools, no allowed_tools field = full access | PASS |
| AC5: All tests pass | pytest: 57 passed, 0 failed (0.66s) incl RED phase from #740 | PASS |
| AC6: ruff clean | ruff check roles.py + test_roles.py: All checks passed | PASS |

### Test Results

- pytest tests/test_roles.py: 57 passed, 0 failed
- ruff check src/owlbear/core/roles.py tests/test_roles.py: All checks passed

### Confidence: .97

### Action: archive
