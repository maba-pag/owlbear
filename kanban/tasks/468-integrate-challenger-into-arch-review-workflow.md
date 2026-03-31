---
id: 468
title: Integrate Challenger into arch-review workflow (Step 3.5)
status: ideation
priority: needed
created: 2026-03-31T05:04:52.5039779+02:00
updated: 2026-03-31T05:04:52.5039779+02:00
tags:
    - scope:agents
    - phase-2
depends_on:
    - 467
class: standard
---

Wire Challenger invocation into the architect's arch-review skill per docs/research/challenger-subagent-design.md S3e-f.

AC:
- [ ] architect.agent.md frontmatter agents: changed from [] to [challenger]
- [ ] arch-review SKILL.md has new Step 3.5: Challenge proposed verdict
- [ ] Step 3.5 is mandatory for APPROVE verdicts, optional for REFINE
- [ ] Integration protocol: proceed (confidence>=.80) / reconsider (<.80) / block in body
- [ ] Architecture Review body section includes Challenge Results subsection
- [ ] Architect retains final authority -- Challenger advises, never decides
- [ ] Sequential fallback: if Challenger subagent errors, architect proceeds without challenge and notes fallback in body
