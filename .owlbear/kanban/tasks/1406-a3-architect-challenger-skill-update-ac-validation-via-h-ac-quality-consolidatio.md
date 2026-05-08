---
id: 1406
title: 'A3: Architect/challenger skill update — AC validation via h-ac-quality, consolidation-test
  backstop'
status: in-progress
priority: needed
created: 2026-05-07T23:16:25.200360+00:00
updated: 2026-05-08T08:37:15.970551+00:00
tags:
- pipeline
- ws-ac-quality
- scope:agents
- agent
parent: 1403
depends_on:
- 1404
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)

## Acceptance Criteria

P1: `w-arch-review/SKILL.md` Step 2.5 expanded — challenger prompt includes AC quality validation using `h-ac-quality` rules and `sibling_tasks` input field for consolidation-test detection; architect action table extended with `ac-quality` finding → REFINE and `consolidation-test-gap` → planner dispatch (td:0)
P2: Challenger detects missing consolidation-test tasks: if task has ≥2 sibling implementation tasks under same parent AND no sibling consolidation-test task → flag for planner (td:0)
P2: Architect acts on AC quality only when challenger flags issues — architect Step 2 does NOT contain AC wording quality checks (checker subagent pattern) (td:0)
P2: `h-ac-quality` added to `<required_reading>` in both `challenger.agent.md` and `architect.agent.md`; challenger `<critical_rules>` expanded with AC quality validation and consolidation-test detection responsibilities (td:0)
P2: Challenger input contract (`Required Input Fields` table) includes new optional `sibling_tasks` field (td:0)
P3: Verification by diff comparison of 3 modified skill/agent files (td:0)

## Scope

**In scope:** `w-arch-review/SKILL.md` Step 2.5 expansion, `challenger.agent.md` required-reading + critical-rules + I/O contract, `architect.agent.md` required-reading
**Out of scope:** h-ac-quality content (A1), planner changes (A2), reviewer changes (B1)
[[2026-05-08]]
## Research
- Research doc: .owlbear/research/1406-architect-challenger-ac-quality.md
- Sources: 7 studied (all codebase-internal), 5 high-relevance
- Recommendation: Approach A — architect passes sibling task data to challenger in prompt (no tool change to challenger); 3 files to modify: w-arch-review (expand Step 2.5 for AC quality + consolidation-test), challenger.agent.md (add h-ac-quality to required reading, expand I/O contract), architect.agent.md (add h-ac-quality to required reading). Confidence: 0.88
- Key finding: Challenger lacks kanban tools — consolidation-test detection uses architect-provided sibling data, not challenger-initiated board queries
- No follow-up tasks needed — this task IS the implementation deliverable
[[2026-05-08]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All changes serve one purpose: wire h-ac-quality into architect/challenger checker-subagent pattern |
| Interface clarity | PASS | Refined AC lines to name specific sections (Step 2.5), input fields (sibling_tasks), and action mappings |
| Dependency correctness | PASS | Depends on #1404 (h-ac-quality skill) — file exists at share/skills/h-ac-quality/SKILL.md; task archived |
| Module layering | N/A | Markdown skill/agent files — no code dependency direction |
| TDD compliance | PASS | All td:0; tagged `agent` for test-writer pass-through |
| KISS/YAGNI | PASS | Approach A (pass sibling data via prompt) avoids adding kanban tools to challenger — simplest solution |
| Premise challenge | PASS | AC quality validation and consolidation-test backstop are new capabilities defined in the brief |
| Pattern consistency | PASS | Follows existing challenger I/O contract pattern (new input field, categorized output) |
| Security surface | PASS | No new system boundaries — agent/skill markdown only |
| Single domain | PASS | All changes in agent/skill domain (scope:agents) |

### AC Refinements Applied
- P1 refined: vague "skill updated" → specific Step 2.5 expansion with action table entries
- Split implicit P2: explicit AC for required_reading additions, critical_rules expansion, and sibling_tasks input contract
- All lines annotated (td:0)
- Added `agent` pass-through tag for non-impl pipeline routing

### Challenge Results
- Challenger: SKIPPED — all AC lines td:0 (per Step 2.1 subagent gating)

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Refined AC for specificity (Step 2.5 section, sibling_tasks field, action table entries), added agent pass-through tag, advanced backlog → todo
[[2026-05-08]]
## Test-Writer Notes
- Non-implementation task (tagged `agent`) — no tests applicable.
- All AC lines annotated td:0; architect explicitly noted "Test-writer: SKIP".
- Passing through to builder.
[[2026-05-08]]
## Builder Notes
- Non-implementation task (tagged `agent`) confirmed from Test-Writer Notes.
- No code changes were made.
- No tests or lint runs were required for this pass-through path.
- Routed directly to review per w-tdd-green Step 0a.
[[2026-05-08]]
## Review Evidence
### Test Results
- pytest: not run — td:0 artifact-only review; no executable task-scoped test surface

### Lint: skipped — td:0 Markdown/agent-skill task; direct artifact inspection used instead of quality-runner

### Coverage: n/a — td:0 artifact-only review

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| All AC lines | N/A — td:0 artifact-inspection task | N/A | N/A |

#### Security Review
- No issues found in current repo state. Scope is Markdown skill/agent artifacts only, and no runtime code changes landed.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| N/A | No TestFromAC_* task tests exist for this td:0 artifact task | N/A |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | N/A | td:0 artifact task; no task-scoped tests |
| Negative/error-path coverage | N/A | td:0 artifact task; no task-scoped tests |
| Manual mutation reasoning | N/A | td:0 artifact task; proof is file-content inspection |
| Test independence | N/A | td:0 artifact task; no task-scoped tests |
| Descriptive test names | N/A | td:0 artifact task; no task-scoped tests |

#### Data Safety
- No issues found. No persistence, concurrency, or unbounded-input code changes are present because the scoped deliverable was not implemented.

#### Implementation-Aware Gaps
- `share/skills/w-arch-review/SKILL.md:116-130` still contains the pre-task challenger flow: the prompt fields stop at `research-doc`, and the action table contains only `proceed` / `reconsider` / `block`. There is no `h-ac-quality` validation mention, no `sibling_tasks` input, and no `ac-quality` or `consolidation-test-gap` routing.
- `share/agents/challenger.agent.md:33-45` still lists only `r-pipeline-protocol` in `<required_reading>` and does not assign AC-quality validation or consolidation-test detection in `<critical_rules>`.
- `share/agents/challenger.agent.md:59-70` omits the required `sibling_tasks` field from `Required Input Fields`.
- `share/agents/architect.agent.md:33-38` still omits `h-ac-quality` from `<required_reading>`.
- The task body explicitly says `No code changes were made` and `Routed directly to review` at `.owlbear/kanban/tasks/1406-a3-architect-challenger-skill-update-ac-validation-via-h-ac-quality-consolidatio.md:83-87`, while git-log search found only a researcher commit for `#1406` at `.git/logs/refs/heads/dev:2075` and `.git/logs/HEAD:2250`. No builder commit evidence was found for this deliverable.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Verified the parent brief directly: `.owlbear/briefs/draft-pipeline-review-rethink/brief.md:94` still defines A3 as expanding architect/challenger AC-quality validation and missing consolidation-test detection, so this is not stale-child-task wording drift.
- `share/skills/w-arch-review/SKILL.md:37-63` does keep Step 2 free of direct AC-wording quality checks, which is consistent with the checker-subagent pattern in isolation. The failure is that Step 2.5 was not expanded to let the challenger surface and route those findings.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| P1: `w-arch-review/SKILL.md` Step 2.5 expanded with `h-ac-quality`, `sibling_tasks`, `ac-quality` -> REFINE, `consolidation-test-gap` -> planner dispatch | `share/skills/w-arch-review/SKILL.md:116-130` still shows only the old challenger contract and old three-row action table | N/A — td:0 artifact inspection | FAIL |
| P2: Challenger detects missing consolidation-test tasks when sibling implementation tasks exist and no consolidation-test sibling exists | `share/skills/w-arch-review/SKILL.md:118-126` and `share/agents/challenger.agent.md:59-70` contain no `sibling_tasks` input or consolidation-test detection contract | N/A — td:0 artifact inspection | FAIL |
| P2: Architect acts on AC quality only when challenger flags issues; Step 2 does not contain AC wording quality checks | `share/skills/w-arch-review/SKILL.md:37-63` keeps Step 2 free of AC-wording checks, but `share/skills/w-arch-review/SKILL.md:118-126` lacks any `ac-quality` finding/action path, so the checker-subagent handling is not implemented end-to-end | N/A — td:0 artifact inspection | FAIL |
| P2: `h-ac-quality` added to both agent files; challenger critical rules expanded | `share/agents/challenger.agent.md:33-45` and `share/agents/architect.agent.md:33-38` omit `h-ac-quality`; challenger critical rules still describe only generic adversarial review | N/A — td:0 artifact inspection | FAIL |
| P2: Challenger `Required Input Fields` includes optional `sibling_tasks` | `share/agents/challenger.agent.md:59-70` ends at `research-doc`; no `sibling_tasks` row exists | N/A — td:0 artifact inspection | FAIL |
| P3: Verification by diff comparison of 3 modified skill/agent files | Task scope names the three target files at `.owlbear/kanban/tasks/1406-a3-architect-challenger-skill-update-ac-validation-via-h-ac-quality-consolidatio.md:37-43`, but the same task file says no code changes were made at `:83-87`, and git-log search shows only a researcher commit for `#1406` | N/A — td:0 artifact inspection | FAIL |

### Deductions
- -0.35: Core Step 2.5 expansion in `share/skills/w-arch-review/SKILL.md` is absent.
- -0.25: Agent-file wiring for `h-ac-quality` and challenger responsibilities is absent.
- -0.20: `sibling_tasks` input contract and consolidation-test detection are absent.
- -0.15: No builder-deliverable evidence exists for the three scoped files.

### Confidence: 0.05
### Verdict: FAIL
### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Implement the A3 Step 2.5 wiring: add `h-ac-quality` validation language, pass `sibling_tasks`, and map challenger outputs `ac-quality` -> REFINE and `consolidation-test-gap` -> planner dispatch | `share/skills/w-arch-review/SKILL.md` | AC rows 1-3; `share/skills/w-arch-review/SKILL.md:116-130` |
| 2 | builder | Add `h-ac-quality` to both agent `<required_reading>` sections; expand challenger `<critical_rules>` for AC-quality validation and consolidation-test detection; add optional `sibling_tasks` to challenger `Required Input Fields` | `share/agents/challenger.agent.md`, `share/agents/architect.agent.md` | AC rows 2, 4, 5; `share/agents/challenger.agent.md:33-45`, `share/agents/challenger.agent.md:59-70`, `share/agents/architect.agent.md:33-38` |
| 3 | builder | Record the actual changed files and builder commit in the task body before returning to review | `.owlbear/kanban/tasks/1406-a3-architect-challenger-skill-update-ac-validation-via-h-ac-quality-consolidatio.md` | AC row 6; task body `:83-87`, git-log evidence `.git/logs/refs/heads/dev:2075` / `.git/logs/HEAD:2250` |