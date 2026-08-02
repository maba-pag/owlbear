---
id: 2073
title: 'P15-03: Re-accept the native MCP control plane at the candidate digest'
status: archived
priority: high
created: 2026-07-26T01:58:52.402176+02:00
updated: 2026-07-26T03:14:33.986485+02:00
tags:
  - phase-15
  - candidate-reacceptance
  - change:replace-delivery-pipeline
  - digest:bf5edd67478d
  - node:DN-009
  - scope:mcp-kanban
  - type:test
  - rigor:thorough
  - proof:PROOF-011
parent: 1968
depends_on:
  - 1981
  - 2072
ac:
  - 'AC-1: Given the candidate modular change and real MCP server context, PROOF-011
    exercises change, validation, admission, job, request, evidence, health, history,
    and completion tools and records the tested SHA.'
  - 'AC-2: The assembled MCP inventory omits generic task mutation and old lifecycle
    tools while stable engine diagnostics remain visible through public tool errors.'
  - 'AC-3: The task records candidate digest, tested SHA, commands, and results for
    DN-009; a failing MCP contract produces a scoped corrective implementation before
    re-acceptance.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`; candidate re-acceptance of unchanged `DN-009` under `PROOF-011`.

## Outcome
The shipped native MCP surface is re-proven over candidate authority and corrected orchestration without restoring generic task tools.

## Envelope
In: IF-010, PROOF-011, assembled MCP server, candidate change/store fixture, old-tool absence.

Out: new MCP controls for priority/cancel, which are not required by the admitted DN-011 browser path; frontend and cutover.

Proof guidance: execute public MCP tools over the real graph-aware engine at a recorded SHA with a temporary store; mocks may not replace server assembly.

[[2026-07-26T03:07:03+02:00]]
## Builder Notes
DONE: Re-accepted unchanged DN-009/PROOF-011 at candidate digest `bf5edd...`, tested SHA `2a804df1ce9b291c5919c9356883f958bba1c362`.

Evidence:
- Complete `serve/mcp-kanban/tests`: 102 passed.
- Focused inventory/native query/request: 39 passed.
- Focused admission/completion/designer/planner/builder interactions: 36 passed.
- Builder challenger: pass; confirmed every PROOF-011 category and generic/old tool absence over the assembled real-engine server.
- MCP product/proof paths remained clean; focused lint passed.

No product edit or priority/cancel MCP expansion was required because IF-010 is unchanged and DN-011 consumes IF-011. Builder memories assessed.

[[2026-07-26T03:13:47+02:00]]
## Verify Notes
PASS: DN-009 candidate re-acceptance is complete.

Evidence:
- Tested product SHA `2a804df1ce9b291c5919c9356883f958bba1c362`; builder evidence commit `80111bd91007a8c32d1721a4ca9be74eb0ad51c9` is in ancestry.
- Complete MCP package: 102 passed.
- Builder focused contract/interactions: 39 + 36 passed.
- Verifier independent inventory/error/absence and jobs/health/history: 7 + 7 passed.
- MCP package remained clean; focused lint passed.
- Verifier challenger: pass; AC-1 through AC-3 and unchanged IF-010 scope are closed.

Verifier memories assessed.

[[2026-07-26T03:14:33+02:00]]
## Collect Notes
ARCHIVED: DN-009 candidate re-acceptance is complete. Tested SHA `2a804df1ce9b291c5919c9356883f958bba1c362`, builder commit `80111bd91007a8c32d1721a4ca9be74eb0ad51c9`, and verifier commit `8747c9ea40d6d2713633bdbd0bcb9c22d079741b` are ancestors. Complete 102-test package and focused 39/36/7/7 evidence passed; both challengers passed; no product delta or open finding. Collector memories assessed.
