"""Updating Impeccable (design skill research §3.5, update procedure; TD-76): the tooling before the first update.

1. Notice: how many skill releases upstream is ahead of the pinned tag; offline is "unknown", a refusal an "error".
2. Diff: rules added, removed and changed, and skill files changed, between the pinned commit and a candidate, read
   from a local clone of upstream; the owner chooses what to adopt in a direct chat. A tag can move; the commit cannot.
3. Golden pages: an engine must find exactly the expected rules on Delivery's fixture pages.
4. Calibration replay: ``pack_replay`` reruns the design judge on decided rounds; ``calibration.replayed`` compares.
5. Activation: a pack is the package's manifest and skills; a reviewed commit switches it in one step, and reverting
   that commit rolls the whole pack back. Each pack installs into its own folder, so a rollback needs no download.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from datetime import UTC, datetime, timedelta
from http.client import HTTPException
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.error import HTTPError

from owlbear_delivery_next.impeccable import detector, pack_files
from owlbear_delivery_next.local_system import local_home

if TYPE_CHECKING:
    from collections.abc import Callable
    from importlib.resources.abc import Traversable

    from owlbear_delivery_next.impeccable.pack_files import Installed

RELEASES = "https://api.github.com/repos/{repo}/releases?per_page=100"
NOTICE = "notice.json"  # beside the installed packs
STALE = timedelta(days=1)
PAGE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*\.html")  # a golden page: a plain file name in its folder
SECONDS = 10.0  # the notice's one request: the readiness check at host start never waits long for it
REGISTRY = "crates/foundation/src/registry.rs"  # upstream's rule registry
TABLE = "pub static ANTIPATTERNS"  # its rule table, ended by the first line "];"
SKILL = "skill"  # upstream's skill text
SKILL_TEXT = "Skill text: "  # the diff report's last line, naming the command that shows the skill text
ENTRY = re.compile(r"^ {4}Antipattern \{\n(?P<body>.*?)^ {4}\},?$", re.DOTALL | re.MULTILINE)  # rustfmt's layout
FIELD = re.compile(r"^ {8}(?P<key>\w+): (?P<value>.*?),?\s*(?=^ {8}\w+: |\Z)", re.DOTALL | re.MULTILINE)


def _version(tag: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", tag))


def behind(fetch: Callable[[str], bytes] | None = None) -> int | None:
    """Skill releases among upstream's newest 100 that are newer than the pinned tag; None when unreadable."""
    found = newer(fetch)
    return None if found is None else len(found)


class Unread(Exception):  # noqa: N818 - it names the outcome, as ``said`` words it
    """Upstream's releases could not be read; ``offline`` when upstream was not reached at all."""

    def __init__(self, detail: str, *, offline: bool) -> None:
        """Why, and whether upstream was reached."""
        super().__init__(detail)
        self.offline = offline


def newer(fetch: Callable[[str], bytes] | None = None) -> list[str] | None:
    """Those releases' tags, oldest first; None when unreadable."""
    try:
        return releases(fetch)
    except Unread:
        return None


def releases(fetch: Callable[[str], bytes] | None = None) -> list[str]:
    """The skill releases newer than the pinned tag, oldest first.

    Raises:
        Unread: Upstream was not reached, refused, or answered with no list of releases.
    """
    upstream = pack_files.manifest()["upstream"]
    url = RELEASES.format(repo=upstream["repository"])
    try:
        raw = fetch(url) if fetch else pack_files.fetch(url, SECONDS)
    except HTTPError as exc:
        msg = f"GitHub answered {exc.code} {exc.reason}"
        raise Unread(msg, offline=False) from exc
    except (OSError, HTTPException) as exc:
        msg = f"GitHub was not reached: {exc}"
        raise Unread(msg, offline=True) from exc
    try:
        found = json.loads(raw)
    except ValueError as exc:
        msg = "GitHub's answer is not JSON"
        raise Unread(msg, offline=False) from exc
    if not isinstance(found, list):
        msg = "GitHub's answer is no list of releases"
        raise Unread(msg, offline=False)
    tags = [r.get("tag_name") for r in found if isinstance(r, dict) and not r.get("prerelease")]
    pinned = _version(upstream["tag"])
    return sorted(
        (t for t in tags if isinstance(t, str) and t.startswith("skill-v") and _version(t) > pinned), key=_version
    )


def notice(*, refresh: bool, force: bool = False, fetch: Callable[[str], bytes] | None = None) -> dict[str, Any]:
    """The last check of upstream for the pinned tag; reading never goes online.

    *refresh* checks when the last count is over a day old, or a check failed since; *force* checks now. ``state`` is
    ``known`` (counted within a day), ``stale`` (counted longer ago), ``unknown`` (never counted, or upstream not
    reached since) or ``error`` (upstream refused or answered unreadably since), with ``detail`` saying why. ``latest``
    is the newest skill release, the pinned tag when none is newer. A failed check keeps the last count in the file;
    it is shown again only by the next count.
    """
    pack, tag = pack_files.manifest()["pack"], pack_files.manifest()["upstream"]["tag"]
    path = local_home.root() / pack_files.PACKS / NOTICE
    try:
        kept = json.loads(path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        kept = {}
    kept = kept if isinstance(kept, dict) and kept.get("tag") == tag else {}  # another pack's count says nothing here
    if force or (refresh and _state(kept)["state"] != "known"):
        now = datetime.now(UTC).isoformat(timespec="seconds")
        try:
            found = releases(fetch)
            kept = {"tag": tag, "behind": len(found), "latest": found[-1] if found else tag, "checked_at": now}
        except Unread as exc:
            kept = kept | {"tag": tag, "failed_at": now, "failure": str(exc)[:400], "offline": exc.offline}
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(kept) + "\n", encoding="utf-8")
        except OSError:
            pass  # the notice is a hint; it is checked again next time
    return {"pack": pack, **_state(kept)}


def _time(value: object) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _state(kept: dict[str, Any]) -> dict[str, Any]:
    checked, failed, behind = _time(kept.get("checked_at")), _time(kept.get("failed_at")), kept.get("behind")
    if failed and (checked is None or failed >= checked):
        state = "unknown" if kept.get("offline") is not False else "error"
        detail = str(kept.get("failure", ""))
        return {"state": state, "behind": None, "latest": "", "checked_at": None, "detail": detail}
    if checked is None or not isinstance(behind, int):
        return {"state": "unknown", "behind": None, "latest": "", "checked_at": None, "detail": ""}
    state = "stale" if datetime.now(UTC) - checked > STALE else "known"
    return {"state": state, "behind": behind, "latest": str(kept.get("latest", "")), "checked_at": kept["checked_at"],
            "detail": ""}  # fmt: skip


def said(n: dict[str, Any]) -> str:
    """The notice in words, for setup and the settings page."""
    if n.get("behind") is None:
        return f"Impeccable ({n['pack']}): releases upstream unknown"
    return f"Impeccable ({n['pack']}): {n['behind']} release{'s' if n['behind'] != 1 else ''} behind"


def _git(clone: Path, *args: str) -> str:
    command = ["git", *args]
    done = subprocess.run(command, cwd=clone, capture_output=True, text=True, check=True, timeout=60)  # noqa: S603
    return done.stdout


def pinned_commit(clone: Path) -> str:
    """The commit the manifest pins, which a moved tag cannot change, once the clone is known to have it.

    Raises:
        pack_files.PackError: The clone does not have the pinned commit.
    """
    upstream = pack_files.manifest()["upstream"]
    commit = upstream["commit"]
    try:
        _git(clone, "cat-file", "-e", f"{commit}^{{commit}}")
    except subprocess.CalledProcessError:
        msg = f"the pinned commit {commit} ({upstream['tag']}) is not in the clone {clone}; fetch upstream there first"
        raise pack_files.PackError(msg) from None
    return commit


def rules(clone: Path, tag: str) -> dict[str, dict[str, str]]:
    """Every field of each rule in upstream's ``ANTIPATTERNS`` table at *tag*, by rule id; not the test fixtures.

    Raises:
        ValueError: The registry has no rule table, or a rule in it could not be read whole.
    """
    text = _git(clone, "show", f"{tag}:{REGISTRY}")
    start = text.find(TABLE)
    if start < 0:
        msg = f"no {TABLE} table in {REGISTRY} at {tag}"
        raise ValueError(msg)
    table, found = text[start : text.find("\n];", start)], {}
    for entry in ENTRY.finditer(table):
        fields = {m["key"]: " ".join(m["value"].split()) for m in FIELD.finditer(entry["body"])}
        found[fields.get("id", "").strip('"')] = fields
    if "" in found or any("name" not in f for f in found.values()) or len(found) != table.count("Antipattern {"):
        msg = f"read {len(found)} of {table.count('Antipattern {')} rules whole in {REGISTRY} at {tag}"
        raise ValueError(msg)
    return found


def diff(clone: Path, to: str) -> str:
    """The report the owner chooses from: rules added, removed and changed field by field, and skill files changed.

    The skill text itself is read with ``git diff PINNED TO -- skill`` in the clone, named at the end.

    Raises:
        pack_files.PackError: The clone does not have the pinned commit.
    """
    pinned = pinned_commit(clone)
    old, new = rules(clone, pinned), rules(clone, to)
    files_changed = _git(clone, "diff", "--name-status", pinned, to, "--", SKILL).splitlines()
    tag = pack_files.manifest()["upstream"]["tag"]
    lines = [f"# Impeccable update: {tag} ({pinned}) to {to}", ""]
    added, removed = sorted(new.keys() - old.keys()), sorted(old.keys() - new.keys())
    for title, ids in (("Rules added", added), ("Rules removed", removed)):
        named = [f"- {r}: {(new.get(r) or old[r])['name'].strip('"')}" for r in ids]
        lines += [f"## {title}", *(named or ["- none"]), ""]
    changed = sorted(r for r in old.keys() & new.keys() if old[r] != new[r])
    lines += ["## Rules changed", *([] if changed else ["- none"])]
    for r in changed:
        keys = sorted(k for k in old[r].keys() | new[r].keys() if old[r].get(k) != new[r].get(k))
        lines += [
            f"- {r}: {new[r]['name'].strip('"')}",
            *(f"  - {k}: {old[r].get(k)} -> {new[r].get(k)}" for k in keys),
        ]
    lines += ["", "## Skill files changed", *(f"- {f}" for f in files_changed), *([] if files_changed else ["- none"])]
    return "\n".join([*lines, "", f"{SKILL_TEXT}git -C {clone} diff {pinned} {to} -- {SKILL}"])


def skill_diff(clone: Path, to: str) -> str:
    """Upstream's skill text from the pinned commit to *to*, as one unified diff: what that last line shows."""
    return _git(clone, "diff", pinned_commit(clone), to, "--", SKILL)


def golden(
    installed: Installed, folder: Traversable | None = None, *, pages: bool = True
) -> dict[str, dict[str, list[str]]]:
    """Each fixture page whose rules differ from the expected ones: what was unexpected and what was missing.

    The engine scans the pages' source; with *pages*, the pack's bundle also scans them rendered. Keyed by page and
    mode, such as ``bad.html (page)``. *folder* holds a candidate's pages and expectations; the package's by default.
    """
    folder = folder or files("owlbear_delivery_next").joinpath("golden")
    expected: dict[str, dict[str, list[str]]] = json.loads(folder.joinpath("expected.json").read_text("utf-8"))
    names = list(expected["source"])
    if bad := [n for n in {*names, *(n for mode in expected.values() for n in mode)} if not PAGE.fullmatch(n)]:
        msg = f"golden/expected.json names pages that are no page file of its folder: {', '.join(sorted(bad)[:5])}"
        raise pack_files.PackError(msg)  # a candidate's names are read and written only inside the folders
    if unknown := sorted({n for mode in expected.values() for n in mode} - set(names)):
        msg = f"golden/expected.json has expectations for pages it does not scan by source: {', '.join(unknown[:5])}"
        raise pack_files.PackError(msg)
    with tempfile.TemporaryDirectory(prefix="owlbear-golden-") as tmp:
        root = Path(tmp).resolve()
        for name in names:
            (root / name).write_bytes(folder.joinpath(name).read_bytes())
        seen = {
            "source": _by_source(installed, root, names),
            **({"page": _in_pages(installed, root, names)} if pages else {}),
        }
    return {
        f"{name} ({mode})": {"unexpected": sorted(found[name] - set(want)), "missing": sorted(set(want) - found[name])}
        for mode, found in seen.items()
        for name, want in expected[mode].items()
        if found[name] != set(want)
    }


def _by_source(installed: Installed, root: Path, names: list[str]) -> dict[str, set[str]]:
    seen: dict[str, set[str]] = {n: set() for n in names}
    for f in detector.scan_source(installed, [root / n for n in names], root):
        seen.setdefault(f.where.removeprefix(f"{root}/").split(":")[0], set()).add(f.rule)
    return seen


def _in_pages(installed: Installed, root: Path, names: list[str]) -> dict[str, set[str]]:
    from playwright.sync_api import Error, sync_playwright  # noqa: PLC0415 - optional browser runtime

    seen = {}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                for name in names:
                    tab = browser.new_page(viewport={"width": 1280, "height": 800})
                    tab.goto((root / name).as_uri())
                    seen[name] = {f.rule for f in detector.scan_page(tab, installed)}
                    tab.close()
            finally:
                browser.close()
    except Error as exc:
        msg = f"the golden pages did not render: {exc}"
        raise detector.DetectorError(msg) from exc
    return seen
