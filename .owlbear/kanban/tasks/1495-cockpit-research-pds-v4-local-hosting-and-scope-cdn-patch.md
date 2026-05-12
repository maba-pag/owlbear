---
id: 1495
title: 'Cockpit: Research PDS v4 local hosting and scope CDN patch'
status: docs
priority: important
created: 2026-05-11T23:15:45.844267+00:00
updated: 2026-05-12T14:42:21.348973+00:00
tags:
  - cockpit
  - frontend
  - research
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Research whether PDS v4 supports native local-hosting configuration and recommend an approach for eliminating the global appendChild monkeypatch in main.tsx.

## Acceptance Criteria

1. Research artifact produced at `.owlbear/research/1495-pds-v4-local-hosting.md` answering whether PDS v4 exposes CDN_BASE_URL, partialBundling, or equivalent config for self-hosted asset loading
2. Research artifact documents the recommended replacement approach with rationale, after evaluating at least 2 candidate strategies
3. Follow-up implementation tasks created as child tasks of #1495 with scoped AC derived from the research recommendation

Proof bundle: skip

## Source
Cockpit audit 2026-05-11, Finding F16
2026-05-12T02:37:17+00:00
## Planning

Created 2 follow-up subtasks at research status:

| ID | Title | Priority | Tags |
|----|-------|----------|------|
| #1496 | Cockpit: Replace PDS appendChild monkeypatch with property trap on document.porscheDesignSystem.cdn | important | cockpit, frontend |
| #1497 | Cockpit: Remove dead pdsPartialsPlugin from vite.config.ts | nice-to-have | cockpit, frontend, cleanup |

Both parented to #1495. No dependencies between them — they can be worked independently.
2026-05-12T02:37:53+00:00
## Research
- Research doc: .owlbear/research/1495-pds-v4-local-hosting.md
- Sources: 5 external + 2 local npm artifacts studied, 4 high-relevance
- Recommendation: Replace appendChild monkeypatch with Object.defineProperty trap on document.porscheDesignSystem.cdn (confidence: 0.80)
- Challenge: block on original "scoped appendChild" approach (0.23) — revised to property trap after challenger identified double-load timing bug, core chunk caching, and readiness boundary issues
- Follow-ups: #1496 (property trap implementation), #1497 (remove dead pdsPartialsPlugin)
- Key finding: PDS v4 has NO native self-hosting config; load() only accepts cdn: 'auto' | 'cn'
2026-05-12T08:19:21+00:00
## Test-Writer Notes
- Non-implementation task (tagged research) — no tests applicable.
- Passing through to builder.
2026-05-12T09:28:13+00:00
## Builder Notes
- Classification: Non-implementation pass-through (from Test-Writer Notes in task body).
- Files changed: none.
- Tests run: none (not applicable for research-only pass-through).
- Lint status: not run (not applicable; no code or test modifications).
- Coverage: not applicable.
- Evidence summary:
  - Task objective and AC are research/documentation scoped.
  - Research artifact already produced: `.owlbear/research/1495-pds-v4-local-hosting.md`.
  - Test-writer explicitly marked: "Non-implementation task (tagged research) — no tests applicable. Passing through to builder."
- Fixes applied: none required in builder phase.
2026-05-12T09:58:59+00:00
## Review Evidence
- Verdict: FAIL
- FAIL #1495 -> backlog | Parent task advanced as research-only even though its AC still requires an implementation outcome that remains both unshipped and contradicted by the research recommendation.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC lines 26-27 | The task was moved to review without satisfying the implementation branch of the AC. Builder notes explicitly say no files changed and no tests ran, while the live Cockpit entrypoint still installs the global appendChild monkeypatch. | `.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md:26-27,58-59`; `serve/cockpit/web/src/main.tsx:10,14,29` | backlog |
| 2 | AC lines 26-27 | The research outcome now contradicts the task contract. The doc recommends a property-trap replacement and records the original scoped-appendChild approach as blocked; child task #1496 captures that replacement and is still open. This parent cannot PASS until its AC is rewritten as research-only or explicitly gated on child completion. | `.owlbear/research/1495-pds-v4-local-hosting.md:60,66,68,70`; `.owlbear/kanban/tasks/1496-cockpit-replace-pds-appendchild-monkeypatch-with-property-trap-on-document-porsc.md:4,20` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Rewrite #1495 so it is either a research-only closure task or a parent tracker with explicit child-completion gating; remove the obsolete scoped-appendChild requirement from the parent AC. | `.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md` | Blocking finding #2; AC at lines 26-27 conflicts with the research recommendation at `.owlbear/research/1495-pds-v4-local-hosting.md:66-70` |
| 2 | architect | Reconcile parent/child delivery before returning #1495 to review; the implementation work still lives in child task #1496 and the production code remains unchanged. | `.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md`, `.owlbear/kanban/tasks/1496-cockpit-replace-pds-appendchild-monkeypatch-with-property-trap-on-document-porsc.md`, `serve/cockpit/web/src/main.tsx` | Blocking finding #1; `serve/cockpit/web/src/main.tsx:10,14,29` and task `#1496` status `todo` at line 4 |

## Observations
- The research artifact itself is useful and does answer the native-config question; the recommendation in `.owlbear/research/1495-pds-v4-local-hosting.md:66-70` is specific and actionable.
- Source-log hygiene needs cleanup on the next pass: two task-1495 rows are filed under the task-1493 heading in `.owlbear/sources/overview.md:43,49-50`, which makes the supporting evidence trail harder to audit.
2026-05-12T10:32:33+00:00
## Architecture Review

### Context
Reviewer correctly rejected this task: the original AC contained implementation branches ("If yes: replace…", "If no: scope the patch…") that conflicted with the research outcome and were never fulfilled. The research IS the deliverable — implementation lives in child tasks #1496 (property trap, at `todo`) and #1497 (remove dead plugin, at `research`).

### AC Refinement
Rewrote AC from hybrid research/implementation to research-only:
- AC-1: Research artifact answers the native-config question (P1: researcher, P2: artifact at path, P3: artifact inspection)
- AC-2: Artifact documents ≥2 candidate strategies with recommended approach (P2: observable content, P3: artifact inspection)
- AC-3: Follow-up implementation tasks created as children with scoped AC (P2: child tasks created, P3: field-presence check)

Removed obsolete implementation branches that contradicted the research recommendation.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC-1 (research artifact) | PASS — Tier 2 P1/P2/P3 compliant | None |
| AC-2 (approach recommendation) | PASS — concrete observable, no banned words | None |
| AC-3 (follow-up tasks) | PASS — verifiable by child task inspection | None |

### Evaluation

| Criterion | Assessment |
|-----------|-----------|
| Single responsibility | PASS — research only, implementation in children |
| AC clarity | PASS — all 3 lines independently verifiable |
| Dependency correctness | PASS — no dependencies |
| Non-impl tagging | PASS — `research` tag present |

### Proof-Bundle Validation
- Planner assignment: none
- Final bundle: skip
- Test-writer: SKIP (non-implementation research task)

### Challenge
- Skipped per Step 2.1 (bundle = skip)

### Verdict: APPROVE (REFINE)
Rewrote AC to match the actual research-only deliverable. Removed implementation branches that the reviewer correctly identified as contradicting the research outcome. Implementation work is properly captured in child tasks #1496 and #1497.
2026-05-12T11:13:57+00:00
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Passing through to builder.
2026-05-12T11:39:10+00:00
## Builder Notes
- Classification: Non-implementation pass-through (`Proof bundle: skip`, research task).
- Files changed: none.
- Tests run: none (not applicable for research-only scope).
- Lint status: not run (no code or test modifications in this task).
- Coverage: not applicable.

### Evidence Summary
- AC-1 satisfied: research artifact exists at `.owlbear/research/1495-pds-v4-local-hosting.md` and explicitly answers the native-config question (no `cdn_base_url`/partial-bundling equivalent; `cdn: 'auto' | 'cn'` only).
- AC-2 satisfied: artifact evaluates 3 strategies (property trap, scoped patch+trap, keep current) and records the recommended replacement approach with rationale.
- AC-3 satisfied: follow-up implementation tasks exist as child tasks of #1495 with scoped AC:
  - #1496 (parent=1495, scoped implementation AC, currently in review)
  - #1497 (parent=1495, scoped cleanup AC, currently in research)

### Fixes Applied
- None required in builder phase; task is a research deliverable and was validated against refined AC.
2026-05-12T12:20:28+00:00
## Review Evidence
- Verdict: FAIL
- FAIL #1495 -> backlog | AC content is satisfied, but independent skip-bundle lint evidence fails on the research artifact and this is a repeated review cycle.
- AC mapping:
  - AC-1: PASS — [.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md](.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md#L26) requires the artifact to answer the native-config question; [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L24) and [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L26) document that PDS v4 has no native self-hosting config and `load()` only accepts `cdn: 'auto' | 'cn'`.
  - AC-2: PASS — [.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md](.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md#L27) requires evaluation of at least 2 strategies with a recommendation; [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L40), [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L54), [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L60), [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L62), and [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L66) show three candidate strategies and the recommended property-trap approach.
  - AC-3: PASS — [.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md](.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md#L28) requires child tasks with scoped AC; [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L74), [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L76), and [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L77) define the follow-ups, while [.owlbear/kanban/tasks/1496-cockpit-replace-pds-appendchild-monkeypatch-with-property-trap-on-document-porsc.md](.owlbear/kanban/tasks/1496-cockpit-replace-pds-appendchild-monkeypatch-with-property-trap-on-document-porsc.md#L11) and [.owlbear/kanban/tasks/1496-cockpit-replace-pds-appendchild-monkeypatch-with-property-trap-on-document-porsc.md](.owlbear/kanban/tasks/1496-cockpit-replace-pds-appendchild-monkeypatch-with-property-trap-on-document-porsc.md#L22), plus [.owlbear/kanban/tasks/1497-cockpit-remove-dead-pdspartialsplugin-from-vite-config-ts.md](.owlbear/kanban/tasks/1497-cockpit-remove-dead-pdspartialsplugin-from-vite-config-ts.md#L12) and [.owlbear/kanban/tasks/1497-cockpit-remove-dead-pdspartialsplugin-from-vite-config-ts.md](.owlbear/kanban/tasks/1497-cockpit-remove-dead-pdspartialsplugin-from-vite-config-ts.md#L23), confirm both child tasks exist under parent `1495` with their own acceptance criteria.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | Proof bundle: skip | The content contract is met, but the required quality proof is not. Builder notes marked lint as not applicable, yet independent `quality-runner` markdown lint on the research artifact failed with `MD032` because the Option A section starts a list immediately after `This way:` without the required blank line. Because this task already failed review once before, the repeated-cycle rule sends it back to backlog. | [.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md](.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md#L30), [.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md](.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md#L72), [.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md](.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md#L136), [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L54), and [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L55) | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-queue #1495 with a markdown-lint-clean research artifact before returning it to review; ensure the Option A section in the research note satisfies `markdownlint` `MD032`. | .owlbear/research/1495-pds-v4-local-hosting.md; .owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md | Blocking finding #1; `quality-runner` reported `MD032` at `.owlbear/research/1495-pds-v4-local-hosting.md:55` with preceding paragraph context at `.owlbear/research/1495-pds-v4-local-hosting.md:54` |

## Observations
- Builder evidence for the content AC is materially consistent with live artifacts: the summary at [.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md](.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md#L143), [.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md](.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md#L144), and [.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md](.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md#L145) matches direct inspection of the research note and child tasks.
- The child-status wording in builder notes is stale but non-blocking: [.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md](.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md#L146) says `#1496` was in review, while the current child file shows [.owlbear/kanban/tasks/1496-cockpit-replace-pds-appendchild-monkeypatch-with-property-trap-on-document-porsc.md](.owlbear/kanban/tasks/1496-cockpit-replace-pds-appendchild-monkeypatch-with-property-trap-on-document-porsc.md#L4). That does not affect AC-3 because the parent only requires child creation and scoped AC, not child completion.
2026-05-12T12:51:28+00:00
## Architecture Review (cycle 2)\n\n### Context\nRepeated review cycle. Prior architecture review (cycle 1) already refined AC from hybrid research/implementation to research-only. AC is verified sound. The sole blocking finding from reviewer cycle 2 is an MD032 lint violation in `.owlbear/research/1495-pds-v4-local-hosting.md:54-55` — paragraph ending `This way:` immediately followed by a list without a blank line.\n\n### AC Assessment\n\n| AC Line | Assessment | Action |\n|---------|-----------|--------|\n| AC-1 (research artifact answers native-config question) | PASS — unchanged from cycle 1 | None |\n| AC-2 (≥2 strategies with recommendation) | PASS — unchanged from cycle 1 | None |\n| AC-3 (follow-up child tasks with scoped AC) | PASS — unchanged from cycle 1 | None |\n\n### Evaluation\n\n| Criterion | Assessment |\n|-----------|-----------|\n| Single responsibility | PASS — research only |\n| AC clarity | PASS — all lines verifiable |\n| Dependency correctness | PASS — no deps |\n| Non-impl tagging | PASS — `research` tag present |\n\n### Proof-Bundle Validation\n- Planner assignment: skip\n- Final bundle: skip\n- Test-writer: SKIP\n\n### Challenge Results\n- Challenger: SKIPPED — proof bundle `skip`\n\n### Builder Guidance\nFix MD032 in `.owlbear/research/1495-pds-v4-local-hosting.md` at line 54-55: add a blank line between `This way:` paragraph and the following list. Then lint-verify with markdownlint.\n\n### Verdict: APPROVE\n### Action Taken: Re-approved to todo with lint-fix guidance for builder.
2026-05-12T13:28:27+00:00
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Retry cycle: reviewer blocking finding is MD032 lint in research artifact (not missing tests). Builder will address per Architecture Review (cycle 2) guidance.
- Passing through to builder.
2026-05-12T14:16:27+00:00
## Builder Notes
- Classification: Proof bundle `skip` research-task retry (non-implementation).
- Files changed:
  - `.owlbear/research/1495-pds-v4-local-hosting.md` (added required blank line before Option A list to satisfy markdownlint MD032)
- Commit:
  - `da570f8d2f77f1fa2b7188aaa2e82704212529b1`
  - `fix: resolve markdownlint MD032 in task 1495 research note (#1495, builder)`
- Quality-runner evidence (scoped):
  - `mode=scoped`, `task_id=1495`
  - `test_paths=[]`
  - `lint_paths=[".owlbear/research/1495-pds-v4-local-hosting.md"]`
  - Result: tests `0 passed / 0 failed`, lint `clean: true`, violations `[]`, markdownlint exit code `0`
- Coverage: not applicable for docs/research task (`Proof bundle: skip`).
- Fixes applied: minimal markdown spacing correction only; no code-path changes.
2026-05-12T14:42:21+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1495 -> docs | AC mapped to live research artifacts and skip-bundle proof is sufficient.
- AC-1: PASS — [.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md](.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md#L26) requires a native-config answer; [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L24) and [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L26) show that PDS v4 has no native self-hosting config and load() accepts only cdn auto or cn.
- AC-2: PASS — [.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md](.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md#L27) requires at least two candidate strategies plus a recommendation; [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L40), [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L61), [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L63), [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L67), and [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L69) document three evaluated strategies and the recommended property-trap replacement with rationale.
- AC-3: PASS — [.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md](.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md#L28) requires child tasks with scoped AC; [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L77) and [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L78) define the follow-ups, while [.owlbear/kanban/tasks/1496-cockpit-replace-pds-appendchild-monkeypatch-with-property-trap-on-document-porsc.md](.owlbear/kanban/tasks/1496-cockpit-replace-pds-appendchild-monkeypatch-with-property-trap-on-document-porsc.md#L11), [.owlbear/kanban/tasks/1496-cockpit-replace-pds-appendchild-monkeypatch-with-property-trap-on-document-porsc.md](.owlbear/kanban/tasks/1496-cockpit-replace-pds-appendchild-monkeypatch-with-property-trap-on-document-porsc.md#L23), [.owlbear/kanban/tasks/1497-cockpit-remove-dead-pdspartialsplugin-from-vite-config-ts.md](.owlbear/kanban/tasks/1497-cockpit-remove-dead-pdspartialsplugin-from-vite-config-ts.md#L12), and [.owlbear/kanban/tasks/1497-cockpit-remove-dead-pdspartialsplugin-from-vite-config-ts.md](.owlbear/kanban/tasks/1497-cockpit-remove-dead-pdspartialsplugin-from-vite-config-ts.md#L23) show both children are attached to #1495 and carry their own acceptance criteria.
- Test-to-AC alignment and proof sufficiency: PASS — [.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md](.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md#L30) sets proof bundle skip, so scoped lint is the required proof surface. Builder supplied clean quality-runner evidence at [.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md](.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md#L188) and [.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md](.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md#L192), and direct inspection of [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L54) plus [.owlbear/research/1495-pds-v4-local-hosting.md](.owlbear/research/1495-pds-v4-local-hosting.md#L56) confirms the repaired paragraph/list boundary that previously triggered MD032.
- Safety and security: PASS — this cycle changes no runtime code or dependencies; builder scope is limited to the research note listed at [.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md](.owlbear/kanban/tasks/1495-cockpit-research-pds-v4-local-hosting-and-scope-cdn-patch.md#L184).

## Observations
- No blocking findings.