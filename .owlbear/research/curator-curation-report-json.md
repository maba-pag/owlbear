# Curator: write curation-report.json to data/memory/

> **Owning task:** #567 — Curator: write curation-report.json to data/memory/
> **Date:** 2026-04-04 **Status:** Complete

## 1. Context and Question

Task #567 adds a JSON report file that the curator writes after each curation cycle. The convention was established in docs/research/approve-memory-cli-wrapper.md §3C: `data/memory/curation-report.json` bridges the curator's curation output to the `approve_memory` CLI without cross-MCP coupling.

**Questions:** (1) What JSON schema? (2) How does the curator write/overwrite the file? (3) Does the consumer (approve.py) already handle it? (4) What skill changes are needed?

## 2. Sources Studied

| # | Source | Path/URL | Relevance |
|---|--------|----------|-----------|
| S1 | approve-memory CLI research §3C | `docs/research/approve-memory-cli-wrapper.md` | .95 |
| S2 | curator-workflow research §3E | `docs/research/curator-workflow-memory-mcp.md` | .90 |
| S3 | approve.py `_load_curation_report` | `packages/mcp-memory/src/owlbear_mcp_memory/approve.py` L88–100 | 1.0 |
| S4 | test_approve_memory_531.py format tests | `tests/test_approve_memory_531.py` L230–310 | .95 |
| S5 | test_approve_memory_585.py report tests | `tests/test_approve_memory_585.py` L595–660 | .90 |
| S6 | w-mem-curation skill Step 5 | `.github/skills/w-mem-curation/SKILL.md` | 1.0 |
| S7 | curator agent definition | `.github/agents/curator.agent.md` | .95 |
| S8 | Task #531 AC (curation report convention) | `kanban/tasks/531-*` | .90 |

## 3. Analysis

### 3A. JSON Schema — Format Alignment

Three authoritative sources define the expected format:

| Source | Top-level | Entry key | Fields |
|--------|-----------|-----------|--------|
| #567 AC | Array | `entry_id` | entry_id, content_preview, recommendation, reason |
| #531 AC | Array | `entry_id` | entry_id, recommendation, reason |
| test_531 (RED) | Array | `entry_id` | entry_id, recommendation, reason |

The current approve.py implementation (S3) reads a **different** format: `{"entries": [{id, recommendation}]}` — wrapped object with `id` key. This format comes from test_585 (S5), which was written before #531's AC was refined.

**Result:** approve.py crashes when given the AC format (4 failing tests in test_531, confirmed by running them). The format fix is tracked in #531, which is at `in-progress` with 13 failing RED tests.

**Schema for #567 (superset):**

```json
[
  {
    "entry_id": "uuid-string",
    "content_preview": "first ~80 chars of content...",
    "recommendation": "approve|delete|keep|cross-pollinate",
    "reason": "one-line rationale"
  }
]
```

`content_preview` is in #567 AC but not #531 AC. The field is additive — approve.py can ignore unknown keys. Recommendation values map to w-mem-curation Step 4 ratings: HIGH→approve, LOW/NOISE→delete, MEDIUM→keep, cross-pollinate→cross-pollinate.

### 3B. Write/Overwrite Mechanism

| Approach | Reliability | KISS | Notes |
|----------|-------------|------|-------|
| `edit/createFile` | Unclear overwrite | High | VS Code API has overwrite option; agent tool may not expose it |
| `edit/editFiles` (replace all) | Works on existing only | Medium | Fails on first write when file doesn't exist |
| `execute/runInTerminal` | Always works | High | PowerShell `Set-Content` overwrites unconditionally |
| Create + editFiles fallback | Always works | Low | Two-step, branching logic in skill text |

**Recommendation (.85):** Don't over-specify the tool in the skill. The skill should say "write the JSON report file" and provide the schema. The curator agent has `edit/createFile`, `edit/editFiles`, and `execute/runInTerminal` — it can determine the appropriate tool. If `createFile` fails on overwrite, the agent falls back to terminal. Specifying the exact tool mechanism in the skill adds coupling to tool implementation details.

### 3C. Skill Changes Required

The w-mem-curation SKILL.md needs one change: update Step 5 (Deliverables) to include writing the JSON report file before appending to the task body.

Current Step 5:
> If dispatched with a task ID, append curation report to task body via `edit_task`.

Proposed Step 5 addition:
1. Write `data/memory/curation-report.json` with entries processed in this cycle
2. Include all entries with their entry_id, content preview, recommendation, and reason
3. File is overwritten each cycle

The output template in the skill already contains the data (Deletions table has ID, Rating, Reason; Promotions table has Finding and Proposed Change). The JSON report is a machine-readable parallel of that human-readable template.

### 3D. Existing Data Flow

```
curator agent
  ├── Step 1–4: gathers, dedupes, assesses, acts on entries
  ├── Step 5: writes task body (Channel B) — human-readable
  └── Step 5 (new): writes curation-report.json — machine-readable
       └── consumed by: approve_memory CLI (_load_curation_report)
```

No new MCP tools, no new Python code in the curator. The curator already collects entry IDs, content, ratings, and reasons during Steps 1–4. The JSON report serializes that existing data.

### 3E. Risk: Content Preview Fidelity

The `content_preview` field truncates entry content. The approve.py CLI also truncates at 80 chars (S3, `_print_table`). If the curator truncates to a different length, the CLI may double-truncate or show inconsistent previews.

**Mitigation:** Specify ~80 chars in the skill schema description, matching approve.py's display width. The CLI can always re-truncate from the original DB content; the preview is advisory.

## 4. Recommendation (.88 confidence)

Update w-mem-curation SKILL.md Step 5 to write `data/memory/curation-report.json` using the top-level array schema with `entry_id` key. No Python code changes needed for #567 — the format fix in approve.py is tracked in #531. The implementation is a ~10-line addition to the skill file.

Challenge: FALLBACK — challenger agent not available in researcher's subagent list.

## 5. Follow-up Tasks

No new tasks needed. Task #567 itself is the implementation task (skill file update). The approve.py format fix is already tracked in #531 (in-progress, 4 RED tests for this specific issue).
