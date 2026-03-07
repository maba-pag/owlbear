---
id: 619
title: Implement context condenser as PydanticAI HistoryProcessor
status: archived
priority: needed
created: 2026-03-07T05:20:54.7703351+01:00
updated: 2026-03-07T18:08:23.538199+01:00
started: 2026-03-07T05:45:57.1242264+01:00
completed: 2026-03-07T18:08:23.538199+01:00
tags:
    - scope:core
    - agent
depends_on:
    - 634
class: standard
---

Implement a context condenser that prevents token overflow in long sessions. Use PydanticAI's HistoryProcessor protocol -- OwlBearAgent already accepts history_processors in __init__ (src/owlbear/core/agent.py).

Pattern: rolling-window LLM summarization (OpenHands-inspired). When message count exceeds max_events, keep head (first keep_first messages) + tail (most recent messages), replace middle with a single LLM-generated summary message. Summary preserves key decisions and context.

See docs/context-condenser-research.md for full research findings.

## Key interfaces

- HistoryProcessor is a callable type alias, not a Protocol class. Four allowed signatures; we use async+ctx. Defined in pydantic_ai._agent_graph.
- ModelRequest (pydantic_ai.messages): dataclass with parts: Sequence[ModelRequestPart], metadata: dict[str, Any] | None
- PydanticAI validation post-processing: result must be non-empty and end with ModelRequest; timestamp auto-filled if None.
- OwlBearAgent.__init__ accepts history_processors: Sequence[HistoryProcessor[OwlBearDeps]] | None (agent.py line 68).
- Config lives in src/owlbear/config.py (NOT core/config.py). Follow existing Field(default=..., description="...") pattern.
- Bootstrap agent construction at src/owlbear/bootstrap.py ~line 967.

## AC

- [ ] SummarizingCondenser class in src/owlbear/core/condenser.py (new file, ~100 LOC)
- [ ] __init__(self, max_events: int = 120, keep_first: int = 4, target_size: int | None = None, model: Model | None = None) -- target_size defaults to max_events // 2 when None; model is pydantic_ai.models.Model | None (None = bootstrap supplies model at wiring time)
- [ ] async def __call__(self, ctx: RunContext[OwlBearDeps], messages: list[ModelMessage]) -> list[ModelMessage] -- matches _HistoryProcessorAsyncWithCtx[OwlBearDeps]
- [ ] No-op fast path: returns messages unchanged when len(messages) <= max_events
- [ ] Condensation path: head = messages[:keep_first], tail = messages[-(tail_size):] where tail_size = target_size - keep_first - 1, middle = messages[keep_first : len(messages) - tail_size]; call internal pydantic_ai.Agent[None, str] to summarize middle; result = head + [summary_request] + tail
- [ ] Boundary alignment: before slicing, adjust the head/tail boundary so a ModelResponse containing any ToolCallPart is never separated from the immediately-following ModelRequest containing its ToolReturnPart. Move the boundary to include both in the same segment (expand head forward or tail backward).
- [ ] Summary message format: ModelRequest(parts=[UserPromptPart(content="[Condensed Context]\n{summary_text}")], metadata={"condensed_at": datetime.now(UTC).isoformat(), "forgotten_count": len(middle)})
- [ ] Post-condition: result is non-empty and ends with ModelRequest (PydanticAI invariant; add assertion)
- [ ] Config fields in src/owlbear/config.py OwlBearSettings class, under a new "# --- Context condenser ---" section: condenser_enabled: bool = Field(default=False, ...), condenser_max_events: int = Field(default=120, ...)
- [ ] src/owlbear/bootstrap.py: in step 8 (agent construction ~line 967), when settings.condenser_enabled is True, import SummarizingCondenser, instantiate with max_events=settings.condenser_max_events and model=model, pass as history_processors=[condenser] to OwlBearAgent
- [ ] No other existing files modified beyond config.py and bootstrap.py
