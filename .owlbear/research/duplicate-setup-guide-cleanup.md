# Duplicate Setup-Guide Task Cleanup

> **Owning task:** #182 — Clean up duplicate setup-guide tasks (#171 #172 #174 #175)
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #25 research produced overlapping `kanban-md create` executions that spawned 5 near-identical tasks for setup/sharing docs. Which is canonical, and what happens to the duplicate research docs?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | kanban task #169 (backlog, most detailed AC) | 1.0 |
| 2 | kanban task #171 (ideation, blocked as dup) | 1.0 |
| 3 | kanban task #172 (backlog, has research notes) | 1.0 |
| 4 | kanban task #174 (ideation, blocked, empty body) | 1.0 |
| 5 | kanban task #175 (backlog, identical AC to #169) | 1.0 |
| 6 | `docs/research/setup-and-sharing-docs.md` (owns #169) | 1.0 |
| 7 | `docs/research/multi-project-doc-guide.md` (owns #172) | .90 |
| 8 | `docs/research/multi-project-setup-docs.md` (owns #175) | .90 |

## 3. Analysis

### 3.1 Duplicate Confirmation

| Task | Status | Blocked? | Claims | Diff from #169 |
|------|--------|----------|--------|-----------------|
| #171 | ideation | Yes (dup) | None | Shorter AC, no parens detail |
| #172 | backlog | No | None | Identical scope, has own research doc |
| #174 | ideation | Yes (empty) | None | Empty body — no AC at all |
| #175 | backlog | No | None | Identical AC verbatim |

**Verdict:** All 4 are duplicates. #169 is canonical (most detailed AC, earliest created, already at backlog).

### 3.2 Research Doc Inventory

Three research docs exist for one topic. Each has unique tables worth preserving:

| Doc | Unique Contribution |
|-----|-------------------|
| setup-and-sharing-docs.md (#169) | 8 AC gap items, doc quality patterns, duplicate inventory |
| multi-project-doc-guide.md (#172) | Aider/Claude Code prior-art comparison, new VS Code features since #25 |
| multi-project-setup-docs.md (#175) | Setup.py 8-artifact table with idempotency, 3 VS Code debug tools, dependency check |

The docs are complementary — deleting the duplicates would lose useful writer context. KISS approach: keep all 3 and update #169's body to reference them.

### 3.3 Cleanup Approach

1. `kanban-md archive 171,172,174,175` — single command, tasks hidden from normal views
2. Update #169 body to reference all 3 research docs
3. No research docs deleted — they contain complementary content for the writer

## 4. Recommendation (.95 confidence)

Archive all 4 duplicates. Keep all 3 research docs (they serve as writer reference for #169). Update #169's body to point to all 3 docs. No new tasks needed beyond what #182 AC already specifies.

**Risk:** Minimal — archival is soft-delete, recoverable via `kanban-md list --archived`.

## 5. Follow-up Tasks

Task #182 AC already covers all cleanup actions. No additional tasks needed. The builder should:

1. Run `kanban-md archive 171,172,174,175`
2. Update #169 body to reference all 3 research docs
3. Verify #169 is the only remaining setup-guide task
