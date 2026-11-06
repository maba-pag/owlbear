"""The readable Spotter records, with optional diagnostics for partial reads."""

from __future__ import annotations

import json
from typing import Any

from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.improvement import acts, spotter


def records(*, unread: list[str] | None = None) -> list[dict[str, Any]]:
    """Keep valid records and acts even when another file or JSONL line cannot be read."""
    found, done = [], acts.acts(spotter.place())
    for path in sorted(spotter.place().glob("records-*.jsonl")):
        try:
            lines = path.read_text().splitlines()
        except (OSError, UnicodeError) as exc:
            if unread is not None:
                unread.append(f"{path}: {failure(exc)}")
            continue
        for number, line in enumerate(lines, 1):
            try:
                record = json.loads(line)
            except ValueError as exc:
                if unread is not None:
                    unread.append(f"{path}, line {number}: {failure(exc)}")
                continue
            if isinstance(record, dict) and record.get("id"):
                found.append(record | (acts.joined(done[record["id"]]) if record["id"] in done else {}))
    return found
