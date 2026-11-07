"""Decision history shown by action only, never by private commit-subject prose."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlbear_decisions import Entry
    from owlbear_delivery_next.local_system.data_repo import DataRepo

ACTIONS = {
    **{a: a for a in ("replace", "withdraw", "activate", "promote", "exception", "keep", "read-back",
                      "queue-read-back", "propose", "record", "accept-existing", "conflict", "correct-origin",
                      "complete")},
    "proposed": "propose", "queue": "queue-read-back",
}  # fmt: skip


def read(shared: DataRepo | None, entry: Entry) -> list[dict[str, str]]:
    """The file's commits, newest first, with their known action word only."""
    if shared is None:
        return []
    rel = entry.path.relative_to(shared.root).as_posix()
    said = shared.git("log", "-n", "30", "--format=%H%x1f%cI%x1f%s", "--", rel)
    if said.returncode:
        return []
    rows = (line.split("\x1f", 2) for line in said.stdout.splitlines() if line.count("\x1f") == 2)  # noqa: PLR2004
    return [{"commit": commit[:12], "at": at, "action": _action(subject)} for commit, at, subject in rows]


def _action(subject: str) -> str:
    """An older subject may contain words a person typed, so unknown actions are shown as "changed"."""
    if not subject.startswith(prefix := "decisions: "):
        return "changed"
    rest = subject.removeprefix(prefix)
    word = "read-back" if rest.startswith("read back ") else rest.split(" ", 1)[0]
    return ACTIONS.get(word, "changed")
