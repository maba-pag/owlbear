---
id: 1501
title: 'Cockpit: Implement api/tasks.ts module'
status: archived
priority: needed
created: 2026-05-12T02:43:28.689799+00:00
updated: 2026-05-12T13:14:29.977127+00:00
tags:
  - cockpit
  - frontend
parent: 1493
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---

## Objective
Create `serve/cockpit/web/src/api/tasks.ts` with centralized API functions following the existing `repair.ts`/`cleanup.ts` pattern.

## Acceptance Criteria
- Exports `getTask()`, `moveTask()`, `editTask()`, `releaseTask()` async functions
- Exports `ApiError` class with `.status` property
- All functions use `getResponseErrorMessage` for error parsing and throw `ApiError` on non-ok responses
- Request/response types exported and match backend contract
- Unit tests cover success and error paths for each function

## Implementation Notes
- Follow existing pattern in `api/repair.ts` and `api/cleanup.ts`
- `ApiError` may live in a shared `api/errors.ts` if cleaner
2026-05-12T04:24:15+00:00
Moved to backlog for architecture review. Task was placed in `todo` directly by researcher without arch review or proof-bundle assignment. AC has B3 violations ("All functions") that need refinement. Proof bundle needs assignment.
2026-05-12T08:50:22+00:00

## Refined Acceptance Criteria
_Supersedes original AC. Numbered, B3-clean, challenger-validated._

- AC-1: `api/errors.ts` exports class `ApiError` extending `Error` with readonly `status: number`; `new ApiError(409, "conflict")` produces `.status === 409` and `.message === "conflict"`
- AC-2: `getTask(id, options?)` in `api/tasks.ts` sends `GET /api/tasks/{id}`, forwards `options.signal` to `fetch` when provided, returns parsed JSON as `TaskDetail` on 2xx, throws `ApiError` on non-ok
- AC-3: `moveTask(id, request)` in `api/tasks.ts` sends `POST /api/tasks/{id}/move` with JSON body, returns `TaskDetail` on 2xx, throws `ApiError` on non-ok
- AC-4: `editTask(id, request)` in `api/tasks.ts` sends `POST /api/tasks/{id}/edit` with JSON body, returns `TaskDetail` on 2xx, throws `ApiError` on non-ok
- AC-5: `releaseTask(id, request)` in `api/tasks.ts` sends `POST /api/tasks/{id}/release` with JSON body, returns `TaskDetail` on 2xx, throws `ApiError` on non-ok
- AC-6: On non-ok response, `getTask`, `moveTask`, `editTask`, and `releaseTask` extract error message via `getResponseErrorMessage(response, fallback)` before throwing `ApiError`; network errors (fetch rejection) propagate unwrapped
- AC-7: `api/tasks.ts` exports request interfaces: `MoveRequest` (`status: string`, `updated: string`, optional `archival_reason: string | null`, `archival_refs: number[] | null`), `EditRequest` (`updated: string`, optional `title: string | null`, `tags: string[] | null`, `priority: string | null`, `depends_on: number[] | null`, `parent: number | null`, `block_reason: string | null`, `body: string | null`), `ReleaseRequest` (`updated: string`)
- AC-8: `api/tasks.ts` exports response interface `TaskDetail` with fields: `id: number`, `title: string`, `status: string`, `priority: string`, `updated: string`, `created: string`, `body: string | null`, `tags: string[]`, `blocked: boolean`, `block_reason: string | null`, `claimed: boolean`, `claimed_at: string | null`, `dep_status: string | null`, `parent: number | null`, `depends_on: number[]`

Proof bundle: behavioral

## Implementation Notes (updated)
- `ApiError` in `api/errors.ts` (shared with #1502 api/decisions.ts)
- Follow `api/repair.ts` / `api/cleanup.ts` pattern for function structure
- `TaskDetail` is a frontend-scope interface covering consumer-needed fields; backend `SingleTaskResponse` and `ShowTaskResponse` share this subset — extra server fields (e.g. `guidance`, `missing_sections`) are silently dropped by TypeScript structural typing
- `EditRequest` optional fields use `T | null` types to support backend tri-state (omit = no change, null = clear, value = set) semantics
- Network errors (fetch throws) propagate as-is; `ApiError` wraps HTTP-level errors only
- `getTask` accepts optional `{ signal?: AbortSignal }` — Shell.tsx passes abort signals to task fetches; mutation functions do not need signal support (no current callers pass signals)
2026-05-12T08:50:49+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One module (api/tasks.ts) + shared error class (api/errors.ts) — single domain concern |
| Interface clarity | PASS | AC-1..AC-8 specify exact function signatures, input types with nullability, response fields, and error semantics |
| Dependency correctness | PASS | No depends_on needed; #1502 correctly depends on #1501 for ApiError; #1503 depends on both |
| Module layering | PASS | api/ sits between components and backend; no upward imports; ApiError in shared api/errors.ts |
| TDD compliance | PASS | Behavioral proof bundle assigned; test-writer derives RED tests from AC-1..AC-8 |
| KISS/YAGNI | PASS | Follows established repair.ts/cleanup.ts pattern; AbortSignal only on getTask (evidence: Shell.tsx); no signal on mutations (no callers use it) |
| Premise challenge | PASS | 8+ raw fetch sites across 5 components justify centralization; pattern already proven by repair.ts/cleanup.ts |
| Pattern consistency | PASS | Matches existing api/ module pattern; ApiError upgrade is additive (justified by DetailTab 409/404/422 branching) |
| Security surface | PASS | Internal SPA→backend fetch calls; no new system boundaries |
| Single domain | PASS | Frontend API client domain |

### Challenger Results
- Challenger: reconsider (0.62)
- Findings addressed:
  1. **ShowTaskResponse vs SingleTaskResponse divergence** — Accepted. TaskDetail scoped to consumer-needed fields (subset); extra server fields dropped by TypeScript structural typing. AC-8 enumerates exact fields. Implementation note added.
  2. **AC-7 nullability/tri-state** — Accepted. EditRequest fields now explicitly typed as `T | null`. Implementation note added about tri-state semantics.
  3. **AbortSignal for getTask** — Accepted. AC-2 now includes `options.signal` forwarding. Mutations kept signal-free (no callers pass signals).
  4. **Error handling divergence** — Accepted as minor. AC-6 now specifies network errors propagate unwrapped (only HTTP errors become ApiError).
  5. **Consolidation-test gap** — Noted, minor. #1503 (consumer migration with behavioral-preservation AC) serves as integration verification.
- Architect response: revised AC based on findings 1-4; noted finding 5 without action

### Proof-Bundle Validation
- Planner assignment: none
- Final bundle: behavioral
- Test-writer: PROCEED

### Design Diverge
- Trigger: skipped — single viable approach (established repair.ts/cleanup.ts pattern + ApiError); no competing designs

### AC Refinement Summary
Original AC had B3 violations ("All functions"), no numbering, vague "match backend contract", and meta-AC about test existence. Refined to 8 numbered, B3-clean AC lines with exact function signatures, enumerated field types with nullability, explicit error semantics, and AbortSignal support where needed.

### Verdict: APPROVE (REFINE + approve)
### Action Taken: Refined AC (B3 fix, numbering, challenger-driven improvements), assigned proof bundle behavioral, advanced to todo
2026-05-12T09:17:04+00:00
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/tasks_1501.test.ts
- Classes: TestFromAC_ApiError, TestFromAC_GetTask, TestFromAC_MoveTask, TestFromAC_EditTask, TestFromAC_ReleaseTask, TestFromAC_RequestInterfaces, TestFromAC_TaskDetailInterface
- Tests per category: happy 22, edge 4, error 16, boundary 8 (interface structural 15)
- Total: 65 tests, all FAIL (module resolution error — api/errors.ts and api/tasks.ts do not exist)
- eslint: clean
- AC coverage: AC-1 (8 tests), AC-2 (12 tests), AC-3 (8 tests), AC-4 (8 tests), AC-5 (8 tests), AC-6 covered in each function group, AC-7 (5 tests), AC-8 (14 tests)
2026-05-12T09:48:21+00:00
## Builder Notes
- Files changed:
  - serve/cockpit/web/src/api/errors.ts
  - serve/cockpit/web/src/api/tasks.ts
- Implementation summary:
  - Added `ApiError` class in `api/errors.ts` with readonly `status` and Error inheritance behavior per AC-1.
  - Added `api/tasks.ts` exporting `TaskDetail`, `MoveRequest`, `EditRequest`, `ReleaseRequest`, and async functions `getTask`, `moveTask`, `editTask`, `releaseTask`.
  - All four API functions call `getResponseErrorMessage(response, fallback)` on non-ok HTTP responses, then throw `ApiError(status, message)`.
  - Network errors are not wrapped (no try/catch around fetch), so fetch rejections propagate as-is per AC-6.
  - `getTask` forwards optional `options.signal` to fetch; mutation functions post JSON bodies to expected endpoints.
- RED verification (quality-runner):
  - tests: 0 passed, import-phase failure confirmed for missing `../api/errors` and `../api/tasks`
  - lint: clean
- GREEN verification (quality-runner):
  - tests: 65 passed, 0 failed, 0 skipped (`serve/cockpit/web/src/__tests__/tasks_1501.test.ts`)
  - coverage: overall 90.32%; `src/api/tasks.ts` 100%, `src/api/errors.ts` 100%
  - lint: clean (no violations)
- Module-level durable test visibility:
  - No durable module-level tasks API test file found; task-scoped behavioral suite used as required proof.
- Commit:
  - 2147d78ff451262c5546aeef36265193606a85ee
  - feat: implement cockpit tasks api client (#1501, builder)
- Evidence summary:
  - AC-1..AC-8 implemented and validated by passing TestFromAC suite and clean lint/coverage gates.
2026-05-12T10:30:11+00:00
## Review Evidence
- Verdict: FAIL
- FAIL route: FAIL #1501 -> backlog | AC-7 contract/proof packet is unsound: the task packet approves a generic `null = clear` EditRequest story that conflicts with backend semantics, and the recorded GREEN evidence does not mechanically prove the type-only exports.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-7 | The task packet and task-scoped tests approve a generic `null = clear` story for `EditRequest`, but the backend contract is field-specific: `body: ""` clears, `body: null` is no-op, and list clears use `[]`, not `null`. That means the reviewed contract is incorrect before downstream consumers adopt it. | `.owlbear/kanban/tasks/1501-cockpit-implement-api-tasks-ts-module.md:55,79`; `serve/cockpit/web/src/__tests__/tasks_1501.test.ts:491-504`; `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:51-67,176-204`; `tests/test_cockpit_mutation_api.py:883-1049` | backlog |
| 2 | AC-7, AC-8 | The proof for the exported interfaces is structurally weak. The recorded GREEN evidence is Vitest + coverage + lint, but the interface assertions live in a test file excluded from project typecheck, so the runtime suite is not a reliable gate for type-only export regressions. | `.owlbear/kanban/tasks/1501-cockpit-implement-api-tasks-ts-module.md:102,120-122`; `serve/cockpit/web/package.json:11`; `serve/cockpit/web/tsconfig.json:17-18`; `serve/cockpit/web/src/__tests__/tasks_1501.test.ts:481-507,521-574` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC-7 and the task implementation notes to describe field-specific `EditRequest` clear/no-op semantics that match the backend contract instead of the generic `null = clear` rule. | `.owlbear/kanban/tasks/1501-cockpit-implement-api-tasks-ts-module.md`; `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`; `tests/test_cockpit_mutation_api.py` | Review finding #1 |
| 2 | architect | Redefine the proof requirement for AC-7 and AC-8 so type-only exports are gated by compile-checked evidence rather than runtime-only Vitest assertions in excluded test files. | `.owlbear/kanban/tasks/1501-cockpit-implement-api-tasks-ts-module.md`; `serve/cockpit/web/package.json`; `serve/cockpit/web/tsconfig.json`; `serve/cockpit/web/src/__tests__/tasks_1501.test.ts` | Review finding #2 |

## Observations
- Direct file review confirms AC-1 through AC-6 are implemented cleanly in `serve/cockpit/web/src/api/errors.ts` and `serve/cockpit/web/src/api/tasks.ts`, and editor diagnostics on the new files plus the task-scoped test file are clean.
- I did not independently rerun the frontend suite because the builder evidence for runtime behavior was internally consistent; the rejection is about contract quality and proof quality, not a contradictory test report.
- I could not independently verify git-scope contamination for the builder commit in this tool surface because no git/terminal execution tool was available.
2026-05-12T11:09:47+00:00
## AC Refinement (post-review cycle 2)
_Supersedes AC-7 from previous "Refined Acceptance Criteria" section. AC-1..AC-6, AC-8 unchanged._

- AC-7 (revised): `api/tasks.ts` exports request interfaces with TypeScript `?:` optional modifiers:
  - `MoveRequest`: `{ status: string; updated: string; archival_reason?: string | null; archival_refs?: number[] | null }`
  - `EditRequest`: `{ updated: string }` with per-field optional semantics matching backend `_build_edit_kwargs` (Pydantic `model_fields_set` distinguishes omit from explicit null):
    | Field | Omit | null | Empty (`""`/`[]`) | Value |
    |-------|------|------|-------------------|-------|
    | `title?: string \| null` | no change | no change | — | set title |
    | `priority?: string \| null` | no change | no change | — | set priority |
    | `parent?: number \| null` | no change | clear parent | — | set parent |
    | `body?: string \| null` | no change | no change | `""` = clear body | set body |
    | `tags?: string[] \| null` | no change | no change | `[]` = remove all | full-replace (server diff) |
    | `depends_on?: number[] \| null` | no change | no change | `[]` = remove all | full-replace (server diff) |
    | `block_reason?: string \| null` | no change | unblock | `""` = unblock | non-empty string = set + block |
  - `ReleaseRequest`: `{ updated: string }`
- AC-9 (new): `tsc --noEmit` (or equivalent `tsc -b` via `npm run build`) exits clean with `api/tasks.ts` and `api/errors.ts` in compilation scope; verified by build-script output

## Implementation Notes (revised, post-review cycle 2)
- `EditRequest` optional fields use `?:` TypeScript modifiers; `JSON.stringify` omits `undefined` properties (= backend no-op), includes `null` (= field-specific behavior per AC-7 table). NOT a uniform "null = clear" pattern.
- `TaskDetail` is a narrowed frontend projection of backend `ShowTaskResponse`/`SingleTaskResponse`; extra server fields (`guidance`, `missing_sections`) are silently dropped by TypeScript structural typing.
- Proof evidence must include `tsc --noEmit` or `npm run build` output alongside Vitest results (addresses reviewer Finding 2: compile-checked evidence for type-only exports).
- The `api/tasks.ts` module is not yet imported by production components — consumer migration is #1503's scope. Current proof covers module-level correctness (compile + behavioral tests); integration proof comes from #1503.

Proof bundle: behavioral
2026-05-12T11:10:09+00:00
## Architecture Review (cycle 2)

### Trigger
Reviewer rejected #1501 with two findings: (1) AC-7 documented generic "null = clear" EditRequest semantics that conflict with per-field backend behavior in `_build_edit_kwargs`, (2) type-only export proof relied on runtime Vitest assertions in test files excluded from `tsconfig.json` typecheck.

### AC Assessment
| AC | Assessment | Action |
|----|-----------|--------|
| AC-1..AC-6 | PASS — unchanged, reviewer confirmed clean | None |
| AC-7 | FAIL — generic "null = clear" story incorrect | REVISED: per-field semantics table matching `_build_edit_kwargs` in `mutation.py` |
| AC-8 | PASS — field enumeration correct | None (proof concern addressed by AC-9) |
| AC-9 | NEW — tsc compile-time evidence for type exports | Added: `tsc --noEmit` gate |

### Architecture Notes
- Implementation code (`api/tasks.ts`, `api/errors.ts`) is already correct — TypeScript `?:` optional modifiers properly distinguish omit (undefined → JSON omits → backend no-op) from null (JSON includes → field-specific behavior). No code changes needed.
- The per-field semantics table in revised AC-7 was verified against `_build_edit_kwargs` in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:176-210`.
- `TaskDetail` is a narrowed projection of backend `ShowTaskResponse`; extra fields dropped by structural typing — documented in implementation notes.

### Challenger Results
- Challenger: reconsider (0.41)
- 5 findings evaluated:
  1. **tsc not in AC** — ACCEPTED. Added AC-9.
  2. **No production imports** — OVERRIDDEN. By design: #1501 creates module, #1503 migrates consumers. Integration proof is #1503's responsibility.
  3. **ERR_NO_OP missing** — OVERRIDDEN. Frontend is a fetch wrapper; backend validation rules are backend AC, not frontend AC. Non-ok responses covered by AC-4/AC-6.
  4. **AC-7 scope** — PARTIALLY ACCEPTED. Kept single AC-7 but added clear sub-structure with per-field table.
  5. **Consolidation-test gap** — NOTED. #1503 migration with behavioral-preservation AC serves as practical integration verification.

### Proof-Bundle Validation
- Previous assignment: behavioral
- Final: behavioral
- Added requirement: `tsc --noEmit` evidence alongside Vitest results (AC-9)

### Verdict: APPROVE (REFINE + approve)
Refined AC-7 with per-field EditRequest semantics table, added AC-9 for compile-time type evidence, updated implementation notes to remove incorrect "null = clear" generic rule.
2026-05-12T11:37:47+00:00
## Test-Writer Notes (retry cycle 2)
- Test file: serve/cockpit/web/src/__tests__/tasks_1501.test.ts
- New class: TestFromAC_EditRequestFieldSemantics (16 tests for revised AC-7 per-field semantics)
- Existing classes preserved: TestFromAC_ApiError, TestFromAC_GetTask, TestFromAC_MoveTask, TestFromAC_EditTask, TestFromAC_ReleaseTask, TestFromAC_RequestInterfaces, TestFromAC_TaskDetailInterface
- Tests per category (new): happy 0, edge 9 (omit=exclude), error 0, boundary 7 (field-specific clear signals)
- Total: 81 tests, all PASS (Step 1b.1: implementation already handles per-field serialisation via JSON.stringify)
- eslint: clean
- AC coverage: AC-7 revised (per-field semantics table: omit→absent, body=""→clear, parent=null→clear-parent, block_reason=null/""→unblock, tags=[]→remove-all, depends_on=[]→remove-all, null for title/priority/tags/depends_on/body→no-op)
- Builder skip: test-only retry, all tests green
- Reviewer note: AC-9 (tsc --noEmit clean) is compile-level proof; requires independent tsc verification — source files api/tasks.ts and api/errors.ts are in tsconfig include scope (src/), not excluded
- Commit: 9a4fa71f
2026-05-12T12:12:46+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1501 -> docs | AC mapped to code and evidence sufficient.
- AC evidence map:

| AC Line | Code Evidence | Test / Proof Evidence | Status |
|---|---|---|---|
| AC-1 | serve/cockpit/web/src/api/errors.ts:1 | serve/cockpit/web/src/__tests__/tasks_1501.test.ts:88; independent quality-runner rerun: vitest 81 passed | PASS |
| AC-2 | serve/cockpit/web/src/api/tasks.ts:57 | serve/cockpit/web/src/__tests__/tasks_1501.test.ts:133; independent quality-runner rerun: vitest 81 passed | PASS |
| AC-3 | serve/cockpit/web/src/api/tasks.ts:66 | serve/cockpit/web/src/__tests__/tasks_1501.test.ts:225; independent quality-runner rerun: vitest 81 passed | PASS |
| AC-4 | serve/cockpit/web/src/api/tasks.ts:78 | serve/cockpit/web/src/__tests__/tasks_1501.test.ts:301; independent quality-runner rerun: vitest 81 passed | PASS |
| AC-5 | serve/cockpit/web/src/api/tasks.ts:90 | serve/cockpit/web/src/__tests__/tasks_1501.test.ts:381; independent quality-runner rerun: vitest 81 passed | PASS |
| AC-6 | serve/cockpit/web/src/api/tasks.ts:48,57,66,78,90 | serve/cockpit/web/src/__tests__/tasks_1501.test.ts:133,225,301,381; independent quality-runner rerun: vitest 81 passed | PASS |
| AC-7 | serve/cockpit/web/src/api/tasks.ts:22,29,40 | serve/cockpit/web/src/__tests__/tasks_1501.test.ts:446,625,677,683,691,699,705,713,727; backend contract cross-check at serve/cockpit/src/owlbear_cockpit/routes/mutation.py:181,183,185,187,190,198,207,227 and tests/test_cockpit_mutation_api.py:891,921,998,1015 | PASS |
| AC-8 | serve/cockpit/web/src/api/tasks.ts:4 | serve/cockpit/web/src/__tests__/tasks_1501.test.ts:522; direct interface inspection | PASS |
| AC-9 | serve/cockpit/web/package.json:11; serve/cockpit/web/tsconfig.json:17-18 | independent quality-runner rerun: build exit 0, eslint clean, errors none | PASS |

- Blocking findings: none.

## Observations
- Independent quality-runner verification was required because cycle-2 introduced AC-9 but the retry packet only noted that compile proof was required; it did not include the actual compile output. The rerun closed that gap with vitest 81 passed, eslint clean, and build exit 0.
- The earlier AC-7 contract issue is resolved: the current EditRequest typing in serve/cockpit/web/src/api/tasks.ts:29 and the revised field-semantics tests at serve/cockpit/web/src/__tests__/tasks_1501.test.ts:625 agree with the backend edit semantics in serve/cockpit/src/owlbear_cockpit/routes/mutation.py:181-227.
- Behavioral-bundle coverage remains sufficiently evidenced from the builder packet (`src/api/tasks.ts` 100%, `src/api/errors.ts` 100%) because cycle-2 was an explicit builder-skip test-only retry with no claimed source changes.
- Challenger cross-check: proceed (0.81). Remaining risk is deferred consumer integration in #1503, which is outside #1501 scope and not a blocker for this module task.
2026-05-12T12:40:50+00:00
## Docs Gate

**Verdict: PASS — no docs impact**

### Checklist

| Item | Result | Evidence |
|------|--------|---------|
| 1. README Verification | N/A — no update needed | Layer 1 grep: no references to `api/tasks`, `api/errors`, `api/repair`, `api/cleanup`, or `ApiError` in `serve/cockpit/README.md`. Existing undocumented pattern confirmed (repair.ts/cleanup.ts absent). Layer 2 editorial: tri-state semantics table in README matches revised AC-7; no contradictions. |
| 2. External Attribution | N/A | No external sources cited in task body. |
| 3. Research Doc | N/A | No research document for this task. |
| 4. Deletion Detection | N/A | All changed files are additions: `api/errors.ts`, `api/tasks.ts`, `src/__tests__/tasks_1501.test.ts`. |

### Scratch Cleanup

No `.owlbear/scratch/1501-*` files found.
2026-05-12T13:14:29+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: Python 4419 passed, 20 failed (pre-existing in unrelated modules: test_cockpit_view, test_engine_accessor_migration, test_server, test_ideation_diagram — last modified at 6e3a195c MegaLinter commit), 5 timeouts (test_cockpit_pds_build_compat). Frontend vitest 81 passed, eslint clean, build exit 0.\n- regression verdict: PASS — no failures attributable to #1501\n\n### Intent Verification\n- scope alignment: PASS (all changed files in serve/cockpit/web/src/api/ — correct frontend API domain)\n- purpose match: PASS (api/errors.ts exports ApiError, api/tasks.ts exports getTask/moveTask/editTask/releaseTask + types — matches task objective)\n- extraneous scope: none (builder commit 2147d78f: 2 files; test-writer commits e5274149 + 9a4fa71f: 1 file each)\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 3/5\nCycle 1 AC-7 documented generic \"null = clear\" EditRequest semantics that conflicted with backend per-field behavior in _build_edit_kwargs. This was caught by the reviewer (2nd line), not by the architect's own quality controls. Cycle 2 refinement was thorough: per-field semantics table matching backend contract, AC-9 added for tsc compile evidence. Final AC set is specific and well-structured, but the initial gap required a full review-rejection cycle.\n\n### Commit Integrity\n- upstream commit presence: PASS (builder 2147d78f, test-writer e5274149 + 9a4fa71f — all tagged #1501 with agent roles)\n- kanban commit packaging: pending (post-archive)\n\n### Deduction Breakdown\n- AC quality score 3/5: -.03\n\n### Confidence: .97\n### Action: archive"