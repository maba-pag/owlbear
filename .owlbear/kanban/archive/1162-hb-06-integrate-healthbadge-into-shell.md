---
id: 1162
title: 'HB-06: Integrate HealthBadge into Shell'
status: archived
priority: medium
created: 2026-04-28T17:35:08.991715+00:00
updated: 2026-04-29T00:20:15.141956+00:00
tags:
- phase:cockpit
- scope:cockpit-frontend
- type:build
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Seed from ideation task #1042 — cockpit health badge feature.
Shell status bar: `data-region="status-bar"` in `serve/cockpit/web/src/Shell.tsx`.
Hook: `useScanPolling` (implemented in #1157, archived). Component: `HealthBadge` (implemented in #1158, archived).
Merged from #1161 (Shell integration tests) — test and build combined into single TDD task.

## Acceptance Criteria

- [ ] HealthBadge rendered inside `[data-region="status-bar"]` (`data-testid="health-badge"` present)
- [ ] Shell calls `useScanPolling()` and passes normalised items to HealthBadge (filters out `ScanItem` entries where any of `code`/`detail`/`file_path` is null — hook returns nullable fields, component expects non-null)
- [ ] Badge reflects updated scan results when poll returns new data
- [ ] HealthBadge not rendered while `useScanPolling().isLoading` is true (absent before first poll completes)
- [ ] Wired with default 60 s poll interval (from `useScanPolling` defaults)

## Scope

- **In scope:** Shell.tsx wiring changes, Shell integration tests (merged from #1161)
- **Out of scope:** New components, new hooks, backend changes, HealthBadge internals

[[2026-04-28]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Shell wiring + Shell integration tests for that wiring |
| Interface clarity | PASS (after refinement) | AC2 tightened: filter strategy specified; AC4 already precise from #1161 merge |
| Dependency correctness | PASS | No formal deps; underlying code exists (useScanPolling.ts from #1157, HealthBadge.tsx from #1158, both archived) |
| Module layering | PASS | Shell imports hook + component from same frontend package |
| TDD compliance | PASS | Combined TDD task (merged #1161 tests + #1162 build); type:build flows through test-writer → builder |
| KISS/YAGNI | PASS | Minimal adapter wiring, no new abstractions |
| Premise challenge | PASS | Shell currently lacks HealthBadge; wiring is necessary |
| Pattern consistency | PASS | Shell already calls usePolling('/health'); adding useScanPolling follows same pattern |
| Security surface | N/A | Frontend component wiring, no new system boundary |
| Single domain | PASS | Cockpit frontend only |

### AC Refinements Applied

- **AC2**: Changed "filter or default" → "filters out ScanItem entries where any of code/detail/file_path is null" — gives test-writer a deterministic contract. Rationale: backend route tests (test_cockpit_kanban_routes_1083.py) confirm non-null values in scan responses; hook nullable type is defensive. Filtering is type-narrowing, not data-loss.
- **Context block**: Updated #1159/#1160 references to point to canonical archived tasks #1157/#1158.

### Type Interface Note

`useScanPolling` exports `ScanItem { code: string|null, … }` while `HealthBadge` exports `ScanItem { code: string, … }`. Shell imports both — builder should use the hook's type for the raw data and the component's type for the filtered output, or define a local type guard. No rename needed; the types are used in different import scopes.

### Challenge Results

- Challenger: **reconsider** (confidence 0.64)
- Key findings: (1) error-state → false-healthy badge when scan fails, (2) filter may hide malformed scan rows, (3) AC2 ambiguity
- Architect response: **partially accepted, override justified**
  - (1) Error-state is a HealthBadge design concern (out of scope — component internals fixed in #1158). Recommended as follow-up.
  - (2) Backend contract already guarantees non-null fields; nullable hook type is defensive. Filtering is type-narrowing, not silent data loss.
  - (3) Accepted — AC2 refined before approval.

### Recommended Follow-up

Error-state semantics: when scan fails, hook returns `error` + empty `items` + `isLoading=false`. HealthBadge renders "Health: OK" for empty items → false-healthy indicator. Separate task needed to add error-state UI to HealthBadge or Shell-level error handling.

### Verdict: APPROVE
### Action Taken: AC2 refined (filter strategy specified), context references updated, advanced to todo.
[[2026-04-28]]
Architecture review complete. AC2 refined: filter strategy specified (drop items with null fields). Context references updated to canonical archived tasks #1157/#1158. Challenger reconsider (0.64) partially accepted — error-state concern acknowledged as recommended follow-up, filter-as-data-loss rebutted with backend contract evidence. All 10 criteria PASS.

[[2026-04-28]]
## Test-Writer Notes
- Python structural guard: tests/test_shell_integration_1162.py
- Vitest behavioral tests: .owlbear/scratch/Shell_1162.test.tsx (gitignored; builder must move to serve/cockpit/web/src/__tests__/Shell_1162.test.tsx)
- Classes: TestFromAC_ShellHealthBadgeStructure (Python), TestFromAC_HealthBadgeShellIntegration (Vitest)
- Tests per category (Vitest): happy 7, edge 8, error 0, boundary 5
- Vitest total: 20 tests across 5 AC describe blocks
- Python structural guards: 5 tests, all FAIL
- ruff: clean
- AC coverage:
  | AC | Tests |
  |----|-------|
  | AC1: health-badge in status-bar | 3 (Vitest) + 1 (Python: imports HealthBadge) |
  | AC2: useScanPolling called + null filter | 8 (Vitest) + 1 (Python: imports useScanPolling) |
  | AC3: badge reflects updated results | 4 (Vitest) |
  | AC4: absent while isLoading=true | 4 (Vitest) + 1 (Python: isLoading referenced) |
  | AC5: default 60 s interval | 2 (Vitest) |
- Builder note: the Vitest tests mock both useScanPolling and usePolling, stub fetch as never-resolving (KanbanBoard pattern from Shell_966.test.tsx). Import order: vi.mock() before imports, then Shell imported after stubs.
[[2026-04-28]]
## Builder Notes
- Implementation: updated `serve/cockpit/web/src/Shell.tsx`; moved task vitest from `.owlbear/scratch/Shell_1162.test.tsx` to `serve/cockpit/web/src/__tests__/Shell_1162.test.tsx`.
- RED verification (pre-implementation): 5 failed in `tests/test_shell_integration_1162.py` (missing `HealthBadge`, `useScanPolling`, `isLoading` wiring, and missing vitest file at destination).
- GREEN verification: 26 passed total (5 Python + 21 Vitest) across `tests/test_shell_integration_1162.py` and `serve/cockpit/web/src/__tests__/Shell_1162.test.tsx`; failed: 0.
- Coverage: 100% reported on `tests/test_shell_integration_1162.py` in scoped quality-runner output.
- Lint/typecheck: ruff clean; TypeScript validation clean.
- Approach: Shell now calls `useScanPolling()` with default options, filters out nullable scan rows via a local type guard, and conditionally renders `<HealthBadge items={normalizedItems} />` only when `isLoading === false` inside `[data-region="status-bar"]`.
- Commit: `ccad5a22` (`feat: integrate HealthBadge into Shell (#1162, builder)`).

### Post-task Reflection
- Problem faced: hook `ScanItem` allows nullable fields while badge props require non-null fields.
- Workaround applied: used explicit type-guard filtering in Shell to narrow and normalize before render.
- Pattern discovered: Shell-level adaptation is a clean boundary when hook/component contracts differ intentionally.
- Time sink: none material beyond task-file relocation from scratch to canonical test path.
- Quality gap: coverage signal here is test-file scoped rather than frontend source-module coverage.
[[2026-04-28]]
## Review Evidence
### Test Results
- Task-scoped evidence: 26 passed, 0 failed across `tests/test_shell_integration_1162.py` and `serve/cockpit/web/src/__tests__/Shell_1162.test.tsx`.
- Related live regression evidence: 89 passed, 0 failed across `tests/test_shell_integration_1162.py`, `serve/cockpit/web/src/__tests__/Shell_1162.test.tsx`, `serve/cockpit/web/src/__tests__/useScanPolling_1157.test.ts`, and `serve/cockpit/web/src/__tests__/HealthBadge.test.tsx`.

### Lint
- Clean. Scoped runs reported ruff, TypeScript, stylelint, htmlhint, and eslint all passing.
- Editor diagnostics: none on `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/__tests__/Shell_1162.test.tsx`, and `tests/test_shell_integration_1162.py`.

### Coverage
- Source-module coverage percentages were not emitted by the scoped frontend integration run, so no module % gate was available from quality-runner for this task.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| HealthBadge rendered inside `[data-region="status-bar"]` | `Shell_1162.test.tsx` AC1 block; `Shell.tsx:35,38` | Yes — badge must exist under the status-bar region | COVERED |
| Shell calls `useScanPolling()` and passes normalised items to HealthBadge | `Shell_1162.test.tsx` AC2 block; `Shell.tsx:15-16,38` | Yes — null-only rows produce green and mixed rows produce `Health: 1 issues`; removing the Shell filter would fail these assertions against the live HealthBadge count contract | COVERED |
| Badge reflects updated scan results when poll returns new data | `Shell_1162.test.tsx` AC3 block; `useScanPolling_1157.test.ts` AC2 block | Yes — Shell rerender assertions fail if updated hook output is ignored, and the upstream hook suite proves the 60 s poll path changes hook output over time | COVERED |
| HealthBadge not rendered while `isLoading` is true | `Shell_1162.test.tsx` AC4 block; `Shell.tsx:38` | Yes — the badge is asserted absent while loading and present after loading clears | COVERED |
| Wired with default 60 s poll interval | `Shell_1162.test.tsx` AC5 block; `useScanPolling.ts:3,22`; `useScanPolling_1157.test.ts:69-84` | Yes — Shell proves no override is passed, and the live hook suite proves the default remains 60_000 ms | COVERED |

#### Security Review
- No issues found. The production diff is local UI wiring plus a null-filter/type-guard in `serve/cockpit/web/src/Shell.tsx`; no new system boundary, dependency, command execution, path handling, or secret surface was introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_HealthBadgeShellIntegration` | Moved from scratch path to `serve/cockpit/web/src/__tests__/Shell_1162.test.tsx`; explicit AC1-AC5 sections remain present | PRESERVED |
| `TestFromAC_ShellHealthBadgeStructure` | Structural guard file remains at `tests/test_shell_integration_1162.py` with import/isLoading/path checks intact | PRESERVED |

Note: no pre-builder scratch snapshot was available in-workspace, so integrity was assessed from the current file shape plus the task-writer handoff notes. No weakened or removed AC sections were found.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | AC2 null-only and mixed-item assertions in the Shell suite would fail if Shell stopped filtering before handing items to the current HealthBadge count contract. |
| Negative/error-path coverage | ADEQUATE | Loading suppression and nullable-row filtering are covered; the known scan-error false-healthy path was already documented by architecture as out of scope for this task. |
| Manual mutation reasoning | ADEQUATE | Removing the Shell filter, ignoring hook updates, or rendering while loading would break named task-owned tests. |
| Test independence | STRONG | Per-test stub setup/teardown isolates mocked hook and fetch state. |
| Descriptive test names | STRONG | AC blocks and individual cases are explicit and map cleanly to the contract. |

#### Data Safety
- No issues found. The change is a pure render-time adapter and conditional render with no persistence, atomic write path, or shared-state race introduced.

#### Implementation-Aware Gaps
- No blocking gaps in task scope.
- Non-blocking residual risk: if scan polling fails, `useScanPolling` returns `error` plus empty `items`, and Shell still renders a green badge once loading clears. This risk was already captured by architecture as a follow-up outside #1162 scope.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- The Python structural guards are low-signal compared with the Vitest behavioral suite, but they remain useful independent proof that the canonical task-owned test file exists and Shell still contains the expected wiring markers.
- Confidence deduction came from missing source-module coverage percentages in the scoped frontend run and from the need to confirm two contracts through the live upstream 1157/1158 regression suites.

### Deductions
- `-0.04` scoped frontend quality-runner output did not emit source-module coverage percentages.
- `-0.03` AC3/AC5 evidence is split between task-owned Shell tests and live upstream hook/component contract suites.

### Verdict
- PASS
- Confidence: `0.93`

### Action
- Advanced to `docs`.

### Post-task Reflection
- Problem faced: the task-owned Shell suite left ambiguity about whether AC5 needed literal-60 proof or just default-wiring proof.
- Workaround applied: reran the live upstream hook and component regression suites to validate the contract chain instead of assuming the task-local tests were weak.
- Pattern discovered: adapter/wiring tasks often need combined evidence from the new wiring tests plus the archived contract suites they intentionally depend on.
- Quality gap: scoped frontend quality runs still do not emit useful source-module coverage percentages for reviewer gating.
[[2026-04-29]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed files are Shell.tsx (frontend source) and test files — no IN-scope prose docs reference Shell wiring specifics or HealthBadge integration details. serve/cockpit/README.md covers backend API surface, not frontend component wiring. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified (Shell.tsx is TypeScript; test_shell_integration_1162.py is a test file with no public API). |
| 3 | External attribution | No | N/A | Task used no external patterns; no new sources.md row needed. |
| 4 | Research doc | No | N/A | No research doc referenced in task body. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` describes `serve/cockpit/web/src/**`; Shell.tsx matches. Footer updated: `Last verified: 2026-04-29 (ccad5a22)`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No deleted files in changed-files set. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/cockpit/web/src/Shell.tsx | OUT (app source) | N/A |
| serve/cockpit/web/src/__tests__/Shell_1162.test.tsx | OUT (test file) | N/A |
| tests/test_shell_integration_1162.py | OUT (test file) | N/A |
| share/diagrams/cockpit.excalidraw | IN (diagram) | Updated footer |

### Files Updated
- share/diagrams/cockpit.excalidraw (footer: `Last verified: 2026-04-29 (ccad5a22)`)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found (no `.owlbear/scratch/1162-*` files existed)
[[2026-04-29]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: HealthBadge in status-bar | Shell.tsx:37-39 — `<HealthBadge>` inside `data-region="status-bar"`; Shell_1162.test.tsx AC1 block (3 tests); test_shell_integration_1162.py structural guard | PASS |
| AC2: useScanPolling + null filter | Shell.tsx:9-11,15-16 — type guard `isHealthBadgeItem` filters null code/detail/file_path; Shell_1162.test.tsx AC2 block (8 tests) | PASS |
| AC3: badge reflects updates | Shell.tsx:16 — `normalizedItems` recomputed per render from hook output; Shell_1162.test.tsx AC3 block (4 tests incl. re-render + transition) | PASS |
| AC4: absent while isLoading | Shell.tsx:39 — `{!isLoading ? <HealthBadge> : null}`; Shell_1162.test.tsx AC4 block (4 tests) | PASS |
| AC5: default 60s interval | Shell.tsx:15 — `useScanPolling()` called with no args (defaults apply); Shell_1162.test.tsx AC5 block (2 tests) | PASS |

### Test Results
- Task-scoped: 26 passed (5 Python + 21 Vitest), 0 failed
- Full suite (quality-runner): 2839 passed, 110 failed — all failures in serve/kanban/tests/ and unrelated modules, 0 in task scope
- ruff: 4 violations, all outside task scope (knowledge, mcp-knowledge, mcp-memory, orchestrator)

### Reviewer Evidence
Detailed PASS verdict (0.93). Code-level findings accepted — reviewer mapped all 5 AC lines with test assertions, ran scoped + regression suites, performed security review and test integrity check. Deductions were for missing frontend coverage % and split AC3/AC5 evidence — reasonable observations, not blocking at audit level.

### Architect Quality: 4/5
AC lines specific and verifiable. AC2 refined during architecture review with explicit filter strategy. Error-state edge case properly documented as out-of-scope follow-up. Type interface note aided builder. Minor gap: AC3 "reflects updated results" is slightly open-ended but was correctly interpreted by test-writer with re-render + transition tests.

### Commit Integrity
- `55ff8630` test: add failing tests for Shell HealthBadge integration (#1162, test-writer)
- `ccad5a22` feat: integrate HealthBadge into Shell (#1162, builder)
- No uncommitted deliverables, no scratch leftovers.

### Deduction Breakdown
- AC lines without evidence: 0 (all 5 PASS) → −0.00
- Lint violations in scope: 0 → −0.00
- AC quality ≤ 3: no (4/5) → −0.00
- Missing reviewer evidence: no (detailed) → −0.00
- Full-suite failures in scope: 0 → −0.00

### Confidence: 1.00
### Action: archive