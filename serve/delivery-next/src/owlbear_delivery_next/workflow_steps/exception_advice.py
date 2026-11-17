"""Configuration judgments are advice on the owner-authored approval question, never approval themselves."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from owlbear_quality.inspect import configured
from owlbear_quality.protected import lint_file

from owlbear_delivery_next.state_store import spend_ledger
from owlbear_delivery_next.workflow_steps import exceptions, sessions

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_quality.inspect import Protected

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.state_store.store import Lock, Store


def items(path: Path, change: Protected) -> list[dict]:
    """Changed lint files or tables only; deletions are judged as the removal of their old content."""
    changes = json.loads(change.text)
    found = []
    for item in configured(path):
        if item.path not in changes:
            continue
        old = changes[item.path]["before"]
        previous = old.get("content") if old else None
        if item.table and isinstance(previous, dict):
            previous = json.dumps(previous.get(item.table), sort_keys=True, indent=2, ensure_ascii=False)
        if previous != item.content:
            found.append(
                {"identity": item.identity, "place": f"{item.path} {item.table}".strip(), "content": item.content}
            )
    for name, delta in changes.items():
        if not lint_file(name):
            continue
        old, new = delta["before"], delta["after"]
        if not any(item["place"].split(" ", 1)[0] == name for item in found) and (new is None or "symlink" in new):
            content = json.dumps(delta, sort_keys=True, indent=2)
            identity = hashlib.sha256(json.dumps([name, content]).encode()).hexdigest()
            found.append({"identity": identity, "place": name, "content": content})
        previous = old.get("content") if old else None
        current = new.get("content") if new else None
        if not isinstance(previous, dict):
            continue
        for table in previous.keys() - (current.keys() if isinstance(current, dict) else set()):
            content = f"Removed table {table}:\n" + json.dumps(previous[table], sort_keys=True, indent=2)
            identity = hashlib.sha256(json.dumps([name, table, content]).encode()).hexdigest()
            found.append({"identity": identity, "place": f"{name} {table}", "content": content})
    return found


class Advice:
    """Bind the project and Change lock for caller-owned run accounting."""

    def __init__(self, store: Store, lock: Lock) -> None:
        """Keep the caller's store and lock, never an identity from the agent."""
        self.store, self.lock = store, lock

    def run(self, c: Change, path: Path, change: Protected, commit: str) -> str:
        """Every changed configuration item receives advice, or the whole failure appears in the question."""
        selected = items(path, change)
        if not selected:
            return ""
        context = exceptions.authority(self.store, c) | {"for": c.slug, "commit": commit}
        where = spend_ledger.where()
        if not where.project:
            where = spend_ledger.Where.of(self.store, change=c.slug, step=str(c.step.kind), job=exceptions.JOB)
        lines = ["\n\nQuality judge's advice (your approval is still required):"]
        for start in range(0, len(selected), exceptions.LIMIT):
            said, done = exceptions.judge(self.store, path, selected[start : start + exceptions.LIMIT], where, context)
            if done:
                sessions.logged(self.store, self.lock, c, done, {"kind": exceptions.JOB, "exit": "advice"})
            if "failed" in said:
                lines.append(f"The quality judge failed: {said['failed']}")
                break
            lines.extend(f"{v['place']}: {v['verdict']}: {v['reason']}" for v in said["verdicts"])
        return "\n".join(lines)
