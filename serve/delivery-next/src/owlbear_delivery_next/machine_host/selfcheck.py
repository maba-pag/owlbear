"""``python -m owlbear_delivery_next selfcheck``: whether this version can take over the machine (self-update §5.1).

Run by an update with the new version's own interpreter, before anything switches: its modules import, its pages and
their assets are there, and every registered project's store and settings are in a format it reads. It only reads:
no store is opened for writing and nothing migrates. Exit 0 when it passes, else 1 with one line per failure.
"""

from __future__ import annotations

import contextlib
import json
import sys
from importlib import import_module
from importlib.resources import files
from pathlib import Path

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
    from owlbear_delivery_next.machine_host import registry  # noqa: PLC0415 - after the imports were checked

    try:
        machine = registry.load()
    except registry.RegistryError as exc:
        return [*found, str(exc)]
    for entry in machine.projects:
        found += [f"{entry.path}: {said}" for said in _project(entry.id, Path(entry.path))]
    return found


def _pages() -> list[str]:
    from owlbear_delivery_next.project_host import pages  # noqa: PLC0415 - checked above

    try:
        listed = pages.pages()
    except Exception as exc:  # noqa: BLE001 - reported
        return [f"the pages cannot be read: {type(exc).__name__}: {exc}"]
    web = files("owlbear_delivery_next").joinpath("web")
    return [] if listed and web.is_dir() else ["the pages or their assets are missing"]


def _project(pid: str, path: Path) -> list[str]:
    """A registered project's store and settings formats, read without opening or migrating anything."""
    from owlbear_delivery_next.settings.config import CONFIG_FORMAT  # noqa: PLC0415
    from owlbear_delivery_next.state_store import project_home  # noqa: PLC0415
    from owlbear_delivery_next.state_store.database import MARKER, STORE_FORMAT  # noqa: PLC0415

    found = []
    markers = [project_home.home(pid) / MARKER]
    if path.is_dir():
        with contextlib.suppress(Exception):  # a clone that is gone fails to load as before; not this check's
            markers.append(project_home.clone_dir(path) / MARKER)
    for marker in markers:
        try:
            value = int(marker.read_text()) if marker.is_file() else 0
        except OSError, ValueError:
            found.append(f"{marker} is unreadable")
            continue
        if value > STORE_FORMAT:
            found.append(f"its store has format {value}, newer than this version's {STORE_FORMAT}")
    config = project_home.home(pid) / "config.json"
    try:
        value = int(json.loads(config.read_text()).get("format", 0)) if config.is_file() else 0
    except OSError, ValueError, AttributeError:
        return [*found, f"{config} is unreadable"]
    if value > CONFIG_FORMAT:
        found.append(f"its settings have format {value}, newer than this version's {CONFIG_FORMAT}")
    return found


def main(_argv: list[str] | None = None) -> int:
    """Print each problem; 0 when there is none."""
    found = problems()
    for line in found:
        sys.stdout.write(f"{line}\n")
    if not found:
        sys.stdout.write("selfcheck passed\n")
    return 1 if found else 0
