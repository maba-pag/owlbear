"""The PDS deprecation audit (#777): the copy, the gate on the auditor's report, its session and the hand audit."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import shutil
import socket
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import jsonschema
import pytest
import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient
from markdown_it import MarkdownIt

from owlbear_delivery_next.change_contracts import audit_tools, tool_schema
from owlbear_delivery_next.change_contracts.audit_tools import AuditResult
from owlbear_delivery_next.impeccable_runs import machine_lock
from owlbear_delivery_next.impeccable_runs.pack_state import MACHINE_LOCK
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.pds_runs import audit, audit_markdown, hand_audit, pin, sessions
from owlbear_delivery_next.project_host import api, pds_routes
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.runtimes.results import ACCEPTED, Gate
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings import carried, config, roles
from owlbear_delivery_next.settings.config import Layer, SettingsUnset, resolve
from owlbear_delivery_next.state_store.store import Store

VERSION = pin.read().version
SCHEMA = json.loads((pin.package() / pin.TREE / audit.SCHEMA).read_text(encoding="utf-8"))
TEMPLATE = (pin.package() / pin.TREE / audit_markdown.TEMPLATE).read_text(encoding="utf-8")
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
    shutil.copyfile(pin.package() / pin.TREE / audit_markdown.TEMPLATE, tree / audit_markdown.TEMPLATE)
    (schema.parent.parent / "references" / "deprecations.md").write_text("# index\n", encoding="utf-8")
    (tree / "package.json").write_text(json.dumps({"name": pin.NAME, "version": VERSION}), encoding="utf-8")
    return SimpleNamespace(web=web, tree=tree, at=tmp_path / "copy")


def submitted(body: object, *, edit=None, **run) -> tuple[list, object]:
    """A fake auditor submitting *body*; *edit* changes its copy first. Returns its calls and the session callable."""
    calls: list = []

    def session(at: Path, skills: Path, message: str) -> Run:
        calls.append((at, skills, message))
        if edit:
            edit(at)
        text = body if isinstance(body, str) else json.dumps(body)
        fields = {"ending": "result", "payload": AuditResult(report=text),
                  "termination": Termination(confirmed=True)} | run  # fmt: skip
        return Run("pds-audit-1", **fields)

    return calls, session


def audited(sources, body, **kw) -> audit.Audit:
    _calls, session = submitted(body, **kw)
    sources.at.mkdir()
    return audit.audit(sources.at, web=sources.web, tree=sources.tree, version=VERSION, session=session)


@pytest.fixture
def no_render(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("rendering ran before the existing acceptance gates")

    monkeypatch.setattr(audit_markdown, "render", forbidden)


@pytest.mark.parametrize("changed", ["schema", "template", "missing-template"])
def test_unsupported_audit_format_never_starts_or_renders(sources, changed):
    if changed == "schema":
        schema = json.loads((sources.tree / audit.SCHEMA).read_text(encoding="utf-8"))
        schema["properties"]["schemaVersion"]["const"] = "2.0.0"
        (sources.tree / audit.SCHEMA).write_text(json.dumps(schema), encoding="utf-8")
        path = sources.tree / audit.SCHEMA
    else:
        path = sources.tree / audit_markdown.TEMPLATE
        if changed == "missing-template":
            path.unlink()
        else:
            path.write_text(TEMPLATE + "\nA new report shape.\n", encoding="utf-8")
    calls, session = submitted(report())
    sources.at.mkdir()
    done = audit.audit(sources.at, web=sources.web, tree=sources.tree, version=VERSION, session=session)
    assert calls == []
    assert done.verdict.outcome == "stop"
    assert f"unsupported PDS audit {changed.removeprefix('missing-')}" in done.verdict.reason
    assert str(path) in done.verdict.reason
    assert not done.markdown


def test_report_renderer_preserves_rich_fields_and_literal_blocks():
    first = finding()
    first["title"] += " #"
    first["deprecationMessage"] = ""
    literal = "**literal** _value_ [label](target) \\ & <tag>"
    first["remediation"]["replacement"] = {"from": f"size=`x-small`\n{literal}", "to": "size=`xs`"}
    first["evidence"][0]["snippet"] = "const size = `x-small`;\n```"
    first["evidence"][0]["anchor"] = {"path": "web/anchor.mjs", "line": 8, "snippet": "const size = `x-small`;"}
    first["evidence"].append(
        {"path": "web/other.mjs", "line": 9, "snippet": "<p-text>", "detection": "direct", "valueResolution": "literal"}
    )
    first["sources"].append({"reference": "references/components.md", "pdsVersion": VERSION})
    second = finding(path="web/second.mjs", line=4)
    second.update(
        id="f2",
        title="Second finding",
        ruleId="component/old",
        usageKind="component",
        confidence="medium",
        baselineEffort="large",
        observedEffort="medium",
        effortRationale="The second location",
    )
    second["remediation"] = {"instruction": "Use the replacement."}
    second["evidence"][0].pop("valueResolution")
    manual = follow_up("Unresolved value #")
    manual["ruleId"] = "dynamic/value"
    limitations = ["---", "- literal", "+ literal", "1. literal", "1) literal"]
    body = report(findings=[first, second], follow_ups=[manual], limitations=limitations)
    jsonschema.Draft202012Validator(SCHEMA).validate(body)
    text = audit_markdown.render(body, TEMPLATE)
    assert "- **2** findings across **3** locations\n- **1** manual follow-ups" in text
    assert all(row in text for row in ("| `trivial` | 1 |\n| `medium` | 1 |", "| `high` | 1 |\n| `medium` | 1 |"))
    assert text.index("### 1. Deprecated value") < text.index("### 2. Second finding")
    assert "- **Effort:** `medium` (observed \u2014 baseline `large`)" in text
    assert [line for line in text.splitlines() if line.startswith("- **Effort rationale:**")] == [
        "- **Effort rationale:** The second location"
    ]
    assert [line for line in text.splitlines() if line.startswith("- **Deprecation message:**")] == [
        "- **Deprecation message:** "
    ]
    assert text.count("- **Replacement:**") == 1
    assert " \u2192 `` size=`xs` ``" in text
    assert "    ````\n    const size = `x-small`;\n    ```\n    ````" in text
    assert "    anchored by `web/anchor.mjs:8`\n    ```\n    const size = `x-small`;\n    ```" in text
    assert "  - `web/other.mjs:9`" in text
    assert "  - `web/second.mjs:4`" in text
    assert text.count(", value `literal`") == 2
    assert f"<code>pds-knowledge-js/references/components.md</code> (PDS {VERSION})" in MarkdownIt("commonmark").render(
        text
    )
    assert "- **Rule id:** `dynamic/value`" in text
    assert "### 1. Unresolved value" in text
    assert "- **Reason:** dynamic value" in text
    assert "- **Evidence (1):**" in text
    tokens = MarkdownIt("commonmark").parse(text)
    replacement = next(token.children for token in tokens if token.content.startswith("**Replacement:**"))
    start = next(i for i, token in enumerate(replacement) if token.content == "<code>")
    end = next(i for i, token in enumerate(replacement) if token.content == "</code>")
    assert [(token.type, token.content) for token in replacement[start + 1 : end]] == [
        ("text", "size=`x-small`"),
        ("html_inline", "<br>"),
        ("text", literal),
    ]
    headings = [
        "".join(child.content for child in tokens[i + 1].children or [] if child.type in {"text", "code_inline"})
        for i, token in enumerate(tokens)
        if token.type == "heading_open" and token.tag == "h3"
    ]
    assert f"1. {first['title']}" in headings
    assert f"1. {manual['subject']}" in headings
    start = next(i for i, token in enumerate(tokens) if token.content == "Limitations")
    end = next(i for i, token in enumerate(tokens) if token.content == "Summary")
    shown = tokens[start + 2 : end - 1]
    assert sum(token.type == "bullet_list_open" for token in shown) == 1
    assert [
        [(child.type, child.content) for child in token.children or []] for token in shown if token.type == "inline"
    ] == [[("text", value)] for value in limitations]


def test_authored_copy_maps_findings_using_release_skills(sources):
    calls, session = submitted(report(findings=[finding()]))
    sources.at.mkdir()
    done = audit.audit(sources.at, web=sources.web, tree=sources.tree, version=VERSION, session=session)
    [(at, skills, message)] = calls
    assert (at / "web/pages/demo.mjs").read_text(encoding="utf-8") == PAGE
    assert not (at / "web/pds").exists()
    assert not (at / "web/vendor").exists()
    assert json.loads((at / "package.json").read_text(encoding="utf-8"))["dependencies"] == {pin.NAME: VERSION}
    assert skills == at / audit.PACKAGE / "skills"
    assert (skills / audit.SKILL / "references/report.schema.json").is_file()
    assert VERSION in message
    assert done.verdict.outcome == "findings"
    [found] = done.verdict.findings
    assert (found.path, found.line) == (f"{pin.PREFIX}web/pages/demo.mjs", 2)
    assert found.replacement == {"from": 'size="x-small"', "to": 'size="xs"'}
    assert 'size="x-small"' in PAGE.splitlines()[found.line - 1]
    absolute = str(sources.at.resolve() / "web/pages/demo.mjs")
    verdict = audit.judge(report(findings=[finding(path=absolute)], included=[str(sources.at)]), schema=SCHEMA,
                          version=VERSION, at=sources.at)  # fmt: skip
    assert verdict.findings[0].path == f"{pin.PREFIX}web/pages/demo.mjs"


def test_clean_audit_writes_submitted_json_and_host_markdown(sources, tmp_path):
    clean = json.dumps(report(), indent=1)
    done = audited(sources, clean)
    assert done.verdict == audit.Verdict("pass")
    audit.write(tmp_path / "out", done)
    folder = tmp_path / "out" / audit.REPORTS / done.run_id
    assert (folder / f"{audit.SKILL}.json").read_text(encoding="utf-8") == clean
    assert (folder / f"{audit.SKILL}.md").read_text(encoding="utf-8") == done.markdown
    assert (
        MarkdownIt("commonmark")
        .render(done.markdown)
        .startswith("<h1>Porsche Design System deprecation audit (js) \u2014 2026-11-01T00-00-00Z</h1>\n")
    )
    assert "- **0** findings across **0** locations\n- **0** manual follow-ups" in done.markdown
    assert "No deprecated usage was found." in done.markdown
    assert "No manual follow-ups." in done.markdown
    assert "| Effort |" not in done.markdown
    assert "| Confidence |" not in done.markdown
    section = TEMPLATE.index("## How to act on this report")
    expected_footer = TEMPLATE[section : TEMPLATE.index("\n````", section)]
    assert done.markdown.endswith(expected_footer.replace("<audit.pdsVersion>", VERSION) + "\n")


def test_followup_identity_preserves_subject_and_normalizes_evidence(tmp_path):
    same = "html`<p-text   size=${s}>`"  # whitespace apart from the other evidence
    verdict = audit.judge(
        report(follow_ups=[follow_up("p-text size"), follow_up("p-text weight", snippet=same)]),
        schema=SCHEMA,
        version=VERSION,
        at=tmp_path,
    )
    assert verdict.outcome == "follow-ups"
    assert not verdict.findings
    one, two = verdict.follow_ups
    assert one.evidence == two.evidence
    assert one.key != two.key
    again = audit.follow_up(follow_up("p-text size", snippet=same))
    assert again.key == one.key
    assert audit.follow_up(follow_up("p-text size", snippet="html`<p-text size=${t}>`")).key != one.key


@pytest.mark.parametrize(
    "cause",
    ["version", "partial", "failed", "result", "missing", "text", "limitation", "skipped", "excluded", "root", "gaps"],
)
def test_incomplete_report_refusals_preserve_reason_and_available_artifacts(sources, whole_error, cause):
    body, why = {
        "version": (report(version="4.9.0"), "pdsVersion '4.9.0'"),
        "partial": (report(result="partial", limitations=["one package unread"]), "ended partial"),
        "failed": (report(result="failed", limitations=["no package.json"]), "ended failed"),
        "result": ({**report(), "summary": {"result": whole_error}}, ""),
        "missing": ({k: v for k, v in report().items() if k != "findings"}, "breaks its schema"),
        "text": (whole_error, ""),
        "limitation": (report(limitations=["templates in .html not read"]), "disclosed gaps: templates"),
        "gaps": (
            report(skipped=["web/a.mjs"], limitations=[whole_error]),
            f"the audit disclosed gaps: web/a.mjs skipped (unreadable); {whole_error}",
        ),
        "skipped": (report(skipped=["web/pages/big.mjs"]), "web/pages/big.mjs skipped"),
        "excluded": (report(excluded=["web/pages"]), ""),
        "root": (report(included=["web"]), "did not include the project root"),
    }[cause]
    if cause == "result":
        [error] = jsonschema.Draft202012Validator(SCHEMA).iter_errors(body)
        why = (
            f"the audit report breaks its schema at summary/result: {error.message}\n"
            f"submitted audit report:\n{json.dumps(body)}"
        )
        assert len(why) > 300
    elif cause == "text":
        with pytest.raises(json.JSONDecodeError, match="Expecting value") as raised:
            json.loads(whole_error)
        why = (
            f"the audit report is not JSON: {type(raised.value).__name__}: {raised.value}\n"
            f"submitted audit report:\n{whole_error}"
        )
    elif cause == "excluded":
        body["scope"]["excludedPaths"][-1]["reason"] = whole_error
        why = f"the audit left out web/pages ({whole_error})"
    done = audited(sources, body)
    assert done.verdict.outcome == "stop"
    if cause in {"result", "text", "gaps", "excluded"}:
        assert done.verdict.reason == why
    else:
        assert why in done.verdict.reason
    out = sources.at.parent / "out"
    audit.write(out, done)
    folder = out / audit.REPORTS / done.run_id
    if isinstance(body, dict):
        assert (folder / f"{audit.SKILL}.json").read_text(encoding="utf-8") == json.dumps(body)
    if isinstance(body, dict) and jsonschema.Draft202012Validator(SCHEMA).is_valid(body):
        assert done.report == body
        assert f"- **Result:** `{body['summary']['result']}`" in done.markdown
        assert "## How to act on this report" in done.markdown
        assert (folder / f"{audit.SKILL}.md").read_text(encoding="utf-8") == done.markdown
    else:
        assert not done.markdown
        assert not (folder / f"{audit.SKILL}.md").exists()


@pytest.mark.parametrize(
    ("edit", "uncertain"),
    [
        (
            lambda at: (at / audit.PACKAGE / "skills" / audit.SKILL / "references/deprecations.md").write_text(
                "# none\n"
            ),
            False,
        ),
        (lambda at: (at / "web/pages/demo.mjs").write_text(PAGE.replace("x-small", "xs")), False),
        (lambda at: (at / ".pds").mkdir() or (at / ".pds/note.md").write_text("x"), False),
        (lambda at: (at / "web/pages/demo.mjs").write_text(PAGE.replace("x-small", "xs")), True),
    ],
    ids=["index", "page", "added", "page-unverified-end"],
)
@pytest.mark.usefixtures("no_render")
def test_mutated_audit_copy_is_void_and_retains_uncertain_end(sources, edit, uncertain, whole_error):
    end = (
        Termination(confirmed=False, survivors=(4242,), problems=(whole_error,))
        if uncertain
        else (Termination(confirmed=True))
    )
    done = audited(sources, report(), edit=edit, termination=end)
    assert done.verdict.outcome == "stop"
    assert "changed its copy" in done.verdict.reason
    assert done.report is None
    if uncertain:
        assert done.verdict.reason == (
            "the auditor changed its copy: web/pages/demo.mjs; termination unverified: processes 4242 still present; "
            f"{whole_error}"
        )


UNENDED = "the auditor's processes are not proven ended; recover the session on the Maintenance page; "
UNENDED += "termination unverified: "


@pytest.mark.parametrize(
    ("run", "why"),
    [
        (
            {"ending": "error", "payload": None, "detail": "quota"},
            "no usable audit report was accepted: ended error; quota",
        ),
        ({"termination": Termination(confirmed=False, survivors=(4242,))}, f"{UNENDED}processes 4242 still present"),
        ({"termination": None}, f"{UNENDED}termination did not run"),
        ({"usage_unread": "no usage event"}, "the auditor's model is unknown: no usage event"),
    ],
    ids=["no-result", "unconfirmed", "no-termination", "usage"],
)
@pytest.mark.usefixtures("no_render")
def test_unclean_auditor_session_never_accepts_clean_report(sources, run, why, whole_error):
    if run.get("ending") == "error":
        run = run | {"detail": whole_error}
        why = f"no usable audit report was accepted: ended error; {whole_error}"
    elif "usage_unread" in run:
        run = run | {"usage_unread": whole_error}
        why = f"the auditor's model is unknown: {whole_error}"
    verdict = audited(sources, report(), **run).verdict
    assert (verdict.outcome, verdict.reason) == ("stop", why)


def auditor_settings(**auditor: object) -> config.Settings:
    base = carried.layer()
    agents = base.agents | {"auditor": base.agents["curator"].model_copy(update=auditor)} if auditor else base.agents
    switches = dict.fromkeys(roles.USER_CONFIG, False) | {"guard_level": "strict"}
    return resolve(base.model_copy(update={"agents": agents, **switches}), Layer())


def test_auditor_sdk_policy_uses_configured_role_and_refuses_unset(tmp_path, production):
    with pytest.raises(SettingsUnset, match=r"agents\.auditor\.model"):
        sessions.auditor(production, tmp_path, tmp_path / "skills", "audit it")
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


def test_audit_submit_gate_allows_correction_and_reports_exhaustion_whole(sources, whole_error):
    """D-01M5DW3X00DR0Q4AC9294F0W9T: the tool checks the report against the copy's schema while it can be fixed."""
    sources.at.mkdir()
    skills = audit.lay_out(sources.at, sources.web, sources.tree, VERSION)
    cfg = sessions.auditor(auditor_settings(model="claude-opus-5.5"), sources.at, skills, "audit it")
    gate = Gate(cfg, Run("s"), lambda **_e: None, lambda: None)
    advertised = tool_schema.schema(audit_tools.SUBMIT)
    assert list(advertised["properties"]) == ["report"]
    assert advertised["required"] == ["report"]
    assert advertised["properties"]["report"]["maxLength"] == audit_tools.REPORT
    parsed, errors = tool_schema.parse(AuditResult, {"report": json.dumps(report()), "markdown": "# obsolete"})
    assert parsed is None
    assert any(error.startswith("markdown:") for error in errors)
    parsed, errors = tool_schema.parse(AuditResult, {"report": "x" * (audit_tools.REPORT + 1)})
    assert parsed is None
    assert any(f"at most {audit_tools.REPORT}" in error for error in errors)
    for bad, said in (("not JSON", "report: not JSON"), ("{}", "'schemaVersion' is a required property")):
        text, ok = gate.call(audit_tools.SUBMIT, AuditResult(report=bad))
        assert (ok, gate.done, said in text) == (False, False, True), text
    parsed, errors = tool_schema.parse(AuditResult, json.dumps({"report": json.dumps(report())}))
    assert isinstance(parsed, AuditResult)
    assert not errors
    text, ok = gate.call(audit_tools.SUBMIT, parsed)
    assert (ok, text, gate.done) == (True, ACCEPTED, True)
    gate = Gate(cfg, run := Run("s"), lambda **_e: None, lambda: None)
    for _ in range(3):
        text, ok = gate.call(audit_tools.SUBMIT, AuditResult(report=json.dumps(report(result=whole_error))))
    expected = (
        f"report: summary/result: {whole_error!r} is not one of ['completed', 'partial', 'failed']\n"
        f"submitted audit report:\n{json.dumps(report(result=whole_error))}"
    )
    assert (ok, run.ending, run.detail) == (False, "invalid", expected)
    assert text == f"Rejected. Fix each field, then call again:\n- {expected}"


@pytest.fixture
def production(monkeypatch) -> config.Settings:
    """A carried Global layer with no test layer under it: the auditor's row is unset until the owner fills it."""
    monkeypatch.setattr(config, "BASE", None)
    return auditor_settings()


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
        assert not (cfg.worktree / "web/pds").exists()
        assert not (cfg.worktree / "web/vendor").exists()
        if gate is not None:
            gate.wait(10)
        payload = AuditResult(report=json.dumps(body or report()))
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


def test_installed_hand_audit_persists_result_stop_and_interrupted_restart(tmp_path):
    body = report(findings=[finding()])
    h, http, seen = hand(tmp_path, body)
    assert http.get("/pds/audit").json() == {"state": "none"}
    assert http.post("/pds/audit").json()["state"] == "running"
    kept = settled(h)
    assert (kept["state"], kept["outcome"], kept["version"]) == ("done", "findings", VERSION)
    assert len(kept["commit"]) == 40 or kept["commit"] == "not a git checkout"
    assert kept["findings"][0]["path"] == f"{pin.PREFIX}web/pages/demo.mjs"
    assert kept["report"] == report(findings=[finding()])
    assert f"- **PDS version audited:** `{VERSION}`" in kept["markdown"]
    assert "- **1** findings across **1** locations" in kept["markdown"]
    assert 'html`<p-text size="x-small">Hi</p-text>`' in kept["markdown"]
    assert http.get("/pds/audit").json() == kept
    [cfg] = seen
    assert (cfg.role, cfg.job, cfg.model) == ("auditor", "pds-audit", "claude-opus-5.5")
    assert not h.maintenance.used[0].exists()
    assert not (tmp_path / "store" / ".pds").exists()  # the hand audit keeps its reports in its state alone
    body.clear()
    body.update(report(result="partial", limitations=["one package unread"]))
    http.post("/pds/audit")
    kept = settled(h)
    assert (kept["state"], kept["outcome"]) == ("failed", "stop")
    assert "ended partial" in kept["reason"]
    assert kept["report"] == body
    assert "- **Result:** `partial`" in kept["markdown"]
    assert "## How to act on this report" in kept["markdown"]
    h.path.write_text(json.dumps({"state": "running", "started_at": "2026-11-01T00:00:00+00:00"}), encoding="utf-8")
    assert http.get("/pds/audit").json()["reason"] == hand_audit.INTERRUPTED
    body.clear()
    body.update(report())
    assert http.post("/pds/audit").json()["state"] == "running"
    assert settled(h)["state"] == "done"
    assert all(not at.exists() for at in h.maintenance.used)


@pytest.mark.parametrize("why", ["running", "other-update", "unproven", "unbound", "unset"])
def test_hand_audit_exclusion_refuses_before_session_or_state_change(tmp_path, production, why):
    if why == "running":
        gate = threading.Event()
        h, http, seen = hand(tmp_path, gate=gate)
        http.post("/pds/audit")
        try:
            assert http.post("/pds/audit").status_code == 409
            assert http.get("/pds/audit").json()["state"] == "running"
            with pytest.raises(machine_lock.HeldError, match=r"shop \(PDS audit\)"):
                os.close(machine_lock.take(local_home.root() / MACHINE_LOCK, "other", lambda: None))
        finally:
            gate.set()
        assert settled(h)["state"] == "done"
        assert len(seen) == 1
        released = machine_lock.take(local_home.root() / MACHINE_LOCK, "other", lambda: None)
        os.close(released)
        return
    if why == "other-update":
        held = machine_lock.take(local_home.root() / MACHINE_LOCK, "garage", lambda: None)
        try:
            h, http, seen = hand(tmp_path)
            refused = http.post("/pds/audit")
        finally:
            os.close(held)
        assert refused.status_code == 409
        assert "an update runs for garage" in refused.json()["detail"]
        assert (seen, h.read()) == ([], {"state": "none"})
        return
    if why == "unset":
        h, http, seen = hand(tmp_path, settings=production)
        refused = http.post("/pds/audit")
        assert refused.status_code == 409
        assert "agents.auditor.model" in refused.json()["detail"]
        assert (seen, h.read()) == ([], {"state": "none"})
        return
    h, http, seen = hand(tmp_path, unproven=why == "unproven")
    if why == "unbound":
        h.maintenance = None
    refused = http.post("/pds/audit")
    assert refused.status_code == 409
    assert ("unproven" if why == "unproven" else "not bound") in refused.json()["detail"]
    assert (seen, h.read()) == ([], {"state": "none"})


class Host:
    maintenance = None
    wake = type("W", (), {"set": staticmethod(lambda: None)})()
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106
    paused = staticmethod(lambda: False)
    draining = staticmethod(lambda: False)
    closed = staticmethod(lambda: False)
    updating = staticmethod(lambda: "")
    launching = threading.Lock()


@pytest.mark.browser
def test_a_failed_hand_audit_shows_its_whole_reason(tmp_path, monkeypatch, caplog, pds, whole_error):
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    def failing(_self):
        broke = RuntimeError(whole_error)
        broke.add_note(f"the session's teardown also failed: OSError: {whole_error}")  # as loop_owner.run adds it
        raise broke

    monkeypatch.setattr(hand_audit.Hand, "_audit", failing)
    h, _http, _seen = hand(tmp_path)
    caplog.set_level(logging.WARNING, logger=hand_audit.__name__)
    h.start()
    reason = f"RuntimeError: {whole_error}\nthe session's teardown also failed: OSError: {whole_error}"
    assert settled(h)["reason"] == reason
    assert [r.getMessage() for r in caplog.records] == [f"PDS hand audit failed: {reason}"]  # with no page reading
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        server = uvicorn.Server(uvicorn.Config(api.create_app(Store(h.store.root), "tok", Host()), log_level="warning"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        try:
            while not server.started:
                assert thread.is_alive(), "the owned page server stopped before startup"
                time.sleep(0.05)
            base = f"http://127.0.0.1:{sock.getsockname()[1]}"
            with sync_playwright() as pw:
                try:
                    browser = pw.chromium.launch()
                except Error as exc:
                    pytest.skip(f"no Playwright Chromium: {exc}")
                page = browser.new_page()
                pds.only(page, base)
                page.add_init_script("sessionStorage.setItem('token', 'tok');")
                page.goto(f"{base}/updates/pds")
                shown = page.locator("#audit-reason")
                expect(shown).to_be_visible()
                assert shown.text_content() == f"{reason[0].upper()}{reason[1:]}."
                browser.close()
        finally:
            server.should_exit = True
            thread.join(5)
            assert not thread.is_alive(), "the owned page server did not stop"


def test_an_unreadable_saved_audit_answers_and_logs_its_whole_reason(tmp_path, caplog, whole_error):
    h, http, _seen = hand(tmp_path)
    h.path.parent.mkdir(parents=True)
    h.path.write_text(whole_error, encoding="utf-8")
    try:
        json.loads(whole_error)
    except ValueError as exc:
        reason = f"the saved audit {h.path} cannot be read: {type(exc).__name__}: {exc}\nsaved audit:\n{whole_error}"
    caplog.set_level(logging.WARNING, logger=hand_audit.__name__)

    assert http.get("/pds/audit").json() == {"state": "failed", "reason": reason}
    assert [r.getMessage() for r in caplog.records if r.name == hand_audit.__name__] == [
        f"PDS hand audit failed: {reason}"
    ]
