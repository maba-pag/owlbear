"""Host-supplied planning authority and visible limits for a pinned audit."""

from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING

from owlbear_decisions import Scope, State
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.github.account import Origin
from owlbear_delivery_next.github.gh_client import GhClient, repo
from owlbear_delivery_next.github.provider import ProviderError
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store import backlog, decision_store, github_writer
from owlbear_delivery_next.state_store.store import StoreError
from owlbear_delivery_next.workflow_steps.lookup import _unresolved

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from typing import Any

    from owlbear_delivery_next.state_store.store import Store


def prepare(store: Store, root: Path, state: dict[str, Any], repository: str) -> list[str]:
    """Supply complete decisions or fail before a session; name every other unavailable source."""
    at = root / "context"
    at.mkdir()
    view = decision_store.load(store.shared, store.name)
    decisions = [
        e.decision
        for e in view.snapshot.entries
        if e.decision.state is State.IN_FORCE and e.decision.scope is not Scope.CHANGE
    ]
    if blocked := _unresolved(view.snapshot, decisions):
        msg = "audit planning authority is unresolved:\n" + json.dumps(blocked, indent=2)
        raise ValueError(msg)
    (at / "decisions.md").write_text(
        json.dumps([d.model_dump(mode="json") for d in decisions], indent=2) + "\n", encoding="utf-8"
    )
    (at / "run.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    limits: list[str] = []

    def supply(name: str, read: Callable[[], object]) -> None:
        try:
            out = read()
            (at / f"{name}.md").write_text(json.dumps(out, indent=2, default=str) + "\n", encoding="utf-8")
        except (OSError, ValueError, TypeError, StoreError, ProviderError, backlog.BacklogError) as exc:
            limits.append(f"{name}: {failure(exc)}")

    supply("changes", lambda: _changes(store))
    supply("backlog", lambda: _backlog(store))
    supply("issues", lambda: _issues(store, repository))
    try:
        if store.shared is None:
            msg = "no shared data repository"
            raise FileNotFoundError(msg)
        source = store.shared.root / store.name / "research"
        shutil.copytree(source, at / "research", symlinks=False)
    except (OSError, shutil.Error) as exc:
        limits.append(f"research: {failure(exc)}")
    (at / "limits.md").write_text("\n".join(limits) + "\n", encoding="utf-8")
    return limits


def _changes(store: Store) -> list[object]:
    found = []
    for slug in store.slugs():
        change = store.read(slug)
        if not change.finished_at and change.brief.approved_at:
            brief = next(
                (b for b in change.brief.approved if b.version == change.brief.approved_version),
                change.brief if change.brief.version == change.brief.approved_version else None,
            )
            if brief is None:
                msg = f"{change.handle}: the approved brief version is missing"
                raise ValueError(msg)
            found.append(
                {
                    "handle": change.handle,
                    "brief": brief.model_dump(mode="json"),
                    "plan": change.plan.model_dump(mode="json") if change.plan else None,
                }
            )
    return found


def _backlog(store: Store) -> list[object]:
    book = backlog.Backlog.of(store)
    entries, invalid = book.read(fresh=True)
    if invalid:
        msg = "unreadable Backlog entries: " + ", ".join(invalid)
        raise ValueError(msg)
    return [
        e.model_dump(mode="json")
        for e in entries.values()
        if e.status not in {"done", "dropped"} and store.name in backlog.named(e)
    ]


def _issues(store: Store, repository: str) -> list[object]:
    if not repository:
        msg = "the project profile has no GitHub repository"
        raise ValueError(msg)
    host = profile.value(store.read_profile(), profile.HOST, "")
    if not host:
        msg = "the project profile has no GitHub host"
        raise ValueError(msg)
    owner, name = repository.split("/")
    writer = github_writer.of(store, Origin(host, owner, name))
    client, found, page = IssueContext(store.root, writer=writer, host=host), [], 1
    while True:
        rows = client.page(repository, page)
        if not isinstance(rows, list):
            msg = "GitHub returned an invalid issue listing"
            raise TypeError(msg)
        found.extend(row for row in rows if "pull_request" not in row)
        if len(rows) < PAGE:
            return found
        page += 1


PAGE = 100


class IssueContext(GhClient):
    """Paginated read-only GitHub planning context."""

    def page(self, repository: str, page: int) -> object:
        """Read one full page, including its body and labels."""
        return self._api("audit_context", "GET", f"{repo(repository)}/issues?state=open&per_page={PAGE}&page={page}")
