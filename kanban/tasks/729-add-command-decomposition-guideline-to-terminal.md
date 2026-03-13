---
id: 729
title: Add command decomposition guideline to Terminal discipline
status: in-progress
priority: nice-to-have
created: 2026-03-10T19:09:59.1137219+01:00
updated: 2026-03-13T20:45:11.9327799+01:00
tags:
    - scope:copilot
    - docs
    - phase-research
class: standard
---

Add a command decomposition bullet to agent-common.instructions.md section 'Terminal discipline'. AC: (1) New bullet point in Terminal discipline using bold-header format matching existing bullets (e.g. '**Command decomposition.**'); (2) Body text advises breaking complex multi-step operations into separate simple terminal calls rather than long chained pipelines; (3) Rationale mentions independent reviewability and reduced approval friction; (4) Does NOT contradict the 'Chain with ;' bullet -- clarify that ;-chaining applies to closely related commands in one logical operation, while decomposition separates distinct logical steps.

[[2026-03-13]] Fri 20:23
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| (1) Bold-header bullet in Terminal discipline | Clear, matches existing format | Keep |
| (2) Advises decomposition of complex multi-step ops | Precise - builder knows what content to write | Keep |
| (3) Rationale: reviewability + approval friction | Clear motivation for the guideline | Keep |
| (4) No contradiction with 'Chain with ;' | Addresses the tension explicitly | Keep (added by architect) |

### Architecture Notes
Existing Terminal discipline section (agent-common.instructions.md L130-142) has 4 bullets in bold-header format. New bullet slots in naturally. The 'Chain with ;' bullet (L139) is syntax guidance (PS 5.1 compat); decomposition is scope guidance (when to use separate tool calls). AC (4) ensures builder addresses this distinction.

Docs-only task -- no test task needed, no .py changes, no failure modes.

### Changes Made
- Refined AC body: added format requirement (bold-header), distinction from ;-chaining, approval friction rationale

### Dependencies
- None

[[2026-03-13]] Fri 20:44
## Test-Writer Notes
Non-implementation task (docs-only, tagged docs). No .py source changes, no testable code. Passing through to builder.

-t
