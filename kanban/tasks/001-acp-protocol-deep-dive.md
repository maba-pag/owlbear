---
id: 1
title: ACP protocol deep-dive
status: archived
priority: needed
created: 2026-03-26T17:18:05.2307425+01:00
updated: 2026-03-29T15:49:28.7825231+02:00
started: 2026-03-29T15:49:28.4753841+02:00
completed: 2026-03-29T15:49:28.4753841+02:00
tags:
    - research
    - phase-1
    - scope:orchestrator
class: standard
---

## Objective
Research the Agent Client Protocol (ACP) and build a hello-world Python client that talks to Copilot CLI via stdin/stdout NDJSON.

## Acceptance Criteria
- [ ] Read ACP specification (agentclientprotocol/specification on GitHub)
- [ ] Document key message types: initialize, newSession, prompt, sessionUpdate
- [ ] Build minimal Python script that spawns `copilot --acp --stdio --allow-all-tools`
- [ ] Successfully send a prompt and receive streamed response
- [ ] Document error handling patterns (process crash, invalid JSON, timeout)
- [ ] Write findings to docs/research/acp-protocol.md
- [ ] Create follow-up tasks for any gaps discovered

## Context
ACP is the communication protocol between our Python orchestrator and Copilot CLI. This is the most critical research task - everything in the orchestrator layer depends on understanding ACP well.

[[2026-03-29]] Sun 12:51
## Research
Research completed 2026-03-26. See docs/research/acp-protocol.md for full findings.

Key outcomes:
- ACP is JSON-RPC 2.0 over stdio NDJSON (spec v0.11.3)
- Official Python SDK (agent-client-protocol v0.9.0) recommended (.85 confidence)
- 10 client-to-agent + 8 agent-to-client message types documented
- Error handling strategy documented in docs/research/acp-error-handling-strategy.md

Follow-up tasks created at ideation:
- #45 Build ACP hello-world script (now implemented)
- #46 Add agent-client-protocol to orchestrator deps (now implemented)
- #47 Document ACP error handling strategy (now complete)

All research checklist items satisfied. Task was researched but not advanced from ideation.

[[2026-03-29]] Sun 14:18
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Read ACP specification | Satisfied: research doc S2 lists spec as source #1 (.95) | Keep |
| Document key message types | Satisfied: S3.2 (10 client methods), S3.3 (8 agent methods), S3.4 (11 update types) | Keep |
| Build minimal Python script | Implementation concern; correctly delegated to #45 (archived) | Note as delegated |
| Successfully send prompt and receive response | Implementation concern; correctly delegated to #45 (archived) | Note as delegated |
| Document error handling patterns | Satisfied: S3.6 + dedicated doc via #47 (archived) | Keep |
| Write findings to docs/research/acp-protocol.md | Satisfied: doc exists, 200+ lines, 5 sources | Keep |
| Create follow-up tasks | Satisfied: #45, #46, #47 created; all archived | Keep |

### Architecture Notes
Completed research task. The research doc (docs/research/acp-protocol.md) is comprehensive: protocol overview, all message types, lifecycle flow, error codes, SDK assessment (.85 rec), and three follow-up tasks. All follow-ups (#45 hello-world, #46 SDK dep, #47 error docs) have completed the full pipeline and are archived.

AC lines 3-4 (build script, send prompt) were implementation concerns bundled in a research task. The researcher correctly split them to #45 rather than mixing research and implementation. This is the right call.

Sources properly attributed in docs/sources/overview.md (5 entries).

No TDD task needed (research deliverable, no application code).

### Dependencies
- None listed, none needed (root research task)
- Follow-ups #45, #46, #47 all archived

### Changes Made
- No AC refinement needed; research body already documents delegation
- Approved to todo

[[2026-03-29]] Sun 15:03
## Test-Writer Notes
- Non-implementation task (tagged research) — no tests applicable.
- Passing through to builder.

[[2026-03-29]] Sun 15:49
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Read ACP specification | docs/research/acp-protocol.md S2: spec listed as source #1 (.95) | PASS |
| Document key message types | S3.2 (10 client), S3.3 (8 agent), S3.4 (11 update types) | PASS |
| Build minimal Python script | Delegated to #45 (archived) per architect approval | PASS |
| Successfully send prompt and receive response | Delegated to #45 (archived) per architect approval | PASS |
| Document error handling patterns | S3.6 + dedicated doc via #47 (archived) | PASS |
| Write findings to docs/research/acp-protocol.md | File exists, 200+ lines, 5 sources, committed (3f4bbbe) | PASS |
| Create follow-up tasks | #45, #46, #47 created at ideation, all archived | PASS |

### Research Verification
- Research doc: docs/research/acp-protocol.md (exists, comprehensive)
- Follow-up tasks: #45 (archived), #46 (archived), #47 (archived)
- Sources attributed: 5 entries in docs/sources/overview.md under Task #1

### Test Results
- pytest: 679 passed, 103 failed (all failures pre-existing from other tasks, none related to #1)
- ruff: All checks passed

### AC Quality Score: 4/5
AC mixed research and implementation concerns (lines 3-4) but researcher correctly delegated implementation to follow-up tasks. Architect noted this in review. 7 clear lines overall.

### Pipeline Note
Builder/reviewer/writer sections absent from task body (research task with no code deliverables; agents passed through without writing notes). Minor quality gap, not blocking.

### Confidence: .96
### Action: archive
