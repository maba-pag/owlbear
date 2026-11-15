"""One per-project audit thread, pinned read-only sessions and resumable publication."""

from __future__ import annotations

import json
import logging
import subprocess
import threading
import uuid
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.audit_runs import context, publish, record, sessions, workspace
from owlbear_delivery_next.change_contracts import project_audit_tools
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.github.provider import ProviderError
from owlbear_delivery_next.runtimes import session_result
from owlbear_delivery_next.settings import profile, roles
from owlbear_delivery_next.settings.config import SettingsUnset
from owlbear_delivery_next.state_store import backlog, spend_ledger, work_block
from owlbear_delivery_next.state_store.store import StoreError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.change_contracts import tools
    from owlbear_delivery_next.local_system.maintenance import Maintenance
    from owlbear_delivery_next.runtimes.sdk_adapter import Session
    from owlbear_delivery_next.runtimes.session_result import Run
    from owlbear_delivery_next.state_store.store import Store

_log = logging.getLogger(__name__)
UNBOUND = "maintenance ownership and the audit session runner must be bound before starting"
NOTE_LIMIT = 2000


class AuditBusyError(RuntimeError):
    """An audit cannot start; the message gives the complete reason."""


Busy = AuditBusyError


def _unbound(_cfg: Session) -> Run:
    raise Busy(UNBOUND)


class Audits:
    """The host binds its maintenance owner, clone and owned session runner before use."""

    def __init__(self, store: Store) -> None:
        self.store = store
        self.repo: Path | None = None
        self.maintenance: Maintenance | None = None
        self.run: Callable[[Session], Run] = _unbound
        self.lock = threading.RLock()
        self.thread: threading.Thread | None = None

    def offered(self) -> tuple[str, ...]:
        """Only OwlBear's shared project folder offers an agent audit."""
        return record.NAMES if self.store.name == "owlbear" else ("doc",)

    def busy(self) -> bool:
        """Whether the project's stop must wait for an audit or its publication."""
        return self.thread is not None and self.thread.is_alive()

    def read(self, audit: str | None = None) -> dict[str, Any] | None:
        """A last flat report, or all last reports when no audit is named."""
        rows = record.read(self.store)
        return rows.get(audit) if audit is not None else rows

    def offer(self) -> dict[str, Any]:
        """The page's offered actions, models, target and reports."""
        branch, role, problem = "", {}, ""
        try:
            branch = profile.value(self.store.read_profile() or Profile(), profile.DEFAULT, "")
            role = self.store.settings().roles.get("project-auditor") or {}
        except (StoreError, SettingsUnset, OSError, ValueError) as exc:
            problem = failure(exc)
        rows = []
        for audit in self.offered():
            last = self.read(audit)
            rows.append(
                {
                    "audit": audit,
                    "name": f"{audit.title()} audit",
                    "branch": branch,
                    "role": {key: role.get(key) for key in ("model", "effort")},
                    "last": last,
                    "blocked": problem or self.refusal(audit),
                    "unpublished": record.unpublished(last or {}),
                }
            )
        return {"audits": rows}

    def refusal(self, audit: str) -> str:
        """Admission reason for Start; unpublished findings require the explicit drop flag separately."""
        why = ""
        if audit not in self.offered():
            why = f"the {audit} audit is not offered for this project"
        elif self.busy():
            why = "an audit is running for this project"
        elif self.maintenance is None or self.repo is None or self.run is _unbound:
            why = UNBOUND
        elif self.maintenance.pending(kind="audit"):
            why = "an earlier audit session is unproven; recover it on the Maintenance page first"
        if why:
            return why
        if blocked := work_block.of_store(self.store).text():
            return blocked
        try:
            settings = self.store.settings()
            roles.chosen(settings, f"{audit}-audit")
            roles.limit(settings, f"{audit}-audit")
            roles.subagents(settings, f"{audit}-audit")
            roles.user_config(settings)
            backlog.Backlog.of(self.store)
            record.load(self.store)
        except (StoreError, SettingsUnset, ProviderError, backlog.BacklogError, OSError, ValueError, TypeError) as exc:
            return failure(exc)
        return ""

    def start(self, audit: str, note: str = "", *, drop_unpublished: bool = False) -> dict[str, Any]:
        """Pin the selected branch and launch one auditor, refusing an undisposed partial publication."""
        with self.lock:
            if why := self.refusal(audit):
                raise Busy(why)
            if len(note) > NOTE_LIMIT:
                msg = "the audit note exceeds 2000 characters"
                raise ValueError(msg)
            old = self.read(audit)
            if old and record.unpublished(old) and not drop_unpublished:
                msg = "the last audit has unpublished findings; finish publishing or explicitly drop them"
                raise Busy(msg)
            prof = self.store.read_profile() or Profile()
            branch = profile.value(prof, profile.DEFAULT, "")
            if not branch:
                msg = "the project profile has no target branch"
                raise Busy(msg)
            state = {
                "id": uuid.uuid4().hex,
                "host": str(self.store.root.resolve()),
                "audit": audit,
                "state": "running",
                "phase": "auditing",
                "started_at": record.now(),
                "ended_at": "",
                "branch": branch,
                "commit": "",
                "note": note,
                "changed_defaults": [],
                "destination": "",
                "summary": "",
                "findings": [],
                "parts": [],
                "not_covered": [],
                "subagents": [],
                "reason": "",
                "session": "",
            }
            self._launch(audit, state, resume=False)
            return state.copy()

    def publish(self, audit: str) -> dict[str, Any]:
        """Finish a partial publication without running another agent."""
        with self.lock:
            if audit not in self.offered() or self.busy():
                msg = "the audit is not offered or an audit is running"
                raise Busy(msg)
            state = self.read(audit)
            if not state or state["state"] != "publishing":
                msg = "this audit has no publication to finish"
                raise Busy(msg)
            self._launch(audit, state, resume=True)
            return state.copy()

    finish = publish

    def _launch(self, audit: str, state: dict[str, Any], *, resume: bool) -> None:
        record.active(self.store, audit, running=True)
        try:
            record.save(self.store, audit, state)
            self.thread = threading.Thread(
                target=self._work,
                args=(audit, state),
                kwargs={"resume": resume},
                name=f"{audit}-audit",
                daemon=True,
            )
            self.thread.start()
        except BaseException:
            record.active(self.store, audit, running=False)
            raise

    def _work(self, audit: str, state: dict[str, Any], *, resume: bool) -> None:
        def save() -> None:
            record.save(self.store, audit, state)

        try:
            if not resume:
                with spend_ledger.at(spend_ledger.Where.of(self.store, job=f"{audit.title()} audit")):
                    self._audit(audit, state, save)
                state.update(state="publishing", phase="opening issues")
                save()
            publish.findings(self.store, state, save)
            state.update(state="done", phase="", reason="", ended_at=record.now())
        except (
            RuntimeError,
            OSError,
            ValueError,
            TypeError,
            subprocess.SubprocessError,
            StoreError,
            SettingsUnset,
            ProviderError,
            backlog.BacklogError,
            session_result.ReturnedRunError,
        ) as exc:
            self._failed(audit, state, exc)
        except Exception as exc:
            self._failed(audit, state, exc)
            raise
        finally:
            try:
                save()
            finally:
                record.active(self.store, audit, running=False)

    @staticmethod
    def _failed(audit: str, state: dict[str, Any], exc: Exception) -> None:
        state.update(reason=failure(exc), ended_at=record.now())
        if state["state"] != "publishing":
            state.update(state="failed", phase="")
        _log.exception("%s audit failed", audit)

    def _audit(self, audit: str, state: dict[str, Any], save: Callable[[], None]) -> None:
        if self.repo is None or self.maintenance is None:
            raise Busy(UNBOUND)
        state["commit"] = workspace.pin(self.repo, state["branch"])
        save()
        prof = self.store.read_profile() or Profile()
        repository = profile.value(prof, profile.REPO, "")
        with workspace.opened(self.maintenance, self.repo, state["commit"]) as copy:
            root = copy.path.parent
            state["not_covered"] = context.prepare(self.store, root, state, repository)
            save()

            def target(args: tools.Args) -> str:
                if not isinstance(args, project_audit_tools.Target):
                    msg = "set_target requires a ref and reason"
                    raise TypeError(msg)
                if not state["note"] or args.ref not in state["note"]:
                    msg = "set_target.ref must occur literally in the owner's note"
                    raise ValueError(msg)
                state["commit"] = workspace.target(copy, args.ref)
                state["changed_defaults"].append({"default": "commit", "to": state["commit"], "reason": args.reason})
                save()
                (root / "context" / "run.json").write_text(json.dumps(state), encoding="utf-8")
                return state["commit"]

            cfg = sessions.auditor(
                self.store,
                root,
                audit,
                state["note"],
                helper=target,
            )
            try:
                try:
                    done = self.run(cfg)
                except session_result.ReturnedRunError as exc:
                    state["session"] = exc.run.session_id
                    state["subagents"] = exc.run.subagents
                    raise
                state["session"] = done.session_id
                state["subagents"] = done.subagents
            finally:
                workspace.inspect(copy, state["commit"])
            result = sessions.accepted(done, root)
            data = result.model_dump(mode="json")
            data["not_covered"] = [*state["not_covered"], *data["not_covered"]]
            data["changed_defaults"] = [*state["changed_defaults"], *data["changed_defaults"]]
            data["findings"] = [{**f, "number": None, "url": "", "pending": None} for f in data["findings"]]
            state.update(data)
