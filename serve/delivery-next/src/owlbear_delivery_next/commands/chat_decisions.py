"""Match a chat's decision-save receipt to its submitted wording, layer and time."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def same(row: dict[str, Any], body: dict[str, Any]) -> bool:
    """The row has the sent wording and the layer it is saved in."""
    wording = (row["title"].strip(), row["statement"].strip())
    return wording == (body["title"].strip(), body["statement"].strip()) and row["scope"] in _layers(body)


def new(row: dict[str, Any], body: dict[str, Any], started: datetime) -> bool:
    """The row was made since the call started, in the layer the save is made in: it may be this save, edited since."""
    return row["scope"] in _layers(body) and datetime.fromisoformat(row["created_at"]) >= started


def _layers(body: dict[str, Any]) -> set[str]:
    """Global, else a project for a new decision, or the project or Change of the decision it replaces."""
    return {"global"} if body["scope"] == "global" else {"project", "change"} if body.get("replaces") else {"project"}


def ids(rows: list[dict[str, Any]]) -> str:
    """The ids a matching receipt names."""
    return ", ".join(d["id"] for d in rows)
