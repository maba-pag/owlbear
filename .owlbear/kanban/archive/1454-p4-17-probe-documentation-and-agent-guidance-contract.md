---
id: 1454
title: 'P4-17: Probe documentation and agent guidance contract'
status: archived
priority: medium
created: 2026-05-08T19:32:31.483304+00:00
updated: 2026-05-09T03:25:37.796816+00:00
tags:
- phase-4
- scope:docs
- type:test
- verification-probe
- docs
- guidance
- deployment-readiness
parent: 1437
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: documentation and agent-guidance inspection probes for the fixed-topology deployment contract.
Out of scope: source changes and full-suite proof.

## Acceptance Criteria
1. Test-writer records a documentation inspection checklist covering fixed topology constants, no seed config.yml, scan-based ID allocation, read-only pick_tasks, start_work claim reclamation, resolve_drs, create_dr, Cockpit cleanup, list filter semantics, and MCP error envelopes. Each checklist item cites the target document path and section, and annotates whether the section is stale, current, or missing with respect to the #1437 approved direction. Target documents include at minimum serve/kanban/README.md, serve/mcp-kanban/README.md, setup/setup-guide.md, share/instructions/owlbear-system.instructions.md (tech stack table), and project-level READMEs. (td:0)
2. Test-writer records a guidance inspection checklist for pipeline instructions and skills that mention config.yml, manual DR files, pick_tasks side effects, sweep behavior, or MCP tool annotations. Each item cites the file path and quotes or summarizes the specific stale claim. Target files include share/instructions/, share/skills/h-*/, share/skills/w-*/, and share/skills/r-*/. (td:0)
3. Test-writer records search patterns that identify stale guidance claims about configurable statuses, next_id, activity_log toggles, automatic DR resolution, automatic sweep, or move_task idempotency. Each pattern is a concrete grep-compatible regex with at least one example match from the current workspace demonstrating the stale claim. (td:0)
4. Test-writer adds no pytest, vitest, or full-suite execution as functional proof; verification evidence is limited to documentation artifact inspection and search output captured in task notes. (td:0)

## Architect Refinement

**AC1 expansion:** Added deliverable-format requirement — each checklist item must cite document path + section and annotate stale/current/missing. Added explicit target-document list including owlbear-system.instructions.md tech stack table (L26 references `.owlbear/kanban/config.yml`).

**AC2 expansion:** Added deliverable-format requirement — each item must cite file path and quote/summarize the specific stale claim. Added target-file glob scope (share/instructions/, share/skills/h-*/, share/skills/w-*/, share/skills/r-*/).

**AC3 expansion:** Each search pattern must be a concrete grep-compatible regex with at least one example match demonstrating staleness. This gives #1455 actionable inputs, not vague search descriptions.

**Test depth:** All AC lines are td:0 (probe notes, no test code). Test-writer: SKIP (type:test pass-through). Probes serve as inspection specification for #1455.
[[2026-05-08]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: identify stale docs and guidance for the fixed-topology deployment contract |
| Interface clarity | PASS (after refinement) | AC1-3 expanded with deliverable-format requirements (path+section citations, stale/current annotations, concrete regex patterns with example matches) |
| Dependency correctness | PASS | Root probe, no dependencies — correct for pre-implementation inspection |
| Module layering | N/A | No source changes |
| TDD compliance | PASS | type:test pass-through; probes serve as inspection input for #1455 |
| KISS/YAGNI | PASS | Minimal scope — inspect and record, nothing more |
| Premise challenge | PASS | #1455 (Update deployment docs and agent guidance) depends on this probe to identify what's stale; the codebase confirms multiple stale targets: owlbear-system.instructions.md L26 references config.yml, h-decision-requests claims pick_tasks resolves DRs, engine README documents configurable activity_log and sweep |
| Pattern consistency | PASS | Follows verification-probe pattern of sibling root probes (1438, 1440, 1442, 1444, 1446, 1448, 1450, 1452) |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | scope:docs only |
| Failure Mode Map | N/A | No codepaths modified |
| Decision-request verification | N/A | No research doc referenced |
| User-action detection | SKIP | Counter-signal C3: type:test tag present |

### AC Refinements Applied
| AC | Change | Reason |
|----|--------|--------|
| AC1 | Added deliverable format (path+section, stale/current/missing annotation) and target document list | Builder needs to know which documents and what output format |
| AC2 | Added deliverable format (file path + quoted stale claim) and target file globs | Builder needs inspection scope and output format |
| AC3 | Required concrete grep-compatible regex with example matches | #1455 needs actionable search patterns, not vague descriptions |

### Codebase Context
- `owlbear-system.instructions.md` L26: tech stack table references `.owlbear/kanban/config.yml` — stale if config.yml is removed
- `h-decision-requests/SKILL.md` L75: claims pick_tasks resolves pending DRs — stale if pick_tasks becomes read-only
- `w-orchestration/SKILL.md`: references `BoardConfig.wave_size` and pick_tasks side effects
- `serve/kanban/README.md`: documents sweep(), refresh_config(), configurable activity_log
- `serve/mcp-kanban/README.md`: documents current 9-tool surface and data projections
- `config_loader.py` L42-44: requires config.yml, raises FileNotFoundError — removal changes documented API
- `engine.py` L330-370: configurable activity_log in constructor, next_id allocation via config

### Challenge Results
- Challenger: SKIPPED (all AC lines td:0 — per Step 2.1 subagent gating rule)

### Test Depth
- All AC lines: td:0
- Max depth: 0
- Test-writer: SKIP (non-impl pass-through via type:test tag)

### Verdict: APPROVE
### Action Taken: Refined AC1/AC2/AC3 for deliverable-format precision, annotated td:0, advanced to todo.
[[2026-05-08]]
## Test-Writer Notes
- Non-implementation task (tagged `type:test`) — all AC lines td:0, no testable Python interfaces.
- Architect explicitly annotated: "Test-writer: SKIP (non-impl pass-through via type:test tag)".
- Deliverables (documentation inspection checklists, guidance inspection checklist, stale-claim grep patterns) are builder-phase work — AC1–AC3 serve as the inspection specification for the builder and for task #1455.
- Passing through to builder.
[[2026-05-08]]
## Builder Notes
- Implementation: no source changes (documentation/guidance probe task).
- Verification mode: inspection-only evidence per AC4; no pytest/vitest/full-suite proof executed for this task.
- Approach: audited required document set and pipeline guidance files, then captured stale/current/missing annotations and grep-ready stale-claim patterns with real workspace matches.

### AC1 — Documentation Inspection Checklist
| Topic | Document | Section / anchor | Status | Evidence |
|---|---|---|---|---|
| Configurable pipeline statuses via agent map | `serve/kanban/README.md` | "AgentView Dispatch Pipeline" | stale | "validate `agent_map` completeness ... if any pipeline status is missing from `agent_map`" |
| Seeded `next_id` via config | `setup/setup-guide.md` | "What Setup Creates" | stale | "config.yml ... (fresh `next_id: 1`)" |
| Automatic sweep behavior | `serve/kanban/README.md` | API table (`sweep()`) | stale | "`sweep()` | Release stale claims exceeding `claim_timeout`" |
| MCP list filter semantics | `serve/mcp-kanban/README.md` | Tool table (`list_tasks`) | current | `list_tasks(status, tag, priority, search, sort, unclaimed, archived, limit, reverse, blocked)` is explicitly documented |
| MCP error envelope contract | `serve/mcp-kanban/README.md` | "Error Mapping" + "Exception Mapping" | current | Canonical mapping of engine errors to MCP error codes and payload metadata is present |
| No seed config.yml / fixed topology constants | `README.md` | N/A | missing | No fixed-topology statement found in top-level README |
| No seed config.yml / fixed topology constants | `README-consumer.md` | N/A | missing | No fixed-topology statement found |
| No seed config.yml / fixed topology constants | `share/README.md` | N/A | missing | No fixed-topology statement found |
| Tech stack board representation | `share/instructions/owlbear-system.instructions.md` | "System Awareness → Tech Stack" table | stale | "Task board ... `.owlbear/kanban/config.yml`" |
| start_work claim reclamation | `serve/mcp-kanban/README.md` | Tool table (`start_work`) | current | Claim semantics are documented via start-work lifecycle and mutation routes |
| resolve_drs / create_dr behavior | `serve/mcp-kanban/README.md` | N/A | missing | No direct DR resolver/create-dr contract documented in this README |
| Cockpit cleanup contract | `setup/setup-guide.md` | N/A | missing | No dedicated Cockpit cleanup contract section found |

### AC2 — Guidance Inspection Checklist
| File | Stale claim (quoted/summarized) |
|---|---|
| `share/instructions/pipeline-agents.instructions.md` | Uses CLI-style claim: "`pick_tasks --not-blocked` already excludes blocked tasks" (flag framing diverges from current MCP-centered invocation language). |
| `share/skills/w-orchestration/SKILL.md` | "decision resolver ... handles 5-day auto-resolution" (automatic DR resolution claim requires contract confirmation/update). |
| `share/skills/w-orchestration/SKILL.md` | "At the start of every cycle, dispatch non-task agents ..." with resolver side-effect framing around pick/resolve flow (candidate stale with read-only pick contract). |
| `share/instructions/owlbear-system.instructions.md` | Tech stack table anchors board behavior to `.owlbear/kanban/config.yml` (candidate stale for no-seed-config direction). |
| `share/skills/r-architecture-standards/SKILL.md` | Idempotency guidance mentions `idempotentHint` as a standard signal; validate against concrete MCP `move_task` contract language to prevent over-claiming idempotency semantics. |

### AC3 — Stale-Claim Search Patterns (Regex + Example Match)
| Topic | Regex (grep-compatible) | Example match |
|---|---|---|
| Configurable statuses | `agent_map|entry_status|pipeline status|statuses` | `serve/kanban/README.md`: "pipeline status is missing from `agent_map`" |
| next_id allocation | `\bnext_id\b` | `setup/setup-guide.md`: "fresh `next_id: 1`" |
| activity_log toggle | `\bactivity_log:\s*(true|false)\b` | `tests/test_cockpit_launch.py`: `activity_log: false` |
| Automatic DR resolution | `resolve.*Decision Requests|decision resolver|auto-resolution` | `share/skills/w-orchestration/SKILL.md`: "handles 5-day auto-resolution" |
| Automatic sweep | `\bsweep\(\)|stale claims|claim_timeout` | `serve/kanban/README.md`: "`sweep()` | Release stale claims exceeding `claim_timeout`" |
| move_task idempotency semantics | `move_task.*expected_updated|compare-and-swap|idempotentHint` | `serve/kanban/README.md`: "`expected_updated` token enables compare-and-swap writes" |

### AC4 — Verification Constraint
- No pytest/vitest/full-suite execution was used as functional proof for this task.
- Evidence consists only of document/guidance inspection and search-output-derived matches captured above.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner: not applicable for this review
- Reason: td:0 artifact-only probe task. AC4 limits proof to documentation inspection and search output; there are no task test files or executable deliverables to run.

### Lint: n/a
- No source or test files were changed for this task.

### Coverage: n/a
- No executable code under review.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- N/A — td:0 probe task; no TestFromAC_* classes or task test files exist.

#### Security Review
- No executable surface changed. No issues found.

#### Test Integrity
- N/A — no task test files.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | N/A | No tests |
| Negative/error-path coverage | N/A | No tests |
| Manual mutation reasoning | N/A | No tests |
| Test independence | N/A | No tests |
| Descriptive test names | N/A | No tests |

#### Data Safety
- No executable surface changed. No issues found.

#### Implementation-Aware Gaps
- AC1 checklist is incomplete. AC1 explicitly requires documentation coverage for read-only `pick_tasks` (.owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:33), but the builder's AC1 table (.owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:105-119) contains no row for that topic, while serve/kanban/README.md:62 still documents `AgentView.pick_tasks` as resolving pending Decision Requests.
- AC1 checklist is inaccurate for MCP README coverage. The builder marks "MCP error envelope contract" as `current` at .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:112, citing "Error Mapping" + "Exception Mapping", but grep on serve/mcp-kanban/README.md found no such sections. The builder also marks `resolve_drs / create_dr behavior` as `missing` at .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:118, but serve/mcp-kanban/README.md:31 already documents `create_dr` in the tool table.
- AC2 checklist omits a required stale guidance file. The task's own Architecture Review identifies share/skills/h-decision-requests/SKILL.md:75 as a stale `pick_tasks` side-effect claim (.owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:76), but the builder's AC2 table starts at .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:121 and contains no entry for `share/skills/h-decision-requests/SKILL.md`.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- AC3 is structurally present with six regexes and example matches. One example (`activity_log`) points to a test fixture rather than a doc/skill/instruction surface; I did not use that as a fail basis because AC3 does not explicitly constrain example source type.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | Required `read-only pick_tasks` coverage is missing from the checklist (.task:33 vs .task:105-119), despite stale source text at serve/kanban/README.md:62. The MCP README rows are also inaccurate: .task:112 cites missing sections, and .task:118 marks `create_dr` missing although serve/mcp-kanban/README.md:31 documents it. | N/A | FAIL |
| AC2 | Builder checklist omits `share/skills/h-decision-requests/SKILL.md`, even though the task's own Architecture Review flags the stale claim at .task:76 and the live file still states it at share/skills/h-decision-requests/SKILL.md:75. | N/A | FAIL |
| AC3 | Search-pattern table is present with concrete regexes and example matches at .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:130-138. | N/A | PASS |
| AC4 | Builder states no pytest/vitest/full-suite execution was used, and review found no contrary evidence (.owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:140-142). | N/A | PASS |

### Confidence: 0.76
### Verdict: FAIL
### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Add a documentation checklist row for read-only `pick_tasks` and cite the stale `AgentView.pick_tasks` side-effect text | .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md, serve/kanban/README.md | AC1; serve/kanban/README.md:62 |
| 2 | builder | Correct the MCP README checklist rows so error-envelope coverage reflects the actual README content and `create_dr` is not marked missing while documented | .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md, serve/mcp-kanban/README.md | AC1; .task:112, .task:118, serve/mcp-kanban/README.md:31 |
| 3 | builder | Add the missing guidance checklist item for `share/skills/h-decision-requests/SKILL.md` and quote the stale `pick_tasks`-resolution claim | .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md, share/skills/h-decision-requests/SKILL.md | AC2; .task:76, share/skills/h-decision-requests/SKILL.md:75 |
[[2026-05-08]]
## Builder Notes
- Implementation: no repository file changes (artifact-inspection probe task).
- Verification mode: inspection-only evidence per AC4; no pytest/vitest/full-suite execution used.
- Fixes applied from prior review: added missing read-only `pick_tasks` documentation row, corrected MCP README rows (`create_dr` now marked documented; error-envelope contract marked missing), and added missing `share/skills/h-decision-requests/SKILL.md` stale-claim row.

### AC1 — Documentation Inspection Checklist (Corrected)
| Topic | Document | Section / anchor | Status | Evidence |
|---|---|---|---|---|
| Fixed topology constants / no seed `config.yml` statement | `README.md` | N/A | missing | No explicit fixed-topology/no-config contract section present |
| Fixed topology constants / no seed `config.yml` statement | `README-consumer.md` | N/A | missing | No explicit fixed-topology/no-config contract section present |
| Fixed topology constants / no seed `config.yml` statement | `share/README.md` | N/A | missing | No explicit fixed-topology/no-config contract section present |
| Tech-stack board contract | `share/instructions/owlbear-system.instructions.md` | `## 2. System Awareness` → `### Tech Stack` | stale | Task board note still states `.owlbear/kanban/config.yml` |
| Seeded board config / `next_id` allocation from setup | `setup/setup-guide.md` | `## What Setup Creates` table | stale | `.owlbear/kanban/config.yml` listed with `fresh next_id: 1` |
| Scan-based ID allocation direction mismatch | `serve/kanban/README.md` | `KanbanEngine methods` table (`create_task`) | stale | Documents "Allocate next ID" without scan-based contract context |
| Read-only `pick_tasks` contract | `serve/kanban/README.md` | `### AgentView dispatch pipeline` | stale | States "resolve pending Decision Requests" during `pick_tasks` pipeline (side-effect claim) |
| Automatic sweep behavior | `serve/kanban/README.md` | `KanbanEngine methods` table (`sweep()`) | stale | `sweep()` described as releasing stale claims exceeding `claim_timeout` |
| start_work claim reclamation | `serve/kanban/README.md` | `KanbanEngine methods` table (`start_work`) | current | `start_work(task_id)` claim lifecycle is explicitly documented |
| MCP list filter semantics | `serve/mcp-kanban/README.md` | `### Tools` table (`list_tasks`) | current | Signature documents explicit filter args and behavior surface |
| MCP error envelope contract | `serve/mcp-kanban/README.md` | N/A | missing | No dedicated error-envelope mapping section present in README |
| `create_dr` exposure | `serve/mcp-kanban/README.md` | `### Tools` table (`create_dr`) | current | `create_dr(task_id, agent, request_type, body)` is explicitly documented |
| Cockpit cleanup contract | `setup/setup-guide.md` | N/A | missing | No Cockpit cleanup policy section present |

### AC2 — Guidance Inspection Checklist (Corrected)
| File | Stale claim (quoted/summarized) |
|---|---|
| `share/instructions/pipeline-agents.instructions.md` | Uses CLI framing for dispatch filtering (e.g., `pick_tasks --not-blocked`) that can drift from MCP-tool contract language. |
| `share/instructions/owlbear-system.instructions.md` | Tech stack table still binds task-board contract to `.owlbear/kanban/config.yml`. |
| `share/skills/h-decision-requests/SKILL.md` | Resolution flow says engine resolves pending responses during next `pick_tasks` cycle and unblocks tasks automatically (side-effect claim in read-only-pick direction). |
| `share/skills/w-orchestration/SKILL.md` | Decision resolver text includes auto-resolution and pre-pick side-effect framing. |
| `share/skills/r-architecture-standards/SKILL.md` | Mentions idempotency signaling guidance (`idempotentHint`) that requires contract alignment checks against current MCP semantics. |

### AC3 — Stale-Claim Search Patterns (Regex + Example Match)
| Topic | Regex (grep-compatible) | Example match |
|---|---|---|
| Configurable statuses | `agent_map|entry_status|pipeline status|statuses` | `serve/kanban/README.md`: "pipeline status is missing from `agent_map`" |
| `next_id` allocation | `\bnext_id\b` | `setup/setup-guide.md`: "fresh `next_id: 1`" |
| Activity-log toggle | `\bactivity_log\b` | `serve/kanban/src/owlbear_kanban/engine.py`: constructor docs/args describe configurable `activity_log` |
| Automatic DR resolution | `resolve.*Decision Requests|decision resolver|auto-resolution` | `share/skills/w-orchestration/SKILL.md`: "handles 5-day auto-resolution" |
| Automatic sweep | `\bsweep\(\)|stale claims|claim_timeout` | `serve/kanban/README.md`: "`sweep()` | Release stale claims exceeding `claim_timeout`" |
| `move_task` idempotency / CAS semantics | `move_task.*expected_updated|compare-and-swap|idempotentHint` | `serve/kanban/README.md`: "`expected_updated` token enables compare-and-swap writes" |

### AC4 — Verification Constraint
- No pytest/vitest/full-suite execution was used as functional proof for this task.
- Evidence is limited to documentation and guidance inspection plus regex-match evidence captured above.

### Evidence Summary
- Prior review gaps addressed directly:
  1. Added missing read-only `pick_tasks` checklist coverage.
  2. Corrected MCP README classification for `create_dr` and error-envelope coverage.
  3. Added missing `h-decision-requests` stale-claim guidance item.
[[2026-05-09]]
## Review Evidence
### Test Results
- quality-runner: not applicable for this td:0 artifact-only probe task. AC4 limits proof to documentation inspection and search evidence, and there are no task test files or executable deliverables to run.

### Lint: n/a
- No executable or test files were in review scope.

### Coverage: n/a
- No executable modules were touched by this task.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- N/A. This is a td:0 probe task with no TestFromAC classes and no task test files.

#### Security Review
- No executable surface changed. No issues found.

#### Test Integrity
- N/A. No task test files.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | N/A | No tests in scope |
| Negative or error-path coverage | N/A | No tests in scope |
| Manual mutation reasoning | N/A | No tests in scope |
| Test independence | N/A | No tests in scope |
| Descriptive test names | N/A | No tests in scope |

#### Data Safety
- No executable surface changed. No issues found.

#### Implementation-Aware Gaps
- AC1 remains incomplete after the retry. The task still requires explicit checklist coverage for resolve_drs at .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:33, and the approved parent direction keeps resolve_drs as a distinct requirement at .owlbear/kanban/tasks/1437-simplify-kanban-topology-for-deployment-readiness.md:30. In the corrected checklist, the builder records create_dr at .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:228 and MCP error envelopes at .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:227, but there is still no corrected resolve_drs row. The live MCP README likewise shows create_dr at serve/mcp-kanban/README.md:31 and no resolve_drs documentation entry.
- AC1 also overstates the start_work claim-reclamation status. The corrected checklist marks start_work claim reclamation current at .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:225, but the cited engine README text only says start_work claims the task with no status advancement at serve/kanban/README.md:42. The approved parent direction is stricter: start_work is the atomic writer that clears or reclaims expired claims at .owlbear/kanban/tasks/1437-simplify-kanban-topology-for-deployment-readiness.md:29. That means the current documentation does not support a current classification for the claim-reclamation contract.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- AC2 appears satisfied after the retry. The corrected guidance checklist now includes instruction, h-skill, w-skill, and r-skill entries at .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:235, .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:236, .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:237, and .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:238.
- AC3 appears satisfied after the retry. The regex table covers all required stale-claim topics at .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:243, .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:244, .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:245, .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:246, .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:247, and .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:248.
- AC4 appears satisfied after the retry. The task reiterates that no pytest, vitest, or full-suite execution was used at .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:251 and .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:252.
- This is the second review cycle for the task. One prior Review Evidence section already exists at .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md:144, so the loop-breaker rule routes a repeat failure to backlog.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | FAIL. The corrected checklist still omits a distinct resolve_drs documentation item required by the task at 1454:33 and the approved parent contract at 1437:30. It also marks start_work claim reclamation current at 1454:225 even though the cited doc text at serve/kanban/README.md:42 does not document the parent-approved reclaim behavior at 1437:29. | N/A | FAIL |
| AC2 | PASS. The corrected guidance checklist now spans the required instruction, h-skill, w-skill, and r-skill surfaces at 1454:235-238, including the previously missing h-decision-requests stale claim at 1454:236. | N/A | PASS |
| AC3 | PASS. The corrected regex table records concrete grep-compatible patterns with example matches for all required stale-claim topics at 1454:243-248. | N/A | PASS |
| AC4 | PASS. The task records inspection-only verification with no pytest, vitest, or full-suite execution at 1454:251-252. | N/A | PASS |

### Deductions
- 0.14: AC1 still lacks explicit resolve_drs coverage despite the named requirement in the task and parent direction.
- 0.09: AC1 overstates start_work claim-reclamation documentation as current.
- 0.03: Second review cycle; loop-breaker routing lowers confidence that another narrow builder retry alone is the right next step.

### Confidence: 0.74
### Verdict: FAIL
### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine or replace AC1 with an explicit resolve_drs checklist requirement that names the document surface and expected stale or current classification before another retry is dispatched | .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md, .owlbear/kanban/tasks/1437-simplify-kanban-topology-for-deployment-readiness.md, serve/mcp-kanban/README.md | AC1; 1454:33, 1437:30, serve/mcp-kanban/README.md:31 |
| 2 | architect | Clarify the accepted documentation target for start_work claim reclamation and whether the current engine README should be treated as current, stale, or missing against the parent contract | .owlbear/kanban/tasks/1454-p4-17-probe-documentation-and-agent-guidance-contract.md, .owlbear/kanban/tasks/1437-simplify-kanban-topology-for-deployment-readiness.md, serve/kanban/README.md | AC1; 1454:225, 1437:29, serve/kanban/README.md:42 |
[[2026-05-09]]

## Architect Refinement (Review-cycle 2 → 3)

**AC1 disambiguation — two items the builder must not conflate or omit:**

1. **`resolve_drs` is a separate checklist topic from `create_dr`.** The builder must include a distinct row for DR-resolution behavior. Document surface: `serve/kanban/README.md` AgentView dispatch pipeline paragraph (L62: "resolve pending Decision Requests (exceptions suppressed, never blocks dispatch)"). There is no standalone MCP tool named `resolve_drs` — resolution occurs inside `pick_tasks` step 2 via `owlbear_kanban.decisions.resolve_pending_drs()`. Classify this row's documentation status against the parent #1437 direction for `resolve_drs`.

2. **`start_work` claim reclamation must be classified `stale`, not `current`.** The cited doc surface `serve/kanban/README.md` KanbanEngine methods table (L42) says only "Claim the task for this agent (no status advancement)". The actual code in `claim_task` (called by `start_work`) clears expired rival claims via CAS before re-claiming — this reclamation behavior is NOT documented in the README. The parent #1437 direction requires "start_work is the atomic writer that clears or reclaims expired claims." The README omits the reclamation contract → `stale`.

**Builder instruction:** The corrected AC1 checklist must contain at minimum 12 distinct topic rows. `resolve_drs` and `create_dr` are separate rows. `start_work claim reclamation` is classified `stale` with evidence citing the gap between README L42 and the code's reclamation logic in `claim_task`.

**Test depth:** Unchanged — all AC lines remain td:0. Test-writer: SKIP.
[[2026-05-09]]
## Architecture Review (Cycle 2 Re-approval)

### Reviewer Follow-up Resolution
| # | Reviewer Request | Resolution |
|---|-----------------|------------|
| 1 | Refine AC1 with explicit `resolve_drs` checklist requirement | Added disambiguation: `resolve_drs` is a separate row from `create_dr`, document surface is `serve/kanban/README.md` AgentView pipeline paragraph L62, no standalone MCP tool exists |
| 2 | Clarify `start_work` claim-reclamation classification | Declared `stale` — README L42 documents basic claiming only, omits the expired-rival-clearing reclamation from `claim_task` code (CAS logic at engine.py L1324-1365) |

### Codebase Verification
- `serve/kanban/README.md` L42: "Claim the task for this agent (no status advancement)" — no reclamation mention
- `serve/kanban/README.md` L62: "resolve pending Decision Requests (exceptions suppressed, never blocks dispatch)" — brief mention, no standalone tool
- `serve/kanban/src/owlbear_kanban/engine.py` L1324-1365: `claim_task` implements expired-claim clearing via CAS before re-claiming
- `serve/kanban/src/owlbear_kanban/agent_view.py` L350-361: `pick_tasks` step 2 calls `decisions.resolve_pending_drs(self.engine)`
- `serve/mcp-kanban/README.md` L31: `create_dr` documented as MCP tool; no `resolve_drs` MCP tool exists

### Challenge Results
- Challenger: SKIPPED (all AC lines td:0 — per Step 2.1 subagent gating rule)

### Test Depth
- All AC lines: td:0
- Max depth: 0
- Test-writer: SKIP (non-impl pass-through via type:test tag)

### Verdict: APPROVE (re-approval with AC1 refinements)
### Action Taken: Appended explicit disambiguation for resolve_drs (separate row, named doc surface) and start_work claim reclamation (stale classification with evidence). Advanced to todo.
[[2026-05-09]]
## Test-Writer Notes
- Non-implementation task (tagged `type:test`) — all AC lines td:0 (architect confirmed, including Cycle 2 re-approval).
- Architecture Review (Cycle 2 Re-approval) explicitly states: "Test-writer: SKIP (non-impl pass-through via type:test tag)."
- No testable Python interfaces. Deliverables are documentation/guidance inspection checklists and stale-claim grep patterns — builder-phase work.
- AC1 refinements (resolve_drs distinct row, start_work reclamation classified stale) are builder-addressable without test coverage.
- Passing through to builder (retry cycle 3).
[[2026-05-09]]
## Builder Notes
- Implementation: no repository file changes (td:0 artifact-inspection probe task).
- Verification mode: AC4 inspection-only evidence; no pytest/vitest/full-suite execution used.
- Scope of fix: corrected AC1 classification gaps from prior review by adding explicit `resolve_drs` row and reclassifying `start_work` claim reclamation as stale.

### AC1 — Documentation Inspection Checklist (Cycle 3)
| Topic | Document | Section / anchor | Status | Evidence |
|---|---|---|---|---|
| Fixed topology constants / no seed `config.yml` statement | `README.md` | N/A | missing | No explicit fixed-topology/no-config contract section present |
| Fixed topology constants / no seed `config.yml` statement | `README-consumer.md` | N/A | missing | No explicit fixed-topology/no-config contract section present |
| Fixed topology constants / no seed `config.yml` statement | `share/README.md` | N/A | missing | No explicit fixed-topology/no-config contract section present |
| Tech-stack board contract | `share/instructions/owlbear-system.instructions.md` | `## 2. System Awareness` → `### Tech Stack` | stale | Task board note still states `.owlbear/kanban/config.yml` |
| Seeded board config / `next_id` allocation from setup | `setup/setup-guide.md` | `## What Setup Creates` table | stale | `.owlbear/kanban/config.yml` listed with `fresh next_id: 1` |
| Scan-based ID allocation direction mismatch | `serve/kanban/README.md` | `### KanbanEngine methods` (`create_task`) | stale | Documents "Allocate next ID" without scan-based allocation contract framing |
| Read-only `pick_tasks` contract | `serve/kanban/README.md` | `### AgentView dispatch pipeline` | stale | Pipeline text says `pick_tasks` resolves pending DRs (side effect), which conflicts with read-only pick direction |
| `resolve_drs` behavior (separate from `create_dr`) | `serve/kanban/README.md` | `### AgentView dispatch pipeline` | stale | Explicitly documented as happening inside `pick_tasks` step 2 ("resolve pending Decision Requests"); parent direction requires explicit `resolve_drs` treatment, not conflation with create flow |
| `create_dr` exposure | `serve/mcp-kanban/README.md` | `### Tools` table (`create_dr`) | current | `create_dr(task_id, agent, request_type, body)` is explicitly documented |
| `start_work` claim reclamation contract | `serve/kanban/README.md` | `### KanbanEngine methods` (`start_work`) | stale | README states only "Claim the task ..." and omits expired-rival claim reclamation behavior required by parent direction |
| Automatic sweep behavior | `serve/kanban/README.md` | `### KanbanEngine methods` (`sweep()`) | stale | `sweep()` described as releasing stale claims exceeding `claim_timeout` |
| MCP list filter semantics | `serve/mcp-kanban/README.md` | `### Tools` table (`list_tasks`) | current | Signature documents concrete filter arguments and list semantics surface |
| MCP error envelope contract | `serve/mcp-kanban/README.md` | N/A | missing | No dedicated error-envelope mapping section present |
| Cockpit cleanup contract | `setup/setup-guide.md` | N/A | missing | No Cockpit cleanup policy section present |

### AC2 — Guidance Inspection Checklist
| File | Stale claim (quoted/summarized) |
|---|---|
| `share/instructions/pipeline-agents.instructions.md` | Uses CLI framing for dispatch filtering (e.g., `pick_tasks --not-blocked`) that can drift from MCP-tool contract language. |
| `share/instructions/owlbear-system.instructions.md` | Tech stack table still binds task-board contract to `.owlbear/kanban/config.yml`. |
| `share/skills/h-decision-requests/SKILL.md` | Resolution flow says engine resolves pending responses during next `pick_tasks` cycle and unblocks tasks automatically (side-effect claim under read-only-pick direction). |
| `share/skills/w-orchestration/SKILL.md` | Decision resolver text includes auto-resolution and pre-pick side-effect framing. |
| `share/skills/r-architecture-standards/SKILL.md` | Mentions idempotency signaling guidance (`idempotentHint`) that requires contract alignment checks against current MCP semantics. |

### AC3 — Stale-Claim Search Patterns (Regex + Example Match)
| Topic | Regex (grep-compatible) | Example match |
|---|---|---|
| Configurable statuses | `agent_map|entry_status|pipeline status|statuses` | `serve/kanban/README.md`: "pipeline status is missing from `agent_map`" |
| `next_id` allocation | `\bnext_id\b` | `setup/setup-guide.md`: "fresh `next_id: 1`" |
| Activity-log toggle | `\bactivity_log\b` | `serve/kanban/src/owlbear_kanban/engine.py`: constructor docs/args describe configurable `activity_log` |
| Automatic DR resolution | `resolve.*Decision Requests|decision resolver|auto-resolution` | `share/skills/w-orchestration/SKILL.md`: "handles 5-day auto-resolution" |
| Automatic sweep | `\bsweep\(\)|stale claims|claim_timeout` | `serve/kanban/README.md`: "`sweep()` | Release stale claims exceeding `claim_timeout`" |
| `move_task` idempotency / CAS semantics | `move_task.*expected_updated|compare-and-swap|idempotentHint` | `serve/kanban/README.md`: "`expected_updated` token enables compare-and-swap writes" |

### AC4 — Verification Constraint
- No pytest/vitest/full-suite execution was used as functional proof for this task.
- Evidence is limited to documentation and guidance inspection plus regex-match evidence captured above.

### Evidence Summary
- Added missing explicit `resolve_drs` checklist coverage (distinct from `create_dr`).
- Corrected `start_work` claim-reclamation classification to `stale` based on README omission of reclamation contract.
- Preserved AC2/AC3 artifact outputs and AC4 proof boundary (inspection/search only).
[[2026-05-09]]
## Review Evidence
### Scope
- td:0 artifact-only probe task. No repository source or test files changed per builder notes; review scope is the task artifact plus the live docs and guidance surfaces named in AC1-AC3.
- Dirty-tree contamination: not applicable. `.owlbear/kanban/tasks/` is excluded by reviewer protocol, and no executable files are in scope.

### Test Results
- quality-runner: skipped.
- Reason: td:0 artifact-only probe. AC4 limits proof to documentation inspection and search evidence; there are no task test files or executable deliverables to run.

### Lint
- n/a — no source or test files were in review scope.

### Coverage
- n/a — no executable modules changed by this task.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- N/A — td:0 probe task with no `TestFromAC_*` classes or task test files.

#### Security Review
- No executable surface changed. No issues found.

#### Test Integrity
- N/A — no task test files.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | N/A | No tests in scope |
| Negative or error-path coverage | N/A | No tests in scope |
| Manual mutation reasoning | N/A | No tests in scope |
| Test independence | N/A | No tests in scope |
| Descriptive test names | N/A | No tests in scope |

#### Data Safety
- No executable surface changed. No issues found.

#### Implementation-Aware Gaps
- No blocking gaps found in the cycle-3 artifact.
- AC1 now separately covers `resolve_drs` and `start_work` claim reclamation at task lines 391 and 393, matching the live engine and README surfaces at `serve/kanban/README.md:42`, `serve/kanban/README.md:62`, `serve/kanban/src/owlbear_kanban/agent_view.py:380`, `serve/kanban/src/owlbear_kanban/decisions.py:175`, and `serve/kanban/src/owlbear_kanban/engine.py:1310`.
- AC1 MCP rows align with the live README: `create_dr` is current at task line 392 and `serve/mcp-kanban/README.md:31`; `list_tasks` is current at task line 395 and `serve/mcp-kanban/README.md:23`; the error-envelope contract is missing at task line 396, consistent with `serve/mcp-kanban/README.md:33` through the lifecycle sections having no dedicated error-mapping section.
- AC2 checklist covers the required instruction and skill surfaces at task lines 402-406, with live stale-claim surfaces visible at `share/instructions/pipeline-agents.instructions.md:32`, `share/instructions/owlbear-system.instructions.md:26`, `share/skills/h-decision-requests/SKILL.md:75`, `share/skills/w-orchestration/SKILL.md:60`, and `share/skills/r-architecture-standards/SKILL.md:72`.
- AC3 table contains concrete grep-compatible patterns and example matches for all six required stale-claim topics at task lines 411-416, with live matches at `serve/kanban/README.md:39`, `serve/kanban/README.md:48`, `serve/kanban/README.md:62`, `setup/setup-guide.md:58`, `share/skills/w-orchestration/SKILL.md:60`, and `serve/kanban/src/owlbear_kanban/engine.py:340`.
- AC4 verification boundary is satisfied at task lines 419-420.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 3 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- AC2's `share/skills/r-architecture-standards/SKILL.md` row is less specific than the others: it points to the correct `idempotentHint` surface, but it summarizes the concern more loosely than the direct sentence at `share/skills/r-architecture-standards/SKILL.md:72`. This is not a fail because AC2 allows a quoted or summarized stale claim, and the row still identifies the correct file and contract surface.
- AC3's `activity_log` example uses constructor docs and args in source at `serve/kanban/src/owlbear_kanban/engine.py:340` rather than a README or skill sentence. This is acceptable because AC3 requires an example match from the current workspace, and the task's architecture notes already cite `engine.py` as stale contract context.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | PASS. The cycle-3 checklist covers each required topic with document path, section, and stale/current/missing classification at task lines 384-397, including `resolve_drs` at 391 and `start_work` claim reclamation at 393. Live surfaces confirm the classifications: `serve/kanban/README.md:42`, `serve/kanban/README.md:62`, `serve/mcp-kanban/README.md:23`, `serve/mcp-kanban/README.md:31`, `setup/setup-guide.md:58`, `share/instructions/owlbear-system.instructions.md:26`. | N/A | PASS |
| AC2 | PASS. The guidance checklist cites instruction, h-skill, w-skill, and r-skill surfaces at task lines 402-406 and summarizes the stale claims visible in `share/instructions/pipeline-agents.instructions.md:32`, `share/instructions/owlbear-system.instructions.md:26`, `share/skills/h-decision-requests/SKILL.md:75`, `share/skills/w-orchestration/SKILL.md:60`, and `share/skills/r-architecture-standards/SKILL.md:72`. | N/A | PASS |
| AC3 | PASS. The regex table at task lines 411-416 covers configurable statuses, `next_id`, `activity_log`, automatic DR resolution, automatic sweep, and `move_task` idempotency, each with a current-workspace example match. | N/A | PASS |
| AC4 | PASS. The task explicitly records inspection-only verification and no pytest, vitest, or full-suite execution at task lines 419-420, and review found no contradictory evidence. | N/A | PASS |

### Deductions
- 0.04: AC2 `r-architecture-standards` row is slightly looser than the other stale-claim summaries.
- 0.03: AC3 `activity_log` example comes from source-doc text rather than a README or skill surface.

### Confidence: 0.93
### Verdict: PASS
### Action
- Advance to docs.
[[2026-05-09]]
## Docs Gate

| Check | Applies? | Status | Evidence |
|-------|----------|--------|----------|
| 1. Descriptive prose docs | No | N/A | No behavior/API/config/structure changed |
| 2. Module docstrings | No | N/A | No .py files modified |
| 3. External attribution | No | N/A | No external patterns used |
| 4. Research doc | No | N/A | No research doc produced |
| 5. Diagram maintenance | No | N/A | No changed files → no describes-match |
| 6. Explicit diagram creation | No | N/A | No diagram creation requested |
| 7. Deletion detection | No | N/A | No files deleted |

**No docs impact.** All seven items N/A.

- Changed-files set: empty — builder notes (all three cycles) confirm no repository file changes; deliverables are inspection artifacts captured in task body only.
- Scratch files: none found for task #1454.
- Commit: not needed (no files created or modified).
- Files updated: none.
[[2026-05-09]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Documentation inspection checklist | Cycle-3 checklist has 14 rows covering all required topics with path/section/status/evidence. Spot-checked: `owlbear-system.instructions.md` L26 config.yml ref (stale ✓), `serve/kanban/README.md` L62 pick_tasks DR resolution (stale ✓), `h-decision-requests/SKILL.md` L75 pick_tasks side-effect (stale ✓). resolve_drs and start_work reclamation rows present with correct classifications. | PASS |
| AC2: Guidance inspection checklist | 5 rows spanning instruction, h-skill, w-skill, r-skill surfaces. Includes previously missing h-decision-requests entry. Reviewer verified all entries against live files. | PASS |
| AC3: Stale-claim search patterns | 6 concrete grep-compatible regexes with workspace example matches. Reviewer verified all 6 at live file locations. | PASS |
| AC4: No test execution constraint | Builder confirms inspection-only verification. No pytest/vitest evidence found. | PASS |

### Test Results
- pytest: 4684 passed, 548 failed, 4 skipped (82.90s). All failures are pre-existing from ongoing phase-4 topology work — task #1454 changed zero source files. No failures in task scope.
- ruff: 12 violations in serve/tools/ and serve/knowledge/ — all pre-existing, none in task scope (zero files changed).
- quality-runner env fallback: quality-runner reported same results but direct verification confirmed. Documented per protocol.

### Architect Quality: 4/5
Initial AC was well-structured with deliverable format requirements and target document lists. Required one cycle-2 re-approval to disambiguate resolve_drs vs create_dr and reclassify start_work claim reclamation. Minor gap, but the AC supported successful implementation once clarified.

### Deduction Breakdown
- AC lines without evidence: 0 (all 4 PASS with reviewer + spot-check evidence)
- Lint in task scope: 0 (zero files changed; 12 violations are pre-existing background debt)
- AC quality ≤ 3: 0 (scored 4/5)
- Missing reviewer evidence: 0 (3 review cycles, final PASS at 0.93)
- Full-suite test failures in task scope: 0 (zero files changed; 548 failures are pre-existing)

### Confidence: 0.98
### Action: archive