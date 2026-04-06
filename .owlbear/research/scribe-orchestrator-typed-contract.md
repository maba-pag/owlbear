# Typed Contract for Scribe↔Orchestrator NEEDS-INFO Boundary

> **Owning task:** #657 — Typed contract for scribe↔orchestrator NEEDS-INFO boundary
> **Date:** 2026-04-06 **Status:** Complete

## 1. Context and Question

The scribe's resolve-mode output is a 3-line text string (`RESOLVED N | ... / NEEDS-INFO M | ... / PENDING P | ...`). The orchestrator regex-parses the `NEEDS-INFO` line to extract `{task_id, agent}` pairs for dispatch injection. This required a carve-out exception to the "never interpret subagent output" critical rule in `orchestrator.agent.md`.

**Question:** How should the scribe↔orchestrator boundary be redesigned to use a typed contract instead of text parsing, removing the carve-out exception?

**Key constraint:** After the scribe processes `response: needs-info`, it resets the DR file to `response: pending`. The needs-info state is therefore ephemeral — it only exists in the scribe's output or whatever state the scribe persists. Any solution must persist this state somewhere.

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| `orchestrator.agent.md` critical_rules (carve-out) | `share/agents/orchestrator.agent.md` L44 | 1.0 — defines the exception to remove |
| `w-orchestration` Step 1 (NEEDS-INFO injection) | `share/skills/w-orchestration/SKILL.md` L28-48 | 1.0 — current consumption logic |
| `scribe.agent.md` resolve output contract | `share/agents/scribe.agent.md` L99-106 | 1.0 — current production format |
| `w-decision-routing` needs-info handling | `share/skills/w-decision-routing/SKILL.md` L52-60 | 0.9 — scribe's processing flow |
| `curation-report.json` pattern (curator→CLI) | `serve/mcp-memory/.../approve.py` L79-95 | 0.7 — file-based agent→consumer precedent |
| `pick_tasks` structured output | `serve/mcp-kanban/.../server.py` L572-604 | 0.6 — existing MCP structured data pattern |
| `r-pipeline-protocol` reading rules | `share/skills/r-pipeline-protocol/SKILL.md` L110-115 | 0.8 — defines what orchestrator reads |

## 3. Analysis

### Option A: Resolve-Summary JSON File

Scribe writes `.owlbear/decisions/resolve-summary.json` (overwritten each cycle) after processing all pending DRs. Orchestrator reads this file via `readFile` instead of parsing Channel A text.

```json
{
  "resolved": [{"task_id": 616, "response": "approved"}],
  "needs_info": [{"task_id": 616, "agent": "researcher"}],
  "pending": [{"task_id": 617, "filename": "617-something.md"}]
}
```

### Option B: Channel B Artifact

Scribe appends structured data to a task body or shared artifact. **Discarded:** the orchestrator protocol states "never reads task bodies" for routing. This option either violates that rule or collapses into Option A.

### Option C: MCP Tool Registration

Add a read-only `get_needs_info_dispatches` MCP tool to `mcp-kanban` that returns structured dispatch data. **Problem:** since the scribe resets DR files to `response: pending` after processing, there is no persistent state for an MCP tool to read. Option C requires state persistence, which means it becomes Option A (file) or Option D (tags) with extra indirection. ~30 LOC Python change + tests.

### Option D: Kanban Tags as Dispatch Hints

Scribe adds a tag `needs-dispatch` (plus agent name in body or tag suffix) to needs-info tasks. Orchestrator reads `list_tasks(tag="needs-dispatch")`, extracts agent, dispatches, removes tag. Uses kanban state (the orchestrator's native data source) rather than a side-channel.

### Trade-Off Matrix

| Criterion | A: JSON File | C: MCP Tool | D: Kanban Tags |
|-----------|:---:|:---:|:---:|
| Removes carve-out exception | Yes (reads state, not output) | Yes (native tool call) | Yes (reads board state) |
| KISS / simplicity | **High** | Medium | Medium |
| Tool calls per cycle | +2 | +1 | +3 to +5 |
| Python code changes | 0 | ~30 LOC | 0 |
| Prompt complexity added | Low (1 file write, 1 file read) | Low (1 tool call) | Medium (tag lifecycle across 2 agents) |
| Failure mode | Stale file → mitigated by delete-after-read | Needs own state → collapses to A/D | Tag persists → safe re-dispatch |
| Human-inspectable | Yes (JSON file) | Via tool | Yes (tags in board) |
| Test coverage possible | No (prompt-level) | Yes (Python unit tests) | No (prompt-level) |
| Files touched (agent/skill) | 4 | 4 + 1 .py | 4 |
| Precedent in codebase | `curation-report.json` (weaker: tool→code, not agent→agent) | Existing MCP tools | Existing tag operations |

### Key Finding: All Options Change Transport, Not Semantics

The orchestrator must act on scribe-derived information regardless of transport. The meaningful distinction is between **parsing agent text output** (current — fragile, requires rule exception) and **reading deposited state** (file, tags, or MCP tool — robust, no exception needed). All three viable options (A, C, D) convert Channel A text into persistent state that the orchestrator reads as infrastructure data.

## 4. Recommendation (confidence: .80)

**Option A: Resolve-Summary JSON File** — with stale-file mitigation.

Challenge: `reconsider` — challenger ranked D > C > A. Challenger raised valid concerns: (1) Option A "launders" the violation by changing transport not semantics, (2) stale-file risk, (3) curator precedent is weaker than claimed (tool→code, not agent→agent). Re-evaluated: all options share the semantic concern (orchestrator acts on scribe-derived data); A wins on simplicity (fewest tool calls, lowest prompt complexity, zero Python changes). Stale-file risk mitigated by delete-after-read. Confidence revised from .85 to .80.

**Implementation sketch:**
1. Scribe resolve mode: after processing all DRs, write `resolve-summary.json` to `.owlbear/decisions/`
2. Orchestrator Step 1: after scribe returns, read `resolve-summary.json` via `readFile`. If file missing → empty dispatches (graceful). Delete file after reading (prevents stale data).
3. Remove carve-out exception from `orchestrator.agent.md` critical_rules
4. Update `w-orchestration` Step 1, `w-decision-routing` resolve output, `scribe.agent.md` output contract

**If Option A is rejected:** Option D (kanban tags) is the runner-up, trading simplicity for tighter kanban integration.

## 5. Follow-up Tasks

Created at ideation status via kanban.
