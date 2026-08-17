# Test Strategy: decisions.py create_dr + resolve_pending_drs

> **Owning task:** #1180 — P1-01: Test decisions.py create_dr + resolve_pending_drs
> **Date:** 2026-04-30 **Status:** Complete

## 1. Context and Question

Task #1180 needs TDD tests for a new `serve/kanban/src/owlbear_kanban/decisions.py` module (part of DR Script Replacement #1179). The module doesn't exist yet — tests define the contract. Key question: what interface should the tests code against, and how should blocking/unblocking be mocked?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `serve/kanban/src/owlbear_kanban/engine.py` — `edit_task(blocked=, block_reason=)` | .95 — only blocking API |
| 2 | `tests/test_engine_end_work_1080.py` — test fixture pattern | .95 — gold-standard `tmp_path` + `KanbanEngine` pattern |
| 3 | `.owlbear/decisions/resolved/1124-*.md` — live DR file format | .90 — existing frontmatter schema |
| 4 | `share/skills/w-decision-routing/SKILL.md` — current DR schema | .90 — 5+ field frontmatter spec |
| 5 | `serve/kanban/src/owlbear_kanban/storage_io.py` — `atomic_write` | .85 — existing atomic file pattern |

## 3. Analysis

### A: Blocking API — No `block_task` method exists

The engine exposes `edit_task(task_id, blocked=True, block_reason=...)` for blocking and `edit_task(task_id, blocked=False)` for unblocking. No dedicated `block_task`/`unblock_task` methods exist.

**Decision for tests:** The `decisions.py` module will call `engine.edit_task`. Tests should either:
- Use a real engine on `tmp_path` (integration-style, matches test_engine_* patterns)
- Mock the engine (isolates decisions logic from engine internals)

**Verdict (.85):** Hybrid — real filesystem for file I/O assertions, mocked engine for blocking calls. This isolates the contract being tested (file creation + blocking orchestration) without recreating a full board.

### B: Module interface inferred from AC

```python
def create_dr(
    decisions_dir: Path,
    engine: KanbanEngine,
    task_id: int,
    agent: str,
    request_type: str,
    body: str,
) -> Path:
    """Create pending DR file, block task. Returns file path."""


def resolve_pending_drs(
    decisions_dir: Path,
    engine: KanbanEngine,
) -> ResolveResult:  # or dict/namedtuple with counts
    """Process responded DRs in pending/. Returns resolution summary."""
```

### C: Frontmatter schema — AC says "5-field"

AC specifies: task_id, agent, request_type, created, response=pending. This is a SIMPLIFIED schema vs. current scribe-created DRs (which have 8+ fields). The "ignores unknown keys" AC confirms forward-compatibility with older files that have extra fields.

### D: O_EXCL testing

`os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)` raises `FileExistsError` on collision. Tests: pre-create the file, assert either raises or falls back to counter suffix (`{slug}-2.md`).

## 4. Recommendation (.90 confidence)

**Test file:** `tests/test_decisions_1180.py`

**Fixture approach:** `tmp_path` with `decisions_dir / "pending/"` and `decisions_dir / "resolved/"` pre-created. Engine mocked via `unittest.mock.MagicMock(spec=KanbanEngine)`.

**Test classes:**
- `TestCreateDr` — 5 tests covering file write, O_EXCL, collision suffix, blocking call, rollback
- `TestResolvePendingDrs` — 5 tests covering skip-pending, approved/rejected, needs-info, unknown, fail-safe
- `TestDrReader` — 1 test for unknown-key tolerance

**Total: 11 tests** mapping 1:1 to the 10 AC lines (approved/rejected split into one test with parametrize).

Challenge: FALLBACK — no challenger invoked (T1 autonomous, no contested recommendation).

## 5. Follow-up Tasks

None required — this task IS the test task. Implementation follows in #1181.
