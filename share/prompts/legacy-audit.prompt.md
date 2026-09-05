---
description: "Run a read-only, evidence-calibrated legacy cleanup audit for stale references and compatibility residue."
---

# Legacy Audit

You are running a read-only cleanup audit and producing a severity-ranked report.

Optional scope input: ${input:scope:Files or surface to audit (optional)}

## Interaction Protocol

Use the user's language unless they ask otherwise. Keep working until the user explicitly stops or
pauses, or until the finding queue is exhausted. Present exactly one finding, action, or continuation
decision before each `askQuestions`; never request a bulk decision. An empty or exhausted queue is a
valid terminal condition; do not manufacture a continuation decision.

When asking the user to choose an action, include status quo, problem, options with
pro/con/risk/confidence, recommendation, and expected outcome. Include `(bp:)` and `(rec:)` when
useful.

## Step 1 - Load authority and scope

Before scanning, read:

- `../skills/h-codebase-orientation/SKILL.md` for project and test-boundary discovery.

Inspect the relevant package manifests and test configuration before selecting commands. State the
selected scope, language/toolchain boundaries, and exclusions before collecting findings.

Determine scope:

- Use `${input:scope}` when provided.
- If no scope is provided, audit tracked active source and test files in the workspace.
- Do not silently broaden a supplied scope. Treat a scope that names an excluded location as an
   explicit request to inspect that location, but still classify archives and generated output as
   non-live evidence.

Unless the user explicitly includes them, exclude:

- `.owlbear/legacy/**` except for provenance lookups;
- `.owlbear/delivery/runtime/**`, `.owlbear/delivery/worktrees/**`, `.owlbear/completed/**`,
   `.owlbear/target/**`, and `.owlbear/scratch/**`;
- `.venv/**`, `**/node_modules/**`, `**/__pycache__/**`, `**/.pytest_cache/**`,
   `**/.ruff_cache/**`, and `**/*.egg-info/**`;
- generated build, coverage, test-result, and linter-report directories, including `dist/**`,
   `coverage/**`, `test-results/**`, and `megalinter-reports/**`.

The immutable legacy snapshot is a provenance authority, not live source. Current Delivery work is
identified by Change IDs and completion records; do not expect or synthesize numeric TODO markers
for it.

## Step 2 - Execute scan checks

Inspect the scoped surface and collect an internal finding queue for all categories below.

1. Stale task TODOs
    - Find `TODO(#nnnn)` references only in the selected live scope.
    - Resolve each numeric ID against the hash-verified immutable legacy snapshot, using its manifest
       and referenced preserved record.
    - Report a TODO only when the record proves the task is archived or completed. If the record is
       missing, unverifiable, or nonterminal, protect the TODO and state that provenance is unresolved.
    - Do not treat archive text as a live TODO and do not infer task status from filename or wording.
2. Dead references
    - For Python, use the configured Ruff boundary and `F401` output for unused imports; inspect
       clean-tooling candidates rather than treating a successful lint run as proof that no dead code
       exists.
    - For TypeScript or JavaScript, use the package's configured compiler, linter, test, and
       language-aware reference/export checks when the selected scope includes that toolchain. Do not
       claim an unreferenced module or export from a text search alone.
    - For likely zero-caller functions, inspect definitions, callers, imports, exports, entry points,
       and registration tables. Before reporting one above low confidence, exclude framework-discovered
       callables such as FastAPI or MCP routes/tools, Pydantic validators, pytest fixtures/plugins,
       React components and event handlers, Vite or test configuration callbacks, CLI entry points,
       `__all__` exports, dynamic imports, callbacks, and reflection or string-based dispatch.
    - Record the exact detection method and whether the result is an unused import, unreferenced
       export/module, or zero-caller candidate.
3. Mock staleness
    - Find mocks, fakes, patches, and fixtures in the selected test boundary.
    - Verify mocked targets, attributes, methods, and signatures against the current public interface.
       A mock target that still exists is not stale by itself; report only removed, renamed, or
       behaviorally incompatible contracts, and protect uncertain cases.
4. Legacy naming residue
    - Inspect function, class, module, and compatibility-branch definitions in live source for
       `legacy`, `compat`, `bridge`, and `shim`.
    - Treat domain nouns, archive/snapshot implementations, migration readers with a live target,
       and active compatibility boundaries as intentional unless other evidence shows residue.
    - Report a name or compatibility path only when supported by one or more additional signals:
       no live caller, a removed target interface or format, a redundant migration branch, or a
       fallback/alias that no maintained producer or consumer can exercise.
    - Include non-name-based residue such as old-field aliases, fallback readers, version branches,
       and adapters when they meet the same evidence rule. A keyword match alone is never a finding.

The audit discovers candidates; it does not decide architectural removal. Use `/test-curation` for
current test-suite quality work, `/arch-audit` for module or boundary deletion questions, and
`/ideate` or `/design` to turn an accepted cleanup proposal into a governed Delivery Change.

## Step 3 - Produce ranked cleanup report

Build findings grouped by type using this exact section order:

1. stale-task-todos
2. dead-references
3. mock-staleness
4. legacy-naming

For every accepted entry, record:

- status: `confirmed` or `candidate`;
- severity: `high`, `medium`, or `low`;
- confidence: `high`, `medium`, or `low`;
- detection method: `tool`, `static-reference`, `history`, `provenance`, or `runtime`;
- file path and line or symbol;
- task ID when applicable;
- concrete evidence and the reason the item appears stale;
- recommended next route: `inspect`, `test-curation`, `arch-audit`, `ideate`, `design`, or `none`.

Use these calibration rules:

- High severity means the evidence identifies a terminal, obsolete reference or a compatibility
   path that can mislead maintainers or block safe removal across an active boundary.
- Medium severity means multiple signals indicate likely residue, but a bounded inspection or owner
   decision is still needed.
- Low severity means the item is heuristic, naming-led, or dependent on unresolved dynamic behavior.
- High confidence requires direct tool, provenance, history, or reproducible call-site evidence.
   Medium confidence requires multiple consistent static signals. Low confidence is appropriate for a
   single heuristic signal or any candidate with plausible dynamic dispatch.
- Never rank a naming-only match above low severity or confidence.

Rank entries by severity, then confidence, then breadth of affected code. If many uninspected
candidates remain, show category counts and ask which single item to inspect next; every accepted
finding must receive the complete evidence record above before it enters the final queue.

## Step 4 - Guardrails and closeout

Before final output, confirm that the selected scope and exclusions were honored; all four categories
appear in the required order with severity, evidence, confidence, and detection method; and cleanup
actions remain suggestions for user decision. If the queue is empty, report the empty result and the
evidence limits instead of asking the user to continue.

## Guardrails

- Do not broaden scope silently beyond the selected surface.
- Do not use raw keyword matches, zero textual callers, or an existing mock target as standalone
   proof of stale code.
- Protect missing or unverifiable legacy provenance and dynamic-dispatch candidates.
- Keep archive, Delivery state, generated output, and retained worktrees out of live findings unless
   the user explicitly scopes them in.
