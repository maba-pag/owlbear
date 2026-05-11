---
id: 1456
title: 'P4-20: consolidation test: fixed-topology deployment readiness'
status: backlog
priority: important
created: 2026-05-08T19:32:35.891593+00:00
updated: 2026-05-11T18:11:12.452793+00:00
tags:
- phase-4
- scope:deployment-readiness
- consolidation-test
- verification-probe
- kanban
- deployment-readiness
- quality
parent: 1437
depends_on:
- 1439
- 1441
- 1443
- 1445
- 1447
- 1449
- 1451
- 1453
- 1455
- 1457
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: final scratch-board and contract-inspection verification across completed child implementations.
Out of scope: source changes and full pytest or vitest execution.

## Acceptance Criteria
1. Test-writer records a fresh scratch-board walkthrough that starts with no config.yml and demonstrates fixed topology exposure, task creation, ID allocation from active plus archive filenames, activity event emission, and setup-created board directories.
2. Test-writer records a dispatch walkthrough showing pick_tasks leaves task and decision files unchanged while start_work reclaims one expired claim through the writer path.
3. Test-writer records a DR walkthrough showing create_dr creates a pending request and resolve_drs resolves it once without duplicate task summaries.
4. Test-writer records a maintenance walkthrough showing user-triggered cleanup releases expired claims, moves active archived tasks to archive storage, and reports skipped items.
5. Test-writer records MCP/Cockpit contract inspection for list filter semantics, tool annotations, structured error envelopes, and POST /api/tasks/cleanup response shape.
6. Test-writer records documentation/guidance inspection showing the fixed-topology deployment contract is described and stale config/automatic-side-effect claims are absent.
7. Test-writer adds no pytest, vitest, or full-suite execution as functional proof; verification evidence is limited to scratch-board walkthrough notes and contract inspection artifacts.
[[2026-05-11]]


## Acceptance Criteria (Revised)

> Supersedes original AC above. Reframed as reviewer-verifiable codebase inspection checks. Original AC assigned work to "Test-writer" but `type:test` tag caused pipeline pass-through — nobody would execute the walkthroughs. Revised AC is a quality-gate with `quality` tag: test-writer and builder pass through; reviewer performs the verification by inspecting cited files.

1. `topology.py` exports `PRODUCT_TOPOLOGY` with frozen statuses, priorities, agent_map, archive_reasons, and claim_timeout; engine loads these constants at init. Inspect: `serve/kanban/src/owlbear_kanban/topology.py`. (td:0)
2. Engine `pick_tasks` (in `agent_view.py`) performs no file writes; MCP `pick_tasks` is annotated `readOnlyHint=True`. `start_work` is the sole writer that reclaims expired claims via the compare-and-swap path. Inspect: `serve/kanban/src/owlbear_kanban/agent_view.py`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`. (td:0)
3. MCP server registers `resolve_drs` as a separate tool; `pick_tasks` does not call resolve logic. `create_dr` creates pending decision/action requests. Inspect: `server.py` tool registrations. (td:0)
4. Engine `cleanup()` releases expired claims, moves archived-status active tasks to archive storage, returns `CleanupResult(released_claim_ids, archived_task_ids, skipped_items)`. Cockpit exposes via `POST /api/tasks/cleanup`. Inspect: `engine.py`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`. (td:0)
5. MCP `list_tasks` supports `status`, `tag`, `search`, `blocked`, `archived`, `unclaimed` filters; tool annotations present on all tools; errors use structured `ToolError` responses. Inspect: `server.py` tool definitions. (td:0)
6. Agent guidance (`h-mcp-kanban`, `w-orchestration`, `h-decision-requests`, `pipeline-agents.instructions.md`) describes `pick_tasks` as read-only, `start_work` as claim-writer, `resolve_drs` as DR resolver, `create_dr` as DR creator. No stale references to automatic sweep/DR-resolution in `pick_tasks`. Inspect: named skill/instruction files via grep. (td:0)
7. `setup/init.py` creates board directories (tasks/, archive/, decisions/pending/, decisions/resolved/) without writing board topology to `config.yml`. Engine allocates IDs by scanning active + archive filename prefixes under a lock. Inspect: `setup/init.py`, `serve/kanban/src/owlbear_kanban/storage.py`. (td:0)

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: consolidation quality gate across P4 deployment readiness |
| Interface clarity | PASS (revised) | Original FAIL: "Test-writer records" contradicted `type:test` pass-through. Revised AC specifies reviewer-verifiable codebase inspection points with file paths |
| Dependency correctness | PASS | All 10 deps (1439–1457) are archived |
| Module layering | N/A | No source changes |
| TDD compliance | PASS | Tagged `quality` — test-writer pass-through; all AC td:0; no testable Python interfaces. Test-writer: SKIP |
| KISS/YAGNI | PASS | Minimal scope — verification only |
| Premise challenge | PASS | Individual task reviews verified components in isolation; this consolidation gate adds cross-cutting integration verification value for a major deployment milestone |
| Pattern consistency | PASS | Follows `quality` pass-through pattern; reviewer-verifiable AC |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | scope:deployment-readiness; verification only |

### AC Refinement Summary
- Removed `type:test` tag (caused unintended pipeline pass-through at both test-writer AND builder stages)
- Added `quality` tag (correct pass-through: test-writer and builder skip; reviewer performs verification)
- Rewrote 7 AC lines from "Test-writer records walkthrough" to reviewer-verifiable codebase inspection checks with specific file paths
- Eliminated AC7's explicit pytest/vitest prohibition (implicit with td:0 and quality tag — no tests to write or run)
- All AC lines td:0 → Test-writer: SKIP

### Challenger
Skipped — all AC lines td:0 per Step 2.1.

### Design Diverge
Skipped — single straightforward approach (quality gate with codebase inspection).
[[2026-05-11]]
Architecture review complete. REFINE + APPROVE: fixed pipeline-breaking AC (original assigned work to "Test-writer" but `type:test` tag caused pass-through at both test-writer AND builder stages — nobody would execute the walkthroughs). Replaced `type:test` with `quality` tag. Rewrote 7 AC lines from walkthrough-recording tasks into reviewer-verifiable codebase inspection checks with specific file paths. All td:0 → Test-writer: SKIP.
[[2026-05-11]]
## Test-Writer Notes
- Non-implementation task (tagged `quality`) — no tests applicable.
- All 7 AC lines are td:0 (reviewer-verifiable codebase inspection only; no testable Python interfaces).
- Passing through to builder.
[[2026-05-11]]
## Builder Notes
- Non-implementation task (tagged `quality`) — no code changes needed.
- AC lines are reviewer-verifiable inspection checks (td:0), so builder GREEN implementation/testing does not apply.
- Passing through to review.
[[2026-05-11]]
## Review Evidence
### Test Results
- quality-runner (td:0 scoped): Tests N/A
- Lint: clean (`ruff: 0`, `markdownlint: 0`)
- Coverage: N/A
- Errors: none
- Changed files: none; builder and test-writer both passed through this `quality` gate, so dirty-tree contamination and builder diff scoping are not applicable.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- Skipped: td:0 quality task; no `TestFromAC_*` classes and no task-scoped test surface.

#### Security Review
- No security issues found in the inspected topology, claim, cleanup, storage, MCP, and Cockpit contract paths.

#### Test Integrity
- Skipped: no `TestFromAC_*` classes; builder made no task-scoped code/test changes.

#### Test Quality
- Skipped: td:0 inspection task.

#### Data Safety
- No issues found in the inspected claim, cleanup, and DR code paths.

#### Implementation-Aware Gaps
- FAIL: AC5 says MCP `list_tasks` supports an `archived` filter, but the live server signature exposes `status`, `tag`, `priority`, `archival_reason`, `ids`, `parent`, `search`, `sort`, `unclaimed`, `limit`, `reverse`, and `blocked` only. The implementation falls back to `resolved_status = "archived"` when `archival_reason` is present, which is not a separate `archived` filter. Evidence: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:226`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:234`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:237`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:262`.
- FAIL: AC6 says the named guidance files describe `resolve_drs` as the DR resolver, but `h-mcp-kanban` still documents exactly 9 tools and omits `resolve_drs`, while `h-decision-requests` explicitly says agents do not resolve DR/AR files and that resolution happens through the Cockpit decision flow. Evidence: `share/skills/h-mcp-kanban/SKILL.md:17`, `share/skills/h-mcp-kanban/SKILL.md:22`, `share/skills/h-mcp-kanban/SKILL.md:28`, `share/skills/h-mcp-kanban/SKILL.md:30`, `share/skills/h-decision-requests/SKILL.md:13`. Additional grep on the named guidance files found no `resolve_drs` entry.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 1 |
| Approach variation | N/A (pass-through) |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- AC1 verified: `PRODUCT_TOPOLOGY` is a frozen dataclass export and the engine loads topology-derived config at init. Evidence: `serve/kanban/src/owlbear_kanban/topology.py:9`, `serve/kanban/src/owlbear_kanban/topology.py:32`, `serve/kanban/src/owlbear_kanban/topology.py:52`, `serve/kanban/src/owlbear_kanban/topology.py:54`, `serve/kanban/src/owlbear_kanban/topology.py:76`, `serve/kanban/src/owlbear_kanban/config_loader.py:19`, `serve/kanban/src/owlbear_kanban/config_loader.py:52`, `serve/kanban/src/owlbear_kanban/config_loader.py:66`, `serve/kanban/src/owlbear_kanban/config_loader.py:70`, `serve/kanban/src/owlbear_kanban/config_loader.py:76`, `serve/kanban/src/owlbear_kanban/engine.py:367`, `serve/kanban/src/owlbear_kanban/engine.py:374`.
- AC2 verified apart from the failing contract wording above: `pick_tasks` reads via `engine.list_tasks()` and `engine.show_task()` only, MCP `pick_tasks` is annotated `readOnlyHint=True`, and `start_work` delegates to the CAS reclaim path in `claim_task()`. Evidence: `serve/kanban/src/owlbear_kanban/agent_view.py:298`, `serve/kanban/src/owlbear_kanban/agent_view.py:379`, `serve/kanban/src/owlbear_kanban/agent_view.py:399`, `serve/kanban/src/owlbear_kanban/agent_view.py:925`, `serve/kanban/src/owlbear_kanban/engine.py:1400`, `serve/kanban/src/owlbear_kanban/engine.py:1416`, `serve/kanban/src/owlbear_kanban/engine.py:1432`, `serve/kanban/src/owlbear_kanban/engine.py:1436`, `serve/kanban/src/owlbear_kanban/engine.py:1552`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:520`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:605`.
- AC3 verified on the server/decisions implementation: `create_dr` and `resolve_drs` are separate MCP tools, and DR creation writes into `decisions/pending/`. Evidence: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:365`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:396`, `serve/kanban/src/owlbear_kanban/decisions.py:89`, `serve/kanban/src/owlbear_kanban/decisions.py:103`, `serve/kanban/src/owlbear_kanban/decisions.py:143`, `serve/kanban/src/owlbear_kanban/decisions.py:176`, `serve/kanban/src/owlbear_kanban/decisions.py:177`.
- AC4 verified: `cleanup()` returns `CleanupResult(released_claim_ids, archived_task_ids, skipped_items)` and Cockpit exposes it at `POST /api/tasks/cleanup`. Evidence: `serve/kanban/src/owlbear_kanban/models.py:571`, `serve/kanban/src/owlbear_kanban/models.py:574`, `serve/kanban/src/owlbear_kanban/models.py:575`, `serve/kanban/src/owlbear_kanban/models.py:576`, `serve/kanban/src/owlbear_kanban/engine.py:1809`, `serve/kanban/src/owlbear_kanban/engine.py:1817`, `serve/kanban/src/owlbear_kanban/engine.py:1818`, `serve/kanban/src/owlbear_kanban/engine.py:1819`, `serve/kanban/src/owlbear_kanban/engine.py:1874`, `serve/kanban/src/owlbear_kanban/engine.py:1935`, `serve/kanban/src/owlbear_kanban/engine.py:1941`, `serve/kanban/src/owlbear_kanban/engine.py:1942`, `serve/kanban/src/owlbear_kanban/engine.py:1943`, `serve/cockpit/src/owlbear_cockpit/main.py:39`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:329`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:330`.
- AC5 partially verified: tool annotations are present on all 10 MCP tools and errors are normalized through structured `ToolError` JSON payloads. Evidence: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:110`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:116`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:118`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:222`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:322`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:338`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:364`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:395`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:415`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:456`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:519`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:543`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:604`.
- AC7 verified: `setup/init.py` creates `tasks/`, `archive/`, `decisions/pending/`, and `decisions/resolved/`, and `allocate_next_id()` scans both active and archive files under the lock. Evidence: `setup/init.py:374`, `setup/init.py:376`, `setup/init.py:377`, `setup/init.py:378`, `setup/init.py:379`, `serve/kanban/src/owlbear_kanban/storage.py:540`, `serve/kanban/src/owlbear_kanban/storage.py:558`.
- Documentation drift is the root cause of this review failure: `h-mcp-kanban` documents 9 tools while the server registers 10 (including `resolve_drs`). Evidence: `share/skills/h-mcp-kanban/SKILL.md:17`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:222`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:322`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:338`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:364`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:395`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:415`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:456`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:519`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:543`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:604`.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| 1 | `topology.py` frozen export + config loader + engine init. Evidence: `serve/kanban/src/owlbear_kanban/topology.py:9`, `serve/kanban/src/owlbear_kanban/topology.py:32`, `serve/kanban/src/owlbear_kanban/topology.py:52`, `serve/kanban/src/owlbear_kanban/topology.py:54`, `serve/kanban/src/owlbear_kanban/topology.py:76`, `serve/kanban/src/owlbear_kanban/config_loader.py:19`, `serve/kanban/src/owlbear_kanban/config_loader.py:52`, `serve/kanban/src/owlbear_kanban/config_loader.py:66`, `serve/kanban/src/owlbear_kanban/config_loader.py:70`, `serve/kanban/src/owlbear_kanban/config_loader.py:76`, `serve/kanban/src/owlbear_kanban/engine.py:367`, `serve/kanban/src/owlbear_kanban/engine.py:374` | N/A | PASS |
| 2 | `pick_tasks` reads only; `start_work` reclaims expired claims through CAS path. Evidence: `serve/kanban/src/owlbear_kanban/agent_view.py:298`, `serve/kanban/src/owlbear_kanban/agent_view.py:379`, `serve/kanban/src/owlbear_kanban/agent_view.py:399`, `serve/kanban/src/owlbear_kanban/agent_view.py:925`, `serve/kanban/src/owlbear_kanban/engine.py:1400`, `serve/kanban/src/owlbear_kanban/engine.py:1416`, `serve/kanban/src/owlbear_kanban/engine.py:1432`, `serve/kanban/src/owlbear_kanban/engine.py:1436`, `serve/kanban/src/owlbear_kanban/engine.py:1552`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:520`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:605` | N/A | PASS |
| 3 | `create_dr` and `resolve_drs` registered separately; pending DR creation verified. Evidence: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:365`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:396`, `serve/kanban/src/owlbear_kanban/decisions.py:89`, `serve/kanban/src/owlbear_kanban/decisions.py:103`, `serve/kanban/src/owlbear_kanban/decisions.py:143`, `serve/kanban/src/owlbear_kanban/decisions.py:176`, `serve/kanban/src/owlbear_kanban/decisions.py:177` | N/A | PASS |
| 4 | `cleanup()` + Cockpit route verified. Evidence: `serve/kanban/src/owlbear_kanban/models.py:571`, `serve/kanban/src/owlbear_kanban/models.py:574`, `serve/kanban/src/owlbear_kanban/models.py:575`, `serve/kanban/src/owlbear_kanban/models.py:576`, `serve/kanban/src/owlbear_kanban/engine.py:1809`, `serve/kanban/src/owlbear_kanban/engine.py:1817`, `serve/kanban/src/owlbear_kanban/engine.py:1818`, `serve/kanban/src/owlbear_kanban/engine.py:1819`, `serve/kanban/src/owlbear_kanban/engine.py:1874`, `serve/kanban/src/owlbear_kanban/engine.py:1935`, `serve/kanban/src/owlbear_kanban/engine.py:1941`, `serve/kanban/src/owlbear_kanban/engine.py:1942`, `serve/kanban/src/owlbear_kanban/engine.py:1943`, `serve/cockpit/src/owlbear_cockpit/main.py:39`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:329`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:330` | N/A | PASS |
| 5 | Tool annotations and structured `ToolError` pass, but the named `archived` filter does not exist in the live `list_tasks` signature. Evidence: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:110`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:116`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:118`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:222`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:226`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:234`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:237`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:262`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:322`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:338`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:364`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:395`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:415`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:456`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:519`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:543`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:604` | N/A | FAIL |
| 6 | `pick_tasks` read-only and `create_dr` creator are documented, but `resolve_drs` is not documented in the named guidance set and `h-decision-requests` routes resolution through Cockpit instead. Evidence: `share/skills/h-mcp-kanban/SKILL.md:17`, `share/skills/h-mcp-kanban/SKILL.md:22`, `share/skills/h-mcp-kanban/SKILL.md:28`, `share/skills/h-mcp-kanban/SKILL.md:30`, `share/skills/h-decision-requests/SKILL.md:13`, `share/skills/h-decision-requests/SKILL.md:32`, `share/skills/h-decision-requests/SKILL.md:84`, `share/skills/w-orchestration/SKILL.md:25`, `share/skills/w-orchestration/SKILL.md:56`, `share/skills/w-orchestration/SKILL.md:125`, `share/instructions/pipeline-agents.instructions.md:31`, `share/instructions/pipeline-agents.instructions.md:32` | N/A | FAIL |
| 7 | Setup/storage contract verified. Evidence: `setup/init.py:374`, `setup/init.py:376`, `setup/init.py:377`, `setup/init.py:378`, `setup/init.py:379`, `serve/kanban/src/owlbear_kanban/storage.py:540`, `serve/kanban/src/owlbear_kanban/storage.py:558` | N/A | PASS |

### Deductions
- `-0.18`: AC5 overstates the live MCP `list_tasks` filter contract.
- `-0.16`: AC6 overstates the current guidance / DR-resolution contract.
- `-0.02`: no builder commit hash or diff surface exists because this was an explicit pass-through verification gate.

### Confidence: 0.64
### Verdict: FAIL
### Action: reject to `backlog` because the gate itself overclaims current repo contracts; this is an architect/AC reconciliation issue, not a builder retry.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | architect | Reconcile AC5 with the actual MCP contract: either narrow the gate to `status="archived"` / `archival_reason` semantics or create a follow-up implementation task for a real `archived` boolean filter | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`; `share/skills/h-mcp-kanban/SKILL.md` | `server.py:226`, `server.py:234`, `server.py:237`, `server.py:262`; `h-mcp-kanban/SKILL.md:17`, `h-mcp-kanban/SKILL.md:22` |
| 2 | architect | Reconcile AC6 with live guidance: either update the named docs to describe `resolve_drs` or narrow the gate to the current Cockpit-based DR resolution contract | `share/skills/h-mcp-kanban/SKILL.md`; `share/skills/h-decision-requests/SKILL.md`; `share/skills/w-orchestration/SKILL.md`; `share/instructions/pipeline-agents.instructions.md` | `h-mcp-kanban/SKILL.md:17`, `h-mcp-kanban/SKILL.md:22`, `h-decision-requests/SKILL.md:13`; grep found no `resolve_drs` entry across the named guidance files |