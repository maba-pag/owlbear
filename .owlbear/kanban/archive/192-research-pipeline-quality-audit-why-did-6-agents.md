---
id: 192
title: 'Research: pipeline quality audit — why did 6 agents miss an obvious redundancy?'
status: archived
priority: medium
created: 2026-03-29 22:54:56.845597+02:00
updated: 2026-03-30 03:47:15.857804+02:00
started: 2026-03-30 03:47:08.488167+02:00
completed: 2026-03-30 03:47:08.488167+02:00
tags:
- research
- agent
- quality
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

A GitHub MCP server entry was added to setup.py and .vscode/mcp.json despite the Copilot extension already providing it — and NO agent in the full pipeline caught it. Six agents (researcher, architect, test-writer, builder, reviewer, writer) plus the auditor all approved or passed through this redundancy. This is a red flag for systemic issues in agent oversight quality.

This is NOT about fixing the GitHub MCP issue (that's trivial). This is about understanding WHY the pipeline failed as a quality gate and what structural improvements would prevent similar blind spots.

## Acceptance Criteria

- [ ] Audit the decision trail for tasks #18 and #121 end-to-end: what did each agent check, what did they skip, what assumptions went unquestioned?
- [ ] Sample 10-15 other recently completed/archived tasks across the pipeline — look for patterns of rubber-stamping, superficial reviews, assumption failures, or agents echoing upstream conclusions without independent verification
- [ ] Identify which pipeline roles are weakest at catching errors of omission (adding unnecessary things) vs. errors of commission (doing wrong things)
- [ ] Assess whether current agent instructions incentivize throughput over critical thinking — do they reward moving tasks forward more than questioning them?
- [ ] Evaluate architect review quality: are AC refinements substantive or cosmetic? How often does the architect push back vs. approve?
- [ ] Evaluate reviewer quality: does the reviewer actually test assumptions or just verify tests pass + ruff clean?
- [ ] Evaluate auditor quality: is the confidence scoring meaningful or performative?
- [ ] Produce concrete, structural recommendations — NOT "add a paragraph about X to instructions" but changes to agent workflows, verification requirements, or pipeline structure that address root causes
- [ ] Recommendations must be grounded in evidence from the sampled tasks, not theoretical

## Context

The triggering incident: Task #18 (Configure MCP server registry) had an AC item "Template includes community GitHub MCP server (if applicable)". The researcher recommended including it at .85 confidence. This spawned #121 (Add GitHub remote MCP to setup.py). The architect approved it as "trivial". Six more agents processed it without questioning whether VS Code already provides this server via the Copilot extension. The entry is literally the same URL the extension uses.

Key files for the #18/#121 trail:
- kanban/tasks/018-configure-mcp-server-registry.md
- kanban/tasks/121-add-github-remote-mcp-server-to-setup-py-template.md
- docs/research/mcp-server-registry.md
- docs/research/github-mcp-server-setup-py.md

Agent definitions: agents/*.agent.md
Agent instructions: instructions/agent-common.instructions.md
Skills: skills/*/SKILL.md (especially arch-review, code-review, task-verification, research-workflow)

## Constraints

- Do NOT propose quick fixes or bandaids — this needs holistic analysis
- Do NOT modify any agent files, instructions, or skills — research only, propose changes
- Create follow-up tasks for each recommended structural change

[[2026-03-29]] Sun 23:46
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Audit decision trail for #18 and #121 | Doc S3.1 reconstructs per-agent trail | Pass |
| Sample 10-15 archived tasks | Doc S3.2 covers 88 archived tasks | Pass (exceeds requirement) |
| Identify weakest roles at omission vs commission | Doc S3.4 Error Type Blindness table | Pass |
| Assess instruction incentive structure | Doc S3.3 identifies anchoring cascade and trivial-label suppression | Pass |
| Evaluate architect review quality | Doc S3.2: 79% first-pass approval, pushback on AC not premise | Pass |
| Evaluate reviewer quality | Doc S3.2: 33 FAILs, 0 cite unnecessary feature | Pass |
| Evaluate auditor quality | Doc S3.2: 59% scores = .97, no calibration | Pass |
| Produce structural recommendations | Doc S4: 4 recommendations targeting skill changes | Pass |
| Recommendations evidence-grounded | Each R1-R4 traces to S3.3 gaps backed by task trails | Pass |

### Architecture Notes
Research-only task, no code changes. Research doc is complete at docs/research/pipeline-quality-audit.md. All 4 follow-up tasks (#194-#197) created at ideation for the full pipeline. Sample size (88 tasks) well exceeds the 10-15 AC requirement. Recommendations are structural (skill-level changes), not cosmetic. No TDD needed (research deliverable). Single domain: process/quality.

### Changes Made
- No AC changes needed: all lines are specific and verifiable
- Approved as-is

### Dependencies
- Follow-ups created: #194 (environment audit), #195 (premise challenge), #196 (necessity check), #197 (confidence scoring)
- No blocking dependencies

[[2026-03-30]] Mon 01:07
## Test-Writer Notes
- Non-implementation task (tagged research) â€” no tests applicable.
- Passing through to builder.

[[2026-03-30]] Mon 01:07
## Test-Writer Notes
- Non-implementation task (tagged research) -- no tests applicable.
- Passing through to builder.

[[2026-03-30]] Mon 01:28
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.

[[2026-03-30]] Mon 02:54
Review Evidence - See docs/scratch/192-reviewer.md for full evidence.

[[2026-03-30]] Mon 03:13
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Research-only task, no behavior or API change |
| 2 | Docstrings | No | N/A | No Python modules created or modified |
| 3 | docs/sources/overview.md | Yes | Pass | Pipeline Quality Audit (Task #192) section present with both external sources (Du et al. 2023, VS Code MCP Server Guide) |
| 4 | README.md | No | N/A | No CLI commands added or modified |
| 5 | Research doc produced | Yes | Pass | docs/research/pipeline-quality-audit.md exists; task body references it; follow-up tasks #194-#197 created |

### Files Updated
- None

### Scratch Files Cleaned
- docs/scratch/192-reviewer.md (deleted)
- docs/scratch/192-reviewer.tmp (deleted)

[[2026-03-30]] Mon 03:47
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Audit decision trail #18/#121 | S3.1: per-agent trail table, 9 agents traced | PASS |
| Sample 10-15 archived tasks | S3.2: 88 tasks analyzed (exceeds 10-15) | PASS |
| Identify weakest roles omission/commission | S3.4: Error Type Blindness table | PASS |
| Assess instruction incentives | S3.3: anchoring cascade + trivial-label suppression | PASS |
| Evaluate architect review quality | S3.2: 79% first-pass approval | PASS |
| Evaluate reviewer quality | S3.2: 33 FAILs, 0 cite unnecessary feature | PASS |
| Evaluate auditor quality | S3.2: 59% scores .97, no calibration | PASS |
| Produce structural recommendations | S4: R1-R4, skill-level changes | PASS |
| Recommendations evidence-grounded | Each R1-R4 traces to S3.3 gaps | PASS |

### Research Task Checks
- Doc exists: docs/research/pipeline-quality-audit.md (113 lines)
- Follow-ups: #194 (review), #195 (docs), #196 (in-progress), #197 (in-progress)
- Sources: docs/sources/overview.md updated

### Test Results
- pytest: 873 passed, 141 failed (all pre-existing RED-phase tests), 6 errors (pre-existing)
- ruff: clean in #192 scope

### AC Quality Score: 5/5
### Upstream Commit Gap
Deliverables uncommitted by upstream. Auditor commit: 193e903.
### Confidence: .98
### Action: archive

[[2026-03-30]] Mon 03:47
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 193e903 | docs | pipeline-quality-audit.md, overview.md | #192 |
