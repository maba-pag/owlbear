# State Machine RED Tests — Design & Feasibility

> **Owning task:** #1304 — P1-03: RED — State machine tests
> **Date:** 2026-05-04 **Status:** Complete

## 1. Context and Question

Task #1304 writes failing (RED) tests for the redesigned state machine defined in the brief (`.owlbear/briefs/draft-memory-mcp-ux/brief.md`). The GREEN implementation (#1305) depends on these tests. The key question: what interface should tests target, and how do we guarantee RED state given the current code?

## 2. Sources Studied

| # | Source | Path/URL | Relevance |
|---|--------|----------|-----------|
| S1 | Brief — state machine section | `.owlbear/briefs/draft-memory-mcp-ux/brief.md` L149–182 | 1.0 |
| S2 | Current tools.py | `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` | 1.0 |
| S3 | Current engine.py | `serve/mcp-memory/src/owlbear_mcp_memory/engine.py` | .95 |
| S4 | Schema test pattern (#1302) | `tests/test_memory_schema_1302.py` | .90 |
| S5 | Brief — curate_memory spec | `.owlbear/briefs/draft-memory-mcp-ux/brief.md` L108–141 | 1.0 |
| S6 | Brief — delete_memory spec | `.owlbear/briefs/draft-memory-mcp-ux/brief.md` L142–152 | 1.0 |

## 3. Analysis

### 3A. Current vs Target State Machine

| Behavior | Current (tools.py) | Target (Brief D29/D31/D36) |
|----------|-------------------|---------------------------|
| Auto-promote | `PENDING→CURATED` via explicit `state` param | `PENDING→CURATED` when `scope_agents` provided |
| Scope gate | None | Pending curate rejected if `scope_agents` missing |
| Edit on curated | Stays curated (implicit) | Stays curated (explicit requirement) |
| Auto-downgrade | Blocked (`"cannot modify approved"`) | `APPROVED→CURATED` unconditionally |
| approved_at lifecycle | Set on approve (never cleared) | Set on approve, cleared on downgrade |
| Hard-delete | Not implemented | Pending → file removed from disk |
| Soft-delete | All states → DELETED | Only curated/approved → DELETED |
| Terminal state | DELETED blocks nothing | DELETED blocks all operations |

### 3B. Test Interface Options

| Option | Interface | RED mechanism | Risk |
|--------|-----------|--------------|------|
| A | Import `curate_memory` from tools | ImportError (doesn't exist) | pytest won't collect → unclear |
| B | Test via current `update_entry`/`delete_entry` | Behavior mismatch (assertions fail) | Tight coupling to old API |
| C | Test engine-level state machine functions | Import from new module → ImportError or behavior mismatch | Clean but requires new module assumption |
| **D** | Test via current tools but assert NEW behaviors | Assertions fail clearly | Best RED signal + guides GREEN |

**Recommendation: Option D (confidence .85)**

Tests import existing `update_entry`, `delete_entry`, `approve_entry` from `owlbear_mcp_memory.tools`. They call these functions but assert the **new** behavior. RED because:
- `update_entry` on approved entry raises ToolError → test expects auto-downgrade = FAIL
- No scope gate exists → test expects rejection without scope_agents = FAIL  
- `delete_entry` on pending doesn't hard-delete → test expects file absence = FAIL
- `delete_entry` always soft-deletes → no terminal enforcement tests pass

Note: #1305 GREEN may rename `update_entry` to `curate_memory` etc., at which point tests get a find-replace. The logic assertions remain stable.

### 3C. RED Guarantee Analysis

| AC line | Why it fails against current code |
|---------|----------------------------------|
| AC1: auto-promote with scope_agents | No scope gate logic; state change requires explicit `state` param |
| AC2: scope gate rejection | `update_entry` doesn't check scope_agents presence |
| AC3: curated stays curated | Actually passes (current code allows this) — needs careful test design |
| AC4: approved auto-downgrade | Current code raises ToolError for approved entries |
| AC5: approved_at cleared | No downgrade path exists to clear it |
| AC6: hard-delete pending | `delete_entry` always soft-deletes |
| AC7: soft-delete curated/approved | Passes (current behavior) — need complementary assertion |
| AC8: deleted terminal | No terminal enforcement; delete_entry is idempotent |
| AC9: invalid transitions | Partially passes (pending→approved blocked by `_ensure_update_transition`) |

**Risk: AC3 and AC7 may accidentally pass.** Mitigation: pair with assertions about the auto-promote path or auto-downgrade that guarantee at least one failure per class.

### 3D. Test Structure

```
tests/test_state_machine_1304.py
├── TestFromAC_AutoPromote (AC1)
├── TestFromAC_ScopeGate (AC2)
├── TestFromAC_CuratedStaysCurated (AC3)
├── TestFromAC_AutoDowngrade (AC4)
├── TestFromAC_ApprovedAtLifecycle (AC5)
├── TestFromAC_HardDeletePending (AC6)
├── TestFromAC_SoftDeleteCuratedApproved (AC7)
├── TestFromAC_DeletedTerminal (AC8)
└── TestFromAC_InvalidTransitions (AC9)
```

Each class: 2–4 test methods. Helpers create entries in specific states via `engine.write()` then call tool functions with a mock `ctx`.

## 4. Recommendation (confidence .85)

Proceed with test-writing. Pattern D (test current tools, assert new behavior) provides the clearest RED signal and gives the GREEN implementer a precise behavioral spec.

**Key design decisions for test-writer:**
1. Use `engine.write()` to plant entries in arbitrary states (bypasses tool logic)
2. Mock `ctx` per #1302 pattern (MagicMock with lifespan_context)
3. For hard-delete (AC6): assert file is absent from disk after delete
4. For terminal (AC8): assert ToolError raised on any operation against deleted entry
5. AC3 risk: include an assertion that `scope_agents` was NOT required (contrast with AC2)

Challenge: SKIPPED — T1 autonomous, no alternative approaches. TDD RED is standard procedure.

**Classification: T1 (Autonomous).** Follow-up task already exists (#1305 GREEN depends on this).

## 5. Follow-up Tasks

No new tasks needed — #1305 (GREEN implementation) already exists and depends on #1304.
