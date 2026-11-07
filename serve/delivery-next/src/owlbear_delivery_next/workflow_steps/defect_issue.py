"""An issue in OwlBear's public repository for a defect a repair found in OwlBear's own code (#1066).

Delivery builds it from parts it checks (D-01M6SY5Y9HA0BANG4F738MB8Y8): the title, the OwlBear paths that exist in the
installed code, the repairer's defect text and the installed version. For a project whose repository is not public (or
whose visibility can't be read), text naming the project, its repository or one of its tracked files is held for the
owner on the repair instead. A marker finds an issue filed before, so one defect gets one issue. Writes go as TD-402's
account for OwlBear's repository (``OwlbearIssues``); a failed write is said whole and never stops the repair.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.github import repo_target
from owlbear_delivery_next.github.account import AccountMissing, Origin
from owlbear_delivery_next.github.owlbear_issues import OwlbearIssues
from owlbear_delivery_next.github.provider import ProviderError
from owlbear_delivery_next.local_system import codebase, local_home

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.change_contracts.repair_tools import Defect
    from owlbear_delivery_next.state_store.store import Store

REPOSITORY = codebase.URL.removeprefix("https://github.com/").removesuffix(".git")
SOURCE = codebase.ROOT.parents[3]  # the OwlBear checkout holding serve/delivery-next/src/owlbear_delivery_next


def file(store: Store, change: Change, path: Path, defect: Defect) -> str:
    """File *defect* once; what happened, as the repair records it."""
    del change  # the issue never names the Change
    verified = [p for p in defect.paths if _ours(p)]
    if not verified:
        return f"not filed: none of {', '.join(defect.paths)} is a file in OwlBear's code at {SOURCE}"
    issues = OwlbearIssues(REPOSITORY, local_home.root())
    body = _body(defect, verified)
    if names := _named(issues, store, path, f"{defect.title}\n{body}"):
        named = ", ".join(names[:5])
        return f"held for you, not filed: it names this private project ({named}). {defect.title}\n{body}"
    marker = f"<!-- owlbear-defect:{hashlib.sha256(defect.title.casefold().encode()).hexdigest()[:16]} -->"
    try:
        if found := issues.find(marker):
            return f"filed before: {found.url}"
        return f"filed {issues.create(defect.title, f'{body}\n\n{marker}').url}"
    except (ProviderError, AccountMissing) as exc:
        return f"not filed: {failure(exc)}"


def _ours(said: str) -> bool:
    """Whether *said* (``path`` or ``path:line``) names a file in OwlBear's code."""
    rel = PurePosixPath(said.split(":", 1)[0].strip())
    return bool(rel.parts) and not rel.is_absolute() and ".." not in rel.parts and (SOURCE / rel).is_file()


def _body(defect: Defect, paths: list[str]) -> str:
    listed = "\n".join(f"- `{p}`" for p in paths)
    return (
        f"{defect.text}\n\n**Where:**\n{listed}\n\n**OwlBear version:** {_version()}\n\n"
        "_Filed by Delivery when a repair of a stuck step found this defect in OwlBear's own code (#1066)._"
    )


def _named(issues: OwlbearIssues, store: Store, path: Path, text: str) -> list[str]:
    """What of a non-public project *text* names: its name, its repository, its tracked files; empty when public."""
    try:
        origin = Origin.of(path)
    except AccountMissing:
        origin = Origin.LOCAL
    slug = f"{origin.owner}/{origin.name}" if origin.host else ""
    if slug.casefold() == REPOSITORY.casefold():
        return []  # OwlBear's own repository is the public one the issue goes to
    try:
        seen = repo_target.view(issues, slug) if slug else None
    except ProviderError, AccountMissing:
        seen = None
    if seen is not None and seen.visibility == "public":
        return []
    names = {store.name, origin.name, slug, *_tracked(path)} - {""}
    low = text.casefold()
    return sorted(n for n in names if n.casefold() in low)


def _tracked(path: Path) -> list[str]:
    done = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector
        [worktree.GIT, "ls-files", "-z"], cwd=path, capture_output=True, text=True, check=False, timeout=60
    )
    return [p for p in done.stdout.split("\0") if "/" in p or "." in p] if done.returncode == 0 else []


def _version() -> str:
    done = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector
        [worktree.GIT, "describe", "--tags", "--always"], cwd=SOURCE, capture_output=True, text=True, check=False
    )
    return done.stdout.strip() or "unknown"
