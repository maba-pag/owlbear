---
id: 2062
title: 'P10-03: Expose whole-change audit rejection through MCP'
status: verify
priority: high
created: 2026-07-25T19:53:28.713892+02:00
updated: 2026-07-25T20:33:36.078556+02:00
tags:
  - phase-10
  - scope:mcp-kanban
  - audit
  - rejection
  - findings
  - invalidation
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-014
  - packet:DN-014-PK-003
  - interface:IF-010
  - interface:IF-014
parent: 1986
depends_on:
  - 2061
  - 1981
ac:
  - 'AC-1: Public MCP inventory exposes `reject_audit` with strict active identity,
    detail, evidence IDs, findings, and invalidation fields; a conforming request
    forwards parsed models unchanged to `DispatchRuntime` and returns the native rejection
    result.'
  - 'AC-2: Through assembled MCP context, successful rejection is observable through
    `show_job`, `list_jobs`, `list_findings`, `show_finding`, and `show_receipt` as
    a failed attempt, superseded audit and affected closure, supersession receipt,
    and minimum corrective plan jobs; the unrelated receipt remains unchanged.'
  - 'AC-3: Malformed parameters map to `ERR_PARAM_VALIDATION`; native invalidation,
    identity, cleanup, and coordination diagnostics retain stable code, detail, lower
    code, target, and holder identities without partial publication.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-014-PK-003`. Resolve behavior from WF-005, IF-010, IF-014, and current strict MCP adapter and query conventions.

## Outcome
Expose native audit rejection and its persisted correction chain through the public MCP control plane.

## Envelope
In: strict `reject_audit` parameters, dispatch forwarding, native result and diagnostics, and existing job, finding, and receipt queries.

Out: auditor workflow, Cockpit HTTP/UI, setup, cutover, and complete-system proof.

Proof guidance: run focused MCP contract and operation checks plus the native rejection downstream scan.

[[2026-07-25T20:33:36+02:00]]
## Builder Notes

DONE

Exposed whole-change audit rejection through the strict FastMCP control plane.

- AC-1: added strict `RejectAuditParams`, an exported annotated `reject_audit` tool, parsed native `RejectAuditRequest` construction, and unchanged forwarding to `DispatchRuntime.reject_audit`. Live registry and nested corrective-schema contracts include the new tool.
- AC-2: an assembled MCP test starts a real terminal audit, rejects it through `server.reject_audit`, and observes the persisted failed attempt, superseded audit, finding, supersession receipt, and zero-job design re-entry through `show_job`, `list_jobs`, `list_attempts`, `list_findings`, `show_finding`, and `show_receipt`; all pre-existing receipt bytes remain unchanged.
- AC-3: malformed audit parameters raise `ERR_PARAM_VALIDATION` before dispatch. Native audit and dispatch diagnostic models are returned unchanged by the adapter, with downstream #2061 tests covering identity, invalidation, cleanup, and coordination failure publication.

Task-scoped lint passed. `uv run pytest serve/mcp-kanban/tests serve/kanban/tests/test_native_runtime.py serve/kanban/tests/test_dispatch_runtime.py -q --tb=short` passed 155 tests. Builder challenger passed after independently rerunning 25 MCP surface/operation tests.

Changed files: `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`, `serve/mcp-kanban/tests/test_mcp_surface_contract.py`, `serve/mcp-kanban/tests/test_mcp_acceptance_tools.py`.
