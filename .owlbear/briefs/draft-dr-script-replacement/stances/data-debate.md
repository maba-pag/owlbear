# Data Panelist — Critic Debate Log

## Cycle 1

### Draft Position

Initial stance focused on seven areas: migration (non-issue), schema validation (fail-fast on read), resolve write-back (keep it), filename collision (sequence suffix), atomicity (two-step), concurrency (low risk), and null propagation (explicit pending state).

### Critic Challenges (Cycle 1)

1. **Critical — Resolved files are live data.** check-or-create mode consults resolved/ to avoid re-raising answered questions. Agents query DR records when task body lacks a summary. The 35 resolved files are not archival — they're part of the dedup and query contract.

2. **Critical — Semantic validation gap.** The most dangerous validation isn't structural YAML — it's semantic misclassification of the response field. The current system explicitly says "never invent decisions" and "downgrade ambiguous approval signals." Position only addressed malformed YAML.

3. **Critical — Concurrency understated.** pick_tasks is published as read-only/idempotent. Adding mutation side-effects means any caller triggers resolution. "Low real risk" is not grounded in the actual API contract.

4. **Moderate — Atomicity is 3+ steps.** Resolve also requires unblocking. Needs-info path doesn't move the file. The two-step model was incomplete.

5. **Moderate — Write-back is multi-section.** Not just "Decision Resolved" — also Action Completed, Clarification Requested, Decision Rejected. Position was too narrow.

6. **Moderate — Collision claim overstated.** Engine could reject on existing path vs. overwrite. The data-loss conclusion was stronger than evidence.

7. **Moderate — Positions 2 and 7 inconsistent.** Fail-fast validation vs. absence-means-pending needed reconciliation.

### Revisions Applied

- Upgraded resolved files to "live data, dual-format read required"
- Separated structural validation (fail-fast) from semantic classification (closed enum)
- Expanded atomicity to four steps including unblock
- Covered all terminal write-back sections
- Changed filename approach to check-before-write with atomic guard
- Upgraded concurrency to "guard required"
- Reconciled validation levels (structural = fail-fast, pending state = valid)

## Cycle 2

### Revised Position

Seven-point stance with closed-enum classification, four-step resolve, check-before-write with `O_CREAT|O_EXCL`, and file-rename concurrency guard.

### Critic Challenges (Cycle 2)

1. **Critical — Freeform escape hatch contradicts safety claim.** The "any unknown value resolves as freeform approval" rule (from draft 2, since removed) was directly contradicted by the current system's "downgrade ambiguous signals" principle. Treating unknowns as approvals reproduces the exact risk being eliminated.

2. **Critical — Concurrency guard only covers final step.** Atomic rename on pending→resolved doesn't prevent two callers from both appending to the task body simultaneously. The full resolve sequence needs single-writer semantics, not just the last step.

3. **Critical — TOCTOU not acceptable.** Glob-then-write for create is vulnerable under the same concurrency model that position 6 admits exists. `O_CREAT|O_EXCL` is the correct primitive.

4. **Critical — Resolved/ namespace needs collision avoidance.** Same task+concern can re-arise after resolution. Move to resolved/ can collide with the previous resolution's file.

5. **Moderate — Idempotency proof covers only one section type.** The dedup check using heading presence must cover all four terminal sections and verify content parity, not just heading existence.

6. **Moderate — pick_tasks contract change is a consumer-facing risk.** Anything treating pick_tasks as a harmless read becomes unsafe once it has mutation side-effects.

7. **Moderate — Response enum incomplete.** `response: pending` (explicitly taught in current README) and `response: completed` (AR terminal state) were missing from the classifier.

### Revisions Applied

- Explicitly rejected the freeform escape hatch — unknown values do NOT resolve, period
- Introduced three-state resolve (pending → processing → resolved) as the concurrency lock
- Switched from glob-check to `open(path, 'x')` for atomic create
- Extended collision avoidance to resolved/ namespace
- Added content-aware idempotency check for all section types
- Added legacy response values (`pending`, `completed`) to the canonical enum
- Surfaced pick_tasks contract change as a top-level warning

## Final Assessment

After two Critic cycles at high pressure (confidence scores 0.32 and 0.29), the position hardened significantly:

- The closed-enum classifier is the cornerstone — no silent auto-approval on unknown values
- Three-state file lifecycle (pending/processing/resolved) provides single-writer semantics without OS-level locks
- Atomic file creation (`O_EXCL`) eliminates TOCTOU for both namespaces
- The pick_tasks contract change is surfaced as a design decision the brief must address explicitly

Remaining uncertainty: whether the three-state approach is the right solution vs. simply documenting that pick_tasks is no longer idempotent. Both are valid; the brief must choose.
