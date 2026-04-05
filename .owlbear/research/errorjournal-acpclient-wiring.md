# ErrorJournal-AcpClient Wiring Research

> **Owning task:** #148 — Wire ErrorJournal into AcpClient when v2 error infrastructure exists
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #148 asks to integrate ErrorJournal logging into AcpClient error paths.
The task was deferred from #59 because v2 has no ErrorJournal module yet. The
v2 error infrastructure is minimal: `OwlBearError` base exception (7 LOC) plus
AcpClient's local `ErrorCategory` enum. No JsonlStore, no ErrorJournal, no
other structured error persistence exists in v2.

**Key questions:** (a) What interface should AcpClient use for error logging?
(b) What prerequisite infrastructure must exist first? (c) What's the
implementation pattern — concrete class, Protocol, or callback?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | v1 ErrorJournal implementation | `v1/src/owlbear/memory/error_journal.py` | .95 |
| 2 | AcpClient `_CancelSignal` Protocol | `packages/orchestrator/src/owlbear_orchestrator/acp_client.py` L33–38 | 1.0 |
| 3 | Tenacity `after` callback pattern | <https://tenacity.readthedocs.io/en/latest/api.html> | .85 |
| 4 | Python `logging.Logger.exception` | <https://docs.python.org/3/library/logging.html> | .70 |
| 5 | ErrorJournal async-safety research | `docs/research/error-journal-async.md` | .90 |
| 6 | ErrorJournal dedup research | `docs/research/error-journal-dedup.md` | .75 |
| 7 | AcpClient wrapper validation | `docs/research/acp-client-wrapper-validation.md` §3.4 | .95 |
| 8 | PydanticAI exceptions hierarchy | <https://github.com/pydantic/pydantic-ai> | .65 |

## 3. Analysis

### 3.1 v2 Infrastructure Gap

v2 currently has zero error persistence infrastructure:

| Component | v1 status | v2 status |
|-----------|-----------|-----------|
| `OwlBearError` base | Exists | Exists (7 LOC) |
| `ErrorCategory` enum | In classify_error | Local to AcpClient only |
| `JsonlStore[T]` base | Exists | **Missing** |
| `ErrorEntry` model | Exists (Pydantic) | **Missing** |
| `ErrorJournal` | Exists (126 LOC) | **Missing** |

#148 is blocked on ≥1 prerequisite task to create the v2 error journal.

### 3.2 Interface Design Options

| Criterion | A: Protocol (.85) | B: Callback (.70) | C: Concrete class (.50) |
|-----------|-------------------|-------------------|-------------------------|
| Decoupling | Full — duck-typed | Full — any callable | Tight — imports ErrorJournal |
| Testability | MockProtocol or `MagicMock` | Simple lambda | Needs real or mock journal |
| Precedent | `_CancelSignal` in same file | Tenacity `after` pattern | No precedent in codebase |
| Type safety | Structural typing | Loose `Callable` | Nominal typing |
| KISS | High — one method | Highest — one callable | Medium — imports + setup |
| Extensibility | Add methods to Protocol | Needs new callback | Full journal API available |

### 3.3 Protocol Design (Recommended)

Following AcpClient's existing `_CancelSignal` Pattern (Source 2):

```python
class _ErrorLogger(Protocol):
    def log_error(self, *, category: str, method: str, message: str) -> None: ...
```

- Thin 3-field signature: `category` (ErrorCategory value), `method` (which
  AcpClient method failed), `message` (exception string)
- Sync call — single JSONL append is sub-ms (Source 5 §3.4 confirms acceptable)
- v2 ErrorJournal implements this Protocol without explicit registration
- Any test mock with `log_error(**kwargs)` also satisfies it

### 3.4 Async Considerations

AcpClient methods are async. ErrorJournal.log() is sync (blocking file I/O).
Source 5 recommends `asyncio.to_thread` at the *call site* (daemon), not inside
the journal. For AcpClient, the journal call happens inside `except` blocks
which already do sync work (`str(exc)`, constructing `AcpClientError`). A
single JSONL append (open + write + close) is sub-ms; blocking is acceptable.
No `asyncio.to_thread` needed inside AcpClient.

### 3.5 Implementation Scope

~20 LOC change to `acp_client.py` once prerequisite exists:
1. Add `_ErrorLogger` Protocol (4 LOC)
2. Add `error_logger: _ErrorLogger | None = None` to `__init__` (2 LOC)
3. Add `_log_error()` helper method (6 LOC, guards on `None`)
4. Call `_log_error()` in 6 catch blocks before re-raising (6 LOC)

### 3.6 Prerequisite Dependency Chain

```
Create v2 ErrorEntry + ErrorJournal  →  Wire into AcpClient (#148)
         │
         └── Optionally: Create v2 JsonlStore[T] base first (DRY)
```

The JsonlStore base is optional. A standalone ErrorJournal with inline JSONL
persistence (~60 LOC) is simpler and YAGNI-aligned until a second JSONL store
appears in v2. The orchestrator audit log research (Source not numbered, see
`docs/research/orchestrator-audit-log.md`) reached the same conclusion.

## 4. Recommendation (.85 confidence)

**Protocol-based integration** — define `_ErrorLogger` Protocol in
`acp_client.py`, accept optional instance in constructor, log before re-raise.

**Prerequisite:** Create a v2 `ErrorJournal` module at
`packages/orchestrator/src/owlbear_orchestrator/error_journal.py` with inline
JSONL persistence (no JsonlStore base needed yet). Port `ErrorEntry` as a
Pydantic model with simplified fields. ~60–80 LOC.

**Risk:** v2 may never need full ErrorJournal features (rotation, dedup, query).
Mitigation: start with append-only; add features when needed (YAGNI).

## 5. Follow-up Tasks

See task body for `kanban-md create` commands executed at `ideation`.
