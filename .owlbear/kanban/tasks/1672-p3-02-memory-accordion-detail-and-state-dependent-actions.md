---
id: 1672
title: 'P3-02: Memory accordion detail and state-dependent actions'
status: in-progress
priority: important
created: 2026-05-18T17:44:11.043517+02:00
updated: 2026-05-27T11:51:05.851947+02:00
tags:
  - phase-3
  - scope:cockpit-web
  - frontend
parent: 1659
depends_on:
  - 1671
ac:
  - "Row click expands PAccordion showing entry content as sanitized markdown (rehype-sanitize:
    p/br/ul/ol/li/strong/em/code/a[http|https|mailto]; strip script/style/img/iframe;
    no dangerouslySetInnerHTML) plus all metadata: id, source_agent, scope_agents,
    categories, confidence, state, created_at, updated_at, approved_at (date or '-')"
  - "State-dependent action buttons: Approve (curated only, no confirm), Edit (pending/curated/approved;
    approved shows 'Editing will require re-approval'), Delete (all non-deleted; opens
    PModal [data-testid='memory-delete-confirm-dialog'] distinguishing hard-delete
    for pending vs soft-delete for curated/approved)"
  - 'Inline edit form: title/categories/confidence/scope_agents/content with char
    counter (max 1024); save POSTs /api/memories/{id}/edit with expected_updated_at;
    silent background refetch after every mutation success (approve/edit/delete);
    nav-rail badge shows pending count >0 (hidden at zero, aria-label with count)'
  - "Error UX: 409 shows inline banner 'Entry was modified — refreshing' + auto-refetch;
    404 shows 'Entry no longer exists' + removes from list; 422 shows field-level
    messages parsed from FastAPI detail array ({detail: [{loc, msg}]})"
  - "Response-driven local update: approve/edit success replaces entry from response
    payload; delete success removes (pending) or sets state='deleted' (curated/approved);
    no list spinner during mutations; on failure leave state unchanged + display per
    AC4"
  - "State promotion: edit response returning state='curated' for previously-pending
    entry updates badge immediately + shows inline note 'Promoted to curated — scope
    agents assigned'"
proof_bundle: behavioral
blocked: false
block_reason: 'test-writer crashed twice: agent returned no output on both attempts'
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1659 and `.owlbear/briefs/draft-cockpit-memory-tab/brief.md`

## Scope

Add interactive accordion detail and mutation actions to the Memory tab list.

### In Scope
- PAccordion expand on row click showing full entry detail
- Markdown content rendering with sanitization (rehype-sanitize)
- State-dependent action buttons: Approve, Edit, Delete
- Approve action: POST /api/memories/{id}/approve (curated only)
- Delete action: confirmation dialog, POST /api/memories/{id}/delete
- Edit form: inline within accordion, character counter, save/cancel
- Approved entry edit warning ("will require re-approval")
- Refetch list after every successful mutation
- Nav-rail pending count badge (visible when count > 0)
- OCC conflict handling (409 → user message to refetch)

### Out of Scope
- SSE/live updates (deferred)
- Bulk approve/delete (deferred)
- Memory creation from cockpit (deferred)
- Memory diff view (deferred)

## Technical Context
- Sanitization: rehype-sanitize or equivalent allowlist — strong, em, code, a (href validated)
- No `dangerouslySetInnerHTML`
- No remote image loading (strip img tags)
- PDS components: PAccordion, PButton, PModal (for delete confirmation), PTextarea

[[2026-05-19T20:40:14+02:00]]
## Research

Key findings documented in `.owlbear/research/memory-accordion-detail-actions.md`:

1. **PAccordion per entry** with conditional detail rendering (only render ReactMarkdown when open) — eliminates DOM weight concern
2. **Custom restrictive sanitize schema** (strong/em/code/a only; no img; href validated to http/https/mailto)
3. **Mutation asymmetry**: approve/edit return entry envelope → replace in array; delete returns `{success: true}` → remove/mark locally
4. **Structured 422 parsing**: New `parseValidationErrors()` helper needed (FastAPI returns `{detail: [{loc, msg}]}`) — current `getResponseErrorMessage` only reads string detail
5. **Nav badge state lifting**: Restore regressed decisions badge (commit a507483d was overwritten by path-normalization refactor); add `usePendingMemoryCount()` to CockpitProvider
6. **AC3+AC5 reconciliation**: Update local state from response payload immediately, then silent background refetch for consistency
7. **Edit form safety**: PAccordion `update` event fires only on summary click — form field clicks in content area do not collapse

Challenge: proceed (confidence 0.78). No additional follow-up tasks — task is well-scoped for TDD.

[[2026-05-19T20:50:25+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All items contribute to one capability: interactive detail + mutations for memory entries |
| Interface clarity | PASS (after refinement) | Refined AC1 allowlist, AC3 silent-refetch, AC5 response-driven semantics, AC4 structured 422 |
| Dependency correctness | PASS | #1671 archived (completed); no missing deps |
| Module layering | PASS | Frontend-only extension of existing MemoryTab; no upward imports |
| TDD compliance | PASS | Proof bundle behavioral; test-writer will proceed |
| KISS/YAGNI | PASS | Scope matches parent Brief; no hypothetical features |
| Premise challenge | PASS | Custom UI feature for custom app; no existing capability covers this |
| Pattern consistency | PASS | Uses established PDS components (PAccordion, PModal, PButton); ReactMarkdown+rehypeSanitize pattern from TaskFieldsEditor; CockpitProvider state-lifting from usePendingDRs |
| Security surface | PASS | Custom restrictive sanitize schema; no dangerouslySetInnerHTML; href protocol validation; img stripped |
| Single domain | PASS | All in scope:cockpit-web frontend |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| approve/edit mutation | 409 OCC conflict | HTTP 409 | Yes (AC4) | Inline banner + auto-refetch |
| approve/edit mutation | 404 not found | HTTP 404 | Yes (AC4) | Entry removed from list |
| edit mutation | 422 validation | HTTP 422 | Yes (AC4) | Field-level messages on form |
| delete mutation | 409/404 | HTTP 409/404 | Yes (AC4) | Same as above |
| markdown render | Malformed content | N/A | Yes | ReactMarkdown renders gracefully |

### Design Diverge
- Trigger: skipped — research doc already evaluated 3 approaches (PAccordion vs details vs modal); PAccordion is the clear winner per AC and PDS convention.

### Challenge Results
- Challenger: reconsider (confidence 0.61)
- Findings: (1) AC1 allowlist missing structural tags; (2) AC3/AC5 refetch-spinner conflict; (3) AC5 optimistic-vs-response-driven misnomer; (4) delete semantics underspecified
- Architect response: ACCEPTED all four findings. Refined AC1 (added p/br/ul/ol/li, explicit strip list), AC3 (silent refetch clarification), AC5 (renamed to response-driven, explicit delete handling), AC4 (inline-within-accordion scope, structured 422 detail). Challenger's nav-badge a11y point addressed in AC3 (aria-label updates with count).

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined 4 of 6 AC lines for precision (allowlist completeness, refetch semantics, delete handling, error scope). Advanced to todo.

[[2026-05-19T21:02:55+02:00]]
test-writer crashed once; releasing claim before retry: agent completed with no output

[[2026-05-19T21:05:50+02:00]]
test-writer crashed twice: agent returned no output on both attempts

[[2026-05-19T22:26:26+02:00]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx
- Classes: TestFromAC_MemoryAccordion, TestFromAC_MemoryAccordionSanitize, TestFromAC_MemoryActionButtons, TestFromAC_MemoryEditForm, TestFromAC_MemoryNavBadge, TestFromAC_MemoryErrorUX, TestFromAC_MemoryLocalUpdate, TestFromAC_MemoryStatePromotion
- Tests per category: happy 28, edge 15, boundary 4, error/security 7
- Total: 54 tests, all FAIL
- ruff: N/A (frontend); ESLint: clean; tsc: clean

AC coverage:
| AC | Tests | Classes |
|----|-------|---------|
| AC1 accordion + sanitize | 14 | TestFromAC_MemoryAccordion, TestFromAC_MemoryAccordionSanitize |
| AC2 state-dependent buttons | 13 | TestFromAC_MemoryActionButtons |
| AC3 edit form | 7 | TestFromAC_MemoryEditForm |
| AC3 nav badge | 3 | TestFromAC_MemoryNavBadge |
| AC4 error UX | 7 | TestFromAC_MemoryErrorUX |
| AC5 local update | 6 | TestFromAC_MemoryLocalUpdate |
| AC6 state promotion | 4 | TestFromAC_MemoryStatePromotion |

Key RED failures: p-accordion not rendered (li used instead), no action buttons, no edit form, no mutation logic, no memory nav badge in Shell, MEMORY_SANITIZE_SCHEMA not exported.

[[2026-05-19T22:39:30+02:00]]
## Builder Notes
- Implementation:
  - serve/cockpit/web/src/pages/MemoryTab.tsx
  - serve/cockpit/web/src/Shell.tsx
  - serve/cockpit/web/src/hooks/usePendingMemoryCount.ts
- Approach:
  - Replaced per-row `<li>` detail rendering with per-entry `p-accordion` behavior driven by `update` events.
  - Added exported `MEMORY_SANITIZE_SCHEMA` and markdown detail rendering via `ReactMarkdown + rehype-sanitize` (custom allowlist/protocols).
  - Implemented state-dependent actions (Approve/Edit/Delete), inline edit form with content char counter (1024), and delete confirmation messaging.
  - Implemented mutation flows for `/approve`, `/edit`, `/delete` with response-driven local updates.
  - Implemented AC4 error UX handling: 409 inline banner + refetch, 404 remove + message, 422 field-level messages.
  - Added state promotion feedback message for pending -> curated edit responses.
  - Added `usePendingMemoryCount` hook and wired memory nav-rail badge + aria-label updates in `Shell`.
- Tests (task-scoped):
  - `serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx`: 54 passed, 0 failed
- Durable regression tests:
  - `serve/cockpit/web/src/__tests__/MemoryTab_1671.test.tsx`
  - `serve/cockpit/web/src/__tests__/NavBadge_1646.test.tsx`
  - Combined run result: 59 passed, 0 failed
- Lint:
  - clean (eslint) on touched files and task test file
- Coverage:
  - quality-runner reported `overall_pct: none` / `modules: none` for this scoped frontend run (no coverage output in runner for this configuration)
- Commit:
  - `91cd4f75` — feat: implement memory accordion mutations and nav badge (#1672, builder)

[[2026-05-19T22:54:49+02:00]]
## Review Evidence
- Verdict: FAIL
- FAIL #1672 -> in-progress | AC2 delete confirmation is inline content instead of a confirmation dialog; AC1 proof also misses approved_at coverage and sanitize-plugin verification.
- Builder evidence reviewed first: task-scoped tests passed (54/54), durable regressions passed (59/59), eslint clean, and the builder note reported no usable coverage output (`overall_pct: none` / `modules: none`).
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC2: Delete visible for all non-deleted states (confirmation dialog with hard-delete vs soft-delete text) | The implementation renders inline confirmation copy and a confirm button inside the accordion instead of a dialog/modal, so the delete path does not satisfy the confirmation-dialog contract. | `.owlbear/kanban/tasks/1672-p3-02-memory-accordion-detail-and-state-dependent-actions.md:21-24` and `:64`; `serve/cockpit/web/src/pages/MemoryTab.tsx:740-749` render inline copy plus `memory-delete-confirm-btn`; task tests at `serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx:456-489` only match copy text and therefore miss the contract violation. | in-progress |
| 2 | AC1 / inherited brief detail metadata | The accordion detail omits `approved_at`, even though the task brief explicitly requires all metadata including `approved_at` in the inline accordion view. | `.owlbear/briefs/draft-cockpit-memory-tab/brief.md:204-219`; `serve/cockpit/web/src/pages/MemoryTab.tsx:697-703` render source/state/created/updated only; `serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx:80,95` mention `approved_at` only in fixtures and never assert it in the UI. | in-progress |
| 3 | AC1: sanitized markdown proof | The task tests do not prove the sanitize-plugin contract. `react-markdown` is mocked to a passthrough wrapper and the suite only asserts the exported schema shape, so the tests would still pass if `rehype-sanitize` were not supplied to `ReactMarkdown`. | `serve/cockpit/web/src/pages/MemoryTab.tsx:693` wires `rehypeSanitize`; `serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx:59` mocks `react-markdown`; `serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx:294-330` assert schema only; `serve/cockpit/web/src/__tests__/ResolveModal.plugins.test.tsx:91-101` shows the existing plugin-prop proof pattern. | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Replace the inline delete-confirmation block with a real confirmation dialog/modal that distinguishes hard-delete vs soft-delete, and update the task tests to assert dialog presence/semantics. | serve/cockpit/web/src/pages/MemoryTab.tsx; serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx | Finding #1 |
| 2 | builder | Render `approved_at` in the accordion metadata surface and add a task test that fails if that field is omitted. | serve/cockpit/web/src/pages/MemoryTab.tsx; serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx | Finding #2 |
| 3 | builder | Strengthen the sanitization proof so the task test asserts `ReactMarkdown` receives `rehypeSanitize` with the custom schema instead of relying on the current passthrough mock. | serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx | Finding #3 |

## Observations
- Challenger cross-check: proceed (confidence 0.81). It agreed the dialog mismatch is a clean blocker and advised treating the sanitize issue as a proof-gap rather than an implementation gap.
- The next builder proof packet should include usable coverage evidence for this behavioral bundle; the current builder note records `overall_pct: none` / `modules: none`.

[[2026-05-19T23:04:31+02:00]]
## Builder Notes
- Implementation: updated serve/cockpit/web/src/pages/MemoryTab.tsx
- Fixes applied:
  - Replaced inline delete confirmation block with a real `PModal` confirmation dialog (`memory-delete-confirm-dialog`) with cancel/confirm actions.
  - Preserved state-specific delete semantics text in the dialog:
    - pending => permanent hard-delete message
    - curated/approved => soft-delete message
  - Added missing accordion metadata rendering for `approved_at` (`Approved: {approved_at ?? '-'}`).
- Tests (task-scoped):
  - serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx: 54 passed, 0 failed
- Durable regression tests:
  - serve/cockpit/web/src/__tests__/MemoryTab_1671.test.tsx
  - serve/cockpit/web/src/__tests__/NavBadge_1646.test.tsx
  - Result: 59 passed, 0 failed
- Lint:
  - eslint clean on touched source + task test path
- Coverage evidence:
  - MemoryTab scoped coverage run (1672 only): 77.91%
  - MemoryTab combined coverage run (1672 + 1671): 83.91%
- Commit:
  - 9a80e166 — feat: enforce memory delete modal and metadata (#1672, builder)
- Evidence summary:
  - Reviewer blocking findings #1 (delete confirmation dialog contract) and #2 (approved_at metadata) addressed in code.
  - No tests were modified by builder (per builder-role constraints).

[[2026-05-20T00:02:01+02:00]]
## Review Evidence
- Verdict: FAIL
- FAIL #1672 -> backlog | Second review cycle: the source now satisfies the prior code defects, but task-local proof still does not cover the modal contract, `approved_at` metadata, `ReactMarkdown` sanitize wiring, or success-path refetch.
- Builder evidence reviewed first: task suite `serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx` passed 54/54, durable regressions passed 59/59, eslint was reported clean, coverage was reported as 77.91% scoped and 83.91% combined, and editor diagnostics are clean for `serve/cockpit/web/src/pages/MemoryTab.tsx` and `serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx`.
- Current source check: `serve/cockpit/web/src/pages/MemoryTab.tsx:698` wires `rehypeSanitize` into `ReactMarkdown`, `serve/cockpit/web/src/pages/MemoryTab.tsx:709` renders `Approved: {entry.approved_at ?? '-'}`, and `serve/cockpit/web/src/pages/MemoryTab.tsx:849-876` now renders a real `PModal` delete confirmation dialog.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1: sanitized markdown plus all metadata fields | The retry fixed the implementation, but the task tests still do not prove `approved_at` is part of the rendered metadata surface. The suite asserts `source_agent`, `confidence`, and `created_at`/`updated_at`, while `approved_at` appears only in fixtures. | Source renders the field at `serve/cockpit/web/src/pages/MemoryTab.tsx:709`; metadata assertions stop at `serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx:240`, `:247`, and `:254`; fixture-only `approved_at` references are at `serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx:80` and `:95`. | backlog |
| 2 | AC1: sanitized markdown proof | The task tests still do not prove that `ReactMarkdown` receives `rehype-sanitize` with the custom schema. `react-markdown` is mocked as a passthrough wrapper and the suite only inspects exported schema shape, so the tests would still pass if the plugin wiring disappeared. | Source wiring is at `serve/cockpit/web/src/pages/MemoryTab.tsx:698`; the passthrough mock is at `serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx:58-61`; schema-only checks are at `serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx:294-330`; an existing proof pattern that inspects `rehypePlugins` exists at `serve/cockpit/web/src/__tests__/ResolveModal.plugins.test.tsx:91-101`. | backlog |
| 3 | AC2: delete confirmation dialog | The retry fixed the implementation, but the task tests still do not prove the dialog contract. The AC2 tests only match confirmation copy in `container.textContent`, and the AC5 delete tests click the confirm button only if it happens to exist rather than asserting that the dialog appears. Inline confirmation text would still false-green these tests. | Source modal is at `serve/cockpit/web/src/pages/MemoryTab.tsx:849-876`; AC2 delete tests are at `serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx:456-489`; conditional confirm-button checks are at `serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx:919` and `:942`. | backlog |
| 4 | AC3: silent background refetch after mutation success | The source refetches after approve, delete, and edit success, but the task suite does not prove the success-path refetch requirement. The only explicit refetch assertion is for the 409 conflict path. | Success-path refetch calls are at `serve/cockpit/web/src/pages/MemoryTab.tsx:503`, `:522`, and `:570`; the only task-local refetch assertion is `serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx:751-766`. | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-scope AC1 proof so the next RED pass must assert `approved_at` rendering and must verify `ReactMarkdown` receives `rehypeSanitize` with the custom schema, not just schema shape. | serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx; serve/cockpit/web/src/pages/MemoryTab.tsx | Findings #1-#2 |
| 2 | architect | Re-scope AC2/AC3 proof so the next RED pass must assert modal presence/semantics for delete confirmation and explicit success-path refetch behavior for approve, edit, and delete. | serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx; serve/cockpit/web/src/pages/MemoryTab.tsx | Findings #3-#4 |

## Observations
- Challenger cross-check: reconsider (confidence 0.67). It agreed the remaining blockers are proof gaps rather than live implementation defects and surfaced the missing success-path refetch proof as an additional blocker.
- I did not dispatch `quality-runner` because the builder evidence was internally consistent; the rejection is based on weak or missing assertions visible in the checked-in task tests.
- Non-blocking note: `serve/cockpit/web/src/pages/MemoryTab.tsx:477` currently renders `Entry was modified - refreshing`, while AC4 quotes `Entry was modified — refreshing`; the current task tests only assert the substring `Entry was modified` at `serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx:735-748`. This is not part of the blocking verdict.

[[2026-05-20T00:11:57+02:00]]
## Proof Guidance (reviewer-cycle-2 findings)

The implementation is complete and correct. The following proof gaps caused the second rejection — the test-writer must address all four:

1. **AC1 sanitize plugin wiring:** Do NOT mock react-markdown as a passthrough. Instead, mock it so that `vi.mocked(ReactMarkdown).mock.calls` can be inspected to verify `rehypePlugins` contains `rehypeSanitize` with `MEMORY_SANITIZE_SCHEMA`. Follow the existing proof pattern at `serve/cockpit/web/src/__tests__/ResolveModal.plugins.test.tsx:91-101`.

2. **AC1 approved_at metadata:** Add a test that renders an entry with `approved_at: '2026-03-15T10:00:00Z'` and asserts the accordion detail contains that date string. Current tests cover source_agent/confidence/timestamps but not approved_at.

3. **AC2 delete modal element:** Tests must assert `container.querySelector('[data-testid=\"memory-delete-confirm-dialog\"]')` is non-null after clicking delete — proving a real PModal renders, not just checking page textContent. Remove conditional `if (confirmBtn)` guards; assert the confirm button exists.

4. **AC3 success-path refetch:** For approve, edit, and delete success paths, assert that fetch call count to `/api/memories` increases after the mutation resolves. The current suite only proves refetch on 409 conflict.

[[2026-05-20T00:12:10+02:00]]
## Architecture Review (cycle 2 re-scope)

### Context
Reviewer rejected twice for proof gaps (not implementation gaps). Source is correct: PModal renders for delete, approved_at displayed, rehypeSanitize wired, success-path refetch present. Tests are insufficient: react-markdown mocked as passthrough, no approved_at assertion, no modal element assertion, no success-refetch assertion.

### Action
Refined AC1-AC3 for precision and added Proof Guidance section addressing all 4 reviewer findings with exact assertion strategies and reference patterns.

### Evaluation (unchanged from cycle 1)
| Criterion | Assessment |
|-----------|------------|
| Single responsibility | PASS |
| Interface clarity | PASS (refined) |
| Dependency correctness | PASS |
| Module layering | PASS |
| TDD compliance | PASS |
| KISS/YAGNI | PASS |
| Premise challenge | PASS |
| Pattern consistency | PASS |
| Security surface | PASS |
| Single domain | PASS |

### Challenge Results
- Challenger: FALLBACK — subagent returned no output
- Architect response: proceeding; this is a proof-refinement pass on an already-reviewed and implemented task

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED (write additional assertions only; implementation already GREEN)

### Verdict: APPROVE (REFINE + advance)
### Action Taken: Refined AC1-AC3 wording for proof precision; added explicit Proof Guidance section with 4 required test-assertion improvements and reference patterns.

[[2026-05-20T00:22:36+02:00]]
## Test-Writer Notes
- Retry: added 9 tests for 4 reviewer proof gaps. All pass against current impl.
- Builder skip: test-only retry, all 63 tests green.
- Test file: serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx
- New classes: TestFromAC_MemoryApprovedAt (1), TestFromAC_MemoryAccordionPlugins (2), TestFromAC_MemoryDeleteModal (3), TestFromAC_MemorySuccessRefetch (3)
- Total: 63 tests (54 original + 9 new), all PASS
- ESLint: clean
- Commit: 1af2ca63

Proof gap coverage:
| Gap | Tests | Evidence |
|-----|-------|----------|
| AC1 approved_at rendering | TestFromAC_MemoryApprovedAt (1 test) | Asserts detail textContent contains '2026-03-15' for approved entry |
| AC1 rehypeSanitize plugin wiring | TestFromAC_MemoryAccordionPlugins (2 tests) | Upgraded mock to vi.fn(); inspects vi.mocked(ReactMarkdown).mock.calls to verify rehypeSanitize + MEMORY_SANITIZE_SCHEMA in rehypePlugins tuple |
| AC2 delete modal element | TestFromAC_MemoryDeleteModal (3 tests) | Asserts [data-testid="memory-delete-confirm-dialog"] non-null after delete click; no conditional if-guards |
| AC3 success-path refetch | TestFromAC_MemorySuccessRefetch (3 tests) | Counts '/api/memories' fetch calls before/after approve, edit, delete — all increase |

[[2026-05-20T00:30:36+02:00]]
## Review Evidence
- Verdict: FAIL
- FAIL #1672 -> backlog | Third review cycle: AC1/AC3 proof remains incomplete and AC4 409 banner copy still mismatches the contract.
- Builder/test-writer evidence reviewed first: latest retry added 9 tests and reports 63/63 green, eslint clean, and the earlier builder packet already established the implementation shape. I did not dispatch quality-runner because the scoped evidence was internally consistent and editor diagnostics are clean for the reviewed files.
- Cross-checks: challenger = reconsider (confidence 0.58), which narrowed the case to the remaining contract/proof issues; code-reader confirmed the AC4 literal mismatch and the residual AC1/AC3 proof gaps.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1: Row click expands PAccordion showing entry content as sanitized markdown plus all metadata | The retry proves approved_at as a date and proves the sanitize plugin wiring, but task-local proof still would not fail if the accordion detail dropped id, scope_agents, categories, state, or the approved_at '-' fallback. | `serve/cockpit/web/src/pages/MemoryTab.tsx:701-709` renders the full metadata block; task tests assert only source_agent/confidence/timestamps at `serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx:243-264` and approved_at date-present at `serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx:1118-1124`. | backlog |
| 2 | AC3: Inline edit form ... nav-rail badge shows pending count >0 (hidden at zero, aria-label with count) | Task-local proof does not fully cover the AC-enumerated edit-form and badge branches: the suite proves the title control and char counter, plus the badge when count >0, but not categories/confidence/scope_agents/content control presence or the hidden-at-zero badge path. | `serve/cockpit/web/src/pages/MemoryTab.tsx:761-821` renders the full edit form; `serve/cockpit/web/src/Shell.tsx:450-476` hides the badge when count is 0; task tests assert title/counter at `serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx:514-548` and only the positive badge path at `serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx:683-712`. | backlog |
| 3 | AC4: 409 shows inline banner 'Entry was modified — refreshing' + auto-refetch | The implementation still emits `Entry was modified - refreshing` instead of the AC's `Entry was modified — refreshing`, and the task test only asserts the shorter substring, so the live mismatch stays false-green. | `serve/cockpit/web/src/pages/MemoryTab.tsx:477-478`; `serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx:738-751`. | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-scope AC1 proof so task-local tests must assert the remaining accordion-detail metadata branches, including id, scope_agents, categories, state, and the approved_at '-' fallback, or explicitly relax that contract. | serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx; serve/cockpit/web/src/pages/MemoryTab.tsx | Finding #1 |
| 2 | architect | Re-scope AC3 proof so task-local tests must assert the remaining required edit-form controls and the zero-count nav-badge hidden state, or explicitly narrow the AC. | serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx; serve/cockpit/web/src/pages/MemoryTab.tsx; serve/cockpit/web/src/Shell.tsx | Finding #2 |
| 3 | architect | Resolve the AC4 banner-copy contract by either keeping the exact string and routing a code+test fix for the current hyphenated implementation, or explicitly relaxing the copy requirement in the AC and tests. | serve/cockpit/web/src/pages/MemoryTab.tsx; serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx | Finding #3 |

## Observations
- The retry did close the prior four reviewer findings: approved_at date rendering, ReactMarkdown sanitize wiring, delete-modal presence, and success-path refetch are now task-local proved.
- No independent quality-runner rerun was needed because the latest builder/test-writer evidence was internally consistent and editor diagnostics are clean for the scoped files.
- If the architect keeps the current AC wording, the next cycle should likely separate the AC4 copy fix from the remaining proof hardening to avoid another review loop.

[[2026-05-20]]
## Proof Guidance (reviewer-cycle-3 findings)

The implementation is correct for all AC lines except AC4's banner copy literal. Three remaining gaps:

### 1. AC1 metadata exhaustive proof
The AC enumerates 9 metadata fields. Tests must assert ALL of them in the accordion detail:
- `ID: {entry.id}` — assert textContent contains the entry ID value
- `Scope agents:` — assert renders comma-joined list (or 'All agents' when empty)
- `Categories:` — assert renders comma-joined list
- `State:` — assert renders entry.state value
- `Approved:` — assert renders date string when `approved_at` is set AND renders '-' when `approved_at` is null

The existing tests already cover source_agent, confidence, created_at, updated_at, and approved_at (date-present). Add 5-6 assertions for the remaining fields including the null-fallback branch.

### 2. AC3 edit form controls + badge hidden-at-zero
The AC enumerates 5 edit-form controls: title, categories, confidence, scope_agents, content. Tests cover title and content (char counter). Add assertions for:
- `input[name=\"edit-categories\"]` is present in the edit form
- `input[name=\"edit-confidence\"]` is present with type=number
- `input[name=\"edit-scope-agents\"]` is present

For the nav badge zero-count path: render Shell with `pendingMemoryCount = 0` and assert `[data-testid=\"nav-badge\"]` is NOT present on the memory nav button. The current suite only tests the positive (count > 0) path.

### 3. AC4 banner copy literal fix (BUILDER)
The source at `MemoryTab.tsx:477` uses `'Entry was modified - refreshing'` (ASCII hyphen). The AC specifies `'Entry was modified — refreshing'` (em-dash U+2014). The builder must fix the source literal to match the AC. The task test must then assert the exact em-dash string.

All other proof gaps from cycles 1-2 are resolved (delete modal, sanitize wiring, success-path refetch, approved_at rendering).

[[2026-05-20T00:44:10+02:00]]
## Architecture Review (cycle 3 re-scope)

### Context
Reviewer rejected third time for 3 remaining proof gaps: (1) AC1 metadata not fully asserted (missing id, scope_agents, categories, state, approved_at null-fallback); (2) AC3 edit-form controls and badge zero-count not proven; (3) AC4 banner copy uses hyphen instead of em-dash. Implementation is correct for all except the AC4 literal.

### Evaluation (unchanged)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | |
| Interface clarity | PASS | AC lines already enumerate every field/control precisely |
| Dependency correctness | PASS | |
| Module layering | PASS | |
| TDD compliance | PASS | |
| KISS/YAGNI | PASS | |
| Premise challenge | PASS | |
| Pattern consistency | PASS | |
| Security surface | PASS | |
| Single domain | PASS | |

### Challenge Results
- Challenger: SKIPPED — proof-refinement pass on already-reviewed task; no architectural changes
- Architect response: N/A

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED (write additional assertions + builder fixes AC4 literal)

### Verdict: APPROVE (REFINE proof guidance)
### Action Taken: Added Proof Guidance cycle-3 section with explicit assertion requirements for all 3 remaining gaps. AC lines unchanged (already precise). Builder must fix hyphen→em-dash in source.

[[2026-05-20T01:07:57+02:00]]
## Test-Writer Notes (cycle-3 retry)
- Test file: serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx
- New classes: TestFromAC_MemoryMetadataFields (6), TestFromAC_MemoryEditFormControls (3), TestFromAC_MemoryNavBadgeZero (1), TestFromAC_MemoryOCCExactCopy (1)
- Total: 74 tests (63 original + 11 new)
- ESLint: clean

### Cycle-3 gap coverage

| Gap (reviewer finding) | Tests added | Result |
|---|---|---|
| AC1: id/scope_agents/categories/state/approved_at-null in accordion detail | TestFromAC_MemoryMetadataFields (6 tests) | 6 PASS (impl correct) |
| AC3: edit-categories/edit-confidence/edit-scope-agents form inputs | TestFromAC_MemoryEditFormControls (3 tests) | 3 PASS (impl correct) |
| AC3: nav badge hidden at zero pending count | TestFromAC_MemoryNavBadgeZero (1 test) | 1 PASS (impl correct) |
| AC4: exact em-dash copy 'Entry was modified — refreshing' | TestFromAC_MemoryOCCExactCopy (1 test) | 1 FAIL — source uses ASCII hyphen (MemoryTab.tsx:477); builder must change literal to U+2014 |

### Builder action required
- Fix `MemoryTab.tsx:477`: change `'Entry was modified - refreshing'` to `'Entry was modified \u2014 refreshing'` (em-dash)
- All 74 tests should pass after that single source change
