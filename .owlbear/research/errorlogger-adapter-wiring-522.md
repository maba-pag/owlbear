# ErrorLogger Adapter Wiring

> **Owning task:** #522 — Wire ErrorLogger adapter at AcpClient construction sites
> **Date:** 2026-04-06 **Status:** Complete

## 1. Context and Question

Task #522 bridges the gap between the `_ErrorLogger` Protocol in `acp_client.py`
(implemented by #521) and `ErrorJournal` (implemented by #184). Without an adapter
and wiring at AcpClient construction sites, the `_ErrorLogger` injection is dead code.

**Key questions:** (a) What adapter pattern? (b) Where to place the adapter?
(c) How to handle `session_id` for pre-session errors? (d) Where does the
ErrorJournal file path come from?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | `_ErrorLogger` Protocol | `owlbear_orchestrator/acp_client.py` L40–46 | 1.0 |
| 2 | `AcpClient` constructor | `owlbear_orchestrator/acp_client.py` L89–98 | 1.0 |
| 3 | `ErrorJournal.log()` signature | `owlbear_orchestrator/error_journal.py` L48–56 | 1.0 |
| 4 | `orchestrate()` — AcpClient construction | `owlbear/orchestrator/loop.py` L464–471 | 1.0 |
| 5 | `dispatch_entry()` — session lifecycle | `owlbear/orchestrator/loop.py` L130–187 | .95 |
| 6 | `cli.py` — `_do_dispatch` | `owlbear/cli.py` L40–47 | .70 |
| 7 | AuditLog injection pattern | `owlbear/orchestrator/loop.py` L420–430 | .85 |
| 8 | Existing wiring research | `.owlbear/research/errorjournal-acpclient-wiring.md` | .90 |

## 3. Analysis

### 3.1 Interface Gap

| Protocol method | Args | ErrorJournal.log() | Gap |
|-----------------|------|--------------------|-----|
| `log_error()` | `category: ErrorCategory, method: str, message: str` | `category: str, method: str, message: str, session_id: str` | `session_id` missing |

`ErrorCategory` is a `StrEnum` — values pass directly as `str`. No conversion needed.
The adapter's sole job: supply `session_id` and delegate.

### 3.2 Adapter Pattern

| Criterion | A: Class adapter (.85) | B: Closure (.65) | C: partial (.45) |
|-----------|----------------------|------------------|-------------------|
| Testability | High — mock journal, assert | Medium — opaque | Low — inspection awkward |
| session_id mutability | `adapter.session_id = X` | `nonlocal` variable | Not possible |
| Discoverability | Named class, IDE support | Anonymous | Generic |
| KISS | ~10 LOC | ~8 LOC | ~4 LOC |
| Precedent | `_CancelSignal` pattern in same file | None in codebase | None |

### 3.3 Adapter Placement

| Location | Pro | Con |
|----------|-----|-----|
| `error_journal.py` | Cohesive — adapter wraps ErrorJournal | Imports ErrorCategory (same package, fine) |
| New `error_logger_adapter.py` | Clean separation | Another file for ~10 LOC |
| `loop.py` | Near consumer | Couples dispatch to journal internals |

Best: `error_journal.py` — both classes are in `owlbear_orchestrator`, keeps adapter
next to the object it adapts. ~10 LOC, no new file needed.

### 3.4 session_id Strategy

The `_ErrorLogger` Protocol doesn't receive `session_id` per-call. The dispatch
cycle is: `new_session()` → get `session_id` → `prompt(session_id=...)`. Errors can
occur at any phase. The AcpClient is shared across all dispatches.

**Concurrency concern (challenger-identified):** `dispatch_wave()` uses
`asyncio.gather()` for parallel dispatch by default. A mutable `session_id` on a
shared adapter races when multiple entries dispatch concurrently — Entry A's
session_id gets overwritten by Entry B before A's prompt error is logged.

| Strategy | Concurrency-safe | Accuracy | KISS |
|----------|-----------------|----------|------|
| Fixed sentinel `"pre-session"` | Yes — immutable | Low — prompt errors lose session context | .90 |
| `contextvars.ContextVar` | Yes — per-asyncio-task | High | .80 |
| Per-dispatch adapter factory | Yes — new instance each call | High | .60 |

**Recommendation:** Fixed sentinel `"pre-session"` is the KISS-aligned default.
The `method` field already disambiguates error phases. If session-level correlation
proves needed later, upgrade to `ContextVar` — ~3 extra LOC, each `asyncio.Task`
from `gather()` gets its own context copy. Builder decides per AC language.

Mutable instance attribute is **not recommended** — unsafe under parallel dispatch.

### 3.5 ErrorJournal File Path

No orchestrator config exists. Two options:

| Option | Path | Pro | Con |
|--------|------|-----|-----|
| Workspace-relative default | `.owlbear/error-journal.jsonl` | Consistent with kanban/audit patterns | Needs cwd awareness |
| Caller-provided | Parameter to `orchestrate()` | Flexible, testable | Requires caller to know about it |

Best: Follow AuditLog injection pattern (Source 7). `orchestrate()` accepts
`error_journal: ErrorJournal | None = None`. Caller creates the journal with
a workspace-relative path. Default: `.owlbear/error-journal.jsonl`.

### 3.6 Construction Sites

| Site | File | Current | Action |
|------|------|---------|--------|
| `orchestrate()` | `loop.py` L471 | `AcpClient(conn)` | Pass `error_logger=adapter` |
| `_do_dispatch()` | `cli.py` L42 | `AcpClient(None)` (placeholder) | Low-priority — placeholder code with `type: ignore` |

## 4. Recommendation (.85 confidence)

**Class adapter in `error_journal.py`**, wired at `orchestrate()` in `loop.py`.

1. `ErrorLoggerAdapter(journal, session_id="pre-session")` — ~10 LOC class
2. `orchestrate()` accepts `error_journal: ErrorJournal | None = None`
3. Creates adapter internally, passes to `AcpClient(conn, error_logger=adapter)`
4. session_id: fixed `"pre-session"` sentinel (concurrency-safe). Upgrade path:
   `ContextVar` for per-dispatch accuracy when needed (~3 LOC delta).
5. `cli.py` wiring deferred — placeholder code, separate follow-up if needed

Challenge: reconsider — confidence in original: .85
Challenger found mutable session_id races under parallel `asyncio.gather()` dispatch.
Revised to fixed sentinel (accepted). Class adapter, placement, and tier upheld.

**Tier: T1 — Autonomous.** Wires existing components. No new capability, no
architecture change, no security/breaking/user-facing impact.

## 5. Follow-up Tasks

Task #522 AC is already well-defined. No new tasks needed — the existing AC
covers: adapter class, session_id strategy, construction-site wiring, file path
sourcing, and unit tests. Task advances to backlog.
