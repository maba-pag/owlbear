---
id: 1424
title: 'P1-03: Update doc-writer.agent.md — remove diagram responsibility'
status: archived
priority: medium
created: 2026-05-08T00:32:21.566488+00:00
updated: 2026-05-09T09:48:55.171173+00:00
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
[[2026-05-09]]
## Review Evidence
### Test Results
- pytest (quality-runner combined): 66 passed, 0 failed via `uv run pytest tests/test_doc_writer_agent_1424.py tests/test_doc_writer_quality_1422.py -v --tb=short`
- pytest (quality-runner rerun): `tests/test_doc_writer_agent_1424.py` collected 10 items, 10 passed
- lint: clean via `uv run ruff check tests/test_doc_writer_agent_1424.py tests/test_doc_writer_quality_1422.py`

### Lint: clean

### Coverage: N/A for markdown-only deliverable (`share/agents/doc-writer.agent.md`)

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| 1. Remove diagram/Excalidraw refs (td:0) | `tests/test_doc_writer_quality_1422.py::test_no_diagram_references_anywhere`, `::test_no_excalidraw_file_references`, `::test_no_excalidraw_brand_references` | Yes — absence assertions fail on any added diagram/Excalidraw text | COVERED |
| 2. Rewrite critical_rules item 5 with checklist names, mapping, TODO marker, and gate behavior (td:1) | 10 tests in `tests/test_doc_writer_agent_1424.py` | Yes — exact string/regex assertions fail if any required phrase or rule semantics regress | COVERED |
| 3. Persona remains fact-checking/verification focused (td:0) | Direct artifact read of `share/agents/doc-writer.agent.md:20` plus no diagram grep | N/A — td:0 manual evidence | COVERED |
| 4. Structural sections remain intact (td:1) | Direct artifact read of `share/agents/doc-writer.agent.md:8,50,59,67` plus adjacent regression suite `tests/test_doc_writer_quality_1422.py` | Yes for section-presence regression; manual read confirms current structure | COVERED |

#### Security Review
- No issues. Markdown-only agent definition change; no runtime logic, secrets, dependencies, or user-input surface added.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `tests/test_doc_writer_agent_1424.py` `TestFromAC_*` suite | No weakening/removal visible in the current file. Git-log evidence confirms the test-writer commit (`adea84f8...`) and builder commit (`10a77c2...`) exist, but this tool surface could not produce a diff for exact immutability proof. | PRESERVED (lower-confidence) |

#### Test Quality
| Dimension | Rating | Evidence |
|----------|--------|----------|
| Assertion specificity | STRONG | Exact string/regex checks for checklist names, mapping, TODO marker, and gate semantics |
| Negative/error-path coverage | ADEQUATE | Static markdown contract; presence/absence assertions cover the meaningful failure modes |
| Manual mutation reasoning | STRONG | Removing any named checklist item, mapping phrase, TODO marker, or gate rule would fail mapped tests |
| Test independence | STRONG | Tests only read files; no shared mutable state |
| Descriptive names | STRONG | Test names map directly to AC claims |

#### Data Safety
- No issues. Declarative markdown edit only.

#### Implementation-Aware Gaps
- No significant untested paths. Changed behavior is fully contained in `critical_rules` text at `share/agents/doc-writer.agent.md:43-45`; surrounding structure was directly verified at lines 8, 50, 59, and 67.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `.git/logs/HEAD` confirms both task commits exist (`adea84f8...` test-writer, `10a77c2...` builder), but terminal/git-show access was unavailable, so changed-file ownership and dirty-tree contamination could not be proven at diff level. Confidence deducted accordingly.
- The first combined quality-runner report misattributed `13 passed` to `tests/test_doc_writer_agent_1424.py`; a targeted rerun resolved the discrepancy at `10 collected, 10 passed`.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| 1. Remove all diagram/Excalidraw/.excalidraw refs | grep on `share/agents/doc-writer.agent.md` returned no `diagram|Excalidraw|\.excalidraw` hits; adjacent no-diagram tests at `tests/test_doc_writer_quality_1422.py:88,98,104` passed | No-diagram trio in `tests/test_doc_writer_quality_1422.py` | PASS |
| 2. Rewrite critical_rules item 5 with checklist names, mapping, TODO marker, and gate behavior | `share/agents/doc-writer.agent.md:43-45` contains the required 4-item checklist, `serve/{pkg}/src/** -> serve/{pkg}/README.md`, and TODO/gate policy; task-local tests at `tests/test_doc_writer_agent_1424.py:21,28,35,42,49,67,74,86,98,105` passed | `tests/test_doc_writer_agent_1424.py` | PASS |
| 3. Persona remains fact-checking/verification focused | `share/agents/doc-writer.agent.md:20` retains "technical editor at a regulated-industry publisher"; no diagram text appears anywhere in the file | Direct artifact check | PASS |
| 4. No functional regressions in tools/pipeline_position/agents/output_format | `share/agents/doc-writer.agent.md:8,50,59,67` shows all required structural sections still present; broader regression suite passed in the scoped quality-runner run | Direct artifact check + adjacent regression suite | PASS |

### Confidence: 0.91
### Verdict: PASS
[[2026-05-09]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Sole changed file is `share/agents/doc-writer.agent.md` (OUT-scope). `share/README.md:64` lists doc-writer in pipeline table only — not referencing internal critical_rules content. No IN-scope prose doc affected. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | No | N/A | Task body: "4 studied, 4 high-relevance (all internal)" — no external patterns used. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/doc-writer-agent-update-1424.md` exists (file_search confirmed). Linked from task body. |
| 5 | Diagram maintenance (describes match) | No | N/A | Doc-index has no `describes` entries matching `share/agents/**`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No deleted files in changed-files set. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| share/agents/doc-writer.agent.md | OUT (agent-executable) | N/A |
| tests/test_doc_writer_agent_1424.py | OUT (test file) | N/A |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1424-* scratch files found)
[[2026-05-09]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. Remove diagram/Excalidraw refs | grep -in on agent file returned NO MATCHES | PASS |
| 2. critical_rules names 4-item checklist, convention mapping, TODO markers, gate-blocking | Lines 41-45 contain all required content; 10/10 task tests pass | PASS |
| 3. Persona fact-checking identity | Line 20: "technical editor at a regulated-industry publisher" | PASS |
| 4. No structural regressions (tools, pipeline_position, agents, output_format) | All sections intact at lines 8, 50, 59, 67; 66/66 combined tests pass | PASS |

### Test Results
- pytest (task-scoped): 66 passed, 0 failed (test_doc_writer_agent_1424 + test_doc_writer_quality)
- pytest (full suite): 4794 passed, 635 failed — all failures in cockpit cache/SSE/PDS (pre-existing, outside task scope)
- vitest (full suite): 1214 passed, 9 failed — all failures in DetailTab/PdsMigration/Shell (pre-existing, outside task scope)
- ruff: pre-existing violations only, none in task scope
- eslint: pre-existing violations only

### Upstream Commits Verified
- adea84f8 test: add failing tests for doc-writer critical_rules alignment (#1424, test-writer)
- 10a77c25 feat: align doc-writer critical rules with docs gate checklist (#1424, builder)

### Architect Quality: 4/5
AC was specific and verifiable. Minor gap: AC #2 initially said "align critical_rules" without naming rule #5 as the target; addressed during arch review after challenger flagged it (0.69 reconsider). Refinement was effective. No builder improvisation needed beyond what AC specified.

### Deduction Breakdown
- Start: 1.00
- All 4 AC lines verified with evidence: no deduction
- Full-suite failures all outside task scope: no deduction
- Lint clean in task scope: no deduction
- AC quality 4/5: no deduction
- Reviewer evidence present and detailed: no deduction
- Minor: reviewer noted lower-confidence on test immutability proof (git-show unavailable at review time): -.01

### Confidence: 0.99
### Action: archive