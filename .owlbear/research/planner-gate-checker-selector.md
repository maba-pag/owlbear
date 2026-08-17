# Planner Gate Checker & Task Selector — Research Validation

> **Owning task:** #145 — Implement planner gate checker and task selector
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #145 (subtask of #20) implements 6 gate predicate functions, a task selector
with dual-key sort, an agent mapper dict, and a 20-task dispatch cap. Parent
research: `docs/research/build-dispatch-planner.md` S3.5.

Key questions: (1) How many gates need Python logic vs. CLI-handled? (2) What's the
exact heuristic for the atomicity gate? (3) Should DECOMP routing be included?
(4) File structure: one file or two? (5) Are there AC gaps?

## 2. Sources Studied

| # | Source | Rel. | What |
|---|--------|:----:|------|
| S1 | `dispatch-planning` SKILL.md (local) | .95 | 6-gate definitions, agent dispatch mapping, DECOMP routing |
| S2 | `build-dispatch-planner.md` S3.5 (local) | .90 | Implementation approach: gates as predicates, dual-key sort |
| S3 | `build_dispatch.ps1` (local) | .80 | Working PS reference: gates 4+5 as inline checks, agent map |
| S4 | `planner-data-models-board-reader.md` (local) | .85 | Input types: `Task`, `DispatchEntry`, `DispatchPlan` from #144 |
| S5 | Python 3.12 `re` module docs | .70 | Regex patterns for body/title scanning |
| S6 | Pydantic v2 docs — Models | .70 | Frozen model reuse for DispatchPlan construction |
| S7 | `orchestration` SKILL.md (local) | .80 | Wave assembly expects `DispatchPlan` with agent field |
| S8 | `mcp-kanban/server.py` (local) | .75 | Subprocess flag patterns for kanban-md |

## 3. Analysis

### 3.1 Gate Architecture — Python vs. CLI

| Gate | Name | Python logic? | Rationale |
|------|------|:---:|-----------|
| 1 | Status | No | `read_board()` uses `--status` filter [S1, S8] |
| 2 | Dependency | No | `read_board()` uses `--unblocked` flag [S1, S8] |
| 3 | Atomicity | Yes | Title scan for " and " joining unrelated concerns [S1] |
| 4 | TDD | Yes | Body regex: `## Test-Writer Notes` absent on `in-progress` [S1, S3] |
| 5 | Clarity | Yes | Body regex: no bullet/numbered AC on `todo+` tasks [S1, S3] |
| 6 | Claim | No | `read_board()` uses `--unclaimed` flag [S1, S8] |

**Finding (.90):** Only 3 gates need Python functions. The AC lists 6 but acknowledges
gates 2 and 6 are CLI-handled. Recommendation: implement 3 predicate functions +
1 composite `check_gates()` that applies all 3. Document CLI-handled gates in the
composite's docstring. Don't create stub functions that always return True — that's
YAGNI noise. [S1, S2]

### 3.2 Gate 3 — Atomicity Heuristic

The dispatch-planning skill says: "Red flag: the word 'and' joining unrelated
concerns." The PS reference (build_dispatch.ps1) doesn't implement this gate at all.
[S1, S3]

In the LLM planner, this uses reasoning. For Python, a simple heuristic:
check for `r"\band\b"` (word-boundary " and ") in the title. False positives
(e.g., "Read board and build DAG") are acceptable — excluded tasks re-enter
next cycle. [S1, S5]

**Recommendation (.75):** Implement as a simple word-boundary regex. Document that
it's an approximation. The LLM planner's Gate 3 is stronger, but the Python
version provides a safety net for obvious violations.

### 3.3 Gate 4 — TDD Fallback

The skill specifies a fallback: "a linked test task in `done` status also satisfies
this gate." [S1] This requires cross-task lookup (finding the test task for an impl
task by scanning `depends_on` or naming conventions). The AC doesn't mention this.

**Recommendation (.85):** Implement the primary check only (body scan for
`## Test-Writer Notes`). The fallback adds complexity for a rare edge case — document
it as a future enhancement in the docstring.

### 3.4 DECOMP Routing — Missing from AC

The dispatch-planning skill defines: tasks with `Needs decomposition:` in the body
dispatch to `kanban-planner` regardless of status. [S1] The AC omits this.

**Recommendation (.90):** Add DECOMP routing to the task selector / agent mapper.
It's a routing override, not a filter — belongs in `selector.py`, not `gates.py`.
Without it, the Python planner cannot dispatch decomposition work.

### 3.5 File Structure

| Option | Files | LOC est. | KISS |
|--------|-------|----------|:----:|
| A. Single `gates.py` | 1 | ~150 | Medium |
| B. `gates.py` + `selector.py` | 2 | ~80 + ~70 | High |

**Recommendation (.85):** Option B — two files. Gates are filter predicates (pure
boolean functions on a single Task). Selector is transformation logic (sort + cap +
mapping on a list). Different patterns, different test strategies. Matches #144's
separation of `models.py` and `board.py`. [S2, S4]

### 3.6 Proposed Function Signatures

```python
# gates.py
def check_atomicity(task: Task) -> bool: ...
def check_tdd(task: Task) -> bool: ...
def check_clarity(task: Task) -> bool: ...
def check_gates(task: Task) -> bool: ...  # composite: all 3


# selector.py
PRIORITY_RANK: dict[str, int]  # critical=0 .. someday=4
STATUS_RANK: dict[str, int]  # done=0 .. ideation=6
STATUS_AGENT_MAP: dict[str, str]  # status -> agent name
DISPATCH_CAP: int = 20


def select_tasks(tasks: list[Task]) -> DispatchPlan: ...
```

The `select_tasks()` function: filters via `check_gates()`, sorts by
`(PRIORITY_RANK, STATUS_RANK)`, applies DECOMP routing override, caps at
`DISPATCH_CAP`, returns `DispatchPlan`. [S1, S2, S7]

### 3.7 AC Gap Summary

| Gap | Impact | Recommendation |
|-----|--------|---------------|
| No function signatures | Builder guesses API | Add exact signatures (§3.6) |
| No `selector.py` file specified | Ambiguous structure | Recommend separate file (§3.5) |
| DECOMP routing missing | Incomplete algorithm | Add to selector (§3.4) |
| TDD gate fallback unmentioned | Minor edge case | Document as future enhancement (§3.3) |
| Unit tests bundled with impl | Violates TDD convention | Separate into test task |
| Gate 3 heuristic undefined | Builder guesses regex | Specify `\band\b` pattern (§3.2) |
| No composite `check_gates()` | No clear entrypoint | Add to AC (§3.1) |
| Only 3 Python gates, not 6 | Misleading AC count | Clarify: 3 Python + 3 CLI-handled |

### 3.8 Testing Strategy

- **Gate functions:** test each independently with canned `Task` objects [S4]
- **Atomicity:** true positive ("Implement X and update Y"), false positive
  ("Read board and build DAG"), no-and title
- **TDD gate:** in-progress with/without `## Test-Writer Notes`, non-in-progress status
- **Clarity gate:** todo with bullets, todo without, ideation (exempt)
- **Composite:** verify all-pass, each-fail independently
- **Selector:** priority sorting with mixed statuses/priorities, DECOMP override,
  20-task cap, empty input, single-task input
- **Agent mapper:** every status maps correctly, unknown status handling
- No real kanban-md.exe needed — pure unit tests on model objects

## 4. Recommendation (.85 confidence)

The AC is directionally correct but needs refinement by the architect:

1. **Clarify gate count:** 3 Python predicate functions + 1 composite, not 6 stubs
2. **Add DECOMP routing** to task selector (missing from AC entirely)
3. **Split into `gates.py` + `selector.py`** — different concerns, cleaner testing
4. **Add function signatures** — exact API prevents builder guesswork
5. **Separate test task** — unit tests should precede implementation per TDD

Risks:
- Gate 3 (atomicity) heuristic has false positives — acceptable, tasks re-enter next cycle
- DECOMP routing adds a routing override that the AC didn't scope — but without it
  the Python planner is incomplete vs. the dispatch-planning skill [S1]

## 5. Follow-up Tasks

No new tasks needed beyond #145 itself. The architect should refine the AC during
backlog review using the gap analysis above (§3.7). A test task for #145 should be
created by the architect (following #144's pattern with #153).
