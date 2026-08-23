# GitHub Merged-PR Acceptance Evidence Design

## Ownership

`serve/delivery-github/src/owlbear_delivery_github/github.py` owns the concrete GitHub adapter. `serve/delivery/src/owlbear_delivery/publication_provider.py` owns the transport-free provider contract and its fail-closed merged-state validator. `PortfolioApplication.observe_acceptance()` owns Delivery completion and must remain unchanged.

## Read And Write Control Flow

The provider has one public `read_pull_request(repository, number)` operation, but its call graph matters. `find_pull_request()` reads a matched PR and must return the public provider contract, while `_require_open_head()` reads before metadata or draft-state writes and draft-state writes read again after mutation. Therefore the implementation must introduce `_read_pull_request_rest()` as a REST wire/parser boundary and keep `_pull_request()` REST-only. Public `read_pull_request()` calls `_read_pull_request_rest()` and, when the parsed response reports `merged=true`, calls `_read_merged_evidence()` before constructing the final merged `PublicationPullRequest`. This enrichment applies to every public `read_pull_request()` caller, including `find_pull_request()` and core publication reconciliation reads, because the public contract cannot represent a merged PR without merge evidence. Provider-owned write fences instead call a private `_read_open_pull_request()` built on the REST-only stage, verify `state="open"` and `merged=false` before mutation, and use the same REST-only path for the post-mutation draft-state read. Create/update responses are REST-only because they are expected to be open. No write-fence path issues the merged GraphQL query.

This arrangement preserves write-fence behavior and prevents a read-evidence query from changing write-operation failure classification. The public result remains `PublicationPullRequest`; GraphQL response models remain private to the adapter.

## Fixed GraphQL Evidence Query

Use one named read query with only these fields:

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

The provider sends this through its existing `_graphql_query()` runner with fixed variables derived from the requested repository and PR number. It adds no generic GraphQL interface, no user query input, and no mutation.

## Cross-Source Contract

REST supplies publication fields: node ID, head branch, head SHA, base branch, title, body, draft, state, merged flag, and any legacy merge fields. GraphQL supplies canonical merged evidence: `mergeCommit.oid` and `mergedAt`. The provider requires:

- repository name matches case-insensitively;
- PR number matches;
- GraphQL `headRefOid` equals REST head SHA;
- GraphQL `baseRefName` equals REST base branch;
- GraphQL `merged` is true;
- `mergeCommit.oid` is a 40-character lowercase hexadecimal SHA;
- `mergedAt` parses as a timezone-aware timestamp;
- REST `merge_commit_sha`, when present, equals GraphQL `mergeCommit.oid`;
- REST `merged_at`, when present, equals GraphQL `mergedAt` after timezone-aware parsing.

GraphQL `mergedAt` is the value passed into the public `PublicationPullRequest`. A null merge object, null or malformed timestamp, identity mismatch, or conflicting legacy REST value is a retry-safe `INVALID_RESPONSE`. Missing repository or pull request is `NOT_FOUND` and non-retryable. Transport and nonzero-command errors retain existing read-side provider mappings.

## Tests

Use the public `GitHubCliPublicationProvider` boundary and the existing queued subprocess runner. Cover:

1. Open REST response without `merge_commit_sha`: one REST call, no GraphQL call, open public result.
2. Merged REST response without the removed field: REST followed by one exact GraphQL call, GraphQL OID/time returned.
3. Merged REST response containing the legacy field: REST followed by GraphQL, matching values accepted and conflicting values rejected.
4. Missing repository/PR, GraphQL errors, malformed envelope, null merge object, invalid OID, invalid timestamp, wrong number, wrong head, wrong base, merged false, and timestamp disagreement.
5. `find_pull_request()` obtains merged evidence for a merged match; create, update, and draft-state write fences use REST-only open reads and preserve their existing conflict behavior without a merged-evidence query.
6. Merge-, squash-, and rebase-shaped fixtures: distinct supplied merge OIDs are accepted without requiring equality to the PR head or inferring the merge method.
7. Existing check-observation and draft-state tests remain green.

Existing `PortfolioApplication.observe_acceptance()` tests prove the core receipt handoff. Add one narrow test only if needed to bind the enriched provider result to the core path; assert accepted merge OID differs from finalized head and replay is idempotent. Do not alter core authority.

## Documentation And Operations

Update `serve/delivery-github/README.md` with the REST version removal, open-response behavior, read-only GraphQL enrichment, REST-only internal calls, cross-source checks, and fail-closed null/mismatch behavior. Update `.owlbear/sources/overview.md` for the breaking-change and GraphQL object sources.

After this provider Change is independently merged and Cockpit is restarted, run the normal acceptance observation for the already-merged PR 194. That operator check must find the persisted publication identity even though the source branch is deleted, obtain the GraphQL OID `c69a8c401bd2b8a71bad1a14d560f28541d0b313`, and create one completion receipt. This is deployment verification of the product goal, not a self-referential acceptance requirement.

## Alternatives Rejected

- Downgrading every REST call to `2022-11-28`: depends on a removed/deprecated field and changes unrelated response contracts.
- REST `GET /pulls/{number}/merge`: returns 204 with no SHA.
- Local target or merge-base derivation: not provider acceptance evidence.
- Relaxing core completion models: permits completion without the accepted merge commit.
- User-supplied SHA: breaks observation-only authority.
- Enrichment in `_pull_request()` or unguarded `read_pull_request()`: leaks merged-read behavior into write and publication-discovery call paths.

## Limits

GraphQL `mergeCommit` is nullable. Null remains incomplete evidence; this design does not invent a fallback. Merge-method behavior is method-neutral and tested with supplied distinct OIDs. The design does not claim a tunnel error fix or a safe manual repair route for a missing completion receipt.
