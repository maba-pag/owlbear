---
id: 1653
title: 'P1-04: Verify handler equivalence for URL_LIST retype'
status: docs
priority: important
created: 2026-05-18T03:11:06.930657+02:00
updated: 2026-05-18T14:32:23.459094+02:00
tags:
  - scope:knowledge
  - research
parent: 1650
depends_on: []
ac:
  - 'AC-1: Research doc in `.owlbear/research/` compares handlers in `refresh.py`
    for `fetch_method="http"` sources covering: (a) fetch-path — prove both resolve
    to HttpxContentFetcher via select_content_fetcher; (b) content delivery — same
    string reaches ingest() with same scope/source_id; (c) counter math — identical
    RefreshResult shape; (d) metadata delta — list IntakeResult.metadata differences
    with per-field downstream-impact cite'
  - 'AC-2: Conclude PASS or FAIL: PASS requires (a)+(b)+(c) identical AND (d) no downstream
    logic branches on differing metadata. FAIL requires citing a codepath where metadata
    diff causes runtime divergence. If PASS, follow-up backlog task for _direct_source_config
    retype exists. If FAIL, append O3-dropped note to parent #1650'
proof_bundle: skip
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1650

## Scope

**In-scope:** Static analysis of `_handle_url_list` vs `_handle_authenticated_web` for `fetch_method="http"` sources. Determine whether `URL_LIST` handler produces equivalent refresh results.

**Out-of-scope:** Implementation of the retype (follow-up task if equivalence holds). Migration of existing `AUTHENTICATED_WEB` records.

## Context

O3 is gated on handler equivalence. `_direct_source_config` currently returns `(SourceType.AUTHENTICATED_WEB, "http", {"url": source_url, "urls": [source_url]})` for HTTP URLs. The proposed change would return `(SourceType.URL_LIST, "http", ...)` instead.

Key question: does `_handle_url_list` with `fetch_method="http"` produce the same documents, chunks, and refresh counters as `_handle_authenticated_web` for a single-URL source?

`_handle_url_list` is at line 199 in refresh.py. `_handle_authenticated_web` is at line 317.

[[2026-05-18T03:27:14+02:00]]
## Planning

Single-task shortcut: created follow-up #1656 at research.

| ID | Title | Priority | Status | Tags | Depends |
|----|-------|----------|--------|------|---------|
| 1656 | Retype _direct_source_config from AUTHENTICATED_WEB to URL_LIST for new HTTP sources | important | research | scope:knowledge | #1653 |

Proof bundle: behavioral. Parent: #1650.

[[2026-05-18T03:27:59+02:00]]
## Research
- Research doc: .owlbear/research/1653-url-list-handler-equivalence.md
- Sources: 9 studied (all codebase), 5 high-relevance
- Recommendation: PASS — conditional handler equivalence for fetch_method="http" (confidence: 0.82)
- Follow-up tasks created: #1656 (retype _direct_source_config, at research)
- Decision requests: none

## Challenge Results
- Challenger: proceed (confidence in original: 0.82)
- Key challenges: (1) metadata persistence — initially cited wrong ingest path for fetched_at backfill; (2) fetch-path equivalence is conditional on HttpxContentFetcher; (3) source-registry contract is separate concern
- Researcher response: accepted (1) — metadata IS persisted but no downstream consumer; rebutted (2) — condition always holds for _direct_source_config; accepted (3) — scoped verdict to refresh-handler only

[[2026-05-18T03:46:26+02:00]]
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Also tagged `research` — non-implementation task.
- Passing through to builder.

[[2026-05-18T03:46:58+02:00]]
## Builder Notes
- Implementation: no files changed (non-implementation pass-through)
- Tests: skipped (Proof bundle: skip; Test-Writer explicitly marked no new test writing required)
- Coverage: not applicable (no touched modules)
- ruff: not run (no code changes)
- Approach: validated task metadata/body and pass-through eligibility, then advanced directly per `w-tdd-green` Step 0a for proof-bundle skip.
- Evidence summary: AC artifacts already present from upstream research (`.owlbear/research/1653-url-list-handler-equivalence.md`), follow-up task #1656 already created, and task marked `research` + `Proof bundle: skip` in Test-Writer Notes.

[[2026-05-18T03:58:47+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: in-progress
- Builder evidence reviewed first: builder correctly reported a non-implementation pass-through with no changed code, so review was scoped to the research artifact and required follow-up task.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1 | The research comparison matrix contains a factual error: it states that empty-URL handling differs, but both handlers take the same `if not urls` branch and return a failed refresh result with `source has no URL configured`. The current artifact is therefore not an accurate handler comparison. | `.owlbear/research/1653-url-list-handler-equivalence.md:38`; `serve/knowledge/src/owlbear_knowledge/refresh.py:209`; `serve/knowledge/src/owlbear_knowledge/refresh.py:350` | in-progress |
| 2 | AC-2 | The PASS path requires a follow-up backlog task, but the created follow-up artifact is persisted in `research` status. AC-2 is not satisfied by the current board state. | `.owlbear/kanban/tasks/1653-p1-04-verify-handler-equivalence-for-url-list-retype.md:18`; `.owlbear/kanban/tasks/1656-retype-direct-source-config-from-authenticated-web-to-url-list-for-new-http-sour.md:5`; `.owlbear/research/1653-url-list-handler-equivalence.md:77` | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Correct the empty-URL comparison row in the research document and revalidate that the PASS conclusion still holds after the correction. | `.owlbear/research/1653-url-list-handler-equivalence.md`; `serve/knowledge/src/owlbear_knowledge/refresh.py` | Research matrix row at `.owlbear/research/1653-url-list-handler-equivalence.md:38` contradicts handler branches at `serve/knowledge/src/owlbear_knowledge/refresh.py:209` and `serve/knowledge/src/owlbear_knowledge/refresh.py:350` |
| 2 | builder | Create or reference an AC-compliant backlog follow-up for the `_direct_source_config` retype, then update task #1653 notes so the PASS path points to that backlog artifact. | `.owlbear/kanban/tasks/1653-p1-04-verify-handler-equivalence-for-url-list-retype.md`; `.owlbear/kanban/tasks/1656-retype-direct-source-config-from-authenticated-web-to-url-list-for-new-http-sour.md` | AC-2 requires a backlog follow-up at `.owlbear/kanban/tasks/1653-p1-04-verify-handler-equivalence-for-url-list-retype.md:18`; current follow-up is `status: research` at `.owlbear/kanban/tasks/1656-retype-direct-source-config-from-authenticated-web-to-url-list-for-new-http-sour.md:5` |

## Observations
- Planning notes still say `Proof bundle: behavioral` while the authoritative task field and downstream notes use `skip` (`.owlbear/kanban/tasks/1653-p1-04-verify-handler-equivalence-for-url-list-retype.md:53`, `.owlbear/kanban/tasks/1653-p1-04-verify-handler-equivalence-for-url-list-retype.md:70`). This did not change the verdict because frontmatter `proof_bundle` is authoritative, but the stale note should be cleaned up to avoid future review-scope confusion.

[[2026-05-18T04:15:38+02:00]]
## Builder Notes
- Files changed: .owlbear/research/1653-url-list-handler-equivalence.md
- Implementation scope: corrected the handler comparison matrix factual error for empty-URL handling; updated follow-up section to reference AC-compliant backlog artifact.
- Tests: skipped (Proof bundle: skip; non-implementation research correction)
- Coverage: not applicable (no runtime code changes)
- Ruff: not run (no Python source changes)
- Evidence summary:
  - Empty-URL behavior now correctly marked equivalent: both handlers return failed=1 with error "source has no URL configured".
  - AC-2 follow-up requirement satisfied via planner action: task #1656 is now in backlog with implementation tag and expanded AC for the retype scope.
- Fixes applied for prior review findings:
  1. Corrected incorrect matrix row in research doc (empty URL behavior).
  2. Ensured PASS path references a backlog follow-up task (#1656).

[[2026-05-18T12:47:21+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: backlog
- Builder evidence reviewed first: builder correctly addressed the prior AC-2 board-state issue and limited this retry to the research artifact, but AC-1 still fails because the memo overclaims handler equivalence without sufficient scoped proof.
- Review-cycle note: this is a second review cycle, so remaining blocking issues route back to backlog per pipeline policy.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1 | The memo still contradicts itself on chunk equivalence. It says metadata differences are persisted and propagated to chunks, then concludes that chunks are identical. The ingest path copies intake metadata into chunk metadata and persists it, so URL_LIST (`source_type=url`, `fetched_at`) and AUTHENTICATED_WEB (`source_type=authenticated_web`) do not produce identical chunk rows. | `.owlbear/research/1653-url-list-handler-equivalence.md:48`; `.owlbear/research/1653-url-list-handler-equivalence.md:64`; `serve/knowledge/src/owlbear_knowledge/ingest.py:429`; `serve/knowledge/src/owlbear_knowledge/chunker.py:132`; `serve/knowledge/src/owlbear_knowledge/document_store.py:119`; `serve/knowledge/src/owlbear_knowledge/intake.py:71`; `serve/knowledge/src/owlbear_knowledge/intake.py:72`; `serve/knowledge/src/owlbear_knowledge/refresh.py:415` | backlog |
| 2 | AC-1 | The PASS conclusion still relies on unproven fetch-path equivalence. URL_LIST is proven to use `HttpxContentFetcher` through `_intake.read_url`, but AUTHENTICATED_WEB only calls an injected `self._content_fetcher` and can fail if none is provided. The scoped evidence does not prove the memo's claim that `fetch_method="http"` maps AUTHENTICATED_WEB to the same fetcher. | `.owlbear/research/1653-url-list-handler-equivalence.md:57`; `.owlbear/research/1653-url-list-handler-equivalence.md:61`; `serve/knowledge/src/owlbear_knowledge/refresh.py:223`; `serve/knowledge/src/owlbear_knowledge/intake.py:66`; `serve/knowledge/src/owlbear_knowledge/fetcher.py:19`; `serve/knowledge/src/owlbear_knowledge/fetcher.py:22`; `serve/knowledge/src/owlbear_knowledge/refresh.py:407`; `serve/knowledge/src/owlbear_knowledge/refresh.py:411` | backlog |
| 3 | AC-1 | The comparison matrix still includes a factual mismatch: it labels `source.id` vs `str(source.id)` as a runtime difference, but `KnowledgeSource.id` is already `str`, so the returned `source_id` values are the same. | `.owlbear/research/1653-url-list-handler-equivalence.md:39`; `serve/knowledge/src/owlbear_knowledge/models.py:116`; `serve/knowledge/src/owlbear_knowledge/refresh.py:244`; `serve/knowledge/src/owlbear_knowledge/refresh.py:390` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine the task contract to define whether handler equivalence means identical persisted document/chunk metadata or only equivalent refresh-status behavior, then reissue the research step against that explicit contract. | `.owlbear/research/1653-url-list-handler-equivalence.md`; `.owlbear/kanban/tasks/1653-p1-04-verify-handler-equivalence-for-url-list-retype.md` | Contradiction between persisted metadata/chunk propagation and `chunks are identical` at `.owlbear/research/1653-url-list-handler-equivalence.md:48` and `.owlbear/research/1653-url-list-handler-equivalence.md:64` |
| 2 | architect | Require scoped proof for the AUTHENTICATED_WEB fetcher binding, or explicitly narrow the memo to only the control-flow facts proven in-scope before reissuing a PASS/FAIL task. | `.owlbear/research/1653-url-list-handler-equivalence.md`; `serve/knowledge/src/owlbear_knowledge/refresh.py`; `serve/knowledge/src/owlbear_knowledge/intake.py`; `serve/knowledge/src/owlbear_knowledge/fetcher.py` | PASS claim at `.owlbear/research/1653-url-list-handler-equivalence.md:57` is not established by `serve/knowledge/src/owlbear_knowledge/refresh.py:407` and `serve/knowledge/src/owlbear_knowledge/refresh.py:411` |
| 3 | architect | Remove or restate the nonexistent `source_id` difference so the comparison matrix only lists runtime-relevant differences. | `.owlbear/research/1653-url-list-handler-equivalence.md`; `serve/knowledge/src/owlbear_knowledge/models.py`; `serve/knowledge/src/owlbear_knowledge/refresh.py` | Matrix row at `.owlbear/research/1653-url-list-handler-equivalence.md:39` conflicts with `KnowledgeSource.id` being `str` at `serve/knowledge/src/owlbear_knowledge/models.py:116` |

## Observations
- AC-2 is now satisfied: the memo points to follow-up task #1656 at `.owlbear/research/1653-url-list-handler-equivalence.md:77`, and task #1656 is now in backlog with implementation-scoped AC.
- The prior empty-URL finding appears fixed; both handlers still take the same no-URL failure branch.
- Planning notes still contain a stale `Proof bundle: behavioral` line while the authoritative task field remains `skip`; this is non-blocking but can confuse future review scope.

[[2026-05-18T12:50:34+02:00]]
[[2026-05-18T14:30:00+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Pure research analysis of handler equivalence |
| Interface clarity | PASS (after REFINE) | AC-1 now defines four explicit comparison dimensions; AC-2 defines PASS/FAIL criteria precisely |
| Dependency correctness | PASS | No dependencies; independent research task |
| Module layering | N/A | Research task, no code changes |
| TDD compliance | PASS | Proof bundle: skip (research artifact only) |
| KISS/YAGNI | PASS | Minimal scope — comparison only, retype deferred to follow-up |
| Premise challenge | PASS | Handler equivalence is prerequisite for O3 per parent #1650 brief |
| Pattern consistency | PASS | Research doc in `.owlbear/research/` per convention |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | scope:knowledge only |

### AC Refinement Rationale
Prior AC-1 said \"documenting input handling, URL fetching, chunking, and result aggregation differences\" without defining what counts as equivalence-breaking. This caused two review failures:
- Reviewer found metadata IS persisted to chunks but memo claimed \"chunks are identical\"
- Reviewer found `source_id` str() cast difference cited as real but `KnowledgeSource.id` is already str
- Reviewer found fetch-path claim unproven (no evidence AUTH_WEB uses same fetcher)

Refined AC defines equivalence boundary: metadata differences acceptable if no downstream code branches on them.

### Codebase Evidence
- `select_content_fetcher(\"http\")` → `HttpxContentFetcher()` at server.py:998
- `_intake.read_url` → `HttpxContentFetcher().fetch(url)` at intake.py:66
- `KnowledgeSource.id` is `str` at models.py:116 — str() cast is no-op
- `content_safety.should_wrap` only metadata consumer at ingest.py:442

### Challenge Results
- SKIPPED — proof bundle `skip`

### Proof-Bundle Validation
- Planner assignment: skip
- Final bundle: skip
- Test-writer: SKIP (bundle `skip`)

### Verdict: REFINE → APPROVE
### Action Taken: Refined AC to define equivalence precisely. Advancing to todo.

[[2026-05-18T12:50:40+02:00]]
Architecture Review: REFINE → APPROVE. AC refined to define handler equivalence precisely — four comparison dimensions (fetch-path binding, content delivery, counter math, metadata delta with impact assessment) and explicit PASS/FAIL boundary (metadata differences acceptable iff no downstream code branches on them). Prior two review-cycle failures caused by ambiguous \"differences\" wording now resolved. Proof bundle: skip confirmed. Task tagged `research` — test-writer will pass through.

[[2026-05-18T13:03:24+02:00]]
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Also tagged `research` — non-implementation task.
- Passing through to builder.

[[2026-05-18T13:12:19+02:00]]
## Builder Notes
- Files changed: `.owlbear/research/1653-url-list-handler-equivalence.md`
- Implementation scope: corrected AC-1 evidence narrative without changing runtime code (research-only correction under `proof_bundle: skip`).
- Tests: skipped (`proof_bundle: skip`; non-implementation research task)
- Coverage: not applicable (no source-code changes)
- ruff: not run (no Python source changes)
- Evidence summary:
  - Corrected matrix claim for `source_id`: `source.id` vs `str(source.id)` is equivalent because `KnowledgeSource.id` is already `str`.
  - Reframed fetch-path equivalence to scoped runtime wiring for `_direct_source_config` HTTP sources: `fetch_method="http"` + `select_content_fetcher` + injected fetcher in `refresh_source`, and URL_LIST path via `_intake.read_url`.
  - Updated recommendation to satisfy refined AC boundary: PASS only because (a) fetch binding, (b) content delivery to ingest, and (c) counter math are equivalent, while metadata differences are explicitly persisted but non-branching.
  - AC-2 follow-up requirement remains satisfied: task #1656 exists in backlog.
- Fixes applied for prior review findings:
  1. Removed overclaim that chunk rows are identical; now explicitly states metadata differs and is persisted.
  2. Removed nonexistent runtime difference for `source_id` cast.
  3. Replaced unproven generic fetcher claim with scoped, code-backed binding path.

[[2026-05-18T13:36:48+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: backlog
- Builder evidence reviewed first: builder correctly limited this retry to a research-only correction with one changed file, and direct file checks confirm AC-2 remains satisfied because follow-up task #1656 exists in backlog.
- Review-cycle note: this is the third review cycle on the task, so the remaining blocker routes to backlog per reviewer policy.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1 | The `source_type` downstream-impact cite is still factually inaccurate. The memo says `content_safety.should_wrap()` trusts only `"git"` and `"text"`, but the actual trusted set is `"file"`, `"file_glob"`, and `"text"`. The compared handlers still both wrap, but the supporting proof text is not accurate enough to approve the research artifact as written. | `.owlbear/research/1653-url-list-handler-equivalence.md:50`; `serve/knowledge/src/owlbear_knowledge/content_safety.py:22`; `serve/knowledge/src/owlbear_knowledge/content_safety.py:42`; `serve/knowledge/src/owlbear_knowledge/ingest.py:442` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Reissue the research step with the `source_type` downstream-impact cite corrected to the actual `should_wrap` trusted set, then have the research artifact restated against that precise code fact before another PASS review. | `.owlbear/research/1653-url-list-handler-equivalence.md`; `serve/knowledge/src/owlbear_knowledge/content_safety.py`; `serve/knowledge/src/owlbear_knowledge/ingest.py` | Memo claim at `.owlbear/research/1653-url-list-handler-equivalence.md:50` conflicts with trusted-set logic at `serve/knowledge/src/owlbear_knowledge/content_safety.py:22-42` and its call site at `serve/knowledge/src/owlbear_knowledge/ingest.py:442` |

## Observations
- The refined AC is otherwise substantially covered: fetch binding is supported by `serve/knowledge/src/owlbear_knowledge/ingest.py:130`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:993`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1564`, `serve/knowledge/src/owlbear_knowledge/intake.py:66`, and `serve/knowledge/src/owlbear_knowledge/refresh.py:223` / `serve/knowledge/src/owlbear_knowledge/refresh.py:364`.
- Content delivery and counter math align across the handlers at `serve/knowledge/src/owlbear_knowledge/refresh.py:223-244` and `serve/knowledge/src/owlbear_knowledge/refresh.py:364-390`; `source_id` equivalence is now correctly handled because `KnowledgeSource.id` is `str` at `serve/knowledge/src/owlbear_knowledge/models.py:116`.
- AC-2 remains satisfied: task #1656 is in backlog and still serves as the required follow-up artifact for the retype.

[[2026-05-18T13:47:08+02:00]]
## Architecture Review (cycle 2)
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Pure research analysis of handler equivalence |
| Interface clarity | PASS | AC defines four explicit comparison dimensions with precise PASS/FAIL boundary |
| Dependency correctness | PASS | No dependencies |
| Module layering | N/A | Research task, no code changes |
| TDD compliance | PASS | Proof bundle: skip (research artifact only) |
| KISS/YAGNI | PASS | Minimal scope — comparison only, retype deferred to #1656 |
| Premise challenge | PASS | Handler equivalence is prerequisite for O3 per parent #1650 brief |
| Pattern consistency | PASS | Research doc in `.owlbear/research/` per convention |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | scope:knowledge only |

### Builder Correction Guidance
One factual cite remains incorrect at `.owlbear/research/1653-url-list-handler-equivalence.md` line ~50:
- **Current:** `"git"` and `"text"` are trusted
- **Actual:** `"file"`, `"file_glob"`, and `"text"` are trusted (see `content_safety.py:22` → `_TRUSTED_SOURCE_TYPES`)
- **Impact on conclusion:** None — both `"url"` and `"authenticated_web"` are NOT in the trusted set regardless of which strings are listed. `should_wrap()` returns `True` for both.
- **Required action:** Replace the incorrect string in the metadata persistence impact section. No other changes needed.

### Challenge Results
- SKIPPED — proof bundle `skip`

### Proof-Bundle Validation
- Planner assignment: skip
- Final bundle: skip
- Test-writer: SKIP (bundle `skip`)

### Verdict: APPROVE
### Action Taken: Approved to todo with explicit builder guidance for the remaining cite correction.

[[2026-05-18T13:47:14+02:00]]
Architecture Review: APPROVE. AC already precisely refined from prior cycle — four comparison dimensions with explicit PASS/FAIL boundary. Single remaining reviewer finding is a factual cite error in research doc (says trusted set is "git"/"text" but actual is "file"/"file_glob"/"text"); conclusion is unaffected. Added explicit builder correction guidance. Proof bundle: skip confirmed. Task tagged `research` — test-writer will pass through.

[[2026-05-18T14:01:28+02:00]]
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Tagged `research` — non-implementation task.
- Passing through to builder.

[[2026-05-18T14:16:13+02:00]]
## Builder Notes
- Files changed: `.owlbear/research/1653-url-list-handler-equivalence.md`
- Commit: `5d490dca`
- Implementation scope: corrected the final factual cite in the metadata impact section to match runtime code (`content_safety.should_wrap` trusted set is `file`, `file_glob`, `text`).
- Tests: skipped (`proof_bundle: skip`; research/non-implementation correction)
- Coverage: not applicable (no runtime code changes)
- Ruff: not run (no Python source changes)
- Evidence summary:
  - Research memo now states the correct trusted source-type set from `serve/knowledge/src/owlbear_knowledge/content_safety.py`.
  - Conclusion remains unchanged and scoped: both `url` and `authenticated_web` are untrusted and therefore wrapped.
  - AC-2 follow-up remains satisfied via backlog task `#1656`.
- Fixes applied for prior review finding:
  1. Replaced incorrect trusted-set wording (`git`/`text`) with the actual set (`file`/`file_glob`/`text`).

[[2026-05-18T14:32:23+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1653 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: builder correctly scoped this retry to a research-only correction in `.owlbear/research/1653-url-list-handler-equivalence.md` under `proof_bundle: skip`; no runtime code changed, so direct artifact/code verification was sufficient and no quality-runner rerun was needed.

| AC Line | Code Evidence | Artifact Evidence | Status |
|---|---|---|---|
| AC-1(a) fetch-path | `_direct_source_config()` still creates non-local HTTP sources as `AUTHENTICATED_WEB` with `fetch_method="http"` at `serve/knowledge/src/owlbear_knowledge/ingest.py:112-130`; `refresh_source` selects `select_content_fetcher(source.fetch_method)` at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1574` and injects it at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1579`; `select_content_fetcher("http")` returns `HttpxContentFetcher()` at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1003`; URL_LIST path reads via `_intake.read_url(url)` at `serve/knowledge/src/owlbear_knowledge/refresh.py:223`, which calls `HttpxContentFetcher().fetch(url)` at `serve/knowledge/src/owlbear_knowledge/intake.py:55-60`; the fetcher returns `response.text` at `serve/knowledge/src/owlbear_knowledge/fetcher.py:13-23`; AUTH_WEB path reads via `self._content_fetcher.fetch(url)` at `serve/knowledge/src/owlbear_knowledge/refresh.py:411`. | `.owlbear/research/1653-url-list-handler-equivalence.md:31`; `.owlbear/research/1653-url-list-handler-equivalence.md:55-65` | PASS |
| AC-1(b) content delivery | Both handlers start from `_configured_urls(source)` at `serve/knowledge/src/owlbear_knowledge/refresh.py:31`, called from URL_LIST at `serve/knowledge/src/owlbear_knowledge/refresh.py:204` and AUTH_WEB at `serve/knowledge/src/owlbear_knowledge/refresh.py:345`; URL_LIST passes the fetched intake to `self._pipeline.ingest(..., scope=source.scope, source_id=source.id)` at `serve/knowledge/src/owlbear_knowledge/refresh.py:224-227`; AUTH_WEB builds `ingest_call = self._pipeline.ingest(..., scope=source.scope, source_id=source.id)` at `serve/knowledge/src/owlbear_knowledge/refresh.py:365-368`; AUTH_WEB intake metadata is created at `serve/knowledge/src/owlbear_knowledge/refresh.py:412-415`. | `.owlbear/research/1653-url-list-handler-equivalence.md:31-32`; `.owlbear/research/1653-url-list-handler-equivalence.md:55-65` | PASS |
| AC-1(c) counter math / RefreshResult shape | URL_LIST initializes the same counters at `serve/knowledge/src/owlbear_knowledge/refresh.py:205`, uses `_record_ingest_outcome(...)` at `serve/knowledge/src/owlbear_knowledge/refresh.py:229`, returns the same no-URL error shape at `serve/knowledge/src/owlbear_knowledge/refresh.py:210-216`, and returns `RefreshResult(... errors=errors, warnings=warnings)` at `serve/knowledge/src/owlbear_knowledge/refresh.py:243-250`; AUTH_WEB mirrors that shape with counter init at `serve/knowledge/src/owlbear_knowledge/refresh.py:346`, no-URL error at `serve/knowledge/src/owlbear_knowledge/refresh.py:351-357`, `_record_ingest_outcome(...)` at `serve/knowledge/src/owlbear_knowledge/refresh.py:375`, and final `RefreshResult(... errors=errors, warnings=warnings)` at `serve/knowledge/src/owlbear_knowledge/refresh.py:389-396`. The `source_id` cast difference is a no-op because `KnowledgeSource.id` is already `str` at `serve/knowledge/src/owlbear_knowledge/models.py:116`. | `.owlbear/research/1653-url-list-handler-equivalence.md:38-44` | PASS |
| AC-1(d) metadata delta with downstream-impact cite | The memo now correctly lists `source_type` and `fetched_at` as the differing intake metadata fields at `.owlbear/research/1653-url-list-handler-equivalence.md:33-36`. Direct repo search of `serve/**` found the only runtime consumer of intake metadata `source_type` at `serve/knowledge/src/owlbear_knowledge/ingest.py:442`, which delegates to `should_wrap()` using the trusted set at `serve/knowledge/src/owlbear_knowledge/content_safety.py:22-42`; both `"url"` and `"authenticated_web"` therefore wrap identically. Direct repo search of `serve/**` found no runtime consumer of `fetched_at`; occurrences are only intake writes/defaults (`serve/knowledge/src/owlbear_knowledge/intake.py:49`, `serve/knowledge/src/owlbear_knowledge/intake.py:72`, `serve/knowledge/src/owlbear_knowledge/intake.py:92`, `serve/knowledge/src/owlbear_knowledge/ingest.py:332` in `ingest_text`, not the handler path under review). Safety check: no injection or credential-handling regression is introduced by this research-only artifact, and the metadata reasoning does not expose a new security branch. | `.owlbear/research/1653-url-list-handler-equivalence.md:48-53`; `.owlbear/research/1653-url-list-handler-equivalence.md:72` | PASS |
| AC-2 PASS/FAIL conclusion + follow-up | The memo now gives the scoped PASS conclusion at `.owlbear/research/1653-url-list-handler-equivalence.md:68-75`, and the required implementation follow-up exists as backlog task `#1656` (`show_task(1656): status=backlog`). | `.owlbear/research/1653-url-list-handler-equivalence.md:84` | PASS |

## Observations
- No blocking findings remain after the final trusted-set wording correction.
- Proof sufficiency is acceptable for a `skip` bundle: this review validated the memo against current codepaths rather than requiring tests for a research-only task.
- Reviewer pitfall noted during verification: `serve/knowledge/src/owlbear_knowledge/ingest.py:300-332` (`ingest_text`) backfills `fetched_at`, but the handler comparison under review uses `ingest(IntakeResult)` at `serve/knowledge/src/owlbear_knowledge/ingest.py:368-485`, which persists `intake.metadata` directly; that distinction does not affect the current verdict but is easy to misread during future reviews.
