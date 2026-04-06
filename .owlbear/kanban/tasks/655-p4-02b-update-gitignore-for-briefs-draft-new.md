---
id: 655
title: 'P4-02b: Update .gitignore for briefs draft-new/ pattern'
status: backlog
priority: needed
created: 2026-04-06T07:17:22.9176335+02:00
updated: 2026-04-06T15:01:06.8045389+02:00
tags:
    - phase-4
    - ' scope:ideator'
    - ' type:config'
depends_on:
    - 642
class: standard
---

## Acceptance Criteria

- [ ] `.gitignore` includes pattern to ignore `.owlbear/briefs/draft-new/` (transient template directory)
- [ ] `.gitignore` preserves `.owlbear/briefs/.gitkeep` and `.owlbear/briefs/README.md`
- [ ] Completed `draft-{name}/` directories are NOT ignored (tracked for audit trail)

## Context

Research: `.owlbear/research/briefs-directory-structure.md` §3B — versioning strategy C.
The `draft-new/` template is created by the Mediator on invocation and renamed to `draft-{project-name}/` after Moment 1. Only the transient template should be ignored.

[[2026-04-06]] Mon 15:01
## Research
- Research doc: .owlbear/research/briefs-directory-structure.md (parent #642, validated)
- Sources: 2 verified — briefs-directory-structure.md S3B/S3C (design decision), .gitignore L55-58 (existing scratch pattern)
- Recommendation: Use specific path pattern `.owlbear/briefs/draft-new/` — no wildcard, no exemptions needed (confidence: .92)
- Follow-up tasks created: none (this IS the implementation follow-up)
- Decision requests: none — T1 autonomous (config tweak)

## Challenge Results
- Challenger: FALLBACK — T1 trivial config with pre-existing research validation from parent #642
- Confidence in original: .92
- Key challenges: wildcard vs specific-path approach — specific path wins on KISS (no exemptions, no risk of matching draft-{name}/)
- Researcher response: accepted — approach A is minimal-risk

## Implementation Guidance
Add to .gitignore (after the scratch section, ~line 58):

```
# Briefs — transient template directory (renamed to draft-{name}/ at M1)
.owlbear/briefs/draft-new/
```

No `!` exemptions needed — pattern is specific to draft-new/ only. .gitkeep, README.md, and completed draft-{name}/ directories are all inherently preserved.
