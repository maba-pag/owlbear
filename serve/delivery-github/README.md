# owlbear-delivery-github — GitHub Publication Adapter

Fixed-operation GitHub publication adapters for Delivery. The package provides a GitHub CLI transport and a deterministic in-memory implementation of the transport-free provider contracts owned by `owlbear-delivery`; it issues no generic provider requests. Its only merge operation is one exact-head direct merge request sent through a release-gated launcher; it never enables auto-merge, updates a PR branch, enqueues into a merge queue or bypasses rules.

**Use this guide when:** you need to change or test the GitHub pull-request publication boundary used
by Delivery.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

---

## Launch / Usage

There is no standalone launch command. Use `GitHubCliPublicationProvider` in application composition and `InMemoryPublicationProvider` in tests that need deterministic repository and pull-request state.

```python
from owlbear_delivery_github import GitHubCliPublicationProvider

provider = GitHubCliPublicationProvider(timeout_seconds=30)
repository = provider.read_repository("example/project")
```

The CLI adapter runs only code-owned `gh api` argument vectors for repository and pull-request reads, draft PR creation, generated metadata updates, draft/ready transitions, merge-setting and merge-evidence reads, and the merge request described below.

### Pull-request read contract

The adapter sends GitHub REST API version `2026-03-10`. That version removes `merge_commit_sha` from pull-request responses, so the field is optional in the REST payload. An open pull request with the field omitted is a normal open `PublicationPullRequest` with no merge OID, and the provider does not issue a merged-evidence GraphQL read.

For a merged public read, `read_pull_request` first treats REST as publication metadata and then issues the fixed named GraphQL query `ReadMergedPullRequest`. The query enriches the result from `mergeCommit.oid` and `mergedAt`. `find_pull_request` lists only open pull requests, so merged or closed pull requests from an earlier delivery on the same Change branch never block or bind a new draft publication; receipt-bound reads by number still observe closed and merged state. The GraphQL fields are canonical merged evidence, while REST remains the publication metadata source.

Before returning a merged `PublicationPullRequest`, the provider requires all of these cross-source checks:

- The repository identity matches case-insensitively and the pull-request number matches.
- REST `head.sha` equals GraphQL `headRefOid`, and REST `base.ref` equals GraphQL `baseRefName`.
- GraphQL reports `merged: true`, provides a lowercase 40-character `mergeCommit.oid`, and provides a timezone-aware `mergedAt` timestamp.
- When REST still supplies `merge_commit_sha` or `merged_at`, each value agrees with the corresponding GraphQL evidence.

Create and update response parsing, including their pre- and post-write read fences, is REST-only and never issues `ReadMergedPullRequest`. Draft-state transitions use REST read fences too, but their existing named `ConvertPullRequestToDraft` or `MarkPullRequestReadyForReview` GraphQL mutation remains separate from the merged-evidence read.

Missing GraphQL repository or pull request data produces a typed, non-retryable `NOT_FOUND`. Null, malformed, or contradictory merged evidence produces a typed, retry-safe `INVALID_RESPONSE`. Read-side transport and nonzero-command failures retain their typed mappings, including `UNAVAILABLE`, `TIMEOUT`, `RATE_LIMITED`, `AUTHENTICATION_REQUIRED`, `NOT_FOUND`, and `CONFLICT` as applicable. Errors redact raw GitHub payloads, and a failed merged read returns no partial `PublicationPullRequest`.

```python
from owlbear_delivery import PublicationRepository
from owlbear_delivery_github import InMemoryPublicationProvider

provider = InMemoryPublicationProvider()
provider.add_repository(PublicationRepository(repository="example/project", default_branch="main"))
```

The public provider models and `PublicationProvider` protocol are exported by `owlbear-delivery`.

### Merge transport contract

Both adapters also implement `PublicationMergeProvider`, a separate protocol imported from `owlbear_delivery.publication_provider`, so publication-only fakes stay valid. It reads merge settings (allowed methods, viewer push permission, target rule types, merge-queue and strict up-to-date rules), branch heads, merge evidence (head, base, stack, merge commit and its first two parents) and async merge request results, and sends one merge request.

- `request_merge` sends `PUT …/pulls/{n}/merge-async` with the canonical frozen body from `merge_request_body`: `sha` (the approved head), `merge_method`, `merge_action: "direct_merge"` and `bypass_rules: false`. The caller writes that body to a read-only file first; a file whose bytes differ is refused before any process starts.
- `effect_launcher.py` runs in a new session and blocks on a fixed-size release token. The provider calls `release(group_id, start_time)` after spawn and writes the token only after it returns; a raising `release` closes the pipe and its exception propagates unchanged. A spawn failure or an unreadable launcher start time raises `UNAVAILABLE` with `retry_safe=True` before `release` runs, because nothing was sent. The launcher re-hashes the file, replaces stdin with `/dev/null` and only then `exec`s `gh api … --input <file>`, so a dead controller can never send an empty or partial body.
- Responses map to `pending` (UUID and the provider-reported options; a `409` adopts the existing request), `merged`, `refused` (`400`, `403`, `405`, `422`, a `failed` result or an `enqueued` result) or, for a readback `404`, `unavailable`. The status comes from either `gh` status line, `gh: <message> (HTTP <code>)` or `gh: HTTP <code>` when the body has no top-level message. A `409` without complete options, a timeout, any other status or an unreadable write response raises `RESPONSE_UNKNOWN` with `retry_safe=False`.
- `execution_scope_enforced` is always `false` for GitHub: no merge API fences the base or the stack.
- Only Delivery's merge approval owner calls `request_merge`, once per user approval in Cockpit; agents never merge through `gh` directly.

The in-memory adapter accepts merge requests as pending and runs them only through `execute_pending_merges`; its fault fields model lost responses, complete refusals, foreign pending requests, expiry, manual merges, target advances, retargets and stack joins.

## Configuration

`GitHubCliPublicationProvider` requires an authenticated `gh` executable on `PATH` and accepts a positive per-operation timeout in seconds. It reads no token or credential from Delivery configuration. The in-memory adapter has no environment variables, files, credentials, or command-line flags; callers register repository state explicitly.

## Dependencies

| Package | Purpose |
| --- | --- |
| `owlbear-delivery` | Owns the transport-free publication models and provider protocol |
| `pydantic` | Validates strict provider request and response models |

The GitHub CLI is an external runtime dependency for `GitHubCliPublicationProvider`; it is not required for the in-memory adapter. The release-gated launcher uses only the standard library and the running Python interpreter. Its EOF falsifier (`tests/test_effect_launcher.py`) requires a real `gh` and points it at a local HTTP recorder only.
