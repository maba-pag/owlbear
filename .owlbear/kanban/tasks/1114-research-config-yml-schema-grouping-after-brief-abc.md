---
id: 1114
title: 'Research: config.yml schema grouping after Brief A/B/C'
status: research
priority: nice-to-have
created: 2026-04-24T12:00:00+00:00
updated: 2026-04-24T12:00:00+00:00
tags:
- scope:kanban
- type:research
parent:
depends_on:
- 1094
blocked: false
block_reason: 'Wait for Briefs A, B, C to land — field set may still change. Unblock when all Brief A tasks reach done.'
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Context

config.yml currently uses a flat namespace for all fields. During the v1→v2 transition the legacy `defaults:` and `board:` groups are stripped, but the new fields (`agent_map`, `agent_types`, `agent_compatibility`, `entry_status`, `wave_size`, `tasks_dir`, `archive_dir`, `status_predicates`, `archival_reasons`, etc.) remain flat at the top level.

As the field count grows, this becomes harder to scan and maintain. A grouped structure (e.g. paths, pipeline, agents, policy) would improve readability and make related settings discoverable.

## Scope

- Researcher or architect decides the grouping structure — do not pre-commit to a layout.
- Fields may still change during Brief A/B/C — only start after all three Briefs land.
- Must update `BoardConfig` model, `_normalise_legacy` validator, all config field accessors, and test fixtures.
- Must remain yamllint-clean (see `yaml_rt.make_yaml` for indent/explicit_start settings).

## Origin

Observed during yaml_rt consolidation (2026-04-24): the flat namespace is a readability debt, not a correctness issue.
