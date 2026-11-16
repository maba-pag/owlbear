"""Local deterministic audit replay over private cases, with real contracts and Git inspection."""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import replace
from pathlib import Path
from subprocess import SubprocessError
from typing import Any

from owlbear_delivery_next.audit_runs import replay_transport, report_publish, sessions, workspace
from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.local_system import data_place

CORPUS = Path("owlbear/research/code-audit-replay")
LIMITS = (
    "Fixture/scripted transport only. No provider SDK, live model judgment, real subagents, GitHub writes, "
    "registered project or host lifecycle operation. Model identity and confirmed termination are simulated. "
    "Credits: 0 actual provider requests; fixture credits are not provider usage evidence."
)


def run(repo: Path, *, corpus: Path | None = None) -> tuple[bool, str]:
    """Return pass/fail and report text; never write reports into the shared data checkout.

    ``corpus`` is a private Python-driver seam for an owned data clone before publication,
    not a public command option. Historical objects must already exist in ``repo``.
    """
    lines = ["# Code audit deterministic replay", "", LIMITS, ""]
    scratch: Path | None = None
    try:
        source = corpus if corpus is not None else _installed()
        expected = _json(source / "expectations.json")
        cases = sorted((source / "cases").iterdir())
        names = [case.name for case in cases if case.is_dir()]
        _require(bool(names) and set(names) == set(expected["cases"]), "case inventory differs from frozen corpus")
        repo = Path(worktree.git(repo, "rev-parse", "--show-toplevel").strip())
        scratch = repo / ".owlbear" / "scratch" / f"audit-replay-{uuid.uuid4().hex}"
        scratch.mkdir(parents=True)
        for case in cases:
            if not case.is_dir():
                continue
            lines.extend([f"## {case.name}", ""])
            got = _case(repo, scratch / case.name, case)
            want = expected["cases"][case.name]
            lines.extend(
                [
                    "Expected (frozen independently):",
                    _block(want),
                    "Got (checked session results and recording publisher):",
                    _block(got),
                ]
            )
            _compare(want, got, expected["summary_sections"])
            lines.extend(["PASS", ""])
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, SubprocessError) as exc:
        lines.extend([f"FAIL: {failure(exc)}", "", "Replay stopped at the first mismatch or execution error."])
        return False, "\n".join(lines)
    finally:
        if scratch is not None:
            shutil.rmtree(scratch)
    lines.append("PASS: every frozen case passed in one invocation.")
    return True, "\n".join(lines)


def _installed() -> Path:
    shared = data_place.configured_root()
    if shared is None:
        msg = "audit replay needs the shared data checkout and its private code-audit-replay corpus"
        raise FileNotFoundError(msg)
    return shared / CORPUS


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _block(value: object) -> str:
    return "```json\n" + json.dumps(value, indent=2, ensure_ascii=False) + "\n```\n"


def _require(condition: object, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _case(repo: Path, root: Path, case: Path) -> dict[str, Any]:
    """Run constructors and Gate before any expectations are passed to comparison."""
    data = _json(case / "case.json")
    root.mkdir()
    shutil.copytree(case / "context", root / "context")
    commit = worktree.git(repo, "rev-parse", "--verify", "--end-of-options", f"{data['commit']}^{{commit}}").strip()
    script = replay_transport.Script(case / "transport.json")
    store = replay_transport.FixtureStore(root / "store", name="fixture")
    store.root.mkdir()
    state, runs = _state(data, root, case.name, commit), []
    with replay_transport.opened(repo, root, commit) as copy:
        authority = copy.path / ".owlbear"
        shutil.copy2(authority / "decisions.md", root / "context" / "decisions.md")
        research = root / "context" / "research"
        research.mkdir(exist_ok=True)
        shutil.copy2(authority / "research" / "owlbear-plan.md", research / "owlbear-plan.md")
        workspace.inspect(copy, commit)
        if data["mode"] == "end-to-end":
            _write_run(root, state)
            cfg = sessions.auditor(store, root, "code", data["note"], helper=_no_target)
            cfg = replace(cfg, session_id=f"fixture-{case.name}-auditor")
            try:
                done = script.run(cfg, "auditor")
            finally:
                workspace.inspect(copy, commit)
            found = sessions.accepted(done, root)
            limits = [*state["not_covered"], *found.not_covered]
            state.update(found.model_dump(mode="json"), session=done.session_id, subagents=done.subagents)
            state["not_covered"] = limits
            runs.append(replay_transport.evidence(done))
        else:
            _require(data["mode"] == "verifier", "case mode must be verifier or end-to-end")
        _write_run(root, state)
        cfg = sessions.verifier(store, root, data["note"])
        cfg = replace(cfg, session_id=f"fixture-{case.name}-verifier")
        try:
            done = script.run(cfg, "verifier")
        finally:
            workspace.inspect(copy, commit)
        checked = sessions.verified(done, root)
        state.update(
            verified=True, verdicts=checked.model_dump(mode="json")["verdicts"], verifier_session=done.session_id
        )
        runs.append(replay_transport.evidence(done))
    state["findings"] = [{**row, "number": None, "url": "", "pending": None} for row in state["findings"]]
    sink = report_publish.Recorder()
    report_publish.publish(state, sink, lambda: _write_run(root, state), project="fixture", audit="code")
    return state | {
        "titles": [row["title"] for row in state["findings"]],
        "helpers": sum(row.get("part") == "helper" for row in state["subagents"]),
        "refusals": script.refusals,
        "runs": runs,
        "issues": sink.issues,
    }


def _state(data: dict[str, Any], root: Path, name: str, commit: str) -> dict[str, Any]:
    return {
        "id": f"fixture-{name}",
        "state": "publishing",
        "phase": "checking findings",
        "started_at": "fixture",
        "ended_at": "",
        "branch": "detached historical fixture",
        "commit": commit,
        "note": data["note"],
        "destination": "",
        "changed_defaults": [],
        "findings": data.get("findings", []),
        "summary": data["summary"],
        "parts": [],
        "not_covered": [(root / "context" / "limits.md").read_text(encoding="utf-8").strip()],
        "subagents": [],
        "session": "",
        "verifier_session": "",
        "verified": False,
        "verdicts": [],
        "summary_issue": {"number": None, "url": "", "pending": None, "complete": False},
        "reason": "",
    }


def _write_run(root: Path, state: dict[str, Any]) -> None:
    (root / "context" / "run.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _no_target(_args: object) -> str:
    msg = "historical fixture target is fixed; this replay script does not request another target"
    raise ValueError(msg)


def _compare(want: dict[str, Any], got: dict[str, Any], sections: list[str]) -> None:
    _require(got["commit"] == want["commit"], "historical commit differs")
    _require(got["titles"] == want["titles"], "finding titles or order differ")
    actual = got["verdicts"]
    _require(len(actual) == len(want["verdicts"]), "verdict count differs")
    for expected, row in zip(want["verdicts"], actual, strict=True):
        _require(
            all(row[key] == expected[key] for key in ("finding", "verdict", "duplicate_of")),
            f"finding {expected['finding']}: verdict or duplicate reference differs",
        )
        _require(bool(row["reason"].strip()), f"finding {row['finding']}: empty reason")
        authority = row["reason"] + "\n" + "\n".join(row["decisions"])
        for reference in expected["references"]:
            _require(reference in authority, f"finding {row['finding']}: missing authority reference {reference}")
    parts = got["parts"]
    _require([row["part"] for row in parts] == want["parts"], "lens parts differ")
    _require(all(row["ran"] and row["note"].strip() for row in parts), "a lens part did not run or lacks evidence")
    _require(got["helpers"] == want["helpers"], "helper count differs")
    _require(len(got["subagents"]) == want["subagents"], "scripted subagent count differs")
    if parts:
        _require(got["subagents"][0]["part"] == "helper", "helper did not precede the lens parts")
        _require([row["part"] for row in got["subagents"][1:]] == want["parts"], "part subagent sequence differs")
    _require(len(got["refusals"]) == want["corrections"], "incomplete-verdict correction count differs")
    for refusal in got["refusals"]:
        _require("verdict" in refusal.lower() or "finding" in refusal.lower(), "Gate refusal does not name its field")
    _publication(got, sections)


def _publication(got: dict[str, Any], sections: list[str]) -> None:
    issues, summary = got["issues"], got["summary_issue"]
    _require(summary["complete"] and summary["number"] == 1, "summary did not complete first")
    body = issues[summary["number"]]["body"]
    _require("audit:summary" in issues[1]["labels"], "summary label missing")
    for section in sections:
        _require(f"## {section}" in body, f"summary section missing: {section}")
    for field in ("commit", "summary", "note", "session", "verifier_session"):
        _require(not got[field] or got[field] in body, f"summary omitted {field}")
    for row in got["changed_defaults"]:
        _require(all(row[key] in body for key in ("default", "to", "reason")), "summary omitted a changed default")
    for row in got["parts"]:
        _require(row["part"] in body and row["note"] in body, "summary omitted a lens part")
    for gap in got["not_covered"]:
        _require(gap in body, "summary omitted a coverage gap")
    _require(f"Subagents: {len(got['subagents'])}" in body, "summary omitted scripted subagent use")
    _require("Destination: Backlog" in body, "summary omitted the destination")
    accepted = {row["finding"] for row in got["verdicts"] if row["verdict"] == "accepted"}
    _require(len(issues) == len(accepted) + 1, "publisher opened the wrong number of issues")
    for index, finding in enumerate(got["findings"], 1):
        if index in accepted:
            issue = issues[finding["number"]]
            _require(finding["url"] in body and finding["title"] in body, "summary omitted a finding link")
            _require(summary["url"] in issue["body"], "finding omitted its summary link")
            _require(f"audit:{got['id']}:{index}" in issue["body"], "finding's original number was not preserved")
            _require(
                all(
                    label in issue["labels"] for label in (f"type:{finding['type']}", f"severity:{finding['severity']}")
                ),
                "finding type or severity label missing",
            )
        else:
            _require(finding["number"] is None, "publisher opened a rejected or unsure finding")
            verdict = next(row for row in got["verdicts"] if row["finding"] == index)
            _require(finding["title"] in body and verdict["reason"] in body, "summary omitted an unaccepted finding")
            for ref in [*verdict["decisions"], verdict["duplicate_of"]]:
                _require(not ref or ref in body, "summary omitted an authority or duplicate reference")
