---
id: 1957
title: 'P1-21: Document memory lifecycle authority and recovery'
status: build
priority: low
created: 2026-07-17T04:54:19.520889+02:00
updated: 2026-07-17T04:54:49.671498+02:00
tags:
  - phase-1
  - scope:docs
  - docs
  - memory
parent: 1958
depends_on:
  - 1952
  - 1953
  - 1954
ac:
  - 'AC-1: The maintained memory documentation states that exceptional edits preserve
    state, resolve returns contested, disputed, or stale entries to approved, first
    contest stores reporting-task provenance, dispute and resolve clear that provenance,
    confidence edits recompute score, and stale resolve resets only didnt_use_count.'
  - 'AC-2: The maintained MCP memory documentation states that curation of contested,
    disputed, and stale entries is rejected, no MCP resolve tool exists, and Cockpit
    is the human editing and resolution surface for those states.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Canonical memory documentation matches the shipped exceptional-edit, human-resolution, provenance, stale-recovery, and MCP authority contracts.

## Planning Source
- OpenSpec: `openspec/changes/expose-memory-lifecycle-in-cockpit`

## Scope
- In scope: maintained memory core and MCP memory README lifecycle/tool documentation.
- Out of scope: implementation, frontend usage prose, unrelated documentation, and an MCP resolve operation.

Proof guidance: no executable proof expected; inspect the maintained artifacts against the implemented domain, HTTP, and MCP public surfaces and the OpenSpec capability.