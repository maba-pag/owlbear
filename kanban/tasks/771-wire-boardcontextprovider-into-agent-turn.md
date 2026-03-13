---
id: 771
title: Wire BoardContextProvider into agent turn() instructions
status: backlog
priority: important
created: 2026-03-13T10:40:14.3912623+01:00
updated: 2026-03-13T14:16:52.2391617+01:00
tags:
    - agent
    - knowledge
    - scope:core
depends_on:
    - 770
claimed_by: researcher
claimed_at: 2026-03-13T14:16:52.2391617+01:00
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
