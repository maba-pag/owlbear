---
id: 744
title: Evaluate compact board-state context injection for agents
status: archived
priority: nice-to-have
created: 2026-03-11T21:17:18.1414264+01:00
updated: 2026-03-21T05:27:21.5466465+01:00
started: 2026-03-12T08:38:53.5327917+01:00
completed: 2026-03-21T05:27:17.4187288+01:00
tags:
    - research
    - agent
    - knowledge
class: standard
---

Investigate injecting a compressed kanban board snapshot into agent system prompts for situational awareness. Compare MC's generate-context.ts approach (~650 tokens) vs piping kanban-md list --compact output. Determine if KnowledgeQueryService is the right injection point. See docs/research/mission-control.md S3.2 and S4.

[[2026-03-13]] Fri 09:12

## AC
- [ ] Research doc at docs/research/compact-board-context.md
- [ ] Compare MC's generate-context.ts (~650 tokens) vs kanban-md list --compact piping
- [ ] Evaluate KnowledgeQueryService as injection point
- [ ] Recommendation with confidence score
- [ ] Follow-up kanban tasks if warranted

[[2026-03-13]] Fri 10:42
## Research
- Doc: docs/research/compact-board-context.md
- MC's generate-context.ts compresses workspace state to ~650 tokens as static file
- kanban-md list --compact (active only) achieves ~220 tokens with real-time data
- KnowledgeQueryService is NOT the right injection point (wrong concern: vector search vs static board state)
- Recommendation (.80): BoardContextProvider with TTL cache, wired to turn() instructions
- Follow-ups: #770 (provider), #771 (wiring), #772 (fix ContextInjectionHook dead code)

[[2026-03-21]] Sat 03:28
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Research doc at docs/research/compact-board-context.md | Clear and verifiable deliverable; the document exists and directly answers the task. | Keep |
| Compare MC's generate-context.ts (~650 tokens) vs kanban-md list --compact piping | Verifiable comparison target; the research doc quantifies token cost and freshness trade-offs for both approaches. | Keep |
| Evaluate KnowledgeQueryService as injection point | Architecturally important and verifiable against src/owlbear/memory/knowledge/query_service.py responsibility. | Keep |
| Recommendation with confidence score | Clear decision requirement; the research doc recommends BoardContextProvider with .80 confidence. | Keep |
| Follow-up kanban tasks if warranted | Met and properly decomposed into #770, #771, and #772. | Keep |

### Architecture Notes
- Single domain verified: #744 is a pure research task about board-context injection strategy.
- Codebase check confirms src/owlbear/memory/knowledge/query_service.py is a query-conditioned memory-layer service, so it is the wrong abstraction for always-on board state.
- src/owlbear/memory/context.py is static startup instructions and src/owlbear/core/context_hook.py is an unwired session-start hook path; neither is the correct home for fresh per-turn board context.
- The runtime-instructions boundary in src/owlbear/core/agent.py is the correct architectural shape for live board state injection.
- The follow-up decomposition is sound and atomic: #770 owns the core provider, #771 owns turn/bootstrap/config wiring, and #772 owns dead ContextInjectionHook cleanup.
- No TDD gate applies to #744 itself because it is a research deliverable. TDD applies to the downstream implementation tasks, which already exist on the board.

### Changes Made
- Claimed #744 as architect.
- Verified docs/research/compact-board-context.md against the current codebase.
- Verified follow-up tasks #770, #771, and #772 exist and preserve single-responsibility boundaries.
- Moving #744 to todo.

### Dependencies
- Verified: #770, #771, and #772 were created from this research outcome.
- No blocking predecessor required for this research task.

[[2026-03-21]] Sat 03:52
## Test-Writer Notes
- Non-implementation task (tagged research) — no tests applicable.
- Passing through to builder.

[[2026-03-21]] Sat 04:07
## Builder Notes
- Non-implementation research task (tagged research) passed through from test-writer
- Files changed: none (research/docs task only)
- AC verified:
  - [x] docs/research/compact-board-context.md exists (5846 bytes)
  - [x] Comparison: MC generate-context.ts ~650 tokens vs kanban-md --compact ~220 tokens (Section 3.2)
  - [x] KnowledgeQueryService evaluated as injection point (Section 3.3, not the right point)
  - [x] Recommendation with .80 confidence (Section 4, Option C - BoardContextProvider with TTL cache)
  - [x] Follow-up tasks: #770 (archived/done), #771 (ideation), #772 (todo)
- Tests: N/A (research task, no implementation)
- Lint: N/A (no code changes)
- Evidence: all AC deliverables verified present and complete

[[2026-03-21]] Sat 04:27
## Review Evidence
### Review: #744 - Evaluate compact board-state context injection for agents

### Test Results
- pytest (independent): uv run pytest tests/test_board_context.py -q --tb=short -> 15 passed, 0 failed, 2 optional-dependency warnings.

### Lint Results
- ruff (independent): uv run ruff check src/ tests/ -> 461 repo-wide findings (baseline debt in unrelated files).
- No #744 AC deliverable is a Python implementation file; lint failures are out of this task scope.

### Coverage
- uv run pytest tests/test_board_context.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
- src/owlbear/core/board_context.py: 100%; overall 2% from project-wide bare --cov behavior.

### Pass 1 - CRITICAL
- Security: No code changes in #744 scope; no secret leakage or unsafe guidance in docs/research/compact-board-context.md.
- Injection-point validation: src/owlbear/memory/knowledge/query_service.py confirms vector-search concern boundary; supports the conclusion that it is not the right injection point for always-on board state.
- Test integrity: N/A (no task-scoped TestFromAC changes for #744).
- Test quality: N/A for this research-only task (AC is doc/board artifact based).
- Data safety: No runtime/persistence changes in #744 scope.

### AC Compliance
- Research doc exists at docs/research/compact-board-context.md (ownership header line 3).
- MC vs compact comparison present in sections 3.1/3.2 with ~650 vs ~220 token evidence (lines 34, 50, 52).
- KnowledgeQueryService evaluation present in section 3.3 with explicit rejection (lines 57-68).
- Recommendation with confidence present in section 4 as .80 (lines 79-88).
- Follow-up tasks listed in section 5 (#770/#771/#772, lines 108-110); board verification confirms #770 archived, #771 ideation (depends_on 770), #772 todo.

### Verdict: PASS (confidence .94)

[[2026-03-21]] Sat 04:50

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | Yes | Pass | BoardContextProvider already documented: `BoardContextProvider (owlbear.core.board_context) injects live kanban board state into agent turns with TTL caching (wired in #771)` |
| 2 | Docstrings complete | No | N/A | Research task — no Python modules created or modified (builder confirmed 'Files changed: none') |
| 3 | sources/overview.md | Yes | Pass | 'Compact Board-State Context Injection (Task #744)' section present with 3 source rows: Mission Control generate-context.ts, PydanticAI Instructions docs, Claude Code Memory docs |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/compact-board-context.md exists; follow-up tasks #770 (archived), #771 (ideation), #772 (todo) verified on board |
| 6 | No impact default | N/A | N/A | Items 1, 3, 5 apply and are verified |

### Files Updated

- None (all docs already current)

### Scratch Files Cleaned

- None (no docs/scratch/744-* files exist)

[[2026-03-21]] Sat 05:27
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Research doc at docs/research/compact-board-context.md | File exists (130 lines), complete with all sections | PASS |
| Compare MC generate-context.ts vs kanban-md --compact | Section 3.1 (MC ~650 tokens), Section 3.2 (comparison table, ~220 tokens) | PASS |
| Evaluate KnowledgeQueryService as injection point | Section 3.3 (4-column table, explicit NOT the right point) | PASS |
| Recommendation with confidence score | Section 4: Option C BoardContextProvider with TTL cache (.80) | PASS |
| Follow-up kanban tasks if warranted | #770 (archived), #771 (ideation), #772 (todo) verified on board | PASS |

### Research Task Checks
- Doc exists at correct path: PASS
- Follow-ups created on board: PASS (#770, #771, #772)
- Follow-ups link back to research doc: PASS
- Attribution in docs/sources/overview.md: PASS (3 source rows)

### Test Results
- test_board_context.py: 15 passed
- Full suite: 3689 passed, 92 failed (all pre-existing baseline debt, none #744-related)
- ruff: All checks passed on task-relevant files

### Confidence: .97
### Action: archive
