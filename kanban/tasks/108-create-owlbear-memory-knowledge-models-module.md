---
id: 108
title: Create owlbear.memory.knowledge.models module
status: archived
priority: high
created: 2026-02-27T03:31:21.0047032+01:00
updated: 2026-02-27T13:21:38.8135412+01:00
started: 2026-02-27T03:32:48.647058+01:00
completed: 2026-02-27T13:21:38.8135412+01:00
tags:
    - memory
    - knowledge-graph
    - phase-2
depends_on:
    - 106
    - 115
class: standard
---

Pydantic models for the knowledge graph: Entity, Edge, Document. Creates the `owlbear.memory.knowledge` subpackage.

## Acceptance Criteria

- [ ] New directory: `src/owlbear/memory/knowledge/`
- [ ] New file: `src/owlbear/memory/knowledge/__init__.py` (export public model names)
- [ ] New file: `src/owlbear/memory/knowledge/models.py`
- [ ] `EntityType` — `StrEnum` with values: `file`, `function`, `class_`, `decision`, `pattern`, `concept`
- [ ] `RelationType` — `StrEnum` with values: `defines`, `imports`, `depends_on`, `related_to`, `implements`, `documents`
- [ ] `Entity` model — fields: `id: str` (default uuid4 hex), `name: str`, `entity_type: EntityType`, `description: str = ""`, `metadata: dict[str, Any] = {}`
- [ ] `Edge` model — fields: `id: str` (default uuid4 hex), `source_id: str`, `target_id: str`, `relation: RelationType`, `weight: float = 1.0`, `metadata: dict[str, Any] = {}`
- [ ] `Document` model — fields: `id: str` (default uuid4 hex), `title: str`, `content: str`, `metadata: dict[str, Any] = {}`
- [ ] All models use `model_config = ConfigDict(frozen=True)` for immutability
- [ ] All models round-trip through `model_dump()` / `model_validate()`
- [ ] Validation: `entity_type` rejects invalid strings, `weight` must be >= 0
- [ ] `ruff check` clean

See docs/knowledge-graph-research.md section 4
