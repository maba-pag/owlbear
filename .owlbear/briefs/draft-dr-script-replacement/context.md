# Context

## Problem Signal

The scribe agent handles DR/AR file operations that appear to be purely mechanical: scan directories, read YAML frontmatter, classify response fields, move files, write to task bodies, and block/unblock tasks. No judgment, creativity, or research is involved — just filesystem operations + kanban MCP calls.

**Hypothesis:** The scribe agent adds no value over a deterministic script or engine function, and could be replaced by folding DR/AR logic into the kanban engine + MCP layer.

## Project Type

existing-feature/refactor

## Current State

- Scribe agent: `share/agents/scribe.agent.md` (ND3, Haiku 4.5 / GPT-5.4 mini)
- Skill: `share/skills/w-decision-routing/SKILL.md` (270 lines)
- File namespace: `.owlbear/decisions/{pending,resolved}/`
- Consumers: orchestrator (resolve mode every cycle), all pipeline agents (check-or-create on demand)
- Kanban engine: `serve/kanban/` — already has block/unblock, edit_task(append_body), guidance field

## Problem Statement

The scribe agent is a pure-mechanical intermediary between pipeline agents and the `.owlbear/decisions/` filesystem. It adds LLM cost and latency to operations that are deterministic (resolve, query) or can be restructured to be deterministic (create — when the calling agent provides structured content). Meanwhile, the user's only interaction path is raw YAML/markdown file editing, when a Cockpit UI would be faster and less error-prone.

## Emerging Shape

- DR/AR logic moves into the kanban engine as deterministic functions
- MCP tools expose create_dr + query_drs (few arguments, minimal context cost)
- Cockpit provides the primary user-facing view/edit/resolve UI
- `pick_tasks` auto-resolves responded DRs as a side-effect (no dedicated cycle needed)
- Files on disk remain the persistence layer in `.owlbear/decisions/` (separate folder, engine-managed)
- File format stays markdown+YAML frontmatter (simplified, not a new format)
- Calling agent provides the full body markdown; engine handles frontmatter + blocking
- Fallback: edit file + curl resolve endpoint or wait for pick_tasks

## What This Eliminates

- The scribe agent entirely
- The orchestrator's "dispatch scribe every cycle" pattern
- The "calling agent → scribe subagent → file" indirection chain
- Raw YAML editing as the primary user interaction (Cockpit replaces it)

## Open Tensions

- Exact MCP tool parameter shape (body as single markdown string vs. structured sections)
- Duplicate detection: drop entirely, or keep task_id-only check?
- Cockpit DR badge design (color semantics for DR/AR/both/none)

## Locked Outcomes

1. Delete scribe agent
2. Engine functions for DR/AR (create + resolve) inside kanban engine
3. `pick_tasks` auto-resolves responded DRs as side-effect (no separate tool/call)
4. `create_dr` MCP tool — few structured params, body as markdown string
5. Streamlined format: drop urgency, decision_type, impact_tier, auto-resolve; add full timestamp+tz; keep agent, task_id, request_type, response
6. New skill (short, precise) replaces `w-decision-routing` — tells agents when/how to use `create_dr`
7. All pipeline agent/skill references to scribe updated
8. Cockpit: status bar indicator (must-have: green=none, colored=pending DR/AR) + optional per-task badge + resolve UI
9. File-edit fallback preserved (markdown+frontmatter, engine-managed)
10. No `query_drs` MCP tool (agents read files directly if needed)
11. No `resolve_drs` MCP tool (auto-triggered inside `pick_tasks`)

## Implementation Phases (single brief)

- P1: Engine functions + format + `create_dr` MCP tool
- P2: Agent/skill references + new skill
- P3: Cockpit status bar indicator + resolve UI

## Validated Assumptions

- Auto-resolve was never triggered (0 `auto-approved` in history) — safe to drop
- Concern matching was already task_id-only in practice — no semantic matching lost
- 35 resolved DRs exist as evidence of the system working
