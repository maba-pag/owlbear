"""A GitHub repository as onboarding reads, checks and creates it (#723), through the account's ``GhClient`` (TD-402).

The view builds no ``Repository``, whose default branch can't be empty: an empty repository reads as one.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from owlbear_delivery_next.github.gh_client import Missing, invalid, repo
from owlbear_delivery_next.github.provider import FailureCode, MergeMethod, ProviderError

if TYPE_CHECKING:
    from owlbear_delivery_next.github.gh_client import GhClient, Json

FIELDS = "nameWithOwner,isEmpty,defaultBranchRef,mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed,visibility,id"
_UNRESOLVED = "could not resolve to a repository"  # gh's answer for a repository that is absent or hidden from us


@dataclass(frozen=True)
class RepoState:
    """One repository's onboarding facts; an empty one has no default branch yet."""

    repository: str  # owner/name as GitHub spells it
    id: str  # GraphQL node id
    empty: bool
    default_branch: str  # "" while empty
    methods: frozenset[MergeMethod]  # the merge methods its settings allow
    visibility: str  # private, public or internal


def _gh(client: GhClient, operation: str, args: tuple[str, ...], **kw: Any) -> Json:  # noqa: ANN401 - JSON
    return client._gh(operation, args, **kw)  # noqa: SLF001 - the account's transport, as GhProvider's mixins use it


def _api(client: GhClient, operation: str, method: str, endpoint: str, **kw: Any) -> Json:  # noqa: ANN401 - JSON
    return client._api(operation, method, endpoint, **kw)  # noqa: SLF001 - as `_gh`


def view(client: GhClient, repository: str) -> RepoState | None:
    """Read *repository* (``owner/name``); ``None`` when it doesn't exist or the account can't see it."""
    try:
        r = _gh(client, "view_repository", ("repo", "view", repository, "--json", FIELDS))
    except ProviderError as exc:
        if _UNRESOLVED in str(exc).casefold():
            return None
        raise
    allowed = (
        (MergeMethod.MERGE, "mergeCommitAllowed"),
        (MergeMethod.SQUASH, "squashMergeAllowed"),
        (MergeMethod.REBASE, "rebaseMergeAllowed"),
    )
    try:
        return RepoState(
            repository=r["nameWithOwner"],
            id=r["id"],
            empty=r["isEmpty"] is True,
            default_branch=r["defaultBranchRef"]["name"],
            methods=frozenset(m for m, key in allowed if r[key] is True),
            visibility=r["visibility"].casefold(),
        )
    except (KeyError, TypeError, AttributeError) as exc:
        invalid("view_repository", f"gh returned an invalid repository: {json.dumps(r)}", exc)


def name_free(client: GhClient, owner: str, name: str) -> bool:
    """Whether the account sees no repository ``owner/name``."""
    return isinstance(_api(client, "name_free", "GET", repo(f"{owner}/{name}"), absent=(404,)), Missing)


def private_rules_limit(client: GhClient, owner: str) -> str:
    """Why a private repository *owner* creates can have no branch rules: its GitHub plan is free; empty otherwise.

    An organisation's plan is read from the organisation, a user's from the account acting for it; a plan GitHub doesn't
    show (an organisation's to a member who isn't its owner) leaves the run to find out, as it does for an existing one.
    """
    found = _api(client, "read the organisation's plan", "GET", f"orgs/{owner}", absent=(404,))
    if isinstance(found, Missing):
        found = _api(client, "read the account's plan", "GET", "user")
        if str(found.get("login", "")).casefold() != owner.casefold():
            return ""
    if (found.get("plan") or {}).get("name") != "free":
        return ""
    return f"GitHub's free plan of {owner} allows no branch rules on a private repository: make it public, or upgrade"


def create(client: GhClient, owner: str, name: str, visibility: Literal["private", "public"]) -> RepoState:
    """Create ``owner/name`` with *visibility* and read it back; a lost answer raises for the caller to reconcile."""
    args = ("repo", "create", f"{owner}/{name}", f"--{visibility}")
    _gh(client, "create_repository", args, write=True, raw=True)
    if (state := view(client, f"{owner}/{name}")) is None:
        detail = f"gh created {owner}/{name}, but GitHub doesn't show it to the account"
        raise ProviderError(FailureCode.RESPONSE_UNKNOWN, "create_repository", detail, retry_safe=False)
    return state


def ci_status(client: GhClient, repository: str, sha: str) -> str:
    """The latest ``CI`` check run on *sha*: its conclusion when finished, else its status; ``missing`` when none."""
    found = _api(client, "ci_status", "GET", f"{repo(repository)}/commits/{sha}/check-runs?check_name=CI")
    try:
        runs = found["check_runs"]
        return (runs[0]["conclusion"] or runs[0]["status"]) if runs else "missing"
    except (KeyError, TypeError, IndexError) as exc:
        invalid("ci_status", f"gh returned invalid check runs: {json.dumps(found)}", exc)


def labels(client: GhClient, repository: str) -> set[str]:
    """The labels *repository* has."""
    found = _gh(client, "read labels", ("label", "list", "--repo", repository, "--json", "name", "--limit", "500"))
    return {x["name"] for x in found}


def create_label(client: GhClient, repository: str, name: str) -> None:
    """Create the label *name* in *repository*."""
    _gh(client, "create a label", ("label", "create", name, "--repo", repository), write=True, raw=True)
