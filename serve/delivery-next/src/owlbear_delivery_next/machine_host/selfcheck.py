"""``python -m owlbear_delivery_next selfcheck``: whether this version can take over the machine (self-update §5.1).

Run by an update with the new version's own interpreter, before anything switches: its modules import, its pages and
their assets are there, and every registered project's store and settings are in a format it reads. It only reads:
no store is opened for writing and nothing migrates. Exit 0 when it passes, else 1 with one line per failure.
"""

from __future__ import annotations

import contextlib
import json
import re
import sys
from importlib import import_module
from importlib.resources import files
from pathlib import Path

IMPORT = r"""(?:\bfrom|\bimport)\s*\(?\s*["']\./([^"'/]+)["']"""  # a page module's import of a sibling module
MODULES = (
    "machine_host.serve", "machine_host.app", "commands.runner", "commands.mcp_server", "project_host.api",
    "project_host.pages",
)  # fmt: skip


def problems() -> list[str]:
    """What keeps this version from serving the machine's projects; empty when nothing does."""
    found = []
    for name in MODULES:
        try:
            import_module(f"owlbear_delivery_next.{name}")
        except Exception as exc:  # noqa: BLE001 - every import failure is reported, none ends the check
            found.append(f"{name} does not import: {type(exc).__name__}: {exc}")
    found += _pages()
    try:
        projects = _registered()
    except ValueError as exc:
        return [*found, str(exc)]
    found += _formats("this machine's settings", [_home() / "settings.json"])
    for pid, path in projects:
        found += [f"{path}: {said}" for said in _project(pid, path)]
    return found


def _home() -> Path:
    from owlbear_delivery_next.local_system import local_home  # noqa: PLC0415 - checked above

    return local_home.root()


def _registered() -> list[tuple[str, Path]]:
    """The registered projects, read from ``machine.json`` without creating anything.

    Raises:
        ValueError: It is unreadable, or newer than this version reads.
    """
    from owlbear_delivery_next.machine_host import registry  # noqa: PLC0415 - checked above

    path = _home() / registry.MACHINE
    if not path.is_file():
        return []
    try:
        machine = registry.Machine.model_validate_json(path.read_text())
    except (OSError, ValueError) as exc:
        msg = f"{path} is unreadable: {exc}"
        raise ValueError(msg) from exc
    if machine.format > registry.MACHINE_FORMAT:
        msg = f"{path} has format {machine.format}, newer than this version's {registry.MACHINE_FORMAT}"
        raise ValueError(msg)
    return [(p.id, Path(p.path)) for p in machine.projects]


def _pages() -> list[str]:
    """Every page and every asset the pages load: the design system, lit-html, ``ui.mjs`` and each page's modules."""
    from owlbear_delivery_next.project_host import pages  # noqa: PLC0415 - checked above

    web = files("owlbear_delivery_next").joinpath("web")
    try:
        listed = pages.pages()
        names = [("pds", n) for n in pages.PDS] + [(pages.LIT, *n.split("/")) for n in pages.lit_files()]
        pages.lit_version()
        own = pages.page_files()
        named = {tuple(n) for html in listed.values() for n in re.findall(r'"/assets/page/([^/"]+)/([^/"]+)"', html)}
        for page, name in own:
            module = web.joinpath("pages", page, name).read_text(encoding="utf-8")
            named |= {(page, n) for n in re.findall(IMPORT, module)}  # a module's own imports must be there too
        missing = ["/".join(n) for n in [*names, ("ui.mjs",)] if not web.joinpath(*n).is_file()]
        missing += [f"pages/{p}/{n}" for p, n in sorted(named - set(own))]
    except Exception as exc:  # noqa: BLE001 - reported
        return [f"the pages cannot be read: {type(exc).__name__}: {exc}"]
    if not listed:
        return ["no page is there"]
    return [f"the pages' assets are missing: {', '.join(missing[:5])}"] if missing else []


def _project(pid: str, path: Path) -> list[str]:
    """A registered project's store and settings formats, read without opening or migrating anything."""
    from owlbear_delivery_next.state_store import project_home  # noqa: PLC0415
    from owlbear_delivery_next.state_store.database import MARKER, STORE_FORMAT  # noqa: PLC0415
    from owlbear_delivery_next.state_store.project_move import FENCE  # noqa: PLC0415

    markers = [project_home.home(pid) / MARKER]
    found, clone = [], None
    if path.is_dir():
        with contextlib.suppress(Exception):  # a clone that is gone fails to load as before; not this check's
            clone = project_home.clone_dir(path)
            markers.append(clone / MARKER)
    for marker in markers:
        try:
            value = int(marker.read_text()) if marker.is_file() else 0
        except OSError, ValueError:
            found.append(f"{marker} is unreadable")
            continue
        if value > STORE_FORMAT:
            if clone is not None and marker == clone / MARKER and value == int(FENCE):
                if (problem := _retained(pid, clone)) is None:
                    continue  # the fenced clone is a retained source; the project's store is checked instead
                found.append(problem)
                continue
            found.append(f"its store has format {value}, newer than this version's {STORE_FORMAT}")
    layers = [project_home.home(pid) / "config.json", *([clone / "config.json"] if clone else []), *_shared(path)]
    return found + _formats("its settings", layers)


def _retained(pid: str, clone: Path) -> str | None:
    """None when the fenced *clone* is a retained source whose SWITCHED receipt names the project's store; else why."""
    from owlbear_delivery_next.state_store import switched_authority  # noqa: PLC0415
    from owlbear_delivery_next.state_store.database import STORE_FORMAT, StoreError  # noqa: PLC0415
    from owlbear_delivery_next.state_store.project_move import FENCE  # noqa: PLC0415

    try:
        if switched_authority.retained_target(clone, pid) is not None:
            return None
    except StoreError as exc:
        return str(exc)
    return f"its store has format {FENCE}, newer than this version's {STORE_FORMAT} and no completed move names it"


def _shared(path: Path) -> list[Path]:
    """The shared repository's global layer and the project's layer there, found without moving anything."""
    from owlbear_delivery_next.local_system import data_repo  # noqa: PLC0415

    with contextlib.suppress(Exception):  # no shared repository, or one that cannot be read: the host says so
        root = Path(json.loads(data_repo.pointer().read_text())["repository"]).expanduser().resolve()
        shared = data_repo.DataRepo(root)
        return [shared.global_path, shared.project_path(data_repo.folder(shared, path))]
    return []


def _formats(what: str, layers: list[Path]) -> list[str]:
    from owlbear_delivery_next.settings.config import CONFIG_FORMAT  # noqa: PLC0415

    found = []
    for layer in layers:
        try:
            value = int(json.loads(layer.read_text()).get("format", 0)) if layer.is_file() else 0
        except OSError, ValueError, AttributeError:
            found.append(f"{layer} is unreadable")
            continue
        if value > CONFIG_FORMAT:
            found.append(f"{what} in {layer} have format {value}, newer than this version's {CONFIG_FORMAT}")
    return found


def main(_argv: list[str] | None = None) -> int:
    """Print each problem; 0 when there is none."""
    found = problems()
    for line in found:
        sys.stdout.write(f"{line}\n")
    if not found:
        sys.stdout.write("selfcheck passed\n")
    return 1 if found else 0
