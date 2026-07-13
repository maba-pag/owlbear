---
id: 622
title: Wire pick_tasks into orchestrator workflow
status: archived
priority: medium
created: 2026-04-05T01:31:13.8750468+02:00
updated: 2026-04-05T21:26:14.3033493+02:00
started: 2026-04-05T21:26:14.3033493+02:00
completed: 2026-04-05T21:26:14.3033493+02:00
tags:
    - scope:agents
    - scope:orchestrator
    - phase-2
    - type:build
    - agent
parent: 619
depends_on:
    - 621
    - 628
class: standard
---

## Acceptance Criteria

### w-orchestration (share/skills/w-orchestration/SKILL.md)

**Step 1 — Plan (rewrite):**
- Replace `runSubagent("dispatcher", ...)` with `pick_tasks(limit=25, tag={scope})` MCP tool call
- tag parameter receives user's scope filter (e.g., "phase-2" from "Orchestrate: tag:phase-2"); pass None when scope is "all" or omitted
- After receiving pick_tasks result, map each task's status to dispatch agent using the status-to-agent mapping table (added below)

**Status-to-Agent Mapping Table (new section in w-orchestration):**
- Reproduce dispatch mapping from w-dispatch-planning: ideation=researcher, backlog=architect, todo=test-writer, in-progress=builder, review=reviewer, docs=doc-writer, done=auditor
- Include Non-Status-Triggered Agents: planner (DECOMP, see below) and curator (periodic, already handled by Step 2)

**DECOMP Post-Filter (new logic in Step 1, after status-to-agent mapping):**
- For each task at `backlog` status in the pick_tasks result, call `show_task(task_id)` (0-3 calls per cycle)
- If task body contains "Needs decomposition:", remap agent to planner instead of architect

**Crash Failure Exclusion (new logic in Step 1, after pick_tasks returns):**
- Apply set-difference filter: exclude task_ids present in crash_failures set from pick_tasks result
- crash_failures populated from previous cycle's errored dispatches (existing pattern)

**Stale Detection (refactor Context Budget and Step 1):**
- Add `last_dispatched: dict[int, str]` to Context Budget (task_id to status from previous pick_tasks result, max 20 entries)
- First-stale detection in Step 1: after pick_tasks returns, compare each result task's status against last_dispatched; same task at same status = stale
- For stale tasks NOT in stale_retried: call show_task, extract single-line retry_hint (120 chars max) from last agent note section
- Update last_dispatched with current cycle's pick_tasks result before proceeding to Step 2

**Gate Warning Removal:**
- Remove `gate_warned` dict from Context Budget section
- Remove gate_warning processing block from Step 1
- Remove "Gate Warning" output line from Output Format section
- Remove gate_warned references from Verification Checklist and Known Pitfalls

**Dispatcher Reference Cleanup (all 13 mentions in w-orchestration):**
- Context Budget: replace "The dispatcher reads the board each cycle" with pick_tasks description
- Signal Contracts: replace "Dispatcher output" subsection with pick_tasks output description
- Step 1: replace runSubagent dispatcher calls with pick_tasks tool call
- Step 3: update re-plan references from dispatcher to pick_tasks
- Output Format: update "Dispatching dispatcher" example line
- Verification Checklist: update "Dispatcher was dispatched" item
- Known Pitfalls: update stale_retried tracking description

### orchestrator.agent.md (share/agents/orchestrator.agent.md)

Update ALL sections containing dispatcher references (9 references across 7 sections):
- `agents:` frontmatter (L10): remove `dispatcher` from list
- `<persona>` (L31): replace "The dispatcher reads it and gives you a flight strip" with pick_tasks tool call metaphor
- `<subagents>` table (L55): remove dispatcher row
- `<output_format>` (L81): replace "Dispatching dispatcher with scope" with pick_tasks phrasing
- `<boundaries>` (L101, L114, L118): replace "If the dispatcher returns empty plan" and "The dispatcher decides, not you" with pick_tasks equivalents
- `<examples>` (L129, L142): update "The dispatcher saw the crashed task" and "the dispatcher should decide" narratives

### w-dispatch-planning (share/skills/w-dispatch-planning/SKILL.md)

- Add archive callout below frontmatter: `> **ARCHIVED** — Superseded by pick_tasks MCP tool (#621) and w-orchestration direct integration (#622). Retained as design reference for NON_IMPL_TAGS authoritative list.`
- Update frontmatter description to: "Workflow (ARCHIVED): Dispatch planning — reference design doc for NON_IMPL_TAGS and agent mapping"
- Do NOT delete or move file — NON_IMPL_TAGS cross-references in w-tdd-red (L23) and w-arch-review (L78) point here

### Scope Boundaries

- Does NOT touch: agent-common.instructions.md, r-pipeline-protocol, agents/README.md, h-agent-structure, dispatcher.agent.md (all deferred to #629)
- Does NOT modify Python code or test files

[[2026-04-05]]
## Research
- Research doc: .owlbear/research/wire-pick-tasks-orchestrator.md
- Sources: 9 studied, 7 high-relevance (all codebase-internal)
- Recommendation: Wire pick_tasks with status-to-agent mapping, DECOMP post-filter via show_task, tag passthrough param, drop gate_warnings (confidence: .82)
- Follow-up tasks created: #628 (update #621 AC for tag param, ideation), #629 (clean up dispatcher references, ideation)
- Decision requests: none — all findings T1/T2

## Challenge Results (Research Phase)
- Challenger: RECONSIDER (items 3 and 4)
- Confidence in original: .75 revised to .82
- Key challenges: (1) needs_decomp field changes #621 AC unnecessarily — use show_task post-filter instead; (2) scope param leaks orchestrator concepts — use tag passthrough instead; (3) missing first-stale detection state tracking
- Researcher response: accepted all three — revised DECOMP to post-filter, scope to tag passthrough, added last_dispatched state tracking to recommendation

[[2026-04-05]] Sun 10:43
Research complete. Doc at .owlbear/research/wire-pick-tasks-orchestrator.md. Key findings: 8 responsibilities migrated from dispatcher, 2 design gaps identified (DECOMP routing, scope filtering) with revised solutions after challenger review. Follow-ups: #628 (tag param AC update), #629 (dispatcher reference cleanup).

[[2026-04-05]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: replace dispatcher subagent with pick_tasks in orchestrator workflow |
| Interface clarity | PASS (refined) | Original AC missing 4 research findings + orchestrator.agent.md coverage gaps; refined to enumerate all 8 migrated responsibilities with line-level specificity |
| Dependency correctness | PASS | depends_on [621] correct. #628 (tag param) must resolve before #621 is built (per #619 arch review dep inversion fix); #622 AC assumes tag param exists |
| Module layering | PASS | Skill files and agent config only; status-to-agent mapping moves from dispatcher skill to orchestrator skill (same layer) |
| TDD compliance | PASS | Non-impl task; added `agent` tag for pass-through |
| KISS/YAGNI | PASS | Minimal migration of existing dispatcher logic; no new capabilities |
| Premise challenge | PASS | Dispatcher is deterministic (disable-model-invocation); MCP tool is correct replacement |
| Pattern consistency | PASS | Follows existing patterns: MCP tool call in skill steps, status-to-agent table format, Context Budget state tracking |
| Security surface | PASS | No new system boundaries; .md file edits only |
| Single domain | PASS | scope:agents + scope:orchestrator, all within orchestrator domain |

### AC Refinement Summary
Original AC missed 4 key responsibilities from research and had ambiguous orchestrator.agent.md coverage. Refined:
1. DECOMP routing via show_task post-filter (research 3.2)
2. Stale detection: last_dispatched tracking with max 20 entries and status-comparison algorithm (research 3.5)
3. Gate warning removal from w-orchestration (research 3.4)
4. orchestrator.agent.md: all 7 sections with dispatcher references enumerated (challenger C1)
5. Crash failure exclusion placed in Step 1 post-processing, not wave assembly (challenger C2)
6. Stale detection data structure specified: dict[int, str], max 20, status-comparison (challenger C3)

### Codebase Evidence
- w-orchestration: 13 dispatcher references (L15, L24, L42, L45, L51, L59, L141, L143, L150, L169, L173, L175, L181)
- orchestrator.agent.md: 9 dispatcher references across 7 sections (L10, L31, L55, L81, L101, L114, L118, L129, L142)
- agent-common.instructions.md: 1 dispatcher row (L14) — deferred to #629
- NON_IMPL_TAGS: w-dispatch-planning is authoritative source (L15, L64); cross-refs in w-tdd-red (L23) and w-arch-review (L78); file retained

### Challenge Results (Architecture Phase)
- Challenger: RECONSIDER (confidence: 0.75)
- C1 (HIGH): orchestrator.agent.md AC incomplete — accepted, expanded to all 7 sections
- C2 (MEDIUM): crash failure exclusion misplaced in "wave assembly" — accepted, moved to Step 1 post-processing
- C3 (LOW-MEDIUM): stale detection struct unspecified — accepted, added dict[int,str] max 20 with algorithm
- Architect response: accepted all three, AC refined accordingly

### Verdict: APPROVE (after REFINE)
### Action: Refined AC with all 8 migrated responsibilities, line-level orchestrator.agent.md coverage, and challenger feedback. Added `agent` tag. Advanced backlog to todo.

[[2026-04-05]] Sun 12:21
Refined AC: expanded from 4 bullets to 7 change areas covering all 8 migrated responsibilities from research doc. Added line-level orchestrator.agent.md coverage (all 7 sections), moved crash exclusion to Step 1, specified stale detection struct (dict[int,str] max 20). Added `agent` pass-through tag. Challenger accepted 3/3.

[[2026-04-05]] Sun 16:19
Non-implementation pass-through. Task tagged `agent`; all AC changes are .md file edits only (w-orchestration/SKILL.md, orchestrator.agent.md, w-dispatch-planning/SKILL.md). AC explicitly states no Python code or test files modified. No tests applicable.

## Test-Writer Notes
- Non-implementation task (tagged `agent`) — no tests applicable.
- All AC changes are to .md files: w-orchestration/SKILL.md, orchestrator.agent.md, w-dispatch-planning/SKILL.md.
- Does NOT modify Python code or test files (explicit scope boundary in AC).
- Passing through to builder.

[[2026-04-05]] Sun 17:43
## Builder Notes\n- Non-implementation task — all changes are .md file edits only.\n- Files changed: 3\n  - `share/skills/w-orchestration/SKILL.md`: replaced all 13 dispatcher references with pick_tasks; added status-to-agent mapping table, DECOMP post-filter, crash failure exclusion, stale detection with last_dispatched; removed gate_warned from Context Budget, Output Format, Verification Checklist, and Known Pitfalls\n  - `share/agents/orchestrator.agent.md`: removed dispatcher from agents frontmatter; updated persona, subagents table (removed dispatcher row), output_format, boundaries (2 locations), and examples (2 locations) — all 9 references across 7 sections\n  - `share/skills/w-dispatch-planning/SKILL.md`: updated frontmatter description to ARCHIVED; added ARCHIVED callout below frontmatter\n- Tests: n/a (non-impl pass-through)\n- Lint: n/a (.md files only)\n- Coverage: n/a\n- No Python files modified. Scope boundary respected.

[[2026-04-05]] Sun 19:08
## Review Evidence

### Test Results
- N/A — tagged `agent` (non-impl pass-through). No Python files modified. Test-writer confirmed skip. No `TestFromAC_*` classes exist.

### Lint: N/A (.md files only)

### Coverage: N/A

### Source Control Changes (3 files)
- `share/skills/w-orchestration/SKILL.md`
- `share/agents/orchestrator.agent.md`
- `share/skills/w-dispatch-planning/SKILL.md`

Scope boundary respected: zero Python files touched (confirmed via git diff).

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
SKIP — conditional check: no `TestFromAC_*` classes exist. Non-impl task per AC scope boundary.

#### Security Review
- .md file edits only. No injection surface, no secrets, no system boundaries. No issues.

#### Test Integrity
SKIP — no `TestFromAC_*` modifications possible on non-impl task.

#### Test Quality
N/A

#### Data Safety
- No data mutations. .md files only. No issues.

#### Implementation-Aware Gaps
N/A — no code changed.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
None.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| w-orchestration: Replace dispatcher subagent with pick_tasks(limit=25, tag) | SKILL.md L43: `pick_tasks(limit=25, tag="{scope_tag}")` | PASS |
| tag param: scope filter passthrough, None when "all" | SKILL.md L45: "Pass `tag=None` when scope is 'all' or omitted." | PASS |
| Status-to-agent mapping table added (all 7 statuses) | SKILL.md L54-64 | PASS |
| Non-Status-Triggered Agents (planner DECOMP, curator periodic) | SKILL.md L66-70 | PASS |
| DECOMP post-filter: show_task for backlog, remap to planner on "Needs decomposition:" | SKILL.md L72 | PASS |
| Crash failure exclusion: set-difference filter | SKILL.md L49 | PASS |
| Stale detection: last_dispatched dict[int,str] max 20, status-comparison algorithm | Context Budget L17 + Step 1 L73-86 | PASS |
| Gate Warning removal: Context Budget | gate_warned removed; last_dispatched added | PASS |
| Gate Warning removal: Step 1 processing block | No gate_warning processing in Step 1 | PASS |
| Gate Warning removal: Output Format | No gate warning output line | PASS |
| Gate Warning removal: Verification Checklist | No gate_warned checklist items | PASS |
| Gate Warning removal: Known Pitfalls | gate_warned pitfall replaced with last_dispatched cap | PASS |
| All 13 dispatcher references replaced (grep confirmed) | 0 matches for "dispatcher" in w-orchestration/SKILL.md | PASS |
| orchestrator.agent.md agents: frontmatter dispatcher removed | L8: dispatcher absent from agents list | PASS |
| orchestrator.agent.md persona: pick_tasks metaphor replacing dispatcher | L31-38 | PASS |
| orchestrator.agent.md subagents table: dispatcher row removed | Table has no dispatcher row | PASS |
| orchestrator.agent.md output_format: updated phrasing | "Running pick_tasks with tag=" | PASS |
| orchestrator.agent.md boundaries (3 locations) | All three replaced with pick_tasks phrasing | PASS |
| orchestrator.agent.md examples (2 locations) | Both narratives updated | PASS |
| All 9 dispatcher refs replaced (grep confirmed) | 0 matches for "dispatcher" in orchestrator.agent.md | PASS |
| w-dispatch-planning: ARCHIVED callout below frontmatter | L8: "> **ARCHIVED** — Superseded by pick_tasks..." | PASS |
| w-dispatch-planning: frontmatter description updated to ARCHIVED | L3: "Workflow (ARCHIVED): Dispatch planning..." | PASS |
| w-dispatch-planning: file NOT deleted | File still at share/skills/w-dispatch-planning/SKILL.md | PASS |
| Scope: Does NOT touch agent-common, r-pipeline-protocol, agents/README, h-agent-structure, dispatcher.agent.md | Confirmed via git diff | PASS |
| Scope: Does NOT modify Python code or test files | Confirmed via git diff | PASS |

### Confidence: .97
### Verdict: PASS

[[2026-04-05]] Sun 19:46
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | `.github/copilot-instructions.md` is 5 lines (project identity only) — no orchestrator/agent tables to update |
| 2 | Module docstrings | No | N/A | Zero Python files modified; confirmed by git diff in review evidence |
| 3 | External attribution | No | N/A | All 9 sources were codebase-internal (confirmed in research doc) |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/wire-pick-tasks-orchestrator.md` exists and linked in task body under ## Research section |

### Files Updated
- Committed builder's uncommitted changes: `share/skills/w-orchestration/SKILL.md`, `share/agents/orchestrator.agent.md`, `share/skills/w-dispatch-planning/SKILL.md` — commit `f212eff` (builder left changes unstaged)

### Scratch Files Cleaned
- None (no `.owlbear/scratch/622-*` files found)

[[2026-04-05]] Sun 21:25
[[audit section appended via MCP]]

[[2026-04-05]] Sun 21:26
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Replace dispatcher with pick_tasks | SKILL.md L43 | PASS |
| tag param None when all/omitted | SKILL.md L45 | PASS |
| Status-to-agent mapping table | SKILL.md L54-64 | PASS |
| Non-Status-Triggered Agents | SKILL.md L66-70 | PASS |
| DECOMP post-filter via show_task | SKILL.md L72 | PASS |
| Crash failure exclusion | SKILL.md L49 | PASS |
| Stale detection last_dispatched | Context Budget + Step 1 | PASS |
| Gate Warning removal (4 locs) | grep gate_warn = 0 | PASS |
| 13 dispatcher refs w-orchestration | grep dispatcher = 0 | PASS |
| agent.md dispatcher removed | L8 absent | PASS |
| agent.md persona pick_tasks | L31-38 | PASS |
| agent.md subagents no dispatcher | confirmed | PASS |
| agent.md all 7 sections updated | confirmed | PASS |
| 9 dispatcher refs agent.md | grep dispatcher = 0 | PASS |
| w-dispatch-planning ARCHIVED callout | L8 | PASS |
| w-dispatch-planning frontmatter | L3 | PASS |
| w-dispatch-planning NOT deleted | exists | PASS |
| Scope: no Python/test files | git log .md-only | PASS |

Reviewer mapped all 26 AC lines. Spot-checked + grep-confirmed.

### Test Results
- pytest: 2899 passed, 435 failed, 18 skipped. Zero failures in scope.
- ruff: All checks passed

### Architect Quality: 5/5

### Deduction Breakdown
- AC lines without evidence: 0
- Lint violations: 0
- AC quality: N/A (5/5)
- Missing reviewer evidence: 0
- Full-suite failures in scope: 0

### Confidence: 1.00
### Action: archive

[[2026-04-05]] Sun 21:26
18/18 AC lines verified (grep-confirmed dispatcher/gate_warned removal). pytest 2899 passed, 0 in-scope failures. ruff clean. Architect quality 5/5. Confidence 1.00.
