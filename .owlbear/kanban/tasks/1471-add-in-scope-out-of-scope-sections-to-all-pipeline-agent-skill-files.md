---
id: 1471
title: Add In Scope / Out of Scope sections to all pipeline agent skill files
status: research
priority: important
created: 2026-05-09T08:33:41.860392+00:00
updated: 2026-05-09T08:33:55.555766+00:00
tags:
- pipeline
- ws-roles
- scope:agents
parent: 1403
depends_on:
- 1411
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)
Research: `.owlbear/research/1411-role-boundary-documentation.md`

## Objective

Add `## Scope` sections (with `### In Scope` and `### Out of Scope` subsections) to 7 pipeline agent skill files. Content sourced from the research doc §3.3.

## Target Files

1. `share/skills/w-task-decomposition/SKILL.md` (planner)
2. `share/skills/w-arch-review/SKILL.md` (architect)
3. `share/skills/w-tdd-red/SKILL.md` (test-writer)
4. `share/skills/w-tdd-green/SKILL.md` (builder)
5. `share/skills/w-code-review/SKILL.md` (reviewer)
6. `share/skills/w-task-verification/SKILL.md` (auditor)
7. `share/skills/w-doc-update/SKILL.md` (doc-writer)

## Acceptance Criteria

P1: Each of the 7 skill files contains a `## Scope` section with `### In Scope` and `### Out of Scope` subsections
P2: Section is placed between the skill description paragraph and `## Step 0 — Setup`
P2: Each "Out of Scope" bullet names the responsible agent
P2: Content matches the boundaries defined in `.owlbear/research/1411-role-boundary-documentation.md` §3.3
P3: Verification by artifact inspection of each skill file