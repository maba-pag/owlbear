---
id: 2031
title: 'P5-05: Replace task requests with native change and job requests'
status: build
priority: high
created: 2026-07-24T23:22:11.813787+02:00
updated: 2026-07-24T23:22:44.362426+02:00
tags:
  - phase-5
  - scope:mcp-kanban
  - native-control-plane
  - requests
  - transaction
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-009
  - packet:DN-009-PK-005
  - interface:IF-010
parent: 1981
depends_on:
  - 2027
ac:
  - 'AC-1: Given a `NativeRequest` bound to the current change and digest with permitted
    optional target-node and job links, public `create_request` persists the request
    and linked job blocks atomically and returns `StoredRequest`; an exact replay
    does not duplicate either record.'
  - 'AC-2: Given mismatched change, digest, target-node, or job references, or changed
    replay content, public `create_request` returns distinct stable reference or conflict
    `ToolError` codes and leaves request and job records unchanged.'
  - 'AC-3: Given pending and resolved native requests plus a `pending | resolved`
    status filter, public `list_requests` returns matching summaries in stable request-identity
    order; an unsupported status returns a stable parameter `ToolError`.'
  - 'AC-4: Given an existing `request_id`, public `show_request` returns the selected
    `StoredRequest` including resolution state; a missing ID returns a stable not-found
    `ToolError`.'
proof_bundle: existing+challenge
blocked: true
block_reason: 'PARTIAL_GRAPH_COMMIT: #2032 creation rejected by ERR_AC_ITEM_TOO_LONG;
  recovery owner shaper must create approved T6 with each AC <=500 chars, complete
  #1981 projection/dependency routing, audit #2027-#2032, then clear blocks.'
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `b56fedd21a54a670b5e192ef88a86d6cb4434597b264135ae6a9fd330458bdca`; `DN-009-PK-005`. Resolve normative behavior from `DN-009`, `REQ-015`, `IF-010`, and `PROOF-011`; this record is not specification authority.

## Outcome
Replace task-ID request adapters with `create_request`, `list_requests`, and `show_request` over native change, authority-digest, graph-target, and job identities while preserving user/Cockpit-controlled resolution.

## Envelope
In: strict MCP request models, stable request error mapping, and `NativeRequestRuntime` create/list/show operations over `RuntimeTransaction` and `JobStore`.

Out: request resolution, corrective invalidation, Cockpit UI/API work, task request compatibility, legacy removal outside MCP registration, and core request semantics.

Proof guidance: invoke public MCP request calls over the real native request runtime and job store with a temporary work root; replacement occurs only below the MCP boundary.