---
id: 1615
title: 'P2-05: Card visual treatment'
status: review
priority: important
created: 2026-05-16T03:37:02.225503+00:00
updated: 2026-05-16T20:31:31.844120+00:00
tags:
  - frontend
  - pds
  - phase-2
parent: 1590
depends_on: []
ac:
  - Status chip renders as `<PTag compact>` with `variant` derived from a 
    mapping utility; unknown status strings map to variant `secondary`
  - Priority chip renders as `<PTag compact>` with `variant` derived from a 
    mapping utility; unknown priority strings map to variant `secondary`
  - Signal icon renders as `<PIcon size="xs" aria-label={signal}>` for signals 
    dr-pending, blocked, claimed, deps-unmet; no icon renders for ready or 
    unknown
  - Each visible tag (up to TAG_PREVIEW_LIMIT=3) renders as individual `<PTag 
    compact variant="secondary">`; overflow count indicator preserved
  - Existing state cue text spans (Blocked, Claimed, Dependencies blocked, 
    Decision pending) preserved unchanged
  - No inline hex color values in Card output; status and priority color 
    expressed exclusively via PTag variant props
  - KanbanBoard.performance-700 test passes with adjusted DOM_NODE_BUDGET 
    accommodating PDS component nodes
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Status chip via PTag with color variant, priority color indicator, signal icon, tag pills, metadata density increase.

Scope: Card visual treatment only.
Out of scope: Simple swaps, sidecar, modals, filter panel.

[[2026-05-16T17:30:02+02:00]]
## Research
- Research doc: .owlbear/research/1615-card-visual-treatment-pds.md
- Sources: 10 studied, 5 high-relevance (PDS v4 GitHub source, codebase Card.tsx/computeSignal/performance-700)
- Recommendation: PTag for status + priority chips, PIcon for signal, PTag pills for tags (confidence: .65)
- Challenge: reconsider → revised from .82 to .65 after challenger identified DOM budget risk (6400 cap vs ~9800 projected at 700 cards), claimed-color exception (no purple PDS variant), and dynamic API mapping contract
- Key risks: (1) DOM node budget needs increase for PDS migration; (2) claimed signal stays as custom chip; (3) status/priority→variant mapping needs fallback utility
- Commit: 38e0ccba

2026-05-16T16:07:45+00:00
## Builder Guidance
- **Priority values (actual):** someday, nice-to-have, important, needed, critical — research doc §3.2 maps wrong literals; use these instead
- **Status values (actual):** research, backlog, todo, in-progress, review, docs, done
- **Mapping utility:** Create `utils/cardVariants.ts` with statusToVariant() and priorityToVariant() functions; accept any string, return PTag variant; fallback = 'secondary'
- **Claimed cue:** Keep as custom styled span (purple token `--pds-signal-claimed`); PTag has no purple variant — do not force into PTag
- **Signal icon:** Only render for dr-pending, blocked, claimed, deps-unmet; signal=ready and signal=unknown render no icon
- **DOM budget:** Increase DOM_NODE_BUDGET constant; validate 700-card render still passes
- **Keep cue text:** Do NOT remove existing state cue text spans; signal icon is additive
- **Import pattern:** See TaskFieldsEditor.tsx for existing PTag import from @porsche-design-system/components-react
- **Research doc:** .owlbear/research/1615-card-visual-treatment-pds.md (§4 has full implementation steps; override §3.2 priority mapping with actual values above)

[[2026-05-16T18:08:03+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Card visual treatment only; scoped per body |
| Interface clarity | PASS (after refine) | AC refined: 7 lines naming exact PDS components, observable outputs, fallback behavior |
| Dependency correctness | PASS | Test task #1610 deprecated (deps cleared); test-writer will create tests from refined AC |
| Module layering | PASS | Card.tsx is leaf component; imports utilities only |
| TDD compliance | PASS | proof_bundle=behavioral; test-writer processes in todo |
| KISS/YAGNI | PASS | Mapping utility justified by dynamic API strings; no over-abstraction |
| Premise challenge | PASS | PDS migration is explicit project goal per parent #1590 |
| Pattern consistency | PASS | TaskFieldsEditor.tsx already imports PTag from @porsche-design-system/components-react |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Frontend/PDS only |

### Challenge Results
- Challenger: reconsider (confidence 0.43)
- Key findings: (1) research priority mapping uses wrong literals (normal/low vs actual someday/nice-to-have/needed); (2) cue text retention not explicit; (3) AC scannable criterion subjective; (4) DOM budget couples constant change with test outcome
- Architect response: ACCEPTED — all findings addressed in AC refinement:
  - Removed subjective scannable criterion
  - Added explicit cue retention AC line (AC-5)
  - Mapping utility specified with fallback contract (AC-1/2)
  - Builder guidance corrects research priority values with actual codebase literals
  - DOM budget AC (7) is testable: constant increased AND test passes

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Design Diverge
- Trigger: skipped — single valid approach (PTag/PIcon migration) with no competing alternatives

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC from 3 vague lines to 7 precise lines naming exact PDS components and observable contracts; added Builder Guidance section correcting research doc priority mapping with actual codebase values; advanced to todo

[[2026-05-16T18:53:10+02:00]]
test-writer crashed once; releasing claim before retry: no structured verdict returned

[[2026-05-16T19:08:20+02:00]]
## Test-Writer Notes
- Test files: `serve/cockpit/web/src/__tests__/CardVariants_1615.test.ts`, `serve/cockpit/web/src/__tests__/CardVisualTreatment_1615.test.tsx`
- Commit: a71a05fd

### Classes and counts

| Class | File | Tests | Category |
|-------|------|-------|----------|
| `TestFromAC_CardVariantsMapping` | CardVariants_1615.test.ts | 14 | utility unit (fails: ModuleNotFoundError) |
| `TestFromAC_CardStatusChip` | CardVisualTreatment_1615.test.tsx | 5 | happy + boundary |
| `TestFromAC_CardPriorityChip` | CardVisualTreatment_1615.test.tsx | 5 | happy + boundary |
| `TestFromAC_CardSignalIcon` | CardVisualTreatment_1615.test.tsx | 6 | happy + edge |
| `TestFromAC_CardTagPills` | CardVisualTreatment_1615.test.tsx | 7 | happy + boundary + edge |
| `TestFromAC_CardCueTextPreserved` | CardVisualTreatment_1615.test.tsx | 4 | regression guard (anchored to AC-1) |
| `TestFromAC_CardNoHexColors` | CardVisualTreatment_1615.test.tsx | 3 | source inspection + rendering |
| `TestFromAC_DOMBudgetAdjusted` | CardVisualTreatment_1615.test.tsx | 1 | source inspection |

**Total: 45 tests, all FAIL — confirmed by quality-runner (passed: 0).**

### AC coverage

| AC | Tests |
|----|-------|
| AC-1: status PTag compact + unknown→secondary | CardVariantsMapping (statusToVariant), CardStatusChip (5 tests) |
| AC-2: priority PTag compact + unknown→secondary | CardVariantsMapping (priorityToVariant), CardPriorityChip (5 tests) |
| AC-3: PIcon for dr-pending/blocked/claimed/deps-unmet; no icon for ready/unknown | CardSignalIcon (6 tests) |
| AC-4: individual PTag pills per tag; overflow preserved | CardTagPills (7 tests) |
| AC-5: cue text spans unchanged (regression guards anchored to AC-1) | CardCueTextPreserved (4 tests) |
| AC-6: no hex colors; PTag imported | CardNoHexColors (3 tests) |
| AC-7: DOM_NODE_BUDGET > 6400 | DOMBudgetAdjusted (1 test) |

### Failure modes
- CardVariants_1615.test.ts: ModuleNotFoundError (`utils/cardVariants` does not exist)
- CardVisualTreatment_1615.test.tsx: AssertionError on `p-tag`/`p-icon` queries returning null (no PDS components in current Card.tsx); DOM budget check fails (6400 not > 6400); source PTag import check fails

### Builder notes
- Create `serve/cockpit/web/src/utils/cardVariants.ts` exporting `statusToVariant(s: string): string` and `priorityToVariant(s: string): string` with 'secondary' fallback
- Migrate status chip to `<PTag compact data-testid="card-status" variant={statusToVariant(task.status)}>` (new element)
- Migrate priority chip to `<PTag compact data-testid="card-priority" variant={priorityToVariant(task.priority)}>`
- Add `<PIcon size="xs" aria-label={signal}>` for signals: dr-pending, blocked, claimed, deps-unmet (not for ready/unknown)
- Migrate tag pills to individual `<PTag compact variant="secondary">` (one per visible tag)
- Keep all cue spans (card-blocked-cue, card-claimed-cue, card-deps-unmet-cue, card-dr-pending-cue) unchanged
- Increase `DOM_NODE_BUDGET` in `KanbanBoard.performance-700.test.tsx` to a value > 6400
- lint: clean

[[2026-05-16T20:03:04+02:00]]
## Builder Notes
### Files changed
- serve/cockpit/web/src/components/Card.tsx
- serve/cockpit/web/src/utils/cardVariants.ts (new)
- serve/cockpit/web/src/__tests__/KanbanBoard.performance-700.test.tsx

### Implementation summary
- Added mapping utility `statusToVariant()` / `priorityToVariant()` with `secondary` fallback for unknown values.
- Migrated Card status and priority chips to PDS tag host elements (`p-tag`) with `data-testid` anchors and explicit `compact`/`variant` attributes.
- Added signal icon host element (`p-icon`) rendered only for `dr-pending`, `blocked`, `claimed`, `deps-unmet`, with `size="xs"` and `aria-label={signal}`.
- Migrated visible tags to individual `p-tag` pills (`compact`, `variant="secondary"`) while preserving overflow indicator behavior.
- Preserved all existing cue spans unchanged (`card-blocked-cue`, `card-claimed-cue`, `card-deps-unmet-cue`, `card-dr-pending-cue`).
- Increased `DOM_NODE_BUDGET` from `6400` to `10000` in the 700-card performance test file per AC-7 guidance.

### Verification evidence
- Quality-runner RED gate (pre-implementation): task-scoped tests failed as expected.
- Quality-runner env fallback: runner reported environment/tooling errors (`document is not defined` in vitest path) after code updates; per pipeline protocol, switched to direct execution fallback.
- Direct scoped test pass:
  - `npm exec vitest run src/__tests__/CardVariants_1615.test.ts src/__tests__/CardVisualTreatment_1615.test.tsx --environment jsdom --reporter=verbose`
  - Result: `45 passed, 0 failed`.
- Direct lint pass:
  - `npm exec eslint -- src/components/Card.tsx src/utils/cardVariants.ts src/__tests__/CardVariants_1615.test.ts src/__tests__/CardVisualTreatment_1615.test.tsx`
  - Result: clean.
- Durable module regression check:
  - `npm exec vitest run src/__tests__/Card.signal.test.ts --environment jsdom --reporter=verbose`
  - Result: `27 passed, 0 failed`.

### Coverage
- Task-scoped frontend runs executed without coverage output in fallback mode.

### Additional notes
- Attempted explicit run of `src/__tests__/KanbanBoard.performance-700.test.tsx` with vitest; command did not complete in this environment (stuck at `0/10` for >120s), so no definitive pass/fail artifact captured for that suite in this builder run.

### Commit
- `b0a0c410`
