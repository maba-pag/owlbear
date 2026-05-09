---
id: 1477
title: Normalize stale durable config test identifiers
status: backlog
priority: nice-to-have
created: 2026-05-09T14:12:06.498671+00:00
updated: 2026-05-09T14:12:23.626815+00:00
tags:
- phase-4
- topology
- type:test
- quality
parent: 1473
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Scope

Rename contradictory pytest-visible class/test identifiers and any remaining AC-labeled headings/docstrings in `tests/test_config_loader.py`, `tests/test_config_authority.py`, and `tests/test_config_schema.py` so they match the current topology-constant contract.

## Acceptance Criteria

1. The durable config tests no longer use names/headings that claim vendor preservation, missing-file exceptions, grouped save emission, or root status/priority persistence when the bodies assert omission or next_id-only behavior.
2. The scoped command `uv run pytest tests/test_config_loader.py tests/test_config_authority.py tests/test_config_schema.py tests/test_config_grouped.py` still exits 0 after the rename-only cleanup.