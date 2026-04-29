---
id: 1175
title: Harden storage.save_config for grouped config output
status: research
priority: needed
created: 2026-04-28T23:07:11.208593+00:00
updated: 2026-04-29T01:40:59.252254+00:00
tags:
- scope:kanban
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

storage.save_config (L236-260) uses a hardcoded legacy-key strip list that will break when BoardConfig gains nested sub-models (#1155). Also silently strips defaults — a key the engine still reads (defaults.priority at engine.py L936).

See `.owlbear/research/1171-config-write-path-audit.md` §4 Step 2.

## Acceptance Criteria

1. Replace hardcoded strip list with model-driven field emission (e.g. model_fields allowlist)
2. Add test proving nested dict values survive save/load round-trip
3. Verify frozenset-to-list conversion works at nested depth
4. `defaults.priority` is not lost after a `save_config` cycle (align strip list with engine read set or preserve defaults until #1170 resolves)

## Decision Resolved

**Decision:** A: Retry when GitHub service recovers

**Reasoning:** GitHub service disruptions are transient; the researcher is stateless and can cleanly retry. Retrying when service recovers preserves research context and is the natural path forward.