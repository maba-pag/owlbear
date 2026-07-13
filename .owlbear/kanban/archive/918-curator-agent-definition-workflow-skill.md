---
id: 918
title: Curator agent definition + workflow skill
status: archived
priority: medium
created: 2026-04-17T11:52:23.667240+00:00
updated: 2026-04-17T20:04:12.089237+00:00
tags:
- test-quality
- type:agent
- scope:copilot
parent: 912
depends_on:
- 914
- 915
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #912

## AC

- `share/agents/curator.agent.md` created — pipeline position (post-archive), tool allowlist, skill reference
- `share/skills/w-test-curation/SKILL.md` created containing all of:
  - **Classification heuristics:** contract-level (public API surface, documented behavior, AC-derived assertions) vs implementation-coupled (internal state, private methods, specific mock configurations). Conservative default: ambiguous cases promoted.
  - **Atomic workflow:** module-by-module processing — read task-scoped file, classify assertions, promote contract-level to `test_{module}.py`, remove task-scoped file. Each module-batch leaves full suite green with coverage >= 90% on touched modules.
  - **AC provenance:** promoted assertions carry comment linking to original AC (format: `# From task #NNN: AC-N — description`)
  - **Lifecycle log:** JSONL schema defined — fields: task_id, module, action (promote/discard/skip), assertions_promoted, assertions_discarded, coverage_before, coverage_after, timestamp. File location: `.owlbear/scratch/curator-log.jsonl`
  - **Hard gates:** green suite + coverage >= 90% on touched modules, checked before and after each batch. Git revert on failure.
  - **Non-blocking:** skill documents that curator never gates next task dispatch
- `share/instructions/curator.instructions.md` stub created (pointer to w-test-curation skill)
- Agent registered in `agent-common.instructions.md` section-header mapping table
