---
id: 522
title: Wire ErrorLogger adapter at AcpClient construction sites
status: todo
priority: nice-to-have
created: 2026-04-01T15:15:04.1613975+02:00
updated: 2026-04-06T01:34:34.4305593+02:00
tags:
    - phase-2
    - scope:orchestrator
    - type:build
depends_on:
    - 521
class: standard
---

## Objective
Create an _ErrorLogger adapter bridging ErrorJournal to the _ErrorLogger Protocol and pass it at AcpClient construction sites.

## AC
- [ ] Adapter class implementing _ErrorLogger Protocol that delegates to ErrorJournal.log() with bound session_id — place in error_journal.py (cohesive with adapted object)
- [ ] session_id: use a fixed immutable sentinel string ('pre-session' or empty string, builder documents choice). Do NOT use a mutable instance attribute — concurrent dispatch_entry() calls via asyncio.gather() in _dispatch_parallel() share the same AcpClient and will race.
- [ ] AcpClient construction in orchestrate() (loop.py) passes error_logger= adapter instance
- [ ] orchestrate() accepts optional error_journal: ErrorJournal | None parameter (follow AuditLog injection pattern); default path: .owlbear/error-journal.jsonl
- [ ] Unit tests verify adapter delegates correctly (mock ErrorJournal, assert log() called with expected args including sentinel session_id)
- [ ] No changes to acp_client.py (Protocol already defined by #521)

Follow-up from #148 arch review. Without this task, _ErrorLogger injection is dead code.
See .owlbear/research/errorlogger-adapter-wiring-522.md for full analysis.

[[2026-04-06]] Mon 01:14
## Research
- Research doc: .owlbear/research/errorlogger-adapter-wiring-522.md
- Sources: 8 studied, 5 high-relevance (all internal codebase)
- Recommendation: Class adapter in error_journal.py, fixed 'pre-session' sentinel, wired at orchestrate() (confidence: .85)
- Follow-up tasks created: none — existing AC covers full scope
- Decision requests: none

## Challenge Results
- Challenger: reconsider (confidence 0.82)
- Confidence in original: .85
- Key challenges: mutable session_id races under parallel asyncio.gather() dispatch
- Researcher response: accepted — revised to fixed sentinel (concurrency-safe), mutable approach removed

[[2026-04-06]] Mon 01:33
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Adapter creation + wiring are tightly coupled — adapter is useless without wiring |
| Interface clarity | PASS (refined) | AC#2 now explicitly prohibits mutable session_id; AC#4 specifies AuditLog injection pattern |
| Dependency correctness | PASS | Updated depends_on from #148 (archived/redundant) to #521 (actual Protocol implementer) |
| Module layering | PASS | error_journal.py adapter wraps ErrorJournal (same package); loop.py consumes it — correct direction |
| TDD compliance | PASS | Pipeline flow: test-writer processes at todo before builder |
| KISS/YAGNI | PASS | ~10 LOC class adapter, follows existing patterns, no speculative features |
| Premise challenge | PASS | _ErrorLogger injection is dead code without this adapter — task fills a real gap |
| Pattern consistency | PASS | Follows AuditLog injection pattern (loop.py L430) and _CancelSignal Protocol pattern (acp_client.py) |
| Security surface | PASS | Local file I/O only, no new system boundaries |
| Single domain | PASS | scope:orchestrator — adapter, journal, and wiring all in orchestrator package |

### Challenge Results
- Challenger: proceed (confidence 0.88)
- Architect response: accepted — applied two recommended refinements (AC#2 concurrency constraint, dependency #148 to #521)

### AC Refinements Applied
1. AC#2: Added explicit prohibition on mutable session_id with asyncio.gather() race rationale
2. AC#4: Specified AuditLog injection pattern and default path (.owlbear/error-journal.jsonl)
3. AC#1: Specified placement in error_journal.py
4. AC#5: Added mock/assert specifics for test-writer clarity
5. AC#6: Updated Protocol attribution from #148 to #521
6. Dependency: replaced depends_on #148 (archived/redundant) with #521 (actual implementer)

### Codebase Evidence
- _ErrorLogger Protocol: acp_client.py L43-46
- AcpClient constructor: acp_client.py L89-97 (error_logger kwarg at L94)
- ErrorJournal.log(): error_journal.py L48-56 (session_id gap confirmed)
- Construction site: loop.py L471 — AcpClient(conn) with no error_logger
- AuditLog precedent: loop.py L430 — audit_log parameter on orchestrate()
- Concurrency: _dispatch_parallel() uses asyncio.gather() — shared AcpClient instance

### Verdict: APPROVE (refined)
### Action Taken: Refined 6 AC lines for precision, updated dependency graph, advancing to todo

[[2026-04-06]] Mon 01:34
Architecture review complete. AC refined (6 lines tightened), dependency updated #148 to #521, all 10 criteria PASS. Challenger: proceed at 0.88. Advancing to todo.
