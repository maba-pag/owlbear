---
id: 771
title: Wire BoardContextProvider into agent turn() instructions
status: archived
priority: important
created: 2026-03-13T10:40:14.3912623+01:00
updated: 2026-03-22T19:20:10.68853+01:00
started: 2026-03-22T19:20:10.68853+01:00
completed: 2026-03-22T19:20:10.68853+01:00
tags:
    - agent
    - knowledge
    - scope:core
depends_on:
    - 770
blocked: true
block_reason: 'Stale board regression: repo and activity log show #771 already implemented, tested, and previously archived; do not redispatch to builder.'
class: standard
---

Integrate BoardContextProvider output with turn() method. Concatenate board state with KnowledgeQueryService output before passing to inner.run(instructions=). Add config setting for enable/disable. See docs/research/compact-board-context.md S4.

[[2026-03-13]] Fri 14:16
## Research
- Doc: docs/research/wire-board-context-into-turn.md
- PydanticAI run(instructions=) appends runtime instructions to static+dynamic
- Strategy: concatenate board ctx + knowledge ctx in turn() before passing to inner.run()
- Board context first (~220 tokens), knowledge context second (~2000 tokens)
- Config: board_context_enabled bool (default True) in OwlBearSettings
- Bootstrap wiring follows knowledge_service= pattern
- Confidence: .85

## AC
- [ ] OwlBearAgent.__init__ accepts optional board_context_provider parameter
- [ ] turn() calls board_context_provider.get_context() before knowledge service
- [ ] Board context and knowledge context concatenated into single instructions= string
- [ ] Graceful degradation: provider exception -> log WARNING, continue without board context
- [ ] No instructions= kwarg when both sources return None/empty
- [ ] Config: board_context_enabled bool in OwlBearSettings (default True)
- [ ] Bootstrap: construct BoardContextProvider when enabled, pass to OwlBearAgent
- [ ] Unit tests covering provider None, returns string, raises, both sources, neither source

[[2026-03-21]] Sat 04:01
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| OwlBearAgent.__init__ accepts optional board_context_provider parameter | Already implemented in src/owlbear/core/agent.py and covered in tests/test_wire_board_context.py | Do not dispatch; task already satisfied in repo |
| turn() calls board_context_provider.get_context() before knowledge service | Already implemented in src/owlbear/core/agent.py and covered by call-order tests in tests/test_wire_board_context.py | Do not dispatch; task already satisfied in repo |
| Board context and knowledge context concatenated into single instructions= string | Already implemented in src/owlbear/core/agent.py and covered in tests/test_wire_board_context.py | Do not dispatch; task already satisfied in repo |
| Graceful degradation: provider exception -> log WARNING, continue without board context | Already implemented in src/owlbear/core/agent.py and covered in tests/test_wire_board_context.py | Do not dispatch; task already satisfied in repo |
| No instructions= kwarg when both sources return None/empty | Already implemented in src/owlbear/core/agent.py and covered in tests/test_wire_board_context.py | Do not dispatch; task already satisfied in repo |
| Config: board_context_enabled bool in OwlBearSettings (default True) | Already implemented in src/owlbear/config.py and covered in tests/test_wire_board_context.py | Do not dispatch; task already satisfied in repo |
| Bootstrap: construct BoardContextProvider when enabled, pass to OwlBearAgent | Already implemented in src/owlbear/bootstrap/__init__.py and covered in tests/test_wire_board_context.py | Do not dispatch; task already satisfied in repo |
| Unit tests covering provider None, returns string, raises, both sources, neither source | Already implemented in tests/test_wire_board_context.py | Do not dispatch; task already satisfied in repo |

### Architecture Notes
- Current repo state already satisfies the full contract in src/owlbear/core/agent.py, src/owlbear/bootstrap/__init__.py, src/owlbear/config.py, and tests/test_wire_board_context.py.
- kanban/activity.jsonl shows builder, reviewer, writer, and auditor touches for #771, including an auditor move of done -> archived on 2026-03-15.
- The current kanban/tasks/771-wire-boardcontextprovider-into-agent-turn.md body has regressed to pre-implementation backlog state with a stale researcher claim. That is board metadata drift, not pending implementation work.
- Routing this card to todo would duplicate completed work and violate KISS/YAGNI.
- Dependency check: #770 exists and is terminal, so there is no missing prerequisite to resolve here.
- TDD note: a distinct RED predecessor for the wiring task is not discoverable in the current board state, but the repo already contains the executable test contract. The right action is to prevent redispatch, not reopen implementation.

### Changes Made
- Claimed #771 as architect after confirming the prior claim had expired under claim-timeout rules.
- Appended this architecture review.
- Blocking the task so stale metadata does not re-enter builder dispatch.

### Dependencies
- Verified: #770 is complete and no longer blocks this behavior contract.
- Verified: repo state already contains the downstream wiring and tests for this contract.
- Gap noted: current task metadata no longer matches repository and activity-log history.
