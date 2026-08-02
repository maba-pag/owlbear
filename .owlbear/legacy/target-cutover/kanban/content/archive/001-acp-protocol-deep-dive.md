---
id: 1
title: ACP protocol deep-dive
status: archived
priority: medium
created: 2026-03-26 17:18:05.230743+01:00
updated: 2026-03-31 15:05:13.194346+02:00
started: 2026-03-29 15:49:28.475384+02:00
completed: 2026-03-31 15:05:07.787814+02:00
tags:
- research
- phase-1
- scope:orchestrator
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-03-29]] Sun 15:49
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 9b49aa9 | chore | kanban/tasks/001-acp-protocol-deep-dive.md | #1 |

[[2026-03-31]] Tue 07:02
[[2026-03-31]] Tue 12:00
## Researcher Re-check
Task was found at ideation despite having completed the full pipeline (archive at .96 on 2026-03-29). All AC satisfied, all deliverables intact. Re-advancing to backlog.

[[2026-03-31]] Tue 08:05
## Architecture Review (Re-review)
**Verdict:** Approve
**DR Verification:** N/A â€” T1 autonomous research (protocol understanding), no T3 triggers

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Read ACP specification | Satisfied: docs/research/acp-protocol.md references spec v0.11.3 | Keep |
| Document key message types | Satisfied: 10 client + 8 agent methods documented | Keep |
| Build minimal Python script | Delegated to #45 (archived) | Keep |
| Send prompt and receive response | Delegated to #45 (archived) | Keep |
| Document error handling patterns | Satisfied: dedicated doc via #47 (archived) | Keep |
| Write findings to docs/research/acp-protocol.md | Satisfied: file exists, comprehensive | Keep |
| Create follow-up tasks | Satisfied: #45, #46, #47 all archived | Keep |

### Architecture Notes
Re-review of completed research task. Previously archived at .96 confidence (2026-03-29). All deliverables intact: research doc exists, error handling doc exists, all three follow-ups (#45, #46, #47) archived. No code changes, no TDD task needed.

Task was found back at ideation despite full pipeline completion. Researcher re-advanced to backlog. Re-approving with no changes.

### Changes Made
- Re-approved to todo (no AC refinement needed)

### Dependencies
- None (root research task, all follow-ups archived)

[[2026-03-31]] Tue 11:30
## Test-Writer Notes (re-cycle)
- Non-implementation task (tagged research) — no tests applicable.
- Passing through to builder.

[[2026-03-31]] Tue 12:10
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.

[[2026-03-31]] Tue 13:14
## Review Evidence

### Task Type
Research/documentation task -- no code changes. TestFromAC classes: N/A. Security scan: N/A (no executable code). Lint: N/A (no Python files changed). This is a re-cycle of a previously archived task (archived 2026-03-29 at .96, found back at ideation 2026-03-31).

### Deliverables Verified

| Artifact | Check | Result |
|----------|-------|--------|
| docs/research/acp-protocol.md | Exists, committed (3f4bbbe) | PASS |
| docs/research/acp-error-handling-strategy.md | Exists (131 lines), committed (8df1572) | PASS |
| docs/sources/overview.md Task #1 section | 5 sources attributed | PASS |
| Task #45 | status: archived | PASS |
| Task #46 | status: archived | PASS |
| Task #47 | status: archived | PASS |

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| Read ACP specification | acp-protocol.md S2: spec v0.11.3 source #1; sources/overview.md L553 | PASS |
| Document key message types | S3.2 (10 client), S3.3 (8 agent); all 4 specified types present | PASS |
| Build minimal Python script | Delegated to #45 (archived); architect approved | PASS |
| Send prompt and receive response | Delegated to #45 (archived); architect approved | PASS |
| Document error handling patterns | S3.6 table covers all 3 scenarios; acp-error-handling-strategy.md 131 lines, committed 8df1572 | PASS |
| Write findings to docs/research/acp-protocol.md | File exists 200+ lines, committed 3f4bbbe | PASS |
| Create follow-up tasks | #45, #46, #47 all status: archived | PASS |

### Process Quality
Builder notes: 1 section (re-cycle pass-through). CLEAN.

### Verdict: PASS
Confidence: .96

[[2026-03-31]] Tue 15:05
## Audit (re-cycle)

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Read ACP specification | docs/research/acp-protocol.md S2: spec v0.11.3 source #1 | PASS |
| Document key message types | S3.2 (10 client), S3.3 (8 agent), S3.4 (11 update types) | PASS |
| Build minimal Python script | Delegated to #45 (archived), architect approved | PASS |
| Send prompt and receive response | Delegated to #45 (archived), architect approved | PASS |
| Document error handling patterns | S3.6 + dedicated doc acp-error-handling-strategy.md via #47 (archived) | PASS |
| Write findings to docs/research/acp-protocol.md | File exists, 200+ lines, committed (3f4bbbe) | PASS |
| Create follow-up tasks | #45, #46, #47 all archived | PASS |

### Research Verification
- Research doc: docs/research/acp-protocol.md (exists, comprehensive)
- Follow-up tasks: #45 (archived), #46 (archived), #47 (archived)
- Sources attributed: 5 entries in docs/sources/overview.md under Task #1

### Test Results
- pytest: 2188 passed, 152 failed, 7 skipped (no failures related to #1; research task, no code)
- ruff: 2 errors in test_necessity_check_196.py (unrelated to #1)

### AC Quality Score: 4/5
AC mixed research and implementation concerns (lines 3-4) but researcher correctly delegated. Architect noted this. Adequate overall.

### Reviewer Evidence
Present: detailed PASS at .96 with full deliverable and AC compliance tables.

### Deduction breakdown: none (all AC verified with evidence, lint clean in scope, reviewer evidence present, AC quality 4)
### Confidence: .98
### Action: archive
