---
id: 126
title: Rewrite askQuestions behavioral references to tool-agnostic language
status: archived
priority: medium
created: 2026-03-29 07:03:36.736260+02:00
updated: 2026-03-29 10:38:13.840189+02:00
started: 2026-03-29 10:38:07.917347+02:00
completed: 2026-03-29 10:38:07.917347+02:00
tags:
- phase-1
- scope:docs
- scope:agents
- type:docs
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] planner.agent.md: 3 occurrences of askQuestions replaced with behavior-focused language (never prompt the user for decisions)
- [ ] agent-audit.prompt.md: 3 occurrences rewritten to present structured options / state confidence (preserve (bp:)/(rec:) and confidence score conventions)
- [ ] project-definition/SKILL.md (both skills/ and .github/skills/ mirrors): 5 occurrences each rewritten, including the askQuestions() code example replaced with a generic present options example
- [ ] research-workflow/SKILL.md (both mirrors): 1 occurrence each replaced with present structured options to the user
- [ ] agent-common.instructions.md: instead of askQuestions phrase removed, decision-requests guidance stands alone
- [ ] grep verify: no remaining askQuestions references in .agent.md behavioral text, .prompt.md, SKILL.md, or .instructions.md files that imply it is a tool available to agents
- [ ] All confidence score, (bp:)/(rec:), and structured option patterns preserved
- [ ] Research docs (docs/research/*.md) NOT modified (historical records)

See docs/research/askquestions-cleanup-scope.md section 3.3 for the replacement language matrix.
Related: #101 (YAML tool removal), #125 (parent research task)

[[2026-03-29]] Sun 07:24
## Research
Validated parent research (#125). All AC counts confirmed against live files. Replacement language matrix in section 3.3 is sound. Highest-risk edit: askQuestions() code example in project-definition SKILL.md needs full rewrite as generic present-options example. No additional follow-up tasks needed.

[[2026-03-29]] Sun 08:34
## Test-Writer Notes
- Non-implementation task (tagged type:docs) â€” no tests applicable.
- Passing through to builder.

[[2026-03-29]] Sun 08:59
## Builder Notes\n- Files changed: agents/planner.agent.md, instructions/agent-common.instructions.md, .github/prompts/agent-audit.prompt.md, .github/skills/project-definition/SKILL.md, skills/project-definition/SKILL.md, .github/skills/research-workflow/SKILL.md, skills/research-workflow/SKILL.md\n- Non-code task â€” no tests or coverage applicable\n- Lint: N/A (docs-only)\n- Evidence: grep verified zero remaining askQuestions in agents/, instructions/, .github/prompts/, skills/, .github/skills/\n- Commit: 22f84da â€” 7 files, 54 ins / 54 del\n- Fixes applied: All 5 AC items â€” planner.agent.md (3 refs), agent-audit.prompt.md (3 refs), project-definition/SKILL.md both mirrors (5 refs each incl. code example rewrite), research-workflow/SKILL.md both mirrors (1 ref each), agent-common.instructions.md (1 ref)

[[2026-03-29]] Sun 09:34
## Review Evidence

**Reviewer:** reviewer | **Task:** #126 — Rewrite askQuestions behavioral references to tool-agnostic language | **Date:** 2026-03-29

### Type: docs-only (type:docs, no tests applicable)

### Commit Verified
- Commit `22f84da` — "docs: rewrite askQuestions behavioral references to tool-agnostic language (#126, builder)"
- 7 files, 54 ins / 54 del — pure rewrite, no net content additions

### Grep Verify (AC item 6)
- .agent.md files: 0 matches for askQuestions
- .prompt.md files: 0 matches for askQuestions
- SKILL.md files: 0 matches for askQuestions
- .instructions.md files: 0 matches for askQuestions
- .github/copilot-instructions.md: 0 matches

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| planner.agent.md: 3 occurrences replaced | L30: "never prompt the user for decisions"; L77: "Never prompt the user for decisions"; L85: "You are about to prompt the user for decisions (you don't interact with the user)" — no askQuestions present | PASS |
| agent-audit.prompt.md: 3 occurrences, (bp:)/(rec:) and confidence preserved | L303: "State confidence and present structured options... Include (bp:) for best practice and (rec:) for recommendation"; L304: "Show Confidence scores... prefix each option label with a confidence score" | PASS |
| project-definition/SKILL.md both mirrors: 5 occurrences each + code example rewritten | Code example replaced with generic "present options" block using confidence scores (.75/.60/.40); "present structured options to the user" appears throughout; both mirrors are identical | PASS |
| research-workflow/SKILL.md both mirrors: 1 occurrence each | L48 in both mirrors: "Present structured options to the user (what aspects? what decision? what constraints?)" | PASS |
| agent-common.instructions.md: instead-of-askQuestions phrase removed | grep confirmed 0 matches; Defer-to-user section reads cleanly with decision-requests guidance standing alone | PASS |
| Grep verify: no remaining references in behavioral files | All behavioral file types: 0 matches. Only docs/research/*.md, docs/sources/, and kanban task bodies retain historical references — none imply tool availability | PASS |
| Confidence score, (bp:)/(rec:), structured option patterns preserved | agent-audit.prompt.md L303-304 explicitly calls for (bp:)/(rec:) and confidence scores; project-definition code example uses .75/.60/.40 scores with Recommendation block | PASS |
| Research docs (docs/research/*.md) NOT modified | docs/research/askquestions-cleanup-scope.md and confidence-scoring-rules.md still contain historical askQuestions references; not in commit 22f84da file list | PASS |

### Verdict: PASS — confidence .96

All 8 AC items verified with specific file/line evidence. Replacement language is consistent with the research matrix (§3.3). No remaining behavioral references. Both mirrors match. Conventions fully preserved.

[[2026-03-29]] Sun 10:37
## Audit
### AC Verification
All 8 AC items PASS. Grep: 0 askQuestions in behavioral files. planner.agent.md L30/L77/L85 rewritten. project-definition code example uses .75/.60/.40 confidence scores. Both mirrors identical. Research docs untouched. Conventions preserved.
### Test Results
- pytest: 725 passed, 81 failed (all pre-existing)
- ruff: N/A (docs-only)
### AC Quality: 4/5
AC was specific with exact file/count targets. Minor gap: no mirror sync risk flag.
### Confidence: .97
### Action: archive
