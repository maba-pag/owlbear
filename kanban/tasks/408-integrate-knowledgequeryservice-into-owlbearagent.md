---
id: 408
title: Integrate KnowledgeQueryService into OwlBearAgent.turn()
status: archived
priority: needed
created: 2026-03-01T20:19:02.2896609+01:00
updated: 2026-03-02T09:15:06.0140543+01:00
started: 2026-03-01T20:23:55.5105382+01:00
completed: 2026-03-02T09:15:06.0140543+01:00
tags:
    - phase-13
    - agent
    - knowledge-graph
depends_on:
    - 425
class: standard
---

From #305 context-aware-knowledge-injection.md. Modify OwlBearAgent in src/owlbear/core/agent.py (~15 LOC). AC: - Add to OwlBearAgent.__init__ signature: knowledge_service: KnowledgeQueryService | None = None (TYPE_CHECKING import) - Store as self._knowledge_service - In turn(): before inner.run(), if self._knowledge_service is not None: call self._knowledge_service.query_for_context(prompt) and store result - Pass result as instructions= parameter to self.inner.run() call - When knowledge_service is None: do not pass instructions= to inner.run() (existing behavior preserved exactly) - When service.query_for_context returns None: instructions=None passed (PydanticAI ignores it) - When service raises any exception: catch with except Exception, log warning, continue turn without injection (never break turn()) - No changes to turn() return type or existing hook/session/tracker logic - Depends on #406, test task #425
