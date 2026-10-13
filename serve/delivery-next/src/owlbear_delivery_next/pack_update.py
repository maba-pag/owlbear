"""Updating the design pack (design skill research §3.5, update procedure; TD-76): the tooling before the first update.

1. Notice: how many skill releases upstream is ahead of the pinned tag; offline is "unknown", never a failure.
2. Diff: rules added, removed and changed, and skill files changed, between the pinned tag and a candidate, read
   from a local clone of upstream; the owner chooses what to adopt in a direct chat.
3. Golden pages: an engine must find exactly the expected rules on Delivery's fixture pages.
4. Calibration replay: ``pack_replay`` reruns the design judge on decided rounds; ``calibration.replayed`` compares.
5. Activation: a pack is the package's manifest and skills; a reviewed commit switches it in one step, and reverting
   that commit rolls the whole pack back. Each pack installs into its own folder, so a rollback needs no download.
"""

from __future__ import annotations

import contextlib
import json
import re
import subprocess
import tempfile
from datetime import UTC, datetime, timedelta
from http.client import HTTPException
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next import design_pack, detector

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.design_pack import Installed

RELEASES = "https://api.github.com/repos/{repo}/releases?per_page=100"
NOTICE = "notice.json"  # beside the installed packs
STALE = timedelta(days=1)
SECONDS = 10.0  # the notice's one request: the readiness check at host start never waits long for it
REGISTRY = "crates/foundation/src/registry.rs"  # upstream's rule registry
TABLE = "pub static ANTIPATTERNS"  # its rule table, ended by the first line "];"
SKILL = "skill"  # upstream's skill text
ENTRY = re.compile(r"^ {4}Antipattern \{\n(?P<body>.*?)^ {4}\},?$", re.DOTALL | re.MULTILINE)  # rustfmt's layout
FIELD = re.compile(r"^ {8}(?P<key>\w+): (?P<value>.*?),?\s*(?=^ {8}\w+: |\Z)", re.DOTALL | re.MULTILINE)


def _version(tag: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", tag))


def behind(fetch: Callable[[str], bytes] | None = None) -> int | None:
    """Skill releases among upstream's newest 100 that are newer than the pinned tag; None when unreadable."""
    upstream = design_pack.manifest()["upstream"]
    url = RELEASES.format(repo=upstream["repository"])
    try:
        releases = json.loads(fetch(url) if fetch else design_pack.fetch(url, SECONDS))
    except OSError, ValueError, HTTPException:
        return None
    if not isinstance(releases, list):
        return None
    tags = [r.get("tag_name") for r in releases if isinstance(r, dict) and not r.get("prerelease")]
    pinned = _version(upstream["tag"])
    return sum(1 for t in tags if isinstance(t, str) and t.startswith("skill-v") and _version(t) > pinned)


def notice(*, refresh: bool, fetch: Callable[[str], bytes] | None = None) -> dict[str, Any]:
    """The last check of upstream for the pinned tag, refreshed at most daily when asked; reading never goes online."""
    pack, tag = design_pack.manifest()["pack"], design_pack.manifest()["upstream"]["tag"]
    path, unknown = design_pack.folder().parent / NOTICE, {"behind": None, "checked_at": None}
    kept: Any = unknown
    try:
        kept = json.loads(path.read_text(encoding="utf-8"))
        checked = datetime.fromisoformat(kept["checked_at"]) if kept.get("tag") == tag else None
    except OSError, ValueError, KeyError, TypeError, AttributeError:
        checked = None
    kept = kept if checked else unknown  # another pack's count says nothing about this one
    if refresh and (checked is None or datetime.now(UTC) - checked > STALE):
        if (found := behind(fetch)) is None:  # offline: unknown now, also to the settings page, and checked next time
            with contextlib.suppress(OSError):
                path.unlink(missing_ok=True)
            return {"pack": pack, **unknown}
        kept = {"tag": tag, "behind": found, "checked_at": datetime.now(UTC).isoformat(timespec="seconds")}
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(kept) + "\n", encoding="utf-8")
        except OSError:
            pass  # the notice is a hint; it is checked again next time
    return {"pack": pack, "behind": kept["behind"], "checked_at": kept["checked_at"]}


def said(n: dict[str, Any]) -> str:
    """The notice in words, for setup and the settings page."""
    if n.get("behind") is None:
        return f"design pack {n['pack']}: releases upstream unknown"
    return f"design pack {n['pack']}: {n['behind']} release{'s' if n['behind'] != 1 else ''} behind"


def _git(clone: Path, *args: str) -> str:
    command = ["git", *args]
    done = subprocess.run(command, cwd=clone, capture_output=True, text=True, check=True, timeout=60)  # noqa: S603
    return done.stdout


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
    """
    pinned = design_pack.manifest()["upstream"]["tag"]
    old, new = rules(clone, pinned), rules(clone, to)
    files_changed = _git(clone, "diff", "--name-status", pinned, to, "--", SKILL).splitlines()
    lines = [f"# Design pack update: {pinned} to {to}", ""]
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
    return "\n".join([*lines, "", f"Skill text: git -C {clone} diff {pinned} {to} -- {SKILL}"])


def golden(installed: Installed, *, pages: bool = True) -> dict[str, dict[str, list[str]]]:
    """Each fixture page whose rules differ from the expected ones: what was unexpected and what was missing.

    The engine scans the pages' source; with *pages*, the pack's bundle also scans them rendered. Keyed by page and
    mode, such as ``bad.html (page)``.
    """
    folder = files("owlbear_delivery_next").joinpath("golden")
    expected: dict[str, dict[str, list[str]]] = json.loads(folder.joinpath("expected.json").read_text("utf-8"))
    names = list(expected["source"])
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
