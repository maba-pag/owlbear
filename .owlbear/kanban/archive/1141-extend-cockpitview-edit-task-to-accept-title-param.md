---
id: 1141
title: Extend CockpitView.edit_task to accept title param
status: archived
priority: medium
created: 2026-04-27T06:38:54.526915+00:00
updated: 2026-04-27T08:27:21.201813+00:00
tags:
- cockpit
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
Objective: Add title parameter to CockpitView.edit_task so cockpit edit routes can fully delegate to the facade.

Context: CockpitView.edit_task (engine.py L3142) forwards body, priority, parent, add_tag, remove_tag, add_dep, remove_dep, block_reason, archival_reason, archival_refs to engine.edit_task but NOT title. The cockpit EditRequest supports title editing, preventing full CockpitView delegation.

Acceptance Criteria:
- [ ] CockpitView.edit_task accepts title: str | None = None parameter
- [ ] When title is not None, it is forwarded as kwargs["title"] = title to engine.edit_task
- [ ] Existing CockpitView tests pass unchanged
- [ ] New test: CockpitView.edit_task(task_id, expected_updated=..., title="New") updates title

Scope: engine.py CockpitView class only (~5 LOC).

See: .owlbear/research/1132-cockpit-mutation-cockpitview-wiring.md
[[2026-04-27]]
## Research

**Tier:** T1 — Autonomous (facade param passthrough, no new capability)

**Findings:**
- `KanbanEngine.edit_task` accepts `title: str | None = None` (engine.py L948)
- `CockpitView.edit_task` (L3142) wraps engine.edit_task but omits `title` from its 17-param signature
- Route helper `_build_edit_kwargs` already builds `kwargs["title"]` (mutation.py L125) for direct engine calls
- Pattern precedent: `body`, `priority`, `parent` all use identical `if X: kwargs["X"] = X` in CockpitView

**Implementation approach (~3 LOC):**
1. Add `title: str | None = None` to `CockpitView.edit_task` signature
2. Add `if title is not None: kwargs["title"] = title` in kwargs building block
3. New test in `test_engine_cockpit_view_1078.py` verifying title update via CockpitView

**Challenge:** Skipped — trivial param passthrough, no recommendation ambiguity.

**No follow-up tasks** — this task has complete AC for direct implementation.
[[2026-04-27]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One param addition to one method |
| Interface clarity | PASS | Signature, default, and forwarding logic specified in AC |
| Dependency correctness | PASS | No deps needed; KanbanEngine.edit_task already supports title (L944) |
| Module layering | PASS | CockpitView delegates to engine — correct direction |
| TDD compliance | PASS | AC4 specifies test shape; test file is test_engine_cockpit_view_1078.py |
| KISS/YAGNI | PASS | Needed for cockpit route migration to CockpitView facade |
| Premise challenge | PASS | Gap is real — CockpitView.edit_task omits title despite engine supporting it |
| Pattern consistency | PASS | Uses str \| None = None with is-not-None guard, matching engine convention. Existing CockpitView params use str="" with truthiness — minor pre-existing inconsistency, not introduced here |
| Security surface | PASS | No new boundary; engine validates title |
| Single domain | PASS | Kanban engine domain only |

### Codebase Evidence
- KanbanEngine.edit_task (engine.py L944): title: str \| None = None
- CockpitView.edit_task (engine.py L3142): 12 params, no title
- AgentView.edit_task (engine.py L2483): also lacks title (separate scope)
- _build_edit_kwargs (mutation.py L119): already handles title for direct engine calls
- Cockpit HTTP route (mutation.py L221): calls engine.edit_task directly, not CockpitView — this is facade readiness work

### Challenge Results
- Challenger: reconsider (0.68)
- Concerns: (1) proof strength — single happy-path test; (2) sentinel semantics — None vs truthiness; (3) broader migration scope
- Architect response: REBUTTED/ACCEPTED-INFORMATIONAL
  - Proof: existing test patterns in test_engine_cockpit_view_1078.py give test-writer sufficient guidance
  - Sentinel: AC line 2 precisely says "When title is not None" — correct contract, accepted as informational
  - Scope: atomicity correct — each param gap is a separate task

### Verdict: APPROVE
### Action Taken: Advanced to todo. No AC changes needed — all 4 lines are precise and testable.
[[2026-04-27]]
## Test-Writer Notes

**Test file:** `tests/test_engine_cockpit_view_1141.py`
**Class:** `TestFromAC_CockpitViewEditTaskTitle`

**Tests per category:**
- Happy path: 2 (title updates task, ac4-e2e literal scenario)
- Edge: 1 (title=None preserves original title)
- Boundary: 1 (title is keyword-only)
- Signature/contract: 2 (param exists, default is None)

**Total:** 6 tests, all FAIL ✓

**Fail verification:** `pytest tests/test_engine_cockpit_view_1141.py` → 0 passed, 6 failed
- 2 AssertionError (title not in signature)
- 3 TypeError (unexpected keyword argument 'title')
- 1 AssertionError (param missing)

**Ruff:** All checks passed

**AC coverage:**

| AC line | Test(s) |
|---------|---------|
| AC1: accepts `title: str \| None = None` | test_edit_task_signature_has_title_param, test_edit_task_title_param_default_is_none |
| AC2: not-None forwarded to engine | test_edit_task_with_title_updates_task_title |
| AC2: None NOT forwarded | test_edit_task_title_none_preserves_original_title |
| AC3: existing tests pass unchanged | Covered by existing test_engine_cockpit_view_1078.py (no additional tests possible — calls without title already pass) |
| AC4: literal e2e scenario | test_edit_task_with_title_returns_response_with_updated_title |

**Boundary bonus:** test_edit_task_title_is_keyword_only (confirms title cannot be passed positionally)
[[2026-04-27]]
## Builder Notes
- Implementation: No net source diff required in `serve/kanban/src/owlbear_kanban/engine.py`; `CockpitView.edit_task` already exposes keyword-only `title: str | None = None` and forwards `kwargs["title"]` when not `None`.
- Tests: 6/6 `TestFromAC_CockpitViewEditTaskTitle` passed; regression companion file `tests/test_engine_cockpit_view_1078.py` also passed (total 69 passed, 0 failed).
- Coverage: `owlbear_kanban.engine` 40% in scoped run (module-wide metric; task-specific behavior covered by AC tests).
- Ruff: clean on task-scoped lint paths (`tests/test_engine_cockpit_view_1141.py`, `tests/test_engine_cockpit_view_1078.py`).
- Evidence summary:
  - RED verification: 0 passed / 6 failed on `tests/test_engine_cockpit_view_1141.py` before implementation step.
  - GREEN verification: scoped quality-runner run reports `failed: []`, `ruff clean: true` for task-owned scope.
  - Existing broader-file lint debt observed when linting full `engine.py` (`C901` on `sweep`) is outside task-owned CockpitView edit-title scope.
- Fixes applied: Confirmed/retained CockpitView title passthrough behavior matching AC1/AC2/AC4 and validated AC3 via existing cockpit-view tests.
[[2026-04-27]]
## Review Evidence
### Test Results
- quality-runner scoped: pytest 69 passed, 0 failed, 0 skipped on `tests/test_engine_cockpit_view_1141.py` and `tests/test_engine_cockpit_view_1078.py`

### Lint
- quality-runner scoped: clean on `tests/test_engine_cockpit_view_1141.py` and `tests/test_engine_cockpit_view_1078.py`
- quality-runner full surfaced unrelated lint in `serve/knowledge`, `serve/mcp-knowledge`, `serve/mcp-memory`, and `serve/orchestrator`; not blocking task 1141

### Coverage
- quality-runner scoped: `owlbear_kanban.engine` 40% when measured only against the 1141 + 1078 test subset
- quality-runner full: `owlbear_kanban.engine` 95% (1431 lines, 71 missing)
- Reviewer decision uses the broader module baseline for this large shared engine module; coverage gate satisfied

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| CockpitView.edit_task accepts `title: str | None = None` parameter | `test_edit_task_signature_has_title_param`, `test_edit_task_title_param_default_is_none` | Yes — removing the param or changing its default breaks the signature assertions in `tests/test_engine_cockpit_view_1141.py:124-141` | COVERED |
| When title is not None, it is forwarded as `kwargs["title"] = title` to `engine.edit_task` | `test_edit_task_with_title_updates_task_title` | Yes — removing `kwargs["title"] = title` at `serve/kanban/src/owlbear_kanban/engine.py:3176` leaves the returned task title unchanged and fails the exact equality assertion in `tests/test_engine_cockpit_view_1141.py:147-159` | COVERED |
| Existing CockpitView tests pass unchanged | `test_edit_task_signature_has_expected_updated_param`, `test_edit_task_expected_updated_is_required_no_default`, `test_edit_task_matching_expected_updated_returns_single_task_response`, `test_cockpit_view_edit_task_emits_source_cockpit` plus the rest of `tests/test_engine_cockpit_view_1078.py` | Yes — scoped quality-runner run reports 69 passed / 0 failed, including the existing 1078 regression file | COVERED |
| New test: `CockpitView.edit_task(task_id, expected_updated=..., title="New")` updates title | `test_edit_task_with_title_returns_response_with_updated_title` | Yes — the literal scenario in `tests/test_engine_cockpit_view_1141.py:182-194` asserts the updated title exactly | COVERED |

#### Security Review
- No task-scoped security issue found in the reviewed facade slice
- Background note only: empty-title validation asymmetry is pre-existing engine/route behavior, not introduced by 1141. The current cockpit route already accepts `title` directly in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:37,119-125,202-220`, while `create_task` alone enforces non-empty titles at `serve/kanban/src/owlbear_kanban/engine.py:2435-2438`

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| 1141 TestFromAC suite (6 tests listed in Test-Writer Notes) | Current file still contains the same six methods/categories in `tests/test_engine_cockpit_view_1141.py` | PRESERVED |
| 1078 OCC/source regression tests | Current file still contains the expected-updated and source assertions in `tests/test_engine_cockpit_view_1078.py:197-244` and `tests/test_engine_cockpit_view_1078.py:1066-1080` | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | The 1141 tests assert exact title equality against a real file-backed engine response in `tests/test_engine_cockpit_view_1141.py:147-194`; removing the `title` forward at `serve/kanban/src/owlbear_kanban/engine.py:3176` causes those assertions to fail |
| Negative/error-path coverage | ADEQUATE | Existing 1078 regression tests cover stale `expected_updated` and normal edit flow in `tests/test_engine_cockpit_view_1078.py:197-244`; 1141 adds the title-specific signature/default and happy-path checks |
| Manual mutation reasoning | ADEQUATE | Removing `kwargs["title"] = title` at `serve/kanban/src/owlbear_kanban/engine.py:3176` or breaking `expected_updated` handling causes 1141/1078 tests to fail |
| Test independence | STRONG | Each test uses a fresh `tmp_path` board helper; no shared mutable state |
| Descriptive test names | STRONG | Test names are explicit about signature, title update, and cockpit-view behavior |

#### Data Safety
- No new race or atomicity issue found in the reviewed slice
- CockpitView still funnels edits through a single `engine.edit_task` OCC write path

#### Implementation-Aware Gaps
- No blocking untested path found inside the task slice
- Optional future hardening only: add an explicit empty-title validation test if edit-title validation becomes part of scope in a later task

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Live code already contained the AC1/AC2 title passthrough in `serve/kanban/src/owlbear_kanban/engine.py:3151-3207` by review time; builder correctly validated the existing implementation rather than forcing an unnecessary diff
- Scoped-only coverage on the large shared `engine.py` module is misleading; the broader full coverage run establishes the real module baseline at 95%

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| CockpitView.edit_task accepts `title: str | None = None` parameter | `serve/kanban/src/owlbear_kanban/engine.py:3151-3156`; `tests/test_engine_cockpit_view_1141.py:124-141` | `test_edit_task_signature_has_title_param`, `test_edit_task_title_param_default_is_none` | PASS |
| When title is not None, it is forwarded as `kwargs["title"] = title` to `engine.edit_task` | `serve/kanban/src/owlbear_kanban/engine.py:3175-3176,3207`; `tests/test_engine_cockpit_view_1141.py:147-159` | `test_edit_task_with_title_updates_task_title` | PASS |
| Existing CockpitView tests pass unchanged | quality-runner scoped run: 69 passed, 0 failed; `tests/test_engine_cockpit_view_1078.py:197-244,1066-1080` | existing 1078 regression suite | PASS |
| New test: `CockpitView.edit_task(task_id, expected_updated=..., title="New")` updates title | `tests/test_engine_cockpit_view_1141.py:182-194` via the live `engine.edit_task` path in `serve/kanban/src/owlbear_kanban/engine.py:3207` | `test_edit_task_with_title_returns_response_with_updated_title` | PASS |

### Deductions
- Minor premise drift only: the task body context lagged the live code, which already contained the facade forwarding path by review time
- No blocking deductions

### Verdict
- PASS -> docs
- Confidence: 0.95

### Action
- Advanced to docs

### Post-task Reflection
- Large shared modules need a broader coverage baseline before using scoped percentages as gate evidence
- Real-engine black-box tests are sufficient proof for small facade passthroughs when removing the forwarded argument changes the observable result
- Separate pre-existing route behavior from task-scoped regressions before treating a validation gap as blocking
[[2026-04-27]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | serve/kanban/README.md lists `cockpit_view()` but has no per-method param docs for CockpitView.edit_task; serve/cockpit/README.md references `engine.edit_task()` (KanbanEngine) not CockpitView. Adding `title` param to the facade doesn't affect any documented API surface. |
| 2 | Module docstrings | Yes | N/A | CockpitView.edit_task docstring: `"Edit a task with OCC compare-and-swap validation for cockpit clients."` — accurate, purpose unchanged. No update needed. |
| 3 | External attribution | No | N/A | Trivial param passthrough; no external patterns referenced. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1132-cockpit-mutation-cockpitview-wiring.md` exists and is linked from task body. Historical artifact; no update required. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` (describes: `serve/kanban/src/**`) and `share/diagrams/mcp-topology.excalidraw` (describes: `serve/mcp-*/src/**, serve/kanban/src/**`) both match `serve/kanban/src/owlbear_kanban/engine.py`. Footers updated to `Last verified: 2026-04-27 (a38d67be)`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/engine.py` | IN | Docstring checked — accurate, no update needed |
| `tests/test_engine_cockpit_view_1141.py` | OUT | Test file — not a doc target |
| `tests/test_engine_cockpit_view_1078.py` | OUT | Test file — not a doc target |
| `share/diagrams/kanban.excalidraw` | IN | Footer updated to `(a38d67be)` |
| `share/diagrams/mcp-topology.excalidraw` | IN | Footer updated to `(a38d67be)` |

### Files Updated
- `share/diagrams/kanban.excalidraw` — footer timestamp updated
- `share/diagrams/mcp-topology.excalidraw` — footer timestamp updated

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1141-*` scratch files found)
[[2026-04-27]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| CockpitView.edit_task accepts `title: str \| None = None` | engine.py L3156 signature; test_edit_task_signature_has_title_param, test_edit_task_title_param_default_is_none (tests/test_engine_cockpit_view_1141.py:124-141) | PASS |
| When title is not None, forwarded as kwargs["title"] to engine.edit_task | engine.py L3176; test_edit_task_with_title_updates_task_title (tests/test_engine_cockpit_view_1141.py:147-159) | PASS |
| Existing CockpitView tests pass unchanged | 70 passed, 0 failed across 1141+1078 test files | PASS |
| New test: CockpitView.edit_task(task_id, expected_updated=..., title="New") updates title | test_edit_task_with_title_returns_response_with_updated_title (tests/test_engine_cockpit_view_1141.py:182-194) | PASS |

### Test Results
- pytest (task-scoped): 70 passed, 0 failed
- pytest (full suite): 2566 passed, 137 failed — all failures in non-task packages (corruption, storage, mcp-models); none in task scope
- ruff (task-scoped): clean
- ruff (full): 9 violations in serve/knowledge, serve/mcp-knowledge, serve/mcp-memory, serve/orchestrator — none in task scope

### Architect Quality: 5/5
All 4 AC lines are precise, testable, and complete. Scope is correct (single param passthrough). Sentinel semantics (None vs truthiness) specified correctly in AC2.

### Deduction Breakdown
- AC lines without evidence: 0 (-.00)
- Lint violations in scope: 0 (-.00)
- AC quality ≤ 3: no (-.00)
- Missing reviewer evidence: no (-.00)
- Full-suite failures in task scope: 0 (-.00)

### Confidence: 1.00
### Action: archive

### Process Note
Test file was uncommitted by upstream agents — committed as leftover (18fc6bd0). Builder correctly identified implementation already existed and validated existing code against RED-phase tests.

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| bb52c06b | docs | share/diagrams/kanban.excalidraw, share/diagrams/mcp-topology.excalidraw | #1141 |
| 18fc6bd0 | test | tests/test_engine_cockpit_view_1141.py | #1141 |