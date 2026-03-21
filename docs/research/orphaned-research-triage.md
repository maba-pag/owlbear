# Orphaned Research Task Triage

> **Owning task:** #766 — Triage orphaned research tasks — backfill follow-ups
> **Date:** 2026-03-13 / Updated: 2026-03-20 **Status:** Reconciled

## 1. Context and Question

An audit found ~11 archived research tasks that produced docs but never executed `kanban-md create` commands to create follow-up implementation tasks. This triage reviews each, determines what's still relevant, and either creates follow-ups, justifies "no action needed," or files a decision request.

## 2. Review of Each Orphaned Task

| ID | Title | Research Doc | Follow-ups Status | Disposition |
|----|-------|-------------|-------------------|-------------|
| #16 | VS Code hooks format | (none — superseded) | Superseded by #38 HookRegistry | **No action** — task body says "Superseded by #38" |
| #22 | Agent patterns from external repos | agent-patterns.md | 13 follow-ups listed but never created | **Superseded** — all patterns now implemented (HookRegistry, channels, agent loop, etc.) |
| #127 | PydanticAI multi-agent patterns | agent-framework.md | 3 refinements + 3 new tasks listed | **Superseded** — AgentRegistry, AgentDefinition, delegation all implemented |
| #137 | MCP servers inventory | mcp-servers.md | 5 MCP follow-ups listed | **Covered** — `mcp_registry.py` + `mcp_servers.py` fully implement the MCP follow-ups; specific server configs (GitHub/Git/Fetch) are user setup, not code changes |
| #141 | PydanticAI web UI / Logfire | agent-observability.md | 3 follow-ups listed | **Superseded** — `ObservabilityHook`, `EventStore`, `Agent.instrument_all()` all implemented |
| #246 | Moonshine streaming API | moonshine-streaming.md | AC edits for #241-#245 listed | **Superseded** — voice module (11 files) uses moonshine |
| #253 | Content hashing / delta re-ingest | content-hashing.md | 8 follow-ups listed | **Superseded** — `content_hash` column exists (24 hits), delta ingest implemented |
| #255 | Intra-document graph builder | intra-document-graph.md | 5 `kanban-md create` commands | **Superseded** — `IntraDocGraphBuilder` class exists, `enrichment.py` wired, provenance tracking done |
| #262 | Adopt existing pipeline vs build custom | knowledge-pipeline.md | 2 follow-ups + confirmation | **Closed** — follow-up #776 was created but is a duplicate of archived #274; research concluded YAGNI (scale mismatch). No further action. |
| #263 | Bootstrap/assembly layer | bootstrap-assembly.md | 9 follow-ups listed | **Superseded** — `src/owlbear/bootstrap/` (15 files) exists, `bootstrap()` function implemented |
| #264 | Browser automation alternatives | browser-automation.md | 4 follow-ups listed | **Superseded** — "keep custom" decision implemented; browser module maintained |

### Root-Level Orphaned Docs (AC4)

| Doc | Has Follow-up Section? | Disposition |
|-----|----------------------|-------------|
| `docs/agent-quality-analysis.md` | Yes — §9 "Follow-up Tasks" (line 350) | **Superseded** — all tasks (instructions, skills, agent rewrites) have been implemented |
| `docs/code-quality-audit.md` | Yes — §"Follow-up Task Commands" (line 379) | **Superseded** — audit findings became tasks in later board sweeps |
| `docs/graph-expansion-benchmark-results.md` | Yes — §"Follow-up Tasks" (line 47) with explicit no-action statement | **No action** — benchmark output, not research. No follow-ups needed. |

## 3. Analysis: Current-State Reconciliation (2026-03-20)

All 11 tasks in the original orphaned list have been fully reconciled against current board and codebase state. No open gaps remain.

**#137 (MCP servers):** Originally flagged as "Partially superseded" because GitHub/Git/Fetch wiring was not yet done. Verification confirms `src/owlbear/tools/mcp_registry.py` and `src/owlbear/tools/mcp_servers.py` fully implement the concrete MCP follow-ups from the research doc. Specific server configurations (GitHub, Git, Fetch) are user-setup concerns, not code changes. Disposition updated to **Covered**.

**#262 (knowledge pipeline):** Originally flagged as "Partially superseded" with community detection as an open gap. Follow-up task #776 was created from this triage. Subsequent research on #776 determined it is a duplicate of archived #274, which concluded YAGNI (scale mismatch: OwlBear's graph of 500–2K entities is 1–2 orders of magnitude below where Leiden community detection produces meaningful structure). Disposition updated to **Closed**.

**Root docs:** All three previously flagged root-level docs already contain follow-up or explicit no-action sections (verified by line search). No doc updates required.

## 4. Recommendation (.95 confidence)

- **All 11 tasks: no action needed** — all follow-ups superseded by implementation or closed as YAGNI
- **Root docs: no action** — all three docs already have follow-up/no-action sections
- **#574 (add follow-up tasks to 3 research docs missing them):** Stale — the 3 docs it targeted already have follow-up sections. Recommended disposition: archive as superseded by this triage.
- **#776 (graph community detection):** Stale — duplicate of archived #274, YAGNI conclusion confirmed. Recommended disposition: archive as duplicate of #274.

## 5. Follow-up Tasks Created by This Triage

**#776** was created during the original March 13 sweep to cover the community detection gap. Its body now documents the YAGNI determination from #274 research. Recommended board action: archive #776 as a duplicate of #274 (no code implementation needed).

No additional `kanban-md create` commands are warranted.

## 6. Verification Note (2026-03-20)

**Audit methodology:** Re-ran archived research task audit by:

1. Listing all archived tasks tagged `research` via `kanban-md list --status archived --tag research`
2. Verifying dispositions for each of the original 11 orphaned tasks against current codebase (`src/owlbear/tools/mcp_registry.py`, `src/owlbear/tools/mcp_servers.py`) and board state (#276, #776, #274)
3. Verifying root-level docs via `grep_search` for follow-up/no-action sections
4. Spot-checking newer archived research tasks (IDs 580–747) for follow-up completeness

**Result:** No additional orphaned research tasks found beyond the original 11. The newer research wave (IDs 580–647) all have either confirmed follow-up tasks (e.g., #580 → #614–#625 series, #583 → #630–#633, #597 → #732–#734, #647 → #703–#705) or explicit no-action documentation. Tasks #700–#747 all passed through the full pipeline with architect/builder/reviewer/auditor verification of follow-up completeness.

**Conclusion:** The orphaned-research audit is complete. All 11 original tasks are reconciled. No new orphaned research docs or tasks identified.
