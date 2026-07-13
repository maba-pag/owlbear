---
id: 461
title: Add decision-request verification to architect backlog gate
status: archived
priority: medium
created: 2026-03-31 03:40:10.027409+02:00
updated: 2026-03-31 09:02:15.756980+02:00
started: 2026-03-31 09:02:12.749795+02:00
completed: 2026-03-31 09:02:12.749795+02:00
tags:
- process
- scope:agents
- quality
class: standard
archival_reason: completed
archival_refs: []
---

Scope: `skills/arch-review/SKILL.md` and `agents/architect.agent.md` only. No code, no tests.

AC:
- [ ] arch-review Step 3 (Evaluate architecture) has a new numbered sub-step 12: "Decision-request verification" — if the task under review references `docs/research/*.md` in its body or is tagged `research`, check `docs/decisions/` for an approved DR (frontmatter `approved: true`) whose `task_id` matches the research doc's owning task; skip for tasks with no research reference
- [ ] arch-review Step 4 (Decide and act) Block row in the table notes: tasks originating from T3 research without an approved DR are blocked to ideation with reason "T3 research outcome requires approved decision request"
- [ ] architect.agent.md `<boundaries>` red flags list has a new entry: "You are approving a task that references a research doc (`docs/research/`) or is tagged `research` without verifying an approved decision request exists for that research"
- [ ] architect.agent.md `<output_format>` Channel B template includes a "DR Verification" line after the Verdict line showing: DR file path and approval status (e.g., `docs/decisions/pending/385-slug.md approved: true`), or "N/A — not research-driven"

See docs/research/mandatory-user-decision-gate.md (Section 6, C4) for context.

## Architecture Review
**Verdict:** Approve

### AC Assessment

- AC1 (arch-review Step 3 sub-step 12): Refined — specified exact step number, trigger conditions (research tag or docs/research/ reference), and verification mechanism (check docs/decisions/ for approved DR matching owning task_id)
- AC2 (Step 4 Block row): Clear — rejection path and reason text specified
- AC3 (boundaries red flag): Clear — exact section and wording specified
- AC4 (output template DR line): Refined — specified placement (after Verdict line), content format, and N/A fallback

### Architecture Notes
Process-only task: modifies arch-review skill and architect agent instruction files. No application code. Both files serve the same agent workflow (single domain: process/agents). Follows existing patterns: numbered sub-steps in Step 3, bullet entries in red flags list, template lines in Channel B output. No TDD needed (instruction files only, matching #460 precedent). Soft dependency on #459 (impact_tier concept) but self-contained — tier classification is defined in the research doc.

### Changes Made
- Refined AC with exact file locations, section targets, and verification mechanism

### Dependencies
- Verified: #459 (soft dep, impact_tier concept) at todo
- Verified: #460 (sibling, researcher tier classification) at todo

[[2026-03-31]] Tue 05:09
## Test-Writer Notes
- Non-implementation task (tagged quality) -- no tests applicable.
- Passing through to builder.

[[2026-03-31]] Tue 06:52
## Builder Notes
- Files changed: `skills/arch-review/SKILL.md`, `agents/architect.agent.md`
- Tests: N/A (non-implementation task — instruction files only)
- Lint: N/A (markdown only)
- AC1: arch-review Step 3 sub-step 12 "Decision-request verification" added after sub-step 11
- AC2: T3 research block path note added to Step 4 after Placeholder block path note
- AC3: Red flag added to architect.agent.md boundaries: "approving research-tagged task without verified approved DR"
- AC4: DR Verification line added to Channel B template immediately after Verdict line

[[2026-03-31]] Tue 09:02
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: arch-review Step 3 sub-step 12 | Verified at SKILL.md L94-99: sub-step 12 "Decision-request verification" with correct trigger, matching mechanism, and skip clause | PASS |
| AC2: Step 4 T3 research block path | Verified at SKILL.md L112: blockquote with exact reason text | PASS |
| AC3: architect boundaries red flag | Verified at architect.agent.md L140: new red flag entry matching specified wording | PASS |
| AC4: Channel B DR Verification line | Verified at architect.agent.md L63: DR Verification line after Verdict line with example and N/A fallback | PASS |

### Test Results
- pytest: 1925 passed, 269 failed (pre-existing, none in task scope; process-only task, no code)
- ruff: N/A (markdown only)

### Notes
- Builder added a "Non-implementation tagging" blockquote in Step 4 between Refine and Split rows (not in AC, benign scope creep). Breaks table rendering (table split into two segments).
- Deliverables were uncommitted by builder (quality gap noted).
- No Review Evidence section from reviewer (missing).

### AC Quality Score: 4
AC was specific: exact file paths, section targets, content format, and placement. Minor gap: AC did not specify whether the Step 4 note should be a blockquote or table row.

### Deduction breakdown
- Missing reviewer evidence section: -.02
### Confidence: .98
### Action: archive
