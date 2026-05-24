---
id: 1849
title: Cockpit public API boundary audit
status: research
priority: important
created: 2026-05-24T19:25:18.570388+02:00
updated: 2026-05-24T19:28:49.518964+02:00
tags:
  - scope:cockpit
  - scope:cockpit-web
  - scope:cockpit-backend
  - boundary-audit
  - discussion
parent:
depends_on: []
ac:
  - Inventory Cockpit frontend and backend calls into other modules, services, 
    APIs, and persistence boundaries.
  - Identify any direct filesystem access, private-member usage, or bypass of 
    exposed public APIs, distinguishing acceptable Cockpit-owned persistence 
    from cross-module coupling.
  - At the first real finding, stop and present it immediately with impact, 
    evidence, and fix options before implementation.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Purpose
Audit Cockpit call boundaries end to end. The goal is to verify Cockpit uses exposed public APIs from other modules and does not directly reach into private members or filesystem-owned data except where Cockpit is explicitly responsible for that boundary.

## User Direction
Report findings immediately with options. Do not silently fix. Some direct access may be acceptable, but it must be surfaced with context.

## Initial Scope
- Cockpit frontend API clients and pages/components.
- Cockpit FastAPI routes and view layer.
- Calls into kanban, memory, knowledge, filesystem paths, and internal/private helpers.
- Direct reads/writes of `.owlbear`, `store`, task files, memory files, ideas files, or related persistence.

## Method
Start broad with call/file inventories, then inspect the highest-risk call sites. Findings are evidence-first and stop the audit for user decision.

[[2026-05-24T19:28:49+02:00]]

## Finding 1: Decisions Route Bypasses A Public Kanban Decision API
Cockpit's Decisions backend directly constructs the decisions directory from `engine.kanban_dir`, reads pending markdown files, rewrites decision frontmatter/body, and moves files to resolved. The route uses public module helpers from `owlbear_kanban.decisions`, but there is no public KanbanEngine/AgentView single-decision API for Cockpit to call.

Evidence:
- `serve/cockpit/src/owlbear_cockpit/deps.py` exposes `get_decisions_dir()` as `Path(engine.kanban_dir) / "decisions"`.
- `serve/cockpit/src/owlbear_cockpit/routes/decisions.py` lists `decisions/pending/*.md`, calls `parse_dr(path)`, rewrites the pending file with `path.write_text(...)`, calls `engine.edit_task(...)` for side effects, and calls `move_to_resolved(...)`.
- `serve/kanban/src/owlbear_kanban/__init__.py`, `engine.py`, and `agent_view.py` expose task/board APIs but no decision listing or single-decision resolution method. `serve/kanban/src/owlbear_kanban/decisions.py` has module-level helpers and a batch `resolve_pending_drs`, but not a Cockpit-ready public boundary.

Impact:
Cockpit knows the Kanban decision storage layout and is responsible for file lifecycle details that should probably belong to Kanban. That makes the Cockpit route harder to keep consistent with any future decision storage/API changes and violates the preferred "Cockpit uses exposed APIs from other modules" boundary.

Status: stopped audit here for user decision before implementation, per user instruction.
