# owlbear-delivery-github — GitHub Publication Adapter

Fixed-operation GitHub publication adapters for Delivery. The package provides a GitHub CLI transport and a deterministic in-memory implementation of the transport-free provider contract owned by `owlbear-delivery`; it cannot merge pull requests or issue generic provider requests.

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

The CLI adapter runs only code-owned `gh api` argument vectors for repository and pull-request reads, draft PR creation, generated metadata updates, and draft/ready transitions.

### Pull-request read contract

The adapter sends GitHub REST API version `2026-03-10`. That version removes `merge_commit_sha` from pull-request responses, so the field is optional in the REST payload. An open pull request with the field omitted is a normal open `PublicationPullRequest` with no merge OID, and the provider does not issue a merged-evidence GraphQL read.

For a merged public read, `read_pull_request` first treats REST as publication metadata and then issues the fixed named GraphQL query `ReadMergedPullRequest`. The query enriches the result from `mergeCommit.oid` and `mergedAt`; `find_pull_request` results that reach `read_pull_request` receive the same enrichment. The GraphQL fields are canonical merged evidence, while REST remains the publication metadata source.

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

## Configuration

`GitHubCliPublicationProvider` requires an authenticated `gh` executable on `PATH` and accepts a positive per-operation timeout in seconds. It reads no token or credential from Delivery configuration. The in-memory adapter has no environment variables, files, credentials, or command-line flags; callers register repository state explicitly.

## Dependencies

| Package | Purpose |
| --- | --- |
| `owlbear-delivery` | Owns the transport-free publication models and provider protocol |
| `pydantic` | Validates strict provider request and response models |

The GitHub CLI is an external runtime dependency for `GitHubCliPublicationProvider`; it is not required for the in-memory adapter.
