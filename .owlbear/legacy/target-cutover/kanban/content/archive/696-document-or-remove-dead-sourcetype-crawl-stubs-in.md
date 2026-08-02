---
id: 696
title: Document or remove dead SourceType.CRAWL stubs in knowledge engine
status: archived
priority: medium
created: 2026-04-08T21:31:29.3651006+02:00
updated: 2026-04-09T03:24:28.3678891+02:00
started: 2026-04-09T03:24:28.3678891+02:00
completed: 2026-04-09T03:24:28.3678891+02:00
tags:
    - scope:knowledge
    - ' source:research-684'
class: standard
---

## Context

The knowledge engine has `SourceType.CRAWL` in `serve/knowledge/src/owlbear_knowledge/models.py` and a `_handle_crawl` method in `RefreshOrchestrator` (`refresh.py`) that raises `ValueError` when no `crawl_handler` is injected. The manifest loader (`loader.py`) also accepts `crawl` as a valid source type.

This code is effectively dead — no crawl handler implementation exists in v2, and research #684 recommends deferring browser integration until demand materializes.

## Options

1. Remove `SourceType.CRAWL` + `_handle_crawl` + crawl from loader schema (clean deletion)
2. Keep stubs but add a docstring/comment marking them as planned integration points for future `serve/mcp-browser/`

## Acceptance Criteria

- [ ] AC1: Decision on remove vs document approach
- [ ] AC2: If removing: stubs deleted, tests updated, no dead code remains
- [ ] AC3: If documenting: clear `# FUTURE:` comment with reference to #684 research doc

[[2026-04-08]] Wed 22:02
## Research
- Research doc: .owlbear/research/dead-crawl-stubs-696.md
- Sources: 6 studied, 3 high-relevance (v2 source code 1.0, #684 research .95, prior crawl research .80)
- Recommendation: Remove all CRAWL stubs — dead code, wrong architectural pattern for v2 (confidence: .85)
- Key findings: (1) 25 LOC of dead production code + ~80 LOC dead tests across 8 files; (2) v2 future crawling would use MCP server pattern not handler injection; (3) trivial to restore from git history; (4) KISS/YAGNI aligned
- Follow-up tasks created: #703 (remove dead SourceType.CRAWL stubs from knowledge engine)
- Decision requests: none — T1 autonomous (dead code removal, no capability change)
- Challenge: FALLBACK — trivial dead-code cleanup, uncontroversial

[[2026-04-08]] Wed 22:18
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Decision scope only; implementation delegated to #703 |
| Interface clarity | PASS | Research section documents decision + rationale clearly |
| Dependency correctness | PASS | No deps; #703 created as independent follow-up |
| Module layering | N/A | Research/decision task, no code output |
| TDD compliance | N/A | No code output |
| KISS/YAGNI | PASS | Decision aligns with KISS/YAGNI (remove dead code) |
| Premise challenge | PASS | Dead code confirmed in codebase — 25 LOC production, ~80 LOC tests, zero consumers |
| Pattern consistency | PASS | v2 uses MCP server pattern, not handler injection — stubs model wrong pattern |
| Security surface | N/A | No new boundaries |
| Single domain | PASS | scope:knowledge only |

### Codebase Verification
Confirmed all CRAWL stub locations match research findings:
- `SourceType.CRAWL` enum in models.py:39
- `CrawlHandler` type alias, constructor param, dispatch branch, `_handle_crawl` method in refresh.py (lines 29, 69, 74, 100-101, 179-203)
- `"crawl"` in loader.py:39 `_SOURCE_SCHEMA`
- Dead test code: test_refresh_orchestrator.py (~3 test classes), test_bookmark_pipeline_136.py (~2 test methods), test_refresh_555.py (~2 test methods)
- MCP test fixtures: test_ingest_graph_tools.py:174, test_list_sources.py:177

### Challenge Results
- Challenger: FALLBACK — trivial research completion, uncontroversial dead-code decision
- Architect response: accepted

### Non-impl tagging
This task produces no testable Python code. Needs `research` pass-through tag (cannot add via available tools — test-writer should note this is research-only).

### AC Assessment
- AC1 (decision): SATISFIED — research recommends removal with .85 confidence, well-justified
- AC2 (implementation if removing): DELEGATED to #703 with detailed 6-AC implementation spec across 8 files
- AC3 (documentation if keeping): N/A — removal chosen

### Verdict: APPROVE
### Action Taken: Advanced #696 to todo. Implementation work lives in #703 (at research status). #696 is complete as a research/decision deliverable.

[[2026-04-08]] Wed 23:01
## Test-Writer Notes
- Non-implementation task — research/decision deliverable only, no testable Python interfaces.
- Architecture reviewer explicitly flagged: "This task produces no testable Python code. Needs `research` pass-through tag."
- AC1 (decision): SATISFIED in research section — removal recommended with .85 confidence.
- AC2 (implementation): DELEGATED to #703 — test-writer will operate on #703 when it enters the pipeline.
- AC3 (documentation): N/A — removal path chosen.
- Passing through to builder.

[[2026-04-09]] Thu 00:41
## Builder Notes
- Non-implementation task — no code changes needed.
- Research/decision deliverable only: removal of SourceType.CRAWL stubs delegated to #703.
- Passing through to review.

[[2026-04-09]] Thu 01:24
## Review Evidence

### Test Results
- pytest: N/A — non-implementation task, no TestFromAC_* classes, no code changes

### Lint
- N/A — no Python files changed

### Coverage
- N/A — no touched modules

### Source Control Changes
- New file: `.owlbear/kanban/tasks/696-document-or-remove-dead-sourcetype-crawl-stubs-in.md` (task body)
- New file: `.owlbear/research/dead-crawl-stubs-696.md` (research deliverable)
- No production code, no test files, no Python modified

### Pass 1 — CRITICAL

#### 5.0 Test-Writer AC Coverage
No TestFromAC_* classes — correct. All four upstream agents (researcher, architect, test-writer, builder) independently confirmed this task produces no testable Python interface. Pass-through is appropriate.

#### 5.1 Security Review
- No code added, no system boundaries, no OWASP surface. **Clean.**

#### 5.2 Test Integrity
No TestFromAC_* tests — N/A.

#### 5.3 Test Quality
N/A (non-implementation task).

#### 5.4 Data Safety
No data persistence, no LLM output, no concurrency concerns. **Clean.**

#### 5.5 Implementation-Aware Test Gap Analysis
No production code changed — no untested paths possible.

#### 5.7 Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
None. Scope is tightly bounded to a research/decision deliverable.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: Decision on remove vs document approach | `.owlbear/research/dead-crawl-stubs-696.md` — recommends removal with .85 confidence; rationale documented across 3 sections (trade-off matrix, key insight, recommendation) | N/A — non-impl | **PASS** |
| AC2: If removing: stubs deleted, tests updated, no dead code remains | Delegation to #703 is correct and appropriate — #703 created with 7 AC lines covering all stub removal work. Research doc identifies exact file locations. #703 is in review status per diff, nearing completion. | N/A — delegated to #703 | **PASS (delegated)** |
| AC3: If documenting: `# FUTURE:` comment | N/A — removal path chosen, documentation path correctly closed out | N/A | **PASS (N/A)** |

### Confidence: .97
### Verdict: PASS → docs

[[2026-04-09]] Thu 02:07
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Pure research/decision task — no code changes, no behavior change |
| 2 | Module docstrings | No | N/A | No Python modules created or modified (builder confirmed pass-through) |
| 3 | External attribution | No | N/A | Sources are internal research docs and v2 source code only; no external repos or articles used |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Verified | `.owlbear/research/dead-crawl-stubs-696.md` exists, linked from task body, follow-up #703 created with full 6-AC implementation spec |

### Files Updated
- None

### Scratch Files Cleaned
- None found (no `.owlbear/scratch/696-*` files)

[[2026-04-09]] Thu 03:24
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Decision on remove vs document approach | `.owlbear/research/dead-crawl-stubs-696.md` — recommends removal with .85 confidence, rationale across trade-off matrix, 3 key insights | PASS |
| AC2: If removing: stubs deleted, tests updated | Delegated to #703 (in-progress, 7-AC spec covering all 8 files). Correct — #696 is research/decision only | PASS (delegated) |
| AC3: If documenting: FUTURE comment | N/A — removal path chosen, documentation path closed | PASS (N/A) |

### Research Task Checklist (Step 1a)
- Research doc at `.owlbear/research/dead-crawl-stubs-696.md`: EXISTS
- Follow-up #703 created at in-progress: EXISTS, references source:research-696
- Follow-up references research doc: YES (owning task #696 in doc header)

### Test Results
- pytest: 3705 passed, 380 failed, 8 skipped (pre-existing; zero code changed by #696)
- ruff: 5 pre-existing violations, none in #696 scope
- Collection error in test_planner_gates.py (pre-existing ImportError, unrelated)

### Architect Quality: 4/5
AC was clear for a decision task. Conditional AC2/AC3 structure slightly unconventional but unambiguous. Decision scope cleanly separated from implementation (#703).

### Deduction Breakdown
- AC lines: 3/3 verified with evidence → no deduction
- Uncommitted deliverables (research doc + kanban task not committed by upstream): -.02
- Pre-existing test failures: not task-scoped → no deduction
- Pre-existing lint: not task-scoped → no deduction
- AC quality 4/5: → no deduction
- Reviewer evidence: present, detailed, PASS at .97 → no deduction

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| db16f1a | docs | .owlbear/research/dead-crawl-stubs-696.md, .owlbear/kanban/tasks/696-*.md | #696 |
