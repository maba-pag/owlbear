"""Behavioral tests for the development-only Archify diagram toolchain."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_DIAGRAM_SCRIPTS = _ROOT / ".owlbear/scripts/diagrams"
_SYNC_PATH = _DIAGRAM_SCRIPTS / "sync.py"
_RENDER_PATH = _DIAGRAM_SCRIPTS / "render.py"
_REQUIRED_FILES = (
    "archify/bin/archify.mjs",
    "archify/assets/template.html",
    "archify/renderers/architecture/render-architecture.mjs",
    "archify/schemas/architecture.schema.json",
)


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def sync_module() -> ModuleType:
    return _load_module("archify_sync_test", _SYNC_PATH)


@pytest.fixture
def render_module() -> ModuleType:
    return _load_module("archify_render_test", _RENDER_PATH)


def _release_archive(path: Path, *, unsafe_name: str | None = None) -> bytes:
    with zipfile.ZipFile(path, "w") as archive:
        if unsafe_name is not None:
            archive.writestr(unsafe_name, "unsafe")
        for relative in _REQUIRED_FILES:
            archive.writestr(relative, "placeholder")
    return path.read_bytes()


def _lock(path: Path, digest: str) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "repository": "tt-a1i/archify",
                "asset": "archify.zip",
                "version": "v2.16.0",
                "sha256": digest,
            }
        ),
        encoding="utf-8",
    )


def test_ensure_archify_installs_verified_archive_and_reuses_offline_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sync_module: ModuleType,
) -> None:
    archive_path = tmp_path / "archify.zip"
    archive_bytes = _release_archive(archive_path)
    digest = hashlib.sha256(archive_bytes).hexdigest()
    lock_path = tmp_path / "archify.lock.json"
    cache_root = tmp_path / "cache/archify"
    _lock(lock_path, digest)
    downloads: list[str] = []

    def download(_url: str, destination: Path) -> None:
        downloads.append(_url)
        shutil.copyfile(archive_path, destination)

    monkeypatch.setattr(sync_module, "_download", download)
    first = sync_module.ensure_archify(lock_path, cache_root)
    assert first == cache_root / "v2.16.0/archify"
    assert (first / "bin/archify.mjs").is_file()
    assert len(downloads) == 1

    monkeypatch.setattr(sync_module, "_download", pytest.fail)
    second = sync_module.ensure_archify(lock_path, cache_root, offline=True)
    assert second == first


def test_ensure_archify_rejects_digest_drift_without_populating_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sync_module: ModuleType,
) -> None:
    archive_path = tmp_path / "archify.zip"
    _release_archive(archive_path)
    lock_path = tmp_path / "archify.lock.json"
    cache_root = tmp_path / "cache/archify"
    _lock(lock_path, "0" * 64)
    monkeypatch.setattr(sync_module, "_download", lambda _url, destination: shutil.copyfile(archive_path, destination))

    with pytest.raises(sync_module.SyncError, match="digest mismatch"):
        sync_module.ensure_archify(lock_path, cache_root)
    assert not (cache_root / "v2.16.0").exists()


def test_extract_archive_rejects_unsafe_zip_paths(tmp_path: Path, sync_module: ModuleType) -> None:
    archive_path = tmp_path / "unsafe.zip"
    _release_archive(archive_path, unsafe_name="../outside.txt")

    with pytest.raises(sync_module.SyncError, match="unsafe ZIP path"):
        sync_module._extract_archive(archive_path, tmp_path / "extracted")  # noqa: SLF001
    assert not (tmp_path / "outside.txt").exists()


def test_standalone_svg_preserves_static_root_and_filters_viewer_css(render_module: ModuleType) -> None:
    html = """<!DOCTYPE html>
<html><head><style>
    [data-theme="light"] { --grid: #eee; }
    @media print { [data-theme="light"] { --grid: transparent; } }
  .c-grid { stroke: var(--grid); }
  .toolbar { display: flex; }
</style></head><body>
<svg viewBox="0 0 320 240" role="img" data-preset="classic"><path class="c-grid" /></svg>
</body></html>"""

    output = render_module._standalone_svg(html, "light")  # noqa: SLF001

    assert output.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert 'xmlns="http://www.w3.org/2000/svg"' in output
    assert 'data-theme="light"' in output
    assert ".c-grid" in output
    assert "--grid: #eee" in output
    assert "--grid: transparent" not in output
    assert "@media" not in output
    assert ".toolbar" not in output
    assert output.count("<svg ") == 1


def test_standalone_svg_rejects_css_without_static_rules(render_module: ModuleType) -> None:
    html = """<!DOCTYPE html>
<html><head><style>
  @media print { .toolbar { display: none; } }
</style></head><body>
<svg viewBox="0 0 320 240" role="img"></svg>
</body></html>"""

    with pytest.raises(render_module.RenderError, match="usable static SVG CSS"):
        render_module._standalone_svg(html, "light")  # noqa: SLF001


def test_standalone_svg_rejects_unmapped_svg_class(render_module: ModuleType) -> None:
    html = """<!DOCTYPE html>
<html><head><style>
  .c-grid { stroke: #eee; }
</style></head><body>
<svg viewBox="0 0 320 240" role="img"><path class="c-grid future-class" /></svg>
</body></html>"""

    with pytest.raises(render_module.RenderError, match="lack retained CSS selectors"):
        render_module._standalone_svg(html, "light")  # noqa: SLF001


def test_render_diagram_validates_then_atomically_writes_svg(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    render_module: ModuleType,
) -> None:
    archify_root = tmp_path / "archify"
    cli = archify_root / "bin/archify.mjs"
    cli.parent.mkdir(parents=True)
    cli.write_text("#!/usr/bin/env node\n", encoding="utf-8")
    source = tmp_path / "diagram.json"
    source.write_text("{}\n", encoding="utf-8")
    output = tmp_path / "diagram.svg"

    calls: list[list[str]] = []

    def run_node(command: list[str], *, cwd: Path) -> object:
        calls.append(command)
        assert cwd == archify_root
        if command[1] == "validate":
            return render_module.subprocess.CompletedProcess(command, 0, json.dumps({"ok": True}), "")
        html_path = Path(command[4])
        html_path.write_text(
            "<html><head><style>.c-grid { stroke: #eee; }</style></head>"
            '<body><svg viewBox="0 0 320 240" role="img"><path class="c-grid" /></svg></body></html>',
            encoding="utf-8",
        )
        return render_module.subprocess.CompletedProcess(command, 0, "", "")

    def fake_ensure_archify(*, offline: bool = False) -> Path:
        assert offline is False
        return archify_root

    monkeypatch.setattr(render_module, "ensure_archify", fake_ensure_archify)
    monkeypatch.setattr(render_module.shutil, "which", lambda _name: "/usr/bin/node")
    monkeypatch.setattr(render_module, "_run_node", run_node)

    render_module.render_diagram(source, output)

    assert output.is_file()
    assert 'xmlns="http://www.w3.org/2000/svg"' in output.read_text(encoding="utf-8")
    assert [command[1] for command in calls] == ["validate", "render"]
