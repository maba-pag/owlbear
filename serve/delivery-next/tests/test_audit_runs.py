"""Audit publication custody and shared-Git read-only boundaries."""

import contextlib
import subprocess
from types import SimpleNamespace

from owlbear_delivery_next.audit_runs import job, publish, record
from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.github.owlbear_issues import OwlbearIssues
from owlbear_delivery_next.state_store.store import Store


def _report():
    return {
        "id": "run-one",
        "host": "fixture",
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


def test_finish_recovers_a_lost_receipt_without_duplicate_issue(tmp_path, monkeypatch):
    store = Store(tmp_path / "store", name="fixture")
    state, written, listing = _report(), [], []

    def add(*_args, **kwargs):
        persisted = record.load(store)["doc"]["findings"][0]
        assert persisted["pending"]
        written.append(kwargs["evidence"][0])
        msg = "GitHub accepted the write but its response was lost"
        raise OSError(msg)

    book = SimpleNamespace(
        repository="fixture/private",
        add=add,
        read=lambda **_kw: ({e.id: e for e in listing}, []),
    )
    monkeypatch.setattr(job.backlog.Backlog, "of", lambda _store: book)
    record.save(store, "doc", state)
    audits = job.Audits(store)
    audits.publish("doc")
    audits.thread.join()
    partial = audits.read("doc")
    assert partial["state"] == "publishing"
    assert partial["findings"][0]["pending"]
    assert "response was lost" in partial["reason"]
    audits.publish("doc")
    audits.thread.join()
    assert "two minutes" in audits.read("doc")["reason"]
    assert written == ["audit:run-one:1"]
    listing.append(SimpleNamespace(id="42", evidence=["audit:run-one:1"]))
    audits.finish("doc")
    audits.thread.join()
    finished = audits.read("doc")
    assert finished["state"] == "done"
    assert finished["findings"][0]["number"] == 42
    assert written == ["audit:run-one:1"]


def test_shared_git_mutation_voids_even_an_errored_session(tmp_path, monkeypatch):
    repo = tmp_path / "clone"
    repo.mkdir()
    worktree.git(repo, "init", "--quiet")
    worktree.git(repo, "config", "user.name", "Fixture")
    worktree.git(repo, "config", "user.email", "fixture@example.invalid")
    (repo / "README.md").write_text("Fixture\n")
    worktree.git(repo, "add", "README.md")
    worktree.git(repo, "commit", "--quiet", "-m", "Fixture")
    commit = worktree.git(repo, "rev-parse", "HEAD").strip()
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
        worktree.git(repo, "tag", "audit-mutation")
        msg = "session connection ended"
        raise OSError(msg)

    audits.run = session
    audits.start("doc")
    audits.thread.join()
    saved = audits.read("doc")
    assert saved["state"] == "failed"
    assert "created tag audit-mutation" in saved["reason"]
    assert not published
    assert worktree.git(repo, "rev-parse", "refs/tags/audit-mutation").strip() == commit
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
