# Rewrite #486 AC to Match Current Architecture

> **Owning task:** #593 — Rewrite #486 AC to match current architecture
> **Date:** 2026-04-04 **Status:** Complete

## 1. Context and Question

Task #486 (Phase C: Consolidate kanban references) has 7 AC items written
before the skills-based architecture solidified. Research in
`docs/research/consolidate-kanban-references.md` found 2/7 reference
non-existent files and 2/7 are already satisfied. This task validates those
findings and drafts concrete replacement AC text for #486.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | docs/research/consolidate-kanban-references.md | Research | .95 — prior research producing this task |
| 2 | 14 w-\* workflow skills (Step 0 + MCP callouts) | Codebase | .95 — consolidation targets |
| 3 | tests/test_mcp_tool_references_483.py | Codebase | .95 — constrains tool name presence |
| 4 | r-pipeline-protocol SKILL.md (Per-Agent Signal Mapping) | Codebase | .90 — section-header source of truth |
| 5 | h-mcp-kanban SKILL.md L30 (param disclaimer) | Codebase | .85 — consolidation principle |
| 6 | Task #484 body (Phase B AC, h-kanban-md retention) | Kanban | .85 — dependency chain constraint |

## 3. Analysis

### 3a. Validation of Prior Research

All claims from `consolidate-kanban-references.md` verified against current HEAD:

| Claim | Verified? | Delta |
|-------|-----------|-------|
| 7 identical Step 0 claiming blocks | Yes | Functionally identical; w-task-verification has minor article variant ("Read **the**") |
| ~14 generic MCP callouts | Yes | Actual: 16 generic (7× start_work, 7× end_work, 2× show_task) |
| ~18 context-specific callouts | Yes | Actual: 16 context-specific (7× edit_task w/ section headers, 9× unique compositions) |
| agent-common.instructions.md doesn't exist | Yes | 0 results workspace-wide |
| Section-header mapping in r-pipeline-protocol | Yes | L115 Per-Agent Signal Mapping table |
| Test requires tool names in skill bodies | Yes | 7 "cheatsheet" skills × 3 tools + 3 "inline-ref" skills × 1+ tool |

### 3b. Test Survival Matrix (post-consolidation)

Critical constraint: `test_mcp_tool_references_483.py` asserts tool name
**strings** (not headings or blocks) exist in each skill body. After removing
generic MCP equiv blocks and consolidating Step 0, all entries survive via prose:

| Skill | `start_work` | `end_work` | `edit_task` |
|-------|-------------|-----------|------------|
| w-arch-review | Step 0 prose | prose L72 | prose L73, L84, L130 |
| w-code-review | Step 0 prose | prose L201 | prose L276 |
| w-doc-update | Step 0 prose | prose L81 | prose L79 |
| w-mem-curation | Step 0 prose | prose L90 | prose L84 |
| w-task-verification | Step 0 prose | prose L100 | prose L94, L148, L158 |
| w-tdd-red | Step 0 prose | prose L36, L48, L67, L140 | prose L34, L46, L67, L116, L169 |
| w-tdd-green | Step 0 prose | prose L27, L138 | prose L25, L123 |

All 21 cells (7 × 3) have surviving prose references. Zero risk of test breakage
from removing `> **MCP equivalent:**` blocks alone.

Inline-ref skills (w-decision-routing, w-dispatch-planning, w-research) retain
context-specific callouts satisfying their 1-of-5 tool name requirement.

### 3c. Scope Clarification: w-mem-curation

w-mem-curation has a conditional Step 0 (not identical to the 7 standard blocks)
→ excluded from Step 0 consolidation. Its 2 generic callouts (show_task L28,
end_work L92) are in scope for generic callout removal per AC 2.

### 3d. Callout Classification

32 total `> **MCP equivalent:**` callouts across w-\* skills:

- **16 generic** (trivial calls: start_work/end_work/show_task with task_id only)
- **16 context-specific** (unique parameter compositions — worked examples)

Boundary rule: if the callout shows parameters beyond `task_id` and generic
`note="..."`, it's context-specific.

## 4. Recommendation: Proposed Replacement AC for #486

Confidence: .82

Replace the 7 stale AC items in #486 with these 7 verifiable items:

> ### Replacement AC
>
> - [ ] **Step 0 claiming consolidated:** 7 functionally identical Step 0
>   claiming blocks (w-arch-review, w-code-review, w-doc-update, w-research,
>   w-task-verification, w-tdd-red, w-tdd-green) reduced from 5-line blocks
>   to 2-line cross-references preserving `start_work` tool name in prose.
>   Post-Step-0 status gates and Step 0a sub-sections (w-doc-update,
>   w-tdd-green) unchanged. Non-standard variants (6 other w-\* skills)
>   unchanged.
>
> - [ ] **Generic MCP callouts removed:** 16 generic `> **MCP equivalent:**`
>   blocks (start_work, end_work, show_task with task_id-only params) removed
>   from all w-\* skills (including w-mem-curation). Prose tool-name references
>   preserved (see survival matrix in research doc).
>
> - [ ] **Context-specific callouts retained:** 16 callouts with unique
>   parameter compositions (edit_task with append_body/section headers,
>   list_tasks with filter combos, create_task, end_work with
>   workflow-specific notes) kept as worked examples.
>
> - [ ] **h-kanban-md unchanged:** Retained as deprecated CLI troubleshooting
>   reference per #484 decision. Exempt from consolidation scope.
>
> - [ ] **test_mcp_tool_references_483.py passes:** Tool name strings survive
>   in all 7 "cheatsheet" skills (3 tools each) and 3 "inline-ref" skills
>   (1+ tool each) via prose references. No test modification required.
>
> - [ ] **Grep verification:** `> **MCP equivalent:**` count reduced from 32
>   to 16 across w-\* skills. Remaining 16 are context-specific worked
>   examples. h-kanban-md excluded from count (deprecated).
>
> - [ ] **Cross-reference integrity:** All skill-name references in modified
>   files resolve to existing .github/skills/{name}/SKILL.md paths.

Challenge: reconsider — confidence in original .72. Accepted C2 (survival
matrix — added 3b), C4 (w-mem-curation scope — added 3c), C5 (AC 7
verifiability — replaced with concrete criteria), C6 (micro-discrepancy —
"functionally identical"), C7 (h-kanban-md exception — explicit in AC 4+6).
Rebutted C1 (test checks string presence not headings — no `## kanban-md
Commands` heading assertion exists in test), C3 (count is 32 per grep, not 33).

## 5. Follow-up Tasks

No new follow-up tasks needed. #593 itself IS the follow-up from the prior
research. The revised AC is the deliverable — the architect applies it to #486
during the architecture review phase.

Dependency chain preserved: #484 (Phase B, todo) → #486 (Phase C, backlog).
