---
id: 561
title: Apply role policy before Agent construction to avoid double-build
status: archived
priority: someday
created: 2026-03-04T07:39:04.0573106+01:00
updated: 2026-03-16T05:07:06.7246212+01:00
started: 2026-03-07T02:20:43.1600761+01:00
completed: 2026-03-16T05:07:02.3405393+01:00
tags:
    - audit
    - code-quality
    - scope:core
depends_on:
    - 827
class: standard
---

F-20: Double Agent construction in _build_agent() when role != BUILDER. See docs/research/role-policy-before-agent-construction.md for analysis.

## AC

- [ ] _build_agent constructs exactly one Agent() call per invocation, regardless of role
- [ ] Role policy filtering (apply_role_policy) applied to toolsets BEFORE the single Agent() call
- [ ] Guard condition preserved: filter only when policy.denied_tools or policy.allowed_tools is non-empty
- [ ] Existing tests pass (test_agent_registry.py, test_roles.py, test_bootstrap_integration.py)
- [ ] ruff clean

Target file: src/owlbear/core/agent_registry.py (_build_agent method)
Test task: #827

## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Single Agent() call per invocation | Clear, verifiable by mocking Agent and checking call_count | Keep |
| apply_role_policy before Agent() | Clear, verifiable by code inspection | Keep |
| Guard: denied_tools or allowed_tools | Precise  matches current code guard. Research doc only mentioned denied_tools; fixed in AC | Refined |
| Existing tests pass | Standard gate | Keep |
| ruff clean | Standard gate | Keep |

### Architecture Notes
- **Single domain:** scope:core only. Change is internal to agent_registry._build_agent.
- **Module layering:** No new imports. Uses already-imported apply_role_policy from core.roles.
- **Pattern consistency:** Follows the pattern documented in roles.py  filter before construct.
- **TDD compliance:** Created #827 as preceding test task. #561 now depends_on #827.
- **Security surface:** None  no new system boundaries or user-facing changes.
- **KISS:** Minimal diff (~10 lines changed). No new abstractions.
- **Research gap fixed:** Research doc recommended `if policy.denied_tools` guard but actual code uses `if policy.denied_tools or policy.allowed_tools`. AC now specifies the correct combined guard.

### Changes Made
- Refined AC: removed bundled test assertion (moved to #827), added precise guard condition, added target file reference
- Created test task #827 (Tests for single Agent construction in _build_agent)
- Fixed dependency: #561 depends_on #827 (TDD ordering)

### Dependencies
- Added: #827 (test task)  must run RED before implementation
- No other external dependencies

[[2026-03-15]] Sun 14:00
## Test-Writer Notes
- Test task #827 already provides RED coverage in tests/test_agent_registry.py
- Class: TestFromAC_SingleAgentConstruction (3 tests, all GREEN from #827 builder)
- Implementation already live — cannot write RED tests (all would pass)
- AC coverage from #827:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| Single Agent() per invocation | test_validator_role_calls_agent_exactly_once | happy |
| Single Agent() per invocation | test_builder_role_calls_agent_exactly_once | happy |
| apply_role_policy BEFORE Agent() | test_validator_role_passes_filtered_toolsets | happy |
| Guard condition (denied or allowed non-empty) | GAP - suggest TestBuilderDiscovered | edge |
| Existing tests pass | 19 passed | regression |

- Note: Guard condition gap exists. Builder should add TestBuilderDiscovered test verifying apply_role_policy is NOT called when policy has both denied_tools and allowed_tools empty (e.g. BUILDER_POLICY on a non-builder role).

[[2026-03-15]] Sun 20:14
## Builder Notes
- Files changed: tests/test_agent_registry.py (1 TestBuilderDiscovered test added)
- Source: src/owlbear/core/agent_registry.py already correct (from #827)
- Tests: 20 passed, coverage 95% on agent_registry.py
- Lint: ruff clean
- Guard condition gap filled: test_empty_policy_skips_apply_role_policy verifies apply_role_policy NOT called when both denied_tools and allowed_tools are empty
- Commit: 8132849

[[2026-03-15]] Sun 21:00
## Review Evidence
See docs/scratch/561-reviewer.md for full evidence.

Verdict: PASS (confidence .92)

[[2026-03-15]] Sun 21:19
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Internal refactor of _build_agent; no behavior/API/convention change |
| 2 | Docstrings complete | Yes | Updated | Added role-policy filtering note to _build_agent docstring in agent_registry.py |
| 3 | sources/overview.md | No | N/A | Sources already logged (PydanticAI Agent docs, FilteredToolset) from research phase |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/role-policy-before-agent-construction.md exists and linked in task body line 1 |
| 6 | No impact | N/A | N/A | Items 2 and 5 applied |

### Files Updated
- src/owlbear/core/agent_registry.py (docstring only â€” added role-policy note to _build_agent)

### Scratch Files Cleaned
- Deleted docs/scratch/561-claim-err.txt, 561-claim.txt, 561-reviewer.md

[[2026-03-16]] Mon 05:04
## Audit
Confidence: .95 | Action: archive
