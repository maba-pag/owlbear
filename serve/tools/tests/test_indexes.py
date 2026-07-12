"""Tests for the combined index generator."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path

from owlbear_tools.indexes import generate_indexes


def test_generates_all_indexes_without_recursive_entries(tmp_path: Path) -> None:
    source = tmp_path / "src/example.py"
    source.parent.mkdir(parents=True)
    source.write_text('"""Example."""\n\ndef run() -> None:\n    pass\n')
    component = tmp_path / "web/example.ts"
    component.parent.mkdir(parents=True)
    component.write_text("export function run(): void {}\n")
    readme = tmp_path / "README.md"
    readme.write_text("# Example\n")

    generate_indexes(tmp_path)
    generate_indexes(tmp_path)

    index_dir = tmp_path / ".owlbear"
    assert {path.name for path in index_dir.iterdir()} == {"doc-index.md", "py-index.md", "ts-index.md"}
    doc_index = (index_dir / "doc-index.md").read_text()
    assert "## README.md" in doc_index
    assert "## .owlbear/py-index.md" not in doc_index
    assert "## .owlbear/ts-index.md" not in doc_index
    assert "## src/example.py" in (index_dir / "py-index.md").read_text()
    assert "## web/example.ts" in (index_dir / "ts-index.md").read_text()


def test_indexes_entry_point_is_registered() -> None:
    names = {entry.name for entry in importlib.metadata.entry_points(group="console_scripts")}
    assert "indexes" in names
