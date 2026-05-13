# Context — Structured Task Specification in Frontmatter

## Problem Statement

Two stable specification fields currently live as freeform markdown in the task body, mixed with volatile operational content (work logs, agent notes, end_work output):

1. **Acceptance Criteria (AC):** List of named criteria, typically under a `## Acceptance Criteria` heading. Not machine-queryable. Gets buried as body grows with work logs.

2. **Proof Bundle:** A single-axis complexity/testing taxonomy (`skip | existing | smoke | behavioral | critical`). Currently a `Proof bundle: behavioral` line in the body. Determines test-writing scope, challenger involvement, and reviewer depth.

Both are specification — they define what the task should accomplish and how thoroughly it should be verified. Neither should live in the volatile body.

**Driver:** Structural cleanliness — no evidence of active breakage, but the current mixing of spec and operational notes is a design smell that compounds as task bodies grow. The user wants a clear boundary between "what the task is" (frontmatter) and "what happened during the task" (body).

**Scope decision:** AC and proof bundle ship as a single feature — they share the same insight and motivation.

## Project Type

`existing-feature/refactor` — modifies the kanban engine, MCP tools, and cockpit UI.

## Current State

- Task model: Pydantic `Task` in `serve/kanban/src/owlbear_kanban/models.py` (line 404)
- Frontmatter parsing: `storage.py` → `_parse_task_file()` → `yaml.load` + `Task.model_validate()`
- Model uses `extra='allow'` — unknown YAML keys survive round-trip but are untyped
- No existing `ac` field in the schema
- AC lives as markdown headings (`## Acceptance Criteria`) in body text
- MCP `show_task` returns body as a single string; agents parse it visually

## Affected Surface

- `serve/kanban/` — models (Task, TaskSummary, TaskFull), storage (_CANONICAL_FIELDS, write_task), engine (create_task, edit_task)
- `serve/mcp-kanban/` — server.py (create_task, edit_task, show_task tool parameters)
- Pipeline agent skills — `w-tdd-red`, `w-code-review`, `w-task-decomposition` reference proof bundle; code-review extracts AC from body

## Outcomes (M2 — locked)

**Best realistic outcome:**
- `ac` (list of strings) and `proof_bundle` (enum string) are first-class frontmatter fields
- MCP tools (`create_task`, `edit_task`, `show_task`) expose and manipulate both fields natively
- `edit_task` gains AC manipulation (atomic add/remove or full-list replacement — design question for Phase 2)
- Pipeline agents and skills read both fields from structured frontmatter
- Body is clean: operational notes only

**Minimum viable win:**
- Model + storage + MCP for both fields
- Forward-only: new tasks use frontmatter fields; agents improvise for legacy tasks with body-embedded AC
- Optional small migration script to convert existing tasks

**Out of scope:**
- Cockpit UI rendering (AC checklist, proof bundle badge) — deferred to follow-up task
- AC status tracking (met/unmet per AC) — authority problem. Separate feature.
- AC templates
- Changes to the proof bundle taxonomy itself
- AC naming convention details (AC1:/AC2: vs semantic names) — panel decision, not user spec

**Migration strategy:** Forward-only with agent improvisation. Implement kanban + MCP, then update agent skills. Agents can read AC from body if frontmatter is empty. Small migration script acceptable but not required.

## Active Tensions (for Phase 2)

- AC storage format: list-of-strings vs YAML map vs list-of-objects
- AC manipulation API: atomic add/remove (like tags) vs full-list replacement
- Proof bundle validation: closed enum vs regex vs config-driven
- `list_tasks` AC exposure: count only vs full list vs nothing
- `pick_tasks` AC/proof_bundle inclusion in dispatch entries

## Early Challenge Summary

- **Simplifier:** scope is ~3× what the driver needs; recommends P1 (schema+MCP) and P2 (cockpit+skills) split. Cockpit cut accepted (D5).
- **First-principles:** proof bundle clearly earned; AC-in-frontmatter challenged (no named consumer, YAML worse ergonomics than markdown for AC content). Body-convention alternative proposed. User overrode at D4 — structural benefit accepted as self-evident.
