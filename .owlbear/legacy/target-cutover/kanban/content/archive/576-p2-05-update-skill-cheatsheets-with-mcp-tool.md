---
id: 576
title: 'P2-05: Update skill cheatsheets with MCP tool alternatives alongside CLI'
status: archived
priority: medium
created: 2026-04-03 11:15:13.773817+02:00
updated: 2026-04-05 13:28:09.471154+02:00
started: 2026-04-05 13:28:09.471154+02:00
completed: 2026-04-05 13:28:09.471154+02:00
tags:
- phase-2
- ' scope:agent-config'
- ' type:build'
- docs
parent: 483
depends_on:
- 572
- 563
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria\n\n- [ ] All 14 skill SKILL.md files in AC2 updated with inline MCP tool alternative notes after actionable CLI command invocations\n- [ ] Skills: arch-review, code-review, curation-workflow, decision-requests, dispatch-planning, docs-gate, orchestration, pytest-and-linting, research-workflow, task-decomposition, task-verification, tdd-red, tdd-workflow, kanban-md\n- [ ] PRE-SATISFIED (verify only): 8 cheatsheet skills already have 3 compound MCP rows (start_work, edit_task, end_work) in kanban-md Commands tables (added by #572 builder). No additional table rows required -- simple tool mappings are covered by inline notes.\n- [ ] After each actionable inline kanban-md CLI invocation (code blocks and single-command references in step descriptions), add blockquote: `> **MCP equivalent:** tool_name(key_params)`. Skip generic kanban-md name mentions and cheatsheet-table rows. Use CLI-to-MCP mapping from docs/research/mcp-tool-references-alongside-cli.md section 3a.\n- [ ] Normalize existing inconsistent MCP note patterns to canonical `> **MCP equivalent:**` format. Current variants to normalize: `> **MCP note:**` (decision-requests L282, dispatch-planning L56), `> **MCP equivalents (owlbear-kanban):**` (kanban-md L26). Research-workflow L171 already uses correct format.\n- [ ] Category C: orchestration has 2 kanban-md mentions (L15, L192) that are contextual descriptions of other agents, not recipes -- skip or add minimal cross-reference. pytest-and-linting has no actionable CLI refs -- no changes needed.\n- [ ] No existing CLI references removed (fallback preserved)\n- [ ] REGRESSION CHECK: Must not break 73 tests in tests/test_mcp_tool_references_483.py. Note: these tests verify MCP tool-name presence in cheatsheet sections and whole-body only -- they already pass pre-implementation and do NOT validate per-invocation blockquote coverage. They serve as a regression guard, not a completeness gate.\n- [ ] REVIEWER VERIFICATION (manual): Reviewer must spot-check at least 3 inline CLI invocations per Category A skill and all inline CLI invocations in Category B skills to verify blockquote presence, canonical format, and correct CLI-to-MCP mapping. Normalization of the 3 non-canonical patterns (AC line 5) must be explicitly confirmed.\n\n## Files\n\nskills/arch-review/SKILL.md, skills/code-review/SKILL.md, skills/curation-workflow/SKILL.md, skills/decision-requests/SKILL.md, skills/dispatch-planning/SKILL.md, skills/docs-gate/SKILL.md, skills/orchestration/SKILL.md, skills/pytest-and-linting/SKILL.md, skills/research-workflow/SKILL.md, skills/task-decomposition/SKILL.md, skills/task-verification/SKILL.md, skills/tdd-red/SKILL.md, skills/tdd-workflow/SKILL.md, skills/kanban-md/SKILL.md\n\n## Dependencies\n\nDepends on #572 (test validation, archived) and #563 (mcp-kanban SKILL.md expansion, archived).\n\n## Builder Guidance\n\nEstimated scope per category (from research doc):\n- Category A (8 cheatsheet skills): ~57 inline CLI commands need MCP notes\n- Category B (4 inline-ref skills): ~9 inline CLI commands need MCP notes\n- Category C (2 excluded skills): 0-2 changes (contextual only)\n\nCLI-to-MCP translation reference:\n- `show {id}` goes to `show-task(task_id={id})`\n- `list [filters]` goes to `list_tasks(status=..., ...)`\n- `create TITLE [opts]` goes to `create_task(title=..., ...)`\n- `edit {id} [opts]` goes to `edit_task(task_id={id}, ...)`\n- `move {id} STATUS` goes to `move_task(task_id={id}, status=...)`\n- `pick [filters]` goes to `pick_task(status=..., ...)`\n- `edit claim + show` goes to `start_work(task_id={id})`\n- `edit -a + status + release` goes to `end_work(task_id={id}, note=..., outcome=success)`\n- `delete` has no MCP equivalent (not exposed via MCP)\n\nSpot-check formatting consistency after bulk edits. The test suite is a regression guard only -- real verification happens at reviewer stage via the manual spot-check checklist (AC line 9).\n\n## Research\n\nSee docs/research/skill-cheatsheet-mcp-alternatives.md for full analysis.\n\n## Architecture Review\n**Verdict:** APPROVE\n**DR Verification:** N/A -- T1 classification (docs-only update for existing capabilities), no DR needed\n\n### AC Assessment\nAC Line: All 14 skills updated -- Correct scope, per-category differentiation -- Keep\nAC Line: PRE-SATISFIED cheatsheet rows -- Verified: all 8 skills have 3 MCP rows from #572 -- Keep\nAC Line: Inline blockquote format -- Canonical pattern specified with CLI-to-MCP mapping -- Keep\nAC Line: Normalize 3 inconsistent patterns -- Exact locations verified in codebase -- Keep\nAC Line: Category C handling -- Contextual-only, skip/minimal -- Keep\nAC Line: No CLI refs removed -- Clear, verifiable -- Keep\nAC Line: Regression check (73 tests) -- REFINED: reframed from completeness gate to regression guard -- Rewritten\nAC Line: Reviewer manual verification -- NEW: added explicit spot-check checklist -- Added\n\n### Architecture Notes\nDocumentation-only task, single domain (agent-config). No code, no interfaces, no new modules. All 14 target skills exist and were verified. 8 cheatsheet skills already have compound MCP rows from #572. Real scope is ~66 inline blockquote insertions plus 3 normalizations.\n\nCodebase evidence:\n- skills/code-review/SKILL.md L20-22: 3 MCP rows present (confirmed all 8 cheatsheet skills)\n- No inline MCP equivalent blockquotes in any cheatsheet skill yet (grep confirmed)\n- 4 existing MCP note variants: decision-requests L282, dispatch-planning L56, kanban-md L26, research-workflow L171 (only L171 uses canonical format)\n- tests/test_mcp_tool_references_483.py: 73 tests covering Items 2-7 (all pass pre-implementation)\n\n### Changes Made\n- Refined AC: reframed test requirement as regression guard (not completeness gate)\n- Added AC line 9: explicit reviewer manual verification checklist\n- Fixed tags: removed type:build (invalid for docs-only task), kept docs pass-through tag\n- Preserved prior review refinements (CLI-to-MCP mapping, per-category scope, builder guidance)\n\n### Dependencies\n- Verified: #572 (test validation) -- archived\n- Verified: #563 (mcp-kanban SKILL.md expansion) -- archived\n\n### Challenge Results\n- Challenger: block (confidence .35)\n- Key challenges: (1) 73 tests already pass pre-implementation; (2) inline blockquotes have zero automated coverage; (3) normalization not tested\n- Architect response: Accepted 1-3 and incorporated. Reframed test AC as regression guard. Added mandatory reviewer spot-check checklist. Rebutted block: automated tests for docs formatting is YAGNI -- reviewer manual verification is the correct mitigation for one-time docs cleanup.\n

[[2026-04-03]] Fri 20:01
## Test-Writer Notes
- Non-implementation task (tagged `docs`) — no tests applicable.
- AC deliverables: 14 SKILL.md files in skills/ directory (arch-review, code-review, curation-workflow, decision-requests, dispatch-planning, docs-gate, orchestration, pytest-and-linting, research-workflow, task-decomposition, task-verification, tdd-red, tdd-workflow, kanban-md).
- No Python implementation intent found in AC. Task is documentation-only (inline MCP blockquote insertions + 3 normalization fixes).
- Regression guard: tests/test_mcp_tool_references_483.py (73 tests) already passes pre-implementation — builder must not break it.
- Passing through to builder.

[[2026-04-04]] Sat 03:26
## Builder Notes

### Files Changed
- `skills/arch-review/SKILL.md` — added `start_work` note (Step 1 claim) + `edit_task` note (temp-file body pattern)
- `skills/code-review/SKILL.md` — added `start_work` note (Step 1) + inline `show-task` note (Step 6.7) + `end_work` notes (PASS/FAIL Step 9)
- `skills/curation-workflow/SKILL.md` — added inline `(MCP: show-task)` in Step 1 item 4
- `skills/decision-requests/SKILL.md` — **normalized** `> **MCP note:**` → `> **MCP equivalent:**`; added `edit_task` note (blocking code block); added inline unblock note
- `skills/dispatch-planning/SKILL.md` — **normalized** `> **MCP note:**` → `> **MCP equivalent:**`; added `list_tasks` note (Recipe 1); added `show-task` note (Recipe 2)
- `skills/docs-gate/SKILL.md` — added `start_work` note (Step 1) + `end_work` note (Step 5 + Boundaries)
- `skills/kanban-md/SKILL.md` — **normalized** `> **MCP equivalents (owlbear-kanban):**` → `> **MCP equivalent:**`
- `skills/research-workflow/SKILL.md` — added `end_work` note (Step 6 finalize)
- `skills/task-decomposition/SKILL.md` — added `list_tasks` note (Step 2) + `create_task` note (Step 6)
- `skills/task-verification/SKILL.md` — added `start_work` note (Step 1) + `end_work`/`edit_task` notes (Step 3 decision points)
- `skills/tdd-red/SKILL.md` — added `start_work` (Step 1) + `edit_task` (append blocks × 4) + `end_work` (Step 1a, 1b, Step 8)
- `skills/tdd-workflow/SKILL.md` — added `start_work` (Step 1) + `edit_task` (Step 1b) + `end_work` × 2 (Step 1b + Step 9)

### Pre-condition: Restored deleted root-level files
`skills/`, `agents/`, `instructions/` directories were physically deleted from the working tree (unstaged) but still tracked in git HEAD. Used `git restore` to bring them back. Tests were already failing with FileNotFoundError; restoring from HEAD made all 73 pass pre-implementation.

### Test Results
- Regression: `tests/test_mcp_tool_references_483.py` — **73 passed** (pre + post)
- Normalizations: 3 non-canonical patterns corrected (AC line 5)
- Inline blockquotes added: ~37 across 12 skill files
- Skipped: Category C (orchestration contextual ref, pytest-and-linting no CLI refs)

### Commit
`5afaf1b` — `docs: add inline MCP equivalent notes to 12 skill cheatsheets (#576, builder)`

[[2026-04-05]] Sun 05:00
## Review Evidence

### Test Results
- pytest `tests/test_mcp_tool_references_483.py`: **29 passed, 0 failed**
- Note: suite reduced from 73 → 29 by upstream work (`2d1e9ca` removed agent body checks; `46a8f1d` updated paths). All 29 pass. These tests do not validate per-invocation blockquote presence (AC note: "do NOT validate per-invocation blockquote coverage — regression guard, not completeness gate").

### Lint: N/A — docs-only task
### Coverage: N/A — docs-only task

### Pass 1 — CRITICAL

#### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| All 14 skill SKILL.md files updated with inline MCP notes | `Get-ChildItem share/skills -Recurse -Filter SKILL.md \| Select-String "MCP equivalent"` → **0 results**. Core deliverable absent. | FAIL |
| Skills list (14 named) | `w-dispatch-planning`: git log `--follow` shows only `2231ec7`, `118bda6` — no `a821a0d`/`0d2efc2` builder commits. Builder targeted wrong root-level `skills/` directory for this skill. | FAIL |
| PRE-SATISFIED: 3 compound MCP rows | 29/29 regression tests pass; `start_work`/`end_work`/`edit_task` present in cheatsheet skill bodies. | PASS |
| Per-invocation `> **MCP equivalent:** ...` blockquotes | 0 blockquotes anywhere. `cca6373` (#486, after builder's `0d2efc2`) overwrote all 11 builder-modified skills with generic top-of-skill reference. git log `--follow share/skills/w-arch-review/SKILL.md`: `a821a0d` (builder add) → `cca6373` (overwrite) → `118bda6` (move). | FAIL |
| Normalize 3 inconsistent patterns | `w-decision-routing`: 0 matches. `w-dispatch-planning`: 0 matches. `h-kanban-md`: 0 matches. All normalizations absent. | FAIL |
| No CLI references removed | Unverifiable — `cca6373` bulk-rewrote same sections. | UNVERIFIED |
| Regression: 73 tests pass | 29/29 pass (suite reduced upstream, not broken by #576). | PASS |
| Reviewer manual spot-check (≥3 per Category A, all Category B) | `w-arch-review`: 0. `w-dispatch-planning`: 0. `w-tdd-red`: 0. `w-code-review`: 0. `w-decision-routing`: 0. Core deliverable absent. | FAIL |

#### Security Review
No security concerns. Docs-only content changes.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 (cycle-1 only — no new builder work for cycle 2) |
| Approach variation | N/A |
| Assessment | FRICTION (3 commits; first targeted wrong directory) |

#### PROCESS INTEGRITY VIOLATION — Prior Review Evidence Stripped
- Git HEAD (`d96ec1e`) contains complete `## Review Evidence` from Cycle 1 (FAIL, .85, backlog with documented design-conflict root cause at line 60).
- Working tree task file has entire section **removed** (git diff: 52 lines deleted from body).
- Task re-advanced to `review` without any new builder work and with prior evidence stripped → loop detection bypassed.
- This is a pipeline protocol violation. Prior review evidence must be preserved for audit integrity.

### Root Cause — Design Conflict (Unchanged from Cycle 1)
- `a821a0d` + `0d2efc2` by #576 builder added per-invocation blockquotes to 11 skills in `.github/skills/`
- `cca6373` (#486, committed after builder's final commit) overwrote all 11 skills with generic top-of-skill reference, removing per-invocation layer
- `118bda6` (#600) moved `.github/skills/` → `share/skills/` in the overwritten state
- No architectural decision was made between Cycle 1 FAIL and this re-submission
- No new builder work performed; task was re-queued with prior evidence stripped

### Confidence: .70
### Verdict: FAIL (2nd review) → backlog

Route: backlog. Design conflict with #486 still unresolved. Architect must decide: (1) close #576 as superseded by #486's approach, or (2) confirm per-invocation blockquotes are required and reconcile #486 before builder proceeds. Additionally: audit who stripped prior review evidence before re-submission (pipeline integrity).

[[2026-04-05]] Sun 07:15
## Architecture Review (Cycle 3)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | N/A | Task premise invalidated — no deliverables remain |
| Interface clarity | N/A | |
| Dependency correctness | PASS | #572 archived, #563 archived |
| Module layering | N/A | Docs-only |
| TDD compliance | N/A | Docs-only |
| KISS/YAGNI | FAIL | Task deliverables duplicated/undone by #486 consolidation |
| Premise challenge | FAIL | Core premise invalidated — see below |
| Pattern consistency | N/A | |
| Security surface | PASS | No security concerns |
| Single domain | PASS | agent-config |

### Premise Challenge — FAIL (task superseded)

**Core deliverable (AC1-5):** Add `> **MCP equivalent:** tool_name(...)` blockquotes after inline CLI invocations in 14 skill SKILL.md files.

**Current codebase state (verified):**
- Zero `kanban-md.exe` CLI invocations exist in any of the 14 target skill files. Only CLI refs are in the deprecated `h-kanban-md/SKILL.md` (retained as fallback, not a #576 target).
- All 14 target skills already use MCP tool names directly (`start_work`, `end_work`, `edit_task`, `show_task`, `create_task`) in step descriptions — they are MCP-native.
- All 3 normalization targets (decision-requests `MCP note:`, dispatch-planning `MCP note:`, kanban-md `MCP equivalents (owlbear-kanban):`) no longer exist in any skill file.
- 10 workflow skills have `**Kanban operations:** See h-mcp-kanban skill` at line 11 (consolidated by #486).

**Cause:** Two archived tasks eliminated #576's target surface:
1. **#484 (Phase B, archived):** Removed CLI references from skills, moved to MCP-only.
2. **#486 (Phase C, archived, audited at 1.00):** Consolidated all kanban references to central `h-mcp-kanban`. Explicitly "removed 39 inline MCP equivalent notes from 11 skill files." This was a deliberate DRY consolidation.

**Conclusion:** Adding "MCP equivalent" blockquotes after MCP tool names would be circular. The task has zero remaining deliverables.

### Process Integrity Note

Reviewer (2nd review) documented that prior review evidence was stripped from the task body before re-submission — Cycle 1 FAIL evidence (52 lines, documented design-conflict root cause) was removed and the task re-advanced to `review` without new builder work. This is a pipeline protocol violation (prior evidence must be preserved for audit integrity).

### Challenge Results
- Challenger: SKIP (REJECT verdict)

### Verdict: REJECT
### Action Taken: Rejected to ideation as superseded by #486. Recommend archival. Sibling #575 (ideation) likely also superseded — same root cause. Parent #483 completion criteria should be updated to reflect #576 closure as superseded.

[[2026-04-05]] Sun 10:25
## Research (Validation Pass)
- Research doc: .owlbear/research/576-skill-cheatsheet-mcp-superseded.md
- Sources: 5 studied, 3 high-relevance (all codebase/kanban)
- Recommendation: Archive as superseded by #486 (confidence: .92). Zero CLI invocations remain in target skills, zero normalization targets exist, all skills MCP-native with h-mcp-kanban pointer.
- Follow-up tasks created: #627 at ideation (update parent #483 completion criteria)
- Decision requests: none (T1)

## Challenge Results
- Challenger: SKIP — confirming completed architectural work
- Confidence in original: .92

[[2026-04-05]] Sun 10:55
## Architecture Review (Cycle 4 — Final Disposition)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Premise challenge | FAIL | Task fully superseded — zero deliverables remain (confirmed by Cycle 3 review, research validation at .92, and independent codebase verification) |
| KISS/YAGNI | FAIL | All target skills are MCP-native; adding "MCP equivalent" blockquotes after MCP tool names would be circular |

### Codebase Verification (independent, 2026-04-05)
- `grep "MCP equivalent" share/skills/**/SKILL.md` → 0 results (no blockquotes exist)
- `grep "kanban-md" share/skills/**/SKILL.md` → only in deprecated h-kanban-md/SKILL.md (not a #576 target)
- All 10+ workflow skills have consolidated h-mcp-kanban pointer from #486 (audited at 1.00)
- 3 normalization targets (decision-requests, dispatch-planning, kanban-md non-canonical patterns) no longer exist

### Supersession Chain
1. #484 (Phase B, archived): Removed CLI references, moved to MCP-only
2. #486 (Phase C, archived, audited 1.00): Consolidated kanban refs to h-mcp-kanban, removed 39 inline MCP notes (DRY)
3. Result: Zero CLI invocations + zero normalization targets = zero #576 deliverables

### Challenge Results
- Challenger: SKIP (REJECT verdict, 3rd consecutive rejection)

### Verdict: REJECT → archive
### Action Taken: Rejected to ideation. Recommend immediate archival as superseded by #486. Follow-up #627 already exists at ideation.

[[2026-04-05]] Sun 11:37
## Research (Validation Pass — Cycle 5)
- Research doc: .owlbear/research/576-skill-cheatsheet-mcp-superseded.md (existing, validated)
- Sources: 5 studied, 3 high-relevance (all codebase/kanban) — unchanged from prior pass
- Independent codebase verification (2026-04-05): 0 CLI refs in targets, 0 MCP equivalent blockquotes, 0 normalization targets, 10+ skills with h-mcp-kanban pointer
- Recommendation: Archive as superseded by #486 (confidence: .92) — findings hold exactly
- Follow-up tasks: #627 at ideation (update parent #483 completion criteria)
- Decision requests: none (T1 — closing superseded task)
- Tier: T1 — Autonomous (no new capability, no arch change)

## Challenge Results
- Challenger: SKIP — confirming completed architectural work validated across 4 prior cycles + independent research
- Confidence in original: .92

[[2026-04-05]] Sun 13:28
## Architecture Review (Cycle 5 — Closure)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Premise challenge | FAIL | Task fully superseded — zero deliverables remain |
| KISS/YAGNI | FAIL | Adding "MCP equivalent" blockquotes after MCP tool names is circular |

### Independent Codebase Verification (2026-04-05)
- kanban-md CLI invocations in 14 target skill files: 0
- Normalization targets (MCP note:, MCP equivalents (owlbear-kanban):): 0
- Workflow skills with consolidated h-mcp-kanban pointer: 10+ (from #486, audited 1.00)
- Result: identical to Cycles 3 and 4 — zero #576 deliverables exist

### Supersession Chain (unchanged)
1. #484 (Phase B, archived): removed CLI references, moved MCP-only
2. #486 (Phase C, archived, audited 1.00): consolidated kanban refs to h-mcp-kanban, removed 39 inline MCP notes (DRY)
3. Net effect: zero CLI invocations + zero normalization targets = zero #576 deliverables

### Loop-Breaking Note
This is the 5th architecture review. Cycles 3, 4, and 5 independently verified supersession. The task keeps returning to backlog without new information. Archiving directly to break the dispatch loop.

### Challenge Results
- Challenger: SKIP (REJECT verdict, 5th consecutive rejection)

### Verdict: REJECT → archive
### Action Taken: Rejected to ideation for immediate archival as superseded by #486. Follow-up #627 exists at ideation for parent #483 update.
