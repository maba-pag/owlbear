---
id: 41
title: Implement JSONL session persistence
status: done
priority: high
created: 2026-02-26T15:56:56.6024432+01:00
updated: 2026-02-26T19:55:54.6119063+01:00
started: 2026-02-26T19:42:07.499875+01:00
completed: 2026-02-26T19:55:54.6119063+01:00
tags:
    - phase-2
    - agent
    - memory
depends_on:
    - 37
class: standard
---

## Research findings (See docs/pydantic-ai-integration-research.md §3.2)

PydanticAI tracks message_history in GraphAgentState but does NOT persist it to disk. This is a genuine gap. pydantic-deepagents has checkpointing (save/rewind/fork) but not simple JSONL persistence.

PydanticAI messages are dataclass-based with part_kind discriminators and Pydantic serialization support. They can be serialized to JSON via Pydantic's model_dump()/model_validate() for structured types.

**Decision:** Build JSONL session store. Serialize PydanticAI ModelMessage list to JSONL. Load back via message type discriminators. Backup before compaction.

**Prior art:**
- pydantic-deepagents checkpointing.py — conversation state save/rewind
- nanobot — HISTORY.md grep-searchable log
- disler — JSONL transcript with pre_compact backup

## AC
Src: src/owlbear/memory/session.py with SessionStore class. create, load, append, save, backup. Serialize PydanticAI ModelMessage to JSONL. Tests cover round-trip persistence and backup.
