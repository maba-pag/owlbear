---
id: 464
title: Update dispatch-planning Recipe 0 to skip auto-resolve for impact_tier=3
status: archived
priority: medium
created: 2026-03-31 03:54:57.049046+02:00
updated: 2026-03-31 22:33:33.160235+02:00
started: 2026-03-31 22:33:32.665506+02:00
completed: 2026-03-31 22:33:32.665506+02:00
tags:
- process
- scope:agents
- quality
depends_on:
- 459
class: standard
archival_reason: completed
archival_refs: []
---

Recipe 0 in dispatch-planning skill auto-resolves pending decisions after 5 days. With impact_tier (from #459), T3 decisions must NOT auto-resolve. Update Recipe 0 logic: check impact_tier field, skip 5-day timer when impact_tier=3, report T3 pending count separately in JSON output. See docs/research/recipe0-tier-aware-auto-resolve.md.

Scope: skills/dispatch-planning/SKILL.md only (3 sections: Recipe 0 prose, Step 1 paragraph, Step 3 JSON format). No code, no tests.
Depends on: #459 (impact_tier field in decision-requests skill).

AC:
- [ ] Recipe 0 prose (lines ~58-71): add conditional before 5-day auto-resolve that reads impact_tier from decision request YAML frontmatter
- [ ] impact_tier=3 decisions skip 5-day auto-resolve timer (remain pending indefinitely until user resolves)
- [ ] Missing impact_tier field defaults to tier 2 (backwards compat: existing files keep current 5-day auto-resolve behavior)
- [ ] impact_tier=1 in a pending file (should not exist) is treated as tier 2
- [ ] Action requests (request_type: action) are unaffected by impact_tier and keep their existing 5-day auto-resolve
- [ ] Step 1 paragraph (~line 159): note that Recipe 0 now distinguishes T2 (auto-resolvable) from T3 (permanently pending)
- [ ] Step 3 JSON format (~line 290+): add pending field with flat keys: decisions_t2 (int), decisions_t3 (int), actions (int)
- [ ] No new files created; no code changes

[[2026-03-31]] Tue 04:56
## Architecture Review
**Verdict:** Approve

### AC Assessment

AC Line: Recipe 0 checks impact_tier -- Assessment: Precise after refinement -- Action: Specified exact lines and frontmatter field
AC Line: T3 skips 5-day auto-resolve -- Assessment: Clear pass/fail -- Action: None
AC Line: Missing impact_tier defaults to T2 -- Assessment: Backwards compat verified -- Action: None
AC Line: T1 in pending treated as T2 -- Assessment: Edge case covered -- Action: Added during refinement
AC Line: Action requests unaffected -- Assessment: Scope boundary clarified -- Action: Added during refinement
AC Line: Step 1 paragraph update -- Assessment: Specific section cited -- Action: Refined from vague 'updated prose'
AC Line: Step 3 JSON flat keys -- Assessment: Exact key names specified -- Action: Refined from vague 'distinguishes T2 vs T3'
AC Line: No new files -- Assessment: Scope guard -- Action: None

### Architecture Notes
Single-file change (skills/dispatch-planning/SKILL.md). Recipe 0 already reads decision request frontmatter; adding impact_tier check is a minimal conditional extension. Flat JSON keys (decisions_t2, decisions_t3, actions) follow KISS and match existing JSON output style in Step 3. No module layering concerns (skill prose only). No security surface. Dependency on #459 added (was missing).

### Changes Made
- Added depends_on: 459 via --add-dep
- Refined 5 AC lines to be section-specific and include exact key names
- Added 3 new AC lines: T1 edge case, action request exclusion, no-new-files guard

### Dependencies
- Added: #459 (impact_tier field in decision-requests skill) -- currently at todo

[[2026-03-31]] Tue 11:37
## Test-Writer Notes
- Non-implementation task (tagged quality) -- no tests applicable.
- Scope is skills/dispatch-planning/SKILL.md prose only; AC explicitly states no code changes.
- Passing through to builder.

[[2026-03-31]] Tue 12:40
## Builder Notes
- Files changed: skills/dispatch-planning/SKILL.md
- Non-code task: SKILL.md prose updated per AC
- Changes made:
  1. Recipe 0 prose: added impact_tier conditional before 5-day auto-resolve; T3 skips timer; missing/T1 defaults to T2; action requests unaffected
  2. Step 1 paragraph: added sentence noting Recipe 0 distinguishes T2 (auto-resolvable) from T3 (permanently pending)
  3. Step 3 JSON format: updated pending field to flat keys decisions_t2/decisions_t3/actions in both examples, good-example, and field description
- No tests applicable (scope: SKILL.md prose only, no code)

[[2026-03-31]] Tue 15:59
## Review Evidence

Non-code prose task. Only file changed: skills/dispatch-planning/SKILL.md.

### AC Compliance (8/8 PASS)

All 8 AC lines verified present in SKILL.md.

### Defect: Self-Contradictory Empty-Board Example

Line 364: `- Fields: dispatch, gate_warnings, and pending (all required)`
Line 365: `- Empty dispatch array is fine: {"dispatch":[],"gate_warnings":[]}`

Builder added `(all required)` to line 364 and updated all other JSON examples to include `pending`, but did NOT update line 365. Direct contradiction: the rule says all 3 fields required; the example omits pending. An LLM planner following line 365 literally would omit pending on empty-board cycles.

Fix: line 365 must read:
`{"dispatch":[],"gate_warnings":[],"pending":{"decisions_t2":0,"decisions_t3":0,"actions":0}}`

### Verdict: FAIL - confidence 0.87

[[2026-03-31]] Tue 16:51
## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL was about prose quality (self-contradictory empty-board example in SKILL.md), not missing tests.
- Existing tests preserved (non-implementation task -- no tests applicable).
- Builder will address reviewer finding: add pending field to empty-board example on line 365.

[[2026-03-31]] Tue 17:18
## Builder Notes (retry)
- Files changed: skills/dispatch-planning/SKILL.md
- Fix: line 365 empty-board example updated to include pending field
- Resolves reviewer FAIL: rule says pending is required but example omitted it
- No tests applicable (prose-only task)

[[2026-03-31]] Tue 21:25
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Skill-internal change; copilot-instructions.md has no Recipe 0 or auto-resolve references |
| 2 | Docstrings | No | N/A | No Python modules changed; scope is SKILL.md prose only |
| 3 | docs/sources/overview.md | No | N/A | GH Actions and AutoGen cited as validation precedent only, not adopted patterns |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Pass | docs/research/recipe0-tier-aware-auto-resolve.md exists and linked from task body; no follow-up tasks needed per doc section 5 |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/464-* files found)
