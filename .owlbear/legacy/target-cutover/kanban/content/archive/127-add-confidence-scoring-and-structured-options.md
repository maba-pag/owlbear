---
id: 127
title: Add confidence scoring and structured options rules to 
  copilot-instructions.md
status: archived
priority: medium
created: 2026-03-29 07:03:49.567621+02:00
updated: 2026-03-29 10:21:27.116973+02:00
started: 2026-03-29 07:29:09.345736+02:00
completed: 2026-03-29 10:21:22.309724+02:00
tags:
- phase-1
- scope:docs
- type:docs
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] copilot-instructions.md Process Habits section includes: State confidence and present structured options at every decision point (replaces old askQuestions liberally guidance)
- [ ] copilot-instructions.md includes a general rule: agents should state confidence (0.0-1.0) when deriving decisions from source material, not only in verdicts
- [ ] Rule references the (bp:)/(rec:) annotation convention from the decision-requests skill
- [ ] Rule does NOT reference askQuestions or any specific tool
- [ ] Existing confidence threshold table in agent-common.instructions.md (reviewer >= .90, auditor >= .95) remains the authority for verdict thresholds

See docs/research/askquestions-cleanup-scope.md section 3.4 for the gap analysis.
Related: #125 (parent research task), #126 (behavioral reference rewrite)

[[2026-03-29]] Sun 07:28
## Research
Research validated (.90 confidence). See docs/research/confidence-scoring-rules.md for full analysis.

Key findings:
- Gap confirmed: no general confidence rule in copilot-instructions.md Process Habits
- Two bullets needed: (1) State confidence at decision points with (bp:)/(rec:) convention, (2) Cross-reference to agent-common verdict thresholds
- Aligns with gstack structured question protocol and Anthropic confidence calibration guidance
- Zero risk of tool-name coupling (no askQuestions reference)
- No additional follow-up tasks needed; AC is complete and actionable

[[2026-03-29]] Sun 07:55
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Process Habits includes confidence+structured options bullet | Clear, verifiable by grep | Keep |
| General rule: state confidence 0.0-1.0 | Clear, verifiable by grep | Keep |
| References (bp:)/(rec:) from decision-requests skill | Clear, verifiable; convention confirmed in SKILL.md L30 | Keep |
| Does NOT reference askQuestions | Clear negative check, verifiable by grep | Keep |
| agent-common threshold table remains authority | Clear, cross-ref verified at agent-common L270-L280 | Keep |

### Architecture Notes
Docs-only task targeting .github/copilot-instructions.md Process Habits section. Two new bullets between existing items. Research doc (docs/research/confidence-scoring-rules.md) provides exact wording. No code, no security surface, no layering concerns. Single domain (scope:docs). TDD not applicable for docs-only changes. Sibling task #126 (behavioral reference rewrite) is independent, no ordering constraint.

### Dependencies
- Verified: #125 (parent research) complete
- Related: #126 (sibling, independent, no blocking dependency)
- Related: #101 (YAML tool removal, out of scope)

[[2026-03-29]] Sun 08:34
## Test-Writer Notes
- Non-implementation task (tagged type:docs, scope:docs) - no tests applicable.
- Passing through to builder.

[[2026-03-29]] Sun 08:50
## Builder Notes\n- Files changed: .github/copilot-instructions.md (+2 bullets in Process Habits)\n- Tests: N/A (docs-only task)\n- Lint: N/A\n- Evidence: AC verified by grep - confidence scoring bullet present, (bp:)/(rec:) referenced, no askQuestions, agent-common deferred for thresholds\n- Fixes applied: None

[[2026-03-29]] Sun 09:47
## Docs Gate

Checklist:
1. .github/copilot-instructions.md - Applies - Pass - Both bullets verified in Process Habits: confidence scoring rule with (bp:)/(rec:) and agent-common cross-ref. All 5 AC items confirmed.
2. Docstrings - No - N/A - Docs-only task, no Python modules changed.
3. sources/overview.md - No - N/A - gstack already cited; Anthropic guidance is general, no URL.
4. README.md - No - N/A - No CLI changes.
5. Research doc - Yes - Pass - docs/research/confidence-scoring-rules.md exists and linked in task body.

Files Updated: None (builder committed .github/copilot-instructions.md)
Scratch Files: None found
