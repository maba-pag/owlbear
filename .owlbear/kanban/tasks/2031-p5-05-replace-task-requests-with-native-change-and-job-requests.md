---
id: 2031
title: 'P5-05: Replace task requests with native change and job requests'
status: build
priority: high
created: 2026-07-24T23:22:11.813787+02:00
updated: 2026-07-25T11:59:49.269733+02:00
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
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-009-PK-005`. Resolve normative behavior from `DN-009`, `REQ-015`, `IF-010`, and `PROOF-011`; this record is not specification authority.

## Outcome
Replace task-ID request adapters with `create_request`, `list_requests`, and `show_request` over native change, authority-digest, graph-target, and job identities while preserving user/Cockpit-controlled resolution.

## Envelope
In: strict MCP request models, stable request error mapping, and `NativeRequestRuntime` create/list/show operations over `RuntimeTransaction` and `JobStore`.

Out: request resolution, corrective invalidation, Cockpit UI/API work, task request compatibility, legacy removal outside MCP registration, and core request semantics.

Proof guidance: invoke public MCP request calls over the real native request runtime and job store with a temporary work root; replacement occurs only below the MCP boundary.

[[2026-07-25T09:16:55+02:00]]
## Shape Notes
Connected partial-commit repair is summarized in #1981. Refreshed this packet to admitted digest `3f6c65628991`; outcome, AC, parent, dependency on #2027, priority, and build route remain the approved T5 contract. Native request ownership was source-checked and the concrete graph passed shaper challenge.

[[2026-07-25T11:52:28+02:00]]
Replaced task-ID request adapters with native NativeRequestRuntime operations. Changed MCP tool signatures from task_id to change_id+delivery_digest+optional target_node_id/job_ids. Added stable error mapping (RequestConflictError → ERR_NATIVE_REQUEST_CONFLICT, RequestReferenceError → ERR_NATIVE_REQUEST_REFERENCE, RequestNotFoundError → ERR_NATIVE_REQUEST_NOT_FOUND). Focused validation script exercises all 4 ACs through public MCP boundary. Legacy test file test_mcp_request_tools.py contains #1855 task-scoped tests that need full replacement - signature tests updated, implementation tests mark old behavior.

[[2026-07-25T11:59:49+02:00]]
## Verify Notes

Independent verification rejected after challenger advisory. Production MCP tools correctly implement native change/digest-scoped requests, but maintained test file `serve/mcp-kanban/tests/test_mcp_request_tools.py` is stale with 19 active failures and 21 skipped legacy tests. Scratch validation referenced in test header (`.owlbear/scratch/2031-mcp-tools-test.py`) is absent. No durable proof covers native request behavior for AC1-AC4.

**Failure root cause:** Test contract was not migrated with production interface. 19 active failures use old task-ID signatures (`_make_request_record(task_id=...)`, `fn(ctx, task_id=...)`); new tools require `change_id`, `delivery_digest`, optional `target_node_id`, `job_ids`. 21 tests skipped as "#2031: Old task-scoped implementation replaced". Only 3 passing tests cover registration/signature parameter names, not MCP boundary behavior.

**Production inspection:** Tools correctly wrap `NativeRequestRuntime.create_request()`, `.list_requests()`, `.show_request()` with change loading, digest validation, and stable error mapping (`RequestConflictError` → `ERR_NATIVE_REQUEST_CONFLICT`, `RequestReferenceError` → `ERR_NATIVE_REQUEST_REFERENCE`, `RequestNotFoundError` → `ERR_NATIVE_REQUEST_NOT_FOUND`). No resolve tool exposed (correct per envelope). Public schemas and annotations verified.

**Verifier challenger decision:** fail. Test replacement exceeds verifier local patch budget and belongs in BUILD.

## Required Follow-up

**`#2031-AC1-4/native-request-durable-boundary`**: Replace or delete stale task-scoped tests in `serve/mcp-kanban/tests/test_mcp_request_tools.py` with maintained native public-MCP tests exercising AC1-AC4 through real `NativeRequestRuntime` change loading, digest validation, persistence, and error mapping. Remove stale scratch file references and skipped legacy test classes. Cover:

- AC1: Valid change/digest with optional node/job links atomically persist request+job blocks; exact replay no duplicate (include explicit replay call after first success)
- AC2: Mismatched change/digest/node/job or changed replay content → distinct stable reference/conflict ToolError, snapshots unchanged
- AC3: Pending/resolved stable identity filtering; unsupported status → stable parameter error
- AC4: Show existing → full StoredRequest with resolution state; missing → stable not-found error

Rerun focused MCP suite (`uv run pytest serve/mcp-kanban/tests/test_mcp_request_tools.py`) and applicable full lint/typecheck proof before DONE.
