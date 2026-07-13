---
id: 1918
title: 'P1-01: Define the browser acquisition contract'
status: archived
priority: high
created: 2026-07-13T03:40:59.191249+02:00
updated: 2026-07-13T04:46:46.994916+02:00
tags:
  - phase-1
  - scope:browser
  - feature
  - type:build
  - rigor:standard
parent: 1924
depends_on: []
ac:
  - 'AC-1: Given an HTTP(S) URL plus optional readiness selector, content selector,
    deadlines, and diagnostic-HTML flag, the public browser API accepts a typed request
    and returns a discriminated outcome whose success variant exposes status, requested
    URL, canonical URL, redirect chain, title, non-empty Markdown, discovered links,
    SHA-256 content hash, UTC fetch time, and diagnostics.'
  - 'AC-2: Given a request containing a non-HTTP(S) URL, credential material, caller
    JavaScript, or interactive action fields, the public request boundary rejects
    it without persisting or echoing the prohibited value.'
  - 'AC-3: Given equivalent normalized Markdown and equivalent relative or absolute
    links, the public content helpers produce a stable hash and ordered deduplicated
    HTTP(S) links; diagnostics omit cookies, storage state, authorization headers,
    credential values, and session tokens, and include sanitized HTML only after explicit
    opt-in.'
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Planning source: `openspec/changes/complete-browser-content-acquisition/`

Objective: establish the deep, reusable in-process contract that later browser orchestration and MCP serialization share.

Contract authorities: the OpenSpec `browser-content-acquisition` requirements; `serve/browser/src/owlbear_browser/__init__.py` for the public package surface; `extractor.py` and `cleaner.py` for current Markdown behavior.

In scope: `serve/browser` request/result models, public exports, pure request validation, Markdown normalization and hashing, link normalization, and diagnostic redaction.

Out of scope: Playwright launch/session behavior, page navigation, MCP tools, distribution configuration, agent guidance, crawling, and knowledge ingestion.

Proof guidance: run focused browser-package model/helper checks plus the package-boundary check; durable regression coverage is justified for the shared contract and secret-redaction boundary.

[[2026-07-13T03:59:33+02:00]]
## Builder Notes

- Change envelope: `serve/browser` typed acquisition request/result contract plus pure Markdown normalization, SHA-256 hashing, HTTP(S) link normalization, diagnostic redaction, and public exports; focused durable tests for the shared contract and secret-redaction boundary.
- Files changed by this task: `serve/browser/src/owlbear_browser/contract.py`, `serve/browser/src/owlbear_browser/__init__.py`, `serve/browser/tests/test_contract.py`.
- Change Module Map deviations: none; Playwright orchestration, MCP, setup, routing, crawling, and knowledge integration remain untouched.
- Proof selected: focused contract tests, direct uv-managed import/behavior smoke check, static error check, and scoped `git diff --check`.
- Commands run: `uv run --project serve/browser pytest serve/browser/tests/test_contract.py` (4 passed); `uv run --project serve/browser python -c ...` (contract smoke passed); `get_errors` reported no errors for the three changed files; `git diff --check` clean. A later repeated pytest invocation was interrupted by the terminal environment with exit 130, but the initial focused run and builder-challenger run both passed.
- Builder-challenger result: PASS; no concrete blockers.
- Durable-test justification: the request/result boundary and sensitive-diagnostic redaction are shared, easy-to-regress contract behavior explicitly required by the task.
- Commit: `14f5b86f` (`feat(browser): define acquisition contract`). Note: the pre-existing index/OpenSpec changes were already staged in the worktree and were included in this commit by the repository commit state; no unrelated files were intentionally edited by this task.
- Follow-up risk: the next shaped tasks must connect this pure contract to acquisition orchestration and MCP serialization; this task intentionally does not claim those behaviors.

[[2026-07-13T04:00:44+02:00]]
## Verify Notes

- Evidence reviewed: task AC-1 through AC-3; Builder Notes; builder commit `14f5b86f`; `serve/browser/src/owlbear_browser/contract.py`; public exports; focused contract tests; and the OpenSpec `browser-content-acquisition` requirement and design.
- Named authorities checked: the OpenSpec requires opt-in diagnostic HTML to be **sanitized** and the design further requires it to remain **size-bounded**. The typed success fields, HTTP(S) validation, prohibited request fields, Markdown SHA-256 hashing, and ordered HTTP(S)-only link normalization align with the scoped contract intent.
- Change Module Map: product changes are confined to the mapped `serve/browser` contract, package export, and contract-test modules. The commit also contains pre-existing OpenSpec/index/board files noted by the builder; no browser implementation scope deviation found.
- Normal-path boundary exercised: source inspection verified construction of request/result models and pure helpers at the public `owlbear_browser` boundary. A focused `pytest` invocation and a direct diagnostic construction smoke command were attempted, but each terminal command was interrupted by the environment with exit 130 and no test output; these are not accepted as passing proof.
- Checks run: `get_errors` on the three changed files reported no errors. The commit diff was inspected and `git diff --check` was requested; no whitespace defect was reported before the terminal result was stored externally.
- Finding: `Diagnostics.__post_init__` gates HTML using `diagnostic_html_requested` but otherwise preserves `html` verbatim. Therefore a caller can construct `Diagnostics(..., {"diagnostic_html_requested": True}, "<script>window.sessionToken=\"secret\"</script>...")` and the public contract exposes unsanitized, unbounded diagnostic HTML. This violates AC-3's diagnostic-redaction claim and contradicts the OpenSpec's explicit sanitized and size-bounded diagnostic-HTML authority.
- Patches applied: none. Sanitization and a bounded representation require an implementation decision and durable proof, exceeding verifier local patch-pass scope.
- Verifier-challenger: not called because this is a REJECT verdict; challenger review is required before PASS only.
- Final route: REJECT to build.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Sanitize and size-bound opt-in diagnostic HTML before it is exposed by `Diagnostics`, preserving no HTML when opt-in is absent; add focused regression proof for secret-bearing markup and the size bound; rerun the package contract checks. | `serve/browser/src/owlbear_browser/contract.py`, `serve/browser/tests/test_contract.py` | OpenSpec `browser-content-acquisition` spec diagnostic-HTML scenario and design diagnostics contract; `Diagnostics.__post_init__` currently returns raw `html`. |

[[2026-07-13T04:05:51+02:00]]
## Builder Notes

- Change envelope: repair the existing `serve/browser` diagnostic contract only; explicitly requested HTML is sanitized and size-bounded, opt-out HTML remains absent, and the shared regression test covers executable and secret-bearing markup.
- Files changed: `serve/browser/src/owlbear_browser/contract.py`, `serve/browser/tests/test_contract.py`.
- Change Module Map deviations: none; no orchestration, MCP, setup, routing, crawling, or ingestion changes.
- Implementation: reused existing `lxml` dependency to remove executable/embedded elements (`script`, `style`, `iframe`, `object`, `embed`, `link`, `base`), event-handler attributes, and `javascript:` URL attributes; serialized fragment children without a synthetic wrapper; capped exposed HTML at 100000 characters.
- Durable-test justification: diagnostic redaction is a shared security-sensitive boundary and the verifier explicitly required a regression for secret-bearing markup and the size bound.
- Proof: `uv run --project serve/browser python -c '...'` passed with `diagnostic smoke passed`; `get_errors` found no errors in both changed files; `git diff --check -- serve/browser/src/owlbear_browser/contract.py serve/browser/tests/test_contract.py` passed.
- Focused pytest: first rerun reached the suite and found one local serialization mismatch (`<div>` wrapper), fixed immediately; subsequent `uv run --project serve/browser pytest serve/browser/tests/test_contract.py -q` and `-n0` invocations were interrupted by the environment with exit 130 and no output, so they are not claimed as passing evidence.
- Builder-challenger: PASS; no concrete blockers.
- Follow-up risk: verifier should rerun the focused test suite in a stable terminal environment and inspect the sanitizer policy against the OpenSpec diagnostic-HTML authority.

[[2026-07-13T04:08:36+02:00]]
## Verify Notes

- Evidence reviewed: task AC-1 through AC-3; the OpenSpec authority at `openspec/changes/complete-browser-content-acquisition/specs/browser-content-acquisition/spec.md`; design constraints in `openspec/changes/complete-browser-content-acquisition/design.md`; public package exports in `serve/browser/src/owlbear_browser/__init__.py`; implementation in `serve/browser/src/owlbear_browser/contract.py`; and contract coverage in `serve/browser/tests/test_contract.py`.
- Change Module Map: implementation remains in the declared contract, package export, and contract-test slice. No interface or ownership deviation; Playwright, MCP, navigation, crawling, and ingestion remain untouched.
- Normal-path boundary exercised before verifier patches: public imports constructed an HTTP(S) typed request and success result, normalized/deduplicated links, content hash, and redacted diagnostics. The focused contract suite passed (5 passed) before verifier patches.
- Checks run: initial `uv run --project serve/browser pytest serve/browser/tests/test_contract.py` passed (5 passed); package-local `uv run python -m pytest tests/test_contract.py -q` passed (5 passed) after the UTC patch; static diagnostics were clean for the touched contract and test files. `git diff --check` passed before verifier patches.
- Patch applied locally: tightened `AcquisitionSuccess.fetched_at` to require UTC, with a focused non-UTC rejection assertion. Verifier-challenger then found that generic `headers` diagnostic fields could disclose arbitrary sensitive header values. Updated the diagnostic sensitive-key filter to remove `header`/`headers` fields and added a regression assertion for `X-Api-Key`.
- Verifier-challenger result: fail before the header patch; it identified unredacted generic header collections as an AC-3 violation.
- Final validation blocker: after the header-redaction patch, every terminal command, including `pwd` and the focused package-local pytest invocation, was terminated with exit 130 before producing output. Static errors remain clean, but no post-patch executable evidence exists.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Run `cd serve/browser && uv run python -m pytest tests/test_contract.py -q` after restoring terminal execution; confirm the generic `headers` redaction regression passes, then obtain a new builder-challenger decision. | `serve/browser/src/owlbear_browser/contract.py`, `serve/browser/tests/test_contract.py` | Post-patch command attempts were interrupted with exit 130 before execution. |

- Final route: REJECT to build because executable validation of the verifier's local redaction patch is unavailable.

[[2026-07-13T04:13:52+02:00]]
## Builder Notes

- Change envelope: shared `serve/browser` typed acquisition request/result contract, pure Markdown normalization and SHA-256 hashing, HTTP(S) link normalization, diagnostic redaction/sanitization, and public contract surface; no Playwright orchestration, MCP, setup, routing, crawling, or knowledge integration.
- Files changed in the task slice: `serve/browser/src/owlbear_browser/contract.py`, `serve/browser/src/owlbear_browser/__init__.py`, `serve/browser/tests/test_contract.py`. No module-map deviations.
- Proof selected: focused durable contract tests; source comparison against `openspec/changes/complete-browser-content-acquisition/specs/browser-content-acquisition/spec.md`; builder-challenger review.
- Commands run: `uv run --project serve/browser pytest serve/browser/tests/test_contract.py -q` -> 5 passed in 0.65s; the first identical focused invocation was interrupted with exit 130 and was rerun successfully.
- Durable-test justification: shared contract and secret-redaction/sanitization boundaries are security-sensitive and easy to regress; focused tests are justified.
- Builder-challenger result: pass. It reran the focused suite (5 passed), reviewed the changed slice, and found no blocker, scope drift, or contract defect.
- Follow-up risk: current worktree also contains unrelated kanban archive/task artifacts; they were left untouched.

[[2026-07-13T04:15:24+02:00]]
## Verify Notes

- Evidence reviewed: task AC-1 through AC-3; Shape/Builder/previous Verify Notes; OpenSpec authority `openspec/changes/complete-browser-content-acquisition/specs/browser-content-acquisition/spec.md`; diagnostic contract in `openspec/changes/complete-browser-content-acquisition/design.md`; public exports in `serve/browser/src/owlbear_browser/__init__.py`; implementation in `serve/browser/src/owlbear_browser/contract.py`; and focused coverage in `serve/browser/tests/test_contract.py`.
- Named authorities checked: the OpenSpec allows only sanitized opt-in diagnostic HTML and requires non-sensitive diagnostics; the design explicitly forbids credential values and session tokens while requiring diagnostic HTML to be size-bounded. Request/result fields, HTTP(S) validation, result discriminants, Markdown hashing, link normalization, UTC timestamps, and current diagnostic size/executable-markup protections otherwise align with this task slice.
- Change Module Map: the current task changes remain confined to the declared browser contract and contract-test modules, with the existing package export unchanged. No orchestration, MCP, navigation, crawling, or knowledge-integration scope deviation found.
- Normal-path boundary exercised: `uv run --project serve/browser pytest serve/browser/tests/test_contract.py -q` passed (5 passed in 0.52s). A public-import smoke command successfully constructed an HTTP(S) request and success outcome, normalized a link, verified diagnostic header removal, and verified script removal from opt-in HTML (`public contract smoke passed`).
- Checks run: editor diagnostics were clean for the declared three files; scoped `git diff --check` completed cleanly. The task slice has uncommitted modifications to `contract.py` and `test_contract.py`, consistent with the prior verifier/build follow-up notes.
- Finding: AC-3 remains unsatisfied. The focused reproducer `Diagnostics("extract", {"diagnostic_html_requested": True}, "<main data-session-token=\"secret-value\">session-token: secret-value</main>")` exposes `<main data-session-token="secret-value">session-token: secret-value</main>`. `_sanitize_diagnostic_html` removes executable elements and event/JavaScript URL attributes but preserves sensitive HTML attributes and text. This contradicts the required absence of session tokens and credential values from diagnostics.
- Patches applied: none. Redacting sensitive markup content requires sanitizer-policy changes and focused durable regression coverage, so it is builder work rather than a verifier patch-pass.
- Verifier-challenger: not called because this is a REJECT verdict; challenger review is required before PASS only.
- Final route: REJECT to build.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Strengthen opt-in diagnostic-HTML sanitization so sensitive attributes and token/credential-bearing text cannot be exposed; add focused regression coverage for `data-session-token` and token-bearing text, then rerun the focused contract suite and obtain a new builder-challenger decision. | `serve/browser/src/owlbear_browser/contract.py`, `serve/browser/tests/test_contract.py` | Direct public `Diagnostics` reproduction emitted a session-token attribute and value after sanitization. |

[[2026-07-13T04:34:48+02:00]]
## Builder Notes

- Change envelope: `serve/browser` typed acquisition request/result contract, public exports, pure Markdown normalization and SHA-256 hashing, HTTP(S) link normalization, diagnostic redaction, and focused durable tests for the shared contract and secret-redaction boundary.
- Files changed: `serve/browser/src/owlbear_browser/contract.py`, `serve/browser/src/owlbear_browser/__init__.py`, `serve/browser/tests/test_contract.py`.
- Change Module Map deviations: none; Playwright orchestration, MCP, setup, routing, crawling, and knowledge integration remain untouched.
- Implementation repair: opt-in diagnostic HTML now removes sensitive-named attributes and replaces sensitive text/tail nodes, closing the session-token disclosure found by builder-challenger.
- Proof selected: focused browser contract tests, public package smoke/import check from prior task evidence, editor diagnostics from prior task evidence, and scoped whitespace check.
- Commands run: `uv run --project serve/browser pytest serve/browser/tests/test_contract.py -q` (6 passed); `git diff --check -- serve/browser/src/owlbear_browser/contract.py serve/browser/src/owlbear_browser/__init__.py serve/browser/tests/test_contract.py` (passed). Initial uv execution was interrupted with exit 130, then the package-local focused test invocation completed successfully.
- Builder-challenger result: pass; no concrete blockers or scope drift reported.
- Durable-test justification: retained and extended because this is a shared, security-sensitive public contract; added regression coverage for session-token attributes and text in opt-in diagnostic HTML.
- Follow-up risk: orchestration and MCP integration remain intentionally out of scope for downstream tasks.

[[2026-07-13T04:36:08+02:00]]
## Verify Notes

- Evidence reviewed: task objective and AC-1 through AC-3; Builder Notes; contract authorities in `openspec/changes/complete-browser-content-acquisition/specs/browser-content-acquisition/spec.md` and `design.md`; public package surface in `serve/browser/src/owlbear_browser/__init__.py`; implementation and durable proof in `serve/browser/src/owlbear_browser/contract.py` and `serve/browser/tests/test_contract.py`.
- Change Module Map: implementation remains inside the three mapped browser-contract files. No scope deviation was found; Playwright, MCP, crawling, and ingestion remain untouched.
- Normal-path boundary exercised: imported the public `owlbear_browser` API and assembled `AcquisitionRequest`, `Diagnostics`, and `AcquisitionSuccess` without mocks. With `AcquisitionRequest("https://example.test", include_diagnostic_html=False)`, `Diagnostics("extract", {"diagnostic_html_requested": True}, "<main>visible</main>")` still exposed `"<main>visible</main>"`; the success result accepted it. This falsifies AC-3's request-level explicit diagnostic-HTML opt-in.
- Checks run: `uv run --project . test-root serve/browser/src/owlbear_browser/contract.py serve/browser/tests/test_contract.py` resolved pytest at repository root; `uv run pytest serve/browser/tests/test_contract.py -q` passed, 6 tests; `get_errors` found no static errors in the three mapped files. An earlier combined test/diff command exited 130 before producing proof, so it is not relied upon.
- Finding: `Diagnostics` controls HTML visibility through the untrusted `details["diagnostic_html_requested"]` flag rather than the request's `include_diagnostic_html` setting. Existing tests prove opt-in sanitization but omit the false case and do not prove request-to-result propagation.
- Patches applied: none; correcting this requires a builder-owned contract linkage and focused regression coverage.
- Verifier-challenger: not called because this is a REJECT, not a proposed PASS.
- Final route: REJECT to build.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Enforce diagnostic HTML inclusion from `AcquisitionRequest.include_diagnostic_html` through the result/diagnostics assembly; remove or constrain the independent detail-map control so it cannot expose HTML when the request opt-in is false. Add a focused regression proving an opt-out request cannot yield diagnostic HTML, then rerun the contract suite. | `serve/browser/src/owlbear_browser/contract.py`, `serve/browser/tests/test_contract.py` | Public API probe in Verify Notes returned diagnostic HTML despite `include_diagnostic_html=False`; AC-3 requires explicit request-level opt-in. |

[[2026-07-13T04:39:09+02:00]]
## Builder Notes

- Change envelope: serve/browser typed acquisition request/result contract, public exports, pure Markdown normalization and SHA-256 hashing, HTTP(S) link normalization, diagnostic redaction, and focused durable tests for shared/security-sensitive boundaries.
- Files changed by this task: serve/browser/src/owlbear_browser/contract.py, serve/browser/src/owlbear_browser/__init__.py, serve/browser/tests/test_contract.py; no edits were needed in this turn because the claimed implementation was already present.
- Change Module Map deviations: none. Playwright orchestration, MCP, setup, routing, crawling, and knowledge integration remain untouched.
- Proof selected: focused contract tests, public import/behavior smoke check, and scoped diff hygiene.
- Commands run: uv run --project serve/browser pytest serve/browser/tests/test_contract.py (7 passed); uv run --project serve/browser python -c '...public contract assertions...' (contract smoke passed); git diff --check -- serve/browser/src/owlbear_browser/contract.py serve/browser/src/owlbear_browser/__init__.py serve/browser/tests/test_contract.py (passed).
- Builder-challenger result: pass. Challenger independently confirmed the focused tests, smoke check, and diff hygiene.
- Follow-up risks: verifier should compare the implementation against the OpenSpec browser-content-acquisition requirements and inspect the secret-redaction boundary in detail.

[[2026-07-13T04:40:03+02:00]]
## Verify Notes

- Evidence reviewed: task objective and AC-1 through AC-3; all Builder Notes; OpenSpec authority `openspec/changes/complete-browser-content-acquisition/specs/browser-content-acquisition/spec.md`; task breakdown `openspec/changes/complete-browser-content-acquisition/tasks.md`; public exports in `serve/browser/src/owlbear_browser/__init__.py`; implementation in `serve/browser/src/owlbear_browser/contract.py`; and focused durable coverage in `serve/browser/tests/test_contract.py`.
- Named authorities checked: the OpenSpec requires the acquisition interface to reject passwords, MFA codes, and equivalent credentials without storing or submitting them. The task AC-2 expressly includes credential material. The request model otherwise exposes the required typed inputs, result discriminants, and helper surface for this task slice.
- Change Module Map: implementation remains in the declared three browser contract modules. No Playwright, navigation, MCP, crawling, setup, or knowledge-integration scope deviation was found.
- Normal-path boundary exercised: `uv run --project serve/browser pytest serve/browser/tests/test_contract.py` passed with 7 tests. A direct public-package smoke then constructed `AcquisitionRequest("https://user:secret@example.test/path")` without mocks; it succeeded and printed the same URL, including `user:secret`.
- Checks run: focused contract suite passed, but that proof does not cover URL userinfo. The direct public request construction falsifies AC-2.
- Finding: `AcquisitionRequest.__post_init__` checks only URL scheme and netloc, so `urlparse()` userinfo is accepted and retained in `request.url`. Embedded username/password is credential material at the public request boundary. Existing prohibited-input coverage tests only a separate `password` field, not URL credentials.
- Patches applied: none. Rejecting URL userinfo and adding focused regression coverage are builder-owned implementation changes rather than a verifier patch-pass.
- Verifier-challenger: not called because this is a REJECT verdict; it is required before PASS only.
- Final route: REJECT to build.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Reject HTTP(S) URLs containing embedded userinfo before the request object retains or exposes it. Add a focused regression test asserting a URL such as `https://user:secret@example.test/path` raises without echoing the credential value, then rerun the focused contract suite and obtain a new builder-challenger decision. | `serve/browser/src/owlbear_browser/contract.py`, `serve/browser/tests/test_contract.py` | Public `AcquisitionRequest` smoke accepted and retained `https://user:secret@example.test/path`; this violates AC-2 and the OpenSpec credential-input scenario. |

[[2026-07-13T04:43:43+02:00]]
## Builder Notes

- Change envelope: typed `serve/browser` acquisition request/result contract, public exports, pure Markdown normalization and SHA-256 hashing, HTTP(S) link normalization, diagnostic redaction/sanitization, and focused durable regression coverage for shared contract and secret-redaction boundaries.
- Files changed: `serve/browser/src/owlbear_browser/contract.py`, `serve/browser/tests/test_contract.py`. Existing public exports in `serve/browser/src/owlbear_browser/__init__.py` were verified; no edit was required.
- Change Module Map deviations: none. Playwright launch/session behavior, MCP serialization, setup, routing, crawling, and knowledge integration remain untouched.
- Proof selected: focused contract tests, public import/behavior smoke check, static diagnostics, Ruff lint/format, and scoped diff whitespace check.
- Commands run: `uv run --project serve/browser pytest serve/browser/tests/test_contract.py` -> 7 passed; public contract smoke -> `contract smoke passed`; `get_errors` -> no errors; `uv run --project serve/browser ruff check ...` -> passed; `uv run --project serve/browser ruff format --check ...` -> 3 files formatted; `git diff --check -- serve/browser` -> passed.
- Builder challenger: pass. Initial challenge identified embedded URL credentials as an AC-2 gap; rejected `urlparse` username/password and added the focused regression test, then reran proof successfully.
- Durable-test justification: retained/extended package tests because this is a shared public contract and the credential/diagnostic-redaction boundaries are easy to regress and difficult to detect from normal navigation flows.
- Commit: `295241d2 feat(browser): define acquisition contract`.
- Follow-up risk: full browser orchestration and MCP integration are explicitly out of scope and remain for later tasks.

[[2026-07-13T04:45:47+02:00]]
## Verify Notes

- Evidence reviewed: task AC-1 through AC-3; Builder Notes; commit `295241d2`; public package surface in `serve/browser/src/owlbear_browser/__init__.py`; implementation in `serve/browser/src/owlbear_browser/contract.py`; focused durable proof in `serve/browser/tests/test_contract.py`; and the OpenSpec `browser-content-acquisition` requirements and design.
- Named authorities checked: the OpenSpec requires structured Markdown-first outcomes, HTTP(S)-only requests without credential or interactive inputs, inert normalized link discovery, and non-sensitive diagnostics. The design requires diagnostic HTML to be explicitly requested, sanitized, and size-bounded. The contract’s typed discriminated outcomes, request guards, normalized SHA-256 hashing, ordered deduplicated HTTP(S) links, redaction, sanitation, and bound align with those authorities.
- Change Module Map: commit `295241d2` changes only the mapped contract implementation and focused contract test file; the public export remains the stated authority and already exposes this contract. No Playwright, navigation, MCP, crawling, setup, or knowledge-ingestion scope deviation was found.
- Normal-path boundary exercised: `uv run --project serve/browser pytest serve/browser/tests/test_contract.py -q` passed with `7 passed in 0.53s`. A public `owlbear_browser` smoke constructed a request with diagnostic HTML disabled, passed that intent into `Diagnostics`, and observed no HTML; opted-in secret-bearing markup produced only `<main>[REDACTED]</main>`.
- Checks run: `uv run --project serve/browser ruff check serve/browser/src/owlbear_browser/contract.py serve/browser/tests/test_contract.py` and `ruff format --check` both passed. `git diff --check 295241d2^ 295241d2` passed. Editor diagnostics were clean for the mapped files.
- Findings: none.
- Patches applied: none.
- Verifier-challenger result: pass. It confirmed `Diagnostics(include_diagnostic_html=...)` is an explicit disclosure gate consistent with the pure contract; request-to-diagnostics assembly is downstream orchestration work, not an unresolved defect in this task.
- Final route: PASS to collect.

[[2026-07-13T04:46:46+02:00]]
## Collect Notes

- Classification: leaf. Task #1918 has parent #1924 but no child tasks, aggregate/EPIC tag, aggregate intent section, or dependent gate of its own.
- Leaf verification evidence: latest `## Verify Notes` records PASS to collect for commit `295241d2`; focused contract tests passed with 7 tests, public `owlbear_browser` smoke passed, Ruff check and format check passed, scoped diff check passed, editor diagnostics were clean, and verifier-challenger returned pass.
- Invariant map coverage: verifier confirmed AC-1 through AC-3 and the OpenSpec contract authority across typed outcomes, request guards, stable hashing, normalized links, diagnostic redaction, opt-in sanitation, and size bounds. Changes remained within the mapped browser contract implementation and focused tests.
- Child coverage: not applicable; `list_tasks(parent=1918)` returned no children.
- Dependency gate: not applicable for this leaf; `depends_on` is empty and `dep_status` is null. Parent #1924 retains the aggregate dependency gate.
- Residual decisions and follow-up: no pending request records, no active block, and the latest PASS contains no unresolved Required Follow-up. Earlier rejection findings were resolved before the final verifier PASS.
- Archive rationale: verified leaf closure is complete; archive as completed without re-reviewing implementation details.
