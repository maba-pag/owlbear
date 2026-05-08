---
id: 1441
title: 'P4-04: Remove config.yml from setup seed and board initialization'
status: backlog
priority: needed
created: 2026-05-08T19:31:53.767342+00:00
updated: 2026-05-08T19:35:01.084330+00:00
tags:
- phase-4
- scope:setup
- type:refactor
- seed
- deployment-readiness
parent: 1437
depends_on:
- 1440
- 1439
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: setup seed files and setup/init.py board-directory creation.
Out of scope: engine constants, MCP transport, Cockpit UI, and docs.

## Acceptance Criteria
1. Builder removes seed/.owlbear/kanban/config.yml from the seed tree and leaves no replacement topology template under seed.
2. setup.init creates missing board directories for tasks, archive, decisions/pending, and decisions/resolved without writing .owlbear/kanban/config.yml.
3. Given a target with existing task, archive, decision, and activity files, setup.init preserves those files' content and does not rewrite task frontmatter.
4. setup.init remains compatible with the fixed-topology engine from #1439 when the target board has no config.yml.
5. Builder verifies AC-1 through AC-4 using the probe artifacts from #1440 and does not use pytest or vitest as the functional proof.