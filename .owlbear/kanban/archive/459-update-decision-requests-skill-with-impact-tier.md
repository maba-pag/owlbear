---
id: 459
title: Update decision-requests skill with impact_tier field and T3 indefinite 
  blocking
status: archived
priority: medium
created: 2026-03-31 03:39:53.060500+02:00
updated: 2026-03-31 11:14:59.738569+02:00
started: 2026-03-31 11:14:59.118333+02:00
completed: 2026-03-31 11:14:59.118333+02:00
tags:
- process
- scope:agents
- quality
class: standard
archival_reason: completed
archival_refs: []
---

Add impact_tier (1/2/3) to decision-request frontmatter. T3 decisions block indefinitely (no auto-resolve). T2 keeps 5-day auto-timeout. Update file format section, resolution workflow, and planner integration notes. See docs/research/mandatory-user-decision-gate.md.

AC:
- [ ] impact_tier field added to frontmatter fields table (values: 1, 2, 3; set by agent)
- [ ] Missing impact_tier defaults to tier 2 (backwards compat: existing files keep current 5-day auto-resolve behavior)
- [ ] T3 decisions do not auto-resolve (auto-resolution section states planner skips 5-day timer when impact_tier=3)
- [ ] T2 decisions keep current 5-day auto-resolve (no behavior change)
- [ ] File format example (decision request template) includes impact_tier in agent metadata block
- [ ] Blocking behavior / auto-resolution section documents tier differences (T2 vs T3)
- [ ] T1 note: impact_tier=1 outcomes do not produce decision requests (autonomous); field value 1 exists for completeness but should not appear in practice

Scope: skills/decision-requests/SKILL.md only. No code, no tests.
Depends on: nothing. Downstream: #464 (dispatch-planning Recipe 0 tier-aware auto-resolve).

[[2026-03-31]] Tue 04:18
## Research
Validated (2026-03-31). See docs/research/impact-tier-decision-requests.md.
Backwards compat: missing impact_tier defaults to T2.
Gap found: dispatch-planning Recipe 0 needs tier-aware auto-resolve (created #464).

[[2026-03-31]] Tue 05:01
## Test-Writer Notes
- Non-implementation task (tagged quality, scope:agents) — no tests applicable.
- Scope explicitly states: "No code, no tests."
- Passing through to builder.

[[2026-03-31]] Tue 06:39
## Builder Notes
- Files changed: skills/decision-requests/SKILL.md
- Non-code task: SKILL.md updated with impact_tier field and T3 indefinite blocking
- Changes made:
  1. Added impact_tier row to agent metadata frontmatter table (values: 1/2/3, set by agent)
  2. Added impact_tier: 2 to decision request file format template example
  3. Updated auto-resolution section: T2 (or missing) keeps 5-day timer; T3 blocks indefinitely; T1 note added; missing impact_tier defaults to T2 for backwards compat
- No tests applicable (scope: SKILL.md only, no code)

[[2026-03-31]] Tue 07:23
## Review Evidence
- Scope: skills/decision-requests/SKILL.md only (confirmed via changed files list)
- No tests applicable (task scope explicitly excludes code/tests)
- No ruff applicable (not Python)
- No TestFromAC classes

### AC Compliance

| AC Line | Evidence | Status |
| --- | --- | --- |
| impact_tier field in frontmatter table (values: 1/2/3, set by Agent) | Agent metadata table row present with correct values and "Agent" setter | PASS |
| Missing impact_tier defaults to T2 | "Missing impact_tier defaults to tier 2 for backwards compatibility" in auto-resolution section | PASS |
| T3 does not auto-resolve | "T3 decisions do not auto-resolve. When impact_tier: 3, the planner skips the 5-day timer entirely." | PASS |
| T2 keeps 5-day auto-resolve | "If an impact_tier: 2 decision (or a decision with no impact_tier field) stays approved: false for 5+ days..." | PASS |
| File format template includes impact_tier in agent metadata block | impact_tier: 2 placed after "Agent metadata (do not edit)" in decision request template | PASS |
| Auto-resolution section documents T2 vs T3 differences | Both T2 (5-day) and T3 (indefinite) explicitly documented in resolution workflow | PASS |
| T1 note: autonomous, value exists for completeness, should not appear in practice | "T1 note: impact_tier: 1 outcomes are autonomous...The value 1 exists for completeness but should not appear in practice in decision request files." | PASS |

### Verdict: PASS (.98)

[[2026-03-31]] Tue 07:57
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Task scope is SKILL.md only; copilot-instructions.md just points to the skill, no tier details to add |
| 2 | Docstrings | No | N/A | No Python modules changed (scope: SKILL.md only, no code) |
| 3 | docs/sources/overview.md | Yes | PASS | Already updated with AutoGen Human-in-the-Loop and GitHub Actions environment sources (lines 90-91) |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | PASS | docs/research/impact-tier-decision-requests.md exists and linked from task body |
| 6 | Scratch files | N/A | PASS | No docs/scratch/459-* files found |

### Files Updated
- None (all sources/research docs updated by builder/researcher upstream)

### Scratch Files Cleaned
- None
