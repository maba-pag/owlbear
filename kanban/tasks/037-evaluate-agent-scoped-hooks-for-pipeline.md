---
id: 37
title: Evaluate agent-scoped hooks for pipeline enforcement
status: ideation
priority: nice-to-have
created: 2026-03-26T18:45:09.795589+01:00
updated: 2026-03-30T20:36:05.740703+02:00
tags:
    - research
    - phase-1
    - scope:agents
    - hooks
blocked: true
block_reason: 'Waiting on user: task body still has no scoped AC — previous researcher refused for same reason on 2026-03-27'
class: standard
---

[[2026-03-27]] Fri 04:35
## Research
Refused dispatch: task body is empty (no AC, no context). Title is suggestive but body must provide:
- What specific hooks are being evaluated (pre-commit, lifecycle, custom)?
- What pipeline rules need enforcement (gate ordering, claim protocol, commit discipline)?
- What problem prompted this task (enforcement gaps observed)?

Please add scoped body content with acceptance criteria before redispatch.

[[2026-03-30]] Mon 20:36
## Research (2nd dispatch)\nRefused again: body still contains only the prior refusal note, no AC or scoped context has been added.\n\nTo unblock, add to the task body:\n1. The specific enforcement gaps observed (what went wrong?)\n2. Which pipeline rules need enforcement (gate ordering? claim protocol? commit discipline?)\n3. What hooks are being considered (pre-commit, lifecycle, custom agent hooks?)\n4. Concrete acceptance criteria for the research output.
