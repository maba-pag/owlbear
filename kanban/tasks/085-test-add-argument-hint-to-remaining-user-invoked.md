---
id: 85
title: 'Test: Add argument-hint to remaining user-invoked skills'
status: in-progress
priority: nice-to-have
created: 2026-03-27T08:48:16.9125448+01:00
updated: 2026-03-27T10:30:50.9903305+01:00
tags:
    - phase-1
    - scope:skills
    - type:test
    - test
class: standard
---

## Objective
RED phase tests for #79. Extend tests/test_argument_hint_skills.py with 3 test classes.

## Acceptance Criteria
- [ ] TestFromAC_ExcalidrawDiagramArgumentHint: key present, value is '[diagram description]', in frontmatter not body
- [ ] TestFromAC_VisualOutputArgumentHint: key present, value is '[diagram or visual description]', in frontmatter not body
- [ ] TestFromAC_FrontendDesignArgumentHint: key present, value is '[component or design question]', in frontmatter not body
- [ ] All new tests FAIL on current HEAD (RED phase)
- [ ] Follow exact pattern from existing TestFromAC_ProjectDefinitionArgumentHint class

## Files
- tests/test_argument_hint_skills.py (extend)

## Context
Test task for #79. Pattern: tests/test_argument_hint_skills.py already has classes for project-definition and retro from #43.
