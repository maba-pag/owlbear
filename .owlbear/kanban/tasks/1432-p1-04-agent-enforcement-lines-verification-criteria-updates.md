---
id: 1432
title: 'P1-04: Agent enforcement lines + verification criteria updates'
status: review
priority: needed
created: 2026-05-08T01:00:48.495798+00:00
updated: 2026-05-08T13:14:33.456493+00:00
tags:
- phase-1
- scope:shared
- ideation
- ux
- agent
parent: 1428
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Add one critical_rule enforcement line to each user-facing agent file and update verification criteria in both workflow skills to check "explains purpose" instead of "names component."

Brief: see parent #1428. Full brief at `.owlbear/briefs/draft-ideation-ux/brief.md`.

## Scope

**In:** 4 files, light edits:
1. `share/agents/ideation-mediator.agent.md` — add 1 critical_rule line
2. `share/agents/ideation-discoverer.agent.md` — add 1 critical_rule line
3. `share/skills/w-ideation-mediation/SKILL.md` — update verification criteria
4. `share/skills/w-ideation-discovery/SKILL.md` — update verification criteria

**Out:** Content creation (#1429). Directive rewrites (#1430, #1431). Panel cleanup (#1433).

## Acceptance Criteria

- [ ] `share/agents/ideation-mediator.agent.md` contains new critical_rule: "Apply user-facing vocabulary from h-ideation § Communication Patterns. Internal names appear with explanatory context. Never announce internal evaluations — narrate only results."
- [ ] `share/agents/ideation-discoverer.agent.md` contains equivalent critical_rule (same text or contextually appropriate variant)
- [ ] Verification criteria in w-ideation-mediation/SKILL.md updated: checks that agent "explains purpose of each review" not "names the panelist agent"
- [ ] Verification criteria in w-ideation-discovery/SKILL.md updated: checks that agent "explains what completed and what's next" not "names the handoff target"
- [ ] Critical_rule lines are placed inside existing `<critical_rules>` sections (not duplicated or misplaced)
- [ ] No other changes to agent files beyond the one added line each
\n\n## CORRECTION (from mediation review)\n\nThe discoverer agent has an EXISTING handoff critical_rule that says something like "End Phase 1 by naming @ideation-mediator." This needs to be REWRITTEN (not just a new line added). The AC item about "No other changes beyond the one added line each" is incorrect for the discoverer — it has 2 changes: add new vocabulary rule + rewrite existing handoff rule.\n\nRevised AC for discoverer:\n- [ ] Existing handoff critical_rule in discoverer rewritten to purpose-framed language (no @handle naming)\n- [ ] New vocabulary enforcement critical_rule added alongside
[[2026-05-08]]


## Architecture Review

### AC Refinement (supersedes original AC + CORRECTION appendix)

**Original AC problems found:**
1. **AC3 phantom target** — "Verification criteria in w-ideation-mediation/SKILL.md updated" says to change from "names the panelist agent" but NO such text exists in the mediation verification checklist (lines 149–163). Builder would have no target to modify.
2. **AC4 scope conflict** — #1431 (approved, in `todo`) already claims line 142 of w-ideation-discovery/SKILL.md in its builder guidance + AC5 grep check. Two tasks editing the same line = merge conflict.
3. **AC6 vs CORRECTION** — "No other changes beyond one added line each" contradicts CORRECTION which correctly notes discoverer needs 2 changes.
4. **CORRECTION appendix** has escaped `\\n` formatting, not integrated into main AC.

**Revised Scope (3 files):**
1. `share/agents/ideation-mediator.agent.md` — add 1 critical_rule line
2. `share/agents/ideation-discoverer.agent.md` — add new vocabulary critical_rule + rewrite existing handoff critical_rule (line 39)
3. `share/skills/w-ideation-mediation/SKILL.md` — add 1 new verification criterion

**Dropped:** `share/skills/w-ideation-discovery/SKILL.md` — entirely handled by #1431 (verified: its builder guidance + AC5 grep covers line 142 update).

### Revised AC (authoritative — ignore original AC above)

- [ ] `share/agents/ideation-mediator.agent.md` `<critical_rules>` section contains new line: "Apply user-facing vocabulary from h-ideation § Communication Patterns. Internal names appear with explanatory context. Never announce internal evaluations — narrate only results." (td:0)
- [ ] `share/agents/ideation-discoverer.agent.md` `<critical_rules>` section contains new vocabulary enforcement line (same text or contextually appropriate variant) (td:0)
- [ ] Existing discoverer critical_rule (line 39: "Handoff is explicit. End Phase 1 by naming `@ideation-mediator` and pointing to the artifact paths it should start from.") rewritten to purpose-framed language — instructs agent to explain what's completed and what opens next, without naming `@ideation-mediator` as the handle. Internal routing references elsewhere in the file (output_format, boundaries) are unchanged — they're agent-internal mechanics, not user-facing narration. (td:0)
- [ ] New verification criterion added to `share/skills/w-ideation-mediation/SKILL.md` verification checklist (line 149+): panelist reviews are introduced by purpose and angle (what's being checked and why), not by raw agent name. (td:0)
- [ ] All critical_rule edits are inside existing `<critical_rules>` sections (not duplicated or misplaced) (td:0)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | 3 files, single concern: enforce user-facing vocabulary rules |
| Interface clarity | PASS | Revised AC specifies exact line targets and placement constraints |
| Dependency correctness | PASS | Removed stale dep #1429 (archived). No dep on #1430/#1431 needed — tasks touch different sections of different files |
| Module layering | N/A | Markdown agent/skill files only |
| TDD compliance | PASS | Non-implementation task (prose edits). Added `agent` pass-through tag for test-writer skip |
| KISS/YAGNI | PASS | Minimal scope: 2 new critical_rule lines + 1 rewrite + 1 new verification criterion |
| Premise challenge | PASS | Jargon leakage is documented in parent brief with before/after pairs. Communication Patterns section (h-ideation line 182+) provides vocabulary source |
| Pattern consistency | PASS | Follows sibling tasks' approach (#1430, #1431 use same co-located annotation pattern) |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Ideation/UX only |

### Builder Guidance
- **Mediator agent:** Insert new critical_rule line into `<critical_rules>` (after line 56 is fine — near the write/transparency rules). Exact text in AC.
- **Discoverer agent:** (1) Rewrite line 39 from "End Phase 1 by naming `@ideation-mediator`..." to purpose-framed language (e.g., "End Phase 1 by explaining what was discovered and what opens next, then pointing to the artifact paths for Phase 2."). (2) Add new vocabulary enforcement line alongside. Do NOT touch lines 60, 68, 81, 98 — those are internal routing, not user-facing narration.
- **Mediation verification:** Add a new checklist item (don't modify existing items). Example: `- [ ] Panelist reviews are introduced by purpose and angle, not raw agent name.`
- **Vocabulary source:** h-ideation/SKILL.md line 182+ (Communication Patterns section, delivered by #1429).

### Test Depth
- All AC lines: td:0 (markdown prose edits, grep-verified)
- Max depth: 0
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — all td:0

### Verdict: APPROVE
### Action Taken: Removed stale dep #1429 (archived). Dropped discovery SKILL from scope (owned by #1431). Added `agent` pass-through tag. Revised AC to fix phantom target, scope conflict, and CORRECTION integration. Advancing to todo.
[[2026-05-08]]
Architecture review complete. REFINED + APPROVED. Fixed 4 AC problems: (1) AC3 phantom target — mediation verification checklist has no "names the panelist agent" text to update; changed to "add new criterion"; (2) AC4 scope conflict with #1431 — dropped discovery SKILL from scope; (3) AC6 contradicted CORRECTION — removed; (4) integrated CORRECTION into revised AC. Scope reduced from 4 to 3 files. Removed stale dep #1429 (archived). Added `agent` pass-through tag. All td:0 — test-writer SKIP. Challenger SKIPPED per td:0 rule.
[[2026-05-08]]
## Test-Writer Notes
- Non-implementation task (tagged `agent`) — all AC lines are (td:0) — no tests applicable.
- Scope: prose edits to agent/skill Markdown files (critical_rule additions + 1 verification criterion).
- Passing through to builder.
[[2026-05-08]]
## Builder Notes
- Implementation: updated `share/agents/ideation-mediator.agent.md`, `share/agents/ideation-discoverer.agent.md`, and `share/skills/w-ideation-mediation/SKILL.md`.
- AC alignment:
  - Added user-facing vocabulary critical_rule line inside existing `<critical_rules>` in mediator agent.
  - Added equivalent user-facing vocabulary critical_rule line inside existing `<critical_rules>` in discoverer agent.
  - Rewrote discoverer handoff critical_rule to purpose-framed language (no `@ideation-mediator` handle naming).
  - Added mediation verification checklist criterion: panelist reviews introduced by purpose/angle, not raw agent name.
- Scope control: no edits outside revised 3-file architecture scope; all critical_rule changes placed in existing sections.
- Quality evidence (td:0 markdown-only task): quality-runner lint pass using markdownlint on all changed files (clean, no violations), tests not applicable.
- Commit: `6b66937a` (`chore: enforce ideation user-facing vocabulary rules (#1432, builder)`).