# Wire or Remove MemoryConsolidator

> **Owning task:** #485 — Wire or remove MemoryConsolidator
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

`MemoryConsolidator` (`src/owlbear/memory/consolidation.py`, ~145 LOC) summarizes
unconsolidated conversation turns into MEMORY.md (always in context) + HISTORY.md
(searchable log). Based on nanobot's two-layer memory pattern. Fully implemented
and tested (299 LOC in `test_consolidation.py`) but never imported in production
code. Flagged as YAGNI-04 and INT-03. Should it be wired or deleted?

## 2. Sources Studied

| # | Source | Path/URL | Relevance |
|---|--------|----------|-----------|
| 1 | MemoryConsolidator impl | `src/owlbear/memory/consolidation.py` | 1.0 |
| 2 | Consolidation tests | `tests/test_consolidation.py` (299 lines) | 0.9 |
| 3 | memory `__init__.py` exports | `src/owlbear/memory/__init__.py` | 1.0 |
| 4 | ContextManager (downstream consumer) | `src/owlbear/memory/context.py` L66-76 | 1.0 |
| 5 | SessionStore (last_consolidated) | `src/owlbear/memory/session.py` | 0.9 |
| 6 | Agent turn cycle | `src/owlbear/core/agent.py` L110-155 | 1.0 |
| 7 | Bootstrap assembly research | `docs/research/bootstrap-assembly.md` §3.5 | 0.9 |
| 8 | Software design audit YAGNI-04 | `docs/software-design-audit.md` L248-260 | 1.0 |
| 9 | Integration audit INT-03 | `docs/integration-audit.md` L22 | 0.9 |
| 10 | EscalationHook research (precedent) | `docs/research/escalation-hook.md` | 0.8 |
| 11 | Architecture docs | `docs/architecture.md` L315-330, L472 | 0.9 |
| 12 | Nanobot two-layer memory | `docs/research/agent-patterns.md` §3.6 | 0.8 |

## 3. Analysis

### How it works

1. `MemoryConsolidator.consolidate(session)` loads messages, checks threshold
2. If unconsolidated count > threshold (default 20), sends to LLM for summary
3. Writes MEMORY.md (overwrites) + appends to HISTORY.md (timestamped log)
4. Updates `session.last_consolidated` pointer

### Plumbing that already exists

| Component | Consolidation support | Status |
|-----------|----------------------|--------|
| `ContextManager.instructions` | Reads MEMORY.md, combines with context.md | **Wired** |
| `SessionStore.last_consolidated` | Pointer + `.meta` persistence | **Wired** |
| `agent.turn()` → `session.save()` | Natural insertion point post-save | **Not wired** |
| `bootstrap.py` | No MemoryConsolidator instantiation | **Not wired** |
| `memory/__init__.py` exports | Not exported | **Not wired** |

### Key difference from EscalationHook (#484)

EscalationHook had a **fundamental conflict** with `_recover_from_error` (ARC-21:
dual-prompt, competing error authority). Wiring it was actively harmful.

MemoryConsolidator has **no architectural conflict**. It fills a slot the architecture
explicitly designed for: ContextManager reads MEMORY.md, SessionStore tracks
`last_consolidated`, bootstrap-assembly-research recommended adoption (.80).

### Trade-off matrix: Wire vs Delete vs Defer

| Criterion | Wire now (.45) | Delete (.70) | Defer (keep dead) (.20) |
|-----------|---------------|-------------|------------------------|
| **YAGNI** | Low — no user hit context limits yet | High — remove until needed | Lowest — dead code stays |
| **KISS** | Medium — adds LLM call per N turns | High — simpler codebase | Low — dead code clutters |
| **Effort** | ~10 LOC in bootstrap + model config | ~40 min (delete + clean refs) | 0 |
| **Risk** | Low (no conflict, but untested in prod) | Minimal (no behavior change) | None |
| **Re-add cost** | N/A | Low (~2 hrs from git history) | N/A |
| **Session growth** | Solved proactively | Unsolved until needed | Unsolved |
| **Test burden** | 299 LOC maintained for live feature | Eliminated | 299 LOC for dead feature |
| **Precedent** | Inconsistent with #484 verdict | Consistent with #484 pattern | Third path, worst YAGNI |

### Why "Defer" is worst

Keeping dead code with tests is pure cost — the test suite runs 299 lines of tests
for code no production path reaches. If it's worth having, wire it. If not, delete.

## 4. Recommendation (.70 confidence)

**Delete MemoryConsolidator and its tests.**

Rationale:

- YAGNI: the daemon doesn't run long-lived sessions yet. No user has hit context
  window exhaustion. The feature solves a problem that doesn't exist today.
- Unlike EscalationHook (architecturally broken), this is sound — but "sound and
  unused" is still dead code.
- Re-adding is cheap: ~2 hrs from git history when context growth becomes a real
  problem. The plumbing (ContextManager, SessionStore.last_consolidated) stays.
- Consistent with #484 pattern: fully-implemented-but-unwired = remove per YAGNI.
- Eliminates 444 LOC (145 impl + 299 test) of maintenance burden.

**What to preserve**: SessionStore.`last_consolidated` property and `_load_meta`/
`_save_meta` are low-cost and support future re-addition. Keep them. Only delete
`consolidation.py` and `test_consolidation.py`.

**Dissenting case (.45)**: Wire it now — it's 10 LOC, architecturally sound, and
proactively prevents context exhaustion. If the team expects long daemon sessions
soon, wiring is the better call. The recommendation flips if there's a near-term
plan for extended sessions.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Delete MemoryConsolidator (YAGNI)" --priority needed --status todo --tags "yagni,cleanup,scope:core" --body "Delete src/owlbear/memory/consolidation.py and tests/test_consolidation.py. Remove consolidation.py reference from docs/architecture.md directory listing (line 120). KEEP SessionStore.last_consolidated and _load_meta/_save_meta (low-cost plumbing for future re-add). AC: (1) consolidation.py deleted (2) test_consolidation.py deleted (3) architecture.md directory listing updated (4) ruff clean (5) all remaining tests pass (6) grep -r MemoryConsolidator src/ returns zero matches. Out of scope: do NOT edit audit/research docs — they are historical records. See docs/research/memory-consolidator.md."
```

## 6. Attribution

No new external sources — all analysis based on existing codebase and previously
documented nanobot research (already in `docs/sources.md`).
