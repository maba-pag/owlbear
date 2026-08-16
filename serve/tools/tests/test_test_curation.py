"""Behavioral tests for the test-curation inventory command."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from owlbear_tools.test_curation import inventory


def _write_manifest(root: Path, records: list[tuple[str, bytes | None, str | None]]) -> None:
    manifest_root = root / ".owlbear/legacy/target-cutover/kanban"
    manifest_root.mkdir(parents=True)
    manifest_records: list[dict[str, str]] = []
    for relative_path, content, expected_hash in records:
        path = manifest_root / relative_path
        if content is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        manifest_records.append(
            {
                "relative_path": relative_path,
                "sha256": expected_hash or hashlib.sha256(content or b"").hexdigest(),
            }
        )
    (manifest_root / "manifest.json").write_text(json.dumps({"files": manifest_records}), encoding="utf-8")


def _write_pytest_config(root: Path) -> None:
    (root / "pyproject.toml").write_text('[tool.pytest.ini_options]\ntestpaths = ["tests"]\n', encoding="utf-8")


def test_inventory_uses_filename_and_header_signals_but_ignores_mined_header(tmp_path: Path) -> None:
    _write_pytest_config(tmp_path)
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_filename_1234.py").write_text("from __future__ import annotations\n", encoding="utf-8")
    (tests / "test_header.py").write_text(
        '"""RED phase tests for #1234."""\nfrom __future__ import annotations\n',
        encoding="utf-8",
    )
    (tests / "test_mined.py").write_text(
        '"""Mined from #1234: durable behavior."""\nfrom __future__ import annotations\n',
        encoding="utf-8",
    )
    _write_manifest(tmp_path, [("content/archive/1234-feature.md", b"archived", None)])

    document = inventory(tmp_path)

    assert document["counts"] == {
        "total": 2,
        "verified": 2,
        "unverified": 0,
        "missing": 0,
        "python": 2,
        "frontend": 0,
        "e2e": 0,
    }
    candidates = {candidate["path"]: candidate for candidate in document["candidates"]}
    assert candidates["tests/test_filename_1234.py"]["signals"] == ("filename",)
    assert candidates["tests/test_header.py"]["signals"] == ("header",)
    assert "tests/test_mined.py" not in candidates


def test_inventory_distinguishes_unverified_and_missing_provenance(tmp_path: Path) -> None:
    _write_pytest_config(tmp_path)
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_unverified_1235.py").write_text("from module import value\n", encoding="utf-8")
    (tests / "test_missing_1236.py").write_text("from module import value\n", encoding="utf-8")
    _write_manifest(
        tmp_path,
        [
            ("content/archive/1235-feature.md", b"changed", "0" * 64),
        ],
    )

    document = inventory(tmp_path)

    assert document["counts"]["unverified"] == 1
    assert document["counts"]["missing"] == 1
    candidates = {candidate["path"]: candidate for candidate in document["candidates"]}
    assert candidates["tests/test_unverified_1235.py"]["provenance"] == "unverified"
    assert candidates["tests/test_missing_1236.py"]["provenance"] == "missing"
