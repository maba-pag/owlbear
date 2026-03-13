---
id: 728
title: Add structured handoff template to agent-common.instructions.md
status: in-progress
priority: nice-to-have
created: 2026-03-10T19:09:53.4156483+01:00
updated: 2026-03-13T20:33:07.033982+01:00
tags:
    - scope:copilot
    - agent
    - phase-research
class: standard
---

Add a what-failed tracking field to the handoff template in agent-common.instructions.md section 'Task coordination > Handoff / blocked'. Current template has 'Current state / Open questions / Next step'; add 'what-failed' tracking. See docs/research/claude-code-tips.md section 3a for context.

## Acceptance Criteria

- [ ] The `## Handoff` note template in the `### Handoff / blocked` section of `.github/instructions/agent-common.instructions.md` (around L36-41) includes a `- What failed:` bullet between `- Current state:` and `- Open questions:`
- [ ] The bullet's purpose is self-evident from the label (no additional prose required; the field name 'What failed' is sufficient documentation per AC2)
- [ ] No other sections of agent-common.instructions.md are changed

## Architecture Notes

- File: `.github/instructions/agent-common.instructions.md`
- Section: `### Handoff / blocked` (L32-41)
- Pattern: existing bullet-list template in a fenced PowerShell block
- Insert `- What failed:` as a new bullet in the `--note` template string

[[2026-03-13]] Fri 20:22
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Handoff template includes What failed bullet | Clear, verifiable  builder checks L36-41 | Keep |
| Field purpose self-evident from label | Clear  no ambiguity | Keep |
| No other sections changed | Scope constraint, verifiable | Keep |

### Architecture Notes
Surgical docs-only change. Existing template at L36-41 uses bullet list in a fenced PS block. The new bullet slots in naturally. No code, no test task needed (instructions file only). Research justification in docs/research/claude-code-tips.md section 3a.

### Dependencies
- None

[[2026-03-13]] Fri 20:32
## Test-Writer Notes
- Non-implementation task (tagged scope:copilot, agent, phase-research) -- no tests applicable.
- AC targets .github/instructions/agent-common.instructions.md only (docs/config change).
- Passing through to builder.
