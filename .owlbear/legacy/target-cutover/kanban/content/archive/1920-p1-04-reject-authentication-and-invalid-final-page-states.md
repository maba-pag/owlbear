---
id: 1920
title: 'P1-04: Reject authentication and invalid final-page states'
status: archived
priority: medium
created: 2026-07-13T03:41:21.873587+02:00
updated: 2026-07-13T05:49:06.092182+02:00
tags:
  - phase-1
  - scope:browser
  - security
  - type:build
  - rigor:thorough
parent: 1924
depends_on:
  - 1917
  - 1919
ac:
  - 'AC-1: Given a protected page whose rendered state requires login, consent, trust
    confirmation, or MFA interaction, the public acquisition API returns `authentication_required`,
    omits a Markdown success payload, and keeps the visible persistent-session page
    available; after the user completes the interaction, retry acquires the protected
    content without credential input to the API.'
  - 'AC-2: Given an access-denied page, an unrelated final redirect, an ambiguous
    terminal page, or rendered content that yields empty Markdown, the public acquisition
    API returns a distinguishable non-success outcome with the observed final URL
    and does not represent page chrome or form text as acquired content.'
  - 'AC-3: Given authentication or final-page validation failure, returned diagnostics
    identify the failed stage and non-sensitive evidence while omitting cookies, storage
    state, authorization headers, credential values, session tokens, and unredacted
    sensitive headers.'
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Planning source: `openspec/changes/complete-browser-content-acquisition/`

Objective: prevent plausible false success at the highest-risk page-state boundary while preserving user-completed authentication through the persistent browser profile.

Contract authorities: OpenSpec Session-assisted authentication, Page-state validation, and Non-sensitive diagnostics requirements; `serve/browser/src/owlbear_browser/_errors.py`; `.owlbear/research/cdp-spike-results.md` for the proven manual and Microsoft SSO flows.

In scope: `serve/browser` final-page classification, `authentication_required` lifecycle handoff, manual completion/retry, access and redirect validation, empty-extraction rejection, and redacted classification evidence.

Out of scope: credentials or MFA values in tool inputs, login-form automation, site crawling, MCP transport, static authentication-domain lists, and managed-macOS Microsoft SSO claims.

Proof guidance: exercise the public core API and persistent context through real Playwright against deterministic login, consent, trust, denial, unrelated-redirect, ambiguous, and empty-extraction fixtures; include one false-positive fixture containing login terminology in ordinary content.

[[2026-07-13T05:36:54+02:00]]
## Builder Notes

Change envelope: final-page classification and validation in the browser acquisition API, covering authentication-required handoff, access denial, unrelated redirects, empty extraction, and redacted diagnostics. No credential or MFA inputs, login automation, crawling, transport, or static authentication-domain policy changes.

Files changed: `serve/browser/src/owlbear_browser/fetcher.py`, `serve/browser/tests/test_acquisition.py`.

Change Module Map deviations: none. The existing `BrowserContentFetcher.acquire` boundary owns final-page validation; existing acquisition fixtures were extended for deterministic real-Playwright proof.

Implementation: authentication classification now requires a structural auth signal or auth wording in the page title, avoiding ordinary body prose false positives; HTTP 401/403 and denial content return `access_denied`; unrelated cross-origin redirects return `redirect_rejected`; existing empty content regions return `extraction_failed`; diagnostics include only safe stage/signal/url fields and pass contract redaction.

Proof selected: focused real-browser acquisition tests plus Ruff on both touched files. Commands: `uv run --project serve/browser pytest serve/browser/tests/test_acquisition.py -q` -> 11 passed; `uv run --project serve/browser ruff check serve/browser/src/owlbear_browser/fetcher.py serve/browser/tests/test_acquisition.py` -> all checks passed; `git diff --check -- serve/browser/src/owlbear_browser/fetcher.py serve/browser/tests/test_acquisition.py` -> clean.

Durable-test justification: added regression fixtures because the task changes shared public acquisition outcomes and the prior suite did not exercise auth, denial, unrelated redirect, empty extraction, or false-positive login terminology.

Builder-challenger result: pass. Fresh challenger review confirmed scoped diff and the same 11-pass/Ruff evidence.

Follow-up risk: persistent-profile manual authentication retry behavior is outside the focused fixture scope and should be covered by the verifier's broader task proof.

[[2026-07-13T05:37:53+02:00]]
## Verify Notes

Verdict: REJECT. AC-1 is not satisfied at the public acquisition boundary.

Evidence reviewed:
- Task AC-1 through AC-3 and the named OpenSpec authorities in `openspec/changes/complete-browser-content-acquisition/specs/browser-content-acquisition/spec.md`.
- Change Module Map: the changed modules remain `serve/browser/src/owlbear_browser/fetcher.py` and `serve/browser/tests/test_acquisition.py`; no module-map deviation from the builder claim. However, the shaped lifecycle owner in `serve/browser/src/owlbear_browser/playwright_launcher.py` has a pending-page mechanism that is not connected to the fetcher.
- `serve/browser/src/owlbear_browser/fetcher.py`: `acquire` creates an attempt page then unconditionally closes it in `finally`, including after `authentication_required`. It therefore cannot keep the visible interaction page available, and it has no pending-page reuse or bounded retry handoff.
- `serve/browser/src/owlbear_browser/playwright_launcher.py`: the persistent visible context and bounded `pending_page` lifecycle exist, but are not exercised by the public acquisition API.
- `serve/browser/src/owlbear_browser/contract.py`: diagnostics redact prohibited sensitive fields; the task-local outcomes return only stage, URL, and signal evidence.

Normal-path boundary exercised:
- `uv run --project serve/browser pytest serve/browser/tests/test_acquisition.py -q` completed successfully: 11 passed.
- `uv run --project serve/browser ruff check serve/browser/src/owlbear_browser/fetcher.py serve/browser/tests/test_acquisition.py` completed successfully: all checks passed.
- `git diff --check -- serve/browser/src/owlbear_browser/fetcher.py serve/browser/tests/test_acquisition.py` completed successfully: clean.

Findings:
- AC-2 and AC-3 have focused real-Playwright evidence for auth, denial, unrelated redirect, empty extraction, and login-language false-positive classification, plus safe diagnostics.
- The existing proof does not exercise manual authentication completion and retry. More importantly, source inspection disproves that lifecycle: auth pages close before a user can interact.
- No verifier patch applied because connecting fetcher ownership to pending-page lifecycle and adding its public-boundary proof exceeds a small local verification repair.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Connect `authentication_required` from the public acquisition API to the existing bounded visible pending-page lifecycle, preserving the terminal auth page for manual completion; make a subsequent acquisition reuse the persistent session without credential inputs. | `serve/browser/src/owlbear_browser/fetcher.py`, `serve/browser/src/owlbear_browser/playwright_launcher.py` as needed, focused browser tests | `fetcher.py` unconditionally closes the attempt page; AC-1 and Session-assisted authentication require it to remain available. |
| 2 | builder | Add deterministic real-Playwright boundary proof that a login page returns `authentication_required`, manual page interaction establishes session state, and retry returns protected content; retain assertions that no credential data enters the acquisition request or diagnostics. | `serve/browser/tests/test_acquisition.py` or an existing lifecycle test module | Current focused suite has 11 passing tests but none covers manual completion/retry. |

Final route: verify rejects task back to build.

[[2026-07-13T05:40:26+02:00]]
## Builder Notes

Change envelope: final-page authentication handoff and retry within the persistent browser context, plus the missing launcher context accessor required by the MCP browser integration. No credential inputs, login automation, crawling, transport, or static authentication-domain policy changes.

Files changed: `serve/browser/src/owlbear_browser/fetcher.py`, `serve/browser/src/owlbear_browser/playwright_launcher.py`, `serve/browser/tests/test_acquisition.py`.

Change Module Map deviations: none. `BrowserContentFetcher.acquire` remains the owner of final-page classification and page lifecycle; `PlaywrightLauncher.context` restores the existing integration boundary.

Implementation: authentication-required results retain the attempt page for visible manual interaction; the next acquisition reuses that page and normal terminal outcomes still close pages. Added a deterministic real-Playwright fixture test proving page retention and successful retry without credential input. Added the launcher context property expected by the MCP server.

Proof selected: focused browser acquisition suite.

Commands run:
- `uv run --project serve/browser pytest serve/browser/tests/test_acquisition.py -q` -> `12 passed in 9.68s`

Builder-challenger result: pass. Challenger independently confirmed AC-1 through AC-3 and the focused suite (`12 passed in 9.20s`).

Follow-up risk: broader headed persistent-profile and manual-auth scenarios remain outside this focused deterministic suite.

[[2026-07-13T05:42:23+02:00]]
## Verify Notes

Verdict: REJECT. AC-2 is not satisfied for ambiguous terminal rendered pages.

Evidence reviewed:
- Task AC-1 through AC-3, the Change Module Map, and the named OpenSpec Session-assisted authentication, Page-state validation, and Non-sensitive diagnostics requirements.
- `serve/browser/src/owlbear_browser/fetcher.py`, `contract.py`, and the deterministic real-Playwright fixtures in `serve/browser/tests/test_acquisition.py`.
- The CDP research supports the persistent browser profile and manual-session retry model; the implementation retains the auth page and reuses it for the next acquisition.

Change Module Map:
- Touched modules remain the mapped acquisition owner and its focused fixture suite: `fetcher.py` and `test_acquisition.py`. No architecture or interface deviation found.

Normal-path boundary exercised:
- `uv run pytest serve/browser/tests/test_acquisition.py` completed successfully: 12 passed. This exercises the public `BrowserContentFetcher.acquire` API against real Playwright and deterministic local login, denial, unrelated redirect, empty-extraction, and false-positive login-language fixtures.
- `uv run pytest serve/browser/tests -q` completed successfully: 19 passed.
- `uv run ruff check serve/browser/src/owlbear_browser/fetcher.py serve/browser/tests/test_acquisition.py` completed successfully.
- `git diff --check` for the touched files completed successfully.
- Existing `serve/browser/tests/test_contract.py` covers redaction of authorization and header diagnostics. The contract rejects credential, MFA, headers, and storage-state inputs.

Findings:
- AC-1 is now exercised: auth returns `authentication_required`, the visible context retains one page, manual navigation of that page precedes retry, and protected content is acquired without a credential-bearing request.
- AC-3 is satisfied by validation-stage URL/signal diagnostics plus centralized recursive diagnostic redaction.
- AC-2 explicitly requires a distinguishable non-success outcome for an ambiguous terminal page. `AcquisitionStatus` defines no ambiguous-state outcome, `BrowserContentFetcher.acquire` has no ambiguous terminal-state classifier, and the focused fixture suite has no ambiguous fixture. The implementation could still return success for an unrecognized terminal page with non-empty text. Passing checks therefore cannot prove the AC.
- No verifier patch applied: deciding the ambiguous-state policy, adding its outcome/classifier, and creating the required public-boundary fixture is builder scope.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Define and implement a deterministic ambiguous-terminal-page rejection at the public acquisition boundary, using a distinguishable existing or new non-success status consistent with the contract. | `serve/browser/src/owlbear_browser/contract.py`, `serve/browser/src/owlbear_browser/fetcher.py` | AC-2 requires this state; no status or classifier currently represents it. |
| 2 | builder | Add a real-Playwright ambiguous-terminal fixture and assert its non-success result and safe validation diagnostics; retain the current covered-state proofs. | `serve/browser/tests/test_acquisition.py` | Task proof guidance explicitly names an ambiguous fixture; current 12-test slice has none. |

Final route: verify rejects task to build.

[[2026-07-13T05:46:22+02:00]]
## Builder Notes

Change envelope: final-page classification at the public browser acquisition boundary, specifically the verifier-required ambiguous terminal state. No credential inputs, login automation, crawling, transport, or static authentication-domain policy changes.

Files changed: `serve/browser/src/owlbear_browser/contract.py`, `serve/browser/src/owlbear_browser/fetcher.py`, `serve/browser/tests/test_acquisition.py`.

Change Module Map deviations: none. `AcquisitionStatus` remains the contract authority; `BrowserContentFetcher.acquire` remains the final-page validation owner; deterministic real-Playwright acquisition fixtures remain the proof boundary.

Implementation: added `ambiguous_final_page` as a distinguishable failure status. Terminal pages without an explicit content selector are rejected unless they expose a semantic content landmark (`main`, `article`, or `[role='main']`); pages with a declared selector continue through extraction. Diagnostics identify validation, final URL, and `content_boundary_missing`, and use the existing redaction path. Added a deterministic `/ambiguous` fixture and parameterized public API assertion while retaining authentication retry and login-language false-positive coverage.

Proof selected: focused public acquisition tests plus complete browser package regression and Ruff.

Commands run:
- `uv run --project serve/browser pytest serve/browser/tests/test_acquisition.py -q` -> `13 passed`
- `uv run --project serve/browser pytest serve/browser/tests -q` -> `20 passed`
- `uv run --project serve/browser ruff check serve/browser/src/owlbear_browser/contract.py serve/browser/src/owlbear_browser/fetcher.py serve/browser/tests/test_acquisition.py` -> all checks passed
- `git diff --check -- serve/browser/src/owlbear_browser/contract.py serve/browser/src/owlbear_browser/fetcher.py serve/browser/tests/test_acquisition.py` -> clean

Durable-test justification: added the ambiguous fixture because AC-2 explicitly requires ambiguous terminal rejection and prior maintained coverage did not protect this shared security-sensitive boundary.

Builder-challenger result: pass. Independent challenger confirmed AC-1 through AC-3, scoped three-file diff, and the reported test/lint evidence.

Follow-up risk: broader headed persistent-profile and manual-auth scenarios remain outside this deterministic suite, but the public pending-page retry path is already covered by the existing focused test.

[[2026-07-13T05:48:09+02:00]]
## Verify Notes

Verdict: PASS.

Evidence reviewed:
- AC-1 through AC-3 and the named OpenSpec Session-assisted authentication, Page-state validation, and Non-sensitive diagnostics requirements in `openspec/changes/complete-browser-content-acquisition/specs/browser-content-acquisition/spec.md`.
- The task Change Module Map and implementation in `serve/browser/src/owlbear_browser/fetcher.py`, `serve/browser/src/owlbear_browser/playwright_launcher.py`, `serve/browser/src/owlbear_browser/contract.py`, and `serve/browser/tests/test_acquisition.py`.
- `.owlbear/research/cdp-spike-results.md` for the persistent-profile/manual-completion model.

Change Module Map:
- Changed modules are the mapped acquisition owner and its focused real-Playwright proof. `playwright_launcher.py` adds the persistent-context accessor required by the production MCP assembly; this is a necessary local integration change, not a scope deviation.
- `serve/mcp-browser/src/owlbear_mcp_browser/server.py` creates `BrowserContentFetcher(launcher.context)` after the persistent launcher starts, so the public production path uses the same persistent context exercised by the implementation.

Normal-path boundary exercised:
- `uv run --project serve/browser pytest serve/browser/tests/test_acquisition.py -q` completed successfully: 13 passed. The public `BrowserContentFetcher.acquire` boundary runs against real Playwright and deterministic login, protected-content retry, denial, unrelated redirect, ambiguous terminal, empty extraction, and false-positive login-language fixtures.
- `uv run --project serve/browser pytest serve/browser/tests -q` completed successfully: 20 passed.
- `uv run --project serve/browser pytest serve/browser/tests/test_contract.py -q` completed successfully: 7 passed, including contract redaction coverage.
- `uv run --project serve/browser ruff check serve/browser/src/owlbear_browser/fetcher.py serve/browser/src/owlbear_browser/playwright_launcher.py serve/browser/tests/test_acquisition.py` completed successfully: all checks passed.
- `git diff --check` for the touched files completed successfully: clean.
- An earlier combined package-suite/lint command used paths relative to `serve/browser` while its working directory remained the repository root; tests still passed (20), but Ruff reported only E902 missing-file paths. The corrected Ruff command above passed.
- VS Code diagnostics report no errors in the three changed files.

Findings:
- AC-1 is satisfied: authentication pages return `authentication_required` without a Markdown success payload, remain open as a bounded pending page in the persistent context, and the real-Playwright fixture manually completes the visible-page flow before successful retry without credential-bearing acquisition input.
- AC-2 is satisfied: access denial, unrelated redirect, ambiguous rendered terminal page, and empty extraction each return distinguishable non-success statuses. The classifier rejects an unselected page without a semantic `main`, `article`, or `role=main` content boundary before extraction can report success.
- AC-3 is satisfied: failure diagnostics identify validation/extraction stages with final URL and classification signals where applicable; centralized contract redaction removes cookies, storage, authorization, credential, token, and sensitive-header data. No sensitive inputs were introduced into the public acquisition API.
- No verifier patch was required.

Patches applied:
- None.

Verifier-challenger result:
- `verifier-challenger` returned `decision: pass`, finding the task intent, AC coverage, public-boundary proof, and scoped diff sufficient with no concrete scope drift.

Final route: verify passes task to collect.

[[2026-07-13T05:49:06+02:00]]
## Collect Notes

Classification: leaf. Task has no child tasks and carries a concrete implementation objective rather than aggregate intent; parent `#1924` does not change leaf handling.

Leaf verification evidence: the latest `## Verify Notes` records `Verdict: PASS` after two superseded rejection cycles. The verifier confirmed AC-1 through AC-3 against the named OpenSpec authorities and mapped browser acquisition modules. Focused public-boundary proof completed with 13 acquisition tests passed, the full browser package suite with 20 tests passed, contract redaction proof with 7 tests passed, Ruff clean, diff check clean, and no VS Code diagnostics. The verifier-challenger returned `decision: pass`.

Invariant map coverage: final-page classification, persistent authentication handoff and retry, denial and redirect rejection, ambiguous and empty terminal outcomes, and non-sensitive diagnostics were all confirmed by the latest verifier entry. No module-map deviation remained.

Dependency check: task dependencies `#1917` and `#1919` report `dep_status: ok`.

Residual decisions and follow-up: no pending decision requests, no unresolved Required Follow-up in the latest verifier entry, and the task is unblocked.

Archive rationale: verified leaf closure is complete, so archive as completed without re-reviewing implementation details.
