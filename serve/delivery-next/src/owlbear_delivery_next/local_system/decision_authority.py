"""A held completion's authority in one pinned Git tree, never its changed working copy."""

from __future__ import annotations

from io import BytesIO, StringIO
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_decisions import DecisionError, Scope, State
from owlbear_decisions.storage import ignored_name, parse_named
from owlbear_decisions.validate import Entry, Layer, check
from owlbear_delivery_next.git.command_failure import failed, failure

if TYPE_CHECKING:
    from owlbear_delivery_next.local_system.data_repo import DataRepo


def _diagnostic(text: str) -> str:
    """Keep diagnostic text UTF-8 encodable without losing undecodable path characters."""
    return text.encode("utf-8", "backslashreplace").decode("utf-8")


def _run(repo: DataRepo, until: float | None, *args: str, lossless: bool = False) -> str:
    said = repo.git(*args, until=until, lossless=lossless)
    if said.returncode:
        msg = f"the held decision's Git authority could not be read in {repo.root}: {failed(said)}"
        raise OSError(_diagnostic(msg))
    return said.stdout


def _layer(root: Path, rel: str, mode: str) -> Layer | None:
    path = Path(rel)
    if path.parent.name == "decisions" and ignored_name(path.name):
        return None
    match path.parts:
        case ("decisions",) if mode != "040000":
            layer = Layer(root, Scope.GLOBAL)
        case ("decisions", _):
            layer = Layer(root, Scope.GLOBAL)
        case (project, "decisions" | "changes") if (
            mode != "040000" and not project.startswith(".") and project != "decisions"
        ):
            layer = Layer(root / project, Scope.PROJECT, project)
        case (project, "changes", _) if mode == "120000" and not project.startswith(".") and project != "decisions":
            layer = Layer(root / project, Scope.PROJECT, project)
        case (project, "changes", change, "decisions") if (
            mode != "040000" and not project.startswith(".") and project != "decisions"
        ):
            layer = Layer(root / project / "changes" / change, Scope.CHANGE, project, change)
        case (project, "decisions", _) if not project.startswith(".") and project != "decisions":
            layer = Layer(root / project, Scope.PROJECT, project)
        case (project, "changes", change, "decisions", _) if not project.startswith(".") and project != "decisions":
            layer = Layer(root / project / "changes" / change, Scope.CHANGE, project, change)
        case _:
            return None
    return layer


def _contents(repo: DataRepo, commit: str, blobs: dict[str, int], until: float | None) -> dict[str, bytes]:
    """Read pinned blobs together, separating their exact bytes by Git's object sizes."""
    if not blobs:
        return {}
    text = _run(repo, until, "show", "--no-color", "--no-ext-diff", "--no-textconv", *blobs, lossless=True)
    data = text.encode("utf-8", "surrogateescape")
    expected = sum(blobs.values())
    if len(data) != expected:
        msg = f"Git returned {len(data)} decision bytes at {commit} in {repo.root}; expected {expected}"
        raise OSError(_diagnostic(msg))
    stream = BytesIO(data)
    return {oid: stream.read(size) for oid, size in blobs.items()}


def _entries(repo: DataRepo, commit: str, until: float | None) -> tuple[list[Entry], list[tuple[Layer, str]]]:
    tree = _run(repo, until, "ls-tree", "-r", "-t", "-l", "-z", commit, lossless=True)
    entries, unreadable = [], []
    wanted: dict[Path, tuple[Layer, str, int]] = {}
    for row in filter(None, tree.split("\0")):
        info, rel = row.split("\t", 1)
        mode, kind, oid, size = info.split()
        layer = _layer(repo.root, rel, mode)
        if layer is None:
            continue
        path = repo.root / rel
        if path.suffix != ".md" or mode not in {"100644", "100755"} or kind != "blob":
            unreadable.append((layer, f"{str(path)!r} at {commit} is not a regular decision file"))
            continue
        try:
            wanted[path] = (layer, oid, int(size))
        except ValueError as exc:
            msg = f"Git returned an unreadable object size {size!r} for {str(path)!r} at {commit}"
            raise OSError(_diagnostic(msg)) from exc
    contents = _contents(repo, commit, {oid: size for _layer, oid, size in wanted.values()}, until)
    for path, (layer, oid, _size) in wanted.items():
        try:
            text = contents[oid].decode("utf-8")
            decision = parse_named(StringIO(text, newline=None).read(), path.name)
        except (DecisionError, UnicodeDecodeError) as exc:
            unreadable.append((layer, f"{str(path)!r} at {commit}: {failure(exc)}"))
        else:
            entries.append(Entry(path, layer, decision))
    return entries, unreadable


def inactive(repo: DataRepo, ref: str, rel: str, until: float | None) -> str:
    """Why the watched project instruction is not active in the fetched, pinned remote authority."""
    commit = _run(repo, until, "rev-parse", "--verify", f"{ref}^{{commit}}").strip()
    entries, unreadable = _entries(repo, commit, until)
    target = next((e.decision for e in entries if e.path == repo.root / rel), None)
    if target is None or target.scope is not Scope.PROJECT:
        return _diagnostic(f"{rel} is not a usable project decision at {commit}")
    if target.state is not State.IN_FORCE or target.conflict or target.read_back == "pending":
        return _diagnostic(f"{target.id} is no longer active and clear of owner questions at {commit}")
    unknown = [why for layer, why in unreadable if layer.scope is Scope.GLOBAL or layer.project == target.project]
    if unknown:
        return _diagnostic(f"{target.id}'s authority is incomplete: {'; '.join(unknown)}")
    findings = [f.message for f in check(entries) if target.id in f.involves]
    return _diagnostic(f"{target.id} is no longer active at {commit}: {'; '.join(findings)}") if findings else ""
