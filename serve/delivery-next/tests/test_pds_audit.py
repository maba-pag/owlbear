"""The PDS deprecation audit (#777): the copy, the gate on the auditor's report, its session and the hand audit."""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts.audit_tools import AuditResult
from owlbear_delivery_next.impeccable_runs import machine_lock
from owlbear_delivery_next.impeccable_runs.pack_state import MACHINE_LOCK
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.pds_runs import audit, hand_audit, pin, sessions
from owlbear_delivery_next.project_host import pds_routes
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings import carried, config, roles
from owlbear_delivery_next.settings.config import Layer, SettingsUnset, resolve

VERSION = pin.read().version
SCHEMA = json.loads((pin.package() / pin.TREE / audit.SCHEMA).read_text(encoding="utf-8"))
PAGE = (
    'import { html } from "/assets/lit-html/3.3.3/lit-html.js";\n'
    'export const t = html`<p-text size="x-small">Hi</p-text>`;\n'
)


def report(  # noqa: PLR0913 - each part of the report a case varies
    *, result="completed", version=VERSION, findings=(), follow_ups=(), included=(".",), excluded=(), skipped=(),
    limitations=(),
) -> dict:  # fmt: skip
    """A report the release's schema accepts, as the skill would write it for the copy."""
    return {
        "schemaVersion": "1.0.0",
        "audit": {"runId": "2026-11-01T00-00-00Z", "generatedAt": "2026-11-01T00:00:00Z", "skillName": audit.SKILL,
                  "auditKind": "deprecations", "framework": "js", "pdsVersion": version},
        "project": {"root": ".", "pdsPackages": [{"name": pin.NAME, "version": version}]},
        "scope": {"includedPaths": list(included),
                  "excludedPaths": [{"path": p, "reason": "default"} for p in ("node_modules", *excluded)]},
        "summary": {"result": result},
        "coverage": {"skippedFiles": [{"path": p, "reason": "unreadable"} for p in skipped],
                     "limitations": list(limitations)},
        "findings": list(findings),
        "manualFollowUps": list(follow_ups),
    }  # fmt: skip


def finding(path="web/pages/demo.mjs", line=2) -> dict:
    return {
        "id": "f1", "ruleId": "propValue/p-text/size/x-small", "usageKind": "propValue",
        "title": "Deprecated value x-small of prop size on p-text", "confidence": "high", "baselineEffort": "trivial",
        "remediation": {"replacement": {"from": 'size="x-small"', "to": 'size="xs"'}, "instruction": "Use xs."},
        "evidence": [{"path": path, "line": line, "snippet": 'html`<p-text size="x-small">Hi</p-text>`',
                      "detection": "direct", "valueResolution": "literal"}],
        "sources": [{"reference": "references/deprecations.md", "pdsVersion": VERSION}],
    }  # fmt: skip


def follow_up(subject: str, *, snippet="html`<p-text size=${s}>`") -> dict:
    return {"subject": subject, "reason": "dynamic value",
            "evidence": [{"path": "web/pages/demo.mjs", "line": 2, "snippet": snippet}]}  # fmt: skip


@pytest.fixture
def sources(tmp_path: Path) -> SimpleNamespace:
    """Pages with a planted deprecated value beside the vendored folders, and a release tree holding the schema."""
    web, tree = tmp_path / "web", tmp_path / "tree"
    (web / "pages").mkdir(parents=True)
    (web / "pages" / "demo.mjs").write_text(PAGE, encoding="utf-8")
    for vendored in ("pds/load.mjs", "vendor/lit.mjs"):
        (web / vendored).parent.mkdir(parents=True)
        (web / vendored).write_text("export {};\n", encoding="utf-8")
    schema = tree / audit.SCHEMA
    schema.parent.mkdir(parents=True)
    shutil.copyfile(pin.package() / pin.TREE / audit.SCHEMA, schema)
    (schema.parent.parent / "references" / "deprecations.md").write_text("# index\n", encoding="utf-8")
    (tree / "package.json").write_text(json.dumps({"name": pin.NAME, "version": VERSION}), encoding="utf-8")
    return SimpleNamespace(web=web, tree=tree, at=tmp_path / "copy")


def submitted(body: object, *, markdown="# Audit\n", edit=None, **run) -> tuple[list, object]:
    """A fake auditor submitting *body*; *edit* changes its copy first. Returns its calls and the session callable."""
    calls: list = []

    def session(at: Path, skills: Path, message: str) -> Run:
        calls.append((at, skills, message))
        if edit:
            edit(at)
        text = body if isinstance(body, str) else json.dumps(body)
        fields = {"ending": "result", "payload": AuditResult(report=text, markdown=markdown),
                  "termination": Termination(confirmed=True)} | run  # fmt: skip
        return Run("pds-audit-1", **fields)

    return calls, session


def audited(sources, body, **kw) -> audit.Audit:
    _calls, session = submitted(body, **kw)
    sources.at.mkdir()
    return audit.audit(sources.at, web=sources.web, tree=sources.tree, version=VERSION, session=session)


def test_the_copy_holds_the_authored_pages_the_manifest_and_the_release_never_the_vendored_folders(sources):
    calls, session = submitted(report())
    sources.at.mkdir()
    audit.audit(sources.at, web=sources.web, tree=sources.tree, version=VERSION, session=session)
    [(at, skills, message)] = calls
    assert (at / "web/pages/demo.mjs").read_text(encoding="utf-8") == PAGE
    assert not (at / "web/pds").exists()
    assert not (at / "web/vendor").exists()
    assert json.loads((at / "package.json").read_text(encoding="utf-8"))["dependencies"] == {pin.NAME: VERSION}
    assert skills == at / audit.PACKAGE / "skills"
    assert (skills / audit.SKILL / "references/report.schema.json").is_file()
    assert VERSION in message
    assert "write no file" in message


def test_the_real_pages_copy_without_their_vendored_folders(tmp_path):
    audit.lay_out(tmp_path, pin.package() / "web", tmp_path / "none", VERSION)
    assert (tmp_path / "web/pages/updates/pds.mjs").is_file()
    assert not (tmp_path / "web/pds").exists()
    assert not (tmp_path / "web/vendor").exists()


def test_a_planted_deprecated_value_is_a_finding_at_its_repository_path_and_line(sources):
    done = audited(sources, report(findings=[finding()]))
    assert done.verdict.outcome == "findings"
    [found] = done.verdict.findings
    assert (found.path, found.line) == (f"{pin.PREFIX}web/pages/demo.mjs", 2)
    assert found.replacement == {"from": 'size="x-small"', "to": 'size="xs"'}
    assert 'size="x-small"' in PAGE.splitlines()[found.line - 1]


def test_an_absolute_path_inside_the_copy_maps_like_a_relative_one(sources):
    sources.at.mkdir()
    absolute = str(sources.at.resolve() / "web/pages/demo.mjs")
    verdict = audit.judge(report(findings=[finding(path=absolute)], included=[str(sources.at)]), schema=SCHEMA,
                          version=VERSION, at=sources.at)  # fmt: skip
    assert verdict.findings[0].path == f"{pin.PREFIX}web/pages/demo.mjs"


def test_only_a_completed_clean_report_passes_and_its_files_hold_what_was_submitted(sources, tmp_path):
    clean = json.dumps(report(), indent=1)
    done = audited(sources, clean, markdown="# Clean\n")
    assert done.verdict == audit.Verdict("pass")
    folder = audit.write(tmp_path / "out", done)
    assert folder == tmp_path / "out" / audit.REPORTS / done.run_id
    assert (folder / f"{audit.SKILL}.json").read_text(encoding="utf-8") == clean
    assert (folder / f"{audit.SKILL}.md").read_text(encoding="utf-8") == "# Clean\n"


def test_follow_ups_are_their_own_outcome_and_each_subject_its_own_identity(sources):
    same = "html`<p-text   size=${s}>`"  # whitespace apart from the other evidence
    done = audited(sources, report(follow_ups=[follow_up("p-text size"), follow_up("p-text weight", snippet=same)]))
    assert done.verdict.outcome == "follow-ups"
    assert not done.verdict.findings
    one, two = done.verdict.follow_ups
    assert one.evidence == two.evidence
    assert one.key != two.key
    again = audit.follow_up(follow_up("p-text size", snippet=same))
    assert again.key == one.key
    assert audit.follow_up(follow_up("p-text size", snippet="html`<p-text size=${t}>`")).key != one.key


@pytest.mark.parametrize(
    ("body", "why"),
    [
        (report(version="4.9.0"), "pdsVersion '4.9.0'"),
        (report(result="partial", limitations=["one package unread"]), "ended partial"),
        (report(result="failed", limitations=["no package.json"]), "ended failed"),
        ({**report(), "summary": {"result": "done"}}, "breaks its schema"),
        ({k: v for k, v in report().items() if k != "findings"}, "breaks its schema"),
        ("not json", "not JSON"),
        (report(limitations=["templates in .html not read"]), "disclosed gaps: templates"),
        (report(skipped=["web/pages/big.mjs"]), "web/pages/big.mjs skipped"),
        (report(excluded=["web/pages"]), "left out web/pages"),
        (report(included=["web"]), "did not include the project root"),
    ],
    ids=["version", "partial", "failed", "result", "missing", "text", "limitation", "skipped", "excluded", "root"],
)
def test_a_report_short_of_complete_and_clean_stops(sources, body, why):
    verdict = audited(sources, body).verdict
    assert verdict.outcome == "stop"
    assert why in verdict.reason


@pytest.mark.parametrize(
    "edit",
    [
        lambda at: (at / audit.PACKAGE / "skills" / audit.SKILL / "references/deprecations.md").write_text("# none\n"),
        lambda at: (at / "web/pages/demo.mjs").write_text(PAGE.replace("x-small", "xs")),
        lambda at: (at / ".pds").mkdir() or (at / ".pds/note.md").write_text("x"),
    ],
    ids=["index", "page", "added"],
)
def test_a_session_that_changed_its_copy_stops_even_with_a_clean_report(sources, edit):
    done = audited(sources, report(), edit=edit)
    assert done.verdict.outcome == "stop"
    assert "changed its copy" in done.verdict.reason
    assert done.report is None


@pytest.mark.parametrize(
    ("run", "why"),
    [
        ({"ending": "error", "payload": None, "detail": "quota"}, "submitted no report: ended error; quota"),
        ({"termination": Termination(confirmed=False)}, "not proven ended"),
        ({"termination": None}, "not proven ended"),
        ({"usage_unread": "no usage event"}, "model is unknown"),
    ],
    ids=["no-result", "unconfirmed", "no-termination", "usage"],
)
def test_a_session_that_did_not_end_cleanly_stops_whatever_it_reported(sources, run, why):
    verdict = audited(sources, report(), **run).verdict
    assert (verdict.outcome, why in verdict.reason) == ("stop", True)


def auditor_settings(**auditor: object) -> config.Settings:
    base = carried.layer()
    agents = base.agents | {"auditor": base.agents["curator"].model_copy(update=auditor)} if auditor else base.agents
    switches = dict.fromkeys(roles.USER_CONFIG, False)
    return resolve(base.model_copy(update={"agents": agents, **switches}), Layer())


def test_the_auditor_session_reads_confined_with_its_own_settings_and_no_question_or_shell(tmp_path):
    settings = auditor_settings(model="claude-opus-5.5", effort="low", context="long", minutes=7,
                                subagents=False)  # fmt: skip
    cfg = sessions.auditor(settings, tmp_path, tmp_path / "skills", "audit it")
    assert (cfg.role, cfg.job, cfg.limit, cfg.subagents) == ("auditor", "pds-audit", 420.0, False)
    assert (cfg.policy.write, cfg.policy.confined, cfg.policy.root) == (False, True, tmp_path)
    loop = SimpleNamespace(call_soon_threadsafe=lambda *_: None)
    options = sdk_adapter._Step(cfg, loop).options()  # noqa: SLF001
    [agent] = options["custom_agents"]
    assert agent["tools"] == ["view", "glob", "grep", "owlbear-memory/recall_memory", "submit_result"]
    assert agent["skills"] == [audit.SKILL]
    assert options["skill_directories"] == [str(tmp_path / "skills" / audit.SKILL)]
    assert (options["model"], options["reasoning_effort"], options["context_tier"]) == ("claude-opus-5.5", "low",
                                                                                         "long_context")  # fmt: skip


@pytest.fixture
def production(monkeypatch) -> config.Settings:
    """A carried Global layer with no test layer under it: the auditor's row is unset until the owner fills it."""
    monkeypatch.setattr(config, "BASE", None)
    return auditor_settings()


def test_an_unset_auditor_refuses_the_session_naming_its_settings(production, tmp_path):
    with pytest.raises(SettingsUnset, match=r"agents\.auditor\.model"):
        sessions.auditor(production, tmp_path, tmp_path / "skills", "audit it")


class Ownership:
    """The maintenance ownership the host binds: a throwaway workspace, and an optional unproven PDS session."""

    def __init__(self, *, unproven: bool = False) -> None:
        self.unproven = unproven
        self.used: list[Path] = []

    def pending(self, *, kind: str) -> bool:
        return self.unproven and kind == "pds"

    @contextlib.contextmanager
    def workspace(self, prefix: str):
        root = Path(local_home.root() / prefix)
        root.mkdir(parents=True)
        self.used.append(root)
        try:
            yield root
        finally:
            shutil.rmtree(root)


def hand(tmp_path, body=None, *, settings=None, gate=None, unproven=False):
    """A hand audit on a project store, its runner a fake auditor; *gate* holds the session until set."""
    seen: list = []

    def run(cfg) -> Run:
        seen.append(cfg)
        assert (cfg.worktree / "web/pages/updates/pds.mjs").is_file()  # the installed pages, copied
        if gate is not None:
            gate.wait(10)
        payload = AuditResult(report=json.dumps(body or report()), markdown="# Audit\n")
        return Run("pds-audit-1", ending="result", payload=payload, termination=Termination(confirmed=True))

    store = SimpleNamespace(root=tmp_path / "store", name="shop", shared=None,
                            settings=lambda: settings or auditor_settings(model="claude-opus-5.5"))  # fmt: skip
    h = hand_audit.Hand(store, run)
    h.maintenance = Ownership(unproven=unproven)
    app = FastAPI()
    app.include_router(pds_routes.router(h))
    return h, TestClient(app, base_url="http://127.0.0.1"), seen


def settled(h) -> dict:
    h.thread.join(30)
    return h.read()


def test_the_hand_audit_audits_the_installed_pages_and_keeps_the_version_commit_and_reports(tmp_path):
    h, http, seen = hand(tmp_path, report(findings=[finding()]))
    assert http.get("/pds/audit").json() == {"state": "none"}
    assert http.post("/pds/audit").json()["state"] == "running"
    kept = settled(h)
    assert (kept["state"], kept["outcome"], kept["version"]) == ("done", "findings", VERSION)
    assert len(kept["commit"]) == 40 or kept["commit"] == "not a git checkout"
    assert kept["findings"][0]["path"] == f"{pin.PREFIX}web/pages/demo.mjs"
    assert (kept["markdown"], kept["report"]["summary"]) == ("# Audit\n", {"result": "completed"})
    assert http.get("/pds/audit").json() == kept
    [cfg] = seen
    assert (cfg.role, cfg.job, cfg.model) == ("auditor", "pds-audit", "claude-opus-5.5")
    assert not h.maintenance.used[0].exists()
    assert not (tmp_path / "store" / ".pds").exists()  # the hand audit keeps its reports in its state alone


def test_a_hand_audit_that_stops_is_failed_with_the_reason(tmp_path):
    h, http, _seen = hand(tmp_path, report(version="4.9.0"))
    http.post("/pds/audit")
    kept = settled(h)
    assert (kept["state"], kept["outcome"]) == ("failed", "stop")
    assert "4.9.0" in kept["reason"]


def test_one_hand_audit_runs_at_a_time_and_it_holds_the_machine_lock(tmp_path):
    gate = threading.Event()
    h, http, _seen = hand(tmp_path, gate=gate)
    http.post("/pds/audit")
    try:
        assert http.post("/pds/audit").status_code == 409
        assert http.get("/pds/audit").json()["state"] == "running"
        with pytest.raises(machine_lock.HeldError, match=r"shop \(PDS audit\)"):
            os.close(machine_lock.take(local_home.root() / MACHINE_LOCK, "other", lambda: None))
    finally:
        gate.set()
    assert settled(h)["state"] == "done"


def test_a_hand_audit_is_refused_while_another_update_holds_the_machine_lock(tmp_path):
    held = machine_lock.take(local_home.root() / MACHINE_LOCK, "garage", lambda: None)
    try:
        h, http, seen = hand(tmp_path)
        refused = http.post("/pds/audit")
    finally:
        os.close(held)
    assert refused.status_code == 409
    assert "an update runs for garage" in refused.json()["detail"]
    assert (seen, h.read()) == ([], {"state": "none"})


@pytest.mark.parametrize("why", ["unproven", "unbound"])
def test_a_hand_audit_is_refused_while_a_pds_session_is_unproven_or_ownership_is_unbound(tmp_path, why):
    h, http, seen = hand(tmp_path, unproven=why == "unproven")
    if why == "unbound":
        h.maintenance = None
    refused = http.post("/pds/audit")
    assert refused.status_code == 409
    assert ("unproven" if why == "unproven" else "not bound") in refused.json()["detail"]
    assert (seen, h.read()) == ([], {"state": "none"})


def test_an_unset_auditor_refuses_the_hand_audit_before_any_session(production, tmp_path):
    h, http, seen = hand(tmp_path, settings=production)
    refused = http.post("/pds/audit")
    assert refused.status_code == 409
    assert "agents.auditor.model" in refused.json()["detail"]
    assert (seen, h.read()) == ([], {"state": "none"})


def test_a_running_audit_the_host_lost_reads_as_failed(tmp_path):
    h, http, _seen = hand(tmp_path)
    h.path.parent.mkdir(parents=True)
    h.path.write_text(json.dumps({"state": "running", "started_at": "2026-11-01T00:00:00+00:00"}), encoding="utf-8")
    assert http.get("/pds/audit").json()["reason"] == hand_audit.INTERRUPTED
    assert http.post("/pds/audit").json()["state"] == "running"
    assert settled(h)["state"] == "done"
