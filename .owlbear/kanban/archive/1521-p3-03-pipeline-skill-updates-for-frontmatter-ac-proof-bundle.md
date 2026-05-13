---
id: 1521
title: 'P3-03: Pipeline skill updates for frontmatter ac/proof_bundle'
status: archived
priority: important
created: 2026-05-13T02:29:51.822731+00:00
updated: 2026-05-13T08:01:28.455609+00:00
tags:
  - phase-3
  - scope:skills
  - feature
  - docs
parent: 1514
depends_on:
  - 1518
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1514

## Scope
In scope: Update w-tdd-red, w-tdd-green, w-code-review, w-arch-review, w-task-decomposition skill files to read/write ac and proof_bundle from frontmatter
Out of scope: Code changes, tests, migration

## Acceptance Criteria
- AC1: `w-tdd-red` SKILL.md reads `proof_bundle` from `show_task` frontmatter field (authoritative when non-null); falls back to body `Proof bundle:` line when field is null (legacy tasks)
- AC2: `w-tdd-green`, `w-code-review`, and `w-arch-review` SKILL.md files reference `proof_bundle` from `show_task` frontmatter field (authoritative when non-null); fall back to body `Proof bundle:` line when field is null
- AC3: `w-task-decomposition` SKILL.md writes `proof_bundle` via `create_task` parameter instead of embedding `Proof bundle: X` body text line
- AC4: No remaining references to body-based `Proof bundle:` or `## Acceptance Criteria` parsing patterns exist in `share/skills/` as primary read paths after updates (fallback references are permitted)

Proof bundle: skip
2026-05-13T06:47:45+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | 5 skill file updates, single concern |
| Interface clarity | PASS | AC refined: authoritative/fallback precedence rule specified |
| Dependency correctness | PASS | #1518 archived/completed — engine supports frontmatter ac/proof_bundle |
| Module layering | PASS | N/A — skill docs only, no code |
| TDD compliance | PASS | Proof bundle: skip, tagged `docs` (non-implementation) |
| KISS/YAGNI | PASS | Minimal scope: edit existing skill files |
| Premise challenge | PASS | Skills must reference new structured fields for feature to be operational |
| Pattern consistency | PASS | Follows existing skill file structure |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | scope:skills only |

### AC Refinement (applied)
- AC1-AC2: Changed "instead of" to authoritative/fallback precedence per Brief: frontmatter is authoritative when non-null, body `Proof bundle:` line is fallback for legacy tasks
- AC3: Unchanged (create_task parameter confirmed in engine.py:1086-1098)
- AC4: Rewritten from process instruction ("Builder greps...") to verifiable condition ("No remaining body-based primary read paths exist")

### Proof-Bundle Validation
- Planner assignment: skip
- Final bundle: skip
- Test-writer: SKIP

### Design Diverge
- Trigger: skipped — single clear approach (edit 5 files per Brief precedence rule)

### Challenge Results
- Challenger: SKIPPED — proof bundle `skip`

### Verdict: APPROVE
### Action Taken: Refined AC1-AC4 for verifiability and Brief alignment. Advanced #1521 → todo.
2026-05-13T06:58:24+00:00
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Tagged `docs`: skill file updates only, no testable Python interfaces.
- Passing through to builder.
2026-05-13T07:14:43+00:00
## Builder Notes
- Scope: Updated pipeline skill docs to use frontmatter `proof_bundle`/`ac` as primary read path with explicit legacy fallback to body parsing when frontmatter is null.
- Files changed:
  - `share/skills/w-tdd-red/SKILL.md`
  - `share/skills/w-tdd-green/SKILL.md`
  - `share/skills/w-code-review/SKILL.md`
  - `share/skills/w-arch-review/SKILL.md`
  - `share/skills/w-task-decomposition/SKILL.md`
- Commit: `f277f525`

### AC Coverage
- AC1: `w-tdd-red` now instructs `show_task(id={id})` frontmatter reads (`proof_bundle`, `ac`) as authoritative, with explicit body fallback only when field is null.
- AC2: `w-tdd-green`, `w-code-review`, and `w-arch-review` now reference frontmatter `proof_bundle`/`ac` as authoritative and body parsing as legacy fallback.
- AC3: `w-task-decomposition` now specifies passing `proof_bundle` via `create_task` parameter and explicitly says not to embed `Proof bundle: {value}` in task body.
- AC4: Verified no primary body-based read-path wording remains in `share/skills/` for proof-bundle/AC parsing after updates; residual mentions are fallback or output formatting only.

### Verification Evidence
- Search validation run across `share/skills/**` for prior primary-path patterns (`Proof bundle` in body / `## Acceptance Criteria` body parsing) after edits.
- Matches in edited files now state frontmatter-first + legacy fallback, satisfying precedence requirement.

### Quality/Lint
- Proof bundle on task: `skip` (docs-only scope). Per workflow, skipped quality-runner execution for `TestFromAC_*`/coverage gates.
- No executable code or tests changed.
2026-05-13T07:35:07+00:00
## Review Evidence
- Verdict: FAIL
- FAIL route: in-progress | `w-task-decomposition` does not yet write frontmatter `ac`, so the frontmatter-first pipeline update is incomplete.
- Builder evidence reviewed first: builder notes covered the five edited skill files and the body-pattern search validation. Because this task is `Proof bundle: skip` and the builder notes did not include lint proof, I independently dispatched `quality-runner` on the five changed `SKILL.md` files. Result: lint clean, `markdownlint` exit code `0`, no errors.

| AC Line | Code Evidence | Proof Evidence | Status |
|---|---|---|---|
| AC1 | `share/skills/w-tdd-red/SKILL.md:36-44`, `share/skills/w-tdd-red/SKILL.md:140-145` | Reviewer `quality-runner`: lint clean | PASS |
| AC2 | `share/skills/w-tdd-green/SKILL.md:39-45`, `share/skills/w-tdd-green/SKILL.md:51`; `share/skills/w-code-review/SKILL.md:41`, `share/skills/w-code-review/SKILL.md:79`, `share/skills/w-code-review/SKILL.md:105`; `share/skills/w-arch-review/SKILL.md:39-47`, `share/skills/w-arch-review/SKILL.md:108` | Reviewer `quality-runner`: lint clean | PASS |
| AC3 | `share/skills/w-task-decomposition/SKILL.md:207` | Reviewer `quality-runner`: lint clean | FAIL |
| AC4 | `share/skills/w-tdd-red/SKILL.md:43-44`, `share/skills/w-tdd-green/SKILL.md:44-45`, `share/skills/w-code-review/SKILL.md:41`, `share/skills/w-code-review/SKILL.md:79`, `share/skills/w-arch-review/SKILL.md:46-47`; workspace search across `share/skills/**` found only fallback/output mentions of `Proof bundle:` / `## Acceptance Criteria` parsing | Reviewer `quality-runner`: lint clean | PASS |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---|---|---|---|
| 1 | AC3 incomplete against task scope line 25 + parent AC8 | The updated `w-task-decomposition` guidance still tells the planner to put Acceptance Criteria only in the task body and to pass only `proof_bundle` through `create_task`. The live task-creation surface already supports both `ac` and `proof_bundle`, so tasks created from this skill will still omit frontmatter `ac` and force downstream skills onto the legacy body fallback. That leaves the task's `read/write ac and proof_bundle from frontmatter` update incomplete. | `.owlbear/kanban/tasks/1521-p3-03-pipeline-skill-updates-for-frontmatter-ac-proof-bundle.md:25`, `.owlbear/kanban/tasks/1514-structured-task-specification-in-frontmatter-ac-proof-bundle.md:24`, `.owlbear/kanban/tasks/1514-structured-task-specification-in-frontmatter-ac-proof-bundle.md:48`, `share/skills/w-task-decomposition/SKILL.md:207`, `serve/kanban/src/owlbear_kanban/engine.py:1086-1097`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:340-349` | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Update `w-task-decomposition` so its `create_task` instructions pass drafted Acceptance Criteria via the `ac` parameter alongside `proof_bundle`, instead of leaving AC only in the body path. | `share/skills/w-task-decomposition/SKILL.md` | `share/skills/w-task-decomposition/SKILL.md:207`, `serve/kanban/src/owlbear_kanban/engine.py:1086-1097`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:340-349`, `.owlbear/kanban/tasks/1521-p3-03-pipeline-skill-updates-for-frontmatter-ac-proof-bundle.md:25`, `.owlbear/kanban/tasks/1514-structured-task-specification-in-frontmatter-ac-proof-bundle.md:48` |

## Observations
- Independent reviewer lint verification was necessary because skip-bundle builder notes omitted lint proof. The scoped `quality-runner` pass on the five changed `SKILL.md` files came back clean.
- Aside from the missing `ac` write path in `w-task-decomposition`, the other four skill updates correctly describe frontmatter-first reads with legacy body fallback.
2026-05-13T07:42:30+00:00
## Builder Notes
- Implementation: Updated `share/skills/w-task-decomposition/SKILL.md` Step 6 task-creation guidance to pass both `ac` and `proof_bundle` via `create_task` parameters, with body reserved for supporting context.
- Files changed: `share/skills/w-task-decomposition/SKILL.md`
- Commit: `b4960b5a`
- Tests: Proof bundle is `skip` (docs-only skill update); no `TestFromAC_*` gate required.
- Coverage: N/A (no Python/runtime code touched).
- Lint: quality-runner scoped lint on changed file reported clean (`markdownlint` exit code 0).
- Evidence summary: This closes reviewer follow-up for AC3 by ensuring decomposition guidance writes frontmatter `ac` alongside `proof_bundle` instead of leaving AC only in body text.
2026-05-13T07:47:25+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1521 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: the retry builder notes narrowed scope to `share/skills/w-task-decomposition/SKILL.md`, recorded scoped `quality-runner` markdown lint clean on that file, and described the AC3 fix. For this `Proof bundle: skip` docs-only task, that evidence plus direct file inspection is sufficient.

| AC Line | Code Evidence | Proof Evidence | Status |
|---|---|---|---|
| AC1 | `share/skills/w-tdd-red/SKILL.md:34-53`, `share/skills/w-tdd-red/SKILL.md:115-140` show frontmatter `proof_bundle`/`ac` as authoritative with body fallback only when null. | Direct file inspection of the updated skill text; no executable proof required for `skip` beyond lint. | PASS |
| AC2 | `share/skills/w-tdd-green/SKILL.md:35-51`, `share/skills/w-tdd-green/SKILL.md:53-81`; `share/skills/w-code-review/SKILL.md:41`, `share/skills/w-code-review/SKILL.md:65-79`, `share/skills/w-code-review/SKILL.md:103-105`; `share/skills/w-arch-review/SKILL.md:37-47`, `share/skills/w-arch-review/SKILL.md:96-117` all route from frontmatter first with legacy body fallback only when null. | Direct file inspection of the live skill text; no contradictory routing language found in the reviewed files. | PASS |
| AC3 | `share/skills/w-task-decomposition/SKILL.md:207` now instructs `create_task` with both `ac` and `proof_bundle`, reserves the body for supporting context only, and explicitly forbids embedding `Proof bundle: {value}` in the body. The runtime interface matches that guidance at `serve/kanban/src/owlbear_kanban/engine.py:1086-1096` and `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:340-349`. | Builder evidence: scoped `quality-runner` markdownlint clean on `share/skills/w-task-decomposition/SKILL.md`; direct file inspection confirms the previous reviewer blocker is closed. | PASS |
| AC4 | Workspace scan across `share/skills/**` found remaining `Proof bundle:` / `## Acceptance Criteria` mentions only as legacy fallback instructions or output/taxonomy text, not as primary read paths. Relevant surviving fallback references are in `w-tdd-red`, `w-tdd-green`, `w-code-review`, and `w-arch-review`; the `w-task-decomposition` write path now uses frontmatter fields. | Direct search verification across `share/skills/**`; no body-first primary read-path guidance found. | PASS |

- Blocking findings: none.

## Observations
- The previous reviewer blocker on `w-task-decomposition` is resolved by the retry at `share/skills/w-task-decomposition/SKILL.md:207`.
- I did not dispatch an independent `quality-runner` rerun on the retry because this task remains `Proof bundle: skip` and the builder supplied scoped lint evidence for the only changed file; that evidence was internally consistent with the live file state.
2026-05-13T07:51:54+00:00
## Docs Gate

### Upstream Evidence
`## Review Evidence` present (second instance, PASS verdict). Upstream evidence complete — proceeding.

### Convention Mapping
Changed files: `share/skills/w-tdd-red/SKILL.md`, `share/skills/w-tdd-green/SKILL.md`, `share/skills/w-code-review/SKILL.md`, `share/skills/w-arch-review/SKILL.md`, `share/skills/w-task-decomposition/SKILL.md`
Maps to: `share/README.md`, `share/WIRING.md`

### Item 1: README Verification
Full read of `share/README.md` and `share/WIRING.md`. Neither document covers skill-internal behavior or frontmatter field semantics — they describe counts, names, prefix conventions, and agent-to-file connection methods only. No symbols, CLI flags, or structural elements were removed or added by this task. Layer 1 grep for `proof_bundle`/`Proof bundle`/`acceptance criteria` in both targets: no matches. Layer 2 editorial: no contradictions or coherence gaps introduced. **No updates needed.**

### Item 2: External Attribution
Builder notes reference no external sources. **N/A — no external attribution needed.**

### Item 3: Research Doc
Task body contains no research document reference. **N/A — no research doc linkage needed.**

### Item 4: Deletion Detection
No files deleted. Only 5 SKILL.md files edited (behavioral instruction updates). **N/A — no deletion impact.**

### Scratch Cleanup
No `.owlbear/scratch/1521-*` files found — nothing to clean.
2026-05-13T08:01:28+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: 4505 passed, 208 failed, 14 skipped, lint clean\n- All 208 failures are pre-existing background failures (identical pattern in prior audit sessions for #1518, #1519). This task changed zero Python files (5 SKILL.md docs only) and cannot introduce Python test regressions.\n- regression verdict: PASS (no task-introduced regressions)\n\n### Intent Verification\n- scope alignment: PASS (all changes in share/skills/w-{tdd-red,tdd-green,code-review,arch-review,task-decomposition}/SKILL.md, matching scope:skills tag)\n- purpose match: PASS (skill instructions now route to frontmatter ac/proof_bundle as authoritative with legacy body fallback)\n- extraneous scope: none\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 4/5\n- AC1-AC2 specific with clear authoritative/fallback precedence rule\n- AC3 initially missed the ac write path (caught by reviewer, fixed in retry); minor architect gap\n- AC4 well-scoped verifiable condition\n- Overall adequate with one gap filled by reviewer escalation\n\n### Commit Integrity\n- upstream commit presence: PASS (f277f525 initial 5-file update, b4960b5a retry AC3 fix; both attributed #1521, builder)\n- kanban commit packaging: pending (this step)\n\n### Deduction Breakdown\nNo deductions applied.\n- Regression: 0 (pre-existing failures, not task-introduced)\n- Intent: 0\n- AC quality 4/5: 0\n- Reviewer evidence: 0 (present, detailed, two-cycle FAIL then PASS)\n- Lint: 0 (clean)\n- Commit integrity: 0\n\n### Confidence: 1.00\n### Action: archive