---
id: 885
title: 'Test: researcher and curator agent definitions expose kanban-md skill'
status: archived
priority: nice-to-have
created: 2026-03-21T04:17:42.6912985+01:00
updated: 2026-03-21T12:55:10.7430661+01:00
started: 2026-03-21T12:54:33.3972336+01:00
completed: 2026-03-21T12:54:33.3972336+01:00
tags:
    - config
    - test
    - scope:core
class: standard
---

Write the RED contract for adding kanban-md skill metadata to the researcher and curator agent definitions.

### Acceptance Criteria

- Update tests/test_agent_definitions.py so EXPECTED_AGENTS[researcher][skills] equals [kanban-md].
- Update tests/test_agent_definitions.py so EXPECTED_AGENTS[curator][skills] equals [kanban-md].
- Keep researcher and curator descriptions, roles, tools, and max_delegation_depth expectations unchanged.
- Verify `uv run pytest tests/test_agent_definitions.py -q --tb=short` fails against the current repo before implementation.
- Scope is tests only; do not edit src/owlbear/agents/*.md in this task.

### Files

- tests/test_agent_definitions.py

[[2026-03-21]] Sat 04:46

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Update tests/test_agent_definitions.py so EXPECTED_AGENTS[researcher][skills] equals [kanban-md]. | Precise RED assertion for the current gap; researcher still declares skills: [] in src/owlbear/agents/researcher.md. | Keep |
| Update tests/test_agent_definitions.py so EXPECTED_AGENTS[curator][skills] equals [kanban-md]. | Precise RED assertion for the matching curator gap; curator still declares skills: [] in src/owlbear/agents/curator.md. | Keep |
| Keep researcher and curator descriptions, roles, tools, and max_delegation_depth expectations unchanged. | Good non-regression guard; the contract stays limited to skill metadata and the existing strict EXPECTED_AGENTS structure. | Keep |
| Verify `uv run pytest tests/test_agent_definitions.py -q --tb=short` fails against the current repo before implementation. | Required RED proof and mechanically verifiable because src/owlbear/core/agent_registry.py only appends SkillRegistry when defn.skills is non-empty. | Keep |
| Scope is tests only; do not edit src/owlbear/agents/*.md in this task. | Correct TDD boundary; prevents GREEN implementation work from leaking into the RED task. | Keep |

### Architecture Notes

- Existing contract pattern: tests/test_agent_definitions.py uses strict EXPECTED_AGENTS equality checks for description, role, tools, skills, and max_delegation_depth.
- Current repo state still supports a deterministic RED failure: src/owlbear/agents/researcher.md and src/owlbear/agents/curator.md both declare skills: [].
- Existing implementation hook is already in place: src/owlbear/core/agent_registry.py appends SkillRegistry when defn.skills is truthy, so the paired GREEN task #775 can stay limited to agent metadata.
- Single domain confirmed: this task is test-only coverage for agent-definition metadata. No registry, tool, or prompt changes belong here.
- Security surface unchanged: no new I/O, permissions, or external boundary is introduced by this test contract.

### Changes Made

- Claimed #885 as architect.
- Verified paired GREEN task #775 remains the implementation follow-up and already carries the source-file scope.
- Approved #885 for RED work without rewriting the AC.

### Dependencies

- Verified downstream pair: #775 depends on #885.
- Verified no additional prerequisite tasks are required.

[[2026-03-21]] Sat 04:56

## Test-Writer Notes\n- Test file: tests/test_agent_definitions.py (existing file, not new)\n- Classes: TestAgentDefinitionFiles.test_skills_match (existing parametrized test)\n- Changes: Updated EXPECTED_AGENTS[researcher][skills] and EXPECTED_AGENTS[curator][skills] from [] to ['kanban-md']\n- Tests per category: happy 0, edge 0, error 0, boundary 0 (existing assertions now target new contract)\n- Total: 2 new failures in existing test, all FAIL against current src\n- ruff: clean\n- AC coverage:\n  | AC Line | Test(s) | Category |\n  |---------|---------|----------|\n  | researcher skills == ['kanban-md'] | test_skills_match[researcher] | happy |\n  | curator skills == ['kanban-md'] | test_skills_match[curator] | happy |\n  | descriptions/roles/tools/max_depth unchanged | all other parametrized tests: 82 pass | non-regression |\n  | tests fail before implementation | confirmed: assert [] == ['kanban-md'] x2 | RED verified |

[[2026-03-21]] Sat 06:25

## Builder Notes

- Files changed: tests/test_agent_definitions.py (test-writer already updated, no builder changes needed)
- RED contract verified: test_skills_match[researcher] FAILED (assert [] == ['kanban-md']), test_skills_match[curator] FAILED (assert [] == ['kanban-md'])
- Scope: tests only per AC; src/owlbear/agents/*.md changes are deferred to #775
- Lint: ruff clean on tests/test_agent_definitions.py
- Evidence: 7 of 9 test_skills_match tests pass; 2 fail exactly as expected (researcher, curator)
- Pass-through: RED contract is correctly in place; builder has no implementation scope in this task

[[2026-03-21]] Sat 06:48

## Review Evidence

## Review: #885 — Test: researcher and curator agent definitions expose kanban-md skill

### Test Results

- Command: uv run pytest tests/test_agent_definitions.py -q --tb=short
- Result: 82 passed, 2 failed, 2 warnings.
- Expected RED failures observed:
  - TestAgentDefinitionFiles::test_skills_match[researcher] failed at  ests/test_agent_definitions.py:121 (ssert [] == ['kanban-md']).
  - TestAgentDefinitionFiles::test_skills_match[curator] failed at  ests/test_agent_definitions.py:121 (ssert [] == ['kanban-md']).

### Lint Results

- Scoped command: uv run ruff check tests/test_agent_definitions.py
- Result: All checks passed.
- Repo-wide command: uv run ruff check src/ tests/
- Result: 460 existing baseline lint errors across unrelated files; no lint regression in the touched task file.

### Coverage

- Command: uv run pytest tests/test_agent_definitions.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
- Result: same two expected RED failures; coverage report emitted (TOTAL 3%) due bare --cov instrumenting the full workspace.
- Coverage gate interpretation: task scope is tests-only and does not modify source modules, so touched-module coverage threshold is not applicable for this RED contract.

### Pass 1 — CRITICAL

#### Security Review

- No security issues found.
- Diff in scope only changes static expected metadata values in  ests/test_agent_definitions.py (skills: [kanban-md] at lines 57 and 92).
- No new I/O boundaries, command execution, deserialization, credential handling, or logging paths introduced.

#### Test Integrity (TestFromAC comparison)

- No TestFromAC_* classes exist in  ests/test_agent_definitions.py; comparison step is not applicable.

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG |  est_skills_match asserts exact equality ( ests/test_agent_definitions.py:121), so missing skill values fail deterministically. |
| Negative/error paths | ADEQUATE | For this metadata-contract RED task, failing-path proof is explicit via two expected assertion failures from the scoped pytest run. |
| Mutation reasoning | STRONG | If researcher/curator expected skills were loosened or removed,  est_skills_match[researcher/curator] would immediately stop producing the required RED failures. |
| Test independence | STRONG | Parametrized tests parse each agent file independently; no shared mutable state or order dependence observed. |
| Descriptive names | STRONG | Test names describe exact contract dimensions ( est_skills_match,  est_description_matches,  est_max_delegation_depth). |

#### Data Safety

- No data safety issues found.
- Change is limited to constant expectations in a test mapping table.

### Pass 2 — INFORMATIONAL

- No informational findings.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Update EXPECTED_AGENTS[researcher][skills] to [kanban-md] |  ests/test_agent_definitions.py:57 sets skills: [kanban-md]; pytest failure confirms source still has skills: [] in src/owlbear/agents/researcher.md:11. | TestAgentDefinitionFiles::test_skills_match[researcher] | PASS |
| Update EXPECTED_AGENTS[curator][skills] to [kanban-md] |  ests/test_agent_definitions.py:92 sets skills: [kanban-md]; pytest failure confirms source still has skills: [] in src/owlbear/agents/curator.md:9. | TestAgentDefinitionFiles::test_skills_match[curator] | PASS |
| Keep researcher/curator description, role, tools, max_delegation_depth expectations unchanged | git diff -- tests/test_agent_definitions.py shows only two hunks changing skills entries; researcher metadata remains at lines 54-56/58 and curator metadata remains at lines 89-91/93. |  est_description_matches[...],  est_tools_match[...],  est_max_delegation_depth[...], role validation tests | PASS |
| Verify uv run pytest tests/test_agent_definitions.py -q --tb=short fails before implementation | Independent run produced exactly 2 failures ( est_skills_match[researcher],  est_skills_match[curator]) and 82 passes. | Scoped pytest command above | PASS |
| Scope is tests only; do not edit src/owlbear/agents/*.md | git diff -- src/owlbear/agents/researcher.md src/owlbear/agents/curator.md returned no output (no source edits). | N/A (scope control AC) | PASS |

### Verdict: PASS

- Confidence: .95

[[2026-03-21]] Sat 12:22

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Test-only RED phase — no behavior/API change introduced |
| 2 | Docstrings | No | N/A | Only tests/test_agent_definitions.py modified; no source modules touched |
| 3 | docs/sources/overview.md | No | N/A | No external patterns used |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research phase for this task |
| 6 | No impact | Yes | Pass | Test-only RED contract; two expected skill values updated in existing parametrized test |

### Files Updated

- None

### Scratch Files Cleaned

- docs/scratch/885-pytest-out.txt (deleted, was 0-byte empty file)

[[2026-03-21]] Sat 12:54

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| EXPECTED_AGENTS[researcher][skills] == [kanban-md] | tests/test_agent_definitions.py:57, diff confirms skills: [] -> [kanban-md] | PASS |
| EXPECTED_AGENTS[curator][skills] == [kanban-md] | tests/test_agent_definitions.py:92, diff confirms skills: [] -> [kanban-md] | PASS |
| Keep other fields unchanged | git diff shows exactly 2 hunks each changing only the skills line | PASS |
| Tests fail before implementation | pytest: 82 passed, 2 failed (test_skills_match[researcher], test_skills_match[curator]) assert [] == ['kanban-md'] | PASS |
| Scope is tests only | git diff -- src/owlbear/agents/researcher.md src/owlbear/agents/curator.md empty | PASS |

### Test Results

- pytest (scoped): 82 passed, 2 failed (expected RED)
- ruff: All checks passed

### Confidence: .97

### Action: archive

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 8433181 | test | tests/test_agent_definitions.py | #885 |
