---
id: 1206
title: Clean up load_config double-validation chain
status: backlog
priority: needed
created: '2026-04-30 15:29:06.219146+00:00'
updated: '2026-04-30 15:32:04.128562+00:00'
tags:
- audit-kanban
- dry
parent:
depends_on:
- 1205
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Remove storage.load_config wrapper; use config_loader directly.

## Files
- storage.py (load_config wrapper)
- config_loader.py
- consumers of storage.load_config

## Change
Remove `storage.load_config()` wrapper. Have consumers use `config_loader.load_config()` directly. Remove the redundant `_validate_claim_timeout` call in the wrapper.

## AC
- [ ] storage.py no longer defines load_config
- [ ] All consumers import from config_loader
- [ ] No redundant validation in the load path
- [ ] Tests pass

## Finding: 1.4
