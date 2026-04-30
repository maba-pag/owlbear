# create_dr MCP Tool + Guidance Text Update

> **Owning task:** #1183 — P1-04: Implement create_dr MCP tool + guidance text update
> **Date:** 2026-04-30 **Status:** Complete

## 1. Context and Question

Task #1183 asks for (a) registering a `create_dr` MCP tool and (b) updating guidance text from "via the scribe agent" to "via the create_dr tool". Dependencies #1181 (decisions module) and #1182 (RED tests) are archived/done.

**Key finding:** The `create_dr` tool is already implemented in `server.py`. Only the guidance text update remains.

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L430-470 | 1.0 — tool already registered |
| 2 | `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py` | 1.0 — 7/7 tests pass |
| 3 | `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py` L14 | 1.0 — `_DR_REQUIRED_MSG` text |
| 4 | `serve/kanban/src/owlbear_kanban/engine.py` L1866 | 0.9 — duplicate `_BLOCK_AR_HINT` |
| 5 | `.owlbear/briefs/draft-dr-script-replacement/brief.md` L126-130 | 0.8 — authoritative new text |

## 3. Analysis

### AC Status Matrix

| AC Line | Status | Evidence |
|---------|--------|----------|
| `create_dr` tool registered | DONE | `server.py` L432 `@mcp.tool` decorator |
| Delegates to `decisions.create_dr()` | DONE | `server.py` L458 `asyncio.to_thread(decisions.create_dr, ...)` |
| Response `{created: true, path: str}` | DONE | `server.py` L467 `return {"created": True, "path": relative_path}` |
| `request_type` validated to enum | DONE | `server.py` L439 rejects non-`{decision, action}` |
| Guidance text updated | **TODO** | Still says "via the scribe agent" |
| #1182 tests pass | DONE | 7/7 green |

### Guidance Text Change — Impact Matrix

| File | Constant | Used by | Update needed |
|------|----------|---------|---------------|
| `guidance.py` L14 | `_DR_REQUIRED_MSG` | `edit_task` block guidance | Yes (AC) |
| `engine.py` L1866 | `AgentView._BLOCK_AR_HINT` | `end_work(outcome="block")` | Yes (same message) |
| `test_mcp_guidance_1089.py` L125 | `_BLOCK_AR_HINT` test constant | test assertion | Yes (tracks source) |
| `tests/test_engine_end_work_1080.py` L94 | inline string | test assertion | Yes (tracks source) |
| `share/skills/h-mcp-kanban/SKILL.md` L96 | prose reference | agent docs | Yes (prose reference) |

### New Text (per Brief)

```
"⚠️ ACTION REQUIRED: Create a Decision Request via the create_dr tool."
" Blocks without a DR are invisible to the pipeline."
```

Changes: drops "for this block", replaces "via the scribe agent", drops "(see w-decision-routing)".

## 4. Recommendation (confidence: 0.92)

**T1 — Autonomous.** Trivial string replacement across 5 files. No architecture decision, no new capability — it's updating text to match already-implemented behavior.

Challenge: SKIPPED — trivial text substitution, no meaningful recommendation to challenge.

Risk: Existing test `test_dr_skill_replacement_1186.py` validates `w-decision-routing` deletion as a P2 gate — removing the `(see w-decision-routing)` reference early is compatible (test checks file existence, not guidance text).

## 5. Follow-up Tasks

None needed — task is ready for direct implementation. The remaining work is a 5-file text substitution. Advance to backlog.
