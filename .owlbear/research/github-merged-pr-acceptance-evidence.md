# GitHub Merged-PR Acceptance Evidence

> **Owning task:** User-directed implementation plan; no Delivery task ID admitted
> **Date:** 2026-08-22
> **Status:** Ready for stepwise implementation; this document makes no product changes
> **Question:** How should Delivery complete a merged pull request when GitHub REST API version `2026-03-10` removes `merge_commit_sha` from pull-request responses?

## 1. Outcome And Boundary

### 1.1 Goal

Make the existing Delivery acceptance path complete a user-merged GitHub pull request without
manual input, local-target inference, branch restoration, or weakening the completion contract.

The provider must return the existing transport-free `PublicationPullRequest` contract with:

- the exact PR number, node identity, head SHA, and base branch;
- `merged=True` and `state="closed"`;
- the exact post-merge commit SHA;
- a timezone-aware merge timestamp.

Once that object is available, the existing `PortfolioApplication.observe_acceptance()` path should
create the normal receipt-backed completion record. The core Delivery acceptance model must remain
the authority for completion.

### 1.2 Definition of done

1. An open PR response under REST API version `2026-03-10` remains readable when it omits
   `merge_commit_sha`.
2. A merged PR response under that same REST version is enriched through one typed GraphQL read of
   `PullRequest.mergeCommit.oid` and `mergedAt`.
3. The enrichment validates repository, PR number, head, base, merged state, commit shape, and
   timestamp before returning the provider contract.
4. A missing, null, malformed, or contradictory merge object fails closed with a typed provider
   error and never creates a completion receipt.
5. No caller supplies a merge SHA. No provider code derives one from local `dev`, a merge base, or
   the deleted source branch.
6. PR `#194` can be observed through the normal acceptance operation and reaches
   `acceptance-observed` with a completion-history record after the fixed provider is deployed and
   Cockpit is restarted.

### 1.3 Non-goals

- Do not restore the deleted source branch. Repository setting `delete_branch_on_merge=true` makes
  deletion expected cleanup; GitHub retains the PR and its immutable head identity.
- Do not change the already-merged PR or rewrite `dev`.
- Do not downgrade the Delivery core requirement for an exact accepted merge commit.
- Do not accept a user-pasted SHA or infer a SHA from local Git state.
- Do not make the provider merge pull requests. Acceptance remains observation-only.
- Do not redesign Cockpit polling, publication checks, or the generic dev-tunnel gateway.
- Do not turn a provider/API compatibility fix into a broad Delivery or Cockpit refactor.

## 2. Proven Incident

### 2.1 Facts from PR `#194`

| Fact | Observed value | Meaning |
|---|---|---|
| Finalized PR head | `7df45c291d04dc10413d844425f8ec0298d865d6` | The exact reviewed Change commit |
| GitHub merge commit | `c69a8c401bd2b8a71bad1a14d560f28541d0b313` | Actual merge commit on `dev`; locally confirmed as a two-parent merge commit |
| PR state | closed, merged, non-draft | GitHub merge succeeded |
| Source branch | auto-deleted | Expected repository cleanup; not a Delivery corruption |
| Delivery state | awaiting-merge, no completion record | Acceptance observation has not produced valid merged evidence |

The local `origin/dev` merge commit has parents `39c2b69...` and
`7df45c291d04dc10413d844425f8ec0298d865d6`. The user did not omit evidence; the repository contains
the merge commit.

### 2.2 REST API version contradiction

The provider sets `_API_VERSION = "2026-03-10"` in
`serve/delivery-github/src/owlbear_delivery_github/github.py` and sends that header on REST calls.
An A/B request against the same PR and endpoint showed:

| Request | `merge_commit_sha` |
|---|---|
| No API-version header | `c69a8c401bd2b8a71bad1a14d560f28541d0b313` |
| `X-GitHub-Api-Version: 2026-03-10` | field absent |

The only response-key differences were removal of `assignee` and `merge_commit_sha`. GitHub's
official breaking-change record explicitly says that `merge_commit_sha` is removed from pull
request payloads, including `GET /repos/{owner}/{repo}/pulls/{pull_number}`.

Therefore the provider's REST model was incompatible with the API version it deliberately pinned.

### 2.3 Existing implementation boundary

The provider currently maps the REST response through `_PullResponse` and constructs the core
`PublicationPullRequest`. The core model intentionally rejects a merged PR without
`merge_commit_sha`, and `CompletionEvidence` requires a 40-character accepted merge commit.

The existing local change that makes `merge_commit_sha` default to `None` is necessary for an open
PR response whose removed field is irrelevant, but it is not the acceptance fix. For a merged PR it
only moves the failure from REST parsing to the core merged-state validator. Keep the nullable open
PR compatibility, but add real merged-evidence retrieval.

### 2.4 Candidate evidence source was tested

The exact GraphQL query below was executed against PR `#194` and returned the actual merge commit
under the same REST API-version header:

```graphql
query ReadMergedPullRequest($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    nameWithOwner
    pullRequest(number: $number) {
      number
      headRefOid
      baseRefName
      merged
      mergedAt
      mergeCommit { oid }
    }
  }
}
```

Observed for PR `#194`:

```text
number: 194
headRefOid: 7df45c291d04dc10413d844425f8ec0298d865d6
baseRefName: dev
merged: true
mergedAt: 2026-08-22T20:57:56Z
mergeCommit.oid: c69a8c401bd2b8a71bad1a14d560f28541d0b313
```

GitHub's GraphQL schema describes `mergeCommit` as “The commit that was created when this pull
request was merged.” Its `headRefOid` description explicitly remains available even if the head
ref was deleted. This makes the query suitable for the post-merge, auto-deleted-branch state.

## 3. Sources Studied

| Source | Relevant fact | Limit |
|---|---|---|
| [GitHub REST API breaking changes](https://docs.github.com/en/rest/about-the-rest-api/breaking-changes) | API version `2026-03-10` removes `merge_commit_sha` from pull-request responses; GitHub says integrations must adapt when selecting a new version | Documents the removal, not OwlBear's provider contract |
| [GitHub REST get a pull request](https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request) | Older response semantics describe the post-merge SHA; the current versioned response no longer carries that field | REST `/merge` is only a merged-status check and returns an empty 204 body |
| [GitHub GraphQL PullRequest object](https://docs.github.com/en/graphql/reference/objects#pullrequest) | `mergeCommit`, `mergedAt`, `headRefOid`, and `baseRefName` provide the exact merged identity; `headRefOid` survives head-ref deletion | Schema reference does not replace runtime identity validation |
| `serve/delivery-github/src/owlbear_delivery_github/github.py` | Owns `GitHubCliPublicationProvider`, fixed `gh api` transport, REST parsing, and existing GraphQL read patterns | Current implementation before the planned enrichment; its call graph includes public reads used by publication and write-fence paths |
| `serve/delivery/src/owlbear_delivery/publication_provider.py` | Owns the stable provider contract and rejects merged evidence without an exact merge commit | Core contract is intentionally fail-closed |
| `serve/delivery/src/owlbear_delivery/portfolio_application.py` | `observe_acceptance()` requires exact finalized/ready authority and creates completion evidence from provider observation | Does not need a caller-supplied SHA |
| `serve/delivery/src/owlbear_delivery/delivery_runtime.py` | Merged latch and completion receipt retain the exact provider-observed merge tuple | A missing merge commit cannot be safely substituted |
| `serve/delivery-github/tests/test_github_provider.py` | Existing runner fixtures cover REST reads, GraphQL checks, draft transitions, and typed failures | Existing merged fixtures still model the removed REST field |
| `serve/delivery/tests/test_portfolio_application.py` | Existing tests prove receipt-backed acceptance with an exact merged `PublicationPullRequest` | Does not exercise GitHub's versioned wire response |
| `serve/delivery-github/README.md` | Documents the adapter's fixed-operation and `gh api` boundary | Must state the versioned REST plus GraphQL merged-evidence split after implementation |

## 4. Contract And Design Decisions

### 4.1 Keep the public core contract unchanged

`PublicationProvider.read_pull_request()` continues to return `PublicationPullRequest`. The
transport adapter absorbs GitHub's REST/GraphQL split. No GraphQL-specific field or API-version
detail crosses into `owlbear-delivery`.

### 4.2 Enrich merged reads through an explicit call graph

Use this provider flow:

1. Run the existing REST PR read with the pinned headers.
2. Parse the REST response into a private `_PullResponse` without constructing a merged
  `PublicationPullRequest`; `merge_commit_sha` is optional at this wire layer.
3. For an open or unmerged PR, construct and return the REST-derived provider object. No GraphQL
  request is made.
4. For `merged=true` in public `read_pull_request()`, run one typed GraphQL query using the repository
  owner/name and PR number, regardless of whether the legacy REST field is present. GraphQL is the
  canonical merged-evidence source and a present REST value is a cross-check.
5. Use GraphQL `mergeCommit.oid` and `mergedAt` to complete merged evidence, while retaining REST
  title, body, draft, state, node ID, head branch, and other publication fields.
6. Return one `PublicationPullRequest` only after all cross-source checks pass.

The private call-site routing is part of the implementation contract. `find_pull_request()` may use
public `read_pull_request()` for a matched PR because it must return the public provider model and
therefore obtains merged evidence for a merged match. `_require_open_head()` must instead use a
private `_read_open_pull_request()` built on the REST-only stage, reject a non-open or merged PR with
the existing write-fence conflict, and avoid GraphQL before a write. The post-mutation draft-state
read uses the same REST-only open path. Create and update response parsing remains REST-only because
those responses are expected to be open. This prevents a merged-evidence network failure from
changing an open-write-fence conflict while preserving the public provider contract.

This keeps the normal open-PR path cheap, preserves the existing fixed-operation adapter, and makes
the additional merged read explicit in code and tests.

### 4.3 Required cross-source validation

The provider must reject the response when any of these checks fail:

- GraphQL repository `nameWithOwner` does not equal the requested repository.
- GraphQL PR is absent or its number differs from the REST PR number.
- GraphQL `headRefOid` differs from REST `head.sha`.
- GraphQL `baseRefName` differs from REST `base.ref`.
- GraphQL `merged` is not true while REST reports merged.
- `mergeCommit` is null or its `oid` is not exactly 40 lowercase hexadecimal characters.
- GraphQL `mergedAt` is absent, invalid, or timezone-naive.
- REST `merged_at` is present but disagrees with GraphQL `mergedAt` after normalization.
- REST `merge_commit_sha` is present but disagrees with GraphQL `mergeCommit.oid`.

For a read operation, malformed or incomplete GraphQL evidence is a retry-safe typed
`INVALID_RESPONSE`; a missing repository or PR is typed `NOT_FOUND`. Neither result may create a
completion record. Preserve the existing provider error redaction and do not expose raw GraphQL
payloads through Cockpit.

### 4.4 Merge methods

The repository currently allows merge commits, squash merges, and rebase merges. The provider must
not derive behavior from an unobserved merge method. The contract is method-neutral: when GitHub
reports `merged=true`, `mergeCommit.oid` must be present and exact. Add fixtures representing:

- a merge commit whose OID differs from the PR head;
- a squash result whose OID differs from the PR head;
- a rebase result with the OID returned by GraphQL.

Before claiming full merge-method coverage, verify the third fixture against GitHub's actual
GraphQL behavior or an existing merged PR. If GitHub ever returns `mergeCommit: null` for an
enabled merge method, stop the implementation claim at that boundary and open a separate evidence
design question. Do not silently use the PR head or target head as a substitute.

### 4.5 No REST downgrade as the primary design

Do not change all calls back to `2022-11-28`. That would make the old field appear again, but it
reintroduces a deprecated response contract and leaves the adapter dependent on a field GitHub has
explicitly removed from the selected current version. A narrowly scoped old-version header is an
emergency diagnostic only, not the target implementation.

## 5. Stepwise Implementation Plan

Each step has an explicit file boundary, proof, and stop condition. Keep the provider change in the
`delivery-github` domain. Do not mix it with the unrelated stale-admission Cockpit work.

### Step 0 - Freeze the baseline and remove ambiguity

**Files:** no product edits; provider tests may receive only a baseline fixture adjustment if
needed.

**Actions:**

- Confirm PR `#194` remains merged and its source branch remains deleted through bounded GitHub
  reads; do not use a raw full-response terminal dump.
- Confirm Delivery still has finalization and ready authority but no completion record.
- Run the focused provider suite and record the current failure for a versioned merged response
  with no `merge_commit_sha`.
- Keep the existing open-PR nullable-field test, but label it as parser compatibility rather than
  acceptance proof.
- Record the exact current provider and core error codes before editing.

**Proof gate:** A fresh process can reproduce the missing-REST-field condition while the merge
commit remains visible through the bounded GraphQL query. If the PR or local Delivery state has
changed, stop and re-read authority before continuing.

### Step 1 - Add typed GraphQL merged-evidence enrichment

**Files:**

- `serve/delivery-github/src/owlbear_delivery_github/github.py`

**Implementation:**

- Add one named query constant such as `READ_MERGED_PULL_REQUEST` with only
  `nameWithOwner`, `number`, `headRefOid`, `baseRefName`, `merged`, `mergedAt`, and
  `mergeCommit { oid }`.
- Add strict Pydantic response models beside the existing check-query models. Use aliases for
  `nameWithOwner`, `headRefOid`, `baseRefName`, `mergedAt`, and `mergeCommit` as appropriate.
- Add a private provider helper that splits the configured repository, invokes the existing
  `_graphql_query()` read path, validates repository/PR presence, parses `mergedAt` through the
  existing timezone-aware timestamp helper, and returns the exact merge OID.
- Parse the REST wire object before core-model construction, call the merged-evidence helper for
  every public `read_pull_request()` result with `merged=true`, and keep `_read_open_pull_request()`
  on the REST-only stage for write fences.
- Compare the GraphQL identity to the REST response before constructing the public provider model.
- Pass GraphQL `mergedAt`, rather than a missing REST timestamp, into the public provider model;
  compare REST `merged_at` when it is present.
- Compare a present REST `merge_commit_sha` to GraphQL `mergeCommit.oid`; never silently select one
  when they disagree.
- Keep all transport operations fixed and read-only. Do not add a generic request method, a merge
  operation, or user-configurable query text.

**Proof gate:** The provider returns a `PublicationPullRequest` for the real PR-194 wire shape with
`merge_commit_sha=c69a8c401bd2...`, and open PR reads do not issue the GraphQL enrichment call.

### Step 2 - Replace unrealistic wire fixtures with discriminating provider tests

**Files:**

- `serve/delivery-github/tests/test_github_provider.py`

**Tests to add or change:**

- REST open PR without `merge_commit_sha` remains accepted and returns `None` for that field.
- REST merged PR without `merge_commit_sha` followed by valid GraphQL evidence returns the exact
  GraphQL OID and merged timestamp.
- The test asserts the exact GraphQL operation vector, operation name, variables, and selected
  query fields; it does not assert a generic substring alone.
- GraphQL repository missing and PR missing map to `NOT_FOUND` with `retry_safe=False`.
- GraphQL errors, malformed data, null `mergeCommit`, invalid OID, wrong number, wrong head, wrong
  base, merged-state disagreement, and timestamp disagreement map to typed retry-safe invalid
  responses.
- `find_pull_request()` uses the public read contract for a merged match; `_require_open_head()` and
  post-mutation draft-state reads use REST-only open-state parsing and preserve the existing
  non-open conflict before any merged-evidence query.
- A merge/squash/rebase fixture matrix proves the provider never assumes the merge OID equals the
  PR head.
- Existing open-PR, draft-state, check-observation, and transport-failure tests continue to pass.

**Proof gate:** `uv run pytest serve/delivery-github/tests/test_github_provider.py -q --tb=short`
passes with the full focused provider count, and `uv run ruff check` passes for the two provider
files. No test prints raw external JSON.

### Step 3 - Prove the core acceptance handoff without changing core authority

**Files:**

- Prefer existing `serve/delivery/tests/test_portfolio_application.py` acceptance coverage.
- Add a focused adapter-to-contract integration test only if the provider fixture cannot already
  prove the returned `PublicationPullRequest` shape at the public boundary.

**Checks:**

- Confirm the existing `observe_acceptance()` path consumes the provider's enriched object without
  a new caller parameter or core-model change.
- Confirm completion evidence stores the GraphQL OID, not the finalized PR head.
- Confirm replay returns the same completion receipt without another provider write or duplicate
  completion history.
- Confirm a null or contradictory GraphQL merge object leaves the Change incomplete and does not
  create a false success.

**Proof gate:** Focused Delivery acceptance tests pass; no `PublicationPullRequest` or
`CompletionEvidence` authority was weakened.

### Step 4 - Deploy the provider fix through its own Delivery Change

**Scope:** `delivery-github` implementation and tests only.

**Order:**

1. Create or resume a dedicated Delivery Change for the provider compatibility fix.
2. Admit only the `delivery-github` maintained surfaces and publish the bounded task plan.
3. Build the implementation in the managed Change worktree.
4. Commit the provider source and provider tests together when their fixture contract must match.
5. Run focused provider and acceptance proofs, obtain independent exact-commit review, and
   finalize that Change.
6. Publish the checkpoint, mark its PR ready, and merge it through the normal user-owned GitHub
   flow.
7. Restart Cockpit/Delivery so the long-lived process loads the new provider code. Do not restart
   VS Code and do not alter the already-merged PR `#194`.

**Proof gate:** A fresh Cockpit process serves the provider version containing the GraphQL
enrichment. Verify this from a compact health/source check, not by dumping process memory or raw
GitHub responses.

### Step 5 - Recover PR `#194` through normal acceptance observation

**Actions after Step 4:**

- Refresh Cockpit and open the existing Change publication detail.
- Click **Check GitHub acceptance** once, or invoke the equivalent exact Delivery observation
  operation once. The user supplies no SHA.
- The provider reads PR `#194` by its persisted publication identity, enriches the merged response,
  and returns `c69a8c401bd2...` as provider evidence.
- Delivery validates the finalized head, ready receipt, PR identity, target branch, merged state,
  merge commit, and merge time, then writes the completion receipt.

**Expected result:**

- publication phase: `acceptance-observed`;
- `accepted_merge_commit`: `c69a8c401bd2b8a71bad1a14d560f28541d0b313`;
- completion history contains exactly one record for the Change;
- a replay is idempotent;
- source branch remains deleted;
- no Change attention remains.

**Failure handling:** If the GraphQL provider returns incomplete or contradictory evidence, leave
the Change incomplete and report the typed provider diagnostic. Do not enter the SHA manually, use
the local `origin/dev` merge commit as an unverified substitute, restore the deleted branch, or
retry a mutation that is not required.

### Step 6 - Verify the Cockpit/tunnel error boundary separately

This is a diagnostic follow-up, not part of the merge-evidence implementation unless reproduced
after Step 5:

- Compare the local Cockpit response on `127.0.0.1:8420` with the dev-tunnel response using a small
  status/code summary only.
- A successful fixed acceptance call must return the normal completion response locally and
  through the tunnel.
- If local Cockpit returns a typed 502 while the tunnel returns 504, open a separate Cockpit/tunnel
  transport issue. Do not obscure the provider diagnosis by changing all errors to 504.
- Preserve the existing safe rule: never print full `gh api` payloads or large GitHub file lists in
  the terminal. Use bounded MCP reads or compact provider summaries.

### Step 7 - Update adapter documentation and source attribution

**Files:**

- `serve/delivery-github/README.md`
- `.owlbear/sources/overview.md`

Document that REST API version `2026-03-10` intentionally omits `merge_commit_sha`, that open PR
reads use the REST response directly, and that merged acceptance evidence uses a typed GraphQL
`mergeCommit.oid` read. Document the fail-closed behavior for null or mismatched merge evidence.

## 6. Alternatives And Decisions

| Option | Evidence | Decision |
|---|---|---|
| GraphQL `PullRequest.mergeCommit.oid` enrichment | Live query returned PR-194's exact `c69a8c4...` under the pinned environment; schema describes it as the commit created by the merge | **Select** |
| Downgrade all REST calls to `2022-11-28` | Restores the removed field today, but depends on a deprecated response and changes every REST operation's contract | Reject as primary; emergency diagnostic only |
| Use REST `GET /pulls/{number}/merge` | Live endpoint returns 204 with an empty body; it proves merged status but supplies no SHA | Reject |
| Derive from local `origin/dev` or merge base | PR-194 happens to have local merge commit `c69a8c4...`, but local target state is not provider acceptance evidence and can advance | Reject |
| Relax `PublicationPullRequest`/`CompletionEvidence` | Would permit a completion record without the exact accepted commit and break the evidence digest contract | Reject |
| Ask the user for the SHA | Violates observation-only acceptance and creates an unverified manual authority path | Reject |

## 7. Proof Matrix

| Boundary | Proof | Required result |
|---|---|---|
| REST open response | Provider fixture omits `merge_commit_sha` while PR is open | Parses; no GraphQL enrichment; merge SHA remains `None` |
| REST merged response | Provider fixture omits `merge_commit_sha` and supplies valid GraphQL evidence | Returns exact GraphQL OID and timestamp |
| GraphQL identity | Wrong repository, number, head, or base | Typed failure; no provider model returned |
| GraphQL evidence | Null/malformed `mergeCommit`, invalid OID, bad timestamp, or disagreement | Retry-safe typed invalid response; no completion |
| Merge methods | Merge, squash, and rebase-shaped evidence fixtures | OID is accepted independently of PR head; no method-specific guess |
| Core handoff | Existing `observe_acceptance()` tests | Completion stores exact merge OID and replays idempotently |
| Existing PR | Fresh-process PR-194 acceptance observation | Change reaches `acceptance-observed`; one completion record |
| Branch deletion | Acceptance after GitHub auto-deletes source branch | Succeeds from persisted PR identity; no branch restoration |
| HTTP boundary | Local Cockpit and tunnel compact status checks | Both expose successful completion after deployment |
| Regression | Provider tests, Delivery acceptance tests, domain-routed suite, Ruff | All pass; no unrelated paths included |

## 8. Commit And Delivery Boundaries

1. **Provider contract implementation:** GraphQL query, typed response models, enrichment, and
   provider tests in `serve/delivery-github/`.
2. **Core acceptance proof only if needed:** a narrowly scoped Delivery test; no core contract
   relaxation.
3. **Adapter documentation:** README and source attribution, separate from runtime behavior when
   practical.
4. **Operational recovery:** no code commit; execute only after the provider Change is merged and
   Cockpit is restarted.

Do not put Cockpit UI changes, stale-admission reconciliation, MCP tool expansion, target sync, or
manual completion repair into the provider Change. If Step 6 proves a real tunnel/API presentation
bug after the provider fix, create a separate Cockpit task with its own evidence.

## 9. Completion Checklist

### Before implementation

- [ ] Preserve the current dirty workspace and do not stage unrelated paths.
- [ ] Confirm the provider fix is being developed in a dedicated `delivery-github` Change.
- [ ] Reproduce the versioned REST omission and the valid GraphQL result with compact output.
- [ ] Verify the current PR-194 Delivery authority has not changed.

### Before declaring the fix complete

- [ ] `_PullResponse` accepts the removed field being absent without treating a merged PR as valid
  until GraphQL enrichment succeeds.
- [ ] GraphQL response models are strict and identity checks are explicit.
- [ ] Null/malformed/mismatched merge evidence fails closed.
- [ ] Provider tests cover open, merge, squash, and rebase-shaped cases.
- [ ] Existing Delivery acceptance tests still require an exact merge commit.
- [ ] PR-194 completes through the normal observation operation without manual data.
- [ ] Completion replay is idempotent and branch deletion remains untouched.
- [ ] The provider README and source ledger explain the REST/GraphQL boundary.
- [ ] Focused and domain-routed proofs pass on the exact deployed commit.

## 10. Recommendation, Confidence, And Limits

**Recommendation:** Implement Steps 0-5 in order. Treat GraphQL enrichment as the selected fix
because it is live-verified, schema-grounded, compatible with the existing fixed-operation
provider, and preserves the core evidence contract. Run Step 6 only if the fixed acceptance path
still shows a local-versus-tunnel discrepancy.

**Confidence:** High that the root cause is the intentional REST field removal under API version
`2026-03-10`; high that GraphQL `mergeCommit.oid` returns the required evidence for PR-194; medium
until provider fixtures or existing PR evidence cover all three enabled merge methods.

**Limits:** The plan does not claim that a null GraphQL `mergeCommit` can be repaired without a
separate authoritative source. Such a response remains a deliberate evidence failure. It also
does not claim that the earlier publication-check 502 and dev-tunnel 504 share one cause; those
must remain separate observations.
