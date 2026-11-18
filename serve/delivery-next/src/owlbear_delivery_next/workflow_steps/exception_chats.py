"""Committed-only chat judging and ephemeral, read-by-id runs, separate from every Change's authority."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_quality import ledger
from owlbear_quality.inspect import added

from owlbear_delivery_next.change_flow import quality, worktree
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.state_store import spend_ledger
from owlbear_delivery_next.state_store.store import StoreError
from owlbear_delivery_next.workflow_steps import exceptions, lookup

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.exception_chat import Request
    from owlbear_delivery_next.state_store.store import Store


def answer(store: Store, request: Request) -> dict[str, Any]:
    """Judge added committed copies for this checkout and branch, or proposed code without recording it."""
    root = Path(request.path).resolve()
    if Path(worktree.git(root, "rev-parse", "--show-toplevel").strip()).resolve() != root:
        return {"failed": "path: use the checkout root, not a subdirectory"}
    head = worktree.head(root)
    branch = worktree.git(root, "symbolic-ref", "--quiet", "--short", "HEAD").strip()
    ref = worktree.git(root, "rev-parse", "--verify", "--end-of-options", request.base + "^{commit}").strip()
    base = worktree.git(root, "merge-base", ref, head).strip()
    scope = f"chat:{root}:{branch}"
    context = exceptions.chat_authority(store) | {"for": scope, "commit": head}
    if "failed" in context:
        return context
    context["advice"] = request.proposed is not None
    items = _proposed(root, request) if request.proposed is not None else _added(store, root, base, head, scope)
    verdicts = []
    where = spend_ledger.Where.of(store, job="chat exception judgment")
    for start in range(0, len(items), exceptions.LIMIT):
        said, _ = exceptions.judge(store, root, items[start : start + exceptions.LIMIT], where, context)
        if "failed" in said:
            return said
        verdicts += said["verdicts"]
    reply: dict[str, Any] = {"verdicts": verdicts}
    if worktree.git(root, "status", "--porcelain").strip():
        reply["note"] = (
            "The checkout is dirty. Added suppressions are read from commits only; proposals read current code."
        )
    if request.proposed is not None:
        reply["advice"] = "Advice only; nothing was recorded. Ask the owner before adding a suppression."
    return reply


def _added(store: Store, root: Path, base: str, head: str, scope: str) -> list[dict]:
    items = []
    for addition in added(quality.git, root, base, head):
        previous = ledger.counting(store.root, addition.identity, scope=scope)
        for n, place in enumerate(addition.places[: addition.count]):
            items.append(
                {
                    "identity": addition.identity,
                    "place": f"{place.path}:{place.line}",
                    "directive": place.directive,
                    "code": place.code,
                    "replaces": [previous[n]["index"]] if n < len(previous) else [],
                }
            )
    return items


def _proposed(root: Path, request: Request) -> list[dict]:
    items = []
    for n, item in enumerate(request.proposed or []):
        path = (root / item.file).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            msg = f"proposed.{n}.file: {item.file} must be an existing file inside {root}"
            raise ValueError(msg)
        code = path.read_text(encoding="utf-8")
        if item.line > len(code.splitlines()):
            msg = f"proposed.{n}.line: {item.line} is beyond the end of {item.file}"
            raise ValueError(msg)
        items.append(
            {
                "identity": f"proposed-{n}",
                "place": f"{item.file}:{item.line}",
                "directive": item.directive,
                "code": code,
                "reason": item.reason,
            }
        )
    return items


class Runs:
    """The lookup's bounded answer storage and admission, for exception requests only."""

    def __init__(self, store: Store) -> None:
        """Bind host-owned storage; requests cannot name a Change's ledger scope."""
        self.store, self.runs = store, lookup.Chats()

    def finish(self, run_id: str, request: Request) -> None:
        """Keep the complete failure as an answer too, then release the host's running slot."""
        try:
            said = answer(self.store, request)
        except (OSError, ValueError, RuntimeError, StoreError, subprocess.SubprocessError) as exc:
            said = {"failed": failure(exc)}
        except BaseException as exc:
            said = {"failed": failure(exc)}
            raise
        finally:
            with self.runs.lock:
                self.runs.answers[run_id] = said
                for key in list(self.runs.answers)[: -lookup.KEPT]:
                    del self.runs.answers[key]
            self.runs.slot.release()
