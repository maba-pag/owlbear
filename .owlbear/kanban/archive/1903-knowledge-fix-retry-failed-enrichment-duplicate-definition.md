---
id: 1903
title: 'Knowledge: fix retry_failed_enrichment duplicate definition'
status: archived
priority: nice-to-have
created: 2026-05-27T21:12:15.503668+02:00
updated: 2026-05-27T21:34:29.566216+02:00
tags:
  - knowledge
  - tech-debt
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason: duplicate
archival_refs:
  - 1901
---
Remove the dead bare-function definition of `retry_failed_enrichment` at line 331 of `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` and its redundant post-def registration at line 585-587. The @mcp.tool version at line 591 is the active one.

## Context

Discovered during #1901 research — the bare function is dead code that shadows the decorated version.

[[2026-05-27T21:14:33+02:00]]
## Research

N/A — trivial dead-code removal, rationale: duplicate definition confirmed via codebase inspection.

**Findings:**
- Bare function at L331-431 is identical in logic to the @mcp.tool version at L591+.
- Post-def registration (L586-588) registers the bare function as a tool, then the @mcp.tool decorator at L591 re-registers and shadows it.
- No external references depend on the bare function; all refs target the MCP tool name.
- `get_next_batch` / `store_enrichment` at L584-585 are unaffected.

**Implementation guidance:**
1. Delete lines 331-431 (bare `retry_failed_enrichment` function).
2. Delete lines 586-588 (post-def `retry_failed_enrichment = mcp.tool(...)(...)` call).
3. Keep the @mcp.tool decorated version at L591+ intact.
4. Run `serve/mcp-knowledge/tests/` to verify no breakage.

Tier: T1 (dead code removal). No DR needed.



[[2026-05-27T21:15:00+02:00]]
## Merged

Subsumed by #1901 AC3 — dead code removal happens as part of the rename. This task is redundant.

[[2026-05-27T21:25:45+02:00]]
## Architecture Review

### Verdict: MERGE

Task is redundant — fully subsumed by #1901 AC3 which covers the identical dead-code removal. #1901 already approved and in `todo`.

### Action Taken: Archived as merged with #1901.

[[2026-05-27T21:34:22+02:00]]
## Audit

**Regression Detection:** N/A — no code changes (merged task, no builder commit).
**Intent Verification:** PASS — #1901 AC3 explicitly subsumes this task's scope (dead-code removal of duplicate retry_failed_enrichment).
**Architect Quality:** 5/5 — correctly identified redundancy, issued MERGE verdict with clear rationale.
**Commit Integrity:** N/A — merged task, no deliverable expected.

**Deductions:** None.
**Confidence:** 1.00
**Action:** Archive (merged into #1901).
