"""Audit publication custody and shared-Git read-only boundaries."""

import contextlib
import json
import subprocess
from types import SimpleNamespace

import pytest

from owlbear_decisions import write
from owlbear_delivery_next.audit_runs import context, job, publish, record
from owlbear_delivery_next.change_contracts import project_audit_tools
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.github.owlbear_issues import OwlbearIssues
from owlbear_delivery_next.github.provider import FailureCode, ProviderError
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.project_host import pack_routes
from owlbear_delivery_next.settings import config, profile
from owlbear_delivery_next.state_store import backlog
from owlbear_delivery_next.state_store.store import Store

from .test_decision_lookup import make


def _report():
    return {
        "id": "run-one",
        "audit": "doc",
        "state": "publishing",
        "phase": "opening issues",
        "started_at": record.now(),
        "ended_at": "",
        "branch": "main",
        "commit": "abc",
        "note": "",
        "changed_defaults": [],
        "destination": "",
        "summary": "Checked docs.",
        "parts": [],
        "not_covered": [],
        "subagents": [],
        "reason": "",
        "findings": [
            {
                "title": "Removed command in setup",
                "type": "defect",
                "severity": "medium",
                "where": "setup.md:1",
                "evidence": "The named command no longer exists.",
                "recommendation": "Name the supported command.",
                "number": None,
                "url": "",
                "pending": None,
            }
        ],
    }


def test_finish_recovers_a_lost_receipt_without_duplicate_issue(tmp_path, monkeypatch, shared_repo, github):
    store = Store(tmp_path / "store", DataRepo(shared_repo[0]), "fixture")
    state, book = _report(), backlog.Backlog.of(store)
    earlier, _ = book.add(state["findings"][0]["title"], "earlier observation", "audit", ["audit:earlier:1"])
    book.update(earlier.id, {"kind": "defect", "status": "done"})
    edit = book.issues.edit

    def lost(number, fields):
        if number != int(earlier.id):
            return edit(number, fields)
        persisted = record.load(store)["doc"]["findings"][0]
        assert persisted["pending"]
        monkeypatch.setattr(book.issues, "edit", edit)
        github.hidden.add(2)
        backlog._recent.clear()  # noqa: SLF001 - simulate restart before GitHub lists the new issue
        raise ProviderError(FailureCode.RESPONSE_UNKNOWN, "edit_issue", "response lost", retry_safe=False)

    monkeypatch.setattr(book.issues, "edit", lost)
    monkeypatch.setattr(job.backlog.Backlog, "of", lambda _store: book)
    record.save(store, "doc", state)
    audits = job.Audits(store)
    audits.publish("doc")
    audits.thread.join()
    partial = audits.read("doc")
    assert partial["state"] == "publishing"
    assert partial["findings"][0]["pending"]
    assert "response lost" in partial["reason"]
    audits.publish("doc")
    audits.thread.join()
    assert "two minutes" in audits.read("doc")["reason"]
    assert len(github.issues) == 2
    github.hidden.clear()
    audits.publish("doc")
    audits.thread.join()
    finished = audits.read("doc")
    assert finished["state"] == "done"
    assert finished["findings"][0]["number"] == 2
    assert len(github.issues) == 2
    assert book.current("1").links == ["2"]
    assert book.current("2").links == ["1"]


def test_shared_git_mutation_voids_even_an_errored_session(tmp_path, monkeypatch):
    repo = tmp_path / "clone"
    repo.mkdir()
    worktree.git(repo, "init", "--quiet")
    worktree.git(repo, "remote", "add", "origin", "https://github.com/acme/tools.git")
    worktree.git(repo, "config", "user.name", "Fixture")
    worktree.git(repo, "config", "user.email", "fixture@example.invalid")
    (repo / "README.md").write_text("Fixture\n")
    worktree.git(repo, "add", "README.md")
    worktree.git(repo, "commit", "--quiet", "-m", "Fixture")
    commit = worktree.git(repo, "rev-parse", "HEAD").strip()
    worktree.git(repo, "tag", "audit-mutation")
    root = tmp_path / "workspace"
    root.mkdir()

    @contextlib.contextmanager
    def allocated(_prefix):
        yield root

    audits = job.Audits(Store(tmp_path / "store", name="fixture"))
    audits.repo = repo
    audits.maintenance = SimpleNamespace(workspace=allocated, retained=lambda _root: False)
    monkeypatch.setattr(job.workspace, "pin", lambda *_args: commit)
    monkeypatch.setattr(job.Audits, "refusal", lambda *_args: "")
    monkeypatch.setattr(job.profile, "value", lambda _p, key, *_a: "main" if key == job.profile.DEFAULT else "")
    monkeypatch.setattr(job.context, "prepare", lambda *_args: [])
    monkeypatch.setattr(job.sessions, "auditor", lambda _store, at, *_args, **_kw: at)
    published = []
    monkeypatch.setattr(job.publish, "findings", lambda *_args: published.append(True))

    def session(_root):
        worktree.git(repo, "tag", "--delete", "audit-mutation")
        msg = "session connection ended"
        raise OSError(msg)

    audits.run = session
    audits.start("doc")
    audits.thread.join()
    saved = audits.read("doc")
    assert saved["state"] == "failed"
    assert "deleted tag audit-mutation" in saved["reason"]
    assert not published
    assert not worktree.git(repo, "tag", "--list", "audit-mutation").strip()
    assert not (root / "repo").exists()


def test_redirected_finding_recovers_its_actual_issue_after_a_lost_receipt(tmp_path, monkeypatch, github):
    store, state = Store(tmp_path / "store", name="fixture"), _report()
    state.update(destination="acme/owlbear-data", note="File findings in acme/owlbear-data.")

    def transport(argv, data, timeout, cwd, env):
        answer = github(argv, data, timeout, cwd, env)
        if github.calls[-1][:2] == ("POST", "repos/acme/owlbear-data/issues"):
            github.hidden.add(1)
            return subprocess.CompletedProcess(argv, 1, b"", b"gh: connection reset")
        return answer

    monkeypatch.setattr(publish, "OwlbearIssues", lambda repo, root: OwlbearIssues(repo, root, runner=transport))
    record.save(store, "doc", state)
    audits = job.Audits(store)
    audits.publish("doc")
    audits.thread.join()
    assert audits.read("doc")["state"] == "publishing"
    assert "<!-- audit:run-one:1 -->" in github.issues[1]["body"]
    audits.publish("doc")
    audits.thread.join()
    assert "two minutes" in audits.read("doc")["reason"]
    github.hidden.clear()
    audits.publish("doc")
    audits.thread.join()
    assert audits.read("doc")["findings"][0]["number"] == 1
    assert audits.read("doc")["state"] == "done"
    assert len(github.issues) == 1


def test_redirected_destination_must_be_named_in_full(tmp_path):
    (tmp_path / "context").mkdir()
    (tmp_path / "context" / "run.json").write_text(json.dumps({"note": "File in acme/private-audit-reports."}))
    report = project_audit_tools.AuditFindings(
        findings=[],
        not_covered=[],
        changed_defaults=[],
        destination="acme/private-audit-reports",
        summary="No findings.",
    )
    assert project_audit_tools.check(report, tmp_path) == []
    report.destination = "acme/private"
    assert project_audit_tools.check(report, tmp_path)
    report.destination = "me/private-audit-reports"
    assert project_audit_tools.check(report, tmp_path)


def test_issue_context_uses_the_project_host_and_selected_account(tmp_path, monkeypatch, shared_repo, github, fake_gh):
    endpoint = "repos/acme/tools/issues?state=open&per_page=100&page=1"
    issues = [{"number": 7, "title": "Enterprise planning context", "body": "Full issue body", "labels": []}]
    fake_gh.set(
        {"github.com": {"acme": "success"}, "git.example.test": {"acme": "success", "octo-writer": "success"}},
        {"github.com": "acme", "git.example.test": "acme"},
        [{"has": ["api", endpoint], "out": issues}],
    )
    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"github_account": "octo-writer"}))
    store = Store(tmp_path / "store", DataRepo(shared_repo[0]), "fixture")
    store.write_profile(Profile(entries={profile.HOST: ProfileEntry(state="known", value="git.example.test")}))
    limits = context.prepare(store, tmp_path, _report(), "acme/tools")
    assert not any(line.startswith("issues:") for line in limits)
    assert json.loads((tmp_path / "context" / "issues.md").read_text()) == issues
    assert not github.issues
    launches = [call for call in fake_gh.calls() if call["argv"][0] == "api"]
    assert len(launches) == 1
    login = "octo-writer"
    assert launches[0]["GH_ENTERPRISE_TOKEN"] == f"tok-{login}"
    argv = launches[0]["argv"]
    assert argv[argv.index("--hostname") + 1] == "git.example.test"


def test_agent_audit_eligibility_follows_repository_identity_not_shared_folder(tmp_path, shared_repo):
    shared = DataRepo(shared_repo[0])
    shared.claim("renamed-engine", "github.com/maba-pag/owlbear")
    shared.claim("owlbear", "github.com/acme/consumer")
    engine = Store(tmp_path / "engine", shared, "renamed-engine")
    consumer = Store(tmp_path / "consumer", shared, "owlbear")
    assert job.Audits(engine).offered() == ("doc", "agent")
    assert job.Audits(engine).refusal("agent") == job.UNBOUND
    assert "Agent audit" in {row["name"] for row in pack_routes.overview(engine)}
    assert job.Audits(consumer).offered() == ("doc",)
    assert "not offered" in job.Audits(consumer).refusal("agent")
    assert "Agent audit" not in {row["name"] for row in pack_routes.overview(consumer)}


def test_unresolved_planning_authority_never_becomes_empty_audit_context(tmp_path, shared_repo):
    shared = DataRepo(shared_repo[0])
    shared.claim("shop-site", "github.com/acme/shop-site")
    rule = make(conflict=True)
    write(rule, shared.root / "shop-site")
    store = Store(tmp_path / "store", shared, "shop-site")
    with pytest.raises(ValueError, match="flagged conflict") as failed:
        context.prepare(store, tmp_path, _report(), "acme/shop-site")
    assert rule.id in str(failed.value)
    assert not (tmp_path / "context" / "decisions.md").exists()
