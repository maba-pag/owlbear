---
id: 1424
title: 'P1-03: Update doc-writer.agent.md — remove diagram responsibility'
status: review
priority: important
created: 2026-05-08T00:32:21.566488+00:00
updated: 2026-05-09T07:41:19.965937+00:00
tags:
- phase-1
- scope:shared
- brief:doc-writer-quality
parent: 1421
depends_on:
- 1423
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

Update `share/agents/doc-writer.agent.md`:

1. Remove all references to diagrams, Excalidraw, `.excalidraw` files from persona, critical_rules, and any other sections (td:0)
2. Rewrite `critical_rules` item 5 ("Every checklist item needs evidence…") to explicitly name the 4-item checklist (README Verification, External Attribution, Research Doc, Deletion Detection), reference convention-based mapping (`serve/{pkg}/src/**` → `serve/{pkg}/README.md`), TODO marker insertion, and gate-blocking behavior (task-caused unverified content blocks the gate; pre-existing issues pass with a TODO marker). May expand into multiple rules. (td:1)
3. Persona remains focused on fact-checking/verification identity — no diagram editor role (td:0)
4. No functional regressions: tools list, pipeline_position, agents section, output_format remain structurally intact (td:1)

**In scope:** Agent definition file only. Must pass assertions from #1422.
**Out of scope:** Skill rewrite (#1423), prompt revision (#1425).

Brief: see parent #1421

[[2026-05-09]]
## Research
- Research doc: .owlbear/research/doc-writer-agent-update-1424.md
- Sources: 4 studied, 4 high-relevance (all internal)
- Recommendation: surgical edit to critical_rules section only (confidence: 0.95)

### Key Findings
- AC #1 (remove diagrams): already satisfied — zero diagram/excalidraw references in current agent file
- AC #2 (align critical_rules): GAP — current rules are generic; need to name 4-item checklist (README Verification, External Attribution, Research Doc, Deletion Detection), convention mapping, TODO markers, gate-blocking
- AC #3 (persona): already satisfied — fact-checking/verification identity
- AC #4 (no regressions): already satisfied — tools, pipeline_position, agents, output_format intact
- Dependency #1423 (w-doc-update v3) is done; all 56 tests from #1422 pass
- T1 classification — no architecture/security/breaking changes, simple agent file edit
[[2026-05-09]]
## Architecture Review

**Verdict:** APPROVED → todo

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| 1. Remove diagram/Excalidraw refs (td:0) | Already satisfied — grep-verified zero refs in current file | No-op; test-writer can skip (existing #1422 tests cover) |
| 2. Align critical_rules (td:1) | GAP — rule #5 is generic; must name 4-item checklist, convention mapping, TODO markers, gate-blocking | Refined AC to specify exact rule #5 target and required content |
| 3. Persona fact-checking identity (td:0) | Already satisfied — "technical editor at regulated-industry publisher" | No change needed |
| 4. No functional regressions (td:1) | Already satisfied — tools, pipeline_position, agents, output_format intact | Smoke-testable |

### Architecture Notes
- Single-file edit to `share/agents/doc-writer.agent.md`, `critical_rules` section only
- Agent already delegates to `w-doc-update` skill (rule #1); new rules reinforce key behaviors that are failure-prone when only in skill text
- No dependency direction violations, no new interfaces, no security surface
- T1 classification — no architecture/security/breaking changes

### Dependency Analysis
- #1423 (w-doc-update v3 skill rewrite): done (archived, confirmed by research and sibling task references)
- #1422 (test suite): 56 tests passing, covers diagram absence and skill content

### Challenger Results
- Verdict: reconsider (0.69)
- Valid concern: AC #2 was underspecified ("align critical_rules" without naming the target rule). Addressed by refining AC #2 to explicitly identify rule #5 and specify required content (4-item checklist names, convention mapping path pattern, TODO markers, gate-blocking semantics).
- Coverage mismatch note: existing #1422 tests don't cover AC #2 — expected, test-writer will create new tests for this task.
- Legacy fixture `tests/fixtures/doc_writer_v2_verification.md` references old diagram items — inert test data, does not affect agent file. No action needed.
[[2026-05-09]]
## Test-Writer Notes
- Test file: tests/test_doc_writer_agent_1424.py
- Classes: TestFromAC_CriticalRulesChecklist, TestFromAC_CriticalRulesConventionMapping, TestFromAC_CriticalRulesTodoMarkers, TestFromAC_CriticalRulesGateBlocking
- Tests per category: happy 10, edge 0, error 0, boundary 0
- Total: 10 tests, all FAIL (AssertionError)
- ruff: clean

### AC Coverage

| AC | Tests | Status |
|----|-------|--------|
| 1 — Remove diagrams (td:0) | skipped | td:0 — no tests needed; already satisfied per research |
| 2 — critical_rules names 4-item checklist, convention mapping, TODO markers, gate-blocking (td:1) | 10 tests | All FAIL ✓ |
| 3 — Persona fact-checking identity (td:0) | skipped | td:0 — no tests needed; already satisfied per research |
| 4 — No functional regressions (td:1) | 0 tests | Structural elements currently intact; regression-guard tests would pass pre-edit — excluded per RED protocol (tests existing behavior) |

### Note on AC #4
AC #4 structural elements (tools, pipeline_position, agents, output_format) are all present in the current agent file. Regression-guard tests would pass before the builder's edit, violating the RED protocol. Excluded per w-tdd-red: "If any passes, it tests existing behavior — remove or refine it." The existing #1422 test suite (56 tests) provides broad coverage of the agent/skill ecosystem and will catch structural regressions.

### Commit
adea84f8 — test: add failing tests for doc-writer critical_rules alignment (#1424, test-writer)
[[2026-05-09]]
## Builder Notes
- Implementation: updated share/agents/doc-writer.agent.md (critical_rules section only).
- Fixes applied:
  - Expanded checklist rule to explicitly name README Verification, External Attribution, Research Doc, and Deletion Detection.
  - Added convention-based mapping rule: serve/{pkg}/src/** -> serve/{pkg}/README.md.
  - Added TODO marker + gate behavior rule: task-caused unverified content blocks gate; pre-existing out-of-scope unverified content may pass only with a TODO marker.
- Tests: 10/10 TestFromAC passed in tests/test_doc_writer_agent_1424.py.
- Coverage: N/A for this scoped run (no source module imported for coverage instrumentation).
- ruff: clean.
- Evidence summary:
  - RED verified pre-change: 10 failed (all TestFromAC assertions failing as expected).
  - GREEN verified post-change: 10 passed, 0 failed.
  - Lint status: clean.
- Regression baseline: no durable module-level doc_writer_agent test file exists beyond tests/test_doc_writer_agent_1424.py.
- Commit: 10a77c2566a12d45a63cf084dabf05315c4df346 (only share/agents/doc-writer.agent.md staged).