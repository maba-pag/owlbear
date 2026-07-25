"""Activity stream append/query/compact for kanban boards (Brief C §7).

Provides three functions over the board-level ``activity.jsonl`` file:
- ``append_activity_event``  — append one ActivityEvent record
- ``list_activity_events``   — query events with optional filters
- ``compact_activity_log``   — rewrite the file retaining only recent events

The canonical source vocabulary for activity attribution is:
- ``engine`` for internal engine operations
- ``agent`` for agent-initiated operations
- ``cockpit`` for Cockpit UI-initiated operations
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003

from owlbear_kanban.models import ActivityCompactionResult, ActivityEvent
from owlbear_kanban.storage_io import atomic_write

_ACTIVITY_FILE = "activity.jsonl"
_HARD_FLOOR = 500  # always keep the last N entries


def append_activity_event(event: ActivityEvent, kanban_dir: Path) -> None:
    """Append *event* as a single JSON line to ``activity.jsonl``.

    The file is created if absent (AC-C42).

    Args:
        event:      Activity event to record.
        kanban_dir: Root directory of the kanban board.
    """
    activity_path = kanban_dir / _ACTIVITY_FILE
    line = json.dumps(event.model_dump()) + "\n"
    with activity_path.open("a", encoding="utf-8") as fh:
        fh.write(line)


def list_activity_events(  # noqa: C901, PLR0912, PLR0913
    kanban_dir: Path,
    *,
    task_id: int | None = None,
    action: str | None = None,
    source: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int | None = None,
) -> list[ActivityEvent]:
    """Return activity events from ``activity.jsonl`` with optional filters.

    Reads only the ``activity.jsonl`` file — never task ``.md`` files (AC-C44).

    Args:
        kanban_dir: Root directory of the kanban board.
        task_id:    Only return events for this task ID.
        action:     Only return events with this action string.
        source:     Only return events with this source string.
        since:      ISO-8601 datetime; only return events at or after this.
        until:      ISO-8601 datetime; only return events at or before this.
        limit:      Maximum number of events to return.

    Returns:
        List of :class:`ActivityEvent` objects matching the filters.
    """
    activity_path = kanban_dir / _ACTIVITY_FILE
    if not activity_path.exists():
        return []

    since_dt = _parse_dt(since)
    until_dt = _parse_dt(until)

    events: list[ActivityEvent] = []
    text = activity_path.read_text(encoding="utf-8")
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        # Accept only canonical activity rows.
        if not all(k in data for k in ("timestamp", "action", "source", "detail")):
            continue
        if not isinstance(data.get("detail"), str):
            continue

        if task_id is not None and data.get("task_id") != task_id:
            continue
        if action == "start_work":
            # Backward-compatible alias: start_work may be persisted as claim.
            if data.get("action") not in {"start_work", "claim"}:
                continue
        elif action is not None and data.get("action") != action:
            continue
        if source is not None and data.get("source") != source:
            continue

        event_dt = _parse_dt(data.get("timestamp"))
        if since_dt is not None and event_dt is not None and event_dt < since_dt:
            continue
        if until_dt is not None and event_dt is not None and event_dt > until_dt:
            continue

        try:
            events.append(ActivityEvent(**data))
        except Exception:  # noqa: BLE001, S112
            continue

    if limit is not None:
        events = events[:limit]
    return events


def compact_activity_log(
    kanban_dir: Path,
    before_dt: datetime | None = None,
) -> ActivityCompactionResult:
    """Rewrite ``activity.jsonl`` retaining only events newer than *before_dt*.

    Retention rules (Brief C §7.1):
    - ``before_dt``: explicit cutoff, or None → use ended_at of most recently
      closed session.
    - Open-session guard: entries belonging to an open session are always kept.
    - Hard floor: always retain the last 500 entries by timestamp.

    Args:
        kanban_dir: Root directory of the kanban board.
        before_dt:  Cutoff datetime; events before this are candidates for
                    compaction (unless open-session or hard-floor rules apply).

    Returns:
        :class:`ActivityCompactionResult` with before_bytes, after_bytes,
        records_compacted counts.
    """
    activity_path = kanban_dir / _ACTIVITY_FILE
    if not activity_path.exists():
        return ActivityCompactionResult(before_bytes=0, after_bytes=0, records_compacted=0)

    before_bytes = activity_path.stat().st_size
    text = activity_path.read_text(encoding="utf-8")
    all_lines = [line for line in text.splitlines() if line.strip()]

    if not all_lines:
        return ActivityCompactionResult(before_bytes=before_bytes, after_bytes=before_bytes, records_compacted=0)

    # Parse all events
    parsed: list[tuple[str, dict]] = []
    for line in all_lines:
        try:
            data = json.loads(line)
            if isinstance(data, dict):
                parsed.append((line, data))
        except json.JSONDecodeError:
            parsed.append((line, {}))

    # Resolve cutoff: use before_dt or ended_at of last closed session
    auto_cutoff = before_dt is None
    if auto_cutoff:
        before_dt = _find_last_closed_session_dt(parsed)

    # Identify currently open claim cycles by their starting row index.
    open_session_starts = _find_open_session_starts(parsed)

    # Determine which entries to keep
    to_keep: list[str] = []
    for index, (entry_line, entry_data) in enumerate(parsed):
        entry_dt = _parse_dt(entry_data.get("timestamp"))
        in_open_session = _entry_in_open_session(index, entry_data, open_session_starts)

        if before_dt is None or entry_dt is None or entry_dt >= before_dt or in_open_session:
            to_keep.append(entry_line)

    # Hard floor: keep the most recent entries by timestamp for all compaction modes.
    floor_count = min(_HARD_FLOOR, len(all_lines))

    if floor_count > 0 and len(to_keep) < floor_count:
        min_dt = datetime.min.replace(tzinfo=UTC)
        parsed_by_ts = sorted(
            parsed,
            key=lambda item: _parse_dt(item[1].get("timestamp")) or min_dt,
        )
        floor_lines = [line for line, _ in parsed_by_ts[-floor_count:]]
        # Merge: union of to_keep and floor_lines, preserving order
        floor_set = set(floor_lines)
        keep_set = set(to_keep)
        to_keep_final = [line for line, _ in parsed if line in keep_set or line in floor_set]
    else:
        to_keep_final = to_keep

    records_compacted = len(all_lines) - len(to_keep_final)

    new_content = "\n".join(to_keep_final) + ("\n" if to_keep_final else "")
    atomic_write(activity_path, new_content)

    after_bytes = activity_path.stat().st_size
    return ActivityCompactionResult(
        before_bytes=before_bytes,
        after_bytes=after_bytes,
        records_compacted=records_compacted,
    )


def _parse_dt(ts: object) -> datetime | None:
    """Parse an ISO-8601 timestamp string, returning None on failure."""
    if not isinstance(ts, str):
        return None
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt  # noqa: TRY300
    except ValueError, TypeError:
        return None


def _find_last_closed_session_dt(parsed: list[tuple[str, dict]]) -> datetime | None:
    """Return the timestamp of the most recently closed session, or None."""
    _close_actions = frozenset({"end_work", "release", "sweep-release"})
    last_close_dt: datetime | None = None
    for _line, data in parsed:
        if data.get("action") in _close_actions:
            dt = _parse_dt(data.get("timestamp"))
            if dt is not None and (last_close_dt is None or dt > last_close_dt):
                last_close_dt = dt
    return last_close_dt


def _find_open_session_starts(
    parsed: list[tuple[str, dict]],
) -> dict[int | None, list[int]]:
    """Return unmatched claim start indices grouped by task ID."""
    _close_actions = frozenset({"end_work", "release", "sweep-release"})
    open_starts: dict[int | None, list[int]] = {}
    for index, (_line, data) in enumerate(parsed):
        action = data.get("action")
        task_id = data.get("task_id")
        if action == "claim":
            open_starts.setdefault(task_id, []).append(index)
        elif action in _close_actions:
            starts = open_starts.get(task_id)
            if starts:
                starts.pop()
                if not starts:
                    del open_starts[task_id]
    return open_starts


def _entry_in_open_session(
    index: int,
    entry_data: dict,
    open_session_starts: dict[int | None, list[int]],
) -> bool:
    """Return True when the row belongs to a currently open claim cycle."""
    task_id = entry_data.get("task_id")
    starts = open_session_starts.get(task_id)
    if not starts:
        return False
    # In malformed streams with repeated unmatched claims for a task, treat only
    # the latest unmatched claim as the active open cycle.
    return starts[-1] <= index
