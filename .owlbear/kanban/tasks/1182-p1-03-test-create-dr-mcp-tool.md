---
id: 1182
title: 'P1-03: Test create_dr MCP tool'
status: backlog
priority: needed
created: 2026-04-30T00:51:39.532255+00:00
updated: 2026-04-30T00:57:26.479155+00:00
tags:
- phase-1
- scope:mcp-kanban
- type:test
parent: 1179
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- Test `create_dr` MCP tool registration via `@mcp.tool()` decorator
- Test tool accepts 4 required params: task_id, agent, request_type, body
- Test tool returns `{created: true, path: "relative/path"}` on success
- Test tool returns error response when task not found
- Test tool handles file collision (counter suffix)
- Test validates request_type enum (`decision` or `action` only)

## Scope

- IN: MCP tool integration tests in `serve/mcp-kanban/`
- OUT: decisions.py unit tests (covered by #1180), guidance text

Brief: see parent #1179

[[2026-04-30]]
## Research
- Research doc: .owlbear/research/create-dr-mcp-tool-tests.md
- Sources: 5 studied (all internal codebase), 3 high-relevance
- Recommendation: Follow test_mcp_mutation_tools_1087.py pattern — mock decisions.create_dr, test delegation + error mapping + enum validation (confidence: 0.92)
- Follow-up tasks created: none (this task IS the test spec)
- Decision requests: none

## Challenge Results
- Challenger: FALLBACK — trivial T1 test scaffolding, no trade-offs to challenge
- Confidence in original: 0.92

## Key Findings
- Test file: serve/mcp-kanban/tests/test_mcp_create_dr_1182.py
- Pattern: AppContext + patch decisions.create_dr at import point in server module
- 6 test cases from AC: registration, signature, success response, not-found error, collision passthrough, enum validation
- request_type enum: "decision" | "action" (brief authoritative, supersedes architect stance "DR"|"AR")