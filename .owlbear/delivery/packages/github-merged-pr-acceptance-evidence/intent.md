# GitHub Merged-PR Acceptance Evidence

## Problem And Product Promise

GitHub REST API version `2026-03-10` removes `merge_commit_sha` from pull-request responses. A user can merge a Delivery pull request and GitHub can delete its source branch, but Delivery cannot complete acceptance because its provider needs the accepted merge commit. The user must not enter a merge SHA, restore a branch, or change a target checkout to make acceptance work.

After a finalized and ready pull request is merged, observation-only Delivery acceptance obtains provider-owned merge evidence, validates it against the persisted publication authority, writes one completion receipt, and exposes the Change in completed history. The existing transport-free provider and fail-closed completion contracts remain unchanged.

## Normal Workflow

1. Delivery publishes and marks a finalized Change pull request ready.
2. The user merges that pull request in GitHub; source-branch deletion is allowed.
3. Cockpit or Delivery invokes observation-only acceptance.
4. The GitHub publication adapter reads publication identity through REST and obtains merged evidence through the pinned-compatible GraphQL read for every merged pull-request observation; the removed REST field is cross-checked when present.
5. Delivery checks repository, PR, base, finalized head, merged state, merge commit, and merge time before creating completion history.
6. Cockpit shows acceptance observed and completed history contains the receipt. Repeating observation replays the receipt without creating another completion.

## In Scope

- `GitHubCliPublicationProvider` merged pull-request evidence under REST API version `2026-03-10`.
- A typed GraphQL read of `PullRequest.mergeCommit.oid`, `mergedAt`, `headRefOid`, and `baseRefName`.
- Cross-source identity and timestamp validation between REST and GraphQL.
- Open-PR compatibility when REST omits `merge_commit_sha`.
- Missing, null, malformed, or contradictory merged-evidence failures.
- Wire-realistic provider tests, including merge, squash-shaped, and rebase-shaped evidence cases where an OID is supplied.
- The existing Delivery acceptance handoff and replay proof.
- Focused adapter documentation and source-grounded operational guidance.

## Out Of Scope And Preserved Remainder

Do not downgrade the REST API version as the product fix. Do not relax `PublicationPullRequest` or `CompletionEvidence`, accept user-supplied merge data, infer a SHA from local `dev`, restore deleted source branches, merge pull requests from Delivery, or alter target refs. Do not redesign Cockpit polling, publication-check display, stale-admission reconciliation, MCP tool surfaces, or the dev-tunnel gateway. A GraphQL response with no merge commit remains an evidence failure and is not replaced with the PR head or target head.

Preserve the existing `PublicationProvider` protocol, `PublicationPullRequest` model, `PortfolioApplication.observe_acceptance`, merged pull-request latch, completion digest, provider error taxonomy, fixed `gh api` argument vectors, and in-memory provider behavior.

## Success

Given a ready finalized Change whose GitHub PR is merged and whose source branch is deleted, the acceptance observation obtains a 40-character merge commit from provider-owned GitHub evidence, confirms that the GraphQL head and base match the persisted PR publication, records the merge time, and creates one completion receipt. Given an open PR response without the removed REST field, the provider returns an open publication object without requesting merged evidence. Given missing or contradictory GraphQL evidence, Delivery remains incomplete and reports a typed failure without creating completion history.

The provider Change's acceptance ends at the provider contract, core acceptance tests, and bounded adapter documentation. After this Change is merged and a fresh Cockpit process loads it, a separate operator procedure re-observes the already-merged PR 194 and verifies its completion receipt; that recovery is not used as acceptance evidence for the provider Change itself.

## Technically Done But Wrong

Treating `merge_commit_sha: None` as sufficient for a merged PR; using the finalized PR head as the accepted merge commit; using the current target head or a merge base; asking the user to paste `c69a8c4...`; downgrading every REST request to an older API version; accepting GraphQL evidence without repository, PR, head, base, merged-state, OID, and timestamp checks; testing only synthetic REST payloads that still contain the removed field; or making the provider merge the pull request.

## Evidence And Assumptions

Observed evidence: GitHub REST requests without the version header return `merge_commit_sha` for PR 194, while the same endpoint with `X-GitHub-Api-Version: 2026-03-10` removes it. GitHub documents that removal. A live GraphQL query under the pinned environment returns PR 194 `mergeCommit.oid=c69a8c401bd2b8a71bad1a14d560f28541d0b313`, `headRefOid=7df45c291d04dc10413d844425f8ec0298d865d6`, `baseRefName=dev`, and `mergedAt=2026-08-22T20:57:56Z`. REST `GET /pulls/194/merge` returns an empty 204 body. The local `origin/dev` merge commit has PR 194 as its second parent.

The adapter separates REST wire parsing from public contract construction. Every invocation of public `read_pull_request()` that observes `merged=true` obtains GraphQL merged evidence, including a matched merged PR returned by `find_pull_request()` or a merged publication read by a core reconciliation path. Provider-owned write fences use a private REST-only open-state read before mutation and do not request merged evidence. GraphQL `mergedAt` is authoritative; REST merge fields are cross-checks when present. Missing repository or PR is `NOT_FOUND`; malformed, null, or contradictory merged evidence is retry-safe `INVALID_RESPONSE`. Merge-method-specific provider behavior is method-neutral and is proven with distinct OIDs rather than by assuming the OID equals the PR head.

```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
provenance: observed PR 194 incident and user-confirmed goal
statement: After a user merges a finalized and ready Delivery pull request, observation-only acceptance obtains provider-owned merge evidence without user-supplied data, source-branch restoration, local-target inference, or target mutation.
```

```yaml target-contract
kind: commitment
id: COM-002
class: protected-request
provenance: source-grounded API and Delivery contract
statement: The GitHub adapter preserves the transport-free PublicationProvider contract while adapting REST API version 2026-03-10 removal of merge_commit_sha through one typed GraphQL merged-evidence read.
```

```yaml target-contract
kind: commitment
id: COM-003
class: dealbreaker
provenance: existing fail-closed completion model
statement: Merged evidence binds one repository, pull request number, node identity, base branch, finalized head, merged state, 40-character merge OID, and timezone-aware merge time before Delivery creates completion history.
```

```yaml target-contract
kind: commitment
id: COM-004
class: important-reviewed
provenance: live query validation and provider boundary
statement: Missing, null, malformed, or contradictory GraphQL evidence produces a typed redacted provider failure and leaves the Change incomplete without substituting the PR head or target head.
```

```yaml target-contract
kind: commitment
id: COM-005
class: agreed-path
provenance: existing provider and workflow tests
statement: Provider tests and Delivery acceptance tests model the pinned REST wire shape, exercise the public provider and acceptance boundaries, and prove replay without duplicate completion.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Versioned GitHub merged evidence
promise: GitHubCliPublicationProvider reads open and merged pull requests through the pinned API contract and returns one cross-source validated PublicationPullRequest.
acceptance:
  - Given an open REST pull-request response without merge_commit_sha, GitHubCliPublicationProvider.read_pull_request returns an open PublicationPullRequest with no merge OID and does not issue a merged-evidence GraphQL read.
  - Given a merged REST response without merge_commit_sha and a GraphQL response whose repository, pull request number, headRefOid, baseRefName, merged, mergedAt, and mergeCommit.oid match the REST publication, GitHubCliPublicationProvider.read_pull_request returns the GraphQL merge OID and timezone-aware merge time.
  - Given a merged REST response with merge_commit_sha and matching GraphQL merged evidence, GitHubCliPublicationProvider.read_pull_request returns the GraphQL merge OID after the REST value is cross-checked.
  - Given a GraphQL response with a missing repository or pull request, the provider returns the existing not-found provider failure and no PublicationPullRequest.
  - Given GraphQL evidence with a null mergeCommit, malformed OID, malformed timestamp, wrong repository, wrong pull request number, wrong head, wrong base, merged false, or timestamp disagreement, the provider returns a retry-safe typed invalid-response failure and no merged PublicationPullRequest.
  - Given create, update, and draft-state provider operations with an open pull request, their REST-only open-state reads issue no merged-evidence GraphQL request; given a matched merged pull request, find_pull_request obtains the public merged contract through its read path.
commitments: [COM-001, COM-002, COM-003, COM-004]
dependencies: []
```

```yaml target-contract
kind: outcome
id: OUT-002
title: Durable provider and acceptance proof
promise: The provider and Delivery acceptance paths prove merged evidence, fail-closed cases, and idempotent completion without caller-supplied merge data.
acceptance:
  - Given queued provider transport responses for open, merged, merge-shaped, squash-shaped, and rebase-shaped evidence, provider tests assert operation names, variables, selected fields, distinct merge OIDs, and no equality assumption between PR head and merge OID.
  - Given an awaiting-merge PortfolioApplication and a provider PublicationPullRequest enriched with a merged OID, observe_acceptance creates one CompletionReceipt whose accepted_merge_commit is the provider OID and whose finalized_change_head remains the PR head.
  - Given an existing CompletionReceipt, a second observe_acceptance call returns the same receipt without another provider mutation or duplicate completion record.
  - Given incomplete merged evidence, observe_acceptance leaves the Change incomplete and creates no completion record.
commitments: [COM-001, COM-003, COM-004, COM-005]
dependencies: [OUT-001]
```

```yaml target-contract
kind: outcome
id: OUT-003
title: Operable adapter boundary
promise: The shipped adapter documentation and focused operational proof explain the REST and GraphQL evidence split and permit recovery of a merged Change through the normal acceptance operation.
acceptance:
  - Given the delivery-github README, it names GitHubCliPublicationProvider, REST API version 2026-03-10, GraphQL mergeCommit.oid enrichment, open-PR omission handling, and fail-closed merged evidence.
  - Given a read-side GraphQL transport failure or malformed merged-evidence response, the adapter exposes a bounded typed provider failure without raw GitHub payloads or a partial merged PublicationPullRequest.
  - Given the focused provider and acceptance test commands, their output records passing provider behavior and the existing exact-evidence core contract without requiring a merged external Change.
commitments: [COM-002, COM-004, COM-005]
dependencies: [OUT-002]
