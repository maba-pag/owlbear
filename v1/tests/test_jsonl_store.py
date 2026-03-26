"""Tests for owlbear.core.jsonl_store — JsonlStore[T] generic base class."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from owlbear.core.jsonl_store import JsonlStore


class _Item(BaseModel):
    """Trivial model for testing the generic store."""

    name: str
    value: int


_adapter: TypeAdapter[_Item] = TypeAdapter(_Item)


# ---------------------------------------------------------------------------
# Construction & path property
# ---------------------------------------------------------------------------


class TestJsonlStoreInit:
    """JsonlStore constructor stores path and creates a TypeAdapter."""

    def test_path_property_returns_stored_path(self, tmp_path: Path) -> None:
        p = tmp_path / "items.jsonl"
        store = JsonlStore(p, _Item)
        assert store.path == p

    def test_accepts_nested_path(self, tmp_path: Path) -> None:
        p = tmp_path / "a" / "b" / "items.jsonl"
        store = JsonlStore(p, _Item)
        assert store.path == p


# ---------------------------------------------------------------------------
# Append
# ---------------------------------------------------------------------------


class TestJsonlStoreAppend:
    """JsonlStore.append() writes one JSON line per record."""

    def test_append_creates_file(self, tmp_path: Path) -> None:
        p = tmp_path / "items.jsonl"
        store = JsonlStore(p, _Item)
        store.append(_Item(name="a", value=1))
        assert p.exists()

    def test_append_writes_one_line(self, tmp_path: Path) -> None:
        p = tmp_path / "items.jsonl"
        store = JsonlStore(p, _Item)
        store.append(_Item(name="a", value=1))
        lines = p.read_text().strip().splitlines()
        assert len(lines) == 1

    def test_append_writes_valid_json(self, tmp_path: Path) -> None:
        p = tmp_path / "items.jsonl"
        store = JsonlStore(p, _Item)
        store.append(_Item(name="hello", value=42))
        data = json.loads(p.read_text().strip())
        assert data["name"] == "hello"
        assert data["value"] == 42

    def test_append_multiple_records(self, tmp_path: Path) -> None:
        p = tmp_path / "items.jsonl"
        store = JsonlStore(p, _Item)
        for i in range(3):
            store.append(_Item(name=f"item-{i}", value=i))
        lines = p.read_text().strip().splitlines()
        assert len(lines) == 3

    def test_append_creates_parent_dirs(self, tmp_path: Path) -> None:
        p = tmp_path / "sub" / "dir" / "items.jsonl"
        store = JsonlStore(p, _Item)
        store.append(_Item(name="nested", value=99))
        assert p.exists()


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------


class TestJsonlStoreLoad:
    """JsonlStore.load() reads all records from the JSONL file."""

    def test_load_returns_records(self, tmp_path: Path) -> None:
        p = tmp_path / "items.jsonl"
        _write(p, [_Item(name="a", value=1), _Item(name="b", value=2)])
        store = JsonlStore(p, _Item)
        loaded = store.load()
        assert len(loaded) == 2
        assert all(isinstance(r, _Item) for r in loaded)

    def test_load_preserves_field_values(self, tmp_path: Path) -> None:
        p = tmp_path / "items.jsonl"
        _write(p, [_Item(name="test", value=999)])
        store = JsonlStore(p, _Item)
        loaded = store.load()
        assert loaded[0].name == "test"
        assert loaded[0].value == 999

    def test_load_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        p = tmp_path / "items.jsonl"
        p.write_text("")
        store = JsonlStore(p, _Item)
        assert store.load() == []

    def test_load_nonexistent_file_returns_empty_list(self, tmp_path: Path) -> None:
        store = JsonlStore(tmp_path / "nope.jsonl", _Item)
        assert store.load() == []


# ---------------------------------------------------------------------------
# Round-trip: append then load
# ---------------------------------------------------------------------------


class TestJsonlStoreRoundTrip:
    """append() followed by load() round-trips correctly."""

    def test_round_trip_single(self, tmp_path: Path) -> None:
        p = tmp_path / "items.jsonl"
        store = JsonlStore(p, _Item)
        store.append(_Item(name="rt", value=7))
        loaded = store.load()
        assert len(loaded) == 1
        assert loaded[0].name == "rt"
        assert loaded[0].value == 7

    def test_round_trip_multiple(self, tmp_path: Path) -> None:
        p = tmp_path / "items.jsonl"
        store = JsonlStore(p, _Item)
        items = [_Item(name=f"n{i}", value=i) for i in range(5)]
        for item in items:
            store.append(item)
        loaded = store.load()
        assert len(loaded) == 5
        assert [r.value for r in loaded] == [0, 1, 2, 3, 4]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, items: list[_Item]) -> None:
    """Manually write items as JSONL for test fixtures."""
    with path.open("w", encoding="utf-8") as fh:
        for item in items:
            fh.write(_adapter.dump_json(item).decode("utf-8") + "\n")
