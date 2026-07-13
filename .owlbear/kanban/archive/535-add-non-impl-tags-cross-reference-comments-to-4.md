---
id: 535
title: Add NON_IMPL_TAGS cross-reference comments to 4 skill/prompt files
status: archived
priority: medium
created: 2026-03-30 20:39:07.921439+02:00
updated: 2026-04-02 05:01:24.010735+02:00
started: 2026-04-02 04:16:07.962537+02:00
completed: 2026-04-02 04:16:07.962537+02:00
tags:
- scope:agents
- quality
- type:config
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria
- [ ] `skills/dispatch-planning/SKILL.md` has an HTML `<!-- NON_IMPL_TAGS: ... -->` comment near the agent dispatch table (L17-28 area) declaring it the authoritative list and enumerating all 3 secondary file paths
- [ ] `skills/tdd-red/SKILL.md` has an HTML `<!-- NON_IMPL_TAGS: ... -->` comment directly above the tag list at Step 1 item 3 (L26) pointing to `skills/dispatch-planning/SKILL.md` as authoritative
- [ ] `.github/prompts/agent-audit.prompt.md` has an HTML `<!-- NON_IMPL_TAGS: ... -->` comment directly above the non-impl paragraph (~L107) pointing to `skills/dispatch-planning/SKILL.md` as authoritative
- [ ] `skills/arch-review/SKILL.md` has an HTML `<!-- NON_IMPL_TAGS: ... -->` comment directly above the non-impl tagging note (~L147) pointing to `skills/dispatch-planning/SKILL.md` as authoritative
- [ ] Each HTML comment includes the keyword `NON_IMPL_TAGS` for grep-based discovery
- [ ] The existing PS code comment `# NON_IMPL_TAGS` at dispatch-planning SKILL.md L123 remains and is consistent with the new HTML comment
- [ ] The dispatch-planning authoritative HTML comment lists exactly 3 secondary locations: tdd-red SKILL.md, agent-audit.prompt.md, arch-review SKILL.md

## Context
See docs/research/non-impl-tag-cross-references.md for the recommended HTML comment pattern (section 3.3).
Research identified 3 files; architect review found a 4th: `skills/arch-review/SKILL.md` L147-150.
Merged from #218 (original research task).

## Implementation Pattern
At each secondary location, add directly above the tag list:
```
<!-- NON_IMPL_TAGS: Authoritative list at skills/dispatch-planning/SKILL.md
     (agent dispatch table). Update there first, then sync here. -->
```

At the authoritative location (dispatch-planning SKILL.md), add near the dispatch table:
```
<!-- NON_IMPL_TAGS: This is the authoritative list. Secondary copies:
     skills/tdd-red/SKILL.md (Step 1 item 3),
     skills/arch-review/SKILL.md (non-impl tagging note),
     .github/prompts/agent-audit.prompt.md (Non-impl paragraph). -->
```

[[2026-04-01]] Wed 12:59
## Architecture Review
Verdict: APPROVED (merged from #218)
DR Verification: N/A (T1 autonomous config task, single clear recommendation at .90 confidence)

### AC Assessment
AC1 (cross-ref comments): Research found 3 files. Architect found 4th (arch-review SKILL.md L147-150). Refined to 4 files.
AC2 (single authoritative location): Achievable via grep keyword. Kept, clarified in implementation pattern.

### Architecture Notes
Non-impl config task (markdown-only). Tags include quality and type:config for pass-through.
Approach: HTML comments with NON_IMPL_TAGS keyword (KISS). Follows existing PS script comment pattern at dispatch-planning L123.
4 files: dispatch-planning SKILL.md (authoritative), tdd-red SKILL.md, agent-audit.prompt.md, arch-review SKILL.md (secondaries).
No security surface. No new codepaths.

### Changes Made
Merged #329 (surviving) with #218 (deleted). Same scope, #329 had better AC structure.
Refined body: added 4th file, implementation pattern, fixed file count. Updated title.

### Dependencies
None required.

### Challenge Results
Challenge: FALLBACK (Challenger subagent network error). Architect analysis stands.

[[2026-04-01]] Wed 15:48
## Test-Writer Notes
- Non-implementation task (tagged type:config, quality) — no tests applicable.
- AC deliverables: skills/dispatch-planning/SKILL.md, skills/tdd-red/SKILL.md, .github/prompts/agent-audit.prompt.md, skills/arch-review/SKILL.md (HTML comment additions only)
- No Python implementation intent found in AC.
- Passing through to builder.

[[2026-04-01]] Wed 15:49
## Test-Writer Notes
- Non-implementation task (tagged type:config, quality) no tests applicable.
- AC deliverables: skills/dispatch-planning/SKILL.md, skills/tdd-red/SKILL.md, .github/prompts/agent-audit.prompt.md, skills/arch-review/SKILL.md (HTML comment additions only)
- No Python implementation intent found in AC.
- Passing through to builder.

[[2026-04-02]] Thu 04:03
## Docs Gate
All 7 AC items verified PASS. No docs impact: config-only task (HTML comments only). No Python, no CLI, no behavior change. Research doc exists at docs/research/non-impl-tag-cross-references.md. No scratch files. No files updated.

[[2026-04-02]] Thu 04:16
## Audit
### AC Verification
| AC | Evidence | Status |
|---|---|---|
| AC1: dispatch-planning authoritative comment | L17-18 HTML comment with 3 secondary paths | PASS |
| AC2: tdd-red secondary comment | L27-28 above Step 1 item 3 | PASS |
| AC3: agent-audit.prompt.md secondary comment | L107 above non-impl paragraph | PASS |
| AC4: arch-review secondary comment | L147-148 above non-impl tagging note | PASS |
| AC5: keyword NON_IMPL_TAGS in all comments | grep confirms 5 occurrences (4 HTML + 1 PS) | PASS |
| AC6: PS code comment at dispatch-planning L127 | Exists, consistent with HTML comment | PASS |
| AC7: authoritative lists exactly 3 secondaries | tdd-red, arch-review, agent-audit confirmed | PASS |

### Test Results
- pytest: 2275 passed, 348 failed (pre-existing, none in task scope), 8 skipped
- ruff: 2 pre-existing violations in unrelated test files

### AC Quality: 5
AC was precise (7 items, exact file/line targets, implementation pattern provided). Clean implementation path.

### Reviewer Evidence
Missing Review Evidence section in task body. Writer Docs Gate present.

### Deduction breakdown
- Start: 1.00
- Missing reviewer evidence section: -.02
### Confidence: .98
### Action: archive
