---
id: 460
title: Update researcher agent and research-workflow skill with tier 
  classification
status: archived
priority: medium
created: 2026-03-31 03:40:02.128799+02:00
updated: 2026-03-31 08:51:41.594064+02:00
started: 2026-03-31 08:51:40.994403+02:00
completed: 2026-03-31 08:51:40.994403+02:00
tags:
- process
- scope:agents
- quality
class: standard
archival_reason: completed
archival_refs: []
---

Add mandatory tier classification step to research-workflow Step 5 and researcher agent boundaries. After completing analysis, researcher must classify outcome as T1/T2/T3 using deterministic triggers. T3 outcomes MUST create a blocking decision request. T1 proceeds directly. See docs/research/mandatory-user-decision-gate.md. AC: - [ ] research-workflow Step 5 has tier classification decision tree - [ ] researcher agent boundaries list T3 triggers explicitly - [ ] researcher critical_rules updated: T3 outcomes require blocking DR - [ ] Red flag added: creating follow-up tasks for T3 outcome without DR

[[2026-03-31]] Tue 03:54
## Research
Researcher validation (2026-03-31): All 6 mandatory checklist items pass. Parent research (docs/research/mandatory-user-decision-gate.md, #385) provides complete backing with 9 sources. No novel research needed.
Changes target: skills/research-workflow/SKILL.md (Step 5 decision tree) and agents/researcher.agent.md (boundaries, critical_rules, red flags).
Builder should reference parent research S4 for exact T1/T2/T3 triggers.

[[2026-03-31]] Tue 04:23
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| research-workflow Step 5 has tier classification decision tree | Clear: builder adds T1/T2/T3 decision tree with 6 deterministic T3 triggers from research S4 | Keep |
| researcher agent boundaries list T3 triggers explicitly | Clear: 6 triggers go in boundaries section | Keep |
| researcher critical_rules updated: T3 outcomes require blocking DR | Clear: new bullet in critical_rules | Keep |
| Red flag added: creating follow-up tasks for T3 outcome without DR | Clear: new row in red flags table | Keep |

### Architecture Notes
Changes target two tightly-coupled markdown files (researcher agent + its workflow skill) for a single concern: tier classification. No Python code produced, so no test task required. The research doc (docs/research/mandatory-user-decision-gate.md S4) provides exact T1/T2/T3 triggers. Builder should copy those verbatim rather than paraphrasing.

No dependency on #459 (impact_tier in DR skill) needed. This task tells the researcher WHEN to create DRs (tier triggers); #459 changes the DR FORMAT. They are additive and order-independent. The existing DR skill already supports urgency: blocking, which is sufficient for T3 DRs.

Patterns to follow: critical_rules uses dash-bullet lists; boundaries red flags use the existing markdown table format; Step 5 in research-workflow should insert the decision tree before the existing create follow-up tasks instructions (classification happens first, then action).

### Changes Made
- Verified both target files have no existing tier language (no conflicts)
- Verified no dependency on #459 needed
- Approved to todo

### Dependencies
- Verified: research doc docs/research/mandatory-user-decision-gate.md exists and is complete
- No depends_on needed. #459 (DR format) and #460 (tier triggers) are order-independent

[[2026-03-31]] Tue 05:09
## Test-Writer Notes
- Non-implementation task (tagged quality) - no tests applicable.
- Architecture review confirmed: No Python code produced, changes target markdown files only.
- Passing through to builder.

[[2026-03-31]] Tue 06:59
## Builder Notes\n- Files changed: skills/research-workflow/SKILL.md, agents/researcher.agent.md\n- Tests: non-implementation task; no pytest run needed\n- Lint: markdown only; no ruff applicable\n- Evidence: 4 AC items verified by file inspection\n- Commit: afa6417

-t

[[2026-03-31]] Tue 07:26
## Review Evidence

Test: N/A markdown only
Lint: N/A markdown only
Commit afa6417f verified: agents/researcher.agent.md +13, skills/research-workflow/SKILL.md +29/-1

AC1: research-workflow Step 5 has tier classification - PASS
AC2: researcher boundaries list T3 triggers explicitly - PASS
AC3: researcher critical_rules T3 requires blocking DR - PASS
AC4: Red flag for T3 tasks without DR - PASS

All 6 T3 triggers in both files match research doc Section 4 verbatim.
Tier classification placed before Create follow-up tasks per architect notes.
No security concerns (markdown only).

Verdict: PASS - confidence .93

[[2026-03-31]] Tue 07:40
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Tier classification is already in agent-common.instructions.md; per-agent enforcement lives in agent/skill files. No project-level behavior or API changed. |
| 2 | Docstrings | No | N/A | No Python files modified. Builder commit afa6417 touches only skills/research-workflow/SKILL.md and agents/researcher.agent.md (markdown). |
| 3 | docs/sources/overview.md | No | N/A | No new external sources. Implementation draws entirely from internal research doc docs/research/mandatory-user-decision-gate.md (#385). Parent task logged its external sources. |
| 4 | README.md | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Pass | docs/research/mandatory-user-decision-gate.md exists (verified). Task body links to it. No new research doc required (implementation task). |
| 6 | Scratch files | N/A | Pass | No docs/scratch/460-* files found. |

### Files Updated
- None

### Scratch Files Cleaned
- None
