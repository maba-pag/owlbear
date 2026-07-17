---
id: 1953
title: 'P1-17: Preserve MCP exceptional-memory authority'
status: build
priority: medium
created: 2026-07-17T04:53:51.213104+02:00
updated: 2026-07-17T04:54:49.653998+02:00
tags:
  - phase-1
  - scope:mcp-memory
  - api
  - authority
parent: 1958
depends_on:
  - 1952
ac:
  - 'AC-1: Given a contested, disputed, or stale persisted entry, invoking curate_memory
    with a mutable field rejects the mutation with ToolError and leaves the persisted
    entry unchanged.'
  - 'AC-2: Given the MCP memory server public tool inventory, no resolve-memory operation
    is registered and the existing save, list, read, recall, curate, delete, approve,
    and assess operations remain registered.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
The final agent tool boundary remains narrower than the human memory-domain capability: agents cannot rewrite or resolve exceptional entries.

## Planning Source
- OpenSpec: `openspec/changes/expose-memory-lifecycle-in-cockpit`
- Capability requirement: Human-only exceptional-state resolution

## Scope
- In scope: MCP memory curation policy and registered public tool inventory.
- Out of scope: canonical engine behavior, Cockpit routes, frontend behavior, and a new resolve tool.

## Accepted Sequencing
This task follows the permissive engine task. The temporary MCP authority expansion between those commits was explicitly accepted during shaping; this task must restore the final authority boundary before downstream Cockpit work begins.

Proof guidance: exercise the real MCP curation adapter and registered server inventory; the canonical engine remains below the boundary and must not be mocked away.