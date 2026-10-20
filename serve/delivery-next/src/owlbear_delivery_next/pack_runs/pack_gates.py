"""The candidate's own files beyond its skills (TD-177, TD-194, TD-414): golden pages and the detector's glue.

The updater's folder holds a copy of each beside the skills: ``golden/`` (the golden pages and ``expected.json``, which
it may add to or remove from) and ``code/`` (the two files that call the engine and read upstream, edited only). A
change to either goes to the owner: changed evidence before the checks go on, code before the pull request. The
run's checks use the running code, never the candidate's (TD-414).
"""

from __future__ import annotations

import difflib
import hashlib
import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.design_packs import design_pack
from owlbear_delivery_next.pack_runs import pack_rounds
from owlbear_delivery_next.pack_runs.pack_candidate import MANIFEST, NOTICE

if TYPE_CHECKING:
    from owlbear_delivery_next.pack_runs.pack_candidate import Candidate

GOLDEN, CODE = "golden/", "code/"
GLUE = {"code/detector.py": "design_packs/detector.py", "code/pack_update.py": "design_packs/pack_update.py"}
GENERATED = frozenset({MANIFEST, NOTICE})  # written by the update, never by the updater: kept or discarded
KINDS = frozenset({"scope", "evidence", "unsure", "code"})
DELETED = "deleted"
AS_EXPECTED = "as expected"


def _sha(data: bytes | None) -> str:
    return DELETED if data is None else hashlib.sha256(data).hexdigest()


def _read(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() and not path.is_symlink() else None


def package_path(path: str) -> str:
    """The package file an updater path stands for."""
    return GLUE.get(path, path)


def restore(at: Path, paths: list[str], package: Path, c: Candidate) -> None:
    """Put back what the owner had undone: the package's file, or none where it has none; ``golden`` is every page.

    Links are removed, never followed. Upstream's text is extracted again by the caller.
    """
    for path in paths:
        _unlinked(at, path)
        if path == GOLDEN.rstrip("/"):
            shutil.rmtree(at / "golden", ignore_errors=True)
            lay_out_golden(at, package)
            continue
        name = path.removeprefix("skills/").removesuffix("/SKILL.md")
        if path.startswith("skills/") and name in c.baseline:
            data: bytes | None = c.baseline[name]
        elif path in GLUE or path.startswith(GOLDEN):
            data = _read(package / package_path(path))
        else:
            data = None
        if data is None:
            (at / path).unlink(missing_ok=True)
        else:
            (at / path).parent.mkdir(parents=True, exist_ok=True)
            (at / path).write_bytes(data)


def _unlinked(at: Path, path: str) -> None:
    """Remove any link on the way to *path*, or at it, so nothing is written or removed through one."""
    here = at
    for part in Path(path).parts:
        here /= part
        if here.is_symlink():
            here.unlink()
            return


def links(at: Path) -> list[str]:
    """Every link in the updater's folder: never followed, always the owner's to undo (TD-194)."""
    found = (p for p in at.rglob("*") if p.is_symlink() and ".git" not in p.relative_to(at).parts)
    return sorted(p.relative_to(at).as_posix() for p in found)


def lay_out_golden(at: Path, package: Path) -> None:
    """Copy the package's golden pages into the updater's folder."""
    (at / "golden").mkdir(parents=True, exist_ok=True)
    for page in sorted((package / "golden").iterdir()):
        if page.is_file():
            shutil.copyfile(page, at / "golden" / page.name)


def lay_out(at: Path, package: Path) -> None:
    """Copy the package's golden pages and glue into the updater's folder."""
    lay_out_golden(at, package)
    (at / "code").mkdir(exist_ok=True)
    for mine, theirs in GLUE.items():
        shutil.copyfile(package / theirs, at / mine)


def baseline(package: Path) -> dict[str, str]:
    """The package's golden pages and glue as the run found them: their digests, by package path."""
    pages = (p for p in sorted((package / "golden").iterdir()) if p.is_file())
    found = {f"golden/{p.name}": _sha(p.read_bytes()) for p in pages}
    return found | {theirs: _sha((package / theirs).read_bytes()) for theirs in GLUE.values()}


def allowed(path: str, present: bool, skills: list[str]) -> bool:  # noqa: FBT001 - whether the path is still there
    """Whether the updater may change *path*: the pinned skills and the glue edited, golden pages any way."""
    if path in GLUE or path in {f"skills/{n}/SKILL.md" for n in skills}:
        return present
    return path.startswith(GOLDEN) and path.count("/") == 1


def edits(at: Path, base: dict[str, str]) -> dict[str, bytes | None]:
    """The golden and glue files the updater changed against the package, by updater path; None when removed."""
    paths = {f"golden/{p.name}" for p in (at / "golden").glob("*") if p.is_file()} | set(GLUE)
    paths |= {p for p in base if p.startswith(GOLDEN)}
    now = {p: _read(at / p) for p in sorted(paths)}
    return {p: data for p, data in now.items() if _sha(data) != base.get(package_path(p), DELETED)}


def digest(changed: dict[str, bytes | None], prefix: str = "") -> str:
    """One digest over the changed files under *prefix*; empty when none changed."""
    picked = sorted((p, _sha(d)) for p, d in changed.items() if p.startswith(prefix))
    return hashlib.sha256(json.dumps(picked).encode()).hexdigest() if picked else ""


def identity(c: Candidate, changed: dict[str, bytes | None]) -> str:
    """The whole candidate's identity: its manifest, notice and skills, and every golden or glue change (TD-194)."""
    pack = design_pack.identity(c.manifest, c.skills)
    return hashlib.sha256(f"{pack}\n{_sha(c.notice.encode())}\n{digest(changed)}".encode()).hexdigest()


def content(c: Candidate, at: Path, path: str) -> str:
    """One candidate file's digest now, or ``deleted``."""
    made = {MANIFEST: c.manifest, NOTICE: c.notice}
    return _sha(made[path].encode()) if path in made else _sha(_read(at / path))


def diff(path: str, old: bytes | None, new: bytes | None, context: int = 5) -> str:
    """A unified diff of one file, from the package's text to the candidate's."""
    before = (old or b"").decode("utf-8", "replace").splitlines(keepends=True)
    after = (new or b"").decode("utf-8", "replace").splitlines(keepends=True)
    shown = difflib.unified_diff(before, after, f"package/{path}", f"candidate/{path}", n=context)
    return "".join(shown) or "(unchanged)"


def diffs(c: Candidate, at: Path, package: Path, changed: dict[str, bytes | None]) -> dict[str, str]:
    """Every file the update changes, by updater path, with its diff against the package: the generated ones first."""
    out = {
        MANIFEST: diff(MANIFEST, _read(package / MANIFEST), c.manifest.encode()),
        NOTICE: diff(NOTICE, _read(package / NOTICE), c.notice.encode()),
    }
    for name in c.pins["skills"]:
        path = f"skills/{name}/SKILL.md"
        if (now := (at / path).read_bytes()) != c.baseline.get(name):
            out[path] = diff(path, c.baseline.get(name), now)
    for path, data in changed.items():
        out[path] = diff(path, _read(package / package_path(path)), data)
    return out


def checked(wrong: dict[str, dict[str, list[str]]]) -> str:
    """The golden check in words."""
    if not wrong:
        return AS_EXPECTED
    pages = "; ".join(f"{p}: missing {', '.join(w['missing']) or 'none'}, unexpected "
                      f"{', '.join(w['unexpected']) or 'none'}" for p, w in wrong.items())  # fmt: skip
    return f"golden pages differ: {pages}"


def scope(run: str, bad: list[str]) -> dict[str, Any]:
    """The owner's question when the updater changed what it may not."""
    text = f"The updater changed {', '.join(bad[:10])}, which it may not change. Have it undo that, or discard?"
    return pack_rounds.question(f"{run}:scope:{_sha(json.dumps(bad).encode())[:12]}", "scope", text,
                                [pack_rounds.UNDO, pack_rounds.DISCARD], bad=bad)  # fmt: skip


def evidence(run: str, shown: str, said: str, golden: str, mark: str) -> dict[str, Any]:
    """The owner's question on changed expected evidence (TD-177), bound to its digest *mark*."""
    text = (f"The updater changed the golden pages' expected evidence. Its reason: {said or 'none given'}. "
            f"The golden check on the candidate: {golden}. Accept it, have it undone, or discard?")  # fmt: skip
    options = [pack_rounds.ACCEPT, pack_rounds.UNDO, pack_rounds.DISCARD]
    return pack_rounds.question(f"{run}:evidence:{mark[:12]}", "evidence", text, options, digest=mark, diff=shown)


def unsure(run: str, path: str, said: str, shown: str, mark: str) -> dict[str, Any]:
    """The owner's question on one change the challenger could not judge (TD-194), bound to its content."""
    text = f"The challenger is unsure whether the upgrade needs the change to {path}: {said} Keep it, or undo it?"
    options = [pack_rounds.KEEP, pack_rounds.DISCARD if path in GENERATED else pack_rounds.UNDO]
    return pack_rounds.question(f"{run}:unsure:{path}:{mark[:12]}", "unsure", text, options, path=path, digest=mark,
                                diff=shown)  # fmt: skip


def code(run: str, shown: str, mark: str) -> dict[str, Any]:
    """The owner's approval of the glue's diff before the pull request (TD-194, TD-414)."""
    text = ("The updater changed the detector's glue. This run checked the pack with the running code; the change "
            "takes effect once merged, after CI's unit tests pass. Approve its diff, or discard?")  # fmt: skip
    options = [pack_rounds.APPROVE, pack_rounds.DISCARD]
    return pack_rounds.question(f"{run}:code:{mark[:12]}", "code", text, options, digest=mark, diff=shown)
