---
id: 1861
title: 'P2-04: Agent instruction updates — h-decision-requests skill'
status: backlog
priority: needed
created: 2026-05-24T20:59:38.739082+02:00
updated: 2026-05-24T21:00:29.545322+02:00
tags:
  - phase-2
  - scope:docs
  - docs
parent: 1850
depends_on:
  - 1855
ac:
  - SKILL.md documents the three MCP tools (create_request, list_requests, 
    show_request) with parameter signatures, required vs optional params, and 
    one usage example per tool.
  - SKILL.md documents the structured data model fields (request_id, task_id, 
    kind, title, summary, agent, options, resolution) with types, constraints, 
    and kind-specific validation rules.
  - SKILL.md documents the resolution lifecycle (pending/ to resolved/ 
    transition, write-back format variants, conditional unblock semantics) so 
    agents consume structured answers via show_request.
proof_bundle: skip
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1850 and `.owlbear/briefs/draft-decision-request-data-model/brief.md`

## Scope

**In scope:**
- Rewrite `share/skills/h-decision-requests/SKILL.md` for structured model
- Document MCP tool parameters and usage patterns
- Document data model field definitions and validation rules
- Document lifecycle (create → pending → resolved → write-back)
- Document kind-specific behavior (decision vs action)

**Out of scope:**
- Code changes (documentation only)
- Cockpit UI documentation (separate from agent skills)
- Old create_dr tool docs (remove references)

## Test scope
Skip (docs/config only per domain mapping)