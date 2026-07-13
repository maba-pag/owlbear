---
id: 83
title: Add skills-ref dev dependency and pre-commit validation hook
status: archived
priority: medium
created: 2026-03-27 04:56:44.051489+01:00
updated: 2026-03-27 05:24:19.924245+01:00
started: 2026-03-27 05:24:19.924245+01:00
completed: 2026-03-27 05:24:19.924245+01:00
tags:
- phase-1
- scope:skills
- scope:build
- type:build
depends_on:
- 44
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Integrate agentskills.io skills-ref validator as a pre-commit hook.

## Acceptance Criteria
- [ ] Add skills-ref==0.1.1 as a dev dependency via uv add --dev
- [ ] Create scripts/validate-skills.py that calls skills_ref.validate() on all .github/skills/*/SKILL.md, filtering errors for known VS Code extension fields (user-invocable, argument-hint, disable-model-invocation)
- [ ] Add repo: local pre-commit hook in .pre-commit-config.yaml that runs scripts/validate-skills.py
- [ ] All 21 skills pass the filtered validation
- [ ] pre-commit run --all-files exits 0

## Architecture Notes
See docs/research/skills-ref-ci-validation.md for analysis.
The wrapper filters VS Code vendor fields because the spec validator rejects them. When the agentskills spec adds vendor extension support, simplify to direct agentskills validate calls.
