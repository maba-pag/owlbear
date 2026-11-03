"""A held completion's authority in one pinned Git tree, never its changed working copy."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_decisions import DecisionError, Scope, State
from owlbear_decisions.storage import parse
from owlbear_decisions.validate import Entry, Layer, check
from owlbear_delivery_next.git.command_failure import failed

if TYPE_CHECKING:
    from owlbear_delivery_next.local_system.data_repo import DataRepo


def _run(repo: DataRepo, until: float | None, *args: str, empty: bool = False) -> str:
    said = repo.git(*args, until=until)
    if said.returncode and not (empty and said.returncode == 1):
        msg = f"the held decision's Git authority could not be read in {repo.root}: {failed(said)}"
        raise OSError(msg)
    return said.stdout


def _layer(root: Path, rel: str) -> Layer | None:
    path = Path(rel)
    if path.suffix != ".md":
        return None
    match path.parts:
        case ("decisions", _):
            return Layer(root, Scope.GLOBAL)
        case (project, "decisions", _) if not project.startswith(".") and project != "decisions":
            return Layer(root / project, Scope.PROJECT, project)
        case (project, "changes", change, "decisions", _) if not project.startswith(".") and project != "decisions":
            return Layer(root / project / "changes" / change, Scope.CHANGE, project, change)
        case _:
            return None


def _contents(text: str, commit: str) -> dict[str, str]:
    """Git's NUL-separated path/line headers permit paths with whitespace and content with NULs."""
    found: dict[str, list[str]] = {}
    offset = 0
    while offset < len(text):
        path_end = text.find("\0", offset)
        number_end = text.find("\0", path_end + 1)
        line_end = text.find("\n", number_end + 1)
        if min(path_end, number_end, line_end) < 0:
            msg = f"Git returned incomplete decision lines at {commit}"
            raise OSError(msg)
        named = text[offset:path_end]
        if not named.startswith(f"{commit}:"):
            msg = f"Git returned a decision line outside pinned commit {commit}"
            raise OSError(msg)
        rel = named.removeprefix(f"{commit}:")
        found.setdefault(rel, []).append(text[number_end + 1 : line_end] + "\n")
        offset = line_end + 1
    return {rel: "".join(lines) for rel, lines in found.items()}


def _entries(repo: DataRepo, commit: str, until: float | None) -> tuple[list[Entry], list[tuple[Layer, str]]]:
    tree = _run(repo, until, "ls-tree", "-r", "-z", commit)
    text = _run(repo, until, "grep", "-z", "-n", "-a", "-e", "^", commit, "--",
                ":(glob)**/decisions/*.md", empty=True)  # fmt: skip
    contents, entries, unreadable = _contents(text, commit), [], []
    for row in filter(None, tree.split("\0")):
        info, rel = row.split("\t", 1)
        layer = _layer(repo.root, rel)
        if layer is None:
            continue
        path = repo.root / rel
        if info.split(" ", 1)[0] not in {"100644", "100755"}:
            unreadable.append((layer, f"{path} at {commit} is not a regular decision file"))
            continue
        try:
            decision = parse(contents.get(rel, ""))
        except DecisionError as exc:
            unreadable.append((layer, f"{path} at {commit}: {exc}"))
        else:
            entries.append(Entry(path, layer, decision))
    return entries, unreadable


def inactive(repo: DataRepo, ref: str, rel: str, until: float | None) -> str:
    """Why the watched project instruction is not active in the fetched, pinned remote authority."""
    commit = _run(repo, until, "rev-parse", "--verify", f"{ref}^{{commit}}").strip()
    entries, unreadable = _entries(repo, commit, until)
    target = next((e.decision for e in entries if e.path == repo.root / rel), None)
    if target is None or target.scope is not Scope.PROJECT:
        return f"{rel} is not a usable project decision at {commit}"
    if target.state is not State.IN_FORCE or target.conflict or target.read_back == "pending":
        return f"{target.id} is no longer active and clear of owner questions at {commit}"
    unknown = [why for layer, why in unreadable if layer.scope is Scope.GLOBAL or layer.project == target.project]
    if unknown:
        return f"{target.id}'s authority is incomplete: {'; '.join(unknown)}"
    findings = [f.message for f in check(entries) if target.id in f.involves]
    return f"{target.id} is no longer active at {commit}: {'; '.join(findings)}" if findings else ""
