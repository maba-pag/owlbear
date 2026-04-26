---
id: 1124
title: 'Research: reconcile end-work outcome contract'
status: backlog
priority: important
created: 2026-04-25 17:19:08.063026+00:00
updated: 2026-04-26T02:18:32.192769+00:00
tags:
- research
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

[[2026-04-25]]
## Research
- Research doc: .owlbear/research/reconcile-end-work-outcome-contract.md
- Sources: 9 studied, 9 high-relevance (all codebase-internal)
- Recommendation: Restore `fail` to AgentView.end_work valid_outcomes (confidence: 0.82)
- Follow-up tasks created: #1125 (restore fail + align model, needed), #1126 (remove dead fallback chain, nice-to-have)
- Decision requests: none (T1 — bug fix restoring documented pipeline behavior)

## Challenge Results
- Challenger: reconsider (confidence in original: 0.34)
- Rebuttal: (a) #1077 architect explicitly deferred MCP alignment to this task; (b) `release` drops notes — not a substitute for `fail`; (c) pipeline protocol is authoritative and mandates `fail` for 3 active use cases
- Post-challenge confidence: 0.82

## Key Finding
`release` does NOT append timestamped notes (goes through `release_task`), while `fail` DOES (goes through raw `engine.end_work`). Pipeline protocol's 3 `fail` use cases (TOOL_UNAVAILABLE, prerequisite handoff, agent handoff) all require note appending. Replacing `fail` with `release` would silently drop agent diagnostic notes — a data-loss gap.
[[2026-04-25]]
## Architecture Review

### Verdict: REJECT → research

### AC Assessment
No implementation AC present (research umbrella task). Research quality assessed instead.

### Critical Gaps Found

**1. Brief B D52 authority conflict — not addressed**
Brief B `decisions.md` D52 explicitly dropped `fail` as a deliberate design choice ("orphan-claim foot-gun"), not a bug. The research doc doesn't reference D52 at all. This transforms the recommendation from T1 (bug fix) to T3 (authority reversal) which requires a Decision Request per `w-arch-review` criterion 12.

**2. The "data loss" finding is actually a `release` implementation bug**
Brief B D52 specifies: "`release`: clears claim, no status change, `note` appended if set." The current code routes `release` through `release_task()` which does NOT append notes — contradicting D52. The research doc treats this as evidence that `fail` must be restored, but the correct reading is that `release` has an unimplemented D52 requirement. If `release` is fixed to append notes (as D52 intended), the semantic gap between `fail` and `release` disappears, and the pipeline protocol use cases could work with `release`.

**3. Two-option analysis needed**
The research should present both paths:
- **Option X**: Fix `release` to append notes per D52 + update pipeline protocol/agents to use `release` instead of `fail`
- **Option Y**: Restore `fail` (override D52) — the current recommendation

Each needs: diff size, authority implications, test impact, and migration cost.

**4. Follow-up tasks lack AC**
#1125 and #1126 have empty bodies. Pipeline protocol requires concrete acceptance criteria on all follow-ups.

### Evaluation (partial — research quality)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Research scope is focused |
| Premise challenge | FAIL | Missed Brief B D52 — the authoritative design source for end_work outcomes |
| Pattern consistency | FAIL | Recommendation overrides Brief B without acknowledging the override |
| KISS/YAGNI | DEFERRED | Cannot assess until both options are analyzed |

### Challenge Results
- Challenger: block (confidence in original: 0.32)
- Key concerns: (1) T1/T3 misclassification, (2) Brief B authority not consulted, (3) selective reading of #1077 deferral, (4) follow-up AC gaps
- Architect response: accepted concerns 1, 2, 3, 4. The Brief B D52 gap is material — it invalidates the core "data loss" argument that underpins the recommendation.

### Action Required for Re-research
1. Read `.owlbear/briefs/draft-kanban-engine-b-2026-04-20/decisions.md` D52 and `paper-integration.md` §outcome matrix
2. Analyze both options (fix release vs restore fail) with trade-off matrix
3. Resolve T1/T3 classification — if T3, create a DR via scribe
4. Populate #1125 and #1126 with concrete AC
5. Address the `release` note-appending implementation gap (is it a separate bug or part of this reconciliation?)
[[2026-04-25]]
## Research (v2 — post-rejection revision)

### Summary
Revised research addressing all 5 architect feedback items. Brief B D52 deliberately dropped `fail`; the original research missed this authority source.

### Key Findings
1. **`fail` ≠ `release` semantically.** Session analytics classify `fail` as `completed-fail` and `release` as `released`. Cockpit UI has distinct filters. Merging them breaks observability.
2. **D52 `release` note gap is a separate bug.** D52 says `release` appends notes; current impl doesn't. This is defect D2, independent of the `fail` question.
3. **Only 2 of 11 layers reject `fail`.** Raw engine, MCP server.py, guidance, pipeline protocol, agent files, skill docs, session analytics, cockpit UI all expect it.

### Recommendation: Option Y — Restore `fail` + fix `release` notes (confidence: 0.72)
Rationale: D52's consolidation overlooked the observability distinction. 9 layers already use `fail`. Lower risk than removing `fail` from everywhere.

### Two-option trade-off matrix
- **Option X (complete D52):** Aligned with brief authority but high risk — requires changes to engine, session classifier, cockpit UI, 5+ test files. KISS: 0.35.
- **Option Y (restore fail + fix release):** Deviates from D52 but aligns with live contract. 2-3 code files changed. KISS: 0.80.

### Tier: T2 (advisory DR created)
D52 deviation doesn't add new capabilities or change architecture — ratifies de facto contract.

### Challenge Results (v2)
- Challenger: `reconsider` (confidence in Option X: 0.36)
- Critical finding: `fail` and `release` carry distinct session/activity/cockpit semantics — not equivalent
- Post-challenge: revised from Option X to Option Y

### Follow-up Tasks
- #1125: Restore `fail` to AgentView + EndWorkParams (already approved, in todo, has AC)
- #1126: Remove dead TypeError fallback chains (already researched, in backlog)
- #1127: Fix `release` note-appending per D52 (new — defect D2, has AC)

### Research doc
`.owlbear/research/reconcile-end-work-outcome-contract-v2.md`

### Attribution
- Sources: 16 studied (Brief B decisions, paper-integration, engine code, MCP code, pipeline protocol, session tests, cockpit tests)
- DR: `.owlbear/decisions/pending/1124-end-work-outcome-authority.md` (T2 advisory, 5-day auto-resolve)
[[2026-04-25]]
## Decision Resolution

**DR:** `.owlbear/decisions/resolved/1124-end-work-outcome-authority.md`
**Decision:** A: Ratify the live 5-outcome contract
**Authority:** User (via scribe)

Approved — restore `fail` to AgentView and EndWorkParams valid_outcomes, overriding Brief B D52 based on system-wide observability evidence. Follow-up tasks #1125, #1126, #1127 approved to proceed.

[[2026-04-26]]
## Research (validation pass)

Validated all v2 research artifacts are current and complete:
- Research doc: `.owlbear/research/reconcile-end-work-outcome-contract-v2.md` — exists, 16 sources
- DR: `.owlbear/decisions/resolved/1124-end-work-outcome-authority.md` — resolved (Option A: ratify live 5-outcome contract)
- Follow-up #1125: in-progress (AC1-AC5, tests written, impl appears done)
- Follow-up #1126: review (AC present, builder done)
- Follow-up #1127: todo (AC present, architecture approved)
- No stale findings — codebase state matches v2 analysis
[[2026-04-26]]
## Architecture Review (v2 research)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Research umbrella for one topic: end-work outcome contract reconciliation |
| Interface clarity | N/A | Research task — no implementation AC. Deliverables documented in body |
| Dependency correctness | PASS | No deps; follow-ups are independent tasks |
| Module layering | N/A | Research only |
| TDD compliance | N/A | Tagged `research` for pass-through |
| KISS/YAGNI | PASS | Focused scope, minimal follow-up set (3 tasks) |
| Premise challenge | PASS | Outcome contract gap confirmed by 9/11 layer analysis; DR resolved |
| Pattern consistency | PASS | Follows research umbrella conventions |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Kanban engine domain |

### Research Quality Assessment
| Deliverable | Status | Evidence |
|---|---|---|
| Research doc v2 | Complete | `.owlbear/research/reconcile-end-work-outcome-contract-v2.md` — 16 sources |
| DR resolved | Complete | `.owlbear/decisions/resolved/1124-end-work-outcome-authority.md` — Option A |
| Two-option trade-off | Complete | Option X (KISS 0.35) vs Option Y (KISS 0.80) with authority/risk/effort analysis |
| Follow-up #1125 | In-progress | AC1-AC5, 13 tests, implementation appears done |
| Follow-up #1126 | Backlog | Returned from review — AC3 needs narrowing (pre-existing suite failures) |
| Follow-up #1127 | Todo | AC1-AC4, architecture approved |

### V1→V2 Rejection Feedback Resolution
All 5 items from previous rejection addressed:
1. ✅ Brief B D52 authority consulted and cited
2. ✅ Two-option analysis with trade-off matrix
3. ✅ T1→T2 reclassification with DR
4. ✅ Follow-ups populated with concrete AC
5. ✅ `release` note gap identified as separate defect (#1127)

### Challenge Results
- Challenger: proceed (confidence: 0.85)
- Key finding: #1126's AC3 issue is a child-task lifecycle concern, not a research gap
- Architect response: accepted — umbrella research is complete regardless of child task status

### Non-implementation tagging
Tagged `research` — task produces no testable Python code; pass-through in pipeline.

### Verdict: APPROVE
### Action Taken: Tagged `research`, advanced to todo.
[[2026-04-26]]
## Test-Writer Notes
- Non-implementation task (tagged `research`) — no tests applicable.
- Passing through to builder.
[[2026-04-26]]
## Builder Notes
- Non-implementation task (tagged `research`) — no code changes needed.
- Passing through to review.
[[2026-04-26]]
## Review Evidence
### Test Results
- N/A. Task `#1124` is tagged `research`, the latest Architecture Review marks TDD as N/A / pass-through, and the review scope is artifact integrity rather than executable implementation.

### Lint
- N/A. No implementation artifact is under review.

### Coverage
- N/A. No touched runtime module is owned by this umbrella research task.

### Pass 1 - CRITICAL
#### Research Deliverable Integrity
| Claim | Evidence | Status |
|---|---|---|
| Research doc v2 is complete and current | The task body marks `Research doc v2` as complete at [.owlbear/kanban/tasks/1124-b-xx-reconcile-mcp-end-work-outcome-contract-with-agentview-validation.md](.owlbear/kanban/tasks/1124-b-xx-reconcile-mcp-end-work-outcome-contract-with-agentview-validation.md#L156) and says `No stale findings` at [.owlbear/kanban/tasks/1124-b-xx-reconcile-mcp-end-work-outcome-contract-with-agentview-validation.md](.owlbear/kanban/tasks/1124-b-xx-reconcile-mcp-end-work-outcome-contract-with-agentview-validation.md#L135), but the follow-up section in [.owlbear/research/reconcile-end-work-outcome-contract-v2.md](.owlbear/research/reconcile-end-work-outcome-contract-v2.md#L112) still lists only `T-A (revised #1125)` and `T-B (existing #1126)` at [.owlbear/research/reconcile-end-work-outcome-contract-v2.md](.owlbear/research/reconcile-end-work-outcome-contract-v2.md#L114) and [.owlbear/research/reconcile-end-work-outcome-contract-v2.md](.owlbear/research/reconcile-end-work-outcome-contract-v2.md#L115). It omits `#1127` entirely. | FAIL |
| D2 (`release` note appending) is captured as a separate defect / follow-up | The task body says `#1127: Fix release note-appending per D52` at [.owlbear/kanban/tasks/1124-b-xx-reconcile-mcp-end-work-outcome-contract-with-agentview-validation.md](.owlbear/kanban/tasks/1124-b-xx-reconcile-mcp-end-work-outcome-contract-with-agentview-validation.md#L109) and later claims previous rejection item 5 was addressed because the `release` note gap is a separate defect `(#1127)` at [.owlbear/kanban/tasks/1124-b-xx-reconcile-mcp-end-work-outcome-contract-with-agentview-validation.md](.owlbear/kanban/tasks/1124-b-xx-reconcile-mcp-end-work-outcome-contract-with-agentview-validation.md#L169). The research doc itself states `D1` and `D2` are separate defects at [.owlbear/research/reconcile-end-work-outcome-contract-v2.md](.owlbear/research/reconcile-end-work-outcome-contract-v2.md#L73) to [.owlbear/research/reconcile-end-work-outcome-contract-v2.md](.owlbear/research/reconcile-end-work-outcome-contract-v2.md#L78), but its follow-up section collapses D2 into revised `#1125` at [.owlbear/research/reconcile-end-work-outcome-contract-v2.md](.owlbear/research/reconcile-end-work-outcome-contract-v2.md#L114). The child tasks prove the actual split: `#1125` scope is fail/model/doc-row work at [.owlbear/kanban/tasks/1125-restore-fail-outcome-to-agentview-end-work-and-align-mcp-model.md](.owlbear/kanban/tasks/1125-restore-fail-outcome-to-agentview-end-work-and-align-mcp-model.md#L36) to [.owlbear/kanban/tasks/1125-restore-fail-outcome-to-agentview-end-work-and-align-mcp-model.md](.owlbear/kanban/tasks/1125-restore-fail-outcome-to-agentview-end-work-and-align-mcp-model.md#L42), while `#1127` separately owns release-note appending at [.owlbear/kanban/tasks/1127-fix-release-outcome-to-append-notes-per-brief-b-d52.md](.owlbear/kanban/tasks/1127-fix-release-outcome-to-append-notes-per-brief-b-d52.md#L22), [.owlbear/kanban/tasks/1127-fix-release-outcome-to-append-notes-per-brief-b-d52.md](.owlbear/kanban/tasks/1127-fix-release-outcome-to-append-notes-per-brief-b-d52.md#L35), and [.owlbear/kanban/tasks/1127-fix-release-outcome-to-append-notes-per-brief-b-d52.md](.owlbear/kanban/tasks/1127-fix-release-outcome-to-append-notes-per-brief-b-d52.md#L36). | FAIL |

#### Deliverable Compliance
| Deliverable | Evidence | Status |
|---|---|---|
| Research doc exists with 16-source analysis | [.owlbear/research/reconcile-end-work-outcome-contract-v2.md](.owlbear/research/reconcile-end-work-outcome-contract-v2.md#L1) to [.owlbear/research/reconcile-end-work-outcome-contract-v2.md](.owlbear/research/reconcile-end-work-outcome-contract-v2.md#L24) | PASS |
| DR is resolved | [.owlbear/decisions/resolved/1124-end-work-outcome-authority.md](.owlbear/decisions/resolved/1124-end-work-outcome-authority.md#L1) to [.owlbear/decisions/resolved/1124-end-work-outcome-authority.md](.owlbear/decisions/resolved/1124-end-work-outcome-authority.md#L7) | PASS |
| Follow-up tasks exist with concrete scopes | [.owlbear/kanban/tasks/1125-restore-fail-outcome-to-agentview-end-work-and-align-mcp-model.md](.owlbear/kanban/tasks/1125-restore-fail-outcome-to-agentview-end-work-and-align-mcp-model.md#L36) to [.owlbear/kanban/tasks/1125-restore-fail-outcome-to-agentview-end-work-and-align-mcp-model.md](.owlbear/kanban/tasks/1125-restore-fail-outcome-to-agentview-end-work-and-align-mcp-model.md#L54), [.owlbear/kanban/tasks/1126-remove-dead-try-except-typeerror-fallback-chain-in-mcp-server-end-work.md](.owlbear/kanban/tasks/1126-remove-dead-try-except-typeerror-fallback-chain-in-mcp-server-end-work.md#L24) to [.owlbear/kanban/tasks/1126-remove-dead-try-except-typeerror-fallback-chain-in-mcp-server-end-work.md](.owlbear/kanban/tasks/1126-remove-dead-try-except-typeerror-fallback-chain-in-mcp-server-end-work.md#L31), and [.owlbear/kanban/tasks/1127-fix-release-outcome-to-append-notes-per-brief-b-d52.md](.owlbear/kanban/tasks/1127-fix-release-outcome-to-append-notes-per-brief-b-d52.md#L26) to [.owlbear/kanban/tasks/1127-fix-release-outcome-to-append-notes-per-brief-b-d52.md](.owlbear/kanban/tasks/1127-fix-release-outcome-to-append-notes-per-brief-b-d52.md#L39) | PASS |
| Research doc accurately reflects the actual follow-up split | See the two FAIL rows above. | FAIL |

### Deductions
- -0.11 The claimed-complete research doc still carries a stale follow-up map that omits `#1127` and misstates D2 ownership.
- -0.04 The validation pass and research-quality matrix overclaim completeness based on that stale document state.

### Verdict
- Confidence: 0.85
- FAIL
- Routing: backlog
- Reason: this is a research-artifact quality issue, not an implementation issue. The parent task cannot pass while its claimed-complete research doc disagrees with both the task body and the actual downstream task split.

### Action
- Researcher/architect should update `.owlbear/research/reconcile-end-work-outcome-contract-v2.md` and the validation/completeness statements in task `#1124` so the umbrella artifact matches the actual three-task split: `#1125` (`fail`/model/doc-row), `#1126` (dead fallback cleanup), `#1127` (release-note defect).

### Post-task Reflection
- The task is legitimately non-implementation, so artifact integrity was the gate rather than test execution.
- The research conclusion may still be sound; the blocking defect is the stale follow-up mapping inside the artifact claimed as complete.
- The fix is surgical because the child tasks already encode the correct split; the parent research artifact just needs to be reconciled to them.