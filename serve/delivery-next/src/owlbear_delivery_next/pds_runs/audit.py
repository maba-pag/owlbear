"""The PDS deprecation audit (#777): a throwaway copy of the pages, the auditor's reports and the gate they pass.

The copy holds what OwlBear authors under ``web/`` (not the vendored ``web/pds/`` and ``web/vendor/``), a
``package.json`` depending on the audited release and that release's vendored files as its installed package. The
auditor only reads it: every file's digest is compared after its session, and any change voids the audit. The report
is checked against the release's own schema and the gate rule below; finding paths map back to repository paths.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import jsonschema

from owlbear_delivery_next.change_contracts import audit_tools
from owlbear_delivery_next.pds_runs import pin

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.runtimes.session_result import Run

SKILL, PACKAGE, SCHEMA = audit_tools.SKILL, audit_tools.PACKAGE, audit_tools.SCHEMA
VENDORED = ("pds", "vendor")  # folders under web/ OwlBear vendors rather than authors: never audited
EXCLUDABLE = ("node_modules/", ".pds/")  # the only paths the auditor may leave out
REPORTS = Path(".pds", "audits")
type Outcome = Literal["pass", "findings", "follow-ups", "stop"]


@dataclass(frozen=True)
class Finding:
    """One deprecated usage at one place: its repository path, line and quoted source, and the fix."""

    path: str
    line: int
    snippet: str
    rule: str
    title: str
    fix: str
    replacement: dict[str, str] | None = None


@dataclass(frozen=True)
class FollowUp:
    """A usage the audit could not resolve, for a human: its identity covers its subject, rule and evidence set."""

    key: str
    subject: str
    reason: str
    evidence: list[dict[str, Any]]


@dataclass(frozen=True)
class Verdict:
    """How the gate judged one audit: pass, findings for the updater, follow-ups for the owner, or stop."""

    outcome: Outcome
    reason: str = ""
    findings: list[Finding] = field(default_factory=list)
    follow_ups: list[FollowUp] = field(default_factory=list)


@dataclass(frozen=True)
class Audit:
    """One audit's verdict, with the reports the auditor submitted (none when it submitted nothing usable)."""

    verdict: Verdict
    run_id: str
    report: dict[str, Any] | None = None
    raw: str = ""  # the JSON report as submitted, which the host writes
    markdown: str = ""


def run_id(now: datetime | None = None) -> str:
    """A filesystem-safe UTC timestamp naming one audit, as the skill names its run folders."""
    return (now or datetime.now(UTC)).astimezone(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")


def lay_out(at: Path, web: Path, tree: Path, version: str) -> Path:
    """Lay the copy out at *at* from the pages *web* and the release's vendored *tree*; return its skills folder."""
    _copy(web, at / "web", skip=VENDORED)
    manifest = {"name": "owlbear-pages", "private": True, "dependencies": {pin.NAME: version}}
    (at / "package.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    _copy(tree, at / PACKAGE)
    return at / PACKAGE / "skills"


def _copy(source: Path, target: Path, skip: tuple[str, ...] = ()) -> None:
    for path in sorted(source.rglob("*")):
        rel = path.relative_to(source)
        if rel.parts[0] in skip or path.is_symlink() or not path.is_file():
            continue
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target / rel)


def digests(at: Path) -> dict[str, str]:
    """Every file under *at* by its relative path: its SHA-256, or ``link`` for a symlink."""
    out: dict[str, str] = {}
    for path in sorted(at.rglob("*")):
        rel = path.relative_to(at).as_posix()
        if path.is_symlink():
            out[rel] = "link"
        elif path.is_file():
            out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def changed(before: dict[str, str], after: dict[str, str]) -> list[str]:
    """The paths the session added, removed or changed."""
    return sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))


def message(version: str, ident: str) -> str:
    """The auditor's first message."""
    return (
        f"Audit this project for deprecated Porsche Design System use with the `{SKILL}` skill: PDS {version}, "
        f"{pin.NAME} under node_modules/. The project root is your working folder and `.` is its one package. "
        f"Use runId {ident}. Submit both reports with submit_result; write no file."
    )


def audit(  # noqa: PLR0913 - the copy's inputs and the session that reads it
    at: Path,
    *,
    web: Path,
    tree: Path,
    version: str,
    session: Callable[[Path, Path, str], Run],
    now: datetime | None = None,
) -> Audit:
    """Audit *web* against the release in *tree* in a copy at *at*; *session* runs the auditor on (at, skills, msg)."""
    ident = run_id(now)
    skills = lay_out(at, web, tree, version)
    schema = json.loads((tree / SCHEMA).read_text(encoding="utf-8"))
    before = digests(at)
    done = session(at, skills, message(version, ident))
    if moved := changed(before, digests(at)):  # first: a changed copy voids whatever the report says
        return Audit(Verdict("stop", f"the auditor changed its copy: {', '.join(moved[:5])}"), ident)
    result = done.payload if isinstance(done.payload, audit_tools.AuditResult) else None
    if why := _unended(done, result):
        return Audit(Verdict("stop", why), ident)
    assert result is not None  # noqa: S101 - _unended refuses a run without one
    try:
        report = json.loads(result.report)
    except ValueError as exc:
        return Audit(Verdict("stop", f"the audit report is not JSON: {exc}"[:300]), ident, markdown=result.markdown)
    verdict = judge(report, schema=schema, version=version, at=at)
    kept = report if isinstance(report, dict) else None
    return Audit(verdict, ident, kept, result.report if kept is not None else "", result.markdown)


def _unended(done: Run, result: audit_tools.AuditResult | None) -> str:
    t = done.termination
    if done.ending != "result" or result is None:
        return " ".join(f"the auditor submitted no report: ended {done.ending}; {done.detail}".split())[:300]
    if t is None or not t.confirmed:
        return "the auditor's processes are not proven ended; recover the session on the Maintenance page"
    if done.usage_unread:
        return " ".join(f"the auditor's model is unknown: {done.usage_unread}".split())[:300]
    return ""


def judge(report: object, *, schema: dict[str, Any], version: str, at: Path | None = None) -> Verdict:  # noqa: PLR0911
    """The gate's verdict on *report* from the copy at *at*: every stop first, then findings, follow-ups, a pass."""
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(report), key=lambda e: list(e.absolute_path))
    if errors:
        where = "/".join(str(p) for p in errors[0].absolute_path) or "the report"
        return Verdict("stop", f"the audit report breaks its schema at {where}: {errors[0].message}"[:300])
    assert isinstance(report, dict)  # noqa: S101 - the schema requires an object
    if (result := report["summary"]["result"]) != "completed":
        return Verdict("stop", f"the audit ended {result}: {_gaps(report)}")
    if why := _mismatch(report["audit"], version):
        return Verdict("stop", why)
    if gaps := _gaps(report):
        return Verdict("stop", f"the audit disclosed gaps: {gaps}")
    if why := _scope(report["scope"], at):
        return Verdict("stop", why)
    if report["findings"]:
        return Verdict("findings", findings=[f for item in report["findings"] for f in mapped(item, at)])
    if report["manualFollowUps"]:
        return Verdict("follow-ups", follow_ups=[follow_up(item, at) for item in report["manualFollowUps"]])
    return Verdict("pass")


def _mismatch(audit: dict[str, Any], version: str) -> str:
    wanted = {"skillName": SKILL, "framework": "js", "pdsVersion": version}
    wrong = [f"{k} {audit.get(k)!r}, not {v!r}" for k, v in wanted.items() if audit.get(k) != v]
    return f"the audit report names {'; '.join(wrong)}" if wrong else ""


def _gaps(report: dict[str, Any]) -> str:
    coverage = report.get("coverage") or {}
    skipped = [f"{s['path']} skipped ({s['reason']})" for s in coverage.get("skippedFiles") or ()]
    return "; ".join([*skipped, *coverage.get("limitations", ())])[:600]


def _scope(scope: dict[str, Any], at: Path | None) -> str:
    if "." not in {_relative(p, at) for p in scope["includedPaths"]}:
        return f"the audit did not include the project root: {', '.join(scope['includedPaths']) or 'nothing'}"
    out = [e for e in scope["excludedPaths"] if not f"{_relative(e['path'], at)}/".startswith(EXCLUDABLE)]
    if out:
        return "the audit left out " + "; ".join(f"{e['path']} ({e['reason']})" for e in out)[:600]
    return ""


def _relative(path: str, at: Path | None) -> str:
    """*path* relative to the copy's root: ``./`` dropped, an absolute path under *at* made relative."""
    for root in (at, at.resolve()) if at is not None and Path(path).is_absolute() else ():
        if Path(path).is_relative_to(root):
            return Path(path).relative_to(root).as_posix()
    return "." if path in (".", "./") else path.removeprefix("./")


def repository(path: str, at: Path | None = None) -> str:
    """The repository path of the copy's *path*: its pages sit in the package folder; others keep their copy path."""
    rel = _relative(path, at)
    return f"{pin.PREFIX}{rel}" if rel.startswith("web/") else rel


def mapped(item: dict[str, Any], at: Path | None = None) -> list[Finding]:
    """One finding's evidence, each place at its repository path."""
    fix = item["remediation"]
    return [
        Finding(
            path=repository(e["path"], at), line=e["line"], snippet=e["snippet"], rule=item["ruleId"],
            title=item["title"], fix=fix["instruction"], replacement=fix.get("replacement"),
        )
        for e in item["evidence"]
    ]  # fmt: skip


def follow_up(item: dict[str, Any], at: Path | None = None) -> FollowUp:
    """A follow-up with its identity: subject, rule (when given) and the sorted, whitespace-normalised evidence set."""
    places = sorted((repository(e["path"], at), e["line"], " ".join(e["snippet"].split())) for e in item["evidence"])
    body = json.dumps([item["subject"], item.get("ruleId"), places])
    shown = [{"path": p, "line": n, "snippet": s} for p, n, s in places]
    return FollowUp(hashlib.sha256(body.encode()).hexdigest(), item["subject"], item["reason"], shown)


def write(out: Path, done: Audit) -> Path | None:
    """Write the submitted reports as the skill names them, in *out*'s ``.pds/audits/<runId>/``; None without one."""
    if done.report is None:
        return None
    folder = out / REPORTS / done.run_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{SKILL}.json").write_text(done.raw, encoding="utf-8")
    (folder / f"{SKILL}.md").write_text(done.markdown, encoding="utf-8")
    return folder
