---
id: 90
title: Update pytest-and-linting skill for v2 paths
status: ideation
priority: nice-to-have
created: 2026-03-28T01:40:27.8103029+01:00
updated: 2026-03-28T01:40:39.6139371+01:00
tags:
    - phase-1
    - docs
    - scope:build
depends_on:
    - 35
class: standard
---

## Objective
Update the pytest-and-linting skill to reflect v2 test infrastructure: new testpaths, coverage source_pkgs config, --import-mode=importlib.

## Acceptance Criteria
- [ ] Skill references v2 package paths instead of v1 src/ paths
- [ ] Coverage section updated for source_pkgs approach
- [ ] Import mode documented

## Context
Depends on #35 (v2 test infrastructure). The skill currently documents v1 patterns.
